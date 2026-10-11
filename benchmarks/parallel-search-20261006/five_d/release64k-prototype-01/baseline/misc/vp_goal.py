#!/usr/bin/env python3
"""Adaptive, cumulatively budget-locked benchmark goal. Only `submit` generates answers.

New artifacts live outside the historical runs. A durable reservation precedes
every paid POST; unknown submissions are never replayed automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import ant_batch_eval as ant, oai_batch_eval as base
from misc.vp_compositional import render as render_compositional
from misc.vp_compositional_prompt_v2 import render as render_plain
from misc.vp_compositional_prompt_v3 import render as render_fields
from misc.vp_compositional_prompt_v4 import render as render_pada
from misc.vp_paradigm_prompt_v1 import render as render_paradigm
from misc.vp_contrast_prompt_v1 import render as render_contrast
from misc.vp_krdanta_prompt_v1 import render as render_krdanta
from misc.vp_paradigm_prompt_v2 import render as render_paradigm_v2
from misc.vp_contrast_prompt_v2 import render as render_contrast_v2
from misc.vp_paradigm_prompt_v3 import render as render_paradigm_v3
from misc.vp_contrast_prompt_v3 import render as render_contrast_v3
from misc.vp_paradigm_prompt_v4 import render as render_paradigm_v4
from misc.vp_contrast_prompt_v4 import render as render_contrast_v4
from misc.vp_multiform_prompt_v5 import render as render_multiform_v5
from misc.vp_samasa_prompt_v1 import render as render_samasa
from misc.vp_samasa_prompt_v2 import render as render_samasa_v2
from misc.vp_samasa_prompt_v3 import render as render_samasa_v3
from misc.vp_bundle_prompt_v1 import render as render_bundle
from misc.vp_unadi_prompt_v1 import render as render_unadi
from misc.vp_sanskrit_prompt_v1 import render as render_sanskrit
from misc.vp_cartesian_prompt_v1 import render as render_cartesian
from misc.vp_cartesian_prompt_v2 import render as render_cartesian_v2
from misc.vp_cartesian_prompt_v3 import render as render_cartesian_v3
from misc.vp_goal_grammar import validate_prefixes

OUT = ROOT / "benchmarks/iterative-goal-20261006"
HISTORY = ROOT / "benchmarks/creation-campaign-20261006"
TEMPLATE = "v2/vp_task_eval.txt"
PROVIDERS = {"Anthropic": {"model": "claude-opus-5-5", "cap_micro": 1_000_000_000,
                           "input_rate": 2, "output_rate": 10},
             "OpenAI": {"model": "gpt-6-astra", "cap_micro": 2_000_000_000,
                        "input_rate": 5, "output_rate": 25}}
# Hard-coded authorization prevents an edited report from raising execution caps.
PHASES = {
    "explore": ("xhigh", 16384, {"Anthropic": 20000, "OpenAI": 20000}),
    "confirm": ("xhigh", 16384, {"Anthropic": 20000, "OpenAI": 20000}),
    "confirm_64k": ("xhigh", 65536, {"Anthropic": 20000, "OpenAI": 20000}),
    "bench_final": ("xhigh", 16384, {"Anthropic": 1000, "OpenAI": 1000}),
    "hard_final": ("xhigh", 16384, {"Anthropic": 1000, "OpenAI": 1000}),
    "cap_check": ("xhigh", 128000, {"Anthropic": 100, "OpenAI": 100}),
    "cap_check_development": ("xhigh", 128000, {"Anthropic": 100, "OpenAI": 100}),
    "bench_extension": ("xhigh", 16384, {"Anthropic": 5000, "OpenAI": 5000}),
    "hard_extension": ("xhigh", 16384, {"Anthropic": 5000, "OpenAI": 5000}),
}
PROTECTED = {"bench_final", "hard_final", "cap_check"}
SENSITIVITY_PHASES = {"cap_check", "cap_check_development"}
CONFIRMATION_PHASES = {"confirm", "confirm_64k"}
EXTENSIONS = {"bench_extension": "bench_final", "hard_extension": "hard_final"}
FINAL_PHASES = PROTECTED | set(EXTENSIONS)
INPUT_ALLOWANCE = 1500
MAX_COUNTED_INPUT = 1300



def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def client_for(provider):
    return ant.api_client() if provider == "Anthropic" else base.api_client()


def load():
    state = base.read_json(OUT / "ledger.json")
    if state["authorization"] != PROVIDERS or state["phase_policy"] != json.loads(json.dumps(PHASES)):
        raise ValueError("Authorization or evaluation protocol changed")
    protected_allocations(state)
    for key, path in (("historical_ledger_sha256", HISTORY / "ledger.json"),
                      ("family_split_sha256", HISTORY / "family-split.json"),
                      ("prompt_sha256", ROOT / "prompts" / TEMPLATE),
                      ("renderer_sha256", ROOT / "misc/vp_compositional.py")):
        if state[key] != base.sha256(path):
            raise ValueError(f"Frozen dependency changed: {key}")
    for name, sha in state.get("additional_renderers", {}).items():
        if base.sha256(ROOT / "misc" / name) != sha:
            raise ValueError("Registered prompt renderer changed")
    return state


def save(state):
    state["updated_at"] = base.now()
    base.atomic_json(OUT / "ledger.json", state)


def initialize():
    with base.lock(OUT):
        if (OUT / "ledger.json").exists():
            return load()
        history = base.read_json(HISTORY / "ledger.json")
        if any(j["attempted_at"] and not j.get("collected_at") for j in history["jobs"].values()):
            raise ValueError("Reconcile earlier outstanding jobs first")
        carried = {p: sum(j.get("actual_cost_upper_micro", 0) for j in history["jobs"].values()
                         if j["provider"] == p) for p in PROVIDERS}
        assert carried == {"Anthropic": 23072126, "OpenAI": 0}
        state = {"schema_version": 2, "created_at": base.now(), "authorization": PROVIDERS,
                 "phase_policy": PHASES, "historical_spend_micro": carried,
                 "historical_ledger_sha256": base.sha256(HISTORY / "ledger.json"),
                 "family_split_sha256": base.sha256(HISTORY / "family-split.json"),
                 "prompt_sha256": base.sha256(ROOT / "prompts" / TEMPLATE),
                 "renderer_sha256": base.sha256(ROOT / "misc/vp_compositional.py"),
                 "sdk_max_retries": 0, "billed_input_allowance": INPUT_ALLOWANCE,
                 "maximum_counted_input": MAX_COUNTED_INPUT,
                 "accounting": "Historical settled usage + new settled upper costs + full outstanding/unknown reservations. Verified savings fund further iterations; protect final evaluation and sensitivity allowances.",
                 "jobs": {}, "status": "exploring_compositional_creation"}
        save(state)
        return state


def request(task, provider, phase, index):
    model = PROVIDERS[provider]["model"]
    effort, cap, _ = PHASES[phase]
    version = task.get("prompt_version", "composition-v1")
    renderers = {"composition-v1": render_compositional, "composition-v2-plain": render_plain,
                 "composition-v3-fields": render_fields, "composition-v4-pada": render_pada,
                 "paradigm-v1": render_paradigm, "contrast-v1": render_contrast,
                 "krdanta-v1": render_krdanta,
                 "paradigm-v2-sanskrit": render_paradigm_v2, "contrast-v2-sanskrit": render_contrast_v2,
                 "paradigm-v3-dhatu": render_paradigm_v3, "contrast-v3-dhatu": render_contrast_v3,
                 "paradigm-v4-lines": render_paradigm_v4, "contrast-v4-lines": render_contrast_v4,
                 "paradigm-v5-fields": render_multiform_v5, "contrast-v5-fields": render_multiform_v5,
                 "samasa-v1": render_samasa, "samasa-v2-fields": render_samasa_v2,
                 "samasa-v3-fields": render_samasa_v3, "bundle-v1": render_bundle,
                 "unadi-v1": render_unadi, "unadi-v2-sanskrit": render_sanskrit,
                 "bundle-v2-sanskrit": render_sanskrit,
                 "cartesian-4d-v1": render_cartesian, "cartesian-5d-v1": render_cartesian,
                 "cartesian-4d-v2-verb": render_cartesian_v2, "cartesian-5d-v2-verb": render_cartesian_v2,
                 "cartesian-4d-v3-sanskrit": render_cartesian_v3, "cartesian-5d-v3-sanskrit": render_cartesian_v3}
    if version not in renderers:
        raise ValueError("Unknown prompt version")
    prompt = renderers[version](task)
    if provider == "Anthropic":
        return {"custom_id": f"task-{index:05d}", "params": {
            "model": model, "max_tokens": cap,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": effort}, "tools": [],
            "tool_choice": {"type": "none"}, "stream": False}}
    return {"custom_id": f"task-{index:05d}", "method": "POST", "url": "/v1/responses", "body": {
        "model": model, "input": [{"role": "user", "content": prompt}],
        "reasoning": {"mode": "standard", "effort": effort},
        "max_output_tokens": cap, "tools": [], "tool_choice": "none",
        "store": False, "stream": False, "truncation": "disabled"}}


def validate_requests(tasks, requests, provider, phase):
    if not tasks or len(tasks) != len(requests) or len({t["id"] for t in tasks}) != len(tasks):
        raise ValueError("Tasks must be nonempty, aligned and unique")
    expected = [request(t, provider, phase, i) for i, t in enumerate(tasks)]
    if requests != expected:
        raise ValueError("Request differs from fixed provider, prompt, effort or token policy")
    if len(tasks) > PHASES[phase][2][provider]:
        raise ValueError("Phase request limit exceeded")


def prepare(job_id, tasks_path, provider, phase, transport="batch"):
    if transport not in {"batch", "direct"} or (transport == "direct" and phase != "explore"):
        raise ValueError("Direct requests are allowed only for exploratory diagnostics")
    if not job_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in job_id):
        raise ValueError("Invalid job ID")
    tasks = base.read_json(tasks_path)
    requests = [request(t, provider, phase, i) for i, t in enumerate(tasks)]
    validate_requests(tasks, requests, provider, phase)
    with base.lock(OUT):
        state = load()
        if job_id in state["jobs"]:
            old = state["jobs"][job_id]
            if old["tasks_digest"] != digest(tasks) or old["provider"] != provider or old["phase"] != phase or old.get("transport", "batch") != transport:
                raise ValueError("Job ID already describes different work")
            return old
        jobdir = OUT / "jobs" / job_id
        base.atomic_json(jobdir / "tasks.json", tasks)
        base.atomic_json(jobdir / "requests.json", requests)
        job = {"id": job_id, "provider": provider, "phase": phase, "n": len(tasks),
               "tasks_digest": digest(tasks), "requests_digest": digest(requests),
               "created_at": base.now(), "status": "prepared", "batch_id": None,
               "attempted_at": None, "reservation_micro": 0, "input_file_id": None, "transport": transport}
        state["jobs"][job_id] = job
        save(state)
    print(f"Prepared {job_id}: {len(tasks)} {provider} tasks; no paid calls", flush=True)
    return job


def verify_job(job):
    jobdir = OUT / "jobs" / job["id"]
    tasks = base.read_json(jobdir / "tasks.json")
    requests = base.read_json(jobdir / "requests.json")
    if digest(tasks) != job["tasks_digest"] or digest(requests) != job["requests_digest"]:
        raise ValueError("Prepared artifacts changed")
    validate_requests(tasks, requests, job["provider"], job["phase"])
    return tasks, requests


def count_inputs(job_id):
    state = load()
    job = state["jobs"][job_id]
    _, requests = verify_job(job)
    provider = job["provider"]
    client = client_for(provider)
    path = OUT / "jobs" / job_id / "input-counts.json"
    saved = base.read_json(path) if path.exists() else {}
    if saved and saved["requests_digest"] != job["requests_digest"]:
        raise ValueError("Token counts belong to different requests")
    counts = saved.get("counts", {})

    def count(r):
        body = r["params" if provider == "Anthropic" else "body"]
        if provider == "Anthropic":
            res = client.messages.count_tokens(model=body["model"], messages=body["messages"],
                      thinking=body["thinking"], tools=[], tool_choice={"type": "none"})
        else:
            # Generic POST works with the installed SDK and returns the raw count.
            import httpx
            res = client.post("/responses/input_tokens", cast_to=httpx.Response,
                              body={k: body[k] for k in ("model", "input", "tools", "tool_choice", "reasoning")}).json()
            return r["custom_id"], res["input_tokens"]
        return r["custom_id"], res.input_tokens

    try:
        with ThreadPoolExecutor(max_workers=12) as pool:
            pending = [pool.submit(count, r) for r in requests if r["custom_id"] not in counts]
            for future in as_completed(pending):
                cid, n = future.result()
                counts[cid] = n
                if len(counts) % 200 == 0:
                    print(f"Counted {job_id}: {len(counts)}/{len(requests)} inputs", flush=True)
    except Exception as exc:
        base.atomic_json(path, {"requests_digest": job["requests_digest"], "counts": counts})
        base.atomic_json(path.with_suffix(".error.json"), base.error_details(exc, client))
        raise RuntimeError("Input counting failed; partial counts saved; no generations submitted") from None
    base.atomic_json(path, {"requests_digest": job["requests_digest"], "counts": counts,
                           "counted_at": base.now(), "maximum": max(counts.values()),
                           "note": "Provider estimates; require <=1300 and reserve 1500 billed input tokens per task."})
    if len(counts) != len(requests) or max(counts.values()) > state["maximum_counted_input"]:
        raise ValueError("Input token gate failed")
    print(f"Input gate passed {job_id}: max {max(counts.values())}, allowance 1500", flush=True)


def committed(state, provider):
    return state["historical_spend_micro"][provider] + sum(
        j["actual_cost_upper_micro"] if j.get("settled") else j["reservation_micro"]
        for j in state["jobs"].values() if j["provider"] == provider)


def rates(job):
    p = PROVIDERS[job["provider"]]
    multiplier = 2 if job.get("transport") == "direct" else 1
    return {"input_rate": p["input_rate"] * multiplier, "output_rate": p["output_rate"] * multiplier}


def protected_allocations(state):
    """Internal planning reserves may be reassigned; hard provider caps never are.

    A coordinator revision must be recorded before changing a reserve. Missing
    configuration retains the original two-core-plus-sensitivity protection.
    """
    default = {p: {phase: PHASES[phase][2][p] for phase in PROTECTED} for p in PROVIDERS}
    allocation = state.get('protected_phase_minimum_questions')
    if allocation is None:
        return default
    if set(allocation) != set(PROVIDERS):
        raise ValueError('Reserve revision must name every provider')
    for provider, phases in allocation.items():
        if set(phases) != PROTECTED:
            raise ValueError('Reserve revision must name every protected phase')
        for phase, n in phases.items():
            if type(n) is not int or not 0 <= n <= default[provider][phase]:
                raise ValueError('Invalid protected question allocation')
    revisions = state.get('reserve_revisions', [])
    if not revisions or revisions[-1].get('new_allocation') != allocation or not revisions[-1].get('reason'):
        raise ValueError('Reserve revision needs a matching documented rationale')
    return allocation


def protected_remaining(state, provider, adding=None):
    p = PROVIDERS[provider]
    allocation = protected_allocations(state)[provider]
    remaining = 0
    for phase in PROTECTED:
        phases = SENSITIVITY_PHASES if phase == 'cap_check' else {phase}
        n = sum(j["n"] for j in state["jobs"].values()
                if j["provider"] == provider and j["phase"] in phases and j["attempted_at"])
        if adding and adding["phase"] in phases:
            n += adding["n"]
        remaining += max(0, allocation[phase] - n) * (
            INPUT_ALLOWANCE * p["input_rate"] + PHASES[phase][1] * p["output_rate"])
    return remaining


def budget_gate(state, job):
    if state.get("status", "").startswith("halted"):
        raise ValueError("Goal runner halted for reconciliation")
    if job["attempted_at"]:
        raise ValueError("Submission already attempted; never replay")
    provider, phase = job["provider"], job["phase"]
    if phase in EXTENSIONS:
        core_n = sum(j["n"] for j in state["jobs"].values()
                     if j["provider"] == provider and j["phase"] == EXTENSIONS[phase]
                     and j.get("settled") and j.get("collected_at"))
        if core_n < PHASES[EXTENSIONS[phase]][2][provider]:
            raise ValueError("Collect and settle the core tier before extending its sample size")
    phases = (SENSITIVITY_PHASES if phase in SENSITIVITY_PHASES else
              CONFIRMATION_PHASES if phase in CONFIRMATION_PHASES else {phase})
    used_n = sum(j["n"] for j in state["jobs"].values()
                 if j["provider"] == provider and j["phase"] in phases and j["attempted_at"])
    if used_n + job["n"] > PHASES[phase][2][provider]:
        raise ValueError("Phase allowance exceeded")
    p = rates(job)
    reserve = job["n"] * (INPUT_ALLOWANCE*p["input_rate"] + PHASES[phase][1]*p["output_rate"])
    if committed(state, provider) + reserve + protected_remaining(state, provider, job) > PROVIDERS[provider]["cap_micro"]:
        raise ValueError("Cumulative provider cap or protected final reserve exceeded")
    return reserve


def prevent_repeated_final_questions(state, job, tasks):
    """Final stages are a partition, even if an earlier POST has unknown status.

    Paired providers and declared cap-sensitivity requests are separate runs.
    This check runs under the same lock as the maximum-cost reservation.
    """
    primary_phases = FINAL_PHASES - {'cap_check'}
    if job['phase'] not in primary_phases:
        return
    ids = {t['id'] for t in tasks}
    for previous in state['jobs'].values():
        if (previous['provider'] == job['provider'] and previous['phase'] in primary_phases
                and previous['attempted_at']):
            old = base.read_json(OUT / 'jobs' / previous['id'] / 'tasks.json')
            if ids.intersection(t['id'] for t in old):
                raise ValueError('Final questions already attempted for this provider; never duplicate a stage')


def submit(job_id):
    with base.lock(OUT):
        state = load()
        job = state["jobs"][job_id]
        tasks, requests = verify_job(job)
        for task in tasks:
            validate_prefixes(task.get("derivation", {}).get("prefixes", []))
        for version, filename in (("composition-v2-plain", "vp_compositional_prompt_v2.py"),
                                  ("composition-v3-fields", "vp_compositional_prompt_v3.py"),
                                  ("composition-v4-pada", "vp_compositional_prompt_v4.py"),
                                  ("paradigm-v1", "vp_paradigm_prompt_v1.py"),
                                  ("contrast-v1", "vp_contrast_prompt_v1.py"),
                                  ("krdanta-v1", "vp_krdanta_prompt_v1.py"),
                                  ("paradigm-v2-sanskrit", "vp_paradigm_prompt_v2.py"),
                                  ("contrast-v2-sanskrit", "vp_contrast_prompt_v2.py"),
                                  ("paradigm-v3-dhatu", "vp_paradigm_prompt_v3.py"),
                                  ("contrast-v3-dhatu", "vp_contrast_prompt_v3.py"),
                                  ("paradigm-v4-lines", "vp_paradigm_prompt_v4.py"),
                                  ("contrast-v4-lines", "vp_contrast_prompt_v4.py"),
                                  ("paradigm-v5-fields", "vp_multiform_prompt_v5.py"),
                                  ("contrast-v5-fields", "vp_multiform_prompt_v5.py"),
                                  ("samasa-v1", "vp_samasa_prompt_v1.py"),
                                  ("samasa-v2-fields", "vp_samasa_prompt_v2.py"),
                                  ("samasa-v3-fields", "vp_samasa_prompt_v3.py"),
                                  ("bundle-v1", "vp_bundle_prompt_v1.py"),
                                  ("unadi-v1", "vp_unadi_prompt_v1.py"),
                                  ("unadi-v2-sanskrit", "vp_sanskrit_prompt_v1.py"),
                                  ("bundle-v2-sanskrit", "vp_sanskrit_prompt_v1.py"),
                                  ("cartesian-4d-v1", "vp_cartesian_prompt_v1.py"),
                                  ("cartesian-5d-v1", "vp_cartesian_prompt_v1.py"),
                                  ("cartesian-4d-v2-verb", "vp_cartesian_prompt_v2.py"),
                                  ("cartesian-5d-v2-verb", "vp_cartesian_prompt_v2.py"),
                                  ("cartesian-4d-v3-sanskrit", "vp_cartesian_prompt_v3.py"),
                                  ("cartesian-5d-v3-sanskrit", "vp_cartesian_prompt_v3.py")):
            if any(t.get("prompt_version") == version for t in tasks) and state.get("additional_renderers", {}).get(filename) != base.sha256(ROOT / "misc" / filename):
                raise ValueError("New prompt must be fingerprinted before spending")
        reserve = budget_gate(state, job)
        prevent_repeated_final_questions(state, job, tasks)
        jobdir = OUT / "jobs" / job_id
        counts = base.read_json(jobdir / "input-counts.json")
        if counts["requests_digest"] != job["requests_digest"] or set(counts["counts"]) != {r["custom_id"] for r in requests}:
            raise ValueError("Missing token counts for these exact requests")
        if max(counts["counts"].values()) > state["maximum_counted_input"]:
            raise ValueError("Input token gate failed")
        splits = base.read_json(HISTORY / "family-split.json")
        final_phase = job["phase"] in FINAL_PHASES
        expected = "test" if final_phase else "development"
        for task in tasks:
            families = task['campaign'].get('root_families', [task['campaign']['root_family']])
            if any(splits['families'][family]['split']!=expected for family in families):
                raise ValueError("Family split violation")
        # A nonempty engine result is insufficient: audit semantic inputs,
        # prompt coverage and regenerated gold immediately before spending.
        from misc.vp_goal_validate import validate as validate_tasks
        validate_tasks(tasks, expected)
        if final_phase:
            gate = base.read_json(OUT / "release-freeze.json")
            if not gate.get("passed") or job["tasks_digest"] not in gate.get("authorized_by_phase", {}).get(job["phase"], []):
                raise ValueError("Final membership must be audited and frozen before evaluation")
        else:
            manifest = base.read_json(OUT / "experiment-registry.json")
            if job["tasks_digest"] not in manifest["authorized_task_digests"]:
                raise ValueError("Register the experiment and rationale before spending")
        # Reserve durably before any operation that may create billable work.
        job.update(attempted_at=base.now(), reservation_micro=reserve, status="submission_unknown")
        save(state)
        client = client_for(job["provider"])
        try:
            if job.get("transport") == "direct":
                client = client.with_options(timeout=600.0)
                # The entire panel is reserved before workers start. Each request is
                # attempted once, with a durable per-request intent and raw receipt.
                def call_one(r):
                    cid = r["custom_id"]
                    intent = jobdir / (cid + ".intent.json")
                    if intent.exists():
                        raise ValueError("Direct request already attempted")
                    base.atomic_json(intent, {"attempted_at": base.now(), "request_digest": digest(r)})
                    try:
                        if job["provider"] == "Anthropic":
                            raw = client.messages.with_raw_response.create(**r["params"])
                            body = base.capture_json(jobdir / (cid + ".http.json"), raw)
                            result = {"custom_id": cid, "result": {"type": "succeeded", "message": body}}
                        else:
                            raw = client.responses.with_raw_response.create(**r["body"])
                            body = base.capture_json(jobdir / (cid + ".http.json"), raw)
                            result = {"custom_id": cid, "response": {"status_code": 200, "body": body}}
                        base.atomic_json(jobdir / (cid + ".result.json"), result)
                    except Exception as exc:
                        base.atomic_json(jobdir / (cid + ".error.json"), base.error_details(exc, client))
                        raise RuntimeError("Direct request uncertain; no retry") from None
                with ThreadPoolExecutor(max_workers=8) as pool:
                    for done in as_completed([pool.submit(call_one, r) for r in requests]):
                        done.result()
                job.update(batch_id="direct-" + job_id, status="awaiting_local_collection")
                state["status"] = "running_" + job["phase"]
                save(state)
                print(f"Completed direct panel {job_id}; maximum reserved ${reserve / 1e6:.5f}", flush=True)
                return
            if job["provider"] == "Anthropic":
                raw = client.messages.batches.with_raw_response.create(requests=requests)
                batch = base.capture_json(jobdir / "create.http.json", raw)
                status = batch["processing_status"]
            else:
                payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests).encode()
                base.atomic_bytes(jobdir / "input.jsonl", payload)
                with (jobdir / "input.jsonl").open("rb") as f:
                    raw = client.files.with_raw_response.create(file=f, purpose="batch")
                    uploaded = base.capture_json(jobdir / "upload.http.json", raw)
                job["input_file_id"] = uploaded["id"]
                save(state)
                raw = client.batches.with_raw_response.create(input_file_id=uploaded["id"], endpoint="/v1/responses",
                    completion_window="24h", metadata={"campaign": OUT.name, "job": job_id,
                    "tasks_digest": job["tasks_digest"], "retries": "0"})
                batch = base.capture_json(jobdir / "create.http.json", raw)
                status = batch["status"]
            job.update(batch_id=batch["id"], batch=batch, status=status)
            state["status"] = "running_" + job["phase"]
            save(state)
            print(f"Submitted {job_id}: {batch['id']}; reserved ${reserve / 1e6:.5f}", flush=True)
        except Exception as exc:
            job["error"] = base.error_details(exc, client)
            save(state)
            raise RuntimeError(f"{job_id} submission outcome uncertain; reservation retained, no retry") from None


def collect(job_id):
    with base.lock(OUT):
        state = load()
        job = state["jobs"][job_id]
        if job.get("collected_at"):
            return job
        jobdir = OUT / "jobs" / job_id
        if not job["batch_id"] and (jobdir / "create.http.json").exists():
            job["batch_id"] = base.read_json(jobdir / "create.http.json")["body"]["id"]
        if not job["batch_id"]:
            raise RuntimeError("No batch ID; reconcile existing submission without re-sending")
        client = client_for(job["provider"])
        anthropic = job["provider"] == "Anthropic"
        if job.get("transport") == "direct":
            results = [base.read_json(jobdir / (r["custom_id"] + ".result.json"))
                       for r in base.read_json(jobdir / "requests.json")]
            batch = {"id": job["batch_id"], "status": "completed", "processing_status": "ended"}
            job["status"] = "ended" if anthropic else "completed"
            return finish_job(state, job, results, batch)
        endpoint = client.messages.batches if anthropic else client.batches
        raw = endpoint.with_raw_response.retrieve(job["batch_id"])
        batch = base.capture_json(jobdir / "status.http.json", raw)
        job.update(batch=batch, status=batch["processing_status" if anthropic else "status"])
        save(state)
        print(f"{job_id}: {job['status']} {batch.get('request_counts')}", flush=True)
        if job["status"] not in ({"ended"} if anthropic else base.TERMINAL):
            return job
        results = []
        if anthropic:
            path = ant.download_results(client, jobdir, batch)
            results = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        else:
            for field in ("output_file_id", "error_file_id"):
                if batch.get(field):
                    raw = client.files.with_raw_response.content(batch[field])
                    content = raw.http_response.content
                    base.atomic_bytes(jobdir / (field + ".jsonl"), content)
                    results.extend(json.loads(line) for line in content.splitlines() if line.strip())
        return finish_job(state, job, results, batch)


def finish_job(state, job, results, batch):
        jobdir = OUT / "jobs" / job["id"]
        job_id = job["id"]
        anthropic = job["provider"] == "Anthropic"
        tasks, requests = verify_job(job)
        rows = [base.base_record(t, i, r, OUT.name, job_id) for i, (t, r) in enumerate(zip(tasks, requests))]
        if job.get("transport") == "direct":
            for row in rows:
                row["transport"] = "direct"
        at = base.now()
        rows = (ant.assemble if anthropic else base.assemble)(rows, results, batch, at)
        from misc.vp_goal_paradigm import grade as grade_paradigm
        for row in rows:
            if row['task'].get('task_type') in {'finite_paradigm','finite_contrast','finite_bundle'} and row['is_correct'] is not None:
                row['paradigm_score'] = grade_paradigm(row['task'], row.get('output_text'))
                row['is_correct'] = row['paradigm_score']['is_correct']
        base.atomic_json(jobdir / "results.json", rows)
        usage = {"input_tokens": 0, "output_tokens": 0, "cache_read": 0, "cache_write": 0}
        violations = []
        for row in rows:
            result = row.get("raw_batch_result") or {}
            message = ((result.get("result") or {}).get("message") or {}) if anthropic else ((result.get("response") or {}).get("body") or {})
            u = message.get("usage") or {}
            for key in ("input_tokens", "output_tokens"):
                usage[key] += u.get(key, 0) or 0
            detail = u.get("input_tokens_details") or {}
            usage["cache_read"] += (u.get("cache_read_input_tokens") if anthropic else detail.get("cached_tokens")) or 0
            usage["cache_write"] += (u.get("cache_creation_input_tokens") if anthropic else detail.get("cache_write_tokens")) or 0
            if u.get("input_tokens", 0) > INPUT_ALLOWANCE or u.get("output_tokens", 0) > PHASES[job["phase"]][1] or usage["cache_write"]:
                violations.append(row["task_id"])
        p = rates(job)
        completed = [r for r in rows if r["status"] == "completed" and r["answer"] is not None and not r["truncated"]]
        job.update(collected_at=at, usage=usage, summary=base.summarize(rows), completed_answers=len(completed),
                   completed_correct=sum(r["is_correct"] for r in completed),
                   actual_cost_upper_micro=usage["input_tokens"]*p["input_rate"]+usage["output_tokens"]*p["output_rate"],
                   token_policy_violations=violations)
        # Release unused reservation only after a complete terminal usage receipt.
        job["settled"] = (not violations and len(results) == job["n"] and all(
            (((r.get("result") or {}).get("message") or {}).get("usage") if anthropic else
            (((r.get("response") or {}).get("body") or {}).get("usage")) for r in results)))
        if job["actual_cost_upper_micro"] > job["reservation_micro"]:
            violations.append("cost_exceeds_reservation")
            job["settled"] = False
        if violations:
            state["status"] = "halted_token_policy_violation"
        elif not any(j["batch_id"] and not j.get("collected_at") for j in state["jobs"].values()):
            state["status"] = "review_" + job["phase"]
        save(state)
        base.atomic_json(jobdir / "summary.json", job)
        print(json.dumps({"job": job_id, "summary": job["summary"], "completed": len(completed),
                          "cost_upper_usd": job["actual_cost_upper_micro"]/1e6}, ensure_ascii=False), flush=True)
        return job


def status():
    state = load()
    print(json.dumps({"status": state["status"], "providers": {
        p: {"cap_usd": cfg["cap_micro"]/1e6,
            "committed_usd": committed(state,p)/1e6,
            "protected_remaining_usd": protected_remaining(state,p)/1e6,
            "historical_spend_usd": state["historical_spend_micro"][p]/1e6,
            "collected_cost_upper_usd": sum(j.get("actual_cost_upper_micro", 0) for j in state["jobs"].values() if j["provider"] == p)/1e6}
        for p, cfg in PROVIDERS.items()},
        "jobs": [{k:j.get(k) for k in ("id", "provider", "phase", "n", "status", "batch_id", "collected_at", "summary")}
                 for j in state["jobs"].values()]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "prepare", "count", "submit", "collect", "status"])
    parser.add_argument("--job")
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--provider", choices=PROVIDERS)
    parser.add_argument("--phase", choices=PHASES)
    parser.add_argument("--transport", choices=["batch", "direct"], default="batch")
    args = parser.parse_args()
    if args.command == "init": initialize()
    elif args.command == "prepare": prepare(args.job, args.tasks, args.provider, args.phase, args.transport)
    elif args.command == "count": count_inputs(args.job)
    elif args.command == "submit": submit(args.job)
    elif args.command == "collect": collect(args.job)
    else: status()


if __name__ == "__main__":
    main()
