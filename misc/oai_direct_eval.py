#!/usr/bin/env python3
"""Fresh, one-attempt Sol xhigh evaluation through Standard Responses API.

Every task is attempted once, including tasks answered in older runs. Immutable
attempt markers prevent resends after a crash. Per-task results are durable;
the existing main JSON list is updated periodically and at completion.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as base
from misc import oai_replace_truncated as repair

MODEL = "gpt-6-sol"
EFFORT = "xhigh"
SLUG = f"{MODEL}-{EFFORT}"
CAP = 6000
WORK = Path(MODEL) / "_direct/xhigh-6000"
PENDING = {"prepared", "in_progress"}
RATES = {"input": 2.0, "cached_input": 0.2, "cache_write": 2.5, "output": 10.0}


def workdir(out):
    return out / WORK


def save_state(out, state):
    state["updated_at"] = base.now()
    base.atomic_json(workdir(out) / "state.json", state)


@contextmanager
def run_lock(out):
    workdir(out).mkdir(parents=True, exist_ok=True)
    with (workdir(out) / "runner.lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another direct runner owns this configuration") from None
        yield


def prepare(out, dataset=base.DATASET, expected_count=6687):
    state_path = workdir(out) / "state.json"
    if state_path.exists():
        return base.read_json(state_path)
    paths = base.configuration_paths(out, SLUG)
    tasks = base.read_json(dataset)
    if len(tasks) != expected_count or len({t["id"] for t in tasks}) != expected_count:
        raise ValueError(f"Expected {expected_count} unique tasks")
    previous_bytes = paths["result"].read_bytes()
    previous = json.loads(previous_bytes)
    if not isinstance(previous, list) or [r["task"] for r in previous] != tasks:
        raise ValueError("Previous Sol tasks do not exactly match full-tasks.json")
    run_id = "direct-sol-xhigh-" + uuid4().hex[:12]
    rows = []
    for i, (task, old) in enumerate(zip(tasks, previous)):
        request = copy.deepcopy(old["request"])
        body = request["body"]
        if (body["model"] != MODEL or body["reasoning"] != {"mode": "standard", "effort": EFFORT}
                or body.get("tools") != [] or body.get("tool_choice") != "none"
                or request["method"] != "POST" or request["url"] != "/v1/responses"):
            raise ValueError("Previous request differs from the authorized configuration")
        if body["input"] != [{"role": "user", "content": base.render_vp_task(task, base.TEMPLATE)}]:
            raise ValueError("Saved prompt differs from prompts/v1/vp_task_eval.txt")
        body.update(max_output_tokens=CAP, service_tier="default")
        row = base.base_record(task, i, request, run_id, SLUG)
        row.update(schema_version=2, transport="direct", attempt_number=1, attempted_at=None,
                   raw_response=None, http_status=None, request_id=None)
        rows.append(row)
    if len({r["custom_id"] for r in rows}) != expected_count:
        raise ValueError("Duplicate custom IDs")
    work = workdir(out)
    repair.backup(work / "previous-results.json", previous_bytes)
    repair.backup(work / "previous-meta.json", paths["meta"].read_bytes())
    repair.backup(work / "prepared.json", repair.json_bytes(rows))
    repair.backup(work / "tasks.snapshot.json", Path(dataset).read_bytes())
    repair.backup(work / "prompt.snapshot.txt", (ROOT / "prompts" / base.TEMPLATE).read_bytes())
    state = {"schema_version": 2, "run_id": run_id, "created_at": base.now(),
             "model": MODEL, "effort": EFFORT, "transport": "direct", "service_tier": "default",
             "max_output_tokens": CAP, "evaluation_max_output_tokens": CAP,
             "uniform_request_cap": True, "task_count": expected_count, "samples_per_task": 1,
             "sdk_max_retries": 0, "retry_failed_tasks": False, "retry_truncated_tasks": False,
             "timeout_seconds": 600, "max_workers": 64, "minimum_request_interval_seconds": 0.1,
             "snapshot_interval_seconds": 15, "status": "prepared", "finished_at": None,
             "dataset_sha256": base.sha256(dataset), "prepared_sha256": base.sha256(work / "prepared.json"),
             "prompt_template": "prompts/" + base.TEMPLATE,
             "prompt_sha256": base.sha256(work / "prompt.snapshot.txt"),
             "result_path": str(paths["result"].relative_to(out)),
             "meta_path": str(paths["meta"].relative_to(out)), "work_dir": str(WORK),
             "previous_result_sha256": hashlib.sha256(previous_bytes).hexdigest(),
             "result_sha256": hashlib.sha256(previous_bytes).hexdigest(),
             "pending_publish_sha256": None,
             "maximum_new_cost_usd_at_460_input_tokens": expected_count * (460 * 2 + CAP * 10) / 1e6}
    save_state(out, state)
    publish(out, state, rows)
    return state


def task_paths(out, row):
    work = workdir(out)
    cid = row["custom_id"]
    return {"attempt": work / "attempts" / f"{cid}.json",
            "response": work / "responses" / f"{cid}.http.json",
            "record": work / "records" / f"{cid}.json"}


def score_receipt(seed, receipt, attempt):
    # Use the existing parser/scorer, without pretending this is a Batch result.
    adapter = {"custom_id": seed["custom_id"], "error": None,
               "response": {"status_code": receipt["status_code"], "body": receipt["body"]}}
    row = base.apply_result(seed, adapter, receipt["received_at"])
    row.update(raw_batch_result=None, raw_response=receipt["body"],
               response_headers=receipt["headers"], http_status=receipt["status_code"],
               request_id=dict((k.lower(), v) for k, v in receipt["headers"]).get("x-request-id"),
               attempted_at=attempt["attempted_at"], latency_ms=receipt["latency_ms"])
    return row


def load_rows(out, state):
    work = workdir(out)
    if base.sha256(work / "prepared.json") != state["prepared_sha256"]:
        raise ValueError("Prepared task snapshot changed")
    rows = base.read_json(work / "prepared.json")
    for i, seed in enumerate(rows):
        paths = task_paths(out, seed)
        if paths["record"].exists():
            row = base.read_json(paths["record"])
            if any(row[k] != seed[k] for k in ("run_id", "custom_id", "task_id", "task", "request", "task_index")):
                raise ValueError("Saved response identity differs from prepared task")
            rows[i] = row
        elif paths["attempt"].exists():
            try:
                attempt = base.read_json(paths["attempt"])
            except (ValueError, OSError):
                attempt = {"attempted_at": None}
            if paths["response"].exists():
                row = score_receipt(seed, base.read_json(paths["response"]), attempt)
            else:
                row = copy.deepcopy(seed)
                row.update(status="unknown_outcome", attempted_at=attempt.get("attempted_at"),
                           collected_at=base.now(), is_correct=None,
                           error={"code": "interrupted_attempt", "message": "Attempt marker exists without a saved response; not resent. Billing outcome unknown."})
            base.atomic_json(paths["record"], row)
            rows[i] = row
    return rows


def claim_attempt(path, attempt):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation is the no-repeat guard, independent of snapshots.
    with path.open("x") as f:
        json.dump(attempt, f)
        f.flush()
        os.fsync(f.fileno())


def execute_one(client, out, seed):
    paths = task_paths(out, seed)
    attempt = {"run_id": seed["run_id"], "custom_id": seed["custom_id"],
               "task_id": seed["task_id"], "attempted_at": base.now(), "attempt_number": 1}
    claim_attempt(paths["attempt"], attempt)
    started = time.monotonic()
    try:
        raw = client.responses.with_raw_response.create(**seed["request"]["body"])
    except Exception as exc:
        error = base.error_details(exc, client)
        row = copy.deepcopy(seed)
        row.update(status="api_error", attempted_at=attempt["attempted_at"], collected_at=base.now(),
                   latency_ms=round((time.monotonic() - started) * 1000, 3),
                   http_status=error.get("status_code"), request_id=error.get("request_id"),
                   response_headers=error.get("headers"), raw_response=error.get("body"),
                   is_correct=None, error=error)
    else:
        latency_ms = round((time.monotonic() - started) * 1000, 3)
        # Persist the complete unknown-field-preserving response before scoring.
        receipt = {"received_at": base.now(), "status_code": raw.status_code,
                   "headers": list(raw.headers.multi_items()), "body": raw.http_response.json(),
                   "latency_ms": latency_ms}
        base.atomic_json(paths["response"], receipt)
        row = score_receipt(seed, receipt, attempt)
    base.atomic_json(paths["record"], row)
    return row


def usage_totals(rows):
    return repair.usage_of([{"raw_batch_result": {"response": {"body": r.get("raw_response")}}} for r in rows])


def metadata(state, rows):
    usage = usage_totals(rows)
    cached, written = usage.get("cached_input_tokens", 0), usage.get("cache_write_tokens", 0)
    cost = ((usage.get("input_tokens", 0) - cached - written) * RATES["input"]
            + cached * RATES["cached_input"] + written * RATES["cache_write"]
            + usage.get("output_tokens", 0) * RATES["output"]) / 1e6
    progress = {"total": len(rows), "finished": sum(r["status"] not in PENDING for r in rows),
                "in_flight": sum(r["status"] == "in_progress" for r in rows),
                "pending": sum(r["status"] == "prepared" for r in rows),
                "attempted": sum(r["status"] != "prepared" for r in rows)}
    return {**state, "progress": progress,
            "summary": {**base.summarize(rows), "final": state["finished_at"] is not None},
            "usage_totals": usage, "estimated_cost_usd": cost,
            "cost_is_usage_estimate_not_invoice": True,
            "unknown_billing_outcomes": sum(r["status"] == "unknown_outcome" or
                (r["status"] == "api_error" and r.get("http_status") is None) for r in rows),
            "prices_usd_per_million_tokens": RATES,
            "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6-sol",
            "previous_results_backup": str(WORK / "previous-results.json"),
            "evaluation_protocol": "Fresh direct Standard run; one attempt per task, cap 6000 including reasoning. No retries or reuse of earlier answers. API failures remain in the all-task denominator."}


def publish(out, state, rows):
    payload = repair.json_bytes(rows)
    new_hash = repair.digest(payload)
    destination = out / state["result_path"]
    with base.lock(out):
        acceptable = {state["result_sha256"], state.get("pending_publish_sha256")}
        if base.sha256(destination) not in acceptable:
            raise ValueError("Main result file changed externally; refusing to overwrite")
        state["pending_publish_sha256"] = new_hash
        save_state(out, state)
        base.atomic_bytes(destination, payload)
        state.update(result_sha256=new_hash, pending_publish_sha256=None)
        meta = metadata(state, rows)
        base.atomic_json(out / state["meta_path"], meta)
        state["progress"] = meta["progress"]
        state["estimated_cost_usd"] = meta["estimated_cost_usd"]
        save_state(out, state)
        print(base.now(), json.dumps({"status": state["status"], **meta["progress"],
              "correct": meta["summary"]["correct"], "truncated": meta["summary"]["truncated"],
              "api_errors": meta["summary"]["statuses"].get("api_error", 0),
              "estimated_cost_usd": round(meta["estimated_cost_usd"], 4)}), flush=True)


def run(out):
    with run_lock(out):
        state = base.read_json(workdir(out) / "state.json")
        if state["finished_at"]:
            print("This direct run is already finished; no requests sent", flush=True)
            return
        rows = load_rows(out, state)
        pending = iter(i for i, row in enumerate(rows) if row["status"] == "prepared")
        stopping = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stopping.set())
        client = base.api_client().with_options(timeout=state["timeout_seconds"])
        state.update(status="running", process_id=os.getpid(), last_started_at=base.now())
        publish(out, state, rows)
        active, exhausted = {}, False
        next_dispatch = time.monotonic()
        last_publish = time.monotonic()
        try:
            with ThreadPoolExecutor(max_workers=state["max_workers"]) as pool:
                while active or (not exhausted and not stopping.is_set()):
                    current = time.monotonic()
                    if not exhausted and not stopping.is_set() and len(active) < state["max_workers"] and current >= next_dispatch:
                        i = next(pending, None)
                        if i is None:
                            exhausted = True
                        else:
                            rows[i]["status"] = "in_progress"
                            active[pool.submit(execute_one, client, out, rows[i])] = i
                            next_dispatch = current + state["minimum_request_interval_seconds"]
                    if active:
                        done, _ = wait(active, timeout=0.1, return_when=FIRST_COMPLETED)
                        for future in done:
                            i = active.pop(future)
                            # A persistence failure stops dispatch; it must not be
                            # hidden as an API error or create an extra attempt.
                            rows[i] = future.result()
                    if time.monotonic() - last_publish >= state["snapshot_interval_seconds"]:
                        publish(out, state, rows)
                        last_publish = time.monotonic()
                if all(r["status"] not in PENDING for r in rows):
                    state.update(status="completed", finished_at=base.now())
                else:
                    state["status"] = "stopped"
                publish(out, state, rows)
        except Exception as exc:
            state.update(status="runner_error", last_runner_error=base.error_details(exc, client))
            save_state(out, state)
            raise
        finally:
            client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "status"))
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks/oai")
    args = parser.parse_args()
    out = args.out.resolve()
    if args.command == "prepare":
        with run_lock(out):
            state = prepare(out)
        print(json.dumps({k: state[k] for k in ("run_id", "task_count", "max_output_tokens", "service_tier", "maximum_new_cost_usd_at_460_input_tokens")}), flush=True)
    elif args.command == "run":
        run(out)
    else:
        state = base.read_json(workdir(out) / "state.json")
        print(json.dumps({k: state.get(k) for k in ("run_id", "status", "progress", "updated_at", "estimated_cost_usd", "finished_at", "last_runner_error")}, indent=2))


if __name__ == "__main__":
    main()
