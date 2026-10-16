"""Export 5,000 distinct tinanta tasks balanced over 190 valid cells, seed 69.

Run from the repository root: python3 data/engine/tinanta/export_benchmark.py
Source JSON objects and their complete accepted answer sets are preserved.
"""

from collections import Counter
import hashlib
from itertools import product
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/datasets/tinanta/full.json"
OUTPUT = ROOT / "data/benchmark/tinanta/tinanta.json"
AXES = ("lakara", "prayoga", "purusha", "vacana")
SEED = 69
SIZE = 5000


def source_rows(digest):
    """Stream the generated array, retaining original object bytes and indices."""
    with SOURCE.open("rb") as source:
        opening = next(source)
        assert opening == b"[\n"
        digest.update(opening)
        for index, line in enumerate(source):
            digest.update(line)
            raw = line.strip()
            if raw == b"]":
                assert not source.read(), "Trailing source content"
                return
            raw = raw.removesuffix(b",")
            yield index, json.loads(raw), raw
    raise ValueError("Missing closing source array bracket")


def coordinate(row):
    return tuple(row["morphology"][axis] for axis in AXES)


def export():
    metadata_bytes = SOURCE.with_name("manifest.json").read_bytes()
    metadata = json.loads(metadata_bytes)
    assert metadata["generation_complete"] and not metadata["has_engine_errors"]
    cells = [
        cell for cell in product(*(metadata["coordinate_space"][axis] for axis in AXES))
        if cell[1] != "Bhave" or cell[2:] == ("Prathama", "Eka")
    ]
    assert len(cells) == len(set(cells)) == 190

    # Exclusions leave slightly different populations per cell; count the actual
    # eligible rows before drawing uniform source-order ranks within each cell.
    populations, source_digest = Counter(), hashlib.sha256()
    for _, row, _ in source_rows(source_digest):
        populations[coordinate(row)] += 1
    expected_hash = metadata["files"]["full.json"]["sha256"]
    assert source_digest.hexdigest() == expected_hash
    assert set(populations) == set(cells)
    assert sum(populations.values()) == metadata["counts"]["full"]

    rng = random.Random(SEED)
    base, remainder = divmod(SIZE, len(cells))
    extra = set(rng.sample(cells, remainder))
    quotas = {cell: base + (cell in extra) for cell in cells}
    ranks = {cell: set(rng.sample(range(populations[cell]), quotas[cell])) for cell in cells}
    observed, second_digest, selected = Counter(), hashlib.sha256(), []
    for index, row, raw in source_rows(second_digest):
        cell = coordinate(row)
        if observed[cell] in ranks[cell]:
            assert row["status"] == "ok" and not row["warnings"]
            assert row["gold_slp1"] and row["gold_devanagari"]
            selected.append((index, cell, row["id"], raw))
        observed[cell] += 1
    assert second_digest.hexdigest() == expected_hash, "Source changed during export"
    assert observed == populations
    assert len(selected) == len({record[2] for record in selected}) == SIZE
    assert Counter(record[1] for record in selected) == Counter(quotas)
    rng.shuffle(selected)
    payload = b"[\n" + b",\n".join(record[3] for record in selected) + b"\n]\n"
    assert len(json.loads(payload)) == SIZE

    manifest = {
        "dataset": "tinanta", "records": SIZE, "seed": SEED, "replacement": False,
        "method": "Stratified uniform sampling over 190 eligible lakara × prayoga × purusha × vacana cells.",
        "allocation": "26 per cell plus one extra in 60 cells selected with the seeded RNG.",
        "eligibility": "Use the filtered full dataset; Bhave is third-person singular only.",
        "rng": "Python random.Random(69); extra cells, within-cell ranks, then final row shuffle.",
        "cell_order": "Listed source-manifest lakara, prayoga, purusha, vacana order; invalid Bhave cells omitted.",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)), "records": sum(populations.values()),
            "sha256": expected_hash, "manifest_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        },
        "exporter": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "cells": [
            {**dict(zip(AXES, cell)), "source_records": populations[cell], "selected": quotas[cell]}
            for cell in cells
        ],
        "selected_by_axis": {
            axis: dict(Counter(record[1][i] for record in selected)) for i, axis in enumerate(AXES)
        },
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
    print("Cell sizes: 130 × 26 and 60 × 27; all source records and answer sets preserved.")
    print("By construction:", json.dumps(manifest["selected_by_axis"]["prayoga"]))


if __name__ == "__main__":
    export()
