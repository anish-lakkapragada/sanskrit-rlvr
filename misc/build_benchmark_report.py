#!/usr/bin/env python3
"""Build the offline benchmark study from saved results; never calls a model.

Run from any directory: .venv/bin/python misc/build_benchmark_report.py
Requires the project's numpy and vidyut packages. Raw benchmark files are read-only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finetune.prompts import (  # noqa: E402
    GANA_EN, LAKARA_EN, PRAYOGA_EN, PURUSHA_EN, VACANA_EN,
    extract_answer, slp1_to_devanagari,
)
from misc.benchmark_forward import build_moving_forward  # noqa: E402

BENCH = ROOT / "benchmarks"
OUT = BENCH / "analysis/performance-study"
BOOTSTRAPS = 2000
SEED = 20260930
NAMES = {
    "claude-opus-5-5": "Opus 5.5", "claude-fable-5-1": "Fable 5.1",
    "claude-sonnet-5": "Sonnet 5", "gpt-6-astra": "GPT-6 Astra",
    "gpt-6-sol": "GPT-6 Sol",
}
DIMENSIONS = {
    "lakara": ("Tense / mood", LAKARA_EN),
    "prayoga": ("Voice", PRAYOGA_EN),
    "purusha": ("Person", PURUSHA_EN),
    "vacana": ("Number", VACANA_EN),
    "gana": ("Verb class", GANA_EN),
    "gold_count": ("Accepted forms", {"1": "One form", "2": "Two forms", "3+": "Three or more"}),
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(s):
    return unicodedata.normalize("NFC", s.strip()) if s is not None else None


def write_json(path, obj, pretty=True):
    path.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False,
                               indent=2 if pretty else None) + "\n")


def main():
    tasks = read(BENCH / "full-tasks.json")
    ids = [t["id"] for t in tasks]
    assert len(set(ids)) == len(ids)
    lookup = {tid: i for i, tid in enumerate(ids)}
    n = len(tasks)
    dataset_hash = sha(BENCH / "full-tasks.json")
    split_ids = {s: {t["id"] for t in read(ROOT / f"data/finetune/task-data/{s}.json")}
                 for s in ("finetune", "validation")}
    assert not split_ids["finetune"] & split_ids["validation"]
    assert set(ids) == split_ids["finetune"] | split_ids["validation"]
    root_keys = [(t["dhatu"]["aupadeshika"], t["dhatu"]["gana"]) for t in tasks]
    roots = sorted(set(root_keys))
    root_lookup = {r: i for i, r in enumerate(roots)}
    root_indices = np.array([root_lookup[r] for r in root_keys])
    training_roots = {root_keys[i] for i, tid in enumerate(ids) if tid in split_ids["finetune"]}
    validation_roots = {root_keys[i] for i, tid in enumerate(ids) if tid in split_ids["validation"]}
    overlap_roots = training_roots & validation_roots
    compact = []
    for i, t in enumerate(tasks):
        m = t["morphology"]
        suspect = m["prayoga"] == "Bhave" and (m["purusha"], m["vacana"]) != ("Prathama", "Eka")
        compact.append({"id": t["id"], "root": slp1_to_devanagari(t["dhatu"]["aupadeshika"]),
            "slp1": t["dhatu"]["aupadeshika"], "gana": t["dhatu"]["gana"], **m,
            "gold": t["gold_devanagari"], "gold_count": str(min(len(t["gold_devanagari"]), 3)).replace("3", "3+"),
            "split": "validation" if t["id"] in split_ids["validation"] else "finetune",
            "shared_root": root_keys[i] in overlap_roots, "audit_bhave": suspect,
            "audit_aorist_bhave": m["lakara"] == "Lun" and m["prayoga"] == "Bhave" and not suspect})

    models, scores, answers, statuses = [], [], [], []
    sources = []
    paths = sorted([*BENCH.glob("ant/*/*.meta.json"), *BENCH.glob("oai/*/*.meta.json")])
    for meta_path in paths:
        meta = read(meta_path)
        assert meta["summary"]["final"], f"Incomplete run: {meta_path}"
        assert meta["dataset_sha256"] == dataset_hash
        assert meta["samples_per_task"] == 1 and meta["summary"]["unscored"] == 0
        path = meta_path.with_name(meta_path.name.replace(".meta.json", ".json"))
        rows = read(path)
        by_id = {r["task_id"]: r for r in rows}
        assert len(by_id) == len(rows) == n and set(by_id) == set(ids)
        sc, ans, stat = [], [], []
        for i, task in enumerate(tasks):
            row = by_id[task["id"]]
            assert row["task"] == task and row["raw_batch_result"] is not None
            answer = extract_answer(row["output_text"])
            assert answer == row["answer"], (path, task["id"], "parser mismatch")
            computed = norm(answer) in {norm(g) for g in task["gold_devanagari"]}
            assert row["is_correct"] is computed, (path, task["id"], "grade mismatch")
            sc.append(float(computed)); ans.append(answer); stat.append(row["status"])
        assert sum(sc) == meta["summary"]["correct"]
        usage = meta["usage_totals"]
        price = meta["batch_prices_usd_per_million_tokens"]
        cached = usage.get("cached_input_tokens", usage.get("cache_read_input_tokens", 0))
        if cached or usage.get("cache_creation_input_tokens", 0):
            raise ValueError("Review cache pricing before calculating costs for this run")
        cost = (usage["input_tokens"] * price["input"] + usage["output_tokens"] * price["output"]) / 1e6
        if "estimated_cost_usd" in meta:
            assert abs(cost - meta["estimated_cost_usd"]) < 1e-6
        config = meta["configuration"]
        source = {"path": str(path.relative_to(BENCH)), "sha256": sha(path),
            "meta_path": str(meta_path.relative_to(BENCH)), "meta_sha256": sha(meta_path),
            "run_id": meta["run_id"], "collected_at": meta["collected_at"],
            "prompt": meta["prompt_template"], "prompt_sha256": meta["prompt_sha256"]}
        sources.append(source)
        models.append({"id": config, "name": NAMES.get(meta["model"], meta["model"]),
            "effort": meta["effort"], "provider": "Anthropic" if "/ant/" in str(path) else "OpenAI",
            "archived": False, "prompt": "v2" if "/v2/" in meta["prompt_template"] else "v1",
            "cost": cost, "output_tokens": usage["output_tokens"],
            "output_per_task": usage["output_tokens"] / n,
            "refused": stat.count("refused"), "no_answer": ans.count(None),
            "wrong_answer": sum(s == 0 and a is not None for s, a in zip(sc, ans)),
            "truncated": sum(bool(r["truncated"]) for r in rows), "source": source})
        scores.append(sc); answers.append(ans); statuses.append(stat)
        print(f"Verified {config}: {int(sum(sc))}/{n}", flush=True)
        del rows, by_id

    current_count = len(models)
    for key, label, path, field, success_key in [
        ("grpo-r3", "Qwen3-4B · GRPO-r3", BENCH / "archive/results/grpo-r3-per-task.json", "tasks", "exact_successes"),
        ("sft-67", "Qwen3-4B · SFT 67%", BENCH / "archive/sft-validation-difficulty/definition.json", "assignments", "successes"),
    ]:
        doc = read(path); rows = doc[field]
        assert len({r["id"] for r in rows}) == len(rows)
        assert {r["id"] for r in rows} == (set(ids) if key == "grpo-r3" else split_ids["validation"])
        sc = [np.nan] * n
        for row in rows:
            assert row["attempts"] == 16 and 0 <= row[success_key] <= 16
            sc[lookup[row["id"]]] = row[success_key] / row["attempts"]
        source = {"path": str(path.relative_to(BENCH)), "sha256": sha(path)}
        sources.append(source)
        models.append({"id": key, "name": label, "effort": "16 samples", "provider": "Local checkpoint",
            "archived": True, "prompt": "v1", "cost": None, "source": source})
        scores.append(sc)

    # One row per task, one column per configuration. NaN means no recorded evaluation.
    matrix = np.array(scores).T
    order = sorted(range(current_count), key=lambda j: -matrix[:, j].mean()) + list(range(current_count, len(models)))
    models = [models[j] for j in order]
    matrix = matrix[:, order]
    answers = [answers[j] for j in order[:current_count]]
    statuses = [statuses[j] for j in order[:current_count]]
    for i, task in enumerate(compact):
        task["scores"] = [None if np.isnan(v) else float(v) for v in matrix[i]]
        task["answers"] = [a[i] for a in answers]
        task["statuses"] = [s[i] for s in statuses]
    model_index = {m["id"]: j for j, m in enumerate(models)}
    rng = np.random.default_rng(SEED)

    def stats(indices):
        """Pointwise whole-root percentile bootstrap; all models share resamples."""
        indices = np.asarray(indices, dtype=int)
        if not len(indices):
            return [None] * len(models), None
        values = matrix[indices]
        unique, inverse = np.unique(root_indices[indices], return_inverse=True)
        num = np.zeros((len(unique), len(models)))
        den = np.zeros_like(num)
        np.add.at(num, inverse, np.nan_to_num(values))
        np.add.at(den, inverse, ~np.isnan(values))
        valid = den.sum(axis=0) > 0
        bootstrap = np.full((BOOTSTRAPS, len(models)), np.nan)
        for offset in range(0, BOOTSTRAPS, 200):
            w = rng.multinomial(len(unique), np.full(len(unique), 1 / len(unique)),
                                size=min(200, BOOTSTRAPS - offset))
            bden = w @ den[:, valid]
            with np.errstate(invalid="ignore", divide="ignore"):
                bootstrap[offset:offset + len(w), valid] = (w @ num[:, valid]) / bden
        result = []
        for j in range(len(models)):
            count = int(den[:, j].sum())
            if not count:
                result.append(None); continue
            lo, hi = np.nanquantile(bootstrap[:, j], [0.025, 0.975])
            result.append({"n": count, "correct": float(num[:, j].sum()),
                "accuracy": float(num[:, j].sum() / count), "ci": [float(lo), float(hi)],
                "clusters": int((den[:, j] > 0).sum())})
        return result, bootstrap

    cohorts = {
        "all": ("All tasks", list(range(n))),
        "validation": ("Original validation", [i for i, t in enumerate(compact) if t["split"] == "validation"]),
        "clean_validation": ("Validation · disjoint root groups", [i for i, t in enumerate(compact) if t["split"] == "validation" and not t["shared_root"]]),
        "finetune": ("Original finetune", [i for i, t in enumerate(compact) if t["split"] == "finetune"]),
    }
    cohort_data = {}
    for ck, (label, indices) in cohorts.items():
        overall, boots = stats(indices)
        dimensions = {}
        for dim, (title, options) in DIMENSIONS.items():
            dimensions[dim] = {"label": title, "rows": []}
            for value, gloss in options.items():
                selected = [i for i in indices if compact[i][dim] == value]
                estimates, _ = stats(selected)
                dimensions[dim]["rows"].append({"value": value, "label": gloss, "n": len(selected), "stats": estimates})
        interactions = []
        for la in LAKARA_EN:
            for pr in PRAYOGA_EN:
                selected = [i for i in indices if compact[i]["lakara"] == la and compact[i]["prayoga"] == pr]
                estimates, _ = stats(selected)
                interactions.append({"lakara": la, "prayoga": pr, "n": len(selected), "stats": estimates})
        effort = []
        for prefix in ["claude-opus-5-5", "gpt-6-astra"]:
            h, x = (model_index[prefix + "-" + e] for e in ["high", "xhigh"])
            delta = matrix[indices, x] - matrix[indices, h]
            ci = np.quantile(boots[:, x] - boots[:, h], [0.025, 0.975])
            effort.append({"name": models[x]["name"], "high": h, "xhigh": x,
                "gained": int((delta > 0).sum()), "lost": int((delta < 0).sum()),
                "delta": float(delta.mean()), "ci": ci.tolist(),
                "cost_ratio": models[x]["cost"] / models[h]["cost"]})
        cohort_data[ck] = {"label": label, "n": len(indices), "overall": overall,
            "dimensions": dimensions, "interactions": interactions, "effort": effort}
        print(f"Analyzed {label}: {len(indices)} tasks", flush=True)

    xhigh = [j for j, m in enumerate(models) if not m["archived"] and m["effort"] == "xhigh"]
    solved_count = matrix[:, xhigh].sum(axis=1)
    for i, task in enumerate(compact):
        task["models_correct"] = int(solved_count[i])
    opus = model_index["claude-opus-5-5-xhigh"]
    op_fail = matrix[:, opus] == 0
    groups = {
        "aorist": [i for i, t in enumerate(compact) if t["lakara"] == "Lun"],
        "bhave_audit": [i for i, t in enumerate(compact) if t["audit_bhave"]],
        "excluding_bhave_audit": [i for i, t in enumerate(compact) if not t["audit_bhave"]],
        "all_five_miss": np.flatnonzero(solved_count == 0).tolist(),
        "at_most_two_correct": np.flatnonzero(solved_count <= 2).tolist(),
        "aorist_bhave_third_singular": [i for i, t in enumerate(compact) if t["audit_aorist_bhave"]],
        "aorist_without_bhave_third_singular": [i for i, t in enumerate(compact) if t["lakara"] == "Lun" and not t["audit_aorist_bhave"]],
    }
    sensitivity = {k: {"n": len(v), "stats": stats(v)[0]} for k, v in groups.items()}
    # Fixed observed three-task bundles per dictionary entry; not an estimate of full paradigms.
    bundles = defaultdict(list)
    for i, t in enumerate(tasks):
        bundles[t["dhatu"]["code"]].append(i)
    assert set(map(len, bundles.values())) == {3}
    bundle_scores = [sum(all(matrix[i, j] == 1 for i in ix) for ix in bundles.values()) / len(bundles)
                     for j in range(current_count)]
    pairwise = []
    for a in range(current_count):
        for b in range(a + 1, current_count):
            av, bv = matrix[:, a] == 1, matrix[:, b] == 1
            pairwise.append({"a": a, "b": b, "both": int((av & bv).sum()),
                "a_only": int((av & ~bv).sum()), "b_only": int((~av & bv).sum()),
                "neither": int((~av & ~bv).sum())})
    macro_class = []
    for j in range(len(models)):
        rowstats = [r["stats"][j] for r in cohort_data["all"]["dimensions"]["gana"]["rows"]]
        macro_class.append(float(np.mean([r["accuracy"] for r in rowstats if r])))
    audit = {"task_count": n, "current_configurations": current_count, "current_models": len(xhigh),
        "verified_responses": n * current_count, "root_entries": len(bundles), "root_clusters": len(roots),
        "split_overlap_clusters": len(overlap_roots),
        "split_overlap_validation_tasks": sum(t["split"] == "validation" and t["shared_root"] for t in compact),
        "bhave_outside_third_singular": len(groups["bhave_audit"]),
        "gold_set_sizes": dict(sorted(Counter(len(t["gold"]) for t in compact).items())),
        "distinct_gold_sets": len({tuple(sorted(t["gold"])) for t in compact}),
        "overlap_histogram": [int((solved_count == i).sum()) for i in range(len(xhigh) + 1)],
        "three_task_bundle_accuracy": bundle_scores, "class_macro_accuracy": macro_class,
        "opus_misses": int(op_fail.sum()),
        "opus_aorist_misses": int(sum(op_fail[i] for i in groups["aorist"])),
        "aorist_bhave_third_singular_all_five_miss": sum(solved_count[i] == 0 for i in groups["aorist_bhave_third_singular"]),
        "aorist_bhave_third_singular_unanimous_answer": sum(
            len({compact[i]["answers"][j] for j in xhigh}) == 1 and compact[i]["answers"][xhigh[0]] is not None
            for i in groups["aorist_bhave_third_singular"]),
    }
    audit["aorist_bhave_third_singular_all_five_miss"] = int(audit["aorist_bhave_third_singular_all_five_miss"])
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": dataset_hash,
        "method": {"bootstrap_resamples": BOOTSTRAPS, "seed": SEED,
            "cluster": "dhatu citation (aupadeshika) + gana", "interval": "pointwise 95% percentile",
            "scope": "Fixed saved runs; task/root variation, not repeated-generation uncertainty. No multiple-testing correction."},
        "models": models, "cohorts": cohort_data, "audit": audit,
        "sensitivity": sensitivity, "pairwise": pairwise, "sources": sources,
        "tasks": compact,
        "external_sources": [
            {"title": "Sanskrit Sentence Generator (2019), §3.2", "url": "https://aclanthology.org/W19-7501.pdf",
             "supports": "Bhāve uses third-person singular; other combinations require linguistic review."},
            {"title": "Vidyut: generating words", "url": "https://vidyut.readthedocs.io/en/latest/prakriya.html",
             "supports": "Prefixes, sanādi suffixes and derivation histories are available for benchmark extensions."},
            {"title": "Aṣṭādhyāyī 3.1.66, ciṇ bhāvakarmaṇoḥ", "url": "https://www.ashtadhyayi.com/sutraani/3/1/66",
             "supports": "The ciṇ substitution applies to bhāva and karman before the specified third-person singular ending; relevant to auditing the aorist bhāve key."},
        ]}
    output["moving_forward"] = build_moving_forward(tasks, compact, models, ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "study.json", output, pretty=False)
    with (OUT / "model-summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cohort", "configuration", "archived", "n", "accuracy", "ci95_low", "ci95_high", "full_run_estimated_cost_usd"])
        for ck, cohort in cohort_data.items():
            for j, model in enumerate(models):
                s = cohort["overall"][j]
                if s:
                    writer.writerow([ck, model["id"], model["archived"], s["n"], s["accuracy"], *s["ci"], model["cost"]])
    with (OUT / "option-summary.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cohort", "dimension", "option", "configuration", "n", "accuracy", "ci95_low", "ci95_high"])
        for ck, cohort in cohort_data.items():
            for dim, group in cohort["dimensions"].items():
                for row in group["rows"]:
                    for j, model in enumerate(models):
                        s = row["stats"][j]
                        if s:
                            writer.writerow([ck, dim, row["value"], model["id"], s["n"], s["accuracy"], *s["ci"]])
    template = (ROOT / "misc/benchmark_report.template.html").read_text()
    # Safe even if a saved model answer contains markup or an HTML end tag.
    payload = json.dumps(output, ensure_ascii=False, allow_nan=False, separators=(",", ":")).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    assert template.count("__STUDY_DATA__") == 1
    (BENCH / "report.html").write_text(template.replace("__STUDY_DATA__", payload))
    print(json.dumps({"report": str(BENCH / "report.html"), "audit": audit}, indent=2))


if __name__ == "__main__":
    main()
