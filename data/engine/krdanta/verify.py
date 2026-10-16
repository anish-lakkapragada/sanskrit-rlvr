#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Verify the full array, every omission, engine answers, and prompt fairness."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from vidyut.prakriya import Vyakarana

from common import (ENGINE_OPTIONS, OUTPUT, ROOT, SOURCE_SHA256, SUFFIXES, TEMPLATE,
                    VIDYUT_VERSION, deva, derive_forms, load_entries, morphology,
                    prompt_conflicts, render_task, require, root_record, sha256, valid_gold)


def verify(output, rederive=False):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["source"]["sha256"] == SOURCE_SHA256, "Source pin changed")
    require(manifest["engine"]["version"] == VIDYUT_VERSION and manifest["engine"]["options"] == ENGINE_OPTIONS,
            "Engine pin changed")
    require(manifest["scope"]["krt"] == list(SUFFIXES), "Suffix scope changed")
    require(manifest["prompt"]["sha256"] == sha256(TEMPLATE), "Prompt changed; regenerate")
    for path, digest in manifest["generator"].items():
        require(sha256(ROOT / path) == digest, f"Generator changed: {path}")
    for name, info in manifest["files"].items():
        require(sha256(output / name) == info["sha256"] and (output / name).stat().st_size == info["bytes"],
                f"Export checksum/size mismatch: {name}")
    rows = json.loads((output / "full.json").read_text(encoding="utf-8"))
    entries = load_entries()
    by_code = {e.code: e for e in entries}
    by_id = {r["id"]: r for r in rows}
    require(len(rows) == len(by_id) == manifest["counts"]["full"], "Duplicate IDs/count mismatch")
    reason_by_id = {}
    for reason, ids in manifest["exclusions"].items():
        require(len(ids) == manifest["counts"]["excluded"][reason], "Exclusion count mismatch")
        for task_id in ids:
            require(task_id not in by_id and task_id not in reason_by_id, "Overlapping exclusions")
            reason_by_id[task_id] = reason
    grid = [f"krdanta:{e.code}:{k}" for e in entries for k in SUFFIXES]
    require(set(grid) == set(by_id) | set(reason_by_id), "Missing or extra candidate")
    require([task_id for task_id in grid if task_id in by_id] == list(by_id), "Incorrect record order")
    prompt_digest = hashlib.sha256()
    for row in rows:
        require(set(row) == {"id", "dhatu", "morphology", "gold_slp1", "gold_devanagari"}, "Unexpected row schema")
        e = by_code[row["dhatu"]["code"]]
        krt = row["morphology"]["krt"]
        require(row["id"] == f"krdanta:{e.code}:{krt}", "ID/request mismatch")
        require(row["dhatu"] == root_record(e), f"Root metadata mismatch: {row['id']}")
        require(row["morphology"] == morphology(krt), "Morphology mismatch")
        require(valid_gold(row["gold_slp1"]), f"Invalid gold: {row['id']}")
        require(row["gold_devanagari"] == [deva(f) for f in row["gold_slp1"]], "Transliteration mismatch")
        prompt = render_task(row)
        require("{" not in prompt and "}" not in prompt, "Unfilled template")
        prompt_digest.update(json.dumps([row["id"], prompt], ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
    require(prompt_digest.hexdigest() == manifest["prompt"]["rendered_sequence_sha256"], "Rendered prompts changed")
    require(not prompt_conflicts(rows)[0], "Conflicting gold for identical prompts")
    require(dict(Counter(r["morphology"]["krt"] for r in rows)) == manifest["counts"]["per_suffix"], "Suffix counts mismatch")
    if rederive:
        # Enable histories to exercise a different engine path from generation.
        engine = Vyakarana(**{**ENGINE_OPTIONS, "log_steps": True})
        before_conflict_filter = []
        for index, e in enumerate(entries, 1):
            for k in SUFFIXES:
                task_id = f"krdanta:{e.code}:{k}"
                m = morphology(k)
                forms = derive_forms(engine, e, m)
                if task_id in by_id:
                    require(forms == by_id[task_id]["gold_slp1"], f"Rederivation mismatch: {task_id}")
                    before_conflict_filter.append(by_id[task_id])
                else:
                    reason = reason_by_id[task_id]
                    if reason == "no_forms":
                        require(not forms, f"Answerable task omitted: {task_id}")
                    elif reason == "invalid_gold_encoding":
                        require(forms and not valid_gold(forms), f"Valid gold omitted: {task_id}")
                    else:
                        require(reason == "ambiguous_prompt" and valid_gold(forms), "Invalid exclusion")
                        before_conflict_filter.append(dict(id=task_id, dhatu=root_record(e), morphology=m,
                                                           gold_slp1=forms, gold_devanagari=[deva(f) for f in forms]))
            if index % 500 == 0:
                print(f"Rederived {index}/{len(entries)} roots", flush=True)
        require(prompt_conflicts(before_conflict_filter)[0] == manifest["exclusions"]["ambiguous_prompt"],
                "Prompt-conflict exclusions do not reproduce")
    report = dict(passed=True, records=len(rows), candidate_requests=len(grid), rederived=rederive,
                  checks=["hashes", "source_metadata", "complete_grid_accounting", "unique_ids_and_order",
                          "gold_roundtrips", "every_prompt_rendered", "prompt_gold_consistency"])
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--rederive", action="store_true")
    args = parser.parse_args()
    verify(args.output, args.rederive)
