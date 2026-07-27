#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets"]
# ///
"""Consolidate the Saamayik English->Sanskrit dataset into one eval JSON.

Downloads acomquest/Saamayik from Hugging Face, merges the in-domain
train/validation/test splits (the Mann Ki Baat test_ood split is discarded),
shuffles with a fixed seed, and writes data/eval/samayik.json as a flat
array of {"en": ..., "sa": ...} pairs (Devanagari kept readable).

Usage:  uv run misc/data/fetch_samayik_eval.py
"""

import json
import random
import sys
from pathlib import Path

from datasets import load_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "data" / "eval" / "samayik.json"
SEED = 42


def main() -> None:
    ds = load_dataset("acomquest/Saamayik")
    available = set(ds.keys())
    wanted = [s for s in ("train", "validation", "dev", "test")
              if s in available and "ood" not in s]
    dropped = sorted(available - set(wanted))
    if len(wanted) != 3:
        sys.exit(f"expected 3 in-domain splits, got {wanted} (available: {sorted(available)})")

    pairs, skipped = [], 0
    for split in wanted:
        n = 0
        for row in ds[split]:
            en = row["translation"]["en"].strip()
            sa = row["translation"]["sa"].strip()
            if not en or not sa:
                skipped += 1
                continue
            pairs.append({"en": en, "sa": sa})
            n += 1
        print(f"{split}: {n} pairs", file=sys.stderr)
    print(f"discarded splits: {dropped}   skipped empty rows: {skipped}", file=sys.stderr)

    random.Random(SEED).shuffle(pairs)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"wrote {len(pairs)} pairs -> {OUT_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
