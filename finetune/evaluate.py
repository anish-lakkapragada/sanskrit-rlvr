"""Benchmark any model (a run's checkpoint, or a raw base model) against any
eval file, judged per-row by its `judge` field:

    python -m finetune.evaluate --run sft-baseline --benchmark data/in_fragment/eval.jsonl
    python -m finetune.evaluate --model mlx-community/Qwen3-4B-Instruct-2507-4bit \
        --benchmark data/out_of_fragment/eval.jsonl --tag base

Writes results/<tag>__<benchmark-stem>.json with a summary + every record.
"""

import argparse
import json
from pathlib import Path

import yaml

from .common import ROOT, RUNS, eval_checkpoint, read_jsonl


def _resolve(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True, type=Path)
    ap.add_argument("--run", help="run name under runs/ (uses its final adapter)")
    ap.add_argument("--checkpoint", type=int,
                    help="specific checkpoint iteration (default: final)")
    ap.add_argument("--model", help="raw model instead of a run")
    ap.add_argument("--backend", choices=("mlx", "cuda"),
                    help="generation backend for --model (a run uses its own)")
    ap.add_argument("--tag", help="results file prefix (default: run name/model)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-think", action="store_true",
                    help="render prompts with enable_thinking=False (hybrid "
                         "Qwen3 raw models; runs read this from their config)")
    args = ap.parse_args()
    if bool(args.run) == bool(args.model):
        ap.error("exactly one of --run / --model")

    chat_kwargs = {"enable_thinking": False} if args.no_think else None
    if args.run:
        run_dir = RUNS / args.run
        cfg = yaml.safe_load((run_dir / "config.yaml").read_text())
        backend = cfg.get("backend", "mlx")
        base = cfg["model"]["base"]
        chat_kwargs = cfg["model"].get("chat_template_kwargs") or chat_kwargs
        if cfg["model"].get("init_from_run"):
            src = RUNS / cfg["model"]["init_from_run"]
            if backend == "cuda":
                src_cfg = yaml.safe_load((src / "config.yaml").read_text())
                base = str(_resolve(src_cfg["model"].get("final_checkpoint")
                                    or src / "checkpoints" / "final"))
            else:
                base = str(src / "fused_4bit")
        # both backends: checkpoints/<iteration>/ dirs + checkpoints/final
        ckpt = (run_dir / "checkpoints" / str(args.checkpoint)
                if args.checkpoint else
                _resolve(cfg["model"].get("final_checkpoint")
                         or run_dir / "checkpoints" / "final"))
        tag = args.tag or args.run
    else:
        backend = args.backend or "mlx"
        base, ckpt, tag = args.model, None, (args.tag or Path(args.model).name)

    rows = read_jsonl(ROOT / args.benchmark)
    if args.limit:
        rows = rows[: args.limit]
    summary, records = eval_checkpoint(base, ckpt, rows, backend=backend,
                                       chat_kwargs=chat_kwargs)
    # both benchmarks are named eval.jsonl — key results by their group dir
    bench_id = "_".join(args.benchmark.parts[-2:]).removesuffix(".jsonl")
    out = ROOT / "results" / f"{tag}__{bench_id}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(
        {"model": base, "checkpoint": str(ckpt) if ckpt else None,
         "benchmark": str(args.benchmark), "summary": summary,
         "records": records}, ensure_ascii=False, indent=1))
    print(json.dumps({"tag": tag, "benchmark": bench_id, **summary},
                     indent=2))


if __name__ == "__main__":
    main()
