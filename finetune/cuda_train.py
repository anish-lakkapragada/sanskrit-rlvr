"""The CUDA trainer: TRL on Lambda-class GPUs. bf16 everywhere, no quantization.

    mode: sft  -> full-parameter fine-tune (TRL SFTTrainer)
    mode: grpo -> LoRA + GRPO, rollouts via colocated vLLM (TRL GRPOTrainer);
                  the KL reference is the base with adapters disabled, i.e.
                  exactly the model this run initialized from — no fused copy,
                  no requantization

Invoked by finetune.train as a subprocess (the same shape as the mlx
backend's mlx_lm_lora.train CLI); reads the run's frozen config.yaml.
Checkpoints land as checkpoint-<step>/ dirs plus a standalone final/ under
runs/<run_name>/checkpoints/.
"""

import argparse
from pathlib import Path

import yaml

from .common import ROOT, read_jsonl
from .reward import reward_from_answer_field


def sft_split(data_dir: Path, tok, split: str):
    """messages -> prompt/completion text pairs (TRL masks the prompt)."""
    from datasets import Dataset
    rows = []
    for r in read_jsonl(data_dir / f"{split}.jsonl"):
        msgs = r["messages"]
        rows.append({
            "prompt": tok.apply_chat_template(
                msgs[:-1], add_generation_prompt=True, tokenize=False),
            "completion": msgs[-1]["content"],
        })
    return Dataset.from_list(rows)


def grpo_dataset(data_dir: Path):
    """Conversational prompts; the grading contract rides in `answer` (an
    opaque JSON string TRL hands back to the reward function per sample)."""
    from datasets import Dataset
    return Dataset.from_list([
        {"prompt": [{"role": "system", "content": r["system"]},
                    {"role": "user", "content": r["prompt"]}],
         "answer": r["answer"]}
        for r in read_jsonl(data_dir / "train.jsonl")])


def lean_sanskrit_reward(prompts, completions, answer, **kwargs):
    """TRL reward contract: one score per completion, judged by Lean."""
    texts = [c[0]["content"] if isinstance(c, list) else c for c in completions]
    return [reward_from_answer_field(spec, text)
            for text, spec in zip(texts, answer)]


def lora_config(base: str, hp: dict):
    """Adapters on every projection of the last num_layers blocks — the same
    footprint the mlx backend trains (its default adapts all linears too)."""
    from peft import LoraConfig
    from transformers import AutoConfig
    total = AutoConfig.from_pretrained(base).num_hidden_layers
    n = int(hp.get("num_layers", 16))
    rank = int(hp.get("lora_rank", 8))
    return LoraConfig(
        r=rank,
        # mlx applies the LoRA delta with a flat scale (default 10); peft
        # scales by alpha/rank, so alpha = 10*rank reproduces it
        lora_alpha=int(hp.get("lora_alpha", 10 * rank)),
        lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        layers_to_transform=list(range(max(total - n, 0), total)),
        task_type="CAUSAL_LM",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path,
                    help="the run's frozen config.yaml (inside runs/<name>/)")
    ap.add_argument("--base", required=True,
                    help="resolved base model (HF id or local checkpoint dir)")
    ap.add_argument("--iters", required=True, type=int)
    ap.add_argument("--save-every", required=True, type=int)
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    hp = cfg["hyperparameters"]
    ckpt_dir = args.config.parent / "checkpoints"
    data_dir = ROOT / cfg["data"]["dir"]
    batch = int(hp.get("batch_size", 1))

    common = dict(
        output_dir=str(ckpt_dir),
        learning_rate=float(hp["learning_rate"]),
        max_steps=args.iters,
        lr_scheduler_type="constant",
        logging_steps=1,
        save_strategy="steps",
        save_steps=args.save_every,
        save_only_model=True,
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        model_init_kwargs={"dtype": "bfloat16"},
        seed=7,
        report_to=[],
        disable_tqdm=True,
    )

    if cfg["mode"] == "sft":
        from transformers import AutoTokenizer
        from trl import SFTConfig, SFTTrainer
        tok = AutoTokenizer.from_pretrained(args.base)
        targs = SFTConfig(
            **common,
            per_device_train_batch_size=batch,
            per_device_eval_batch_size=batch,
            max_length=int(hp.get("max_seq_length", 768)),
            completion_only_loss=True,
            eval_strategy="steps",
            eval_steps=max(args.save_every, 100),
        )
        trainer = SFTTrainer(
            model=args.base, args=targs, processing_class=tok,
            train_dataset=sft_split(data_dir, tok, "train"),
            eval_dataset=sft_split(data_dir, tok, "valid"))
    else:
        from trl import GRPOConfig, GRPOTrainer
        group = int(hp.get("group_size", 6))
        max_completion = int(hp.get("max_completion_length", 200))
        targs = GRPOConfig(
            **common,
            # TRL counts completions, not prompts: batch_size prompts/step
            per_device_train_batch_size=batch * group,
            num_generations=group,
            max_prompt_length=int(hp.get("max_seq_length", 768)) - max_completion,
            max_completion_length=max_completion,
            temperature=float(hp.get("temperature", 0.8)),
            beta=float(hp.get("beta", 0.1)),
            use_vllm=bool(hp.get("use_vllm", True)),
            vllm_mode="colocate",
            vllm_gpu_memory_utilization=float(
                hp.get("vllm_gpu_memory_utilization", 0.25)),
        )
        trainer = GRPOTrainer(
            model=args.base, args=targs,
            reward_funcs=lean_sanskrit_reward,
            train_dataset=grpo_dataset(data_dir),
            peft_config=lora_config(args.base, hp))

    trainer.train()
    trainer.save_model(str(ckpt_dir / "final"))


if __name__ == "__main__":
    main()
