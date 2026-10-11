"""Independently audit saved pilot requests, receipts, scores, and costs; no API calls."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from misc import vp_goal as budget

DIRECTORY = Path(__file__).resolve().parent / "opus-50-20261009"


def read(path):
    return json.loads(path.read_text())


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, "Duplicate JSON key"
        result[key] = value
    return result


def normalize(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def verify():
    plan, tasks, requests, analysis = [read(DIRECTORY / name) for name in
                                       ["plan.json", "tasks.json", "requests.json", "analysis.json"]]
    assert len(tasks) == len(requests) == len(analysis["results"]) == 50
    for name, sha in plan["dependencies"].items():
        assert fingerprint(ROOT / name) == sha, name
    all_tasks = {task["id"]: task for task in read(DIRECTORY.parent / "tasks.json")}
    assert all(task == all_tasks[task["id"]] for task in tasks)
    assert len({task["id"] for task in tasks}) == 50
    assert len({task["dhatu"]["code"] for task in tasks}) == 50
    assert Counter(task["morphology"]["lakara"] for task in tasks) == Counter(plan["distribution"]["lakara"])
    assert set(plan["distribution"]["lakara"].values()) == {5}
    assert len(plan["distribution"]["gana"]) == 10
    response_ids, scores, first_errors, final_words, costs = set(), [], [], [], []
    state = budget.load()
    job = state["jobs"][plan["job_id"]]
    for index, (task, request, result) in enumerate(zip(tasks, requests, analysis["results"])):
        assert request["tools"] == [] and request["tool_choice"] == {"type": "none"}
        assert "system" not in request
        assert request["messages"] == [{"role": "user", "content": task["prompt"]}]
        assert request["output_config"] == {"effort": "xhigh"}
        assert request["model"] == plan["model"] == "claude-opus-5-5"
        path = DIRECTORY / "receipts" / f"{index:03d}.json"
        assert fingerprint(path) == analysis["receipt_hashes"][str(path.relative_to(DIRECTORY))]
        receipt = read(path)
        body = receipt["body"]
        assert receipt["task_id"] == task["id"] == result["id"]
        assert body["model"] == request["model"] and body["stop_reason"] == "end_turn"
        assert {block["type"] for block in body["content"]} <= {"thinking", "text"}
        assert body["id"] not in response_ids
        response_ids.add(body["id"])
        text = "\n".join(block["text"] for block in body["content"] if block["type"] == "text")
        parsed = json.loads(text, object_pairs_hook=unique_keys)
        assert set(parsed) == {"first_incorrect_step", "corrected_steps", "final_answer"}
        assert type(parsed["first_incorrect_step"]) is int
        assert isinstance(parsed["corrected_steps"], list) and parsed["corrected_steps"]
        assert isinstance(parsed["final_answer"], str) and parsed["final_answer"]
        for offset, checkpoint in enumerate(parsed["corrected_steps"]):
            assert set(checkpoint) == {"step", "terms"}
            assert type(checkpoint["step"]) is int
            assert checkpoint["step"] == parsed["first_incorrect_step"] + offset
            assert isinstance(checkpoint["terms"], list) and checkpoint["terms"]
            assert all(isinstance(term, str) and term for term in checkpoint["terms"])
        gold = [normalize(answer) for answer in task["accepted_answers"]]
        normalized = normalize(parsed)
        scores.append(normalized in gold)
        first_errors.append(normalized["first_incorrect_step"] == task["generation"]["first_incorrect_step"])
        final_words.append(normalized["final_answer"] in {answer["final_answer"] for answer in gold})
        assert scores[-1] == result["strict_pass"]
        assert text == result["raw_output"] and parsed == result["parsed_output"]
        usage = body["usage"]
        assert not usage.get("server_tool_use")
        assert not usage.get("cache_creation_input_tokens") and not usage.get("cache_read_input_tokens")
        assert usage["service_tier"] == "standard" and usage["inference_geo"] == "global"
        costs.append(usage["input_tokens"] * 4 + usage["output_tokens"] * 20)
        account = job["request_accounts"][str(index)]
        assert account["state"] == "settled" and account["response_id"] == body["id"]
        assert account["actual_cost_upper_micro"] == costs[-1]
    assert sum(scores) == analysis["summary"]["strict_passes"] == 24
    assert sum(first_errors) == sum(final_words) == 50
    assert sum(costs) == job["actual_cost_upper_micro"] == job["reservation_micro"] == 2267960
    assert job["settled"] and job["status"] == "complete"
    assert sum(costs) / 1e6 == analysis["cost"]["actual_usd"]
    assert state["status"] == plan["existing_execution_fence"]
    for provider, cap in plan["lifetime_caps_micro"].items():
        assert budget.committed(state, provider) <= cap
    report = {
        "verified_at": datetime.now(timezone.utc).isoformat(), "passed": True,
        "requests_and_receipts_checked": 50, "unique_response_ids": len(response_ids),
        "tools_explicitly_disabled": True, "no_tool_response_blocks_or_server_tool_usage": True,
        "exact_saved_prompts_without_extra_messages": True,
        "independent_full_answer_matches": sum(scores), "correct_first_errors": sum(first_errors),
        "correct_final_words": sum(final_words), "all_finished_normally": True,
        "actual_cost_usd": sum(costs) / 1e6, "cost_matches_lifetime_ledger": True,
        "lifetime_caps_respected": True, "existing_execution_fence_unchanged": True,
        "analysis_sha256": fingerprint(DIRECTORY / "analysis.json"),
    }
    (DIRECTORY / "evaluation-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
