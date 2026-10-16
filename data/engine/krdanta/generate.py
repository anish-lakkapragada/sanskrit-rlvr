#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Export every answerable, prompt-consistent request in the reviewed krt scope."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import time

from vidyut.prakriya import Krt, Vyakarana

from common import (ENGINE_OPTIONS, OUTPUT, ROOT, SDIST_SHA256, SDIST_URL, SOURCE,
                    SOURCE_SHA256, SUFFIXES, TEMPLATE, VIDYUT_VERSION, enum_name,
                    load_entries, make_record, prompt_conflicts, render_task,
                    require, sha256, valid_gold, write_array)


def generate(output, overwrite=False):
    output = Path(output).resolve()
    names = ("full.json", "manifest.json")
    require(overwrite or not any((output / n).exists() for n in names),
            "Export already exists; use --output or --overwrite")
    entries = load_entries()
    engine = Vyakarana(**ENGINE_OPTIONS)
    records = []
    excluded = {"no_forms": [], "invalid_gold_encoding": [], "ambiguous_prompt": []}
    started = time.monotonic()
    for index, entry in enumerate(entries, 1):
        for krt in SUFFIXES:
            # Engine errors (including Rust panics) abort the build. Never publish
            # a purportedly complete dataset after silently skipping a failure.
            try:
                row = make_record(engine, entry, krt)
            except BaseException as exc:
                if isinstance(exc, Exception) or type(exc).__name__ == "PanicException":
                    raise RuntimeError(f"Engine failure at {entry.code}:{krt}") from exc
                raise
            if not row["gold_slp1"]:
                excluded["no_forms"].append(row["id"])
            elif not valid_gold(row["gold_slp1"]):
                excluded["invalid_gold_encoding"].append(row["id"])
            else:
                records.append(row)
        if index % 250 == 0 or index == len(entries):
            print(f"{index}/{len(entries)} roots; {len(records):,} answerable requests; "
                  f"{time.monotonic() - started:.1f}s", flush=True)
    conflicts, _ = prompt_conflicts(records)
    excluded["ambiguous_prompt"] = conflicts
    conflict_ids = set(conflicts)
    records = [row for row in records if row["id"] not in conflict_ids]
    candidates = len(entries) * len(SUFFIXES)
    require(len(records) + sum(map(len, excluded.values())) == candidates, "Incomplete grid")
    require(records, "No eligible tasks")
    # Hash the sequence of fully hydrated prompts without storing gold in them.
    prompt_digest = hashlib.sha256()
    for row in records:
        prompt_digest.update(json.dumps([row["id"], render_task(row)],
                                       ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".krdanta-build-", dir=output.parent) as temp:
        build = Path(temp)
        write_array(build / "full.json", records)
        code_files = [Path(__file__), Path(__file__).with_name("common.py")]
        manifest = {
            "schema_version": 1, "dataset": "vp-krdanta-reviewed-v1", "generation_complete": True,
            "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": SOURCE_SHA256,
                       "rows": 2259, "placeholders_excluded": 30, "roots": len(entries)},
            "engine": {"package": "vidyut", "version": VIDYUT_VERSION, "options": ENGINE_OPTIONS,
                       "request": "Pratipadika.krdanta(loaded_dhatu, Krt)",
                       "source_distribution_url": SDIST_URL, "source_distribution_sha256": SDIST_SHA256},
            "generator": {p.resolve().relative_to(ROOT).as_posix(): sha256(p) for p in code_files},
            "prompt": {"path": TEMPLATE.relative_to(ROOT).as_posix(), "sha256": sha256(TEMPLATE),
                       "rendered_sequence_sha256": prompt_digest.hexdigest(),
                       "sequence_format": "compact UTF-8 JSON [id,prompt] plus newline for each row"},
            "scope": {
                "krt": list(SUFFIXES),
                "suffixes": {k: {"gloss": g, "licensing_rules": r} for k, (g, r) in SUFFIXES.items()},
                "excluded_suffixes": sorted(enum_name(k) for k in Krt.choices() if enum_name(k) not in SUFFIXES),
                "excluded_suffix_reason": "outside reviewed classical root-plus-suffix scope; not a claim of invalidity",
                "additional_prefixes": [], "additional_sanadi": [], "upapada": None, "krt_artha": None,
                "participle_defaults": {"krt": ["Satf", "SAnac"], "lakara": "Lat", "prayoga": "Kartari"},
                "outputs": "uninflected nominal stems and complete indeclinables",
                "fairness_checks": ["reviewed_suffix_scope", "lexical_prefixes_visible",
                                    "participle_defaults_visible", "nonempty_complete_engine_gold",
                                    "gold_transliteration_roundtrip", "no_identical_prompt_with_different_gold"],
                "limits": "Engine-backed formal derivations; not independent certification of every Sanskrit form or all 122 suffixes.",
            },
            "enumeration_order": "source code ascending, then krt in listed order",
            "gold_order": "sorted unique SLP1, with paired NFC Devanagari",
            "sampling": None, "splits": None,
            "counts": {
                "roots": len(entries), "suffixes": len(SUFFIXES), "candidates": candidates,
                "full": len(records), "engine_errors": 0,
                "excluded": {k: len(v) for k, v in excluded.items()},
                "per_suffix": {k: sum(row["morphology"]["krt"] == k for row in records) for k in SUFFIXES},
                "gold_forms_per_task": dict(sorted(Counter(str(len(r["gold_slp1"])) for r in records).items())),
                "roots_with_tasks": len({r["dhatu"]["code"] for r in records}),
                "tasks_with_prefixes": sum(bool(r["dhatu"]["prefixes"]) for r in records),
            },
            "exclusions": excluded,
            "files": {"full.json": {"sha256": sha256(build / "full.json"), "bytes": (build / "full.json").stat().st_size}},
        }
        (build / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name in names:  # Publish the manifest last, after the complete array.
            (build / name).replace(output / name)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2), flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    generate(args.output, args.overwrite)
