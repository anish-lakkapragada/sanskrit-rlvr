#!/usr/bin/env python
"""Build the mixed translation+morphology SFT corpora (sft-qwen3-4b-mix-upsample-* runs).

Base corpus: the Samayik translation pairs (data/finetune/sft-standard/
samayik_finetune.json, already excluding both 750-pair contamination-free
validation sets -- see make_standard_sft_data.py). Into it we mix the Opus
reasoning traces (data/finetune/sft-r1/claude-opus-5.json) upsampled by a factor k --
k copies of every trace -- so the morphology share of the corpus sweeps from ~7% to ~62%.

A FIXED validation split is carved out of BOTH task pools first and is identical for
every arm, so per-task eval loss is comparable across the whole sweep (and so
"converged" can be demonstrated rather than assumed).

Records use the schema finetune.sft consumes unchanged:
    prompt:     [{"role": "user", ...}]
    completion: [{"role": "assistant", ...}]
finetune.data.load_sft_dataset keeps only those two columns, so the extra `task`
field is provenance only and never reaches the trainer.

Usage:  uv run python misc/data/make_mixed_sft_data.py
"""

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

TRANSLATION_SRC = REPO_ROOT / "data" / "finetune" / "sft-standard" / "samayik_finetune.json"
MORPHOLOGY_SRC = REPO_ROOT / "data" / "finetune" / "sft-r1" / "claude-opus-5.json"
OUT_DIR = REPO_ROOT / "data" / "finetune" / "sft-upsample-mix"

RATIOS = (0.5, 1, 2, 4, 6, 8, 10)
N_VAL_TRANSLATION = 500
N_VAL_MORPHOLOGY = 300
SEED = 42


def fmt(ratio) -> str:
    """0.5 -> '0.5', 1.0 -> '1' (run/file names stay clean)."""
    return str(int(ratio)) if float(ratio).is_integer() else str(ratio)


def slim(record: dict, task: str, idx: int) -> dict:
    return {"id": f"{task}:{idx:06d}", "task": task,
            "prompt": record["prompt"], "completion": record["completion"]}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trans = [slim(r, "translation", i)
             for i, r in enumerate(json.loads(TRANSLATION_SRC.read_text()))]
    morph = [slim(r, "morphology", i)
             for i, r in enumerate(json.loads(MORPHOLOGY_SRC.read_text()))]
    print(f"source pools: {len(trans)} translation, {len(morph)} morphology", file=sys.stderr)

    # --- fixed validation split, carved before any upsampling -------------
    rng = random.Random(SEED)
    val_trans = rng.sample(trans, N_VAL_TRANSLATION)
    val_morph = rng.sample(morph, N_VAL_MORPHOLOGY)
    val_ids = {r["id"] for r in val_trans} | {r["id"] for r in val_morph}
    train_trans = [r for r in trans if r["id"] not in val_ids]
    train_morph = [r for r in morph if r["id"] not in val_ids]
    assert len(train_trans) == len(trans) - N_VAL_TRANSLATION
    assert len(train_morph) == len(morph) - N_VAL_MORPHOLOGY

    for name, rows in (("val-translation", val_trans), ("val-morphology", val_morph)):
        (OUT_DIR / f"{name}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    print(f"val split: {len(val_trans)} translation + {len(val_morph)} morphology "
          f"(held out of EVERY arm)", file=sys.stderr)
    print(f"train pools: {len(train_trans)} translation, {len(train_morph)} morphology\n",
          file=sys.stderr)

    # --- one mixed corpus per upsampling ratio ----------------------------
    for ratio in RATIOS:
        if ratio < 1:  # fractional -> seeded subsample, never a partial duplicate
            n = round(len(train_morph) * ratio)
            morph_rows = random.Random(SEED).sample(train_morph, n)
        else:
            assert float(ratio).is_integer(), f"non-integer ratio > 1: {ratio}"
            morph_rows = train_morph * int(ratio)

        rows = train_trans + morph_rows
        random.Random(SEED).shuffle(rows)
        share = len(morph_rows) / len(rows)
        out = OUT_DIR / f"mix-upsample-{fmt(ratio)}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
            f.write("\n")

        # sanity: mask-relevant schema must be uniform across both task types
        assert all(len(r["prompt"]) == 1 and r["prompt"][0]["role"] == "user"
                   and len(r["completion"]) == 1
                   and r["completion"][0]["role"] == "assistant" for r in rows), out
        print(f"upsample {fmt(ratio):>4}x: {len(train_trans)} translation + "
              f"{len(morph_rows)} morphology = {len(rows):>6} rows "
              f"({share:5.1%} morphology) -> {out.relative_to(REPO_ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
