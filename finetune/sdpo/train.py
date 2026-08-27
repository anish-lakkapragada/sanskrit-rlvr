"""SDPO fine-tuning entry point (pure self-distillation, no GRPO term).

Preflight (CPU-only, needs transformers for the tokenizer):
    uv run --with transformers python -m finetune.sdpo --config configs/sdpo-upsample-2.yml --dry-run

Training (single GPU):
    python -m finetune.sdpo --config configs/sdpo-upsample-2.yml --force

Artifacts land in runs/<run_name>/ exactly like GRPO runs:
    config.yml, tensorboard/, sdpo_history.jsonl,
    checkpoints/checkpoint-<N>/ (adapter), evals/step-<N>/

The probe suite is finetune.grpo.make_eval_suite — identical protocol and
TensorBoard tags to the GRPO runs, so pass@1 curves overlay directly.
"""

import argparse
import json
import random
import statistics
import time

from finetune import rewards
from finetune.config import load_config
from finetune.grpo import is_main_process, make_eval_suite, setup_run_dir
from finetune.model import build_peft_config, load_model, load_tokenizer, resolve_model_id
from finetune.sdpo.data import (
    chat_wrap, completion_token_weights, load_sdpo_tasks, render_pair,
)

REWARD_COLS = ("id", "dhatu", "morphology", "gold_slp1", "gold_devanagari")


def _task_cols(task: dict, n: int) -> dict:
    return {k: [task[k]] * n for k in REWARD_COLS}


def dry_run(cfg, run_dir) -> None:
    from pathlib import Path

    from transformers import AutoTokenizer

    model_id = resolve_model_id(cfg.model)
    if model_id.startswith("/") and not Path(model_id).exists():
        # Box-local merged dir not present on this machine; its tokenizer is
        # byte-identical to the hub base (verified 2026-08-20).
        print(f"[dry-run] {model_id} not present locally -> tokenizer from Qwen/Qwen3-4B")
        model_id = "Qwen/Qwen3-4B"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tasks = load_sdpo_tasks(cfg.dataset)
    pair = render_pair(tasks[0], cfg.prompt_template, tokenizer)
    demo = "<thinking>\nभू + तिप् → भवति\n</thinking>\n\n<answer>भवति</answer>"
    ids, weights = completion_token_weights(
        tokenizer, demo, cfg.sdpo.thinking_block_weight, cfg.sdpo.answer_block_weight)
    n_ans = sum(1 for w in weights if w == cfg.sdpo.answer_block_weight)
    blocks = [t["block_tokens"] for t in tasks]
    blocks.sort()
    print(f"[dry-run] config OK: run={cfg.run_name} model={resolve_model_id(cfg.model)}")
    print(f"[dry-run] sdpo tasks: {len(tasks)} (privileged blocks p50="
          f"{blocks[len(blocks)//2]} max={blocks[-1]} tokens, budget "
          f"{cfg.sdpo.privileged_budget}; over-budget tasks were excluded at build)")
    print(f"[dry-run] weight-mask demo: {len(ids)} completion tokens, "
          f"{len(ids) - n_ans} thinking-weighted ({cfg.sdpo.thinking_block_weight}) + "
          f"{n_ans} answer-weighted ({cfg.sdpo.answer_block_weight}); "
          "prompt tokens carry NO loss by construction (scored region = completion only)")
    print("[dry-run] STUDENT prompt x:\n" + "-" * 60 + f"\n{pair['student_text']}\n" + "-" * 60)
    print("[dry-run] TEACHER prompt x+ (tail incl. privileged block):\n" + "-" * 60
          + f"\n...{pair['teacher_text'][-900:]}\n" + "-" * 60)
    print(f"[dry-run] run dir scaffolded at {run_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_dir = setup_run_dir(cfg, args.config, args.force)

    if args.dry_run:
        dry_run(cfg, run_dir)
        return

    # ---------------- GPU path ----------------
    import torch
    from peft import get_peft_model
    from tensorboardX import SummaryWriter
    from transformers import get_scheduler

    from finetune.sdpo.engine import build_engine, generate, push_policy_weights
    from finetune.sdpo.loss import sdpo_kl

    writer = SummaryWriter(str(run_dir / "tensorboard")) if is_main_process() else None
    if writer:
        writer.add_text("run/config", f"```\n{(run_dir / 'config.yml').read_text()}\n```", 0)

    tokenizer = load_tokenizer(cfg)
    model = load_model(cfg)
    peft_model = get_peft_model(model, build_peft_config(cfg, model))
    peft_model.print_trainable_parameters()
    if cfg.train.gradient_checkpointing:
        peft_model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False})
        peft_model.enable_input_require_grads()
    peft_model.config.use_cache = False
    device = torch.device("cuda")
    peft_model.to(device).train()

    trainable = [p for p in peft_model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=cfg.train.learning_rate,
                                  weight_decay=cfg.sdpo.weight_decay)
    scheduler = get_scheduler(
        cfg.sdpo.lr_scheduler, optimizer,
        num_warmup_steps=int(cfg.sdpo.warmup_ratio * cfg.iterations),
        num_training_steps=cfg.iterations)

    engine = build_engine(cfg, resolve_model_id(cfg.model))
    reward_fn = rewards.get(cfg.reward)
    sdpo_cfg = cfg.sdpo

    def generate_fn(prompts, n, temperature, max_new_tokens):
        texts = [chat_wrap(tokenizer, p) for p in prompts]
        return generate(engine, texts, n, temperature, max_new_tokens)

    eval_suite = make_eval_suite(cfg, generate_fn, writer, run_dir)
    push_policy_weights(engine, peft_model)   # LoRA is zero-init: policy == base
    eval_suite(0)

    tasks = load_sdpo_tasks(cfg.dataset)
    rng = random.Random(cfg.seed)
    order = list(range(len(tasks)))
    rng.shuffle(order)
    history = (run_dir / "sdpo_history.jsonl").open("a")

    def score_pass(prompt_text: str, task: dict, comps: list[str]) -> list[bool]:
        rs = reward_fn([prompt_text] * len(comps), comps, **_task_cols(task, len(comps)))
        return [r is not None and r >= sdpo_cfg.gate_threshold for r in rs]

    def forward_logits(ids: list[int], comp_len: int, grad: bool):
        """Distributions predicting each completion token: [comp_len, V]."""
        x = torch.tensor([ids], device=device)
        ctx = torch.enable_grad() if grad else torch.no_grad()
        with ctx:
            out = peft_model(input_ids=x, logits_to_keep=comp_len + 1)
        return out.logits[0, :-1, :]   # drop the post-final-token position

    step_iter = iter(())
    for step in range(1, cfg.iterations + 1):
        t0 = time.time()
        try:
            idx = next(step_iter)
        except StopIteration:
            rng.shuffle(order)
            step_iter = iter(order)
            idx = next(step_iter)
        task = tasks[idx]
        pair = render_pair(task, cfg.prompt_template, tokenizer)

        if (step - 1) % sdpo_cfg.weight_sync_every == 0:
            push_policy_weights(engine, peft_model)

        comps = generate(engine, [pair["student_text"]],
                         cfg.generation.num_generations,
                         cfg.generation.temperature,
                         cfg.generation.max_completion_length)[0]
        passed = score_pass(pair["user_text"], task, comps)
        pass_rate = sum(passed) / len(passed)
        comp_lens = sorted(len(tokenizer(c, add_special_tokens=False)["input_ids"])
                           for c in comps)

        rec = {"step": step, "time": time.time(), "task_id": task["id"],
               "pass_rate": pass_rate, "len_p50": comp_lens[len(comp_lens) // 2],
               "len_max": comp_lens[-1]}

        if sdpo_cfg.skip_all_correct and all(passed):
            scheduler.step()
            rec.update({"skipped": True})
            history.write(json.dumps(rec) + "\n"); history.flush()
            if writer and step % cfg.logging_every == 0:
                writer.add_scalar("sdpo/skipped", 1.0, step)
                writer.add_scalar("train/group_pass_rate", pass_rate, step)
            continue

        # failed-first, capped
        ranked = sorted(range(len(comps)), key=lambda i: passed[i])
        distill = [comps[i] for i in ranked[:sdpo_cfg.max_distill_rollouts]]

        student_prompt_ids = tokenizer(pair["student_text"],
                                       add_special_tokens=False)["input_ids"]
        teacher_prompt_ids = tokenizer(pair["teacher_text"],
                                       add_special_tokens=False)["input_ids"]

        kl_means, kl_thinking, kl_answer, n_used = [], [], [], 0
        optimizer.zero_grad(set_to_none=True)
        for comp in distill:
            comp_ids, weights = completion_token_weights(
                tokenizer, comp, sdpo_cfg.thinking_block_weight,
                sdpo_cfg.answer_block_weight)
            comp_ids = comp_ids[:cfg.generation.max_completion_length]
            weights = weights[:len(comp_ids)]
            if not comp_ids:
                continue
            w = torch.tensor(weights, device=device, dtype=torch.float32)
            teacher_logits = forward_logits(teacher_prompt_ids + comp_ids,
                                            len(comp_ids), grad=False)
            student_logits = forward_logits(student_prompt_ids + comp_ids,
                                            len(comp_ids), grad=True)
            loss, kl_t = sdpo_kl(student_logits, teacher_logits, w,
                                 direction=sdpo_cfg.kl_direction,
                                 temperature=sdpo_cfg.kl_temperature,
                                 chunk=sdpo_cfg.logits_chunk,
                                 clamp=sdpo_cfg.kl_clamp)
            (loss / len(distill)).backward()
            n_used += 1
            think_mask = w == sdpo_cfg.thinking_block_weight
            kl_means.append(kl_t.mean().item())
            if think_mask.any():
                kl_thinking.append(kl_t[think_mask].mean().item())
            if (~think_mask).any():
                kl_answer.append(kl_t[~think_mask].mean().item())
            del teacher_logits, student_logits

        grad_norm = torch.nn.utils.clip_grad_norm_(trainable, sdpo_cfg.grad_clip)
        optimizer.step()
        scheduler.step()

        rec.update({
            "skipped": False, "n_distilled": n_used,
            "kl_mean": statistics.fmean(kl_means) if kl_means else None,
            "kl_thinking": statistics.fmean(kl_thinking) if kl_thinking else None,
            "kl_answer": statistics.fmean(kl_answer) if kl_answer else None,
            "grad_norm": float(grad_norm), "sec": round(time.time() - t0, 2),
        })
        history.write(json.dumps(rec) + "\n"); history.flush()

        if writer and step % cfg.logging_every == 0:
            writer.add_scalar("sdpo/skipped", 0.0, step)
            writer.add_scalar("train/group_pass_rate", pass_rate, step)
            if kl_means:
                writer.add_scalar("sdpo/kl_mean", rec["kl_mean"], step)
            if kl_thinking:
                writer.add_scalar("sdpo/kl_thinking", rec["kl_thinking"], step)
            if kl_answer:
                writer.add_scalar("sdpo/kl_answer", rec["kl_answer"], step)
            writer.add_scalar("sdpo/grad_norm", float(grad_norm), step)
            writer.add_scalar("sdpo/lr", scheduler.get_last_lr()[0], step)
            writer.add_scalar("completions/len_p50", rec["len_p50"], step)
            print(f"[step {step}/{cfg.iterations}] pass_rate={pass_rate:.2f} "
                  f"kl={rec['kl_mean'] if kl_means else float('nan'):.4f} "
                  f"len_p50={rec['len_p50']} {rec['sec']}s")

        if step % cfg.checkpoint_every == 0:
            ckpt = run_dir / "checkpoints" / f"checkpoint-{step}"
            peft_model.save_pretrained(str(ckpt))
            tokenizer.save_pretrained(str(ckpt))
            push_policy_weights(engine, peft_model)
            eval_suite(step)

    if cfg.iterations % cfg.checkpoint_every != 0:
        ckpt = run_dir / "checkpoints" / f"checkpoint-{cfg.iterations}"
        peft_model.save_pretrained(str(ckpt))
        push_policy_weights(engine, peft_model)
        eval_suite(cfg.iterations)
    history.close()
    if writer:
        writer.close()


if __name__ == "__main__":
    main()
