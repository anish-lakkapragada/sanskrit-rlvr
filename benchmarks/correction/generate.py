"""Generate the reproducible 200-root correction pilot without model calls."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.correction import core


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path, values):
    path.write_text("".join(core.canonical_json(value) + "\n" for value in values))


def class_quotas(groups, count):
    quotas = Counter({name: 0 for name in groups})
    ordered = sorted(groups, key=lambda name: (len(groups[name]), name))
    while sum(quotas.values()) < count:
        eligible = [name for name in ordered if quotas[name] < len(groups[name])]
        if not eligible:
            raise ValueError("Not enough distinct roots in the inventory")
        chosen = min(eligible, key=lambda name: (quotas[name], ordered.index(name)))
        quotas[chosen] += 1
    return quotas


def build(count=200, seed=core.SEED):
    entries, excluded = core.inventory_entries()
    groups = defaultdict(list)
    for entry in entries:
        groups[entry.dhatu.gana.name].append(entry)
    assigned_citations = set()
    for name in sorted(groups, key=lambda name: (len(groups[name]), name)):
        unique = []
        for entry in groups[name]:
            if entry.dhatu.aupadeshika not in assigned_citations:
                unique.append(entry)
                assigned_citations.add(entry.dhatu.aupadeshika)
        groups[name] = unique
    for name in groups:
        groups[name].sort(key=lambda entry: core.digest([seed, "entry", entry.code]))
    quotas = class_quotas(groups, count)
    slots = [core.coordinates(core.LAKARAS[index % 10], core.PERSONS[index % 3],
                              core.NUMBERS[(index // 3) % 3]) for index in range(count)]
    slots = [slot for _, slot in sorted(enumerate(slots), key=lambda pair: core.digest([seed, "slot", pair[0]]))]
    axes = [(core.AXES[index % 3], index) for index in range(count)]
    axes.sort(key=lambda pair: core.digest([seed, "axis", pair[1]]))
    used_codes = set()
    used_citations = set()
    class_counts = Counter()
    rejected = Counter()
    tasks = []
    evidence = []
    for number, (morphology, (axis, _)) in enumerate(zip(slots, axes), 1):
        names = sorted(
            [name for name in groups if class_counts[name] < quotas[name]],
            key=lambda name: (class_counts[name] / quotas[name], len(groups[name]),
                              core.digest([seed, "class", number, name])),
        )
        selected = None
        for name in names:
            for entry in groups[name]:
                if entry.code in used_codes or entry.dhatu.aupadeshika in used_citations:
                    continue
                try:
                    core.devanagari(entry.dhatu.aupadeshika)
                    core.devanagari(entry.artha)
                    candidates = core.candidates_for(entry, morphology, axis, seed)
                except core.Excluded as error:
                    rejected[str(error)] += 1
                    continue
                if candidates:
                    selected = entry, candidates[0]
                    break
                rejected["No valid donor satisfying the prefix/suffix constraints"] += 1
            if selected:
                break
        if selected is None:
            raise RuntimeError(f"Cannot fill slot {number}: {morphology}, error axis {axis}")
        entry, candidate = selected
        task, oracle = core.materialize(entry, candidate, number)
        tasks.append(task)
        evidence.append(oracle)
        used_codes.add(entry.code)
        used_citations.add(entry.dhatu.aupadeshika)
        class_counts[entry.dhatu.gana.name] += 1
    return tasks, evidence, {
        "inventory_entries": len(entries) + len(excluded),
        "held_inventory_entries": excluded,
        "class_quotas": dict(quotas), "candidate_exclusion_counts": dict(rejected),
    }


def summarize(tasks):
    def counts(values):
        return {str(key): value for key, value in sorted(Counter(values).items(), key=lambda pair: str(pair[0]))}
    return {
        "tasks": len(tasks), "unique_dictionary_entries": len({task["dhatu"]["code"] for task in tasks}),
        "unique_citations": len({task["dhatu"]["aupadeshika"] for task in tasks}),
        "max_tasks_per_dhatu": max(Counter(task["dhatu"]["code"] for task in tasks).values()),
        "gana": counts(task["dhatu"]["gana"] for task in tasks),
        **{axis: counts(task["morphology"][axis] for task in tasks)
           for axis in ("lakara", "prayoga", "purusha", "vacana")},
        "error_coordinate": counts(task["generation"]["changed_coordinate"] for task in tasks),
        "first_incorrect_step": counts(task["generation"]["first_incorrect_step"] for task in tasks),
        "accepted_answer_count": counts(len(task["accepted_answers"]) for task in tasks),
        "target_coordinate_cells": len({core.canonical_json(task["morphology"]) for task in tasks}),
        "proposed_checkpoints": {"min": min(len(task["proposed_steps"]) for task in tasks),
                                  "max": max(len(task["proposed_steps"]) for task in tasks)},
        "total_target_raw_paths": sum(task["generation"]["target_raw_paths"] for task in tasks),
    }


def generate(output, count=200, seed=core.SEED):
    output.mkdir(parents=True, exist_ok=True)
    tasks, evidence, selection = build(count, seed)
    write_json(output / "tasks.json", tasks)
    write_jsonl(output / "prompts.jsonl", [{"id": task["id"], "prompt": task["prompt"]} for task in tasks])
    write_jsonl(output / "answers.jsonl", [{"id": task["id"], "accepted_answers": task["accepted_answers"]} for task in tasks])
    write_jsonl(output / "oracle.jsonl", evidence)
    manifest = {
        "version": core.VERSION, "created_date": "2026-10-09", "seed": seed,
        "vidyut_version": core.VP_VERSION, "vp_settings": core.SETTINGS,
        "source_inventory": str(core.INVENTORY.relative_to(ROOT)),
        "source_inventory_sha256": core.file_sha(core.INVENTORY),
        "dictionary": str(core.DICTIONARY.relative_to(ROOT)),
        "dictionary_sha256": core.file_sha(core.DICTIONARY),
        "statistics": summarize(tasks), "selection": selection,
        "scope": "Ordinary 4D Kartari conjugation; one wrong tense, person, or number; VP-generated erroneous continuation",
        "trace_contract": "All consecutive-distinct nonempty Devanagari term arrays in VP order, preserving technical markers; final word separate",
        "first_error_definition": "First proposed checkpoint whose complete prefix is absent from every projected target path",
        "gold_policy": "All complete target continuations sharing the valid observed prefix; no mixing branches",
        "selection_policy": "One task per distinct dictionary entry and citation; capped balanced classes; input-seeded coordinates and donor selection; no model outcomes",
        "status": "Generated mechanical-verification pilot; no frontier-model evaluation or difficulty claim",
        "paid_api_calls": 0, "provider_cost_usd": {"Anthropic": 0, "OpenAI": 0},
        "files": {name: core.file_sha(output / name) for name in ("tasks.json", "prompts.jsonl", "answers.jsonl", "oracle.jsonl")},
        "generation_dependencies": {
            str(path.relative_to(ROOT)): core.file_sha(path)
            for path in [core.DIRECTORY / "core.py", core.DIRECTORY / "generate.py",
                         core.DIRECTORY / "prompt.txt", core.DIRECTORY / "scoring.py",
                         ROOT / "misc/vp_cartesian_task.py", ROOT / "misc/vp_campaign_candidates.py",
                         ROOT / "finetune/prompts.py"]
        },
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=core.DIRECTORY)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", default=core.SEED)
    arguments = parser.parse_args()
    manifest = generate(arguments.output, arguments.count, arguments.seed)
    print(json.dumps(manifest["statistics"], ensure_ascii=False, indent=2))
