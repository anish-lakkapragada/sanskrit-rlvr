"""Benchmark any model (a run's checkpoint, or a raw base model) against any
eval file, judged per-row by its `judge` field:

    python -m finetune.evaluate --run sft-baseline --benchmark data/eval/held_out_vocab.jsonl
    python -m finetune.evaluate --model mlx-community/Qwen3-4B-Instruct-2507-4bit \
        --benchmark data/eval/beyond_fragment.jsonl --tag base

Writes results/<tag>__<benchmark-stem>.json with a summary + every record.
"""

import argparse
import json
from pathlib import Path

import yaml

from .common import ROOT, RUNS, eval_checkpoint, read_jsonl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True, type=Path)
    ap.add_argument("--run", help="run name under runs/ (uses its final adapter)")
    ap.add_argument("--checkpoint", type=int,
                    help="specific checkpoint iteration (default: final)")
    ap.add_argument("--model", help="raw model instead of a run")
    ap.add_argument("--tag", help="results file prefix (default: run name/model)")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    if bool(args.run) == bool(args.model):
        ap.error("exactly one of --run / --model")

    if args.run:
        run_dir = RUNS / args.run
        cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
        base = cfg["model"]["base"]
        if cfg["model"].get("init_from_run"):
            base = str(RUNS / cfg["model"]["init_from_run"] / "fused_4bit")
        ckpt = (run_dir / "checkpoints" /
                (f"{args.checkpoint:07d}_adapters.safetensors"
                 if args.checkpoint else "adapters.safetensors"))
        tag = args.tag or args.run
    else:
        base, ckpt, tag = args.model, None, (args.tag or Path(args.model).name)

    rows = read_jsonl(ROOT / args.benchmark)
    if args.limit:
        rows = rows[: args.limit]
    summary, records = eval_checkpoint(base, ckpt, rows)
    out = ROOT / "results" / f"{tag}__{args.benchmark.stem}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(
        {"model": base, "checkpoint": str(ckpt) if ckpt else None,
         "benchmark": str(args.benchmark), "summary": summary,
         "records": records}, ensure_ascii=False, indent=1))
    print(json.dumps({"tag": tag, "benchmark": args.benchmark.stem, **summary},
                     indent=2))


if __name__ == "__main__":
    main()
