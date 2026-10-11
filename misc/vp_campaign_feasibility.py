#!/usr/bin/env python3
"""Audit whether low-scoring discovery predicates have enough new root families.

Counts are optimistic supply bounds before semantic review and prompt deduping.
This never treats High discovery scores as xHigh calibration or selects final IDs.
"""
from __future__ import annotations
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign as c, vp_campaign_candidates as g, oai_batch_eval as b


def supply():
    analysis = b.read_json(c.OUT / "discovery-analysis.json")
    predicates = analysis["exploratory_predicates"] + analysis.get("low_support_leads", [])
    predicates = [p for p in predicates if p["completed_spelling_tolerant_accuracy"] <= .75]
    seen = set()
    unique = []
    for p in predicates:
        key = tuple(tuple(v) for v in p["predicate"])
        if key not in seen:
            unique.append(p); seen.add(key)
    issued = {t["id"] for batch in (1, 2, 3) for t in b.read_json(c.OUT / f"discovery-{batch:02d}.json")}
    historical = {t["id"] for t in b.read_json(ROOT / "benchmarks/full-tasks.json")}
    excluded = issued | historical
    db = g.connect()
    checks = []
    unions = {"bench_leads": {}, "hard_leads": {}}
    for i, p in enumerate(unique):
        clauses, params = [], []
        for key, value in p["predicate"]:
            if key == "rule":
                clauses.append("rules LIKE ?"); params.append('%"' + value + '"%')
            elif key == "gana":
                clauses.append("family LIKE ?"); params.append("%|" + value)
            elif key in {"lakara", "prayoga", "purusha", "vacana"}:
                clauses.append(key + "=?"); params.append(value)
            else:
                raise ValueError("Unknown construction feature")
        rows = list(db.execute("SELECT id,family,split,lakara FROM candidates WHERE " + " AND ".join(clauses), params))
        rows = [row for row in rows if row[0] not in excluded]
        families = defaultdict(Counter)
        tenses = defaultdict(Counter)
        for tid, family, split, lakara in rows:
            families[split][family] += 1; tenses[split][lakara] += 1
        optimistic = {split: {"tasks": sum(values.values()), "families": len(values),
                       "maximum_tasks_at_two_per_family": sum(min(2, n) for n in values.values()),
                       "lakaras": dict(tenses[split])} for split, values in families.items()}
        enough_dev = len(families["development"]) >= 50 and sum(families["development"].values()) >= 100
        # These are deliberately relaxed discovery leads: final xHigh gates remain 60/40.
        lead_tiers = []
        if enough_dev:
            for tier, ceiling in (("bench_leads", .70), ("hard_leads", .50)):
                if p["completed_spelling_tolerant_accuracy"] <= ceiling:
                    lead_tiers.append(tier)
                    unions[tier].update({tid: (f, la) for tid, f, split, la in rows if split == "test"})
        checks.append({"predicate": p["predicate"], "discovery_n": p["n"],
                       "discovery_families": p["root_families"],
                       "discovery_completed_accuracy": p["completed_spelling_tolerant_accuracy"],
                       "candidate_supply_upper_bounds": optimistic,
                       "enough_new_development_examples_and_families": enough_dev,
                       "relaxed_discovery_lead_tiers": lead_tiers})
        if (i + 1) % 25 == 0:
            print(f"Supply audit: {i+1}/{len(unique)} predicates", flush=True)
    combined = {}
    for tier, rows in unions.items():
        families = Counter(f for f, la in rows.values())
        tenses = Counter(la for f, la in rows.values())
        combined[tier] = {"predicate_count": sum(tier in p["relaxed_discovery_lead_tiers"] for p in checks),
                          "test_families": len(families), "test_tasks": len(rows),
                          "maximum_test_tasks_at_two_per_family": sum(min(2, n) for n in families.values()),
                          "lakaras": dict(tenses),
                          "can_support_minimum_size_before_other_gates": sum(min(2, n) for n in families.values()) >= 500}
        max_percent, minimum_lakaras = (30, 5) if tier == "bench_leads" else (50, 3)
        upper = combined[tier]["maximum_test_tasks_at_two_per_family"]
        quota_upper = next((n for n in range(upper, 0, -1)
                            if len(tenses) >= minimum_lakaras and n >= minimum_lakaras
                            and sum(min(count, n * max_percent // 100) for count in tenses.values()) >= n), 0)
        combined[tier]["maximum_tasks_after_tense_quota_upper_bound"] = quota_upper
        combined[tier]["can_support_minimum_size_with_tense_quota"] = quota_upper >= 500
    result = {"created_at": b.now(), "analyzed_discovery_tasks": analysis["overall"]["n"],
              "analysis_sha256": b.sha256(c.OUT / "discovery-analysis.json"),
              "screening_bands": {"bench_lead_maximum": .70, "hard_lead_maximum": .50,
                                   "calibration_bands_remain": {"bench": .60, "hard": .40}},
              "checks": checks, "combined_optimistic_supply": combined,
              "notes": ["Discovery High/4096 scores are not headline xHigh/16384 scores.",
                        "Includes noisy low-support leads (>=6 completed answers, >=3 observed families) to avoid discarding narrow hypotheses prematurely.",
                        "Every candidate cell must still supply >=100 new development tasks from >=50 families before calibration.",
                        "Family/task supply counts are optimistic; validity, spelling, predicate overlap, sampling weights and grammar diversity can only reduce them.",
                        "This is a bounded search over the recorded predicate library, not proof that no other creation benchmark exists."]}
    b.atomic_json(c.OUT / "construction-feasibility.json", result)
    print(json.dumps({"analyzed_discovery_tasks": result["analyzed_discovery_tasks"], "predicates_checked": len(checks),
                      "combined_optimistic_supply": combined}, indent=2), flush=True)
    return result


if __name__ == "__main__":
    supply()
