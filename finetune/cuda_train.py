"""The CUDA trainer: TRL on Lambda-class GPUs. bf16 everywhere, no quantization.

    mode: sft  -> full-parameter fine-tune (TRL SFTTrainer)
    mode: grpo -> LoRA + GRPO, rollouts via colocated vLLM (TRL GRPOTrainer);
                  the KL reference is the base with adapters disabled, i.e.
                  exactly the model this run initialized from — no fused copy,
                  no requantization

Invoked by finetune.train as a subprocess (the same shape as the mlx
backend's mlx_lm_lora.train CLI); reads the run's frozen config.yaml.

Telemetry: every `eval.every` iterations the trainer saves a checkpoint AND
judges the live model on every configured benchmark (in-fragment: Lean
compile-rate / chrF++ / TER; out-of-fragment: chrF++ / TER) — appending to
metrics.jsonl, writing a snapshots/checkpoint_<step>/ folder, and mirroring
the scores into TensorBoard (runs/<run_name>/tb) alongside the per-step
training metrics. The final model lands at model.final_checkpoint.
"""

import argparse
import json
from pathlib import Path

import yaml

from .common import ROOT, eval_point, read_jsonl, record_eval_point
from .reward import chrf_reward_from_answer_field, reward_from_answer_field


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


def chrf_format_reward(prompts, completions, answer, **kwargs):
    """The non-verified control: same shape, chrF++ instead of the compiler."""
    texts = [c[0]["content"] if isinstance(c, list) else c for c in completions]
    return [chrf_reward_from_answer_field(spec, text)
            for text, spec in zip(texts, answer)]


# hyperparameters.reward selects the GRPO training signal
REWARDS = {"lean": lean_sanskrit_reward, "chrf": chrf_format_reward}


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


def load_benchmarks(cfg: dict) -> dict:
    ev = cfg["eval"]
    groups = ev.get("benchmarks") or {"in_fragment": ev["prompts"]}
    benchmarks = {}
    for group, rel in groups.items():
        rows = read_jsonl(ROOT / rel)
        if ev.get("samples"):
            rows = rows[: int(ev["samples"])]
        benchmarks[group] = rows
    return benchmarks


def make_eval_callback(run_dir: Path, benchmarks: dict, temp: float):
    """A TrainerCallback that judges the LIVE training model (SFT: the full
    model; GRPO: base + current adapter) at step 0 and at every checkpoint
    save, then mirrors the scores into TensorBoard via trainer.log."""
    from transformers import TrainerCallback

    from .cuda_eval import _generate_all

    class EvalCallback(TrainerCallback):
        trainer = None  # set after the trainer is constructed
        _last_evaled = None

        def _eval(self, step: int, kind: str):
            import torch
            model, tok = self.trainer.model, self.trainer.processing_class
            was_training, padding_side = model.training, tok.padding_side
            model.eval()
            with torch.no_grad():
                results = eval_point(
                    benchmarks,
                    lambda rows: _generate_all(model, tok, rows, temp))
            tok.padding_side = padding_side
            if was_training:
                model.train()
            row = record_eval_point(run_dir, step, kind, results)
            scalars = {f"eval/{group}/{k}": v
                       for group, (summary, _) in results.items()
                       for k, v in summary.items()
                       if isinstance(v, (int, float))}
            self.trainer.log(scalars)
            self._last_evaled = step
            print(f"[eval] step {step}: " + json.dumps(
                {g: row[g] for g in results}, ensure_ascii=False), flush=True)

        def on_train_begin(self, args, state, control, **kwargs):
            self._eval(0, "init")

        def on_save(self, args, state, control, **kwargs):
            # checkpoints/<iteration>/ instead of HF's checkpoint-<iteration>
            # (safe: no rotation, no resume — nothing else reads the name)
            step = state.global_step
            hf_dir = Path(args.output_dir) / f"checkpoint-{step}"
            if hf_dir.exists():
                hf_dir.rename(Path(args.output_dir) / str(step))
            self._eval(step, "checkpoint")

        def on_train_end(self, args, state, control, **kwargs):
            # covers iters not divisible by the save cadence
            if state.global_step != self._last_evaled:
                self._eval(state.global_step, "checkpoint")

    return EvalCallback()


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
    run_dir = args.config.parent
    ckpt_dir = run_dir / "checkpoints"
    data_dir = ROOT / cfg["data"]["dir"]
    batch = int(hp.get("batch_size", 1))

    common = dict(
        output_dir=str(ckpt_dir),
        learning_rate=float(hp["learning_rate"]),
        max_steps=args.iters,
        lr_scheduler_type="constant",
        logging_steps=1,
        logging_dir=str(run_dir / "tb"),
        report_to=["tensorboard"],
        save_strategy="steps",
        save_steps=args.save_every,
        save_only_model=True,
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        model_init_kwargs={"dtype": "bfloat16"},
        seed=7,
        disable_tqdm=True,
    )

    if cfg["mode"] == "sft":
        from transformers import AutoTokenizer
        from trl import SFTConfig, SFTTrainer
        tok = AutoTokenizer.from_pretrained(args.base)
        targs = SFTConfig(
            **common,
            per_device_train_batch_size=batch,
            max_length=int(hp.get("max_seq_length", 768)),
            completion_only_loss=True,
        )
        trainer = SFTTrainer(
            model=args.base, args=targs, processing_class=tok,
            train_dataset=sft_split(data_dir, tok, "train"))
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
        reward_name = hp.get("reward", "lean")
        if reward_name not in REWARDS:
            raise SystemExit(f"hyperparameters.reward must be one of "
                             f"{sorted(REWARDS)} (got {reward_name!r})")
        trainer = GRPOTrainer(
            model=args.base, args=targs,
            reward_funcs=REWARDS[reward_name],
            train_dataset=grpo_dataset(data_dir),
            peft_config=lora_config(args.base, hp))

    cb = make_eval_callback(run_dir, load_benchmarks(cfg),
                            float(cfg["eval"].get("temperature", 0)))
    cb.trainer = trainer
    trainer.add_callback(cb)

    trainer.train()

    final = Path(cfg["model"].get("final_checkpoint") or ckpt_dir / "final")
    if not final.is_absolute():
        final = ROOT / final
    trainer.save_model(str(final))
    print(f"[final] model saved to {final}", flush=True)


if __name__ == "__main__":
    main()
