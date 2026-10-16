#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Verify every exported task and source-row audit; optionally rederive the grid."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from common import (CASES, ENGINE_OPTIONS, NUMBERS, OUTPUT, ROOT, SOURCE, SOURCE_REVISION,
                    SOURCE_SHA256, TEMPLATE, VIDYUT_VERSION, compact, coordinates,
                    derive_paradigm, finish_audits, iter_array, make_record,
                    load_stems, render_task, require, sha256, source_counts,
                    code_files, shared_source_metadata,
                    valid_gold)


def verify(output=OUTPUT, rederive=False):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["generation_complete"] and manifest["schema_version"] == 2, "Expected shared-inventory v2 export; older exports must be regenerated")
    require(manifest["dataset"] == "vp-subanta-shared-nominals-v2", "Wrong dataset")
    require(manifest["source"] == shared_source_metadata(), "Wrong shared source")
    require(manifest["engine"]["version"] == VIDYUT_VERSION and
            manifest["engine"]["options"] == ENGINE_OPTIONS, "Wrong engine")
    require(manifest["scope"]["cases"] == list(CASES) and
            manifest["scope"]["numbers"] == list(NUMBERS), "Wrong grid")
    expected_code = {p.resolve().relative_to(ROOT).as_posix() for p in code_files()}
    require(set(manifest["generator"]) == expected_code, "Wrong generator files")
    for name, expected in manifest["generator"].items():
        require(sha256(ROOT / name) == expected, f"Generator changed: {name}")
    require(manifest["prompt"]["path"] == TEMPLATE.relative_to(ROOT).as_posix() and
            sha256(TEMPLATE) == manifest["prompt"]["sha256"], "Prompt changed")
    require(set(manifest["files"]) == {"full.json", "stems.json", "source_rows.json", "excluded_tasks.json"},
            "Wrong artifact inventory")
    for name, expected in manifest["files"].items():
        path = output / name
        require(path.stat().st_size == expected["bytes"] and sha256(path) == expected["sha256"],
                f"Artifact changed: {name}")

    entries, audits = load_stems()
    exclusions = list(iter_array(output / "excluded_tasks.json"))
    rejected = {row["id"]: row for row in exclusions}
    require(len(rejected) == len(exclusions), "Duplicate exclusions")
    seen_rejections = set()
    exported, genders, variants = Counter(), Counter(), Counter()
    rows = iter_array(output / "full.json")
    digest = hashlib.sha256()
    started = time.monotonic()
    total = 0
    for index, entry in enumerate(entries, 1):
        derived = derive_paradigm(entry, log_steps=True) if rederive else [
            (case, number, None, None) for case, number in coordinates()]
        for case, number, forms, reason in derived:
            task_id = f"{entry['id']}:{case}:{number}"
            if task_id in rejected:
                item = rejected[task_id]
                require(set(item) == {"id", "reason", "engine_forms_slp1"}, f"Bad exclusion: {task_id}")
                require(item["reason"] in {"no_forms", "invalid_gold_encoding"}, "Unknown exclusion reason")
                require((not item["engine_forms_slp1"] if item["reason"] == "no_forms"
                         else bool(item["engine_forms_slp1"]) and not valid_gold(item["engine_forms_slp1"])),
                        f"Incorrect exclusion reason: {task_id}")
                if rederive:
                    require(item == {"id": task_id, "reason": reason, "engine_forms_slp1": forms},
                            f"Excluded derivation changed: {task_id}")
                seen_rejections.add(task_id)
                continue
            row = next(rows, None)
            require(row is not None and row.get("id") == task_id, f"Missing/out-of-order task: {task_id}")
            require(valid_gold(row["gold_slp1"]), f"Invalid gold: {task_id}")
            require(row == make_record(entry, case, number, row["gold_slp1"]), f"Invalid record: {task_id}")
            if rederive:
                require(reason is None and row["gold_slp1"] == forms, f"Derivation changed: {task_id}")
            digest.update((compact([task_id, render_task(row)]) + "\n").encode("utf-8"))
            exported[entry["id"]] += 1
            genders[entry["linga"]] += 1
            variants[str(len(row["gold_slp1"]))] += 1
            total += 1
        if index % 5000 == 0 or index == len(entries):
            print(f"Verified {index:,}/{len(entries):,} stem–gender pairs; {total:,} tasks; "
                  f"{time.monotonic() - started:.1f}s", flush=True)
    require(next(rows, None) is None, "Unexpected extra task")
    require(seen_rejections == set(rejected), "Unknown excluded tasks")
    require(digest.hexdigest() == manifest["prompt"]["rendered_sequence_sha256"], "Hydrated prompts changed")
    expected_stems = [{**e, "candidate_tasks": 24, "exported_tasks": exported[e["id"]]} for e in entries]
    require(list(iter_array(output / "stems.json")) == expected_stems, "Stem inventory changed")
    finish_audits(entries, audits, exported)
    actual_audits = iter_array(output / "source_rows.json")
    for expected in audits:
        require(next(actual_audits, None) == expected, f"Source audit changed: {expected['mw_id']}")
    require(next(actual_audits, None) is None, "Unexpected extra source row")
    counts = {
        "stem_gender_pairs": len(entries), "candidates": len(entries) * 24, "full": total,
        "engine_errors": 0, "excluded_tasks": len(exclusions),
        "excluded_by_reason": dict(Counter(row["reason"] for row in exclusions)),
        "per_gender": dict(genders), "gold_forms_per_task": dict(variants), "source_rows": source_counts(audits),
    }
    require(total + len(exclusions) == counts["candidates"], "Grid is incomplete")
    require(counts["source_rows"]["new_unique_tasks"] == total, "Source ownership mismatch")
    require(counts == manifest["counts"], "Manifest counts differ")
    print(f"PASS: {total:,} tasks, {len(audits):,} source rows; rederived={rederive}", flush=True)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--rederive", action="store_true", help="Rederive all candidates with VP history enabled")
    args = parser.parse_args()
    verify(args.output, args.rederive)
