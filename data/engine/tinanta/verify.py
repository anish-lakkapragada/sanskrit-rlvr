#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Validate every exported record, optionally rederiving every answer with VP."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time

from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Vyakarana

from generate import (AXES, COORDINATES, ENGINE_OPTIONS, EXPECTED_CANDIDATES, EXPECTED_ELIGIBLE, OUTPUT, ROOT,
                      SOURCE_SHA256, VIDYUT_VERSION, enum_name, load_entries,
                      request, sha256, to_devanagari, make_record)
from data.engine.tinanta.common import (TEMPLATE, coordinate_exclusion, prompt_conflicts,
                                        render_task, valid_gold)


def records(path):
    """Read the generator's ordinary JSON arrays with bounded memory.

    Also enforces commas/brackets, so a malformed JSONL-like file cannot pass.
    """
    with path.open(encoding="utf-8") as f:
        first = f.readline()
        if first == "[]\n":
            if f.read().strip():
                raise ValueError(f"Trailing data in {path}")
            return
        if first != "[\n":
            raise ValueError(f"Unexpected JSON array opening in {path}")
        previous_had_comma = None
        for line in f:
            if line == "]\n":
                if previous_had_comma is not False or f.read().strip():
                    raise ValueError(f"Invalid JSON array ending in {path}")
                return
            if previous_had_comma is False:
                raise ValueError(f"Missing comma in {path}")
            text = line.rstrip("\n")
            previous_had_comma = text.endswith(",")
            if previous_had_comma:
                text = text[:-1]
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"Expected a record object in {path}")
            yield value
        raise ValueError(f"Unclosed array in {path}")


def verify(output: Path, rederive: bool, legacy_commit: str | None):
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"]["sha256"] == SOURCE_SHA256
    assert manifest["engine"]["version"] == VIDYUT_VERSION
    assert manifest["engine"]["options"] == ENGINE_OPTIONS
    assert manifest["coordinate_space"] == AXES
    assert manifest["generator"]["sha256"] == sha256(Path(__file__).with_name("generate.py"))
    assert manifest["eligibility_and_rendering"]["sha256"] == sha256(Path(__file__).with_name("common.py"))
    assert manifest["prompt"]["sha256"] == sha256(TEMPLATE)
    assert manifest["schema_version"] == 2
    assert set(manifest["files"]) == {"full.json", "excluded_tasks.json"}
    for filename, info in manifest["files"].items():
        path = output / filename
        assert path.stat().st_size == info["bytes"], filename
        assert sha256(path) == info["sha256"], filename
    legacy = {}
    if legacy_commit:
        for path in ["data/finetune/task-data/finetune.json", "data/finetune/task-data/validation.json"]:
            for row in json.loads(subprocess.check_output(["git", "show", f"{legacy_commit}:{path}"], cwd=ROOT)):
                assert row["id"] not in legacy
                legacy[row["id"]] = row
    legacy_total = len(legacy)
    legacy_excluded = 0
    exclusions = list(records(output / "excluded_tasks.json"))
    exclusion_map = {r["id"]: r["reason"] for r in exclusions}
    assert len(exclusions) == len(exclusion_map)
    exclusion_counts = Counter(r["reason"] for r in exclusions)
    seen_exclusions = set()
    ambiguous_rows = []
    diagnostic_engine = Vyakarana(**ENGINE_OPTIONS)
    # Deliberately retain derivation logging here, unlike the exporter.
    engine = Vyakarana(**{**ENGINE_OPTIONS, "log_steps": True}) if rederive else None
    all_rows = iter(records(output / "full.json"))
    counts = Counter({"ok": 0, "no_forms": 0, "error": 0})
    warnings = Counter()
    multiplicities = Counter()
    total = 0
    prompt_digest = hashlib.sha256()
    prompt_answers = {}
    per_lakara, per_prayoga = Counter(), Counter()
    started = time.monotonic()
    for root_index, entry in enumerate(load_entries(), 1):
        for coordinate in COORDINATES:
            task_id = ":".join((entry.code, *coordinate))
            reason = coordinate_exclusion(coordinate)
            if reason or task_id in exclusion_map:
                assert task_id in exclusion_map, task_id
                seen_exclusions.add(task_id)
                if reason:
                    assert exclusion_map[task_id] == reason
                else:
                    excluded_row = make_record(diagnostic_engine, entry, coordinate)
                    reason = exclusion_map[task_id]
                    if reason == "ambiguous_prompt":
                        assert valid_gold(excluded_row["gold_slp1"])
                        ambiguous_rows.append(excluded_row)
                    elif reason == "no_forms":
                        assert excluded_row["status"] == "no_forms"
                    else:
                        assert reason == "invalid_gold_encoding" and not valid_gold(excluded_row["gold_slp1"])
                legacy_excluded += legacy.pop(task_id, None) is not None
                continue
            row = next(all_rows)
            assert row["id"] == ":".join((entry.code, *coordinate)), row["id"]
            assert row["dhatu"] == {
                "code": entry.code, "aupadeshika": entry.dhatu.aupadeshika,
                "gana": enum_name(entry.dhatu.gana), "artha": entry.artha,
                "antargana": enum_name(entry.dhatu.antargana),
                "prefixes": list(entry.dhatu.prefixes),
                "sanadi": [enum_name(s) for s in entry.dhatu.sanadi]}, row["id"]
            assert row["morphology"] == dict(zip(AXES, coordinate)), row["id"]
            assert row["warnings"] == [], row["id"]
            assert row["status"] == "ok"
            gold = row["gold_slp1"]
            assert gold == sorted(set(gold)) and all(gold), row["id"]
            assert row["gold_devanagari"] == [to_devanagari(s) for s in gold], row["id"]
            for slp1, deva in zip(gold, row["gold_devanagari"]):
                assert transliterate(deva, Scheme.Devanagari, Scheme.Slp1) == slp1, row["id"]
            if row["status"] == "ok":
                assert gold and "error" not in row
            else:
                assert not gold
                if row["status"] == "error":
                    assert row["error"]["type"]
                else:
                    assert "error" not in row
            if engine is not None:
                assert row["status"] != "error", row["id"]
                fresh = sorted({p.text for p in engine.derive(request(entry, coordinate))})
                assert fresh == gold, row["id"]
            old = legacy.pop(row["id"], None)
            if old is not None:
                assert old["gold_slp1"] == gold, row["id"]
                assert old["gold_devanagari"] == row["gold_devanagari"], row["id"]
                assert all(row["dhatu"][k] == v for k, v in old["dhatu"].items()), row["id"]
            counts[row["status"]] += 1
            warnings.update(row["warnings"])
            multiplicities[len(gold)] += 1
            prompt = render_task(row)
            digest = hashlib.sha256(prompt.encode()).digest()
            answers = tuple(row["gold_devanagari"])
            assert prompt_answers.setdefault(digest, answers) == answers, row["id"]
            prompt_digest.update((json.dumps([row["id"], prompt], ensure_ascii=False,
                                            separators=(",", ":")) + "\n").encode())
            per_lakara[coordinate[0]] += 1
            per_prayoga[coordinate[1]] += 1
            total += 1
        if root_index % 200 == 0:
            print(f"Verified {total:,}/{manifest['counts']['full']:,} records; {time.monotonic() - started:.1f}s", flush=True)
    assert next(all_rows, None) is None
    assert total == manifest["counts"]["all"] == manifest["counts"]["full"]
    assert total + len(exclusions) == EXPECTED_CANDIDATES == manifest["counts"]["candidates"]
    assert EXPECTED_ELIGIBLE == manifest["counts"]["attempted"]
    assert seen_exclusions == set(exclusion_map)
    assert exclusion_counts == Counter(manifest["counts"]["excluded_by_reason"])
    assert len(exclusions) == manifest["counts"]["excluded_tasks"]
    assert set(prompt_conflicts(ambiguous_rows)) == {k for k, v in exclusion_map.items() if v == "ambiguous_prompt"}
    assert prompt_digest.hexdigest() == manifest["prompt"]["rendered_sequence_sha256"]
    assert all(v["ok"] == per_lakara[k] for k, v in manifest["by_lakara"].items())
    assert all(v["ok"] == per_prayoga[k] for k, v in manifest["by_prayoga"].items())
    assert counts == manifest["counts"]["status"]
    assert counts["ok"] == manifest["counts"]["answerable"]
    assert warnings == manifest["counts"]["warnings"]
    assert {str(k): v for k, v in sorted(multiplicities.items())} == manifest["counts"]["gold_forms_per_task"]
    assert not legacy, "Some archived task IDs were absent from the exhaustive export"
    assert counts["error"] == 0, "Engine errors remain in the export"
    report = {
        "passed": True, "all_records_checked": total,
        "all_records_rederived_with_log_steps": rederive,
        "legacy_commit": legacy_commit, "legacy_records_matched": legacy_total - legacy_excluded,
        "legacy_records_now_excluded": legacy_excluded,
        "status_counts": dict(counts), "warning_counts": dict(warnings),
        "checks": ["source_and_export_hashes", "all_expected_unique_ids_in_order", "root_metadata",
                   "complete_candidate_and_exclusion_accounting", "sorted_unique_gold", "all_gold_transliteration_roundtrips",
                   "answerable_status_counts", "manifest_counts", "no_invalid_bhave_coordinates",
                   "no_identical_prompt_with_different_gold", "hydrated_prompt_digest"],
        "manifest_sha256": sha256(output / "manifest.json"),
        "verifier_sha256": sha256(Path(__file__)),
    }
    print(json.dumps(report, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--rederive", action="store_true", help="Recompute every gold set with VP")
    parser.add_argument("--legacy-commit", help="Also compare the archived train/validation tasks")
    args = parser.parse_args()
    verify(args.output, args.rederive, args.legacy_commit)


if __name__ == "__main__":
    main()
