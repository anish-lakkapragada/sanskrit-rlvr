"""Offline evidence and a bounded proposal for the next creation benchmark."""
from __future__ import annotations

import math
import json
import tempfile
from collections import Counter
from decimal import Decimal, ROUND_CEILING
from pathlib import Path


def parallel_search_execution(root):
    directory = root / 'benchmarks/parallel-search-20261006'
    if not (directory / 'run.json').exists():
        return None
    from misc.vp_parallel_monitor import snapshot
    data = snapshot()
    data['directory'] = 'parallel-search-20261006/'
    return data


def iterative_goal_execution(root):
    directory = root / "benchmarks/iterative-goal-20261006"
    if not (directory / "ledger.json").exists():
        return None
    from misc import vp_goal as runner
    state = json.loads((directory / "ledger.json").read_text())
    plan = json.loads((directory / "plan.json").read_text())
    jobs = list(state["jobs"].values())
    from misc.vp_cartesian_visibility import pending_confirmation_ids
    withheld = pending_confirmation_ids(state)
    providers = []
    for provider, cfg in state["authorization"].items():
        actual = state["historical_spend_micro"][provider] + sum(
            j.get("actual_cost_upper_micro", 0) for j in jobs if j["provider"] == provider)
        committed = runner.committed(state, provider)
        protected = runner.protected_remaining(state, provider)
        providers.append({"provider": provider, "cap_usd": cfg["cap_micro"] / 1e6,
                          "usage_cost_upper_usd": actual / 1e6, "committed_usd": committed / 1e6,
                          "protected_usd": protected / 1e6,
                          "available_for_new_experiments_usd": (cfg["cap_micro"] - committed - protected) / 1e6})
    cells = {}
    for j in jobs:
        result_path = directory / "jobs" / j["id"] / "results.json"
        if not j.get("collected_at") or not result_path.exists() or j["id"] not in {"opus-composition-01", "astra-composition-01"}:
            continue
        for row in json.loads(result_path.read_text()):
            cell = row["task"]["campaign"]["construction"]
            record = cells.setdefault(cell, {}).setdefault(j["provider"], {"n": 0, "correct": 0, "completed": 0, "truncated": 0})
            record["n"] += 1
            record["correct"] += int(row["is_correct"] is True)
            record["completed"] += int(row["status"] == "completed" and row["answer"] is not None)
            record["truncated"] += int(row["truncated"])
    return {"updated_at": state["updated_at"], "status": state["status"], "plan": plan,
            "providers": providers, "cells": cells,
            "development": (json.loads((directory / "development-analysis.json").read_text())
                            if (directory / "development-analysis.json").exists() else None),
            "supply": (json.loads((directory / "composition-supply.json").read_text())["strata"]["test_initial"]
                       if (directory / "composition-supply.json").exists() else None),
            "jobs": [{**{k: (None if j['id'] in withheld and k in {'summary', 'completed_answers', 'completed_correct'} else j.get(k)) for k in ("id", "provider", "n", "status", "batch_id", "summary", "settled", "completed_answers", "completed_correct", "transport")},
                      "invalid_inputs": j.get("input_validity", {}).get("n_invalid", 0)} for j in jobs],
            "directory": "iterative-goal-20261006/"}


def campaign_execution(root):
    directory = root / "benchmarks/creation-campaign-20261006"
    ledger = directory / "ledger.json"
    if not ledger.exists():
        return None
    state = json.loads(ledger.read_text())
    jobs = list(state["jobs"].values())
    discovery = (json.loads((directory / "discovery-analysis.json").read_text())
                 if (directory / "discovery-analysis.json").exists() else None)
    feasibility = (json.loads((directory / "construction-feasibility.json").read_text())
                   if (directory / "construction-feasibility.json").exists() else None)
    return {"updated_at": state["updated_at"], "status": state["status"],
            "directory": "creation-campaign-20261006/", "ledger": "creation-campaign-20261006/ledger.json",
            "providers": [{"provider": p, "cap_usd": config["cap_micro"] / 1e6,
                           "reserved_usd": sum(j["reservation_micro"] for j in jobs if j["provider"] == p) / 1e6,
                           "collected_cost_upper_usd": sum(j.get("actual_cost_upper_micro", 0) for j in jobs if j["provider"] == p) / 1e6,
                           "submitted_tasks": sum(j["n"] for j in jobs if j["provider"] == p and j["attempted_at"])}
                          for p, config in state["authorization"].items()],
            "jobs": [{k: j.get(k) for k in ("id", "provider", "phase", "n", "status", "batch_id", "collected_at", "summary", "completed_answers", "completed_correct")}
                     for j in jobs],
            "family_split": (json.loads((directory / "family-split.json").read_text())["counts"]
                             if (directory / "family-split.json").exists() else None),
            "generation": (json.loads((directory / "candidate-generation.json").read_text())
                           if (directory / "candidate-generation.json").exists() else None),
            "discovery": ({"overall": discovery["overall"], "strata": discovery["strata"],
                           "weakest_supported_predicates": discovery["exploratory_predicates"][:5],
                           "support_note": "At least 20 discovery examples and 10 root families; not xHigh calibration"}
                          if discovery else None),
            "feasibility": ({"analyzed_discovery_tasks": feasibility["analyzed_discovery_tasks"],
                             "combined_optimistic_supply": feasibility["combined_optimistic_supply"]}
                            if feasibility else None),
            "outcome": (json.loads((directory / "outcome.json").read_text())
                        if (directory / "outcome.json").exists() else None)}


def build_moving_forward(tasks, compact, models, root: Path):
    """Reproduce exploratory slices without submitting or modifying model runs."""
    from vidyut.prakriya import Data, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana

    index = {m["id"]: i for i, m in enumerate(models)}
    opus = index["claude-opus-5-5-xhigh"]
    astra = index["gpt-6-astra-xhigh"]
    other = [index[k] for k in ("claude-fable-5-1-xhigh", "gpt-6-sol-xhigh", "claude-sonnet-5-xhigh")]
    high = [index[k] for k in ("claude-opus-5-5-high", "gpt-6-astra-high")]
    retained = [t for t in compact if not t["audit_bhave"] and not t["audit_aorist_bhave"]]
    original = {t["id"]: t for t in tasks}
    min_steps = {}
    worked_id = "01.0022:VidhiLin:Karmani:Madhyama:Bahu"
    worked_rules = []
    # Derivation length is an exploratory proxy. Verify the same gold sets before using it.
    with tempfile.TemporaryDirectory(prefix="vp-forward-") as directory:
        Path(directory, "dhatupatha.tsv").symlink_to(root / "data/finetune/task-data/vidyut_dhatupatha_5.tsv")
        entries = {e.code: e for e in Data(directory).load_dhatu_entries()}
        grammar = Vyakarana()
        for row in retained:
            task = original[row["id"]]
            m = task["morphology"]
            derivations = grammar.derive(Pada.Tinanta(
                dhatu=entries[task["dhatu"]["code"]].dhatu,
                lakara=getattr(Lakara, m["lakara"]), prayoga=getattr(Prayoga, m["prayoga"]),
                purusha=getattr(Purusha, m["purusha"]), vacana=getattr(Vacana, m["vacana"]),
            ))
            assert {p.text for p in derivations} == set(task["gold_slp1"]), task["id"]
            min_steps[row["id"]] = min(len(p.history) for p in derivations)
            if row["id"] == worked_id:
                worked_rules = list(dict.fromkeys(step.code for p in derivations for step in p.history))
    assert "8.2.78" in worked_rules

    def summarize(key, label, rows):
        return {"id": key, "label": label, "n": len(rows),
                "opus_correct": sum(t["scores"][opus] == 1 for t in rows),
                "astra_correct": sum(t["scores"][astra] == 1 for t in rows),
                "training_tasks": sum(t["split"] == "finetune" for t in rows),
                "validation_tasks": sum(t["split"] == "validation" for t in rows),
                "root_groups": len({(t["slp1"], t["gana"]) for t in rows})}

    other_misses = [t for t in retained if all(t["scores"][j] == 0 for j in other)]
    high_misses = [t for t in retained if all(t["scores"][j] == 0 for j in high)]
    slices = [
        summarize("retained", "All tasks after the two flag exclusions", retained),
        summarize("aorist", "Aorist / Lun only", [t for t in retained if t["lakara"] == "Lun"]),
        summarize("perfect", "Perfect / Lit only", [t for t in retained if t["lakara"] == "Lit"]),
        summarize("long", "Shortest VP history has at least 38 logged steps", [t for t in retained if min_steps[t["id"]] >= 38]),
        summarize("other_misses", "Fable, Sol and Sonnet xHigh all miss", other_misses),
        summarize("high_misses", "Opus High and Astra High both miss", high_misses),
    ]
    # Budget for 1,000 distinct tasks per benchmark and a separate cap-sensitivity check.
    # This report does not configure a runner or submit paid requests.
    phases = [
        {"id": "opus_screen", "label": "Discover difficult constructions", "scope": "Up to 6,000 development tasks; 3 batches of 2,000", "requests": {"Anthropic": 6_000, "OpenAI": 0}, "output_cap": 4_096, "effort": "High"},
        {"id": "astra_screen", "label": "Cross-check both difficulty tiers", "scope": "1,200 development tasks across candidate constructions", "requests": {"Anthropic": 0, "OpenAI": 1_200}, "output_cap": 4_096, "effort": "High"},
        {"id": "confirm", "label": "Calibrate at the headline settings", "scope": "1,200 development tasks × 1 fresh attempt per model", "requests": {"Anthropic": 1_200, "OpenAI": 1_200}, "output_cap": 16_384, "effort": "xHigh"},
        {"id": "bench_final", "label": "Frozen VP-Bench · target <70%", "scope": "1,000 unique tasks × 1 fresh attempt per model", "requests": {"Anthropic": 1_000, "OpenAI": 1_000}, "output_cap": 16_384, "effort": "xHigh"},
        {"id": "hard_final", "label": "Frozen VP-Bench-Hard · target <50%", "scope": "1,000 unique tasks × 1 fresh attempt per model", "requests": {"Anthropic": 1_000, "OpenAI": 1_000}, "output_cap": 16_384, "effort": "xHigh"},
        {"id": "cap_check", "label": "Higher-budget sensitivity check", "scope": "50 VP-Bench + 50 Hard tasks × 1 extra attempt per model", "requests": {"Anthropic": 100, "OpenAI": 100}, "output_cap": 128_000, "effort": "xHigh"},
    ]
    providers = [
        {"provider": "Anthropic", "model": "Claude Opus 5.5", "model_index": opus, "input_rate": 2, "output_rate": 10,
         "spend_cap_usd": 1_000, "source": "https://platform.claude.com/docs/en/about-claude/pricing"},
        {"provider": "OpenAI", "model": "GPT-6 Astra", "model_index": astra, "input_rate": 5, "output_rate": 25,
         "spend_cap_usd": 2_000, "source": "https://developers.openai.com/api/docs/pricing"},
    ]
    input_cap = 1_000
    for provider in providers:
        def cost(requests, output_cap):
            amount = Decimal(requests * (input_cap * provider["input_rate"] + output_cap * provider["output_rate"])) / 1_000_000
            return float(amount.quantize(Decimal("0.01"), rounding=ROUND_CEILING))
        name = provider["provider"]
        provider["requests"] = sum(p["requests"][name] for p in phases)
        provider["phase_maxima"] = {p["id"]: cost(p["requests"][name], p["output_cap"]) for p in phases}
        provider["maximum_usd"] = round(sum(provider["phase_maxima"].values()), 2)
        provider["headroom_usd"] = round(provider["spend_cap_usd"] - provider["maximum_usd"], 2)
        provider["reserved_final_evaluation_usd"] = round(sum(provider["phase_maxima"][p] for p in ("bench_final", "hard_final")), 2)
        provider["reserved_evaluation_and_check_usd"] = round(provider["reserved_final_evaluation_usd"] + provider["phase_maxima"]["cap_check"], 2)
        provider["full_128k_evaluation_maximum_usd"] = cost(2_000, 128_000)
        provider["minimum_size_campaign_maximum_usd"] = round(provider["maximum_usd"] - cost(1_000, 16_384), 2)
        assert provider["maximum_usd"] <= provider["spend_cap_usd"]
    precision = {
        "interpretation": "Standard error of aggregate accuracy across sampled tasks, in percentage points; not run-to-run SD or 95% margin of error",
        "formula": "SE = sqrt(p * (1 - p) / N), assuming independent unweighted binary tasks",
        "target_se": .01,
        "rows": [{"n": n, "se_at_50": math.sqrt(.25 / n), "se_at_70": math.sqrt(.21 / n), "ci95_half_width_at_70": 1.96 * math.sqrt(.21 / n), "ci95_half_width_at_50": 1.96 * math.sqrt(.25 / n)} for n in (500, 1_000)],
        "minimum_independent_n_below_1pp_at_70": 2_101,
        "minimum_independent_n_below_1pp_worst_case": 2_501,
        "guarantees_sub_1pp": False,
        "reported_uncertainty": "Root-family bootstrap of frozen-set scores; generation variance needs additional repeat runs",
        "source": "https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm",
    }
    misses = sum(t["scores"][opus] == 0 for t in retained)
    return {
        "iterative_goal": iterative_goal_execution(root),
        "parallel_search": parallel_search_execution(root),
        "execution": campaign_execution(root),
        "proposal_date": "2026-10-06", "scope": "Creation only; VP-Bench <70% and VP-Bench-Hard <50% for each reference model; $3,000 hard API-credit limit ($1,000 Anthropic + $2,000 OpenAI)",
        "slices": slices,
        "high_misses_lakara_counts": dict(sorted(Counter(t["lakara"] for t in high_misses).items())),
        "worked_example": {"task_id": worked_id, "trace_rule_ids": worked_rules, "highlighted_rule": "8.2.78", "status": "Historical discovery example; linguistic audit pending; not final membership"},
        "candidate_task_ids": {"other_misses": [t["id"] for t in other_misses], "high_misses": [t["id"] for t in high_misses]},
        "retained_opus_misses": misses,
        "saved_subset_limits": {key: {"accuracy_ceiling": ceiling, "operator": "<", "maximum_n": max(0, math.ceil(Decimal(misses) / (1 - Decimal(str(ceiling)))) - 1)} for key, ceiling in (("vp_bench", .70), ("vp_bench_hard", .50))},
        "raw_coordinate_upper_bound": len({t["dhatu"]["code"] for t in tasks}) * 190,
        "precision": precision,
        "selection_policy": {
            "status": "Proposed; no final benchmark membership selected",
            "common": {"task": "one accepted Devanagari conjugation", "prompt": "same answer-only prompt", "tools": "none", "input_cap": input_cap, "final_effort": "xHigh", "final_output_cap": 16_384,
                       "split": "final evaluation root families disjoint from both development calibration and RL training; disjoint benchmark task IDs", "oracle": "reviewed VP gold sets; unresolved cases excluded"},
            "vp_bench": {"target_n": 1_000, "minimum_release_n": 500, "max_tasks_per_root_family": 2,
                         "minimum_root_families_at_target": 500, "minimum_lakaras": 5, "maximum_lakara_share": .30,
                         "minimum_primary_phenomena": 3, "maximum_primary_phenomenon_share": .50,
                         "selection": "fixed-seed sample from calibrated challenge constructions; stronger-model development accuracy >40% and <=60%; no unrestricted coverage sampling",
                         "target_point_accuracy_per_model": .70, "target_operator": "<", "final_attempts_per_task": 1,
                         "freeze": "construction predicates, sampling weights and membership frozen before final model calls"},
            "vp_bench_hard": {"target_n": 1_000, "minimum_release_n": 500, "max_tasks_per_root_family": 2,
                              "minimum_root_families_at_target": 500, "minimum_lakaras": 3, "maximum_lakara_share": .50,
                              "minimum_primary_phenomena": 3, "maximum_primary_phenomenon_share": .50,
                              "selection": "fixed-seed sample from deeper challenge constructions; stronger-model development accuracy <=40%; final item scores never determine membership",
                              "final_attempts_per_task": 1, "target_point_accuracy_per_model": .50, "target_operator": "<",
                              "freeze": "construction predicates, sampling weights and membership frozen before final model calls"},
            "calibration": {"panel_n": 1200, "initial_examples_per_provisional_tier": 600, "max_constructions": 10, "minimum_examples_per_selected_construction": 100, "minimum_root_families_per_selected_construction": 50,
                            "effort": "xHigh", "output_cap": 16_384, "minimum_completion_fraction_per_model": .95,
                            "routing_statistic": "max(Opus completed-answer accuracy, Astra completed-answer accuracy), computed separately for each construction",
                            "tier_bands": {"vp_bench": {"lower_exclusive": .40, "upper_inclusive": .60}, "vp_bench_hard": {"upper_inclusive": .40}},
                            "mixture_accuracy_ceilings_per_model": {"vp_bench": .60, "vp_bench_hard": .40},
                            "minimum_development_gap_per_model": .10,
                            "rule": "resolve overlapping predicates into disjoint cells before fresh calibration; sample all matching cases including successes; no conditioning on individual Opus misses; verify the proposed mixtures separately for each model"},
            "success_criteria": {"all_reference_models_required": True, "point_targets": "each model <70% on VP-Bench AND <50% on VP-Bench-Hard", "stronger_claim": "the corresponding root-bootstrap 95% upper confidence limits must also be below the target", "on_failure": "report each unmet tier/model target without changing frozen membership"},
            "cap_check": {"n": 100, "tasks_per_benchmark": {"vp_bench": 50, "vp_bench_hard": 50}, "output_cap": 128_000, "effort": "xHigh", "selection": "fixed-seed samples before final answers; separate paired sensitivity results for each tier, not replacements for headline scores"},
            "discovery": {"maximum_paid_tasks": 6000, "batches": 3, "tasks_per_batch": 2000,
                          "review_gate": "review valid construction yield and reserved-family supply after each batch; stop if both tiers are not plausibly attainable within remaining discovery and calibration allowances",
                          "tradeoff": "smaller paid search under the $1,000 Anthropic cap; retain calibration, final sample sizes and sensitivity checks, with less confidence in finding enough qualifying constructions"},
            "candidate_mix": {"failure_analogues": 3000, "unusual_rule_combinations": 1500, "coverage_controls": 1500},
            "manifest_fields": ["task_id", "root_family", "source_split", "coordinates", "vp_version", "gold_version", "trace_rule_ids", "primary_phenomenon", "review_evidence", "selection_reason", "construction_predicate", "development_calibration_and_caps", "sampling_seed_and_weights", "membership_hash", "final_responses", "cap_check_responses"],
            "posthoc_explanation": "Rules are discovered from development errors, audited, then frozen before sampling test families. Explain that chronology; a trace does not establish a model's internal failure cause.",
        },
        "budget": {"checked_on": "2026-10-06", "currency": "USD", "processing": "Batch",
                   "input_cap": input_cap, "phases": phases, "providers": providers,
                   "requests_total": sum(p["requests"] for p in providers),
                   "maximum_usd": round(sum(p["maximum_usd"] for p in providers), 2),
                   "spend_cap_usd": sum(p["spend_cap_usd"] for p in providers),
                   "headroom_usd": round(sum(p["headroom_usd"] for p in providers), 2)},
    }
