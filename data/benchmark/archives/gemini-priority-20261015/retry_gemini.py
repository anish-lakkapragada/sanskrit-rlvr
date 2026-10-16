"""Explicit, resumable retries of infrastructure failures; replace selected rows."""

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_gemini as runner


def retry_failed(folder, batch_id, expected_count, concurrency=7, budget=None):
    with (folder / "run.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return retry_locked(folder, batch_id, expected_count, concurrency, budget)


def retry_locked(folder, batch_id, expected_count, concurrency, budget):
    manifest, tasks, prompts, validator = runner.load_inputs(folder)
    execution = manifest["execution"]
    budget = execution["budget_usd"] if budget is None else budget
    runner.check_budget(manifest, budget)
    if execution.get("retry_runner"):
        runner.base.verify_descriptor(execution["retry_runner"])
    journals = {f: runner.base.Journal(folder / "journals" / f"{f}.jsonl") for f in tasks}
    started, attempts, unresolved = runner.recover_attempts(journals, tasks, manifest, prompts)
    if unresolved:
        raise RuntimeError("Unresolved started attempts must be inspected; never automatically resend")
    records = runner.base.latest_records(attempts)
    if any(len(records[f]) != len(tasks[f]) for f in tasks):
        raise RuntimeError("Finish all primary tasks before explicitly retrying infrastructure failures")
    batches = execution.setdefault("retry_batches", [])
    matches = [batch for batch in batches if batch["id"] == batch_id]
    if len(matches) > 1:
        raise RuntimeError("Duplicate retry batch ID")
    if matches:
        batch = matches[0]
        if len(batch["targets"]) != expected_count:
            raise RuntimeError("Existing retry batch has a different target count")
    else:
        runner.inspect(folder, verify=True)
        targets = [{"family": f, "task_id": task_id, "attempt_number": row["attempt_number"] + 1}
                   for f in tasks for task_id, row in records[f].items()
                   if runner.transient_failure(row)]
        if len(targets) != expected_count:
            raise RuntimeError(f"Expected {expected_count} infrastructure failures, found {len(targets)}")
        batch = {"id": batch_id, "authorized_at": runner.base.now(),
                 "authorization": "User requested the same completed benchmark workflow for Gemini 4 Argon, including infrastructure failure recovery. No retries of completed answers or refusals.",
                 "targets": targets, "state": "planned", "started_at": None, "finished_at": None}
        batches.append(batch)
    target_keys = [(t["family"], t["task_id"], t["attempt_number"]) for t in batch["targets"]]
    if len(set(target_keys)) != len(target_keys):
        raise RuntimeError("Duplicate target in retry batch")
    pending = [key for key in target_keys if key not in started]
    for family, task_id, attempt in pending:
        prior = records[family][task_id]
        if attempt != prior["attempt_number"] + 1 or not runner.transient_failure(prior):
            raise RuntimeError("Retry target is no longer the recorded infrastructure failure")
    reserve = runner.base.reserve_per_request(manifest, prompts)
    progress = runner.base.summarize_attempts(attempts, started)
    if progress["known_cost_usd"] + (progress["unknown_cost_attempts"] + len(pending)) * reserve > budget:
        raise RuntimeError("Budget cannot reserve the full uncapped allowance for this retry batch")
    key = runner.ADCToken() if pending else None
    if key:
        key.get()
    execution.update(
        retry_runner={"path": str(Path(__file__).relative_to(ROOT)), "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        active_retry_batch=batch_id, state="running", pid=os.getpid(), concurrency=concurrency,
        reservation_usd_per_inflight_request=reserve, stopped_reason=None,
        explicit_retries="Explicitly authorized infrastructure retries replace the selected row in place. All attempts and charges remain in journals; no automatic retries.")
    manifest.update(status="running", finished_at=None)
    batch.update(state="running", started_at=batch["started_at"] or runner.base.now())
    futures, cursor = {}, 0
    state = {"stop": None}

    def checkpoint():
        progress = runner.base.summarize_attempts(attempts, started)
        progress["unknown_cost_reserve_usd"] = round(progress["unknown_cost_attempts"] * reserve, 8)
        execution["progress"] = progress
        execution["stopped_reason"] = state["stop"]
        execution["submission_state"] = ("draining" if state["stop"] or cursor == len(pending) else "submitting") if manifest["status"] == "running" else manifest["status"]
        manifest["submitted_requests"] = len(started)
        batch["submitted"] = sum(k in started for k in target_keys)
        batch["settled"] = sum(k[1:] in attempts[k[0]] for k in target_keys)
        runner.base.atomic_write(folder / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        return progress

    def handle_signal(number, frame):
        state["stop"] = f"Received signal {number}; save in-flight retries and pause"

    old_handlers = {s: signal.signal(s, handle_signal) for s in (signal.SIGINT, signal.SIGTERM)}
    checkpoint()  # Persist the explicit target list before any paid request.
    try:
        with httpx.Client(timeout=httpx.Timeout(1800, connect=30), follow_redirects=False,
                          transport=httpx.HTTPTransport(retries=0, limits=httpx.Limits(max_connections=concurrency))) as client, ThreadPoolExecutor(max_workers=concurrency) as pool:
            while cursor < len(pending) or futures:
                while state["stop"] is None and cursor < len(pending) and len(futures) < concurrency:
                    family, task_id, attempt = pending[cursor]
                    cursor += 1
                    body = runner.request_body(prompts[family, task_id], manifest["request_defaults"])
                    marker = {"event": "started", "task_id": task_id, "attempt_number": attempt,
                              "timestamp": runner.base.now(), "client_request_id": str(uuid.uuid4()), "request": body}
                    journals[family].append(marker)
                    started[family, task_id, attempt] = {k: v for k, v in marker.items() if k != "request"}
                    future = pool.submit(runner.execute, client, manifest, task_id, body,
                                         marker["client_request_id"], journals[family], key, attempt_number=attempt)
                    futures[future] = (family, task_id, attempt)
                checkpoint()
                if not futures:
                    break
                done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    family, task_id, attempt = futures.pop(future)
                    row = runner.result_row(future.result(), tasks[family][task_id], manifest)
                    validator.validate([row])
                    attempts[family][task_id, attempt] = row
                    records[family][task_id] = row
                    runner.base.write_results(folder, family, records[family], tasks[family])
                    print(runner.base.compact({"at": runner.base.now(), "family": family, "task_id": task_id,
                                          "attempt_number": attempt, "status": row["status"],
                                          "correct": row["correct"], "cost_usd": row["cost_usd"],
                                          "refusal_category": ((row.get("error") or {}).get("stop_details") or {}).get("category")}), flush=True)
                checkpoint()
    finally:
        for s, handler in old_handlers.items():
            signal.signal(s, handler)
        started, attempts, unresolved = runner.recover_attempts(journals, tasks, manifest, prompts)
        records = runner.base.latest_records(attempts)
        for family in tasks:
            validator.validate(list(records[family].values()))
            runner.base.write_results(folder, family, records[family], tasks[family])
        complete = not unresolved and all(k[1:] in attempts[k[0]] for k in target_keys)
        manifest["status"] = "completed" if complete else "paused"
        execution.update(state=manifest["status"], pid=None)
        batch["state"] = manifest["status"]
        if complete:
            batch["finished_at"] = manifest["finished_at"] = runner.base.now()
            for journal in journals.values():
                journal.archive()
        else:
            state["stop"] = state["stop"] or "Retry batch has unsent or unresolved attempts; inspect before resuming"
        checkpoint()
    report = runner.inspect(folder, verify=True)
    execution["last_verification"] = {"at": runner.base.now(), "passed": True,
                                      "tasks": report["settled"], "attempts": report["attempts_settled"]}
    checkpoint()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--concurrency", type=int, default=7)
    parser.add_argument("--budget-usd", type=float)
    args = parser.parse_args()
    if args.expected_count < 1 or not 1 <= args.concurrency <= runner.base.MAX_CONCURRENCY or args.budget_usd is not None and args.budget_usd <= 0:
        parser.error("Expected count and budget must be positive; concurrency must be 1..512")
    report = retry_failed(args.folder, args.batch_id, args.expected_count, args.concurrency, args.budget_usd)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
