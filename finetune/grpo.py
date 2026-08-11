"""GRPO fine-tuning entry point.

Preflight (CPU-only, no GPU deps):
    uv run python -m finetune.grpo --config configs/example.yml --dry-run

Training (Lambda box, 8x H100 example):
    accelerate launch --num_processes 8 -m finetune.grpo --config configs/example.yml

Run artifacts land in runs/<run_name>/ (see README of the plan):
    config.yml, tensorboard/, reward_history.jsonl,
    checkpoints/checkpoint-<N>/, evals/step-<N>/
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

import yaml

from finetune import evals, rewards
from finetune.callbacks import RewardHistoryRecorder, make_checkpoint_eval_callback
from finetune.config import ROOT, RunConfig, load_config
from finetune.data import load_samayik_pairs, load_vp_dataset, load_vp_tasks
from finetune.model import resolve_model_id
from finetune.prompts import PROMPT_VERSION, render_vp_task


def is_main_process() -> bool:
    return int(os.environ.get("RANK", 0)) == 0


def _git_sha() -> str | None:
    import subprocess

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def setup_run_dir(cfg: RunConfig, config_path: str, force: bool) -> Path:
    run_dir = cfg.run_dir
    if run_dir.exists():
        if not force:
            sys.exit(f"run dir already exists: {run_dir} (pass --force to overwrite)")
        if is_main_process():
            import shutil

            shutil.rmtree(run_dir)
    if is_main_process():
        (run_dir / "evals").mkdir(parents=True, exist_ok=True)
        (run_dir / "tensorboard").mkdir(exist_ok=True)
        frozen = yaml.safe_load(Path(config_path).read_text())
        frozen["_resolved"] = {
            "model_id": resolve_model_id(cfg.model),
            "prompt_version": PROMPT_VERSION,
            "git_sha": _git_sha(),
            "argv": sys.argv,
        }
        (run_dir / "config.yml").write_text(
            yaml.safe_dump(frozen, sort_keys=False, allow_unicode=True))
    return run_dir


def make_eval_suite(cfg: RunConfig, generate_fn, writer, run_dir: Path):
    """Returns eval_suite(step): runs Pass@K + Samayik chrF, writes
    runs/<run>/evals/step-<N>/ and TensorBoard scalars."""
    vp_tasks = load_vp_tasks(cfg.eval_dataset)
    samayik = load_samayik_pairs(cfg.samayik_eval.path)
    reward_fn = rewards.get(cfg.reward)  # unwrapped: eval rewards stay out of training history

    def eval_suite(step: int) -> None:
        out = run_dir / "evals" / f"step-{step:07d}"
        out.mkdir(parents=True, exist_ok=True)
        # Seed must NOT depend on step: it selects WHICH prompts are evaluated,
        # so varying it re-rolls the subset every checkpoint and makes
        # checkpoints incomparable. At 1-2% pass rates the subset dominates the
        # measurement -- an early run swung pass@1 0.29% -> 2.15% -> 0.10% ->
        # 1.46% on nothing but redrawn prompts. Sampling diversity comes from
        # the generation temperature, not from here.
        rng = random.Random(cfg.seed)

        pk_metrics, pk_samples = evals.eval_pass_at_k(
            generate_fn, vp_tasks, reward_fn,
            ks=cfg.pass_at_k.ks,
            samples_per_prompt=cfg.pass_at_k.samples_per_prompt,
            pass_threshold=cfg.pass_at_k.pass_threshold,
            temperature=cfg.pass_at_k.temperature,
            max_new_tokens=cfg.generation.max_completion_length,
            num_prompts=cfg.pass_at_k.num_prompts,
            rng=rng,
            template=cfg.prompt_template,
        )
        sm_metrics, sm_samples = evals.eval_samayik(
            generate_fn, samayik,
            num_samples=cfg.samayik_eval.num_samples,
            temperature=cfg.samayik_eval.temperature,
            max_new_tokens=cfg.samayik_eval.max_new_tokens,
            rng=rng,
        )

        (out / "pass_at_k.json").write_text(
            json.dumps(pk_metrics, ensure_ascii=False, indent=1))
        (out / "samayik.json").write_text(
            json.dumps(sm_metrics, ensure_ascii=False, indent=1))
        with (out / "samples.jsonl").open("w") as f:
            for s in pk_samples:
                f.write(json.dumps({"kind": "vp", **s}, ensure_ascii=False) + "\n")
            for s in sm_samples:
                f.write(json.dumps({"kind": "samayik", **s}, ensure_ascii=False) + "\n")

        for k in cfg.pass_at_k.ks:
            writer.add_scalar(f"eval/pass_at_{k}", pk_metrics[f"pass_at_{k}"], step)
        writer.add_scalar("eval/answer_tag_rate", pk_metrics["answer_tag_rate"], step)
        writer.add_scalar("eval/samayik_chrf", sm_metrics["chrf"], step)
        writer.add_scalar("eval/samayik_chrfpp", sm_metrics["chrf_pp"], step)
        writer.add_scalar("eval/translation_tag_rate",
                          sm_metrics["translation_tag_rate"], step)
        snap = pk_metrics["reward_snapshot"]
        if snap["mean"] is not None:
            writer.add_scalar("eval/reward_mean", snap["mean"], step)
        writer.flush()
        print(f"[eval step {step}] pass@k={ {k: round(pk_metrics[f'pass_at_{k}'], 4) for k in cfg.pass_at_k.ks} } "
              f"chrf={sm_metrics['chrf']:.2f} chrf++={sm_metrics['chrf_pp']:.2f}")

    return eval_suite


def make_generate_fn(trainer, tokenizer, cfg: RunConfig):
    """generate_fn(prompts, n, temperature, max_new_tokens) -> list[list[str]].

    Prefers the trainer's colocated vLLM engine (kept weight-synced by TRL);
    falls back to HF model.generate (e.g. server mode)."""

    def chat(prompt: str) -> str:
        # enable_thinking=False: keep Qwen3's native think channel out of
        # evals, matching SFT/prevals rendering (ignored by other templates).
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False)

    def generate_fn(prompts, n, temperature, max_new_tokens):
        texts = [chat(p) for p in prompts]
        # trl <1.0 kept the colocated engine at trainer.llm; trl >=1.0 moved it
        # into the VLLMGeneration helper.
        engine = getattr(trainer, "llm", None)
        if engine is None:
            engine = getattr(getattr(trainer, "vllm_generation", None), "llm", None)
        if engine is not None:
            from vllm import SamplingParams

            params = SamplingParams(
                n=n,
                temperature=max(temperature, 1e-6),
                max_tokens=max_new_tokens,
            )
            outs = engine.generate(texts, params, use_tqdm=False)
            return [[o.text for o in out.outputs] for out in outs]

        # Server mode: there is no local engine, only an HTTP client to the
        # vllm-serve process. It returns token ids grouped n-per-prompt, so
        # decode and regroup. Without this the eval suite would silently fall
        # through to HF generate against a possibly-sharded model.
        client = getattr(getattr(trainer, "vllm_generation", None),
                         "vllm_client", None)
        if client is not None:
            out = client.generate(
                prompts=texts,
                n=n,
                temperature=max(temperature, 1e-6),
                max_tokens=max_new_tokens,
            )
            flat = [tokenizer.decode(ids, skip_special_tokens=True)
                    for ids in out["completion_ids"]]
            if len(flat) != len(texts) * n:
                raise RuntimeError(
                    f"vLLM server returned {len(flat)} completions, "
                    f"expected {len(texts)} prompts x {n}")
            return [flat[i * n:(i + 1) * n] for i in range(len(texts))]

        # HF fallback (batched, sampled)
        import torch

        model = trainer.model
        model.eval()
        results = []
        with torch.no_grad():
            for text in texts:
                inputs = tokenizer(text, return_tensors="pt").to(model.device)
                gen = model.generate(
                    **inputs,
                    do_sample=temperature > 0,
                    temperature=max(temperature, 1e-6),
                    max_new_tokens=max_new_tokens,
                    num_return_sequences=n,
                    pad_token_id=tokenizer.eos_token_id,
                )
                prompt_len = inputs["input_ids"].shape[1]
                results.append([
                    tokenizer.decode(seq[prompt_len:], skip_special_tokens=True)
                    for seq in gen
                ])
        model.train()
        return results

    return generate_fn


def restrict_sync_to_language_model(trainer) -> int:
    """Send only language-model weights to vLLM on multimodal checkpoints.

    transformers-5 and vllm<=0.25.1 disagree on the non-text parameter names:
    gemma3's tower is ``model.vision_tower.embeddings.*`` in transformers but
    ``vision_tower.vision_model.embeddings.*`` in vLLM, and gemma4 adds an
    audio tower plus a separate ``model.embed_vision``. Those towers are
    frozen (LoRA targets the language model only) and unused for text-only
    rollouts, so vLLM's copy from disk stays authoritative. Returns the number
    of parameters excluded, or 0 when the model is text-only."""
    gen = getattr(trainer, "vllm_generation", None)
    push = getattr(gen, "_push_param_to_vllm", None)
    if push is None:
        return 0
    names = [n for n, _ in trainer.model.named_parameters()]
    if not any("vision_tower" in n or "audio_tower" in n for n in names):
        return 0

    def is_language(name: str) -> bool:
        return "language_model" in name or "lm_head" in name

    def filtered(name, param):
        return push(name, param) if is_language(name) else None

    gen._push_param_to_vllm = filtered
    return sum(1 for n in names if not is_language(n))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="validate config/registry/prompts/data + scaffold "
                             "the run dir, without any GPU dependency")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing runs/<run_name>/")
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_dir = setup_run_dir(cfg, args.config, args.force)

    from tensorboardX import SummaryWriter

    writer = SummaryWriter(str(run_dir / "tensorboard")) if is_main_process() else None
    if writer:
        writer.add_text("run/config", f"```\n{(run_dir / 'config.yml').read_text()}\n```", 0)

    reward_fn = rewards.get(cfg.reward)
    recorder = RewardHistoryRecorder(reward_fn, run_dir, writer)

    if args.dry_run:
        tasks = load_vp_tasks(cfg.dataset)
        eval_tasks = load_vp_tasks(cfg.eval_dataset)
        samayik = load_samayik_pairs(cfg.samayik_eval.path)
        sample_prompt = render_vp_task(tasks[0], template=cfg.prompt_template)
        dummy_rewards = recorder([sample_prompt] * 2, ["<answer>x</answer>", "y"],
                                 id=[tasks[0]["id"]] * 2,
                                 dhatu=[tasks[0]["dhatu"]] * 2,
                                 morphology=[tasks[0]["morphology"]] * 2,
                                 gold_slp1=[tasks[0]["gold_slp1"]] * 2,
                                 gold_devanagari=[tasks[0]["gold_devanagari"]] * 2)
        assert len(dummy_rewards) == 2
        if writer:
            writer.flush()
        print(f"[dry-run] config OK: run={cfg.run_name} model={resolve_model_id(cfg.model)} "
              f"reward={cfg.reward} (registry: {rewards.names()})")
        print(f"[dry-run] datasets: train={len(tasks)} pass@k-pool={len(eval_tasks)} "
              f"samayik={len(samayik)}")
        print(f"[dry-run] run dir scaffolded at {run_dir}")
        print("[dry-run] sample prompt:\n" + "-" * 60 + f"\n{sample_prompt}\n" + "-" * 60)
        return

    # ---------------- GPU path ----------------
    from trl import GRPOConfig, GRPOTrainer

    from finetune.model import build_peft_config, load_model, load_tokenizer

    tokenizer = load_tokenizer(cfg)
    model = load_model(cfg)
    train_dataset = load_vp_dataset(cfg.dataset, template=cfg.prompt_template,
                                    tokenizer=tokenizer)

    grpo_args = GRPOConfig(
        output_dir=str(run_dir / "checkpoints"),
        max_steps=cfg.iterations,
        save_strategy="steps",
        save_steps=cfg.checkpoint_every,
        logging_steps=cfg.logging_every,
        logging_dir=str(run_dir / "tensorboard"),
        report_to=["tensorboard"],
        per_device_train_batch_size=cfg.train.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.train.gradient_accumulation_steps,
        learning_rate=cfg.train.learning_rate,
        beta=cfg.train.beta,
        bf16=cfg.train.bf16,
        gradient_checkpointing=cfg.train.gradient_checkpointing,
        num_generations=cfg.generation.num_generations,
        max_completion_length=cfg.generation.max_completion_length,
        temperature=cfg.generation.temperature,
        use_vllm=True,
        vllm_mode=cfg.vllm.mode,
        vllm_gpu_memory_utilization=cfg.vllm.gpu_memory_utilization,
        vllm_max_model_length=cfg.vllm.max_model_length,
        vllm_server_host=cfg.vllm.server_host,
        vllm_server_port=cfg.vllm.server_port,
        remove_unused_columns=False,
        seed=cfg.seed,
    )
    trainer = GRPOTrainer(
        model=model,
        args=grpo_args,
        train_dataset=train_dataset,
        reward_funcs=recorder,
        peft_config=build_peft_config(cfg, model),
        processing_class=tokenizer,
    )
    skipped = restrict_sync_to_language_model(trainer)
    if skipped:
        print(f"[setup] vLLM sync restricted to the language model "
              f"({skipped} tower params excluded)")

    generate_fn = make_generate_fn(trainer, tokenizer, cfg)
    if is_main_process():
        eval_suite = make_eval_suite(cfg, generate_fn, writer, run_dir)
        eval_suite(0)  # checkpoint 0 = base model
        trainer.add_callback(make_checkpoint_eval_callback(eval_suite))

    trainer.train()

    if is_main_process() and cfg.iterations % cfg.checkpoint_every != 0:
        eval_suite(cfg.iterations)
    if writer:
        writer.close()


if __name__ == "__main__":
    main()
