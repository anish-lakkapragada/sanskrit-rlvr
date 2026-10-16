#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Bounded shared-input checks; never generate or replace the full datasets."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.nominal_stems import inventory
from data.engine.subanta import common as subanta
from data.engine.taddhitanta import common as taddhita

OUTPUT = ROOT / "data/datasets/nominal-preflight"
REFERENCES = ROOT / "data/datasets/taddhitanta/pilot/reference_checks.json"
ANCHORS = {"cUqA", "mAyA", "samA", "suparRA", "vinatA", "vAqavA", "dattA", "gopI",
           "lakzmI", "devI", "deva", "guru", "gurvI", "aSva", "go", "nO", "strI", "mAtf",
           "pfTu", "mfdu", "rAjan", "yogin", "manas", "yaSas", "loman"}


def select(entries, size):
    subanta.require(64 <= size <= 256, "Preflight is bounded to 64–256 inputs")
    selected = {e["nominal_id"]: e for e in entries if e["stem"] in ANCHORS}
    ranked = sorted(entries, key=lambda e: hashlib.sha256(e["nominal_id"].encode()).hexdigest())
    groups = set()
    for entry in ranked:
        group = (entry["linga"], entry["is_nyap"], entry["stem"][-1])
        if group not in groups:
            selected[entry["nominal_id"]] = entry
            groups.add(group)
    subanta.require(len(selected) <= size, "Sample too small for anchors and stem/gender strata")
    for entry in ranked:
        if len(selected) >= size:
            break
        selected[entry["nominal_id"]] = entry
    return sorted(selected.values(), key=lambda e: e["nominal_id"])


def reference_checks(binary):
    refs = json.loads(REFERENCES.read_text())
    requests = []
    for r in refs:
        requests.append({k: r[k] for k in ("id", "stem", "is_nyap", "suffix", "artha")})
        requests[-1]["gender"] = "Stri" if r["is_nyap"] else "Pum"
    for stem, expected, rule in [("suparRA", "sOparReya", "4_1_120"), ("vinatA", "vEnateya", "4_1_120"),
                                 ("vAqavA", "vAqaveya", "4_1_120"), ("dattA", "dAtteya", "4_1_121"),
                                 ("gopI", "gOpeya", "4_1_121")]:
        request = dict(id=f"feminine:{stem}:Qak", stem=stem, is_nyap=True,
                       gender="Stri", suffix="Qak", artha="TasyaApatyam")
        requests.append(request)
        refs.append({**request, "expected": [expected], "evidence": f"kashika_4_1.rs::sutra_{rule}"})
    results = taddhita.adapter.derive(binary, requests)
    subanta.require(results == taddhita.adapter.derive(binary, requests, log_steps=True),
                    "Reference results depend on logging")
    checks = []
    for ref, request, result in zip(refs, requests, results):
        passed = result["forms"] == ref["expected"] and result["error"] is None
        known = (ref["stem"] in {"pfTu", "mfdu"} and ref["suffix"] == "aR"
                 and ref["artha"] == "TasyaBhava" and result["forms"] == [] and result["error"] is None)
        subanta.require(passed or known, f"Unexpected reference failure: {request['id']}: {result}")
        checks.append({**request, "expected": ref["expected"], "actual": result["forms"],
                       "passed": passed, "known_explicit_meaning_limitation": known,
                       "evidence": ref["evidence"]})
    return checks


def run(output=OUTPUT, size=128):
    entries, _ = inventory.load()
    selected = select(entries, size)
    print(f"Shared inventory: {len(entries):,} stem–gender inputs; preflight sample: {len(selected)}", flush=True)
    sub_counts, tad_counts = Counter(), Counter()
    digest = hashlib.sha256()
    for e in selected:
        entry = {**e, "id": subanta.paradigm_id((e["stem"], e["is_nyap"], e["linga"]))}
        result = subanta.derive_paradigm(entry)
        subanta.require(result == subanta.derive_paradigm(entry, log_steps=True), "Subanta logging mismatch")
        subanta.require(len(result) == 24, "Incomplete subanta grid")
        for case, number, forms, reason in result:
            sub_counts[reason or "exported"] += 1
            if not reason:
                task = subanta.make_record(entry, case, number, forms)
                digest.update((subanta.compact([task, subanta.render_task(task)]) + "\n").encode())
    print(f"Subanta: {sum(sub_counts.values()):,} coordinates checked twice", flush=True)
    tad_entries = [{**e, "id": taddhita.base_id(e["stem"], e["is_nyap"], e["linga"])} for e in selected]
    # Also exercise deterministic multi-process batching against serial replay.
    results = list(taddhita.iter_derivations(tad_entries, workers=2))
    replay = list(taddhita.iter_derivations(tad_entries, workers=1, log_steps=True))
    subanta.require(results == replay, "Taddhitanta logging/worker-count mismatch")
    for entry, (pid, result) in zip(tad_entries, results):
        subanta.require(pid == entry["id"] and [r[0] for r in result] == list(taddhita.SUFFIXES),
                        "Incomplete taddhitanta grid")
        for suffix, forms, error in result:
            status = taddhita.classify(forms, error)
            tad_counts[status] += 1
            if status == "exported":
                task = taddhita.make_record(entry, suffix, forms)
                prompt = taddhita.render_task(task)
                subanta.require(entry["gender"] in prompt, "Missing source gender in prompt")
                digest.update((subanta.compact([task, prompt]) + "\n").encode())
    subanta.require(not tad_counts["engine_error"] and not tad_counts["invalid_gold_encoding"],
                    "Taddhitanta engine/encoding failures")
    subanta.require(not sub_counts["invalid_gold_encoding"], "Subanta encoding failures")
    binary, metadata = taddhita.adapter.prepare()
    refs = reference_checks(binary)
    report = {
        "scope": "Bounded adapter checks only; full datasets were not regenerated.",
        "source": inventory.source_metadata(), "sample_size": len(selected),
        "sampling": "Named regression anchors, one per gender/constructor/final-letter stratum, then SHA256-ranked fill. Not a quality estimate.",
        "subanta": {"attempts": sum(sub_counts.values()), "outcomes": dict(sub_counts)},
        "taddhitanta": {"attempts": sum(tad_counts.values()), "suffixes": len(taddhita.SUFFIXES),
                       "outcomes": dict(tad_counts)},
        "logging_and_worker_replay_identical": True,
        "reference_checks": {"total": len(refs), "passed": sum(r["passed"] for r in refs),
                             "known_explicit_meaning_limitations": sum(r["known_explicit_meaning_limitation"] for r in refs)},
        "limitation": "VP 0.4.0 still returns no form for pfTu/mfdu + aR with explicit TasyaBhava. The full task grid uses artha=null. This patch does not change those meaning rules.",
        "task_and_prompt_sequence_sha256": digest.hexdigest(), "engine": metadata,
        "code": {p.relative_to(ROOT).as_posix(): subanta.sha256(p)
                 for p in [Path(__file__), *taddhita.code_files(), Path(subanta.__file__).with_name("generate.py")]},
        "historical_reference_sha256": subanta.sha256(REFERENCES),
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    subanta.write_array(output / "inputs.json", selected)
    subanta.write_array(output / "reference_checks.json", refs)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("subanta", "taddhitanta", "reference_checks")}, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--sample-size", type=int, default=128)
    args = parser.parse_args()
    run(args.output, args.sample_size)
