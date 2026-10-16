#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Export the complete supported MWlexnorm subanta grid, with source-row audits."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import time

from common import (CASES, ENGINE_OPTIONS, NUMBERS, OUTPUT, REASON_LABELS, ROOT,
                    SOURCE, SOURCE_REVISION, SOURCE_SHA256, TEMPLATE, VIDYUT_VERSION,
                    compact, derive_paradigm, finish_audits, make_record,
                    load_stems, render_task, require, sha256, source_counts,
                    code_files, shared_source_metadata,
                    write_array)


def generate(output=OUTPUT, overwrite=False):
    output = Path(output).resolve()
    names = ("full.json", "stems.json", "source_rows.json", "excluded_tasks.json", "manifest.json")
    require(overwrite or not any((output / name).exists() for name in names),
            "Export already exists; use --output or --overwrite")
    entries, audits = load_stems()
    exported = Counter()
    excluded = []
    per_gender, variants = Counter(), Counter()
    digest = hashlib.sha256()
    started = time.monotonic()

    def records():
        total = 0
        for index, entry in enumerate(entries, 1):
            for case, number, forms, reason in derive_paradigm(entry):
                if reason:
                    excluded.append({"id": f"{entry['id']}:{case}:{number}",
                                     "reason": reason, "engine_forms_slp1": forms})
                    continue
                row = make_record(entry, case, number, forms)
                digest.update((compact([row["id"], render_task(row)]) + "\n").encode("utf-8"))
                exported[entry["id"]] += 1
                per_gender[entry["linga"]] += 1
                variants[str(len(forms))] += 1
                total += 1
                yield row
            if index % 5000 == 0 or index == len(entries):
                print(f"{index:,}/{len(entries):,} stem–gender pairs; {total:,} tasks; "
                      f"{time.monotonic() - started:.1f}s", flush=True)

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".subanta-build-", dir=output.parent) as temp:
        build = Path(temp)
        write_array(build / "full.json", records())
        full = sum(exported.values())
        candidates = len(entries) * 24
        require(full and full + len(excluded) == candidates, "Incomplete or empty grid")
        finish_audits(entries, audits, exported)
        row_counts = source_counts(audits)
        require(row_counts["new_unique_tasks"] == full, "Source ownership mismatch")
        write_array(build / "stems.json", ({**e, "candidate_tasks": 24,
                    "exported_tasks": exported[e["id"]]} for e in entries))
        write_array(build / "source_rows.json", audits)
        write_array(build / "excluded_tasks.json", excluded)
        manifest = {
            "schema_version": 2, "dataset": "vp-subanta-shared-nominals-v2", "generation_complete": True,
            "source": shared_source_metadata(),
            "engine": {"package": "vidyut", "version": VIDYUT_VERSION, "options": ENGINE_OPTIONS,
                       "request": "Pada.Subanta(Pratipadika.basic/nyap(stem), Linga, Vibhakti, Vacana)"},
            "generator": {p.resolve().relative_to(ROOT).as_posix(): sha256(p) for p in code_files()},
            "prompt": {"path": TEMPLATE.relative_to(ROOT).as_posix(), "sha256": sha256(TEMPLATE),
                       "rendered_sequence_sha256": digest.hexdigest(),
                       "sequence_format": "compact UTF-8 JSON [id,prompt] plus newline for each row"},
            "scope": {
                "cases": list(CASES), "numbers": list(NUMBERS), "tasks_per_stem_gender": 24,
                "stem_classes": ["a/i/u/r vowel stems", "resolved feminine A/I/U stems",
                                 "polysyllabic masculine A", "masculine/neuter an/in",
                                 "as/is/us except vas/Iyas", "go/nau"],
                "input_policy": "Only shared-nominal-stems.json; reuse its resolved spellings and source genders.",
                "source_exclusion_reasons": "See shared-nominal-stems.manifest.json",
                "task_exclusion_reasons": {"no_forms": "VP produced no derivation.",
                                           "invalid_gold_encoding": "Gold cannot round-trip through Devanagari."},
                "deduplication": "Resolved SLP1 stem, basic/nyap constructor, gender, case, number; retain all MW IDs.",
                "row_counts": "exported_tasks includes shared tasks; new_unique_tasks assigns each task to its first source row.",
                "fairness_checks": ["reviewed_basic_stem_scope", "resolved_feminine_stem_visible",
                                    "no_hidden_constructor_conflict", "nonempty_complete_engine_gold",
                                    "gold_transliteration_roundtrip"],
                "limits": "Exhaustive within the adapter's supported scope, not all MWlexnorm entries. Engine-backed forms are not independently certified Sanskrit judgments.",
            },
            "enumeration_order": "paradigm ID ascending, then listed case and number order",
            "gold_order": "sorted unique SLP1, with paired NFC Devanagari",
            "sampling": None, "splits": None,
            "counts": {"stem_gender_pairs": len(entries), "candidates": candidates, "full": full,
                       "engine_errors": 0, "excluded_tasks": len(excluded),
                       "excluded_by_reason": dict(sorted(Counter(r["reason"] for r in excluded).items())),
                       "per_gender": dict(sorted(per_gender.items())),
                       "gold_forms_per_task": dict(sorted(variants.items(), key=lambda p: int(p[0]))),
                       "source_rows": row_counts},
            "files": {name: {"sha256": sha256(build / name), "bytes": (build / name).stat().st_size}
                      for name in names if name != "manifest.json"},
        }
        (build / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name in names:  # Publish the manifest last, after all complete arrays.
            (build / name).replace(output / name)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2), flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    generate(args.output, args.overwrite)
