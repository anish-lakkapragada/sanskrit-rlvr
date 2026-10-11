#!/usr/bin/env python3
"""Offline task-by-task overlap of the seven completed OAI/ANT benchmark runs."""
import csv
import hashlib
import json
import math
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks/analysis/model-overlap"
CONFIGS = [
    ("opus_xhigh", "Opus 5.5 xHigh", "ant/claude-opus-5-5/xhigh"),
    ("opus_high", "Opus 5.5 High", "ant/claude-opus-5-5/high"),
    ("fable_xhigh", "Fable 5.1 xHigh", "ant/claude-fable-5-1/xhigh"),
    ("astra_xhigh", "Astra xHigh", "oai/gpt-6-astra/xhigh"),
    ("astra_high", "Astra High", "oai/gpt-6-astra/high"),
    ("sol_xhigh", "Sol xHigh", "oai/gpt-6-sol/xhigh"),
    ("sonnet_xhigh", "Sonnet 5 xHigh", "ant/claude-sonnet-5/xhigh"),
]


def read(path):
    return json.loads(path.read_text())


def normalized(value):
    return unicodedata.normalize("NFC", value.strip()) if value is not None else None


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dataset = ROOT / "benchmarks/full-tasks.json"
    tasks = read(dataset)
    dataset_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
    ids = [t["id"] for t in tasks]
    universe = set(ids)
    assert len(ids) == len(universe) == 6687
    n = len(ids)
    correct, outcomes, sources = {}, {}, []
    for key, label, stem in CONFIGS:
        path = ROOT / "benchmarks" / (stem + ".json")
        meta = read(path.with_name(path.stem + ".meta.json"))
        assert meta["dataset_sha256"] == dataset_hash and meta["summary"]["final"]
        rows = read(path)
        by_id = {r["task_id"]: r for r in rows}
        assert len(by_id) == len(rows) == n and set(by_id) == universe
        assert all(r["raw_batch_result"] is not None for r in rows)
        outcomes[key] = {}
        for task in tasks:
            r = by_id[task["id"]]
            assert r["task"] == task
            computed = normalized(r["answer"]) in {normalized(g) for g in task["gold_devanagari"]}
            assert r["is_correct"] is computed
            outcomes[key][task["id"]] = {
                "correct": computed, "answer": r["answer"], "status": r["status"],
                "truncated": r["truncated"],
            }
        correct[key] = {i for i, v in outcomes[key].items() if v["correct"]}
        assert len(correct[key]) == meta["summary"]["correct"]
        sources.append({"key": key, "label": label, "path": str(path.relative_to(ROOT)),
            "run_id": meta["run_id"], "prompt_template": meta["prompt_template"],
            "prompt_sha256": meta["prompt_sha256"], "correct": len(correct[key]),
            "statuses": dict(Counter(v["status"] for v in outcomes[key].values()))})
        print(label, "verified", len(correct[key]), "correct", flush=True)
        del rows, by_id

    keys = [c[0] for c in CONFIGS]
    labels = {c[0]: c[1] for c in CONFIGS}
    xhigh = [k for k in keys if k.endswith("_xhigh")]

    def spectrum(subset):
        counts = Counter(sum(i in correct[k] for k in subset) for i in ids)
        exclusive = {k: sorted(correct[k] - set.union(*(correct[o] for o in subset if o != k))) for k in subset}
        return {"configurations": subset, "tasks_by_number_correct": {str(j): counts[j] for j in range(len(subset)+1)},
            "all_correct": len(set.intersection(*(correct[k] for k in subset))),
            "none_correct": len(universe - set.union(*(correct[k] for k in subset))),
            "any_correct": len(set.union(*(correct[k] for k in subset))),
            "only_this_configuration_correct": {k: len(v) for k, v in exclusive.items()},
            "exclusive_task_ids": exclusive}

    pairs = []
    for ai, a in enumerate(keys):
        for b in keys[ai+1:]:
            ac, bc = correct[a], correct[b]
            both, aonly, bonly, neither = len(ac & bc), len(ac - bc), len(bc - ac), len(universe - (ac | bc))
            assert both + aonly + bonly + neither == n
            denom = math.sqrt(len(ac) * (n-len(ac)) * len(bc) * (n-len(bc)))
            pairs.append({"a": a, "b": b, "both_correct": both, "only_a_correct": aonly,
                "only_b_correct": bonly, "both_incorrect": neither, "at_least_one_correct": len(ac | bc),
                "success_jaccard": both / len(ac | bc),
                "failure_jaccard": neither / len(universe - (ac & bc)),
                "correctness_phi": (both * neither - aonly * bonly) / denom,
                "fraction_a_successes_also_b": both / len(ac),
                "fraction_b_successes_also_a": both / len(bc)})

    strata = {}
    for field in ("lakara", "prayoga", "purusha", "vacana", "gana", "source_split"):
        groups = defaultdict(list)
        for index, task in enumerate(tasks):
            value = (task["dhatu"]["gana"] if field == "gana" else
                     ("finetune" if index < 6018 else "validation") if field == "source_split" else task["morphology"][field])
            groups[value].append(task["id"])
        strata[field] = {g: {"n": len(group),
            "correct": {k: sum(i in correct[k] for i in group) for k in keys},
            "accuracy": {k: sum(i in correct[k] for i in group)/len(group) for k in keys},
            "none_xhigh_correct": sum(not any(i in correct[k] for k in xhigh) for i in group)}
            for g, group in sorted(groups.items())}

    baseline = correct["opus_xhigh"]
    extras = {k: {"correct": len(correct[k]), "also_correct_by_opus_xhigh": len(correct[k] & baseline),
        "percent_successes_also_opus_xhigh": 100*len(correct[k] & baseline)/len(correct[k]),
        "solves_opus_xhigh_misses": len(correct[k] - baseline),
        "misses_opus_xhigh_solves": len(baseline - correct[k]),
        "both_miss": len(universe - (baseline | correct[k]))} for k in keys if k != "opus_xhigh"}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "task_count": n,
        "dataset_sha256": dataset_hash, "sources": sources,
        "notes": ["Matched by task ID and verified gold-set scoring for every record.",
            "OpenAI uses prompt v1; Anthropic uses v2. These are overlaps between observed runs, not an isolated comparison of model capabilities.",
            "Each configuration has one sampled response per task; difficulty and disagreement are empirical, not intrinsic.",
            "Refusals, missing answers, and incorrect answers all count as unsuccessful.",
            "At least one correct is retrospective coverage using gold labels, not a deployable ensemble accuracy.",
            "The dataset includes 6018 finetuning tasks and 669 validation tasks."],
        "seven_configurations": spectrum(keys), "five_xhigh_models": spectrum(xhigh),
        "pairwise": pairs, "compared_with_opus_xhigh": extras, "by_grammar": strata}
    write_json(OUT / "summary.json", report)

    with (OUT / "task-overlap.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["task_index", "task_id", "dhatu_code", "gana", "lakara", "prayoga", "purusha", "vacana", "num_correct_all_seven", "num_correct_five_xhigh", *keys])
        for index, t in enumerate(tasks):
            i = t["id"]
            writer.writerow([index, i, t["dhatu"]["code"], t["dhatu"]["gana"], *[t["morphology"][v] for v in ("lakara", "prayoga", "purusha", "vacana")],
                sum(i in correct[k] for k in keys), sum(i in correct[k] for k in xhigh), *[int(i in correct[k]) for k in keys]])

    interesting = []
    for index, t in enumerate(tasks):
        i=t["id"]
        count=sum(i in correct[k] for k in xhigh)
        if count <= 1 or i not in baseline:
            interesting.append({"task_index": index, "task": t, "num_correct_five_xhigh": count,
                                "outcomes": {k: outcomes[k][i] for k in keys}})
    write_json(OUT / "hard-and-disagreement-tasks.json", interesting)

    lines = ["# Task-level overlap across benchmark runs", "", f"All {n:,} task IDs and gold-set scoring verified for seven completed runs.", "",
        "OpenAI used v1 and Anthropic used v2. All results are single sampled responses; refusals and missing answers count as failures.", "",
        "## Five distinct models at xHigh", "", "| Number of models correct | Tasks | Share |", "|---:|---:|---:|"]
    for j, count in report["five_xhigh_models"]["tasks_by_number_correct"].items():
        lines.append(f"| {j} | {count:,} | {count/n:.2%} |")
    lines += ["", "## Complementarity with Opus 5.5 xHigh", "",
        "| Configuration | Its successes also solved by Opus xHigh | Solves Opus misses | Both miss |", "|---|---:|---:|---:|"]
    for k, v in extras.items():
        lines.append(f"| {labels[k]} | {v['percent_successes_also_opus_xhigh']:.2f}% | {v['solves_opus_xhigh_misses']} | {v['both_miss']} |")
    lines += ["", "## Pairwise counts", "", "| A | B | Both correct | Only A | Only B | Both unsuccessful |", "|---|---|---:|---:|---:|---:|"]
    for p in pairs:
        lines.append(f"| {labels[p['a']]} | {labels[p['b']]} | {p['both_correct']} | {p['only_a_correct']} | {p['only_b_correct']} | {p['both_incorrect']} |")
    for field in ("lakara", "prayoga"):
        lines += ["", "## " + field, "", "| Category | Tasks | " + " | ".join(labels[k] for k in xhigh) + " |", "|---|---:|"+"---:|"*len(xhigh)]
        for value, v in strata[field].items():
            lines.append(f"| {value} | {v['n']} | " + " | ".join(f"{v['accuracy'][k]:.2%}" for k in xhigh) + " |")
    lines += ["", "The CSV contains every task's correctness for every configuration. The JSON includes pairwise metrics, all-seven overlap, five-xHigh overlap, grammatical breakdowns, and source metadata. The task example file retains outcomes and gold forms for hard and disagreement cases.",
        "", "Coverage by any model uses the known gold labels; it does not establish that an ensemble could choose the right answer.", ""]
    (OUT / "report.md").write_text("\n".join(lines))
    print(json.dumps({"five_xhigh_models":report["five_xhigh_models"], "seven_configurations":report["seven_configurations"],
                      "compared_with_opus_xhigh":extras, "by_lakara":strata["lakara"], "by_prayoga":strata["prayoga"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
