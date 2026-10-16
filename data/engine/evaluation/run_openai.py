"""Prepare, run, or verify the pinned GPT-6 Astra/Sol/Luna xHigh benchmarks.

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
from data.engine.evaluation.scaffold_astra import descriptor, schema, FAMILIES
from data.engine.evaluation.scoring import score_output
from data.engine.evaluation.admission import Admission, capacity_error

ENDPOINT = "https://api.openai.com/v1/responses"
BACKOFF_SECONDS = 15
MODELS = {
    "astra-xhigh": {"id": "gpt-6-astra", "name": "GPT-6 Astra xHigh", "budget_usd": 5000,
                    "rates": {"uncached_input": 10, "cached_input": 1, "cache_write_input": 12.5, "output": 50}},
    "sol-xhigh": {"id": "gpt-6-sol", "name": "GPT-6 Sol xHigh", "budget_usd": 1500,
                  "rates": {"uncached_input": 2, "cached_input": .2, "cache_write_input": 2.5, "output": 10}},
    "luna-xhigh": {"id": "gpt-6-luna", "name": "GPT-6 Luna xHigh", "budget_usd": 250,
                   "rates": {"uncached_input": .1, "cached_input": .01, "cache_write_input": .125, "output": .5}},
}
PRIOR_ASTRA = ROOT / "data/benchmark/results/v2/astra-xhigh/manifest.json"


def defaults(model):
    return {"model": MODELS[model]["id"], "reasoning": {"effort": "xhigh"},
            "service_tier": "default", "store": False, "stream": True}


def request_body(prompt, settings):
    return {**deepcopy(settings), "input": prompt}


def pricing_for(model):
    rates = deepcopy(MODELS[model]["rates"])
    return {"verified_date": "2026-10-14", "currency": "USD", "tier": "standard",
            "endpoint": "global direct OpenAI", "rates_usd_per_million_tokens": rates,
            "long_context_threshold_input_tokens": 272000,
            "long_context_rates_usd_per_million_tokens": {k: v * (1.5 if k == "output" else 2) for k, v in rates.items()},
            "formula": "((input_tokens - cached_tokens - cache_write_tokens) * uncached_input_rate + cached_tokens * cached_input_rate + cache_write_tokens * cache_write_input_rate + output_tokens * output_rate) / 1000000",
            "rules": ["Cache counters are subsets of input_tokens.",
                      "Output usage already includes hidden reasoning; never add reasoning tokens twice.",
                      "Unknown final usage retains a full request reserve; never count unknown charges as zero.",
                      "All attempts, including refusals and infrastructure failures, remain in the cost ledger.",
                      "Rates above 272000 input tokens apply to the entire request.",
                      "Estimates exclude taxes, credits and invoice adjustments."],
            "sources": [f"https://developers.openai.com/api/docs/models/{MODELS[model]['id']}",
                        "https://developers.openai.com/api/docs/pricing"]}


def check_budget(manifest, budget):
    maximum = MODELS[manifest["run_id"]]["budget_usd"]
    if not 0 < budget <= maximum:
        raise ValueError(f"Budget must be positive and no greater than the allocated ${maximum}. The three allocations total $6750.")


def prepare(folder, model, prompt_version="v3"):
    config = MODELS[model]
    if prompt_version != "v3":
        raise ValueError("These comparison runs require v3")
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError("Run folder is not empty; never regenerate an existing run")
    source = json.loads(PRIOR_ASTRA.read_bytes())
    if source["status"] != "completed":
        raise RuntimeError("Expected the completed prior Astra run")
    result_schema = schema()
    result_schema["title"] = f"Compact {config['name']} benchmark family results (schema v2, prompts v3)"
    schema_text = json.dumps(result_schema, ensure_ascii=False, indent=2) + "\n"
    manifest = {k: deepcopy(source[k]) for k in (
        "schema_version", "planned_tasks", "planned_primary_requests", "path_conventions",
        "sampling_seed", "sampling_seed_scope", "rendering_dependencies", "tasks", "scoring", "preservation")}
    for entry in manifest["tasks"]:
        template = ROOT / f"data/engine/prompts/v3/vp_{entry['family']}.txt"
        entry["prompt_template"] = {**descriptor(template), "text": template.read_text(encoding="utf-8")}
        entry["journal_file"] = f"journals/{entry['family']}.jsonl"
        entry.pop("journal_archive_member", None)
    manifest["scoring"].pop("selected_attempt", None)
    manifest.update(
        run_id=model, prompt_version="v3", status="scaffolded", created_at=base.now(), started_at=None,
        finished_at=None, submitted_requests=0, provider="openai",
        api={"method": "POST", "url": ENDPOINT}, request_defaults=defaults(model),
        request_input="Exact rendered prompt as request.input; independent requests; no extra instructions, history, tools, web, or model fallbacks.",
        output_limit={"benchmark_cap": None, "max_output_tokens_parameter": "omitted",
                      "documented_model_max_output_tokens": 128000,
                      "meaning": "No benchmark output cap; provider/model limits still apply. Output includes reasoning."},
        omitted_request_parameters=["max_output_tokens", "instructions", "tools", "tool_choice", "previous_response_id", "temperature", "top_p", "seed"],
        comparison_run={**descriptor(PRIOR_ASTRA), "meaning": "Same benchmark tasks and scorer as prior Astra v2; these runs use the v3 templates shared with Anthropic."},
        result_schema={"path": "result.schema.json", "sha256": hashlib.sha256(schema_text.encode()).hexdigest()},
        pricing=pricing_for(model),
        budget_accounting={"overall_openai_target_usd": 8000, "additional_authorized_usd": 5000, "prior_astra_known_cost_usd": 1156.9801,
                           "prior_astra_unknown_cost_reserve_usd": 45.016825,
                           "combined_new_run_ceiling_usd": 6750, "other_prior_pilot_buffer_usd": 48.003075,
                           "allocations_usd": {m: c["budget_usd"] for m, c in MODELS.items()},
                           "scope": "Local usage accounting, not an account balance. Prior pilot invoices unavailable; remaining $48.003075 is held as a buffer. Reserve all in-flight requests at the full provider output maximum."},
        execution={"state": "not_started", "runner_implemented": True, "pid": None,
                   "runner": descriptor(Path(__file__)), "automatic_retries": 0, "model_fallbacks": [],
                   "concurrency": 32, "concurrency_control_file": "run-control.json", "max_concurrency": base.MAX_CONCURRENCY,
                   "budget_usd": config["budget_usd"],
                   "resume": "Replay durable records; submit only tasks without a started marker. Unresolved attempts block resume.",
                   "failure_handling": "Retain transient failures; cool down and reduce concurrency on rate limits. Explicit later batches may retry infrastructure errors, never wrong answers or refusals.",
                   "stopped_reason": None},
        implementation_dependencies=[descriptor(Path(base.__file__)), descriptor(ROOT / "data/engine/evaluation/scaffold_astra.py"),
                                     descriptor(ROOT / "data/engine/evaluation/admission.py")],
        official_references=["https://developers.openai.com/api/reference/resources/responses/methods/create",
                             "https://developers.openai.com/api/docs/guides/reasoning"],
    )
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "journals").mkdir()
    base.atomic_write(folder / "result.schema.json", schema_text)
    base.atomic_write(folder / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    base.atomic_write(folder / "README.md", f"# {config['name']} — v3\n\n20,000 tasks: 5,000 per family, using the pinned v3 templates. xHigh reasoning; no tools, internet, or output token cap.\n\nThe four family JSON files retain the same compact result schema as the other runs. manifest.json pins inputs, templates, rates, settings and progress. Raw journals are preserved during execution and archived after verification.\n")
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


# Preserve the existing streaming implementation and its pinned historical runs.
visible_text = base.visible_text
execute = base.execute
estimate_cost = base.estimate_cost


def result_row(event, task, manifest):
    row = base.result_row(event, task, manifest)
    response = event.get("response") or {}
    error = dict(row["error"] or {})
    unexpected = [b.get("type") for b in response.get("output", [])
                  if b.get("type") not in ("message", "reasoning")]
    if unexpected:
        row["status"] = "api_error"
        error["unexpected_content_types"] = unexpected
    if "model_mismatch" in error:
        row["cost_usd"] = None
        error["unknown_cost_reason"] = "Returned model differs from the model whose rates are pinned"
    row.update(score_output(row["output_text"], task["gold_devanagari"], row["status"]))
    row["error"] = error or None
    return row


def recover_attempts(journals, tasks, manifest, prompts):
    started, attempts = {}, {family: {} for family in tasks}
    authorized = {(target["family"], target["task_id"], target["attempt_number"])
                  for batch in manifest["execution"].get("retry_batches", [])
                  for target in batch["targets"]}
    for family, journal in journals.items():
        for event in journal.read():
            task_id, attempt = event["task_id"], event["attempt_number"]
            if task_id not in tasks[family] or type(attempt) is not int or attempt < 1:
                raise RuntimeError("Unknown task/attempt in OpenAI journal")
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
    if isinstance(provider, dict) and isinstance(provider.get("error"), dict):
        provider = provider["error"]
    # Billing/authentication/quota errors require inspection, not retry loops.
    if isinstance(provider, dict) and provider.get("code") in ("insufficient_quota", "billing_hard_limit_reached"):
        return False
    return (row["status"] == "api_error" and (error.get("http_status") in (429, 500, 502, 503, 504)
            or isinstance(provider, dict) and provider.get("code") in ("server_is_overloaded", "server_error", "rate_limit_exceeded"))
            or row["status"] == "transport_error" and "stream_error" not in error and (
                error.get("type") in ("ReadTimeout", "ReadError", "RemoteProtocolError", "ConnectError", "ConnectTimeout", "WriteError", "WriteTimeout")
                or error.get("message") == "Stream ended without a terminal response; cost unknown"))


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


def run(folder, concurrency=32, budget=1250, max_new=None):
    with (folder / "run.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(folder, concurrency, budget, max_new)


def run_locked(folder, concurrency, budget, max_new):
    manifest, tasks, prompts, validator = load_inputs(folder)
    check_budget(manifest, budget)
    if manifest["execution"].get("retry_batches"):
        raise RuntimeError("Use retry_openai.py to resume an explicit retry batch; primary execution is already finished")
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
    key = os.environ.get("OPENAI_API_KEY") or dotenv_values(ROOT / ".env").get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    reserve = base.reserve_per_request(manifest, prompts)
    execution = manifest["execution"]
    execution.update(state="running", pid=os.getpid(), concurrency=concurrency, budget_usd=budget,
                     reservation_usd_per_inflight_request=reserve, stopped_reason=None,
                     runtime_versions={"python": platform.python_version(), **{p: importlib.metadata.version(p) for p in ("httpx", "python-dotenv", "vidyut", "jsonschema")}})
    manifest.update(status="running", started_at=manifest.get("started_at") or base.now(), finished_at=None)
    state = {"stop": None, "cooldown": 0.0, "consecutive_failures": 0, "rate_limit_ceiling": base.MAX_CONCURRENCY}
    admission = Admission(base.MAX_CONCURRENCY, recovery_step=16, backoff_seconds=BACKOFF_SECONDS)
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
                target = admission.target(base.requested_concurrency(folder, concurrency))
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
                    time.sleep(.05)  # Smooth admission instead of a large startup burst.
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
                        if capacity_error(row, event):
                            state["cooldown"] = admission.pressure(target, event.get("rate_limits", {}).get("retry-after"))
                        if state["consecutive_failures"] >= 5:
                            state["stop"] = "Five consecutive transient failures; inspect before continuing"
                    elif row["cost_usd"] is None or row["status"] in ("api_error", "transport_error", "unknown"):
                        state["stop"] = f"Inspect {family}/{task_id}: {row['status']} or unknown cost"
                    else:
                        state["consecutive_failures"] = 0
                        admission.success()
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
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--budget-usd", type=float)
    parser.add_argument("--max-new", type=int)
    parser.add_argument("--prompt-version", choices=("v3",),
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
