"""Prepare, run, or verify the pinned Gemini 3.8 Flash HIGH benchmark.

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
import subprocess
import threading
import sys
import time
import uuid
from unittest.mock import patch

import httpx
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_astra as base
from data.engine.evaluation.scaffold_astra import descriptor, schema as base_schema, FAMILIES
from data.engine.evaluation.scoring import score_output
from data.engine.evaluation.admission import Admission, capacity_error

PROJECT = "sanskrit-project-511705"
LOCATION = "global"
MODEL = "gemini-3.8-flash"
RUN_ID = "gemini38-flash-high"
ENDPOINT = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent"
GCLOUD = "/Users/anish/google-cloud-sdk/bin/gcloud"
BACKOFF_SECONDS = 15
MODELS = {RUN_ID: {"id": MODEL, "name": "Gemini 3.8 Flash HIGH", "budget_usd": 1000}}
PRIOR_ASTRA = ROOT / "data/benchmark/results/v2/astra-xhigh/manifest.json"


def schema():
    result = base_schema()
    # Vertex confirms non-200 requests are unbilled even without usage counters.
    # Preserve null for unknown transport costs; permit only zero as an exception.
    result["$defs"]["result"]["allOf"][1]["then"]["properties"]["cost_usd"] = {"enum": [None, 0]}
    result["$defs"]["result"]["properties"]["cost_usd"]["description"] = (
        "Gross usage-based estimate; null when unknown. Zero without usage only "
        "for confirmed non-200 responses or requests never sent."
    )
    return result


def defaults(model=RUN_ID):
    if model != RUN_ID:
        raise ValueError("Unexpected model")
    return {"generationConfig": {"thinkingConfig": {"thinkingLevel": "HIGH"}}}


def request_body(prompt, settings):
    return {"contents": [{"role": "user", "parts": [{"text": prompt}]}], **deepcopy(settings)}


def request_headers(priority=False):
    headers = {"Content-Type": "application/json", "X-Goog-User-Project": PROJECT}
    if priority:
        headers.update({"X-Vertex-AI-LLM-Request-Type": "shared",
                        "X-Vertex-AI-LLM-Shared-Request-Type": "priority"})
    return headers


def pricing_for(model=RUN_ID):
    if model != RUN_ID:
        raise ValueError("Unexpected model")
    return {"verified_date": "2026-10-15", "currency": "USD", "tier": "per_response_standard_or_priority",
            "endpoint": "Vertex AI global direct generateContent", "cost_usd_basis": "Gross charges for the actual response trafficType, before promotional credits, taxes or account-specific discounts.",
            "rates_usd_per_million_tokens": {"uncached_input": 1.5, "cached_input": .15, "cache_write_input": 1.5, "output": 7.5},
            "priority_rates_usd_per_million_tokens": {"uncached_input": 2.7, "cached_input": .27, "cache_write_input": 2.7, "output": 13.5},
            "introductory_credit": {"through_date": "2026-12-31", "estimated_credit_fraction": .5,
                                    "effective_rates_usd_per_million_tokens": {"uncached_input": .75, "cached_input": .075, "output": 3.75},
                                    "priority_effective_rates_usd_per_million_tokens": {"uncached_input": 1.35, "cached_input": .135, "output": 6.75},
                                    "meaning": "Google documents 50% credits back on eligible net spend. Record gross charges in cost_usd; estimated discounted totals are separate and are not an invoice or confirmation of project eligibility."},
            "formula": "((promptTokenCount - cachedContentTokenCount) * input_rate + cachedContentTokenCount * cached_input_rate + (candidatesTokenCount + thoughtsTokenCount) * output_rate) / 1000000",
            "rules": ["candidatesTokenCount excludes thoughtsTokenCount: add both once to obtain output_tokens.",
                      "cachedContentTokenCount is a subset of promptTokenCount; implicit cache writes use ordinary input pricing.",
                      "Only HTTP 200 requests incur input/output charges according to Google's pricing page. Confirmed non-200 responses cost zero; transport failures without a status have unknown cost.",
                      "Retain full provider usage metadata alongside normalized cross-provider token counters.",
                      "ON_DEMAND_PRIORITY uses priority rates; ON_DEMAND uses standard rates, including provider downgrades. Historical standard requests retain their original costs.",
                      "Priority headers change scheduling only. No grounding, tools, explicit cache storage or batch pricing.",
                      "An unknown returned model, unsupported modalities, or inconsistent usage counters pauses the run for inspection."],
            "sources": ["https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing",
                        "https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/GenerateContentResponse",
                        "https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/context-cache/context-cache-overview",
                        "https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/priority-paygo"]}


def check_budget(manifest, budget):
    if not 0 < budget <= MODELS[RUN_ID]["budget_usd"]:
        raise ValueError("Budget must be positive and at most the $1000 gross execution ceiling")


def reserve_per_request(manifest, prompts):
    reservation_manifest = deepcopy(manifest)
    if manifest["api"]["headers_without_credentials"].get("X-Vertex-AI-LLM-Shared-Request-Type") == "priority":
        reservation_manifest["pricing"]["rates_usd_per_million_tokens"] = manifest["pricing"]["priority_rates_usd_per_million_tokens"]
    return base.reserve_per_request(reservation_manifest, prompts)


class ADCToken:
    """Private in-memory tokens, refreshed before expiry; never persisted/logged."""
    def __init__(self):
        self._token = None
        self._refresh_at = 0.0
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            if self._token is None or time.monotonic() >= self._refresh_at:
                try:
                    result = subprocess.run([GCLOUD, "auth", "application-default", "print-access-token"],
                                            capture_output=True, text=True, timeout=60)
                except Exception:
                    raise RuntimeError("ADC token refresh could not execute; credential output was not logged") from None
                token = result.stdout.strip()
                if result.returncode or not token or any(c.isspace() for c in token):
                    raise RuntimeError("ADC token refresh failed; credential output was not logged")
                self._token = token
                self._refresh_at = time.monotonic() + 2700
            return self._token

    def invalidate(self):
        with self._lock:
            self._refresh_at = 0.0


def prepare(folder, model=RUN_ID, prompt_version="v3"):
    if model != RUN_ID or prompt_version != "v3":
        raise ValueError("Expected Gemini 3.8 Flash HIGH with v3 prompts")
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError("Run folder is not empty; never overwrite an existing evaluation")
    source = json.loads(PRIOR_ASTRA.read_bytes())
    if source["status"] != "completed":
        raise RuntimeError("Expected completed comparison run")
    result_schema = schema()
    result_schema["title"] = "Compact Gemini 3.8 Flash HIGH results (schema v2, prompts v3)"
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
    manifest["preservation"]["stream_handling"] = "Non-streaming generateContent, exactly as requested. Preserve the complete response before scoring; no stream or continuation loop."
    manifest.update(
        run_id=RUN_ID, model=MODEL, prompt_version="v3", status="scaffolded", created_at=base.now(), started_at=None,
        finished_at=None, submitted_requests=0, provider="google_vertex_ai",
        api={"method": "POST", "url": ENDPOINT, "project": PROJECT, "location": LOCATION,
             "headers_without_credentials": request_headers(priority=True)},
        authentication={"method": "Application Default Credentials", "command": [GCLOUD, "auth", "application-default", "print-access-token"],
                        "refresh_interval_seconds": 2700, "token_storage": "Process memory only; never in files, logs, shell arguments, manifests or journals."},
        request_defaults=defaults(),
        request_input="Exact hydrated v3 prompt as the sole user text part; no system instruction, history, tools, search, grounding or fallback model.",
        output_limit={"benchmark_cap": None, "maxOutputTokens_parameter": "omitted", "thinkingBudget_parameter": "omitted",
                      "documented_model_max_output_tokens": 65536,
                      "provider_limit_scope": "Documented model output maximum including thinking and answer tokens; conservatively reserve this full allowance.",
                      "unified_model_context_tokens": 1048576,
                      "meaning": "No benchmark-specified output limit. Omit maxOutputTokens and thinkingBudget; provider defaults apply. Reserve the documented 65536-token model output maximum for every active or unknown-charge request.",
                      "source": "https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash"},
        omitted_request_parameters=["maxOutputTokens", "thinkingBudget", "includeThoughts", "systemInstruction", "tools", "toolConfig", "safetySettings", "temperature", "topP", "topK", "candidateCount", "continuationToken", "cachedContent", "seed"],
        comparison_run={**descriptor(PRIOR_ASTRA), "meaning": "Same sampled tasks and scorer; v3 templates match the ongoing OpenAI and completed Anthropic v3 runs."},
        result_schema={"path": "result.schema.json", "sha256": hashlib.sha256(schema_text.encode()).hexdigest()},
        pricing=pricing_for(),
        execution={"state": "not_started", "runner_implemented": True, "pid": None,
                   "runner": descriptor(Path(__file__)), "automatic_retries": 0, "model_fallbacks": [],
                   "concurrency": 8, "concurrency_control_file": "run-control.json", "max_concurrency": base.MAX_CONCURRENCY,
                   "budget_usd": 1000, "budget_scope": "Gross Google Cloud charges only; separate from OpenAI and Anthropic budgets. User prioritized speed over cost. Reserve the full documented model output allowance at the requested service tier for each active/unknown request.",
                   "resume": "Replay durable journals; submit only tasks without started markers. Unresolved attempts block resume.",
                   "failure_handling": "Preserve failures; cool down on transient errors and reduce concurrency on rate limits. Later explicit batches may retry infrastructure errors, never wrong answers or refusals.",
                   "stopped_reason": None},
        implementation_dependencies=[descriptor(Path(base.__file__)), descriptor(ROOT / "data/engine/evaluation/scaffold_astra.py"),
                                     descriptor(ROOT / "data/engine/evaluation/admission.py")],
        official_references=["https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash",
                             "https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/GenerateContentResponse"],
    )
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "journals").mkdir()
    base.atomic_write(folder / "result.schema.json", schema_text)
    base.atomic_write(folder / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    base.atomic_write(folder / "README.md", "# Gemini 3.8 Flash HIGH — v3\n\n20,000 tasks: 5,000 per family. Same v3 prompts, sampled tasks and exact-answer scorer as the other evaluations. Project `sanskrit-project-511705`, location `global`, model `gemini-3.8-flash`.\n\nRequests omit maxOutputTokens and thinkingBudget; thinkingLevel is HIGH. No tools, web or extra instructions. The specified non-streaming v1 endpoint has a documented model maximum of 65,536 output tokens, used for cost reservation; the request leaves output limits at provider defaults.\n\nThe four family JSON files use the same compact 13-field schema. usage.output_tokens includes candidate and thinking tokens; provider_usage preserves Google's original usageMetadata. cost_usd is gross before promotional credits; the manifest records the estimated 50% promotional credit separately.\n\nADC access tokens are held only in process memory and refreshed before expiry. Raw journals are archived after verification; the finished directory contains README.md, manifest.json and the four family result files.\n")
    for family in FAMILIES:
        base.atomic_write(folder / f"{family}.json", "[]\n")
    load_inputs(folder)
    return manifest


def load_inputs(folder):
    manifest = json.loads((folder / "manifest.json").read_bytes())
    if manifest["run_id"] != RUN_ID or manifest["model"] != MODEL or manifest["request_defaults"] != defaults() or manifest["api"]["url"] != ENDPOINT:
        raise RuntimeError("Unexpected model/request settings or endpoint")
    if manifest["api"]["project"] != PROJECT or manifest["api"]["location"] != LOCATION:
        raise RuntimeError("Unexpected Google project/location")
    if manifest["api"]["headers_without_credentials"] not in (request_headers(), request_headers(priority=True)):
        raise RuntimeError("Unexpected headers, credentials or service tier")
    if manifest["pricing"] != pricing_for():
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


def visible_text(response):
    candidates = response.get("candidates") or []
    if not candidates:
        return ""
    return "".join(p["text"] for p in (candidates[0].get("content") or {}).get("parts", [])
                   if isinstance(p.get("text"), str) and not p.get("thought", False))


def normalized_usage(response):
    raw = response.get("usageMetadata")
    if not isinstance(raw, dict) or "promptTokenCount" not in raw or "totalTokenCount" not in raw:
        raise ValueError("Provider usage metadata is missing required counters")
    inputs, total = raw["promptTokenCount"], raw["totalTokenCount"]
    answer, thoughts, cached, tool = (raw.get(k, 0) for k in
        ("candidatesTokenCount", "thoughtsTokenCount", "cachedContentTokenCount", "toolUsePromptTokenCount"))
    if any(type(n) is not int or n < 0 for n in (inputs, total, answer, thoughts, cached, tool)):
        raise ValueError("Invalid token counters")
    if cached > inputs or total != inputs + answer + thoughts + tool:
        raise ValueError("Inconsistent provider token counters")
    if tool:
        raise ValueError("Unexpected tool use tokens")
    for field in ("promptTokensDetails", "cacheTokensDetails", "candidatesTokensDetails"):
        if any(item.get("modality") != "TEXT" for item in raw.get(field, [])):
            raise ValueError("Unexpected non-text token usage")
    if raw.get("trafficType") not in (None, "ON_DEMAND", "ON_DEMAND_PRIORITY"):
        raise ValueError("Unexpected traffic type for on-demand pricing")
    return {"input_tokens": inputs, "output_tokens": answer + thoughts, "total_tokens": total,
            "input_tokens_details": {"cached_tokens": cached},
            "output_tokens_details": {"reasoning_tokens": thoughts, "answer_tokens": answer},
            "provider_usage": deepcopy(raw)}


def estimate_cost(response, pricing):
    try:
        usage = normalized_usage(response)
        priority = usage["provider_usage"].get("trafficType") == "ON_DEMAND_PRIORITY"
        rates = pricing["priority_rates_usd_per_million_tokens" if priority else "rates_usd_per_million_tokens"]
        cached = usage["input_tokens_details"]["cached_tokens"]
        return round(((usage["input_tokens"]-cached)*rates["uncached_input"] + cached*rates["cached_input"]
                      + usage["output_tokens"]*rates["output"])/1e6, 10), None
    except (ValueError, TypeError, KeyError) as error:
        return None, str(error)


REFUSAL_REASONS = {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY", "MODEL_ARMOR"}


def result_row(event, task, manifest):
    response = event.get("response") or {}
    output = visible_text(response)
    error = dict(event.get("error") or {})
    usage, cost, cost_error = None, None, None
    if event["event"] == "response":
        candidates = response.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        feedback = response.get("promptFeedback") or {}
        reason = (candidate.get("finishReason") or "").removeprefix("FINISH_REASON_")
        block = feedback.get("blockReason")
        if reason in REFUSAL_REASONS or block not in (None, "", "BLOCK_REASON_UNSPECIFIED"):
            status = "refused"
            error.update(finish_reason=reason, prompt_feedback=feedback, safety_ratings=candidate.get("safetyRatings"))
        elif len(candidates) == 1 and reason == "STOP":
            status = "completed"
        else:
            status = "incomplete"
            error.update(finish_reason=reason, finish_message=candidate.get("finishMessage"), candidate_count=len(candidates))
        returned_model = response.get("modelVersion")
        if returned_model != MODEL and not (status == "refused" and returned_model is None):
            status = "api_error"
            error["model_mismatch"] = returned_model
        parts = (candidate.get("content") or {}).get("parts", [])
        unexpected = sorted({k for part in parts for k in part if k not in ("text", "thought", "thoughtSignature")})
        if unexpected or candidate.get("groundingMetadata") or len(candidates) > 1:
            status = "api_error"
            error.update(unexpected_content_types=unexpected, unexpected_grounding=bool(candidate.get("groundingMetadata")), candidate_count=len(candidates))
        try:
            usage = normalized_usage(response)
        except (ValueError, TypeError, KeyError) as problem:
            cost_error = str(problem)
        else:
            cost, cost_error = estimate_cost(response, manifest["pricing"])
            requested_priority = (event.get("request_headers") or {}).get("X-Vertex-AI-LLM-Shared-Request-Type") == "priority"
            if requested_priority and usage["provider_usage"].get("trafficType") is None:
                cost, cost_error = None, "Priority request response omitted trafficType; cannot determine the billed tier"
        if "model_mismatch" in error:
            cost, cost_error = None, "Returned model differs from the model whose rates are pinned"
    else:
        status = event.get("status", "unknown")
        if event.get("http_status") is not None and event["http_status"] != 200 or event.get("request_sent") is False:
            cost = 0.0
        else:
            cost_error = "Final provider usage unavailable after transport failure"
    if cost_error:
        error["unknown_cost_reason"] = cost_error
    return {"task_id": task["id"], "attempt_number": event["attempt_number"], "status": status,
            "output_text": output, **score_output(output, task["gold_devanagari"], status),
            "usage": usage, "cost_usd": cost, "request_id": event.get("request_id"),
            "response_id": response.get("responseId"), "elapsed_ms": event.get("elapsed_ms"), "error": error or None}


def execute(client, manifest, task_id, body, client_request_id, journal, key, attempt_number=1):
    started = time.monotonic()
    event = {"event": "error", "task_id": task_id, "attempt_number": attempt_number,
             "request_headers": deepcopy(manifest["api"]["headers_without_credentials"]),
             "request_id": None, "http_status": None, "status": "api_error", "request_sent": False}
    token = None
    try:
        token = key.get()
        headers = {"Authorization": "Bearer " + token, **manifest["api"]["headers_without_credentials"]}
        event.update(request_sent=True, status="transport_error")
        response = client.post(manifest["api"]["url"], headers=headers, json=body)
        event["http_status"] = response.status_code
        event["request_id"] = response.headers.get("x-request-id") or response.headers.get("x-goog-request-id")
        event["rate_limits"] = {k: v for k, v in response.headers.items() if k.startswith("x-ratelimit-") or k == "retry-after"}
        raw = response.text.replace(token, "[REDACTED]")
        try:
            payload = json.loads(raw)
        except ValueError:
            event.update(status="api_error", error={"message": "Provider returned invalid JSON", "body": raw})
        else:
            if response.status_code == 200 and isinstance(payload, dict) and "error" not in payload:
                event.update(event="response", response=payload)
                event.pop("status", None)
            else:
                event.update(status="api_error", error={"http_status": response.status_code, "provider_error": payload})
                if response.status_code == 401:
                    key.invalidate()
    except Exception as error:
        message = str(error)
        if token:
            message = message.replace(token, "[REDACTED]")
        event["error"] = {"type": type(error).__name__, "message": message}
    event.update(timestamp=base.now(), elapsed_ms=round((time.monotonic()-started)*1000, 3))
    journal.append(event)
    return event


def recover_attempts(journals, tasks, manifest, prompts):
    started, attempts = {}, {family: {} for family in tasks}
    authorized = {(target["family"], target["task_id"], target["attempt_number"])
                  for batch in manifest["execution"].get("retry_batches", [])
                  for target in batch["targets"]}
    for family, journal in journals.items():
        for event in journal.read():
            task_id, attempt = event["task_id"], event["attempt_number"]
            if task_id not in tasks[family] or type(attempt) is not int or attempt < 1:
                raise RuntimeError("Unknown task/attempt in Gemini journal")
            key = family, task_id, attempt
            if event["event"] == "started":
                if attempt > 1:
                    prior = attempts[family].get((task_id, attempt - 1))
                    if key not in authorized or prior is None or not transient_failure(prior):
                        raise RuntimeError(f"Unauthorized retry or unresolved/non-infrastructure predecessor: {key}")
                if key in started or event["request"] != request_body(prompts[family, task_id], manifest["request_defaults"]):
                    raise RuntimeError("Duplicate start or request differs from pinned prompt")
                if event.get("request_headers") not in (None, request_headers(), request_headers(priority=True)):
                    raise RuntimeError("Unexpected headers in started journal record")
                started[key] = {k: v for k, v in event.items() if k != "request"}
            elif event["event"] in ("response", "error"):
                if key not in started or (task_id, attempt) in attempts[family]:
                    raise RuntimeError("Duplicate/unmatched terminal record")
                if started[key].get("request_headers") is not None and event.get("request_headers") != started[key]["request_headers"]:
                    raise RuntimeError("Terminal request headers differ from the started journal record")
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
    return (row["status"] == "api_error" and error.get("http_status") in (429, 500, 502, 503, 504)
            or row["status"] == "transport_error" and error.get("type") in
            ("ReadTimeout", "ReadError", "RemoteProtocolError", "ConnectError", "ConnectTimeout", "WriteError", "WriteTimeout"))


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


def run(folder, concurrency=8, budget=1000, max_new=None):
    with (folder / "run.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(folder, concurrency, budget, max_new)


def run_locked(folder, concurrency, budget, max_new):
    manifest, tasks, prompts, validator = load_inputs(folder)
    check_budget(manifest, budget)
    if manifest["execution"].get("retry_batches"):
        raise RuntimeError("Use retry_gemini_flash.py to resume an explicit retry batch; primary execution is already finished")
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
    key = ADCToken()
    key.get()  # Obtain fresh ADC credentials privately before recording any requests.
    reserve = reserve_per_request(manifest, prompts)
    execution = manifest["execution"]
    execution.update(state="running", pid=os.getpid(), concurrency=concurrency, budget_usd=budget,
                     reservation_usd_per_inflight_request=reserve, stopped_reason=None,
                     runtime_versions={"python": platform.python_version(), **{p: importlib.metadata.version(p) for p in ("httpx", "vidyut", "jsonschema")}})
    manifest.update(status="running", started_at=manifest.get("started_at") or base.now(), finished_at=None)
    state = {"stop": None, "cooldown": 0.0, "consecutive_failures": 0, "rate_limit_ceiling": base.MAX_CONCURRENCY}
    admission = Admission(base.MAX_CONCURRENCY, recovery_step=4, backoff_seconds=BACKOFF_SECONDS)
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
                          transport=httpx.HTTPTransport(retries=0, limits=httpx.Limits(max_connections=base.MAX_CONCURRENCY, max_keepalive_connections=base.MAX_CONCURRENCY, keepalive_expiry=60))) as client, ThreadPoolExecutor(max_workers=base.MAX_CONCURRENCY) as pool:
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
                              "timestamp": base.now(), "client_request_id": client_id, "request": body,
                              "request_headers": deepcopy(manifest["api"]["headers_without_credentials"])}
                    journals[family].append(marker)
                    started[family, task_id] = {k: v for k, v in marker.items() if k != "request"}
                    futures[pool.submit(execute, client, manifest, task_id, body, client_id, journals[family], key)] = family, task_id
                    priority = manifest["api"]["headers_without_credentials"].get("X-Vertex-AI-LLM-Shared-Request-Type") == "priority"
                    time.sleep(.1 if priority else .2)  # Smooth admission, even on Priority PayGo.
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
    parser.add_argument("--concurrency", type=int, default=8)
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
