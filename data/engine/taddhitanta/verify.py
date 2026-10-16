#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Verify the full base × 175-suffix grid, with optional complete rederivation."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from common import (OUTPUT, ROOT, SUFFIXES, TEMPLATE, classify, finish_source_audits,
                    iter_derivations, load_bases, make_record, nominal, render_task,
                    suffix_inventory, inventory as shared_source, code_files, engine_metadata)


def verify(output=OUTPUT, rederive=False, workers=4):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text())
    nominal.require(manifest["generation_complete"] and manifest["schema_version"] == 2, "Expected shared-inventory v2 export; older exports must be regenerated")
    nominal.require(manifest["dataset"] == "vp-taddhitanta-shared-nominals-v2", "Wrong dataset")
    nominal.require(manifest["scope"]["suffixes"] == list(SUFFIXES) and
                    manifest["scope"]["suffix_filter"] is None and manifest["scope"]["meaning_filter"] is None and
                    manifest["scope"]["pilot_exclusions_applied"] is False, "Unexpected scope restriction")
    nominal.require(manifest["engine"]["version"] == nominal.VIDYUT_VERSION and
                    manifest["engine"]["options"] == nominal.ENGINE_OPTIONS and manifest["engine"]["artha"] is None,
                    "Engine configuration changed")
    expected_engine = engine_metadata()
    actual_engine = json.loads(json.dumps(manifest["engine"]))
    # Compiler versions are provenance, not part of the task definition.
    for item in (expected_engine, actual_engine):
        item["compatibility_build"].pop("rustc", None)
    nominal.require(actual_engine == expected_engine, "Compatibility adapter changed")
    expected_code = {p.resolve().relative_to(ROOT).as_posix() for p in code_files()}
    nominal.require(set(manifest["generator"]) == expected_code, "Wrong generator inventory")
    for name, digest in manifest["generator"].items():
        nominal.require(nominal.sha256(ROOT / name) == digest, f"Generator changed: {name}")
    nominal.require(manifest["prompt"]["path"] == TEMPLATE.relative_to(ROOT).as_posix() and
                    nominal.sha256(TEMPLATE) == manifest["prompt"]["sha256"], "Prompt changed")
    nominal.require(set(manifest["files"]) == {"full.json", "attempts.json", "bases.json", "source_rows.json", "suffixes.json"},
                    "Wrong artifact inventory")
    for name, info in manifest["files"].items():
        path = output / name
        nominal.require(path.stat().st_size == info["bytes"] and nominal.sha256(path) == info["sha256"],
                        f"Artifact changed: {name}")
    entries, source_audits, inventory = load_bases()
    expected_source = {**shared_source.source_metadata(), **inventory}
    nominal.require(manifest["source"] == expected_source, "Source inventory changed")
    nominal.require(list(nominal.iter_array(output / "suffixes.json")) == suffix_inventory(), "Suffix inventory changed")
    tasks = nominal.iter_array(output / "full.json")
    attempts = nominal.iter_array(output / "attempts.json")
    bases = nominal.iter_array(output / "bases.json")
    derived = iter_derivations(entries, workers, log_steps=True) if rederive else None
    exported, totals, variants = Counter(), Counter(), Counter()
    per_suffix = {s: Counter() for s in SUFFIXES}
    digest = hashlib.sha256()
    started = time.monotonic()
    for index, entry in enumerate(entries, 1):
        attempt = next(attempts, None)
        nominal.require(attempt is not None and attempt.get("base_id") == entry["id"], f"Missing base audit: {entry['id']}")
        nominal.require(set(attempt) == {"base_id", "exported", "no_forms", "invalid_gold_encoding", "engine_error"},
                        "Invalid audit schema")
        statuses, details = {}, {}
        for status in ("exported", "no_forms", "invalid_gold_encoding", "engine_error"):
            suffix_ids = []
            for value in attempt[status]:
                suffix = value if isinstance(value, str) else value["suffix"]
                nominal.require(suffix not in statuses, "Duplicate attempted coordinate")
                statuses[suffix] = status
                details[suffix] = value
                suffix_ids.append(suffix)
            nominal.require(suffix_ids == sorted(suffix_ids), "Unordered suffix audit")
        nominal.require(set(statuses) == set(SUFFIXES), f"Incomplete 175-suffix audit: {entry['id']}")
        if rederive:
            pid, result = next(derived)
            nominal.require(pid == entry["id"] and [r[0] for r in result] == list(SUFFIXES), "Rederivation grid changed")
            reference = {suffix: (forms, error) for suffix, forms, error in result}
        for suffix in SUFFIXES:
            status = statuses[suffix]
            totals[status] += 1
            per_suffix[suffix][status] += 1
            forms, error = [], None
            if status == "exported":
                row = next(tasks, None)
                nominal.require(row is not None and row.get("id") == f"{entry['id']}:{suffix}", "Missing/out-of-order task")
                forms = row["gold_slp1"]
                nominal.require(nominal.valid_gold(forms) and row == make_record(entry, suffix, forms),
                                f"Invalid task/gold: {row['id']}")
                exported[entry["id"]] += 1
                variants[str(len(forms))] += 1
                digest.update((nominal.compact([row["id"], render_task(row)]) + "\n").encode())
            elif status == "invalid_gold_encoding":
                item = details[suffix]
                nominal.require(set(item) == {"suffix", "forms_slp1"}, "Invalid encoding audit schema")
                forms = item["forms_slp1"]
                nominal.require(forms and not nominal.valid_gold(forms), "Incorrect encoding exclusion")
            elif status == "engine_error":
                item = details[suffix]
                nominal.require(set(item) == {"suffix", "error"} and set(item["error"]) == {"type", "message"},
                                "Invalid error audit schema")
                error = item["error"]
            if rederive:
                actual_forms, actual_error = reference[suffix]
                nominal.require(classify(actual_forms, actual_error) == status and actual_forms == forms and actual_error == error,
                                f"Derivation changed: {entry['id']}:{suffix}")
        expected_base = {**entry, "candidate_tasks": len(SUFFIXES), "exported_tasks": exported[entry["id"]]}
        nominal.require(next(bases, None) == expected_base, "Base inventory/count changed")
        if index % 2000 == 0 or index == len(entries):
            print(f"Verified {index:,}/{len(entries):,} bases; {index * len(SUFFIXES):,} requests; "
                  f"{totals['exported']:,} tasks; {time.monotonic() - started:.1f}s", flush=True)
    for iterator in (tasks, attempts, bases):
        nominal.require(next(iterator, None) is None, "Unexpected extra record")
    if rederive:
        nominal.require(next(derived, None) is None, "Unexpected extra derivation")
    nominal.require(digest.hexdigest() == manifest["prompt"]["rendered_sequence_sha256"], "Hydrated prompt sequence changed")
    source_counts = finish_source_audits(entries, source_audits, exported)
    saved_audits = nominal.iter_array(output / "source_rows.json")
    for row in source_audits:
        nominal.require(next(saved_audits, None) == row, f"Source row changed: {row['mw_id']}")
    nominal.require(next(saved_audits, None) is None, "Unexpected source row")
    counts = {"bases": len(entries), "suffixes": len(SUFFIXES), "candidates": len(entries) * len(SUFFIXES),
              "full": totals["exported"], "no_forms": totals["no_forms"],
              "invalid_gold_encoding": totals["invalid_gold_encoding"], "engine_errors": totals["engine_error"],
              "per_suffix": {s: {k: per_suffix[s][k] for k in ("exported", "no_forms", "invalid_gold_encoding", "engine_error")}
                             for s in SUFFIXES},
              "gold_forms_per_task": dict(variants),
              "tasks_per_base": dict(Counter(str(exported[e["id"]]) for e in entries)), "source_rows": source_counts}
    nominal.require(sum(totals.values()) == counts["candidates"] and source_counts["new_unique_tasks"] == counts["full"],
                    "Incomplete grid/source ownership")
    nominal.require(counts == manifest["counts"], "Manifest counts changed")
    print(f"PASS: {counts['candidates']:,} requests; {counts['full']:,} tasks; rederived={rederive}", flush=True)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--rederive", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    verify(args.output, args.rederive, args.workers)
