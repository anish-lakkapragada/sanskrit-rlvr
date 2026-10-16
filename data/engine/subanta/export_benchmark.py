"""Export 5,000 distinct subanta tasks balanced over case × number, seed 69.

Run from any directory: python3 data/engine/subanta/export_benchmark.py
The output preserves the source JSON objects and their complete answer sets.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/datasets/subanta/full.json"
OUTPUT = ROOT / "data/benchmark/subanta/subanta.json"
SEED = 69
SIZE = 5000


def export():
    metadata_path = SOURCE.with_name("manifest.json")
    metadata_bytes = metadata_path.read_bytes()
    metadata = json.loads(metadata_bytes)
    assert metadata["generation_complete"]
    cells = [(case, number) for case in metadata["scope"]["cases"]
             for number in metadata["scope"]["numbers"]]
    assert len(cells) == len(set(cells)) == 24
    population = metadata["counts"]["stem_gender_pairs"]
    assert metadata["counts"]["full"] == population * len(cells)
    rng = random.Random(SEED)
    base, remainder = divmod(SIZE, len(cells))
    extra = set(rng.sample(cells, remainder))
    quotas = {cell: base + (cell in extra) for cell in cells}
    # Uniform sampling without replacement from each cell's source-order ranks.
    ranks = {cell: set(rng.sample(range(population), quotas[cell])) for cell in cells}
    observed, digest, selected = Counter(), hashlib.sha256(), []
    with SOURCE.open("rb") as source:
        opening = next(source)
        assert opening == b"[\n"
        digest.update(opening)
        for line in source:
            digest.update(line)
            raw = line.strip()
            if raw == b"]":
                assert not source.read(), "Trailing source content"
                break
            raw = raw.removesuffix(b",")
            row = json.loads(raw)
            cell = (row["morphology"]["vibhakti"], row["morphology"]["vacana"])
            if observed[cell] in ranks[cell]:
                assert row["gold_slp1"] and row["gold_devanagari"] and not row.get("warnings")
                selected.append((sum(observed.values()), cell, row["id"], raw))
            observed[cell] += 1
        else:
            raise ValueError("Missing closing source array bracket")
    assert digest.hexdigest() == metadata["files"]["full.json"]["sha256"]
    assert observed == Counter({cell: population for cell in cells})
    assert len(selected) == len({record[2] for record in selected}) == SIZE
    assert Counter(record[1] for record in selected) == Counter(quotas)
    rng.shuffle(selected)
    payload = b"[\n" + b",\n".join(record[3] for record in selected) + b"\n]\n"
    # The output is a strict subset of complete, unmodified source objects.
    assert len(json.loads(payload)) == SIZE
    manifest = {
        "dataset": "subanta", "records": SIZE, "seed": SEED, "replacement": False,
        "method": "Stratified uniform sampling over 8 cases × 3 numbers; genders pooled within each cell.",
        "allocation": "208 per cell plus one extra in 8 cells selected with the seeded RNG.",
        "rng": "Python random.Random(69); extra cells, within-cell ranks, then final row shuffle.",
        "cell_order": "Listed source-manifest case order, then listed number order.",
        "source": {"path": str(SOURCE.relative_to(ROOT)), "records": sum(observed.values()),
                   "sha256": digest.hexdigest(), "manifest_sha256": hashlib.sha256(metadata_bytes).hexdigest()},
        "exporter": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                     "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "cells": [{"vibhakti": case, "vacana": number, "source_records": observed[case, number],
                   "selected": quotas[case, number]} for case, number in cells],
        "source_indices_zero_based_in_output_order": [record[0] for record in selected],
        "output": {"path": str(OUTPUT.relative_to(ROOT)), "bytes": len(payload),
                   "sha256": hashlib.sha256(payload).hexdigest()},
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_bytes(payload)
    temp.replace(OUTPUT)
    output_metadata = OUTPUT.with_suffix(".manifest.json")
    temp_metadata = output_metadata.with_suffix(".json.tmp")
    temp_metadata.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    temp_metadata.replace(output_metadata)
    print(f"Exported {SIZE:,} unique tasks to {OUTPUT.relative_to(ROOT)} (seed {SEED}).")
    print("Cell sizes: 16 × 208 and 8 × 209; all source records and answer sets preserved.")


if __name__ == "__main__":
    export()
