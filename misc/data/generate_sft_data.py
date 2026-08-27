#!/usr/bin/env python
"""Generate an SFT distillation corpus by rejection-sampling a Claude teacher
over the vidyut-prakriya training tasks (Anthropic Message Batches API, 50%
of standard token prices).

For every task in the configured dataset, sample N completions, score them
with the configured reward (same registry as training/eval), and keep only
trajectories that are fully correct (reward >= min_reward) and not truncated.
Output records use TRL's prompt/completion conversational format, so
SFTTrainer masks prompt tokens from the loss automatically.

Usage (repo root):
    uv run python misc/data/generate_sft_data.py misc/data/claude-opus-5-sft.yml --dry-run
    uv run python misc/data/generate_sft_data.py misc/data/claude-opus-5-sft.yml --smoke
    uv run python misc/data/generate_sft_data.py misc/data/claude-opus-5-sft.yml

Resumable: batch ids are persisted to the state file right after submission
and results are cached under raw_dir/*.jsonl. Re-running skips submitted
shards and re-uses harvested results (batches stay retrievable for 29 days),
so a crash or ^C never re-spends money.
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml

from finetune.prompts import extract_answer, render_vp_task
from finetune.rewards import get as get_reward
from prevals.eval import _anthropic_api_key

# $/MTok (input, output) at Message Batches rates (50% of standard).
BATCH_PRICES = {"claude-opus-5": (2.50, 12.50)}
# Measured means: v1/vp_task_eval.txt on the opus-5 tokenizer; output at
# max_new_tokens=2048 (prevals/outputs/prompt-v1/claude-api-sweep/).
EST_INPUT_TOK, EST_OUTPUT_TOK = 458, 1063

SMOKE_TASKS = 5


def load_cfg(path: str) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    required = ["model", "dataset", "prompt_template", "samples_per_prompt",
                "max_new_tokens", "reward", "min_reward", "shard_size",
                "output", "raw_dir", "state"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"{path}: missing config key(s) {missing}")
    get_reward(cfg["reward"])  # fail fast on unknown reward
    if not (ROOT / cfg["dataset"]).exists():
        raise FileNotFoundError(cfg["dataset"])
    mode = cfg.get("anthropic_thinking", "omit")
    if mode not in ("omit", "disabled", "adaptive"):
        raise ValueError(f"anthropic_thinking must be omit|disabled|adaptive, got {mode!r}")
    return cfg


def resolve_paths(cfg: dict, smoke: bool):
    """(output, state, shard_path_fn); --smoke gets its own files so a test
    run never touches the real corpus or resume state."""
    tag = ".smoke" if smoke else ""
    out, st = Path(cfg["output"]), Path(cfg["state"])
    output = ROOT / out.with_name(out.stem + tag + out.suffix)
    state = ROOT / st.with_name(st.stem + tag + st.suffix)
    raw_dir = ROOT / cfg["raw_dir"]
    return output, state, lambda si: raw_dir / f"{out.stem}{tag}.shard{si}.jsonl"


def submit_missing_shards(client, cfg, prompts, shards, state, state_path):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    extra = ({} if cfg.get("anthropic_thinking", "omit") == "omit"
             else {"thinking": {"type": cfg["anthropic_thinking"]}})
    for si, shard in enumerate(shards):
        if str(si) in state["shards"]:
            continue
        requests = [
            Request(
                custom_id=f"t{i}-s{j}",  # batches reject :/. -> index-based ids
                params=MessageCreateParamsNonStreaming(
                    model=cfg["model"],
                    max_tokens=cfg["max_new_tokens"],
                    messages=[{"role": "user", "content": prompts[i]}],
                    **extra,
                ),
            )
            for i, j in shard
        ]
        batch = client.messages.batches.create(requests=requests)
        state["shards"][str(si)] = {"batch_id": batch.id, "harvested": False}
        state_path.write_text(json.dumps(state, indent=1))
        print(f"[sft-gen] shard {si}: batch {batch.id} submitted "
              f"({len(requests)} requests)", flush=True)


def harvest(client, batch_id: str, path: Path) -> None:
    """Batch results -> one JSONL row per request (raw cache; refiltering
    never has to re-download). Written atomically via a temp file."""
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        for result in client.messages.batches.results(batch_id):
            row = {"custom_id": result.custom_id, "batch_id": batch_id,
                   "ok": result.result.type == "succeeded"}
            if row["ok"]:
                msg = result.result.message
                row.update(
                    text="".join(b.text for b in msg.content if b.type == "text"),
                    stop_reason=msg.stop_reason,
                    input_tokens=msg.usage.input_tokens,
                    output_tokens=msg.usage.output_tokens,
                )
            else:
                row["result_type"] = result.result.type
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.rename(path)


def poll_and_harvest(client, state, state_path, shard_path, interval: int):
    pending = {k: v for k, v in state["shards"].items() if not v["harvested"]}
    t0 = time.perf_counter()
    while pending:
        for key, meta in sorted(pending.items()):
            batch = client.messages.batches.retrieve(meta["batch_id"])
            if batch.processing_status == "ended":
                harvest(client, meta["batch_id"], shard_path(key))
                meta["harvested"] = True
                state_path.write_text(json.dumps(state, indent=1))
                del pending[key]
                print(f"[sft-gen] shard {key}: harvested -> {shard_path(key)}",
                      flush=True)
            else:
                c = batch.request_counts
                print(f"[sft-gen] shard {key}: {batch.processing_status} "
                      f"({c.succeeded} ok, {c.errored} errored, {c.processing} left, "
                      f"{time.perf_counter() - t0:.0f}s)", flush=True)
        if pending:
            time.sleep(interval)


def assemble(cfg, tasks, prompts, n, state, shard_path, output: Path) -> None:
    rows = []
    for key in sorted(state["shards"], key=int):
        with shard_path(key).open() as f:
            rows.extend(json.loads(line) for line in f)

    counts = defaultdict(int)
    candidates = []  # (task_idx, sample_idx, row) for succeeded requests
    in_tok = out_tok = 0
    for row in rows:
        counts["requests"] += 1
        if not row["ok"]:
            counts["errored"] += 1
            continue
        in_tok += row["input_tokens"]
        out_tok += row["output_tokens"]
        if row["stop_reason"] == "refusal":
            counts["refused"] += 1
        if row["stop_reason"] == "max_tokens":
            counts["truncated"] += 1
        i, j = (int(p[1:]) for p in row["custom_id"].split("-"))
        candidates.append((i, j, row))
    candidates.sort(key=lambda c: (c[0], c[1]))

    reward_fn = get_reward(cfg["reward"])
    rewards = reward_fn(
        [prompts[i] for i, _, _ in candidates],
        [row["text"] for _, _, row in candidates],
        gold_devanagari=[tasks[i]["gold_devanagari"] for i, _, _ in candidates],
    )

    kept, seen, covered = [], defaultdict(set), set()
    today = time.strftime("%Y-%m-%d")
    for (i, j, row), reward in zip(candidates, rewards):
        if reward < cfg["min_reward"]:
            continue
        if cfg.get("discard_truncated", True) and row["stop_reason"] == "max_tokens":
            counts["kept_but_truncated_dropped"] += 1
            continue
        if cfg.get("dedupe", True) and row["text"] in seen[i]:
            counts["dedupe_dropped"] += 1
            continue
        seen[i].add(row["text"])
        covered.add(i)
        task = tasks[i]
        kept.append({
            "id": task["id"],
            "sample": j,
            "prompt": [{"role": "user", "content": prompts[i]}],
            "completion": [{"role": "assistant", "content": row["text"]}],
            "answer_devanagari": extract_answer(row["text"]),
            "gold_devanagari": task["gold_devanagari"],
            "reward": reward,
            "dhatu": task["dhatu"],
            "morphology": task["morphology"],
            "meta": {"teacher": cfg["model"],
                     "prompt_template": cfg["prompt_template"],
                     "output_tokens": row["output_tokens"],
                     "batch_id": row["batch_id"],
                     "generated": today},
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(kept, ensure_ascii=False, indent=1))

    in_price, out_price = BATCH_PRICES[cfg["model"]]
    cost = (in_tok * in_price + out_tok * out_price) / 1e6
    thin = "-" * 64
    print(f"\n{thin}\n[sft-gen] {output}  ({len(kept)} records)\n{thin}")
    print(f" requests        {counts['requests']}  "
          f"(errored {counts['errored']}, refused {counts['refused']}, "
          f"truncated {counts['truncated']})")
    print(f" kept            {len(kept)} / {counts['requests']} "
          f"({len(kept) / max(counts['requests'], 1) * 100:.1f}%)"
          f"   dedupe-dropped {counts['dedupe_dropped']}")
    print(f" task coverage   {len(covered)} / {len(tasks)} "
          f"({len(covered) / len(tasks) * 100:.1f}%)")
    print(f" spend           {in_tok:,} in + {out_tok:,} out tokens "
          f"= ${cost:,.2f} (batch rates)")
    print(thin)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("config")
    ap.add_argument("--dry-run", action="store_true",
                    help="render prompts + print shard plan and cost estimate; no API")
    ap.add_argument("--smoke", action="store_true",
                    help=f"end-to-end run on the first {SMOKE_TASKS} tasks, "
                         "separate .smoke output/state files")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    tasks = json.loads((ROOT / cfg["dataset"]).read_text())
    if args.smoke:
        tasks = tasks[:SMOKE_TASKS]
    prompts = [render_vp_task(t, template=cfg["prompt_template"]) for t in tasks]
    n = cfg["samples_per_prompt"]
    reqs = [(i, j) for i in range(len(tasks)) for j in range(n)]
    shards = [reqs[k:k + cfg["shard_size"]]
              for k in range(0, len(reqs), cfg["shard_size"])]
    output, state_path, shard_path = resolve_paths(cfg, args.smoke)

    if args.dry_run:
        in_price, out_price = BATCH_PRICES[cfg["model"]]
        est = len(reqs) * (EST_INPUT_TOK * in_price + EST_OUTPUT_TOK * out_price) / 1e6
        print(f"[dry-run] {len(tasks)} tasks x {n} samples = {len(reqs)} requests "
              f"in {len(shards)} shard(s) of <= {cfg['shard_size']}")
        print(f"[dry-run] model {cfg['model']}  max_tokens {cfg['max_new_tokens']}  "
              f"thinking {cfg.get('anthropic_thinking', 'omit')}")
        print(f"[dry-run] keep iff reward >= {cfg['min_reward']} and not truncated; "
              f"output -> {output}")
        print(f"[dry-run] estimated cost ~${est:,.0f} "
              f"({EST_INPUT_TOK} in / {EST_OUTPUT_TOK} out tok/request, batch rates)")
        print("[dry-run] sample prompt " + "-" * 40 + f"\n{prompts[0]}")
        return

    import anthropic

    api_key = _anthropic_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set (environment or .env)")
    client = anthropic.Anthropic(api_key=api_key)

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = (json.loads(state_path.read_text()) if state_path.exists()
             else {"shards": {}})

    submit_missing_shards(client, cfg, prompts, shards, state, state_path)
    poll_and_harvest(client, state, state_path, shard_path,
                     interval=15 if args.smoke else 60)
    assemble(cfg, tasks, prompts, n, state, shard_path, output)


if __name__ == "__main__":
    main()
