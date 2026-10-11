"""Grade saved Opus responses without changing the frozen task or gold sets."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.correction import core
from benchmarks.correction.scoring import canonical_answer, grade, unique_object
from misc import oai_batch_eval as io, vp_goal as budget

DIRECTORY = core.DIRECTORY / "opus-50-20261009"


def normalized(value):
    return unicodedata.normalize("NFC", value) if isinstance(value, str) else value


def differences(actual, expected):
    if not isinstance(actual, dict):
        return [{"field": "answer", "expected": "A JSON object", "actual": actual}]
    changes = []
    if type(actual.get("first_incorrect_step")) is not int or actual.get("first_incorrect_step") != expected["first_incorrect_step"]:
        changes.append({"field": "first_incorrect_step", "expected": expected["first_incorrect_step"], "actual": actual.get("first_incorrect_step")})
    rows = actual.get("corrected_steps")
    if not isinstance(rows, list):
        changes.append({"field": "corrected_steps", "expected": "An ordered array of checkpoints", "actual": rows})
        rows = []
    expected_rows = expected["corrected_steps"]
    for index in range(max(len(rows), len(expected_rows))):
        actual_row = rows[index] if index < len(rows) else None
        expected_row = expected_rows[index] if index < len(expected_rows) else None
        if actual_row != expected_row:
            changes.append({"field": f"corrected_steps[{index}]", "expected": expected_row, "actual": actual_row})
    if normalized(actual.get("final_answer")) != expected["final_answer"]:
        changes.append({"field": "final_answer", "expected": expected["final_answer"], "actual": actual.get("final_answer")})
    return changes


def evaluate(task, receipt):
    body = receipt["body"]
    text = "\n".join(block["text"] for block in body.get("content", []) if block.get("type") == "text")
    parsed = None
    json_valid = True
    schema_valid = True
    try:
        parsed = json.loads(text, object_pairs_hook=unique_object)
    except (ValueError, TypeError, RecursionError):
        json_valid = False
    try:
        canonical_answer(text)
    except (ValueError, TypeError, RecursionError):
        schema_valid = False
    passed = grade(text, task["accepted_answers"])
    first_correct = (isinstance(parsed, dict) and type(parsed.get("first_incorrect_step")) is int
                     and parsed["first_incorrect_step"] == task["generation"]["first_incorrect_step"])
    final_correct = (isinstance(parsed, dict) and normalized(parsed.get("final_answer")) in
                     {answer["final_answer"] for answer in task["accepted_answers"]})
    candidate_diffs = [differences(parsed, answer) for answer in task["accepted_answers"]]
    closest = min(range(len(candidate_diffs)), key=lambda index: (len(candidate_diffs[index]), index))
    if passed:
        reason = "pass"
    elif body.get("stop_reason") in {"refusal", "max_tokens", "model_context_window_exceeded"}:
        reason = body["stop_reason"]
    elif not json_valid:
        reason = "invalid_json"
    elif not schema_valid:
        reason = "invalid_schema"
    elif not first_correct:
        reason = "wrong_first_error"
    elif not final_correct:
        reason = "wrong_final_word"
    else:
        reason = "trace_mismatch"
    return {
        "id": task["id"], "number": task["number"], "status": "pass" if passed else "fail",
        "strict_pass": passed, "first_error_correct": first_correct, "final_word_correct": final_correct,
        "json_valid": json_valid, "schema_valid": schema_valid, "reason": reason,
        "raw_output": text, "parsed_output": parsed, "closest_gold_index": closest,
        "differences": candidate_diffs[closest], "stop_reason": body.get("stop_reason"),
        "response_id": body.get("id"), "returned_model": body.get("model"),
        "latency_seconds": receipt.get("latency_seconds"), "usage": body.get("usage"),
        "receipt_file": "receipts/" + receipt["filename"],
    }


def wilson(correct, total):
    if not total:
        return None
    probability = correct / total
    zscore = 1.959963984540054
    denominator = 1 + zscore ** 2 / total
    center = (probability + zscore ** 2 / (2 * total)) / denominator
    radius = zscore * math.sqrt(probability * (1 - probability) / total + zscore ** 2 / (4 * total ** 2)) / denominator
    return [max(0, center - radius), min(1, center + radius)]


def analyze():
    plan = io.read_json(DIRECTORY / "plan.json")
    for name, fingerprint in plan["dependencies"].items():
        if io.sha256(ROOT / name) != fingerprint:
            raise ValueError("Frozen evaluation dependency changed: " + name)
    tasks = io.read_json(DIRECTORY / "tasks.json")
    results = []
    receipt_hashes = {}
    for index, task in enumerate(tasks):
        path = DIRECTORY / "receipts" / f"{index:03d}.json"
        error_path = path.with_suffix(".error.json")
        if path.exists():
            receipt = io.read_json(path)
            if receipt["task_id"] != task["id"] or receipt["body"]["model"] != plan["model"]:
                raise ValueError("Response identity mismatch")
            receipt["filename"] = path.name
            results.append(evaluate(task, receipt))
            receipt_hashes[str(path.relative_to(DIRECTORY))] = io.sha256(path)
        else:
            results.append({"id": task["id"], "number": task["number"],
                            "status": "error" if error_path.exists() else "pending",
                            "strict_pass": False, "reason": "api_error" if error_path.exists() else "pending",
                            "error": io.read_json(error_path) if error_path.exists() else None})
    completed = [row for row in results if row["status"] in {"pass", "fail"}]
    correct = sum(row["strict_pass"] for row in completed)
    summary = {
        "planned": len(tasks), "received": len(completed), "pending": sum(row["status"] == "pending" for row in results),
        "api_errors": sum(row["status"] == "error" for row in results),
        "strict_passes": correct, "strict_failures": len(completed) - correct,
        "strict_accuracy": correct / len(completed) if completed else None,
        "first_error_correct": sum(row["first_error_correct"] for row in completed),
        "final_word_correct": sum(row["final_word_correct"] for row in completed),
        "valid_json": sum(row["json_valid"] for row in completed),
        "valid_schema": sum(row["schema_valid"] for row in completed),
        "stop_reasons": dict(Counter(row["stop_reason"] for row in completed)),
        "failure_reasons": dict(Counter(row["reason"] for row in completed if not row["strict_pass"])),
        "descriptive_wilson95": wilson(correct, len(completed)),
        "interval_note": "Descriptive binomial interval; a selected 50-task pilot, not a population guarantee or repeat-generation study",
    }
    strata = {}
    for key in ["lakara", "gana", "error_coordinate"]:
        groups = {}
        for task, result in zip(tasks, results):
            value = (task["dhatu"][key] if key == "gana" else task["generation"]["changed_coordinate"]
                     if key == "error_coordinate" else task["morphology"][key])
            record = groups.setdefault(value, {"n": 0, "received": 0, "correct": 0})
            record["n"] += 1
            record["received"] += result["status"] in {"pass", "fail"}
            record["correct"] += result["strict_pass"]
        strata[key] = groups
    state = budget.load()
    job = state["jobs"].get(plan["job_id"], {})
    analysis = {
        "updated_at": io.now(), "model": plan["model"], "effort": plan["effort"],
        "tools_enabled": False, "internet_tools_enabled": False,
        "status": "complete" if not summary["pending"] else "running",
        "summary": summary, "strata": strata, "results": results,
        "sample_numbers": plan["task_numbers"], "sample_task_ids": plan["task_ids"],
        "plan_sha256": io.sha256(DIRECTORY / "plan.json"),
        "full_dataset_sha256": io.sha256(core.DIRECTORY / "tasks.json"),
        "receipt_hashes": receipt_hashes,
        "cost": {"actual_usd": job.get("actual_cost_upper_micro", 0) / 1e6,
                 "committed_usd": job.get("reservation_micro", 0) / 1e6,
                 "maximum_usd": plan["maximum_cost_micro"] / 1e6,
                 "billing_settled": job.get("settled", False),
                 "lifetime_anthropic_committed_usd": budget.committed(state, "Anthropic") / 1e6,
                 "lifetime_anthropic_cap_usd": 1000},
        "scoring": "Strict original schema plus complete gold-set membership; diagnostics do not change grades",
    }
    io.atomic_json(DIRECTORY / "analysis.json", analysis)
    return analysis


if __name__ == "__main__":
    result = analyze()
    print(json.dumps({"summary": result["summary"], "cost": result["cost"]}, indent=2))
