#!/usr/bin/env python3
"""Independently reconstruct exported correction gold directly from VP history.

Does not call core.derive/collect_traces/project/repairs/propose. Uses core.grade
only as the system under test. No provider or network calls.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmarks.correction.core import grade
from misc.vp_cartesian_task import entries_by_code
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana

HERE = Path(__file__).resolve().parent


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deva(value):
    return unicodedata.normalize("NFC", transliterate(value, Scheme.Slp1, Scheme.Devanagari))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tasks = json.loads((HERE / "tasks.json").read_text())
    manifest = json.loads((HERE / "manifest.json").read_text())
    entries = entries_by_code()
    vp = Vyakarana(**manifest["vp_settings"])
    counts = Counter()
    assert len(tasks) == 200
    assert len({t["dhatu"]["code"] for t in tasks}) == 200
    assert len({t["dhatu"]["aupadeshika"] for t in tasks}) == 200
    for task in tasks:
        m = task["morphology"]
        ps = vp.derive(Pada.Tinanta(
            dhatu=entries[task["dhatu"]["code"]].dhatu,
            lakara=getattr(Lakara, m["lakara"]),
            prayoga=getattr(Prayoga, m["prayoga"]),
            purusha=getattr(Purusha, m["purusha"]),
            vacana=getattr(Vacana, m["vacana"])))
        direct_paths = {}
        for p in ps:
            seen, states, positions = Counter(), {}, {}
            for i, step in enumerate(p.history):
                pair = (repr(step.source).split(".")[-1], step.code)
                seen[pair] += 1
                key = (*pair, seen[pair])
                states[key] = [deva(term) for term in step.result if term]
                positions[key] = i
            requested_keys = [tuple(k) for k in task["checkpoint_keys"]]
            indices = [positions[key] for key in requested_keys]
            assert indices == sorted(set(indices)), task["id"]
            path = [states[key] for key in requested_keys] + [[deva(p.text)]]
            direct_paths[encoded(path)] = path
        paths = list(direct_paths.values())
        assert set(direct_paths) == {encoded(p) for p in task["valid_paths"]}
        assert len(ps) == task["vp_derivation_count"]
        counts["vp_derivations_inspected"] += len(ps)
        first = None
        for i in range(1, len(task["proposed"]) + 1):
            if not any(p[:i] == task["proposed"][:i] for p in paths):
                first = i
                break
        assert first == task["mutation"]["first_incorrect_step"]
        assert task["proposed"][-1] not in [p[-1] for p in paths]
        expected = [{"first_incorrect_step": first, "corrected_steps": [
            {"step": i + 1, "terms": p[i]} for i in range(first - 1, len(p))]}
            for p in paths if p[:first - 1] == task["proposed"][:first - 1]]
        assert {encoded(g) for g in expected} == {encoded(g) for g in task["accepted_answers"]}
        for answer in expected:
            assert grade(answer, task["accepted_answers"])
            assert grade(json.dumps(answer, ensure_ascii=False, indent=4), task["accepted_answers"])
            decomposed = unicodedata.normalize("NFD", json.dumps(answer, ensure_ascii=False))
            assert grade(decomposed, task["accepted_answers"])
            counts["gold_answers_checked"] += 1
        gold = expected[0]
        negatives = []
        bad = deepcopy(gold)
        bad["first_incorrect_step"] = float(first)
        negatives.append(bad)
        bad = deepcopy(gold)
        bad["first_incorrect_step"] = True
        negatives.append(bad)
        bad = deepcopy(gold)
        bad["corrected_steps"] = bad["corrected_steps"][:-1]
        negatives.append(bad)
        bad = deepcopy(gold)
        bad["corrected_steps"][0]["terms"][0] += "अ"
        negatives.append(bad)
        bad = deepcopy(gold)
        bad["corrected_steps"].reverse()
        negatives.append(bad)
        bad = deepcopy(gold)
        bad["explanation"] = "Extra key is forbidden."
        negatives.append(bad)
        negatives.append({"first_incorrect_step": first, "corrected_steps": [
            {"step": i + 1, "terms": task["proposed"][i]}
            for i in range(first - 1, len(task["proposed"]))]})
        duplicate = json.dumps(gold, ensure_ascii=False).replace(
            '"first_incorrect_step":', '"first_incorrect_step": 1, "first_incorrect_step":', 1)
        negatives.append(duplicate)
        for bad in negatives:
            assert not grade(bad, task["accepted_answers"]), task["id"]
            counts["negative_grader_cases"] += 1
        # Try every one-cut splice of distinct gold branches. A splice must be
        # accepted iff it is itself a complete accepted continuation.
        gold_strings = {encoded(a) for a in expected}
        for a in expected:
            for b in expected:
                if a == b:
                    continue
                for cut in range(1, len(a["corrected_steps"])):
                    hybrid = {"first_incorrect_step": first, "corrected_steps":
                              a["corrected_steps"][:cut] + b["corrected_steps"][cut:]}
                    accepted = encoded(hybrid) in gold_strings
                    assert grade(hybrid, task["accepted_answers"]) == accepted
                    counts["branch_splice_checks"] += 1
                    counts["incoherent_splices_rejected"] += int(not accepted)
        counts["tasks_verified"] += 1

    result = {"passed": True, "scope": "Independent direct-VP path regeneration, prefix and gold-set reconstruction, strict grader checks. Not primary-source or model-difficulty certification.",
              "counts": dict(counts), "tasks_sha256": sha(HERE / "tasks.json"),
              "implementation_sha256": {f: sha(HERE / f) for f in ("core.py", "generate.py", "review_audit.py")},
              "findings": [
                  "No gold-path, first-invalid-prefix, or full-continuation mismatch found.",
                  "Technical affix forms and unchanged snapshots are explicitly described in prompts.",
                  "Conservative unchanged-term corruption favors later checkpoints; error-location and repair-length histograms are reported.",
                  "All 200 tasks are Kartari. Other voices and more general corruption types remain outside this pilot.",
                  "VP-relative correctness is reproducible; independent linguistic certification and empirical difficulty remain open."]}
    (HERE / "review-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
