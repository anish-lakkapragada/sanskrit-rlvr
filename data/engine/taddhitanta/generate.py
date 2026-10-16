#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Attempt all 175 VP suffixes for each filtered shared stem–gender input."""

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from common import (JsonArrayWriter, OUTPUT, ROOT, SUFFIXES, TEMPLATE, classify,
                    finish_source_audits, iter_derivations, load_bases, make_record,
                    nominal, render_task, suffix_inventory, inventory as shared_source, code_files, engine_metadata)


def generate(output=OUTPUT, overwrite=False, workers=4):
    output = Path(output).resolve()
    names = ("full.json", "attempts.json", "bases.json", "source_rows.json", "suffixes.json", "manifest.json")
    nominal.require(overwrite or not any((output / n).exists() for n in names),
                    "Export already exists; use --overwrite or another --output")
    entries, audits, inventory = load_bases()
    print(f"{len(entries):,} inputs × {len(SUFFIXES)} suffixes = {len(entries) * len(SUFFIXES):,} requests", flush=True)
    exported, totals, variants = Counter(), Counter(), Counter()
    per_suffix = {s: Counter() for s in SUFFIXES}
    prompt_digest = hashlib.sha256()
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".taddhitanta-build-", dir=output.parent) as tmp:
        build = Path(tmp)
        results = iter_derivations(entries, workers)
        with JsonArrayWriter(build / "full.json") as full, JsonArrayWriter(build / "attempts.json") as attempts:
            for index, entry in enumerate(entries, 1):
                pid, derived = next(results)
                nominal.require(pid == entry["id"] and [r[0] for r in derived] == list(SUFFIXES), "Incomplete grid")
                audit = {"base_id": pid, "exported": [], "no_forms": [], "invalid_gold_encoding": [], "engine_error": []}
                for suffix, forms, error in derived:
                    status = classify(forms, error)
                    totals[status] += 1
                    per_suffix[suffix][status] += 1
                    if status == "exported":
                        row = make_record(entry, suffix, forms)
                        full.add(row)
                        prompt_digest.update((nominal.compact([row["id"], render_task(row)]) + "\n").encode())
                        exported[pid] += 1
                        variants[str(len(forms))] += 1
                        audit[status].append(suffix)
                    elif status == "no_forms":
                        audit[status].append(suffix)
                    elif status == "invalid_gold_encoding":
                        audit[status].append({"suffix": suffix, "forms_slp1": forms})
                    else:
                        audit[status].append({"suffix": suffix, "error": error})
                attempts.add(audit)
                if index % 2000 == 0 or index == len(entries):
                    print(f"{index:,}/{len(entries):,} bases; {index * len(SUFFIXES):,} attempted; "
                          f"{totals['exported']:,} tasks; {totals['engine_error']} errors; "
                          f"{time.monotonic() - started:.1f}s", flush=True)
            nominal.require(next(results, None) is None, "Unexpected derivations")
        candidates = len(entries) * len(SUFFIXES)
        nominal.require(sum(totals.values()) == candidates and totals["exported"] > 0, "Incomplete/empty export")
        nominal.require(totals["engine_error"] == 0, "Engine errors found; export was not published")
        source_counts = finish_source_audits(entries, audits, exported)
        nominal.require(source_counts["new_unique_tasks"] == totals["exported"], "Source ownership mismatch")
        nominal.write_array(build / "bases.json", ({**e, "candidate_tasks": len(SUFFIXES),
                            "exported_tasks": exported[e["id"]]} for e in entries))
        nominal.write_array(build / "source_rows.json", audits)
        nominal.write_array(build / "suffixes.json", suffix_inventory())
        code = code_files()
        manifest = {
            "schema_version": 2, "dataset": "vp-taddhitanta-shared-nominals-v2", "generation_complete": True,
            "source": {**shared_source.source_metadata(), **inventory},
            "engine": engine_metadata(),
            "generator": {p.resolve().relative_to(ROOT).as_posix(): nominal.sha256(p) for p in code},
            "prompt": {"path": TEMPLATE.relative_to(ROOT).as_posix(), "sha256": nominal.sha256(TEMPLATE),
                       "rendered_sequence_sha256": prompt_digest.hexdigest(),
                       "sequence_format": "compact UTF-8 JSON [id,prompt] plus newline per record"},
            "scope": {
                "suffixes": list(SUFFIXES), "suffix_filter": None, "meaning_filter": None,
                "headword_policy": "Use only shared-nominal-stems.json; do not re-read or union raw headwords.",
                "additional_inputs": None,
                "pilot_exclusions_applied": False,
                "output_policy": "Retain every nonempty, losslessly renderable engine result; audit all remaining attempted coordinates.",
                "task_identity": "stem + constructor + source gender + suffix; artha=null",
                "attempt_audit": "One row per base partitions all 175 suffixes into exported, no_forms, invalid_gold_encoding, engine_error.",
                "limits": "All 175 suffixes attempted. Engine-backed answers are not independent linguistic certification. Explicit-meaning coverage is not claimed.",
            },
            "enumeration_order": "base ID ascending, then suffix ID ascending",
            "gold_order": "sorted unique SLP1, aligned NFC Devanagari",
            "sampling": None, "splits": None,
            "counts": {"bases": len(entries), "suffixes": len(SUFFIXES), "candidates": candidates,
                       "full": totals["exported"], "no_forms": totals["no_forms"],
                       "invalid_gold_encoding": totals["invalid_gold_encoding"], "engine_errors": totals["engine_error"],
                       "per_suffix": {s: {k: per_suffix[s][k] for k in ("exported", "no_forms", "invalid_gold_encoding", "engine_error")}
                                      for s in SUFFIXES},
                       "gold_forms_per_task": dict(sorted(variants.items(), key=lambda p: int(p[0]))),
                       "tasks_per_base": dict(sorted(Counter(str(exported[e["id"]]) for e in entries).items(), key=lambda p: int(p[0]))),
                       "source_rows": source_counts},
            "files": {n: {"sha256": nominal.sha256(build / n), "bytes": (build / n).stat().st_size}
                      for n in names if n != "manifest.json"},
        }
        (build / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for name in names:
            (build / name).replace(output / name)
    print(json.dumps({k: v for k, v in manifest["counts"].items()
                      if k not in {"per_suffix", "gold_forms_per_task", "tasks_per_base"}}, indent=2), flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    result = generate(args.output, args.overwrite, args.workers)
    if result["counts"]["engine_errors"]:
        raise SystemExit("All inputs attempted; engine errors recorded in attempts.json")
