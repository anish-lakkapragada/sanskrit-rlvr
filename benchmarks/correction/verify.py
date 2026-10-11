"""Regenerate all oracle branches and exercise the correction scorer offline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.correction import core
from benchmarks.correction.generate import build, summarize, write_json
from benchmarks.correction.scoring import canonical_answer, grade


def verify(directory, regeneration=True):
    tasks = json.loads((directory / "tasks.json").read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    oracle = [json.loads(line) for line in (directory / "oracle.jsonl").read_text().splitlines()]
    assert len(tasks) == len(oracle) == manifest["statistics"]["tasks"]
    assert len({task["id"] for task in tasks}) == len(tasks)
    assert len({task["dhatu"]["code"] for task in tasks}) == len(tasks)
    assert len({task["dhatu"]["aupadeshika"] for task in tasks}) == len(tasks)
    assert core.file_sha(core.INVENTORY) == manifest["source_inventory_sha256"]
    assert core.file_sha(core.DICTIONARY) == manifest["dictionary_sha256"]
    for name, expected in manifest["files"].items():
        assert core.file_sha(directory / name) == expected, name
    for name, expected in manifest["generation_dependencies"].items():
        assert core.file_sha(ROOT / name) == expected, name
    accepted = 0
    rejected = 0
    for task, witness in zip(tasks, oracle):
        assert task["id"] == witness["id"]
        target = core.derive_for(task["dhatu"]["code"], task["morphology"])
        assert target == witness["target_paths"]
        donor_coordinates = task["generation"]["donor_morphology"]
        changed = [key for key in task["morphology"] if task["morphology"][key] != donor_coordinates[key]]
        assert changed == [task["generation"]["changed_coordinate"]]
        assert task["morphology"]["prayoga"] == donor_coordinates["prayoga"] == "Kartari"
        assert witness["donor_path"] in core.derive_for(task["dhatu"]["code"], donor_coordinates)
        observed = task["proposed_steps"]
        assert observed == witness["donor_path"]["states"]
        assert task["proposed_final_answer"] == witness["donor_path"]["final_answer"]
        assert task["proposed_final_answer"] not in {path["final_answer"] for path in target}
        error_index = core.first_invalid_index(observed, target)
        assert error_index is not None and error_index >= 2
        assert len(observed) - error_index >= 2
        gold = core.accepted_repairs(observed, error_index, target)
        assert gold == task["accepted_answers"]
        assert len(gold) == len({canonical_answer(answer) for answer in gold})
        assert task["prompt"] == core.render_prompt(task)
        assert task["prompt_sha256"] == hashlib.sha256(task["prompt"].encode()).hexdigest()
        assert task["generation"]["first_incorrect_step"] == error_index + 1
        for answer in gold:
            assert grade(answer, gold)
            reordered = json.dumps(dict(reversed(list(answer.items()))), ensure_ascii=True, indent=4)
            assert grade(reordered, gold)
            assert grade(unicodedata.normalize("NFD", json.dumps(answer, ensure_ascii=False)), gold)
            accepted += 3
        answer = gold[0]
        bad_position = copy.deepcopy(answer)
        bad_position["first_incorrect_step"] += 1
        bad_middle = copy.deepcopy(answer)
        bad_middle["corrected_steps"][0]["terms"] = observed[error_index]
        bad_final = copy.deepcopy(answer)
        bad_final["final_answer"] = task["proposed_final_answer"]
        truncated = copy.deepcopy(answer)
        truncated["corrected_steps"] = truncated["corrected_steps"][:-1]
        final_only = {"final_answer": answer["final_answer"]}
        bool_position = copy.deepcopy(answer)
        bool_position["first_incorrect_step"] = True
        deeply_nested = "[" * 2000 + "0" + "]" * 2000
        for invalid in [bad_position, bad_middle, bad_final, truncated, final_only, bool_position, "not JSON", deeply_nested]:
            assert not grade(invalid, gold)
            rejected += 1
    assert manifest["statistics"] == summarize(tasks)
    if regeneration:
        regenerated, regenerated_oracle, _ = build(len(tasks), manifest["seed"])
        assert regenerated == tasks
        assert regenerated_oracle == oracle
    result = {
        "status": "passed", "tasks_checked": len(tasks),
        "vp_target_and_donor_regeneration": True, "complete_gold_sets_recomputed": True,
        "all_first_errors_verified_against_every_target_path": True,
        "deterministic_dataset_regeneration": regeneration,
        "accepted_format_checks": accepted, "rejected_incorrect_answers": rejected,
        "tasks_sha256": core.file_sha(directory / "tasks.json"),
        "verifier_sha256": core.file_sha(Path(__file__)), "paid_api_calls": 0,
        "limits": "Engine-relative mechanical verification; coordinate-substitution pilot; model difficulty unmeasured",
    }
    write_json(directory / "verification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=core.DIRECTORY)
    parser.add_argument("--skip-determinism-check", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.directory, not arguments.skip_determinism_check), indent=2))
