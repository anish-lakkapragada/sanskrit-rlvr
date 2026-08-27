#!/usr/bin/env python
"""Results table for the fixed-token-budget mixture campaign.

One row per model (base + 15 mixtures):
    Model | pass@1 [95% CI] | pass@2 | pass@4 | pass@8 | pass@16 | Solved |
    FLORES-200 chrF/chrF++ (tag%, n) | Samayik chrF/chrF++ (tag%, n)

VP metrics come from the prevals 669x16 summaries (data/data-mixture/eval/
vp-eval.json). chrF/chrF++ are TAG-CONDITIONAL: computed only over completions
with exactly one well-formed <translation> tag (the tag%% column reports
compliance; n is the number of tagged completions actually scored). Eval sets:
data/data-mixture/eval/{samayik-eval,flores-200}.json (byte-identical to the
files the eval jobs read).

Usage: uv run python misc/mixture_campaign/make_results.py [--root DIR]
Missing models are skipped, so the table can be regenerated incrementally
while the campaign is still running.
"""

import argparse
import glob
import json
from pathlib import Path

from sacrebleu.metrics import CHRF

BUDGETS = ("10m", "15m", "20m")
SHARES = (100, 67, 50, 33, 0)
CHRF_STD, CHRF_PP = CHRF(), CHRF(word_order=2)


def tag_conditional(final_json: Path):
    d = json.loads(final_json.read_text())
    samples = d["samples"]
    kept = [s for s in samples if s["hyp"]]
    if not kept:
        return None
    hyps = [s["hyp"] for s in kept]
    refs = [[s["ref"] for s in kept]]
    return {
        "chrf": CHRF_STD.corpus_score(hyps, refs).score,
        "chrf_pp": CHRF_PP.corpus_score(hyps, refs).score,
        "tag_pct": 100 * len(kept) / len(samples),
        "n": len(kept),
    }


def load_model(root: Path, run_dir: str, suite: str):
    row = {}
    hits = glob.glob(str(root / "data-mixture" / suite / "*" / "summary.json"))
    if hits:
        s = json.loads(Path(hits[0]).read_text())
        row["pass"] = {k: 100 * v for k, v in s["pass_at_k"].items()}
        row["ci1"] = [100 * v for v in s["ci95_pass"]["1"]]
        row["solved"] = f"{s['solved_tasks']}/{s['num_prompts']}"
    for ds, key in (("flores-200", "flores"), ("samayik", "samayik")):
        f = root / run_dir / "evals-final" / f"final-{ds}.json"
        if f.exists():
            row[key] = tag_conditional(f)
    return row or None


def fmt_chrf(c):
    if not c:
        return "--"
    return (f"{c['chrf']:.2f}/{c['chrf_pp']:.2f} "
            f"({c['tag_pct']:.1f}%, {c['n']})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="runs-pull-staging")
    ap.add_argument("--out", default="misc/figures/data-mixture-results.md")
    args = ap.parse_args()
    root = Path(args.root)

    models = [("Qwen3-4B (base)", "base-qwen3-4b", "dm-base-qwen3-4b")]
    for b in BUDGETS:
        for p in SHARES:
            models.append((f"{b.upper()} · {p}% samayik",
                           f"sft-qwen3-4b-tb{b}-samayik{p}",
                           f"dm-tb{b}-samayik{p}"))

    lines = [
        "| Model | pass@1 [95% CI] | pass@2 | pass@4 | pass@8 | pass@16 | Solved "
        "| FLORES-200 chrF/chrF++ (tag%, n) | Samayik chrF/chrF++ (tag%, n) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    missing = []
    for name, run_dir, suite in models:
        row = load_model(root, run_dir, suite)
        if row is None:
            missing.append(name)
            continue
        if "pass" in row:
            p = row["pass"]
            vp = (f"{p['1']:.2f}% [{row['ci1'][0]:.2f}, {row['ci1'][1]:.2f}] "
                  f"| {p['2']:.2f}% | {p['4']:.2f}% | {p['8']:.2f}% | {p['16']:.2f}% "
                  f"| {row['solved']}")
        else:
            vp = "-- | -- | -- | -- | -- | --"
            missing.append(f"{name} (VP pending)")
        lines.append(f"| {name} | {vp} "
                     f"| {fmt_chrf(row.get('flores'))} | {fmt_chrf(row.get('samayik'))} |")

    out = "\n".join(lines) + "\n"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(out)
    print(out)
    if missing:
        print(f"[incomplete] awaiting: {', '.join(missing)}")


if __name__ == "__main__":
    main()
