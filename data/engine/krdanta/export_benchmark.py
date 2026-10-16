"""Export 5,000 distinct krdanta tasks in source suffix proportions, seed 69.

Run from the repository root: python3 data/engine/krdanta/export_benchmark.py
Source JSON objects and their complete accepted answer sets are preserved.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/datasets/krdanta/full.json"
OUTPUT = ROOT / "data/benchmark/krdanta/krdanta.json"
SEED = 69
SIZE = 5000


def export():
    metadata_bytes = SOURCE.with_name("manifest.json").read_bytes()
    metadata = json.loads(metadata_bytes)
    assert metadata["generation_complete"] and not metadata["counts"]["engine_errors"]
    suffixes = metadata["scope"]["krt"]
    populations = metadata["counts"]["per_suffix"]
    total = metadata["counts"]["full"]
    assert len(suffixes) == len(set(suffixes)) == 14
    assert set(suffixes) == set(populations)
    assert sum(populations.values()) == total
    assert 0 < SIZE < total

    # Largest-remainder allocation keeps each quota within one task of its
    # proportional target. Integer arithmetic avoids floating-point tie errors.
    quotas = {suffix: SIZE * populations[suffix] // total for suffix in suffixes}
    remainder_order = sorted(suffixes, key=lambda suffix: -(SIZE * populations[suffix] % total))
    for suffix in remainder_order[:SIZE - sum(quotas.values())]:
        quotas[suffix] += 1
    assert sum(quotas.values()) == SIZE

    rng = random.Random(SEED)
    ranks = {
        suffix: set(rng.sample(range(populations[suffix]), quotas[suffix]))
        for suffix in suffixes
    }
    observed, digest, selected = Counter(), hashlib.sha256(), []
    with SOURCE.open("rb") as source:
        opening = next(source)
        assert opening == b"[\n"
        digest.update(opening)
        for index, line in enumerate(source):
            digest.update(line)
            raw = line.strip()
            if raw == b"]":
                assert not source.read(), "Trailing source content"
                break
            raw = raw.removesuffix(b",")
            row = json.loads(raw)
            suffix = row["morphology"]["krt"]
            if observed[suffix] in ranks[suffix]:
                assert row["gold_slp1"] and row["gold_devanagari"] and not row.get("warnings")
                selected.append((index, suffix, row["id"], raw))
            observed[suffix] += 1
        else:
            raise ValueError("Missing closing source array bracket")
    assert digest.hexdigest() == metadata["files"]["full.json"]["sha256"]
    assert observed == Counter(populations)
    assert len(selected) == len({record[2] for record in selected}) == SIZE
    assert Counter(record[1] for record in selected) == Counter(quotas)
    rng.shuffle(selected)
    payload = b"[\n" + b",\n".join(record[3] for record in selected) + b"\n]\n"
    assert len(json.loads(payload)) == SIZE

    manifest = {
        "dataset": "krdanta", "records": SIZE, "seed": SEED, "replacement": False,
        "method": "Proportional stratified sampling over the 14 reviewed krt suffixes; uniform sampling within each suffix.",
        "allocation": "Floor 5000 × suffix source records / total source records, then add one to the largest fractional remainders until the total is 5000.",
        "allocation_tie_break": "Listed source-manifest suffix order.",
        "rng": "Python random.Random(69); within-suffix source-order ranks, then final row shuffle.",
        "cell_order": "Listed source-manifest krt order.",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)), "records": total,
            "sha256": digest.hexdigest(), "manifest_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        },
        "exporter": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "cells": [
            {"krt": suffix, "source_records": populations[suffix], "selected": quotas[suffix]}
            for suffix in suffixes
        ],
        "source_indices_zero_based_in_output_order": [record[0] for record in selected],
        "output": {
            "path": str(OUTPUT.relative_to(ROOT)), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_bytes(payload)
    temp.replace(OUTPUT)
    output_metadata = OUTPUT.with_suffix(".manifest.json")
    temp_metadata = output_metadata.with_suffix(".json.tmp")
    temp_metadata.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_metadata.replace(output_metadata)
    print(f"Exported {SIZE:,} unique tasks to {OUTPUT.relative_to(ROOT)} (seed {SEED}).")
    print("Proportional suffix counts:", json.dumps(quotas))


if __name__ == "__main__":
    export()
