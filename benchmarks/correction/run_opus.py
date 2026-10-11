"""Frozen 50-task Opus pilot with shared lifetime budget accounting."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.correction import core
from misc import ant_batch_eval as ant, oai_batch_eval as io, vp_goal as budget
from misc.vp_continuous64k import transaction

DIRECTORY = core.DIRECTORY / "opus-50-20261009"
JOB = "correction-opus50-20261009"
MODEL = "claude-opus-5-5"
OUTPUT_CAP = 65536
INPUT_CAP = 8192
WORKERS = 16
MAXIMUM_PER_TASK = INPUT_CAP * 4 + OUTPUT_CAP * 20
MAXIMUM_TOTAL = 50 * MAXIMUM_PER_TASK


def select_tasks(tasks):
    groups = {tense: [task for task in tasks if task["morphology"]["lakara"] == tense]
              for tense in sorted({task["morphology"]["lakara"] for task in tasks})}
    if len(groups) != 10 or any(len(group) < 5 for group in groups.values()):
        raise ValueError("Require ten tense strata with at least five tasks")
    proposals = []
    for seed_index in range(256):
        seed = f"correction-opus50-20261009-{seed_index}"
        selected = [task for tense, group in groups.items()
                    for task in sorted(group, key=lambda task: core.digest([seed, task["id"]]))[:5]]
        classes = Counter(task["dhatu"]["gana"] for task in selected)
        axes = Counter(task["generation"]["changed_coordinate"] for task in selected)
        persons = Counter(task["morphology"]["purusha"] for task in selected)
        numbers = Counter(task["morphology"]["vacana"] for task in selected)
        penalty = (-len(classes), sum((count - 50 / 3) ** 2 for count in axes.values()),
                   sum((count - 50 / 3) ** 2 for count in persons.values()) +
                   sum((count - 50 / 3) ** 2 for count in numbers.values()), seed_index)
        proposals.append((penalty, seed, selected))
    _, seed, selected = min(proposals, key=lambda item: item[0])
    selected.sort(key=lambda task: task["number"])
    return selected, seed


def params(task):
    return {
        "model": MODEL, "max_tokens": OUTPUT_CAP,
        "messages": [{"role": "user", "content": task["prompt"]}],
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": "xhigh"}, "tools": [], "tool_choice": {"type": "none"},
        "stream": False, "service_tier": "standard_only", "inference_geo": "global",
    }


def prepare():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    plan_path = DIRECTORY / "plan.json"
    if plan_path.exists():
        return inspect()[0]
    verification = io.read_json(core.DIRECTORY / "verification.json")
    independent = io.read_json(core.DIRECTORY / "independent-audit.json")
    task_sha = io.sha256(core.DIRECTORY / "tasks.json")
    if verification["status"] != "passed" or not independent["passed"]:
        raise ValueError("Correction task verification failed")
    if verification["tasks_sha256"] != task_sha or independent["tasks_sha256"] != task_sha:
        raise ValueError("Correction verification is stale")
    selected, seed = select_tasks(io.read_json(core.DIRECTORY / "tasks.json"))
    requests = [params(task) for task in selected]
    client = ant.api_client()
    model = client.models.retrieve(MODEL).model_dump(mode="json")
    if model.get("id") != MODEL or model.get("max_tokens", 0) < OUTPUT_CAP:
        raise ValueError("Unexpected model identity or output ceiling")
    io.atomic_json(DIRECTORY / "model-preflight.json", model)
    def count(request):
        result = client.messages.count_tokens(
            model=MODEL, messages=request["messages"], thinking=request["thinking"],
            tools=[], tool_choice={"type": "none"})
        return result.input_tokens
    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(count, requests))
    if any(type(counted) is not int or counted + 256 > INPUT_CAP for counted in counts):
        raise ValueError("Input allowance exceeded; no generation submitted")
    io.atomic_json(DIRECTORY / "tasks.json", selected)
    io.atomic_json(DIRECTORY / "requests.json", requests)
    io.atomic_json(DIRECTORY / "input-counts.json", counts)
    state = budget.load()
    dependencies = [core.DIRECTORY / "tasks.json", core.DIRECTORY / "scoring.py", Path(__file__),
                    DIRECTORY / "tasks.json", DIRECTORY / "requests.json", DIRECTORY / "input-counts.json"]
    plan = {
        "created_at": io.now(), "job_id": JOB, "provider": "Anthropic", "model": MODEL,
        "n": 50, "effort": "xhigh", "max_output_tokens": OUTPUT_CAP, "input_allowance": INPUT_CAP,
        "concurrency": WORKERS, "transport": "direct", "sdk_max_retries": 0,
        "maximum_cost_micro": MAXIMUM_TOTAL, "maximum_per_task_micro": MAXIMUM_PER_TASK,
        "rates_micro_per_token": {"input": 4, "output": 20},
        "pricing_source": "https://platform.claude.com/docs/en/models/opus-5-5/overview",
        "pricing_checked_date": "2026-10-09", "seed": seed,
        "selection": "Input-only seeded selection: five per tense; choose among 256 seeds for all ten classes, balanced error types/person/number. No model outcomes used.",
        "task_ids": [task["id"] for task in selected], "task_numbers": [task["number"] for task in selected],
        "distribution": {
            "lakara": dict(Counter(task["morphology"]["lakara"] for task in selected)),
            "gana": dict(Counter(task["dhatu"]["gana"] for task in selected)),
            "error_coordinate": dict(Counter(task["generation"]["changed_coordinate"] for task in selected)),
        },
        "primary_scoring": "Unchanged strict structured full-answer membership in the frozen VP gold set",
        "secondary_diagnostics": "First-error position, final word, schema validity, and first differing checkpoint; none replaces strict pass rate",
        "stopping": "One request per frozen task; no paid retries, prompt edits, task replacement, or outcome-based stopping",
        "lifetime_caps_micro": {provider: config["cap_micro"] for provider, config in budget.PROVIDERS.items()},
        "before_committed_micro": {provider: budget.committed(state, provider) for provider in budget.PROVIDERS},
        "protected_allocation": budget.protected_allocations(state),
        "existing_execution_fence": state.get("status"),
        "fence_scope": "User explicitly authorized this new Anthropic-only correction pilot. Existing OpenAI infrastructure-failure fence and full unknown liability stay unchanged; this driver cannot resume old jobs.",
        "dependencies": {str(path.relative_to(ROOT)): io.sha256(path) for path in dependencies},
    }
    if budget.committed(state, "Anthropic") + budget.protected_remaining(state, "Anthropic") + MAXIMUM_TOTAL > 1_000_000_000:
        raise ValueError("Insufficient lifetime Anthropic budget")
    io.atomic_json(plan_path, plan)
    return plan


def inspect():
    plan = io.read_json(DIRECTORY / "plan.json")
    if (plan["job_id"] != JOB or plan["model"] != MODEL or plan["n"] != 50 or
            plan["maximum_cost_micro"] != MAXIMUM_TOTAL or plan["max_output_tokens"] != OUTPUT_CAP):
        raise ValueError("Frozen execution policy changed")
    for name, fingerprint in plan["dependencies"].items():
        if io.sha256(ROOT / name) != fingerprint:
            raise ValueError("Frozen dependency changed: " + name)
    tasks = io.read_json(DIRECTORY / "tasks.json")
    requests = io.read_json(DIRECTORY / "requests.json")
    if requests != [params(task) for task in tasks] or [task["id"] for task in tasks] != plan["task_ids"]:
        raise ValueError("Request or task membership changed")
    return plan, tasks, requests


def register(plan):
    with transaction():
        state = budget.load()
        if JOB in state["jobs"]:
            raise ValueError("This pilot has already been admitted; inspect receipts instead of replaying")
        if state.get("status") != plan["existing_execution_fence"]:
            raise ValueError("Shared execution state changed")
        if budget.protected_allocations(state) != plan["protected_allocation"]:
            raise ValueError("Protected budget allocation changed")
        if any(job.get("attempted_at") and not job.get("settled") and job["provider"] == "Anthropic"
               for job in state["jobs"].values()):
            raise ValueError("Unsettled Anthropic work must be reconciled first")
        if budget.committed(state, "Anthropic") + budget.protected_remaining(state, "Anthropic") + MAXIMUM_TOTAL > 1_000_000_000:
            raise ValueError("Insufficient lifetime Anthropic budget")
        if budget.committed(state, "OpenAI") > 2_000_000_000:
            raise ValueError("OpenAI liability already exceeds the authorized cap")
        state["jobs"][JOB] = {
            "id": JOB, "provider": "Anthropic", "phase": "correction_pilot_v1", "transport": "direct",
            "accounting_driver": "correction-opus50-v1", "n": 50, "batch_id": None,
            "created_at": io.now(), "attempted_at": io.now(), "settled": False, "collected_at": None,
            "reservation_micro": MAXIMUM_TOTAL, "actual_cost_upper_micro": 0, "status": "running",
            "plan_sha256": io.sha256(DIRECTORY / "plan.json"), "request_accounts": {},
        }
        budget.save(state)


def settle(index, receipt=None, error=None):
    actual = None
    if receipt:
        usage = receipt.get("usage") or {}
        valid = (receipt.get("model") == MODEL and receipt.get("id") and receipt.get("type") == "message"
                 and type(usage.get("input_tokens")) is int and 0 <= usage["input_tokens"] <= INPUT_CAP
                 and type(usage.get("output_tokens")) is int and 0 <= usage["output_tokens"] <= OUTPUT_CAP
                 and usage.get("service_tier") == "standard" and usage.get("inference_geo") == "global"
                 and not usage.get("cache_creation_input_tokens", 0) and not usage.get("cache_read_input_tokens", 0))
        if valid:
            actual = usage["input_tokens"] * 4 + usage["output_tokens"] * 20
    with transaction():
        state = budget.load()
        job = state["jobs"][JOB]
        if str(index) in job["request_accounts"]:
            raise ValueError("Attempt already settled or recorded")
        job["request_accounts"][str(index)] = {
            "state": "settled" if actual is not None else "unknown_liability_retained",
            "maximum_cost_micro": MAXIMUM_PER_TASK, "actual_cost_upper_micro": actual,
            "response_id": receipt.get("id") if receipt else None,
            "error": error if error else (None if actual is not None else "Receipt usage could not be validated"),
        }
        accounts = list(job["request_accounts"].values())
        cost = sum(record["actual_cost_upper_micro"] or 0 for record in accounts)
        unknown = 50 - sum(record["state"] == "settled" for record in accounts)
        job["actual_cost_upper_micro"] = cost
        job["reservation_micro"] = cost + unknown * MAXIMUM_PER_TASK
        complete = len(accounts) == 50 and unknown == 0
        job["settled"] = complete
        job["collected_at"] = io.now() if complete else None
        job["status"] = "complete" if complete else "running_or_unknown_liability"
        budget.save(state)
        snapshot = {"updated_at": io.now(), "n": 50, "received": len(accounts), "settled": 50 - unknown,
                    "actual_cost_usd": cost / 1e6, "committed_usd": job["reservation_micro"] / 1e6,
                    "complete": complete, "job_id": JOB}
        io.atomic_json(DIRECTORY / "execution.json", snapshot)
    return snapshot


def execute():
    with (DIRECTORY / "executor.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan, tasks, requests = inspect()
        register(plan)
        client = ant.api_client().with_options(timeout=600.0, max_retries=0)
        def call(index):
            path = DIRECTORY / "receipts" / f"{index:03d}.json"
            intent = path.with_suffix(".intent.json")
            if intent.exists() or path.exists():
                raise ValueError("Request already attempted; no replay")
            io.atomic_json(intent, {"at": io.now(), "task_id": tasks[index]["id"], "request_sha256": core.digest(requests[index])})
            started = time.monotonic()
            try:
                message = client.messages.create(**requests[index])
                receipt = message.model_dump(mode="json")
                io.atomic_json(path, {"task_id": tasks[index]["id"], "received_at": io.now(),
                                     "latency_seconds": time.monotonic() - started, "body": receipt})
                return index, receipt, None
            except Exception as exception:
                error = {"type": type(exception).__name__, "http_status": getattr(exception, "status_code", None),
                         "request_id": getattr(exception, "request_id", None)}
                io.atomic_json(path.with_suffix(".error.json"), error)
                return index, None, error
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(call, index) for index in range(50)]
            for future in as_completed(futures):
                index, receipt, error = future.result()
                snapshot = settle(index, receipt, error)
                print(json.dumps({"task_number": tasks[index]["number"], **snapshot}), flush=True)
        return io.read_json(DIRECTORY / "execution.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run"])
    arguments = parser.parse_args()
    result = prepare() if arguments.command == "prepare" else execute()
    if arguments.command == "prepare":
        print(json.dumps({key: result[key] for key in ["n", "distribution", "maximum_cost_micro", "effort", "concurrency"]}, indent=2))
    else:
        print(json.dumps(result, indent=2))
