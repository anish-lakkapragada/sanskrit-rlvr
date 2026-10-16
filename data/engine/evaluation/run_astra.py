"""Run or inspect the pinned Astra benchmark. Only the `run` command sends requests.

uv run --python 3.11 --with httpx==0.28.1 --with python-dotenv==1.1.1 \
  --with vidyut==0.4.0 --with jsonschema==4.23.0 python \
  data/engine/evaluation/run_astra.py run
"""

import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import sys
import threading
import time
import uuid

import httpx
from dotenv import dotenv_values
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation.scaffold_astra import FAMILIES, REQUEST_DEFAULTS, RUN
from data.engine.evaluation.scoring import score_output


def now():
    return datetime.now(timezone.utc).isoformat()


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def atomic_write(path, text):
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verify_descriptor(entry, root=ROOT):
    raw = (root / entry["path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise RuntimeError(f"Pinned file changed: {entry['path']}")


def load_inputs(folder=RUN):
    manifest = json.loads((folder / "manifest.json").read_bytes())
    if manifest["request_defaults"] != REQUEST_DEFAULTS:
        raise RuntimeError("Unexpected model/request settings")
    if manifest["api"]["url"] != "https://api.openai.com/v1/responses":
        raise RuntimeError("Unexpected API endpoint")
    verify_descriptor(manifest["result_schema"], folder)
    verify_descriptor(manifest["scoring"]["implementation"])
    verify_descriptor(manifest["scaffold_generator"])
    pinned_runner = manifest["execution"].get("runner")
    if pinned_runner:
        verify_descriptor(pinned_runner)
    tasks, prompts = {}, {}
    for entry in manifest["tasks"]:
        family = entry["family"]
        for name in ("dataset", "sampling_manifest", "prompt_template", "renderer"):
            verify_descriptor(entry[name])
        rows = json.loads((ROOT / entry["dataset"]["path"]).read_bytes())
        if len(rows) != 5000 or len({row["id"] for row in rows}) != 5000:
            raise RuntimeError(f"Invalid benchmark cardinality: {family}")
        renderer = importlib.import_module(f"data.engine.{family}.common").render_task
        tasks[family] = {row["id"]: row for row in rows}
        for row in rows:
            if not row["gold_devanagari"] or row.get("warnings"):
                raise RuntimeError(f"Invalid benchmark gold/warnings: {row['id']}")
            prompt = renderer(row)
            if "<thinking>" in prompt or "{stem_deva}" in prompt:
                raise RuntimeError("Unexpected prompt hydration")
            prompts[family, row["id"]] = prompt
    if set(tasks) != set(FAMILIES):
        raise RuntimeError("Expected all four task families")
    validator = Draft202012Validator(json.loads((folder / "result.schema.json").read_bytes()))
    return manifest, tasks, prompts, validator


def estimate_cost(response, pricing):
    usage = response.get("usage")
    if not usage:
        return None, "Provider usage unavailable"
    if response.get("service_tier") not in ("default", "standard"):
        return None, "Unrecognized or missing returned service tier"
    try:
        inputs, outputs = usage["input_tokens"], usage["output_tokens"]
        details = usage.get("input_tokens_details") or {}
        cached, written = details.get("cached_tokens", 0), details.get("cache_write_tokens", 0)
        if any(type(n) is not int or n < 0 for n in (inputs, outputs, cached, written)):
            raise ValueError("Invalid token counters")
        if cached + written > inputs:
            raise ValueError("Cache counters exceed input tokens")
        rates = pricing["long_context_rates_usd_per_million_tokens"] if inputs > pricing["long_context_threshold_input_tokens"] else pricing["rates_usd_per_million_tokens"]
        cost = ((inputs - cached - written) * rates["uncached_input"]
                + cached * rates["cached_input"] + written * rates["cache_write_input"]
                + outputs * rates["output"]) / 1_000_000
        return round(cost, 10), None
    except (KeyError, TypeError, ValueError) as error:
        return None, str(error)


def visible_text(response):
    return "".join(block.get("text", "") for item in response.get("output", [])
                   if item.get("type") == "message" for block in item.get("content", [])
                   if block.get("type") == "output_text")


def result_row(event, task, manifest):
    response = event.get("response") or {}
    error = dict(event.get("error") or {})
    if event["event"] == "response":
        output = visible_text(response)
        refusals = [block for item in response.get("output", [])
                    for block in item.get("content", []) if block.get("type") == "refusal"]
        details = response.get("incomplete_details") or {}
        if refusals or details.get("reason") == "content_filter":
            status = "refused"
            error.update(refusals=refusals, incomplete_details=details)
        elif response.get("status") == "completed":
            status = "completed"
        elif response.get("status") == "incomplete":
            status = "incomplete"
            error["incomplete_details"] = details
        else:
            status = "api_error"
            error["provider_error"] = response.get("error")
        if response.get("model") != manifest["request_defaults"]["model"]:
            status = "api_error"
            error["model_mismatch"] = response.get("model")
    else:
        status = event.get("status", "unknown")
        output = event.get("partial_output", "")
    cost, cost_error = estimate_cost(response, manifest["pricing"])
    if cost_error:
        error["unknown_cost_reason"] = cost_error
    return {
        "task_id": task["id"], "attempt_number": event["attempt_number"],
        "status": status, "output_text": output,
        **score_output(output, task["gold_devanagari"], status),
        "usage": response.get("usage"), "cost_usd": cost,
        "request_id": event.get("request_id"),
        "response_id": response.get("id") or event.get("response_id"),
        "elapsed_ms": event.get("elapsed_ms"), "error": error or None,
    }


class Journal:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()

    def append(self, entry):
        # A process-wide flock prevents two runners; the thread lock protects lines.
        with self.lock:
            archive = self.path.with_suffix(self.path.suffix + ".gz")
            if archive.exists():
                raw = gzip.decompress(archive.read_bytes())
                if self.path.exists() and self.path.read_bytes() != raw:
                    raise RuntimeError("Journal/archive mismatch; inspect before appending")
                if not self.path.exists():
                    atomic_write(self.path, raw.decode("utf-8"))
                # The expanded copy is durable before removing its old archive.
                archive.unlink()
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(compact(entry) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def read(self):
        archive = self.path.with_suffix(self.path.suffix + ".gz")
        if self.path.exists() and archive.exists():
            if self.path.read_bytes() != gzip.decompress(archive.read_bytes()):
                raise RuntimeError("Journal/archive mismatch; inspect before resuming")
        path = self.path if self.path.exists() else archive
        if not path.exists():
            return
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.endswith("\n"):
                    raise RuntimeError(f"Truncated journal {path}:{line_number}; do not resend")
                yield json.loads(line)

    def archive(self):
        if not self.path.exists():
            return
        raw = self.path.read_bytes()
        archive = self.path.with_suffix(self.path.suffix + ".gz")
        temporary = archive.with_suffix(".gz.tmp")
        with temporary.open("wb") as handle:
            handle.write(gzip.compress(raw, mtime=0))
            handle.flush()
            os.fsync(handle.fileno())
        if gzip.decompress(temporary.read_bytes()) != raw:
            raise RuntimeError("Journal compression verification failed")
        temporary.replace(archive)
        self.path.unlink()


def recover_attempts(journals, tasks, manifest, prompts):
    started, attempts = {}, {family: {} for family in tasks}
    authorized = {(target["family"], target["task_id"], target["attempt_number"])
                  for batch in manifest["execution"].get("retry_batches", [])
                  for target in batch["targets"]}
    for family, journal in journals.items():
        for event in journal.read():
            task_id, attempt = event["task_id"], event["attempt_number"]
            if task_id not in tasks[family] or type(attempt) is not int or attempt < 1:
                raise RuntimeError("Unknown task/attempt in journal")
            key = (family, task_id, attempt)
            if event["event"] == "started":
                if key in started:
                    raise RuntimeError(f"Duplicate started entry: {key}")
                if attempt > 1:
                    prior = attempts[family].get((task_id, attempt - 1))
                    if key not in authorized or prior is None or not transient_request_failure(prior):
                        raise RuntimeError(f"Unauthorized retry or unresolved/non-infrastructure predecessor: {key}")
                expected = {**manifest["request_defaults"], "input": prompts[family, task_id]}
                if event["request"] != expected:
                    raise RuntimeError(f"Journal request differs from pinned prompt: {key}")
                started[key] = {k: v for k, v in event.items() if k != "request"}
            elif event["event"] in ("response", "error"):
                if key not in started or (task_id, attempt) in attempts[family]:
                    raise RuntimeError(f"Unmatched or duplicate terminal entry: {key}")
                attempts[family][task_id, attempt] = result_row(event, tasks[family][task_id], manifest)
            else:
                raise RuntimeError("Unrecognized journal event")
    unresolved = [key for key in started if key[1:] not in attempts[key[0]]]
    return started, attempts, unresolved


def latest_records(attempts):
    records = {family: {} for family in attempts}
    for family, rows in attempts.items():
        for (task_id, attempt), row in rows.items():
            prior = records[family].get(task_id)
            if prior is None or attempt > prior["attempt_number"]:
                records[family][task_id] = row
    return records


def recover(journals, tasks, manifest, prompts):
    started, attempts, unresolved = recover_attempts(journals, tasks, manifest, prompts)
    unique_started = {(family, task_id): event for (family, task_id, _), event in started.items()}
    return unique_started, latest_records(attempts), [(family, task_id) for family, task_id, _ in unresolved]


def sse_events(response):
    data = []
    for line in response.iter_lines():
        if line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
        elif not line and data:
            payload, data = "\n".join(data), []
            if payload == "[DONE]":
                return
            yield json.loads(payload)
    if data and "\n".join(data) != "[DONE]":
        yield json.loads("\n".join(data))


def execute(client, manifest, task_id, body, client_request_id, journal, key, attempt_number=1):
    start = time.monotonic()
    event = {"event": "error", "task_id": task_id, "attempt_number": attempt_number,
             "request_id": None, "response_id": None, "http_status": None,
             "status": "transport_error", "partial_output": ""}
    terminal = None
    partial, refusals = [], []
    try:
        headers = {"Authorization": f"Bearer {key}", "X-Client-Request-Id": client_request_id}
        with client.stream("POST", manifest["api"]["url"], headers=headers, json=body) as response:
            event["http_status"] = response.status_code
            event["request_id"] = response.headers.get("x-request-id")
            event["rate_limits"] = {k: v for k, v in response.headers.items()
                                    if k.startswith("x-ratelimit-") or k == "retry-after"}
            if response.status_code != 200:
                raw = response.read().decode(errors="replace").replace(key, "[REDACTED]")
                try:
                    error = json.loads(raw)
                except ValueError:
                    error = {"body": raw}
                event.update(status="api_error", error={"http_status": response.status_code, "provider_error": error})
            else:
                for part in sse_events(response):
                    kind = part.get("type")
                    if isinstance(part.get("response"), dict):
                        event["response_id"] = part["response"].get("id")
                    if kind == "response.output_text.delta":
                        partial.append(part.get("delta", ""))
                    elif kind == "response.refusal.delta":
                        refusals.append(part.get("delta", ""))
                    elif kind == "error":
                        event["error"] = {"stream_error": part}
                    elif kind in ("response.completed", "response.incomplete", "response.failed"):
                        terminal = part["response"]
                        break
                if terminal is None:
                    event.setdefault("error", {"message": "Stream ended without a terminal response; cost unknown"})
    except Exception as error:
        event["error"] = {"type": type(error).__name__, "message": str(error).replace(key, "[REDACTED]")}
    event.update(timestamp=now(), elapsed_ms=round((time.monotonic() - start) * 1000, 3))
    if terminal is not None:
        event.update(event="response", response=terminal)
        for name in ("status", "partial_output", "error"):
            event.pop(name, None)
    else:
        event["partial_output"] = "".join(partial)
        if refusals:
            event.setdefault("error", {})["partial_refusal"] = "".join(refusals)
    # Never hand a paid response to scoring before its durable journal exists.
    journal.append(event)
    return event


def summarize(records, started_count, planned=20000):
    families = {}
    for family, mapping in records.items():
        rows = list(mapping.values())
        usage = [r["usage"] for r in rows if r["usage"] is not None]
        families[family] = {
            "settled": len(rows), "statuses": dict(Counter(r["status"] for r in rows)),
            "correct": sum(r["correct"] is True for r in rows),
            "format_ok": sum(r["format_ok"] for r in rows),
            "strict_correct": sum(r["correct"] is True and r["format_ok"] for r in rows),
            "known_cost_usd": round(sum(r["cost_usd"] or 0 for r in rows), 8),
            "unknown_cost_attempts": sum(r["cost_usd"] is None for r in rows),
            "input_tokens": sum(u["input_tokens"] for u in usage),
            "output_tokens": sum(u["output_tokens"] for u in usage),
            "mean_output_tokens": round(sum(u["output_tokens"] for u in usage) / len(usage), 2) if usage else None,
        }
    settled = sum(f["settled"] for f in families.values())
    projected = (sum(5000 * f["known_cost_usd"] / f["settled"] for f in families.values())
                 if all(f["settled"] and not f["unknown_cost_attempts"] for f in families.values()) else None)
    return {"updated_at": now(), "planned": planned, "started": started_count, "settled": settled,
            "unsettled": started_count - settled, "not_started": planned - started_count,
            "known_cost_usd": round(sum(f["known_cost_usd"] for f in families.values()), 8),
            "unknown_cost_attempts": sum(f["unknown_cost_attempts"] for f in families.values()),
            "projected_full_run_cost_usd": round(projected, 2) if projected is not None else None,
            "families": families}


def write_results(folder, family, records, tasks):
    rows = [records[task_id] for task_id in tasks if task_id in records]
    atomic_write(folder / f"{family}.json", "[\n" + ",\n".join(map(compact, rows)) + "\n]\n")


def summarize_attempts(attempts, started, planned=20000):
    """Score selected rows once per task, but bill every preserved attempt."""
    selected = summarize(latest_records(attempts), len({key[:2] for key in started}), planned)
    ledger = summarize(attempts, len(started), planned)
    selected.update(attempts_started=len(started), attempts_settled=ledger["settled"],
                    unsettled_attempts=ledger["unsettled"],
                    retry_attempts=sum(key[2] > 1 for key in started))
    for name in ("known_cost_usd", "unknown_cost_attempts"):
        selected[name] = ledger[name]
    selected["projected_full_run_cost_usd"] = None if ledger["unknown_cost_attempts"] else selected["projected_full_run_cost_usd"]
    for family in selected["families"]:
        for name in ("known_cost_usd", "unknown_cost_attempts", "input_tokens", "output_tokens", "mean_output_tokens"):
            selected["families"][family][name] = ledger["families"][family][name]
    return selected


def reserve_per_request(manifest, prompts):
    # A byte-based upper estimate plus ample framing allowance, and the provider's
    # full output ceiling. This reserves dollars, without setting an output cap.
    prompt_bound = max(len(p.encode("utf-8")) for p in prompts.values()) + 1024
    rates = manifest["pricing"]["rates_usd_per_million_tokens"]
    return (prompt_bound * max(rates[k] for k in ("uncached_input", "cached_input", "cache_write_input"))
            + manifest["output_limit"]["documented_model_max_output_tokens"] * rates["output"]) / 1e6


MAX_CONCURRENCY = 512
TRANSIENT_BACKOFF_SECONDS = 60


def terminal_overload(row):
    """A provider-terminal overload can be retained while other tasks continue."""
    error = row.get("error") or {}
    provider_error = error.get("provider_error") or {}
    return (row["status"] == "api_error" and bool(row.get("response_id"))
            and isinstance(provider_error, dict)
            and provider_error.get("code") == "server_is_overloaded"
            and "model_mismatch" not in error)


def transient_request_failure(row):
    """Retain an interrupted attempt; only unrelated, unsent tasks may continue."""
    error = row.get("error") or {}
    interrupted_stream = (
        row["status"] == "transport_error" and bool(row.get("response_id"))
        and "stream_error" not in error
        and (error.get("type") == "RemoteProtocolError"
             or error.get("message") == "Stream ended without a terminal response; cost unknown")
    )
    return terminal_overload(row) or interrupted_stream


def requested_concurrency(folder, fallback):
    """Adjust admission between requests without cancelling active requests."""
    path = folder / "run-control.json"
    if not path.exists():
        return fallback
    control = json.loads(path.read_bytes())
    value = control.get("concurrency")
    if set(control) != {"concurrency"} or type(value) is not int or not 1 <= value <= MAX_CONCURRENCY:
        raise ValueError(f"run-control.json must contain concurrency between 1 and {MAX_CONCURRENCY}")
    return value


def run(folder, concurrency, budget, max_new=None):
    # flock is automatically released on crash, unlike stale PID-only lock files.
    with (folder / "run.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another runner already owns this benchmark")
        return run_locked(folder, concurrency, budget, max_new)


def run_locked(folder, concurrency, budget, max_new):
    manifest, tasks, prompts, validator = load_inputs(folder)
    if manifest["execution"].get("retry_batches"):
        # A primary-run resume must not rewrite or resend explicit retry work.
        return inspect(folder, verify=True)
    concurrency = requested_concurrency(folder, concurrency)
    journals = {f: Journal(folder / "journals" / f"{f}.jsonl") for f in tasks}
    started, records, unresolved = recover(journals, tasks, manifest, prompts)
    if unresolved:
        raise RuntimeError(f"{len(unresolved)} started requests have no terminal record; do not resend")
    for family in tasks:
        validator.validate(list(records[family].values()))
        write_results(folder, family, records[family], tasks[family])
    existing = summarize(records, len(started))
    unknown = [row for family in records.values() for row in family.values() if row["cost_usd"] is None]
    if any(not transient_request_failure(row) for row in unknown):
        raise RuntimeError("Resolve unknown-cost attempts other than recognized overloads or interrupted streams before sending more requests")
    key = os.environ.get("OPENAI_API_KEY") or dotenv_values(ROOT / ".env").get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    pending = [(family, task_id) for ids in zip(*(tasks[f] for f in tasks))
               for family, task_id in zip(tasks, ids) if (family, task_id) not in started]
    if max_new is not None:
        pending = pending[:max_new]
    if not pending:
        print("No new primary requests to submit", flush=True)
        return existing
    (folder / "journals").mkdir(exist_ok=True)
    for journal in journals.values():
        journal.path.touch(exist_ok=True)
    manifest.update(status="running", started_at=manifest.get("started_at") or now(), finished_at=None)
    execution = manifest["execution"]
    execution.update(state="running", runner_implemented=True, concurrency=concurrency, pid=os.getpid(),
                     max_concurrency=MAX_CONCURRENCY, concurrency_control_file="run-control.json",
                     runtime_versions={"python": platform.python_version(), **{p: importlib.metadata.version(p) for p in ("httpx", "python-dotenv", "vidyut", "jsonschema")}},
                     runner={"path": str(Path(__file__).relative_to(ROOT)), "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
                     budget_usd=budget, budget_scope="This run only; account-wide remaining credit is not available from the local ledger.",
                     reservation_usd_per_inflight_request=reserve_per_request(manifest, prompts),
                     transient_failure_handling="Retain failed attempts without retrying. Reserve a full possible request charge for missing usage; pause new submissions for 60 seconds after a terminal overload or recognized stream interruption, then continue unsent tasks. Five new transient failures in one invocation pause the run for inspection.",
                     stopped_reason=None)
    execution.pop("overload_handling", None)
    reserve = execution["reservation_usd_per_inflight_request"]
    state = {"stop": None, "cooldown_until": 0.0, "new_transient_failures": 0}
    def handle_signal(number, frame):
        state["stop"] = f"Received signal {number}; finish in-flight requests and pause"
    old_handlers = {s: signal.signal(s, handle_signal) for s in (signal.SIGINT, signal.SIGTERM)}
    futures, cursor = {}, 0
    last_log = 0.0
    def checkpoint(force_log=False):
        nonlocal last_log
        progress = summarize(records, len(started))
        progress["unknown_cost_reserve_usd"] = round(progress["unknown_cost_attempts"] * reserve, 8)
        execution["progress"] = progress
        if manifest["status"] == "running":
            execution["stopped_reason"] = state["stop"]
            execution["submission_state"] = (
                "draining" if state["stop"] or cursor == len(pending)
                else "cooling_down" if time.monotonic() < state["cooldown_until"]
                else "submitting"
            )
        else:
            execution["submission_state"] = manifest["status"]
        manifest["submitted_requests"] = len(started)
        atomic_write(folder / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        if force_log or time.monotonic() - last_log >= 30:
            print(compact({"at": now(), "state": manifest["status"], "settled": progress["settled"],
                           "in_flight": len(futures), "known_cost_usd": progress["known_cost_usd"],
                           "projected_full_run_cost_usd": progress["projected_full_run_cost_usd"],
                           "stop": state["stop"]}), flush=True)
            last_log = time.monotonic()
        return progress
    checkpoint(True)
    try:
        with httpx.Client(timeout=httpx.Timeout(1800, connect=30), follow_redirects=False,
                          transport=httpx.HTTPTransport(retries=0, limits=httpx.Limits(
                              max_connections=MAX_CONCURRENCY, max_keepalive_connections=MAX_CONCURRENCY))) as client, ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as pool:
            while cursor < len(pending) or futures:
                try:
                    target = requested_concurrency(folder, concurrency)
                    execution["concurrency"] = target
                except (ValueError, OSError) as error:
                    state["stop"] = f"Invalid concurrency control: {error}"
                    target = concurrency
                progress = summarize(records, len(started))
                while state["stop"] is None and time.monotonic() >= state["cooldown_until"] and cursor < len(pending) and len(futures) < target:
                    if progress["known_cost_usd"] + (progress["unknown_cost_attempts"] + len(futures) + 1) * reserve > budget:
                        if not futures:
                            state["stop"] = "Budget guard: insufficient remaining dollars for one uncapped request"
                        break
                    family, task_id = pending[cursor]
                    cursor += 1
                    body = {**manifest["request_defaults"], "input": prompts[family, task_id]}
                    client_id = str(uuid.uuid4())
                    marker = {"event": "started", "task_id": task_id, "attempt_number": 1,
                              "timestamp": now(), "client_request_id": client_id, "request": body}
                    journals[family].append(marker)
                    started[family, task_id] = {k: v for k, v in marker.items() if k != "request"}
                    future = pool.submit(execute, client, manifest, task_id, body, client_id, journals[family], key)
                    futures[future] = (family, task_id)
                if not futures:
                    if state["stop"] is None and cursor < len(pending) and time.monotonic() < state["cooldown_until"]:
                        checkpoint()
                        time.sleep(max(0, min(1, state["cooldown_until"] - time.monotonic())))
                        continue
                    break
                done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    family, task_id = futures.pop(future)
                    event = future.result()
                    row = result_row(event, tasks[family][task_id], manifest)
                    validator.validate([row])
                    records[family][task_id] = row
                    write_results(folder, family, records[family], tasks[family])
                    if transient_request_failure(row):
                        state["new_transient_failures"] += 1
                        state["cooldown_until"] = time.monotonic() + TRANSIENT_BACKOFF_SECONDS
                        if state["new_transient_failures"] >= 5:
                            state["stop"] = "Five transient request failures in this invocation; pause for inspection without retrying"
                    elif row["cost_usd"] is None or row["status"] in ("api_error", "transport_error", "unknown"):
                        state["stop"] = f"Inspect {family}/{task_id}: {row['status']} or unknown cost; no automatic retries"
                    if row["cost_usd"] is not None and row["cost_usd"] > reserve:
                        state["stop"] = "Provider charge exceeded reserved estimate; inspect before continuing"
                checkpoint()
    finally:
        for s, handler in old_handlers.items():
            signal.signal(s, handler)
        # Replay durable terminal records even if scoring/checkpointing raised.
        started, records, unresolved = recover(journals, tasks, manifest, prompts)
        for family in tasks:
            validator.validate(list(records[family].values()))
            write_results(folder, family, records[family], tasks[family])
        complete = all(len(records[f]) == len(tasks[f]) for f in tasks) and not unresolved
        manifest["status"] = "completed" if complete else "paused"
        execution["state"] = manifest["status"]
        execution["stopped_reason"] = state["stop"] or (None if complete else "Invocation ended; unsent tasks remain")
        execution["pid"] = None
        if complete:
            manifest["finished_at"] = now()
            for journal in journals.values():
                journal.archive()
        checkpoint(True)
    return execution["progress"]


def inspect(folder, verify=False):
    manifest, tasks, prompts, validator = load_inputs(folder)
    journals = {f: Journal(folder / "journals" / f"{f}.jsonl") for f in tasks}
    started, attempts, unresolved = recover_attempts(journals, tasks, manifest, prompts)
    records = latest_records(attempts)
    if verify:
        for family in tasks:
            expected = [records[family][task_id] for task_id in tasks[family] if task_id in records[family]]
            actual = json.loads((folder / f"{family}.json").read_bytes())
            validator.validate(actual)
            if actual != expected:
                raise RuntimeError(f"Results differ from journal replay: {family}")
        if unresolved:
            raise RuntimeError(f"Unresolved requests: {len(unresolved)}")
    return {"state": manifest["status"], "unresolved": len(unresolved),
            **summarize_attempts(attempts, started)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "status", "verify"))
    parser.add_argument("--folder", type=Path, default=RUN)
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--budget-usd", type=float, default=3000)
    parser.add_argument("--max-new", type=int)
    args = parser.parse_args()
    if not 1 <= args.concurrency <= MAX_CONCURRENCY or args.budget_usd <= 0 or (args.max_new is not None and args.max_new < 1):
        parser.error(f"Concurrency must be 1..{MAX_CONCURRENCY}; budget and max-new must be positive")
    if args.action == "run":
        result = run(args.folder, args.concurrency, args.budget_usd, args.max_new)
    else:
        result = inspect(args.folder, args.action == "verify")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
