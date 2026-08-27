#!/usr/bin/env python
"""Build the SDPO training corpus: task records + rendered privileged blocks.

For every task in the source file, re-derive the gold form with vidyut-prakriya
(log_steps=True), render the derivation as the teacher's "Reference (for
grading)" block (Devanagari segments, 1.3.x it-samjna housekeeping steps
filtered, consecutive duplicate results collapsed), and measure its length in
student-tokenizer tokens.

USER POLICY (2026-08-24): tasks whose rendered block exceeds --budget tokens
are EXCLUDED from the corpus entirely (no truncation), and the exclusion
percentage is reported.

    uv run --with transformers --with tokenizers python misc/data/make_sdpo_data.py

Output records are the original task fields plus:
    privileged_block: str   # the exact text appended to the teacher prompt
    block_tokens: int       # length under the student tokenizer
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HEADER = "=== Reference (for grading) ==="


def render_block(task: dict, prakriya, deva) -> str:
    lines, prev = [], None
    for step in prakriya.history:
        if step.code.startswith("1.3."):        # it-samjna housekeeping
            continue
        result = " + ".join(deva(seg) for seg in step.result)
        if result == prev:                       # no visible change
            continue
        prev = result
        lines.append(f"{step.code}  {result}")
    return (f"{HEADER}\n"
            f"Correct form: {task['gold_devanagari'][0]}\n"
            "Derivation (vidyut-prakriya):\n" + "\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", default="data/finetune/task-data/finetune.json")
    ap.add_argument("--out", default="data/finetune/task-data/sdpo-finetune.json")
    ap.add_argument("--budget", type=int, default=512,
                    help="max privileged-block tokens; over-budget tasks are EXCLUDED")
    ap.add_argument("--tokenizer", default="Qwen/Qwen3-4B")
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from vidyut.lipi import Scheme, transliterate
    from vidyut.prakriya import (
        Dhatu, Gana, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana,
    )

    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    V = Vyakarana(log_steps=True)
    deva = lambda slp1: transliterate(slp1, Scheme.Slp1, Scheme.Devanagari)

    tasks = json.loads((ROOT / args.tasks).read_text())
    kept, over_budget, derive_failures, no_match = [], 0, 0, 0
    token_counts = []

    for t in tasks:
        try:
            dhatu = Dhatu.mula(t["dhatu"]["aupadeshika"],
                               getattr(Gana, t["dhatu"]["gana"]))
            prakriyas = V.derive(Pada.Tinanta(
                dhatu=dhatu,
                prayoga=getattr(Prayoga, t["morphology"]["prayoga"]),
                lakara=getattr(Lakara, t["morphology"]["lakara"]),
                purusha=getattr(Purusha, t["morphology"]["purusha"]),
                vacana=getattr(Vacana, t["morphology"]["vacana"])))
        except Exception:
            derive_failures += 1
            continue
        golds = set(t["gold_slp1"])
        p = next((x for x in prakriyas if x.text in golds), None)
        if p is None:
            no_match += 1
            continue
        block = render_block(t, p, deva)
        n_tokens = len(tok(block, add_special_tokens=False)["input_ids"])
        token_counts.append(n_tokens)
        if n_tokens > args.budget:
            over_budget += 1
            continue
        kept.append({**t, "privileged_block": block, "block_tokens": n_tokens})

    out_path = ROOT / args.out
    out_path.write_text(json.dumps(kept, ensure_ascii=False, indent=1))

    n = len(tasks)
    token_counts.sort()
    tc = token_counts
    print(f"[sdpo-data] source tasks:        {n}")
    print(f"[sdpo-data] derivation failures: {derive_failures} ({derive_failures/n:.2%})")
    print(f"[sdpo-data] no gold-match:       {no_match} ({no_match/n:.2%})")
    print(f"[sdpo-data] block tokens: p50={tc[len(tc)//2]} p90={tc[int(len(tc)*.9)]} "
          f"p99={tc[int(len(tc)*.99)]} max={tc[-1]}")
    print(f"[sdpo-data] OVER BUDGET (> {args.budget} tokens, EXCLUDED): "
          f"{over_budget}/{n} = {over_budget/n:.2%}")
    print(f"[sdpo-data] kept: {len(kept)}/{n} = {len(kept)/n:.2%} -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
