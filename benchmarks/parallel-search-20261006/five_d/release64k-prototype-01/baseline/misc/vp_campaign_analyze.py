#!/usr/bin/env python3
"""Analyze discovery results without using any held-out model answers."""
from __future__ import annotations
import argparse
import itertools
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign as c, vp_campaign_candidates as g, oai_batch_eval as b


def spelling_key(text):
    text = text or ""
    for nasal, following in (("ङ", "कखगघ"), ("ञ", "चछजझ"), ("ण", "टठडढ"), ("न", "तथदध"), ("म", "पफबभ")):
        text = re.sub(nasal + "्(?=[" + following + "])", "ं", text)
    return text


def features(task):
    m = task["morphology"]
    attrs = [(k, m[k]) for k in ("lakara", "prayoga", "purusha", "vacana")]
    attrs.append(("gana", task["dhatu"]["gana"]))
    # Predicates use grammar, not individual root IDs or answers.
    for n in (1, 2):
        for pairs in itertools.combinations(attrs, n):
            yield tuple(sorted(pairs))
    rules = [r for r in task["campaign"]["trace_rule_ids"] if r.split(".")[0] in {"3", "6", "7", "8"}]
    for rule in rules:
        yield (("rule", rule),)
        for attr in attrs:
            yield tuple(sorted((attr, ("rule", rule))))
        yield tuple(sorted((("lakara", m["lakara"]), ("prayoga", m["prayoga"]), ("rule", rule))))


def matches(task, predicate):
    for key, value in predicate:
        if key == "rule":
            if value not in task["campaign"]["trace_rule_ids"]: return False
        elif key == "gana":
            if value != task["dhatu"]["gana"]: return False
        elif task["morphology"][key] != value:
            return False
    return True


def summarize(rows):
    completed = [r for r in rows if r["status"] == "completed" and r["answer"] and not r["truncated"]]
    exact = sum(r["is_correct"] is True for r in completed)
    adjusted = sum(r["is_correct"] is True or spelling_key(r["answer"]) in {spelling_key(f) for f in r["task"]["gold_devanagari"]} for r in completed)
    return {"n": len(rows), "completed": len(completed), "completion_fraction": len(completed)/len(rows),
            "correct_all": sum(r["is_correct"] is True for r in rows), "completed_exact_correct": exact,
            "completed_exact_accuracy": exact/len(completed) if completed else None,
            "completed_spelling_tolerant_correct": adjusted,
            "completed_spelling_tolerant_accuracy": adjusted/len(completed) if completed else None,
            "nasal_spelling_only_errors": adjusted-exact,
            "root_families": len({r["task"]["campaign"]["root_family"] for r in rows})}


def analyze():
    state = c.load()
    rows, jobs = [], []
    for job in state["jobs"].values():
        if job["phase"] == "opus_screen" and job.get("collected_at"):
            rows.extend(b.read_json(c.OUT / "jobs" / job["id"] / "results.json"))
            jobs.append(job["id"])
    if not rows: raise ValueError("No collected discovery results")
    groups = defaultdict(list)
    rule_frequency = Counter(rule for row in rows for rule in row["task"]["campaign"]["trace_rule_ids"])
    for row in rows:
        for feature in features(row["task"]): groups[feature].append(row)
        uncommon = sorted((rule for rule in row["task"]["campaign"]["trace_rule_ids"]
                           if rule.split(".")[0] in {"3", "6", "7", "8"} and 10 <= rule_frequency[rule] <= len(rows)/4),
                          key=lambda rule: (rule_frequency[rule], rule))[:12]
        for first, second in itertools.combinations(uncommon, 2):
            groups[tuple(sorted((("rule", first), ("rule", second))))].append(row)
    predicates, low_support = [], []
    for predicate, subset in groups.items():
        if len(subset) < 6: continue
        summary = summarize(subset)
        if summary["completed"] < 6 or summary["root_families"] < 3: continue
        row = {"predicate": list(predicate), **summary}
        if len(subset) >= 20 and summary["root_families"] >= 10 and summary["completed"] >= 15:
            predicates.append(row)
        elif summary["completed_spelling_tolerant_accuracy"] <= .70:
            low_support.append(row)
    predicates.sort(key=lambda p: (p["completed_spelling_tolerant_accuracy"], -p["completed"], str(p["predicate"])))
    low_support.sort(key=lambda p: (p["completed_spelling_tolerant_accuracy"], -p["completed"], str(p["predicate"])))
    errors = []
    for row in rows:
        if row["is_correct"] is True: continue
        t = row["task"]
        errors.append({"task_id": t["id"], "root_family": t["campaign"]["root_family"],
                       "root": t["dhatu"], "coordinates": t["morphology"], "gold": t["gold_devanagari"],
                       "answer": row["answer"], "status": row["status"], "truncated": row["truncated"],
                       "spelling_only": row["answer"] is not None and spelling_key(row["answer"]) in {spelling_key(f) for f in t["gold_devanagari"]},
                       "rules": t["campaign"]["trace_rule_ids"]})
    result = {"updated_at": b.now(), "jobs": jobs, "overall": summarize(rows),
              "strata": {key: {v: summarize([r for r in rows if (r['task']['morphology'].get(key) if key != 'category' else r['task']['campaign']['selection_reason']['category']) == v]) for v in sorted({(r['task']['morphology'].get(key) if key != 'category' else r['task']['campaign']['selection_reason']['category']) for r in rows})} for key in ("lakara", "prayoga", "category")},
              "exploratory_predicates": predicates,
              "low_support_leads": low_support,
              "predicate_search": "Single grammar coordinates, pairs of coordinates, individual rules with coordinates, and pairs among the twelve least frequent eligible rules per task (frequency 10 through N/4)",
              "notes": ["Adaptive exploratory search on Opus High at 4096 output tokens; not final difficulty calibration", "Spelling-tolerant score is a diagnostic upper bound to prevent nasal typography from creating artificial hardness; headline gold-set scoring is unchanged", "At least 20 observed examples and 10 families for discovery listings; later calibration still needs >=100 examples and >=50 families", "Predicates overlap and are not yet frozen construction cells"]}
    b.atomic_json(c.OUT / "discovery-analysis.json", result)
    b.atomic_json(c.OUT / "discovery-errors.json", errors)
    print(json.dumps({"overall": result["overall"], "strata": result["strata"], "lowest_accuracy_predicates": predicates[:20]}, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    analyze()
