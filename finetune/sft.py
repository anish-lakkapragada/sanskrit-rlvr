"""LoRA SFT on a distilled trace corpus (cold-start stage before GRPO).

Preflight (CPU-only, no GPU deps):
    uv run python -m finetune.sft --config configs/sft-qwen3-4b.yml --dry-run

Training (Lambda box, 1x A100):
    uv run python -m finetune.sft --config configs/sft-qwen3-4b.yml [--merge]

Hyperparameter defaults follow LoRA-Without-Regret / TRL guidance (all-linear
targets, lr ~10x full-FT with cosine schedule, effective batch < 32,
completion-only loss); see finetune.config.SFTSettings.

Run artifacts land in runs/<run_name>/:
    config.yml (frozen + _resolved), tensorboard/, evals/step-<N>/,
    checkpoints/checkpoint-<N>/, adapter/ (final LoRA), merged/ (--merge)
"""

import argparse
import json
import math
import random
from pathlib import Path

from finetune import evals, rewards
from finetune.callbacks import make_checkpoint_eval_callback
from finetune.config import RunConfig, load_config
from finetune.data import load_sft_dataset, load_vp_tasks
from finetune.grpo import is_main_process, setup_run_dir
from finetune.model import resolve_model_id

_SENTINEL = "\x00sft-sentinel\x00"


def build_text_pairs(tokenizer, records) -> list[dict]:
    """Distillation records -> {"prompt", "completion"} STRING pairs.

    Rendering is done here (not by TRL) so ``enable_thinking=False`` is pinned
    deterministically: Qwen3's template must not open its native think channel,
    because eval-time generation conditions on exactly this prefix. The
    completion is the assistant content plus whatever the template emits after
    assistant content (e.g. ``<|im_end|>``), probed via a sentinel render --
    correct by construction even when the template injects an empty
    ``<think>`` block into the generation prompt.
    """
    probe = tokenizer.apply_chat_template(
        [{"role": "user", "content": "x"},
         {"role": "assistant", "content": _SENTINEL}],
        tokenize=False, enable_thinking=False)
    suffix = probe.split(_SENTINEL, 1)[1]

    pairs = []
    for r in records:
        prefix = tokenizer.apply_chat_template(
            r["prompt"], tokenize=False, add_generation_prompt=True,
            enable_thinking=False)
        pairs.append({"prompt": prefix,
                      "completion": r["completion"][0]["content"] + suffix})
    return pairs


def filter_overlong(tokenizer, pairs: list[dict], max_seq_len: int):
    """Drop pairs that exceed max_seq_len instead of letting the trainer
    truncate them: the answer tag sits at the END of the completion, so a
    truncated target would teach the model to run past its budget."""
    kept, dropped = [], 0
    for p in pairs:
        n = len(tokenizer(p["prompt"] + p["completion"])["input_ids"])
        if n <= max_seq_len:
            kept.append(p)
        else:
            dropped += 1
    return kept, dropped


def make_hf_generate_fn(trainer, tokenizer):
    """generate_fn(prompts, n, temperature, max_new_tokens) -> list[list[str]]
    over HF generate; renders with the SAME enable_thinking=False prefix the
    training pairs use."""
    import torch

    def generate_fn(prompts, n, temperature, max_new_tokens):
        model = trainer.model
        model.eval()
        results = []
        with torch.no_grad():
            for prompt in prompts:
                text = tokenizer.apply_chat_template(
                    [{"role": "user", "content": prompt}],
                    tokenize=False, add_generation_prompt=True,
                    enable_thinking=False)
                inputs = tokenizer(text, return_tensors="pt").to(model.device)
                gen = model.generate(
                    **inputs,
                    do_sample=temperature > 0,
                    temperature=max(temperature, 1e-6),
                    max_new_tokens=max_new_tokens,
                    num_return_sequences=n,
                    pad_token_id=tokenizer.eos_token_id,
                )
                plen = inputs["input_ids"].shape[1]
                results.append([
                    tokenizer.decode(seq[plen:], skip_special_tokens=True)
                    for seq in gen
                ])
        model.train()
        return results

    return generate_fn


def make_eval_suite(cfg: RunConfig, generate_fn, writer, run_dir: Path):
    """Small pass@k probe on held-out dhatus, run at every checkpoint save.
    Uses the SFT corpus's prompt template (v1), not the v0 GRPO default."""
    vp_tasks = load_vp_tasks(cfg.eval_dataset)
    reward_fn = rewards.get(cfg.reward)
    s = cfg.sft
    ks = sorted({1, s.eval_samples_per_prompt})

    def eval_suite(step: int) -> None:
        rng = random.Random(cfg.seed)  # fixed subset: keeps checkpoints comparable
        metrics, samples = evals.eval_pass_at_k(
            generate_fn, vp_tasks, reward_fn, ks=ks,
            samples_per_prompt=s.eval_samples_per_prompt,
            pass_threshold=cfg.pass_at_k.pass_threshold,
            temperature=cfg.pass_at_k.temperature,
            max_new_tokens=s.eval_max_new_tokens,
            num_prompts=s.eval_prompts_per_epoch,
            rng=rng, template=s.prompt_template)
        out = run_dir / "evals" / f"step-{step:07d}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "pass_at_k.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=1))
        with (out / "samples.jsonl").open("w") as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        for k in ks:
            writer.add_scalar(f"eval/pass_at_{k}", metrics[f"pass_at_{k}"], step)
        writer.add_scalar("eval/answer_tag_rate", metrics["answer_tag_rate"], step)
        writer.flush()
        print(f"[eval step {step}] "
              f"pass@k={ {k: round(metrics[f'pass_at_{k}'], 4) for k in ks} } "
              f"tag_rate={metrics['answer_tag_rate']:.2f}")

    return eval_suite


def dry_run(cfg: RunConfig, run_dir: Path) -> None:
    from finetune.config import ROOT

    records = json.loads((ROOT / cfg.sft.dataset).read_text())
    assert records, f"empty SFT corpus: {cfg.sft.dataset}"
    for r in records[:100]:
        assert r["prompt"][0]["role"] == "user" and r["completion"][0]["role"] == "assistant"
    eff_batch = cfg.sft.per_device_train_batch_size * cfg.sft.gradient_accumulation_steps
    if cfg.sft.max_steps:
        steps = cfg.sft.max_steps
        epochs_equiv = steps * eff_batch / len(records)
        print(f"[dry-run] FIXED BUDGET {steps} steps = {epochs_equiv:.2f} epochs "
              f"over this corpus ({steps * eff_batch} examples seen)")
    else:
        steps = math.ceil(len(records) / eff_batch * cfg.sft.epochs)
    for name, path in (cfg.sft.val_datasets or {}).items():
        n_val = len(json.loads((ROOT / path).read_text()))
        print(f"[dry-run] val '{name}': {n_val} pairs, every {cfg.sft.eval_every} steps")
    print(f"[dry-run] corpus {cfg.sft.dataset}: {len(records)} records")
    print(f"[dry-run] model {resolve_model_id(cfg.model)}  lora r={cfg.train.lora.r} "
          f"alpha={cfg.train.lora.alpha} dropout={cfg.train.lora.dropout}")
    print(f"[dry-run] lr={cfg.sft.learning_rate} ({cfg.sft.lr_scheduler}, "
          f"warmup {cfg.sft.warmup_ratio:.0%})  effective_batch={eff_batch}  "
          f"epochs={cfg.sft.epochs} (~{steps} optimizer steps)")

    try:
        from transformers import AutoTokenizer
    except ImportError:
        print("[dry-run] transformers not installed here -- skipping chat-template "
              "render preview (runs on the training box)")
        return
    tokenizer = AutoTokenizer.from_pretrained(resolve_model_id(cfg.model))
    pairs = build_text_pairs(tokenizer, records[:1])
    p = pairs[0]
    n_prompt = len(tokenizer(p["prompt"])["input_ids"])
    n_total = len(tokenizer(p["prompt"] + p["completion"])["input_ids"])
    assert n_total > n_prompt, "completion contributes no tokens"
    print(f"[dry-run] rendered example: {n_prompt} prompt tokens (loss-masked) + "
          f"{n_total - n_prompt} completion tokens (loss) <= {cfg.sft.max_seq_len}")
    print("[dry-run] prompt tail:  ..." + repr(p["prompt"][-80:]))
    print("[dry-run] completion:   " + repr(p["completion"][:120]) + " ...")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="validate config + corpus (and render preview if "
                             "transformers is installed), no GPU")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing runs/<run_name>/")
    parser.add_argument("--merge", action="store_true",
                        help="after training, merge the adapter into the base "
                             "model at runs/<run_name>/merged/")
    args = parser.parse_args()

    cfg = load_config(args.config)
    from finetune.config import ROOT

    if not (ROOT / cfg.sft.dataset).exists():
        raise SystemExit(f"SFT corpus not found: {cfg.sft.dataset} "
                         "(generate it with misc/data/generate_sft_data.py)")
    run_dir = setup_run_dir(cfg, args.config, args.force)

    if args.dry_run:
        dry_run(cfg, run_dir)
        print(f"[dry-run] run dir scaffolded at {run_dir}")
        return

    # ---------------- GPU path ----------------
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    from finetune.model import build_peft_config, load_model, load_tokenizer

    tokenizer = load_tokenizer(cfg)
    model = load_model(cfg)

    records = load_sft_dataset(cfg.sft.dataset)
    pairs = build_text_pairs(tokenizer, records)
    pairs, dropped = filter_overlong(tokenizer, pairs, cfg.sft.max_seq_len)
    if dropped:
        print(f"[setup] dropped {dropped} over-length pairs "
              f"(> {cfg.sft.max_seq_len} tokens); {len(pairs)} remain")
    train_dataset = Dataset.from_list(pairs)

    # Held-out validation, one dataset per task: HF logs eval_<name>_loss for each,
    # so a mixed run shows both capabilities' curves separately and convergence can
    # be read off rather than assumed. Same completion-only masking as training.
    eval_dataset = None
    if cfg.sft.val_datasets and cfg.sft.eval_every > 0:
        eval_dataset = {}
        for name, path in cfg.sft.val_datasets.items():
            vp = build_text_pairs(tokenizer, load_sft_dataset(path))
            vp, vdropped = filter_overlong(tokenizer, vp, cfg.sft.max_seq_len)
            eval_dataset[name] = Dataset.from_list(vp)
            print(f"[setup] val '{name}': {len(vp)} pairs from {path}"
                  + (f" ({vdropped} over-length dropped)" if vdropped else ""))

    sft_args = SFTConfig(
        output_dir=str(run_dir / "checkpoints"),
        num_train_epochs=cfg.sft.epochs,
        learning_rate=cfg.sft.learning_rate,
        lr_scheduler_type=cfg.sft.lr_scheduler,
        warmup_ratio=cfg.sft.warmup_ratio,
        weight_decay=cfg.sft.weight_decay,
        per_device_train_batch_size=cfg.sft.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.sft.gradient_accumulation_steps,
        bf16=cfg.train.bf16,
        gradient_checkpointing=cfg.train.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_length=cfg.sft.max_seq_len,
        packing=False,
        completion_only_loss=True,   # loss on completion tokens only
        max_steps=cfg.sft.max_steps or -1,   # -1 = honor num_train_epochs instead
        save_strategy="steps" if cfg.sft.save_every else "epoch",
        save_steps=cfg.sft.save_every or 500,
        eval_strategy="steps" if eval_dataset else "no",
        eval_steps=cfg.sft.eval_every or 500,
        logging_steps=cfg.logging_every,
        logging_dir=str(run_dir / "tensorboard"),
        report_to=["tensorboard"],
        seed=cfg.seed,
    )
    trainer = SFTTrainer(
        model=model,
        args=sft_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        peft_config=build_peft_config(cfg, model),
        processing_class=tokenizer,
    )

    from tensorboardX import SummaryWriter

    writer = SummaryWriter(str(run_dir / "tensorboard")) if is_main_process() else None
    if is_main_process() and cfg.sft.eval_prompts_per_epoch > 0:
        eval_suite = make_eval_suite(
            cfg, make_hf_generate_fn(trainer, tokenizer), writer, run_dir)
        eval_suite(0)  # step 0 = base model
        trainer.add_callback(make_checkpoint_eval_callback(eval_suite))

    trainer.train()

    if is_main_process():
        trainer.save_model(str(run_dir / "adapter"))
        tokenizer.save_pretrained(str(run_dir / "adapter"))
        print(f"[done] adapter saved to {run_dir / 'adapter'}")
        if args.merge:
            merged = trainer.model.merge_and_unload()
            merged.save_pretrained(str(run_dir / "merged"))
            tokenizer.save_pretrained(str(run_dir / "merged"))
            print(f"[done] merged model saved to {run_dir / 'merged'}")
    if writer:
        writer.close()


if __name__ == "__main__":
    main()
