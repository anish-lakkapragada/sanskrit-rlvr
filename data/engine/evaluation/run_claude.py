"""Prepare, run, or verify the pinned Sonnet/Haiku 5.5 xHigh benchmarks.

Only `run` sends model requests. All other actions are offline.
"""

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import fcntl
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import sys
import time
import uuid
from unittest.mock import patch

import httpx
from dotenv import dotenv_values
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_astra as base
from data.engine.evaluation import run_opus as opus
from data.engine.evaluation.scaffold_astra import descriptor, schema, FAMILIES
from data.engine.evaluation.scoring import score_output

ENDPOINT = opus.ENDPOINT
BACKOFF_SECONDS = opus.BACKOFF_SECONDS
MODELS = {
    "sonnet55-xhigh": {"id": "claude-sonnet-5-5", "name": "Sonnet 5.5 xHigh", "budget_usd": 500,
                       "rates": {"uncached_input": 2, "cached_input": .1, "cache_write_input": 4,
                                 "cache_write_5m_input": 2.5, "cache_write_1h_input": 4, "output": 10}},
    "haiku55-xhigh": {"id": "claude-haiku-5-5", "name": "Haiku 5.5 xHigh", "budget_usd": 100,
                      "rates": {"uncached_input": .1, "cached_input": .01, "cache_write_input": .2,
                                "cache_write_5m_input": .125, "cache_write_1h_input": .2, "output": .5}},
}


def defaults(model):
    return {"model": MODELS[model]["id"], "thinking": {"type": "adaptive"},
            "output_config": {"effort": "xhigh"}, "max_tokens": 128000,
            "service_tier": "standard_only", "stream": True}


def request_body(prompt, settings):
    return {**deepcopy(settings), "messages": [{"role": "user", "content": prompt}]}


def pricing_for(model):
    short = "sonnet" if model == "sonnet55-xhigh" else "haiku"
    return {"verified_date": "2026-10-14", "currency": "USD", "tier": "standard",
            "endpoint": "global direct Anthropic", "rates_usd_per_million_tokens": deepcopy(MODELS[model]["rates"]),
            "max_prompt_tokens_for_rates": 100000 if short == "haiku" else 1000000,
            "formula": "Sum uncached input, cache reads, 5m/1h cache writes and output tokens multiplied by their respective rates, divided by 1000000.",
            "rules": ["Cache counters are additional to input_tokens, not subsets.",
                      "Output usage already includes hidden thinking; never add thinking tokens twice.",
                      "No-output empty-content refusals are unbilled except bio, frontier_llm and reasoning_extraction; mid-stream refusals are billed normally.",
                      "Interrupted streams have unknown final usage/cost; retain a full request reserve.",
                      "Haiku rates apply only at or below 100000 prompt tokens. All benchmark prompts are much shorter; unexpected longer usage stops the run for review.",
                      "Estimates exclude taxes, credits and invoice adjustments."],
            "sources": [f"https://platform.claude.com/docs/en/models/{short}-5-5/overview",
                        "https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback"]}


def prepare(folder, model, prompt_version="v3"):
    config = MODELS[model]
    if prompt_version not in ("v2", "v3"):
        raise ValueError("Expected prompt version v2 or v3")
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError("Run folder is not empty; never regenerate an existing run")
    source_path = base.RUN / "manifest.json"
    source = json.loads(source_path.read_bytes())
    if source["status"] != "completed" or not source.get("manifest_history"):
        raise RuntimeError("Consolidate the completed Astra manifests before preparing this benchmark")
    result_schema = schema()
    result_schema["title"] = f"Compact {config['name']} benchmark family results (v2)"
    schema_text = json.dumps(result_schema, ensure_ascii=False, indent=2) + "\n"
    manifest = {k: deepcopy(source[k]) for k in (
        "schema_version", "planned_tasks", "planned_primary_requests", "path_conventions",
        "sampling_seed", "sampling_seed_scope", "rendering_dependencies", "tasks", "scoring", "preservation")}
    for entry in manifest["tasks"]:
        template = ROOT / f"data/engine/prompts/{prompt_version}/vp_{entry['family']}.txt"
        entry["prompt_template"] = {**descriptor(template), "text": template.read_text(encoding="utf-8")}
    manifest["scoring"].pop("selected_attempt", None)
    manifest.update(
        run_id=model, prompt_version=prompt_version, status="scaffolded", created_at=base.now(), started_at=None,
        finished_at=None, submitted_requests=0, provider="anthropic",
        api={"method": "POST", "url": ENDPOINT, "anthropic_version": "2023-06-01"},
        request_defaults=defaults(model),
        request_input="Exact rendered prompt as one user message; no extra instructions, conversation history, tools, or model fallbacks.",
        output_limit={"benchmark_cap": None, "max_tokens_parameter": 128000,
                      "documented_model_max_output_tokens": 128000,
                      "meaning": "Anthropic requires max_tokens. Use the full supported model maximum, including thinking and answer tokens; no smaller benchmark cap."},
        omitted_request_parameters=["system", "tools", "tool_choice", "fallbacks", "temperature", "top_p", "stop_sequences", "speed", "cache_control"],
        comparison_run={**descriptor(source_path), "meaning": "Same four benchmark inputs, renderers and exact membership scorer as the completed Astra run. Prompt templates are pinned separately in tasks; Astra used v2."},
        result_schema={"path": "result.schema.json", "sha256": hashlib.sha256(schema_text.encode()).hexdigest()},
        pricing=pricing_for(model),
        execution={"state": "not_started", "runner_implemented": True, "pid": None,
                   "runner": descriptor(Path(__file__)), "automatic_retries": 0, "model_fallbacks": [],
                   "concurrency": 64, "concurrency_control_file": "run-control.json", "max_concurrency": base.MAX_CONCURRENCY, "budget_usd": config["budget_usd"],
                   "budget_scope": "Separate ceilings of $500 Sonnet and $100 Haiku ($600 combined), within the earlier $1500 Anthropic target after known prior runs. Not an account-balance measurement.",
                   "resume": "Replay durable records. Submit only tasks without a started marker; unresolved attempts block resume.",
                   "failure_handling": "Preserve transient failures without retrying; cool down before sending unrelated tasks. Rate limits reduce admission concurrency. Five consecutive transient failures pause for inspection.",
                   "stopped_reason": None},
        implementation_dependencies=[descriptor(Path(opus.__file__)), descriptor(Path(base.__file__)), descriptor(ROOT / "data/engine/evaluation/scaffold_astra.py")],
        official_references=["https://platform.claude.com/docs/en/api/messages/create",
                             "https://platform.claude.com/docs/en/build-with-claude/streaming",
                             "https://platform.claude.com/docs/en/build-with-claude/effort"],
    )
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "journals").mkdir()
    base.atomic_write(folder / "result.schema.json", schema_text)
    base.atomic_write(folder / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    for family in FAMILIES:
        base.atomic_write(folder / f"{family}.json", "[]\n")
    load_inputs(folder)
    return manifest


def load_inputs(folder):
    manifest = json.loads((folder / "manifest.json").read_bytes())
    if manifest["run_id"] not in MODELS or manifest["request_defaults"] != defaults(manifest["run_id"]) or manifest["api"]["url"] != ENDPOINT:
        raise RuntimeError("Unexpected model/request settings or endpoint")
    if manifest["pricing"] != pricing_for(manifest["run_id"]):
        raise RuntimeError("Unexpected model pricing")
    base.verify_descriptor(manifest["result_schema"], folder)
    base.verify_descriptor(manifest["scoring"]["implementation"])
    base.verify_descriptor(manifest["execution"]["runner"])
    if manifest["execution"].get("retry_runner"):
        base.verify_descriptor(manifest["execution"]["retry_runner"])
    for entry in manifest["implementation_dependencies"]:
        base.verify_descriptor(entry)
    tasks, prompts = {}, {}
    for entry in manifest["tasks"]:
        family = entry["family"]
        for name in ("dataset", "sampling_manifest", "prompt_template", "renderer"):
            base.verify_descriptor(entry[name])
        rows = json.loads((ROOT / entry["dataset"]["path"]).read_bytes())
        if len(rows) != 5000 or len({r["id"] for r in rows}) != 5000:
            raise RuntimeError(f"Invalid benchmark cardinality: {family}")
        module = importlib.import_module(f"data.engine.{family}.common")
        template = (ROOT / entry["prompt_template"]["path"]).read_text(encoding="utf-8")
        if template != entry["prompt_template"]["text"]:
            raise RuntimeError(f"Pinned template text differs from its file: {family}")
        tasks[family] = {r["id"]: r for r in rows}
        # Rendering finishes before request workers start. Restore the module's
        # default template afterward so other runs can still use their version.
        with patch.object(module, "template_text", return_value=template):
            for row in rows:
                if not row["gold_devanagari"] or row.get("warnings"):
                    raise RuntimeError("Invalid benchmark gold/warnings")
                prompt = module.render_task(row)
                if "<thinking>" in prompt or "{stem_deva}" in prompt:
                    raise RuntimeError("Unexpected prompt hydration")
                prompts[family, row["id"]] = prompt
    if set(tasks) != set(FAMILIES):
        raise RuntimeError("Expected all four task families")
    return manifest, tasks, prompts, Draft202012Validator(json.loads((folder / "result.schema.json").read_bytes()))


# Reuse the audited streaming and billing implementation without changing any
# source file pinned by the completed Opus evaluation.
visible_text = opus.visible_text
execute = opus.execute


def estimate_cost(response, pricing):
    usage = response.get("usage") or {}
    try:
        prompt_tokens = sum(usage.get(k, 0) for k in
                            ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        if prompt_tokens > pricing["max_prompt_tokens_for_rates"]:
            return None, "Prompt exceeds the verified pricing tier"
    except (TypeError, KeyError):
        return None, "Invalid prompt token counters or pricing tier"
    return opus.estimate_cost(response, pricing)


def result_row(event, task, manifest):
    response = event.get("response") or event.get("partial_response") or {}
    error = dict(event.get("error") or {})
    output = visible_text(response)
    usage, cost = None, None
    if event["event"] == "response":
        reason = response.get("stop_reason")
        details = response.get("stop_details") or {}
        if reason == "refusal" or details.get("type") == "refusal":
            status = "refused"
            error.update(stop_reason=reason, stop_details=details)
        elif reason == "end_turn":
            status = "completed"
        else:
            status = "incomplete"
            error.update(stop_reason=reason, stop_details=details)
        if response.get("model") != manifest["request_defaults"]["model"]:
            status = "api_error"
            error["model_mismatch"] = response.get("model")
        unexpected = [b.get("type") for b in response.get("content", [])
                      if b.get("type") not in ("text", "thinking", "redacted_thinking")]
        if unexpected:
            status = "api_error"
            error["unexpected_content_types"] = unexpected
        if event.get("usage_final"):
            usage = response.get("usage")
            cost, cost_error = estimate_cost(response, manifest["pricing"])
        else:
            cost_error = "Stream did not report final output usage"
        if "model_mismatch" in error:
            cost, cost_error = None, "Returned model differs from the model whose rates are pinned"
    else:
        status = event.get("status", "unknown")
        cost_error = "Provider final usage unavailable after failed request"
    if cost_error:
        error["unknown_cost_reason"] = cost_error
    return {"task_id": task["id"], "attempt_number": event["attempt_number"], "status": status,
            "output_text": output, **score_output(output, task["gold_devanagari"], status),
            "usage": usage, "cost_usd": cost, "request_id": event.get("request_id"),
            "response_id": response.get("id"), "elapsed_ms": event.get("elapsed_ms"), "error": error or None}


def recover_attempts(journals, tasks, manifest, prompts):
    started, attempts = {}, {family: {} for family in tasks}
    authorized = {(target["family"], target["task_id"], target["attempt_number"])
                  for batch in manifest["execution"].get("retry_batches", [])
                  for target in batch["targets"]}
    for family, journal in journals.items():
        for event in journal.read():
            task_id, attempt = event["task_id"], event["attempt_number"]
            if task_id not in tasks[family] or type(attempt) is not int or attempt < 1:
                raise RuntimeError("Unknown task/attempt in Claude journal")
            key = family, task_id, attempt
            if event["event"] == "started":
                if attempt > 1:
                    prior = attempts[family].get((task_id, attempt - 1))
                    if key not in authorized or prior is None or not transient_failure(prior):
                        raise RuntimeError(f"Unauthorized retry or unresolved/non-infrastructure predecessor: {key}")
                if key in started or event["request"] != request_body(prompts[family, task_id], manifest["request_defaults"]):
                    raise RuntimeError("Duplicate start or request differs from pinned prompt")
                started[key] = {k: v for k, v in event.items() if k != "request"}
            elif event["event"] in ("response", "error"):
                if key not in started or (task_id, attempt) in attempts[family]:
                    raise RuntimeError("Duplicate/unmatched terminal record")
                attempts[family][task_id, attempt] = result_row(event, tasks[family][task_id], manifest)
            else:
                raise RuntimeError("Unknown journal event")
    return started, attempts, [key for key in started if key[1:] not in attempts[key[0]]]


def recover(journals, tasks, manifest, prompts):
    started, attempts, unresolved = recover_attempts(journals, tasks, manifest, prompts)
    unique_started = {(family, task_id): event for (family, task_id, _), event in started.items()}
    return unique_started, base.latest_records(attempts), [(family, task_id) for family, task_id, _ in unresolved]


def transient_failure(row):
    error = row.get("error") or {}
    if "model_mismatch" in error or "unexpected_content_types" in error:
        return False
    provider = error.get("provider_error") or {}
    return (row["status"] == "api_error" and (error.get("http_status") in (429, 500, 502, 503, 504, 529)
            or isinstance(provider, dict) and provider.get("type") in ("overloaded_error", "rate_limit_error", "api_error"))
            or row["status"] == "transport_error" and (
                error.get("type") in ("ReadTimeout", "ReadError", "RemoteProtocolError", "ConnectError", "ConnectTimeout")
                or error.get("message") == "Stream ended without message_stop; final cost unknown"))


def inspect(folder, verify=False):
    manifest, tasks, prompts, validator = load_inputs(folder)
    journals = {f: base.Journal(folder / "journals" / f"{f}.jsonl") for f in tasks}
    started, attempts, unresolved = recover_attempts(journals, tasks, manifest, prompts)
    records = base.latest_records(attempts)
    if verify:
        for family in tasks:
            actual = json.loads((folder / f"{family}.json").read_bytes())
            validator.validate(actual)
            expected = [records[family][task_id] for task_id in tasks[family] if task_id in records[family]]
            if actual != expected:
                raise RuntimeError(f"Result differs from journal replay: {family}")
        if unresolved:
            raise RuntimeError(f"{len(unresolved)} started attempts remain unresolved")
    return {"state": manifest["status"], "unresolved": len(unresolved), **base.summarize_attempts(attempts, started)}


def run(folder, concurrency=64, budget=500, max_new=None):
    with (folder / "run.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(folder, concurrency, budget, max_new)


def run_locked(folder, concurrency, budget, max_new):
    manifest, tasks, prompts, validator = load_inputs(folder)
    if manifest["execution"].get("retry_batches"):
        raise RuntimeError("Use retry_claude.py to resume an explicit retry batch; primary execution is already finished")
    journals = {f: base.Journal(folder / "journals" / f"{f}.jsonl") for f in tasks}
    started, records, unresolved = recover(journals, tasks, manifest, prompts)
    if unresolved:
        raise RuntimeError("Unresolved started requests block resume; never automatically resend")
    for family in tasks:
        validator.validate(list(records[family].values()))
        base.write_results(folder, family, records[family], tasks[family])
    unknown = [r for rows in records.values() for r in rows.values() if r["cost_usd"] is None]
    if any(not transient_failure(row) for row in unknown):
        raise RuntimeError("Inspect unrecognized unknown-cost attempts before resuming")
    pending = [(f, task_id) for ids in zip(*(tasks[f] for f in tasks))
               for f, task_id in zip(tasks, ids) if (f, task_id) not in started]
    if max_new is not None:
        pending = pending[:max_new]
    if not pending:
        return inspect(folder, verify=True)
    key = os.environ.get("ANTHROPIC_API_KEY") or dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is missing")
    reserve = base.reserve_per_request(manifest, prompts)
    execution = manifest["execution"]
    execution.update(state="running", pid=os.getpid(), concurrency=concurrency, budget_usd=budget,
                     reservation_usd_per_inflight_request=reserve, stopped_reason=None,
                     runtime_versions={"python": platform.python_version(), **{p: importlib.metadata.version(p) for p in ("httpx", "python-dotenv", "vidyut", "jsonschema")}})
    manifest.update(status="running", started_at=manifest.get("started_at") or base.now(), finished_at=None)
    state = {"stop": None, "cooldown": 0.0, "consecutive_failures": 0, "rate_limit_ceiling": base.MAX_CONCURRENCY}
    futures, cursor, last_log = {}, 0, 0.0

    def checkpoint(force=False):
        nonlocal last_log
        progress = base.summarize(records, len(started))
        progress["unknown_cost_reserve_usd"] = round(progress["unknown_cost_attempts"] * reserve, 8)
        execution["progress"] = progress
        execution["stopped_reason"] = state["stop"]
        execution["submission_state"] = ("draining" if state["stop"] or cursor == len(pending)
                                          else "cooling_down" if time.monotonic() < state["cooldown"] else "submitting") if manifest["status"] == "running" else manifest["status"]
        manifest["submitted_requests"] = len(started)
        base.atomic_write(folder / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        if force or time.monotonic() - last_log >= 30:
            print(base.compact({"at": base.now(), "state": manifest["status"], "submission_state": execution["submission_state"],
                                "settled": progress["settled"], "in_flight": len(futures), "known_cost_usd": progress["known_cost_usd"],
                                "unknown_cost_attempts": progress["unknown_cost_attempts"], "stop": state["stop"]}), flush=True)
            last_log = time.monotonic()
        return progress

    def handle_signal(number, frame):
        state["stop"] = f"Received signal {number}; finish in-flight requests and pause"

    old_handlers = {s: signal.signal(s, handle_signal) for s in (signal.SIGINT, signal.SIGTERM)}
    checkpoint(True)
    try:
        with httpx.Client(timeout=httpx.Timeout(1800, connect=30), follow_redirects=False,
                          transport=httpx.HTTPTransport(retries=0, limits=httpx.Limits(max_connections=base.MAX_CONCURRENCY, max_keepalive_connections=base.MAX_CONCURRENCY))) as client, ThreadPoolExecutor(max_workers=base.MAX_CONCURRENCY) as pool:
            while cursor < len(pending) or futures:
                target = min(base.requested_concurrency(folder, concurrency), state["rate_limit_ceiling"])
                execution["concurrency"] = target
                progress = base.summarize(records, len(started))
                while state["stop"] is None and time.monotonic() >= state["cooldown"] and cursor < len(pending) and len(futures) < target:
                    if progress["known_cost_usd"] + (progress["unknown_cost_attempts"] + len(futures) + 1) * reserve > budget:
                        if not futures:
                            state["stop"] = "Budget guard: insufficient remaining dollars for one full-output request"
                        break
                    family, task_id = pending[cursor]
                    cursor += 1
                    body = request_body(prompts[family, task_id], manifest["request_defaults"])
                    client_id = str(uuid.uuid4())
                    marker = {"event": "started", "task_id": task_id, "attempt_number": 1,
                              "timestamp": base.now(), "client_request_id": client_id, "request": body}
                    journals[family].append(marker)
                    started[family, task_id] = {k: v for k, v in marker.items() if k != "request"}
                    futures[pool.submit(execute, client, manifest, task_id, body, client_id, journals[family], key)] = family, task_id
                if not futures:
                    if state["stop"] is None and cursor < len(pending) and time.monotonic() < state["cooldown"]:
                        checkpoint()
                        time.sleep(max(0, min(1, state["cooldown"] - time.monotonic())))
                        continue
                    break
                done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    family, task_id = futures.pop(future)
                    event = future.result()
                    row = result_row(event, tasks[family][task_id], manifest)
                    validator.validate([row])
                    records[family][task_id] = row
                    base.write_results(folder, family, records[family], tasks[family])
                    if transient_failure(row):
                        state["consecutive_failures"] += 1
                        try:
                            delay = max(BACKOFF_SECONDS, float(event.get("rate_limits", {}).get("retry-after", 0)))
                        except ValueError:
                            delay = BACKOFF_SECONDS
                        state["cooldown"] = time.monotonic() + delay
                        if event.get("http_status") == 429:
                            state["rate_limit_ceiling"] = max(1, target // 2)
                        if state["consecutive_failures"] >= 5:
                            state["stop"] = "Five consecutive transient failures; inspect before continuing"
                    elif row["cost_usd"] is None or row["status"] in ("api_error", "transport_error", "unknown"):
                        state["stop"] = f"Inspect {family}/{task_id}: {row['status']} or unknown cost"
                    else:
                        state["consecutive_failures"] = 0
                    if row["cost_usd"] is not None and row["cost_usd"] > reserve:
                        state["stop"] = "Provider charge exceeded reserved estimate"
                checkpoint()
    finally:
        for s, handler in old_handlers.items():
            signal.signal(s, handler)
        started, records, unresolved = recover(journals, tasks, manifest, prompts)
        for family in tasks:
            validator.validate(list(records[family].values()))
            base.write_results(folder, family, records[family], tasks[family])
        complete = not unresolved and all(len(records[f]) == len(tasks[f]) for f in tasks)
        manifest["status"] = "completed" if complete else "paused"
        execution.update(state=manifest["status"], pid=None)
        if complete:
            manifest["finished_at"] = base.now()
            for journal in journals.values():
                journal.archive()
        elif state["stop"] is None:
            state["stop"] = "Invocation ended; unsent tasks remain"
        checkpoint(True)
    return execution["progress"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "status", "verify"))
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--model", choices=tuple(MODELS), help="Required for prepare; thereafter pinned in the manifest")
    parser.add_argument("--concurrency", type=int, default=64)
    parser.add_argument("--budget-usd", type=float)
    parser.add_argument("--max-new", type=int)
    parser.add_argument("--prompt-version", choices=("v2", "v3"),
                        help="Template version for prepare; execution uses the pinned manifest")
    args = parser.parse_args()
    if args.prompt_version is not None and args.action != "prepare":
        parser.error("--prompt-version applies only to prepare; existing manifests pin their templates")
    if not 1 <= args.concurrency <= base.MAX_CONCURRENCY or args.budget_usd is not None and args.budget_usd <= 0 or args.max_new is not None and args.max_new < 1:
        parser.error("Invalid concurrency, budget, or max-new")
    if args.action == "prepare":
        if args.model is None:
            parser.error("prepare requires --model")
        manifest = prepare(args.folder, args.model, args.prompt_version or "v3")
        result = {"prepared": manifest["run_id"], "tasks": manifest["planned_tasks"]}
    elif args.action == "run":
        manifest, _, _, _ = load_inputs(args.folder)
        budget = args.budget_usd if args.budget_usd is not None else manifest["execution"]["budget_usd"]
        result = run(args.folder, args.concurrency, budget, args.max_new)
    else:
        result = inspect(args.folder, args.action == "verify")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
