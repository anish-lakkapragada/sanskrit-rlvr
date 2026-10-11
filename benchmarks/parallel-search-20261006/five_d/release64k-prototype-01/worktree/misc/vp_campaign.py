#!/usr/bin/env python3
"""Budget-locked creation benchmark campaign. Only `submit` generates answers.

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
from finetune.prompts import render_vp_task

OUT = ROOT / "benchmarks/creation-campaign-20261006"
TEMPLATE = "v2/vp_task_eval.txt"
PROVIDERS = {"Anthropic": {"model": "claude-opus-5-5", "cap_micro": 1_000_000_000,
                           "input_rate": 2, "output_rate": 10},
             "OpenAI": {"model": "gpt-6-astra", "cap_micro": 2_000_000_000,
                        "input_rate": 5, "output_rate": 25}}
# Hard-coded authorization prevents an edited report from raising execution caps.
PHASES = {
    "opus_screen": ("high", 4096, {"Anthropic": 6000, "OpenAI": 0}),
    "astra_screen": ("high", 4096, {"Anthropic": 0, "OpenAI": 1200}),
    "confirm": ("xhigh", 16384, {"Anthropic": 1200, "OpenAI": 1200}),
    "bench_final": ("xhigh", 16384, {"Anthropic": 1000, "OpenAI": 1000}),
    "hard_final": ("xhigh", 16384, {"Anthropic": 1000, "OpenAI": 1000}),
    "cap_check": ("xhigh", 128000, {"Anthropic": 100, "OpenAI": 100}),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def client_for(provider):
    return ant.api_client() if provider == "Anthropic" else base.api_client()


def load():
    state = base.read_json(OUT / "ledger.json")
    if state["authorization"] != PROVIDERS or state["phase_policy"] != json.loads(json.dumps(PHASES)):
        raise ValueError("Campaign authorization has changed")
    if base.sha256(OUT / "policy.json") != state["policy_sha256"]:
        raise ValueError("Frozen policy changed")
    if base.sha256(ROOT / "prompts" / TEMPLATE) != state["prompt_sha256"]:
        raise ValueError("Frozen prompt changed")
    if base.sha256(ROOT / "finetune/prompts.py") != state["renderer_sha256"]:
        raise ValueError("Prompt renderer changed")
    return state


def save(state):
    state["updated_at"] = base.now()
    base.atomic_json(OUT / "ledger.json", state)


def initialize():
    with base.lock(OUT):
        if (OUT / "ledger.json").exists():
            return load()
        proposal = base.read_json(ROOT / "benchmarks/analysis/performance-study/study.json")["moving_forward"]
        base.atomic_json(OUT / "policy.json", proposal)
        state = {"schema_version": 1, "created_at": base.now(),
                 "authorization": PROVIDERS, "phase_policy": PHASES,
                 "policy_sha256": base.sha256(OUT / "policy.json"),
                 "prompt_sha256": base.sha256(ROOT / "prompts" / TEMPLATE),
                 "renderer_sha256": base.sha256(ROOT / "finetune/prompts.py"),
                 "sdk_max_retries": 0, "billed_input_allowance": 1000,
                 "maximum_counted_input": 900,
                 "accounting": "Full worst-case reservations remain charged against the cap even after collection; actual token costs reported separately. No savings reused automatically.",
                 "jobs": {}, "status": "preparing_discovery"}
        save(state)
        return state


def request(task, provider, phase, index):
    model = PROVIDERS[provider]["model"]
    effort, cap, _ = PHASES[phase]
    prompt = render_vp_task(task, TEMPLATE)
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


def prepare(job_id, tasks_path, provider, phase):
    if not job_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in job_id):
        raise ValueError("Invalid job ID")
    tasks = base.read_json(tasks_path)
    requests = [request(t, provider, phase, i) for i, t in enumerate(tasks)]
    validate_requests(tasks, requests, provider, phase)
    with base.lock(OUT):
        state = load()
        if job_id in state["jobs"]:
            old = state["jobs"][job_id]
            if old["tasks_digest"] != digest(tasks) or old["provider"] != provider or old["phase"] != phase:
                raise ValueError("Job ID already describes different work")
            return old
        jobdir = OUT / "jobs" / job_id
        base.atomic_json(jobdir / "tasks.json", tasks)
        base.atomic_json(jobdir / "requests.json", requests)
        job = {"id": job_id, "provider": provider, "phase": phase, "n": len(tasks),
               "tasks_digest": digest(tasks), "requests_digest": digest(requests),
               "created_at": base.now(), "status": "prepared", "batch_id": None,
               "attempted_at": None, "reservation_micro": 0, "input_file_id": None}
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
                           "note": "Provider estimates; require <=900 and reserve 1000 billed input tokens per task."})
    if len(counts) != len(requests) or max(counts.values()) > state["maximum_counted_input"]:
        raise ValueError("Input token gate failed")
    print(f"Input gate passed {job_id}: max {max(counts.values())}, allowance 1000", flush=True)


def budget_gate(state, job):
    if state.get("status", "").startswith("halted"):
        raise ValueError("Campaign halted; review the recorded violation before spending")
    provider, phase = job["provider"], job["phase"]
    if job["attempted_at"]:
        raise ValueError("Submission already attempted; never replay")
    used_n = sum(j["n"] for j in state["jobs"].values()
                 if j["provider"] == provider and j["phase"] == phase and j["attempted_at"])
    if used_n + job["n"] > PHASES[phase][2][provider]:
        raise ValueError("Cumulative phase allowance exceeded")
    used = sum(j["reservation_micro"] for j in state["jobs"].values() if j["provider"] == provider)
    p = PROVIDERS[provider]
    reserve = job["n"] * (1000 * p["input_rate"] + PHASES[phase][1] * p["output_rate"])
    if used + reserve > p["cap_micro"]:
        raise ValueError("Hard provider budget exceeded")
    # Protect every unsubmitted planned phase, including calibration and final calls.
    remaining = 0
    for name, (_, output, limits) in PHASES.items():
        submitted = sum(j["n"] for j in state["jobs"].values()
                        if j["provider"] == provider and j["phase"] == name and j["attempted_at"])
        if name == phase:
            submitted += job["n"]
        remaining += (limits[provider] - submitted) * (1000 * p["input_rate"] + output * p["output_rate"])
    if used + reserve + remaining > p["cap_micro"]:
        raise ValueError("Submission would consume protected later-phase reserves")
    return reserve


def submit(job_id):
    with base.lock(OUT):
        state = load()
        job = state["jobs"][job_id]
        tasks, requests = verify_job(job)
        reserve = budget_gate(state, job)
        jobdir = OUT / "jobs" / job_id
        counts = base.read_json(jobdir / "input-counts.json")
        if counts["requests_digest"] != job["requests_digest"] or set(counts["counts"]) != {r["custom_id"] for r in requests}:
            raise ValueError("Missing token counts for these exact requests")
        if max(counts["counts"].values()) > state["maximum_counted_input"]:
            raise ValueError("Input token gate failed")
        splits = base.read_json(OUT / "family-split.json")
        if base.sha256(OUT / "family-split.json") != state.get("family_split_sha256"):
            raise ValueError("Frozen family split changed")
        final_phase = job["phase"] in {"bench_final", "hard_final", "cap_check"}
        for task in tasks:
            family = task["campaign"]["root_family"]
            expected = "test" if final_phase else "development"
            if splits["families"][family]["split"] != expected:
                raise ValueError("Family split violation")
        if job["phase"] != "opus_screen":
            gate_path = OUT / ("final-gate.json" if final_phase else "calibration-gate.json")
            gate = base.read_json(gate_path)
            if not gate.get("passed") or job["tasks_digest"] not in gate.get("authorized_task_digests", []):
                raise ValueError("Phase prerequisites have not passed for this exact task list")
        else:
            discovery = base.read_json(OUT / "discovery-manifest.json")
            matches = [i for i, b in enumerate(discovery["batches"]) if b["digest"] == job["tasks_digest"]]
            if len(matches) != 1:
                raise ValueError("Discovery list is not in the frozen manifest")
            audit = base.read_json(OUT / "discovery-audit.json")
            if not audit.get("passed_for_discovery"):
                raise ValueError("Discovery audit has not passed")
            if matches[0] > 0:
                review = base.read_json(OUT / f"review-discovery-{matches[0]:02d}.json")
                if not review.get("continue_discovery"):
                    raise ValueError("Previous discovery batch did not pass its review gate")
        # Reserve durably before any operation that may create billable work.
        job.update(attempted_at=base.now(), reservation_micro=reserve, status="submission_unknown")
        save(state)
        client = client_for(job["provider"])
        try:
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
        tasks, requests = verify_job(job)
        rows = [base.base_record(t, i, r, OUT.name, job_id) for i, (t, r) in enumerate(zip(tasks, requests))]
        at = base.now()
        rows = (ant.assemble if anthropic else base.assemble)(rows, results, batch, at)
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
            if u.get("input_tokens", 0) > 1000 or u.get("output_tokens", 0) > PHASES[job["phase"]][1] or usage["cache_write"]:
                violations.append(row["task_id"])
        p = PROVIDERS[job["provider"]]
        completed = [r for r in rows if r["status"] == "completed" and r["answer"] is not None and not r["truncated"]]
        job.update(collected_at=at, usage=usage, summary=base.summarize(rows), completed_answers=len(completed),
                   completed_correct=sum(r["is_correct"] for r in completed),
                   actual_cost_upper_micro=usage["input_tokens"]*p["input_rate"]+usage["output_tokens"]*p["output_rate"],
                   token_policy_violations=violations)
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
            "reserved_usd": sum(j["reservation_micro"] for j in state["jobs"].values() if j["provider"] == p)/1e6,
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
    args = parser.parse_args()
    if args.command == "init": initialize()
    elif args.command == "prepare": prepare(args.job, args.tasks, args.provider, args.phase)
    elif args.command == "count": count_inputs(args.job)
    elif args.command == "submit": submit(args.job)
    elif args.command == "collect": collect(args.job)
    else: status()


if __name__ == "__main__":
    main()
