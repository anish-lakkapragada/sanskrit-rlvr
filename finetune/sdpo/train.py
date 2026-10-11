"""SDPO fine-tuning entry point (pure self-distillation, no GRPO term).

Data-parallel over torchrun ranks, GRPO-r3's exact batch shape: each rank
takes ONE prompt per optimizer step and generates the full rollout group, so
8 ranks = 8 prompts x 8 rollouts per step. Paper-faithful full-group
distillation (Algorithm 1 trains every rollout, not failed-only) with top-K
KL (section 2.2: student top-K + tail bucket).

Preflight (CPU-only, needs transformers for the tokenizer):
    uv run --with transformers python -m finetune.sdpo --config configs/sdpo-opus-r1.yml --dry-run

Training:
    torchrun --nproc-per-node 8 -m finetune.sdpo --config configs/sdpo-opus-r1.yml --force
    python -m finetune.sdpo --config ... --force          # single GPU still works

Artifacts land in runs/<run_name>/ exactly like GRPO runs:
    config.yml, tensorboard/, sdpo_history.jsonl,
    checkpoints/checkpoint-<N>/ (adapter), evals/step-<N>/

The probe suite is finetune.grpo.make_eval_suite — identical protocol and
TensorBoard tags to the GRPO runs (plus eval/flores_* when configured), so
pass@1 and chrF curves overlay directly.
"""

import argparse
import json
import os
import random
import statistics
import sys
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


def _pin_gpu() -> None:
    """Restrict this torchrun rank to its own physical GPU BEFORE any CUDA
    context exists (must run before importing torch/vllm). Each process then
    sees exactly one device as cuda:0 — the in-process vLLM engine and the
    trainer land on the same card, and NCCL still spans ranks because the
    physical devices differ."""
    local_rank = os.environ.get("LOCAL_RANK")
    if local_rank is None:
        return
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible:
        devices = visible.split(",")
        if len(devices) > 1:
            os.environ["CUDA_VISIBLE_DEVICES"] = devices[int(local_rank)]
    else:
        os.environ["CUDA_VISIBLE_DEVICES"] = local_rank


def batch_iter(n_tasks: int, world: int, seed: int):
    """Yield global batches of <= world task indices; identical permutation on
    every rank (same seed), reshuffled each epoch."""
    rng = random.Random(seed)
    while True:
        order = list(range(n_tasks))
        rng.shuffle(order)
        for i in range(0, n_tasks, world):
            yield order[i:i + world]


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
    blocks = sorted(t["block_tokens"] for t in tasks)
    world = int(os.environ.get("WORLD_SIZE", 8))
    steps_per_epoch = (len(tasks) + world - 1) // world
    print(f"[dry-run] config OK: run={cfg.run_name} model={resolve_model_id(cfg.model)}")
    print(f"[dry-run] sdpo tasks: {len(tasks)} (privileged blocks p50="
          f"{blocks[len(blocks)//2]} max={blocks[-1]} tokens, budget "
          f"{cfg.sdpo.privileged_budget}; over-budget tasks were excluded at build)")
    print(f"[dry-run] loss: kl_direction={cfg.sdpo.kl_direction} "
          f"top_k={cfg.sdpo.top_k or 'full-vocab'} clamp={cfg.sdpo.kl_clamp}; "
          f"distill up to {cfg.sdpo.max_distill_rollouts}/{cfg.generation.num_generations} "
          f"rollouts/prompt (skip_all_correct={cfg.sdpo.skip_all_correct})")
    print(f"[dry-run] batch shape at WORLD_SIZE={world}: {world} prompts x "
          f"{cfg.generation.num_generations} rollouts/step; one epoch = "
          f"{steps_per_epoch} steps (configured iterations: {cfg.iterations})")
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
    _pin_gpu()   # BEFORE importing torch: one physical GPU per rank

    import torch
    import torch.distributed as dist
    from peft import get_peft_model
    from tensorboardX import SummaryWriter
    from transformers import get_scheduler

    from finetune.sdpo.engine import build_engine, generate, push_policy_weights
    from finetune.sdpo.loss import sdpo_kl, sdpo_topk_kl

    world = int(os.environ.get("WORLD_SIZE", 1))
    rank = int(os.environ.get("RANK", 0))
    ddp = world > 1
    if ddp:
        from datetime import timedelta

        # Generous timeout: checkpoint evals and engine builds are minutes of
        # collective silence; the default 10min NCCL watchdog is too twitchy.
        dist.init_process_group("nccl", timeout=timedelta(hours=2))
    is_main = is_main_process()
    device = torch.device("cuda", 0)   # post-pin every rank sees one GPU
    torch.cuda.set_device(device)

    writer = SummaryWriter(str(run_dir / "tensorboard")) if is_main else None
    if writer:
        writer.add_text("run/config", f"```\n{(run_dir / 'config.yml').read_text()}\n```", 0)

    # Identical LoRA-A init on every rank is REQUIRED: gradient averaging only
    # keeps replicas in lockstep if they start from the same parameters.
    torch.manual_seed(cfg.seed)
    tokenizer = load_tokenizer(cfg)
    model = load_model(cfg)
    peft_model = get_peft_model(model, build_peft_config(cfg, model))
    if is_main:
        peft_model.print_trainable_parameters()
    if cfg.train.gradient_checkpointing:
        peft_model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False})
        peft_model.enable_input_require_grads()
    peft_model.config.use_cache = False
    peft_model.to(device).train()

    trainable = [p for p in peft_model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=cfg.train.learning_rate,
                                  weight_decay=cfg.sdpo.weight_decay)
    scheduler = get_scheduler(
        cfg.sdpo.lr_scheduler, optimizer,
        num_warmup_steps=int(cfg.sdpo.warmup_ratio * cfg.iterations),
        num_training_steps=cfg.iterations)

    # Distinct sampling seed per rank: ranks roll out DIFFERENT prompts, and
    # the eval shards must not replay one another's sample streams.
    engine = build_engine(cfg, resolve_model_id(cfg.model), seed=cfg.seed + rank)
    reward_fn = rewards.get(cfg.reward)
    sdpo_cfg = cfg.sdpo

    def dist_generate_fn(prompts, n, temperature, max_new_tokens):
        """Eval-suite generation, sharded round-robin across ranks. Every rank
        calls this (collective!) and every rank returns the full result list,
        so eval metrics are computed identically everywhere; only rank 0
        writes them (make_eval_suite write flag)."""
        texts = [chat_wrap(tokenizer, p) for p in prompts]
        shard = texts[rank::world]
        mine = generate(engine, shard, n, temperature, max_new_tokens) if shard else []
        if not ddp:
            return mine
        shards = [None] * world
        dist.all_gather_object(shards, mine)
        result = [None] * len(prompts)
        for r, shard in enumerate(shards):
            for j, comps in enumerate(shard):
                result[r + j * world] = comps
        return result

    eval_suite = make_eval_suite(cfg, dist_generate_fn, writer, run_dir,
                                 write=is_main)
    push_policy_weights(engine, peft_model)   # LoRA is zero-init: policy == base
    metrics0 = eval_suite(0)
    if sdpo_cfg.step0_min_pass1 > 0 and metrics0["pass_at_1"] < sdpo_cfg.step0_min_pass1:
        # Metrics are identical on every rank (same seed, gathered completions),
        # so every rank reaches this exit together — no stray survivors.
        if is_main:
            print(f"[abort] step-0 pass@1 {metrics0['pass_at_1']:.4f} < "
                  f"gate {sdpo_cfg.step0_min_pass1} — bad merge or engine/policy "
                  "mismatch; refusing to train")
        if ddp:
            dist.barrier()
            dist.destroy_process_group()
        sys.exit(2)

    tasks = load_sdpo_tasks(cfg.dataset)
    batches = batch_iter(len(tasks), world, cfg.seed)
    history = (run_dir / "sdpo_history.jsonl").open("a") if is_main else None

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

    def distill_loss(student_logits, teacher_logits, w):
        if sdpo_cfg.top_k > 0:
            return sdpo_topk_kl(student_logits, teacher_logits, w,
                                direction=sdpo_cfg.kl_direction,
                                temperature=sdpo_cfg.kl_temperature,
                                top_k=sdpo_cfg.top_k,
                                chunk=sdpo_cfg.logits_chunk,
                                clamp=sdpo_cfg.kl_clamp)
        return sdpo_kl(student_logits, teacher_logits, w,
                       direction=sdpo_cfg.kl_direction,
                       temperature=sdpo_cfg.kl_temperature,
                       chunk=sdpo_cfg.logits_chunk,
                       clamp=sdpo_cfg.kl_clamp)

    for step in range(1, cfg.iterations + 1):
        t0 = time.time()
        batch = next(batches)
        task = tasks[batch[rank]] if rank < len(batch) else None

        if (step - 1) % sdpo_cfg.weight_sync_every == 0:
            push_policy_weights(engine, peft_model)

        optimizer.zero_grad(set_to_none=True)
        rec = {"rank": rank, "task_id": None, "pass_rate": None, "len_p50": None,
               "skipped": False, "n_distilled": 0, "kl_mean": None,
               "kl_thinking": None, "kl_answer": None}

        if task is not None:
            pair = render_pair(task, cfg.prompt_template, tokenizer)
            comps = generate(engine, [pair["student_text"]],
                             cfg.generation.num_generations,
                             cfg.generation.temperature,
                             cfg.generation.max_completion_length)[0]
            passed = score_pass(pair["user_text"], task, comps)
            comp_lens = sorted(len(tokenizer(c, add_special_tokens=False)["input_ids"])
                               for c in comps)
            rec.update({"task_id": task["id"],
                        "pass_rate": sum(passed) / len(passed),
                        "len_p50": comp_lens[len(comp_lens) // 2]})

            if sdpo_cfg.skip_all_correct and all(passed):
                rec["skipped"] = True
                distill = []
            else:
                # failed-first ordering, capped; max_distill_rollouts >= group
                # size distills the ENTIRE group (paper-faithful).
                ranked = sorted(range(len(comps)), key=lambda i: passed[i])
                distill = [comps[i] for i in ranked[:sdpo_cfg.max_distill_rollouts]]

            student_prompt_ids = tokenizer(pair["student_text"],
                                           add_special_tokens=False)["input_ids"]
            teacher_prompt_ids = tokenizer(pair["teacher_text"],
                                           add_special_tokens=False)["input_ids"]

            kl_means, kl_thinking, kl_answer = [], [], []
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
                loss, kl_t = distill_loss(student_logits, teacher_logits, w)
                (loss / len(distill)).backward()
                rec["n_distilled"] += 1
                think_mask = w == sdpo_cfg.thinking_block_weight
                kl_means.append(kl_t.mean().item())
                if think_mask.any():
                    kl_thinking.append(kl_t[think_mask].mean().item())
                if (~think_mask).any():
                    kl_answer.append(kl_t[~think_mask].mean().item())
                del teacher_logits, student_logits
            rec.update({
                "kl_mean": statistics.fmean(kl_means) if kl_means else None,
                "kl_thinking": statistics.fmean(kl_thinking) if kl_thinking else None,
                "kl_answer": statistics.fmean(kl_answer) if kl_answer else None,
            })

        # ---- global gradient average (zero grads = idle/skipped rank) ----
        n_global = rec["n_distilled"]
        if ddp:
            for p in trainable:
                if p.grad is None:
                    p.grad = torch.zeros_like(p.data)
                dist.all_reduce(p.grad)
                p.grad.div_(world)
            n_t = torch.tensor([n_global], device=device)
            dist.all_reduce(n_t)
            n_global = int(n_t.item())

        grad_norm = None
        if n_global > 0:
            # With zero global grads AdamW would still coast on momentum;
            # only step when some rank actually distilled.
            grad_norm = float(torch.nn.utils.clip_grad_norm_(
                trainable, sdpo_cfg.grad_clip))
            optimizer.step()
        scheduler.step()

        # ---- telemetry: gather per-rank recs, rank 0 writes one line ----
        if ddp:
            recs = [None] * world
            dist.all_gather_object(recs, rec)
        else:
            recs = [rec]
        if is_main:
            active = [r for r in recs if r["task_id"] is not None]
            mean_of = lambda key: (statistics.fmean(v) if (v := [
                r[key] for r in active if r[key] is not None]) else None)
            merged = {
                "step": step, "time": time.time(),
                "task_ids": [r["task_id"] for r in active],
                "pass_rate": mean_of("pass_rate"),
                "len_p50": mean_of("len_p50"),
                "n_distilled": sum(r["n_distilled"] for r in active),
                "skipped_ranks": sum(1 for r in active if r["skipped"]),
                "kl_mean": mean_of("kl_mean"),
                "kl_thinking": mean_of("kl_thinking"),
                "kl_answer": mean_of("kl_answer"),
                "grad_norm": grad_norm,
                "lr": scheduler.get_last_lr()[0],
                "sec": round(time.time() - t0, 2),
            }
            history.write(json.dumps(merged) + "\n")
            history.flush()
            if writer and step % cfg.logging_every == 0:
                for tag, key in (("train/group_pass_rate", "pass_rate"),
                                 ("sdpo/kl_mean", "kl_mean"),
                                 ("sdpo/kl_thinking", "kl_thinking"),
                                 ("sdpo/kl_answer", "kl_answer"),
                                 ("completions/len_p50", "len_p50")):
                    if merged[key] is not None:
                        writer.add_scalar(tag, merged[key], step)
                if grad_norm is not None:
                    writer.add_scalar("sdpo/grad_norm", grad_norm, step)
                writer.add_scalar("sdpo/lr", merged["lr"], step)
                writer.add_scalar("sdpo/n_distilled", merged["n_distilled"], step)
                writer.add_scalar("sdpo/skipped_ranks", merged["skipped_ranks"], step)
                print(f"[step {step}/{cfg.iterations}] "
                      f"pass_rate={merged['pass_rate'] if merged['pass_rate'] is not None else float('nan'):.2f} "
                      f"kl={merged['kl_mean'] if merged['kl_mean'] is not None else float('nan'):.4f} "
                      f"n_distilled={merged['n_distilled']} {merged['sec']}s")

        if step % cfg.checkpoint_every == 0 or step == cfg.iterations:
            if ddp:
                dist.barrier()
            if is_main:
                ckpt = run_dir / "checkpoints" / f"checkpoint-{step}"
                peft_model.save_pretrained(str(ckpt))
                tokenizer.save_pretrained(str(ckpt))
            if ddp:
                dist.barrier()
            push_policy_weights(engine, peft_model)
            eval_suite(step)

    if is_main:
        history.close()
        if writer:
            writer.close()
    if ddp:
        dist.barrier()
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
