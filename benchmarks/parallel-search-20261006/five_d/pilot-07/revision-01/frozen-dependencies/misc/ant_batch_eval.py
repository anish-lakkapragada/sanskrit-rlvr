#!/usr/bin/env python3
"""Fresh, single-attempt Sanskrit evaluations using Anthropic Message Batches.

prepare is offline and requires explicit model/effort selections. Only submit
creates paid requests. collect/watch never submit, retry, or continue a task.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as base

MODELS = ("claude-opus-5-5", "claude-fable-5-1", "claude-sonnet-5")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
DEFAULT_EFFORTS = dict(zip(MODELS, ("medium", "high", "high")))
MODEL_MAX_TOKENS = 128000
TEMPLATE = "v2/vp_task_eval.txt"
BATCH_RATES = {
    "claude-opus-5-5": {"input": 2.0, "output": 10.0},
    "claude-fable-5-1": {"input": 5.0, "output": 25.0},
    "claude-sonnet-5": {"input": 1.0, "output": 5.0},
}
PRICING_SOURCE = "https://platform.claude.com/docs/en/about-claude/pricing"


def api_client():
    import anthropic
    from dotenv import dotenv_values
    key = dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is missing from the repository .env")
    return anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com",
                               max_retries=0, timeout=60.0)


def preflight(client, out):
    """Read-only model access/capability check; no generation requests."""
    for model in MODELS:
        raw = client.models.with_raw_response.retrieve(model)
        body = base.capture_json(out / "_preflight" / f"{model}.http.json", raw)
        caps = body.get("capabilities") or {}
        if body.get("id") != model or body.get("max_tokens", 0) < MODEL_MAX_TOKENS:
            raise ValueError(f"Unexpected model identity or output ceiling for {model}")
        for feature in (caps.get("batch", {}), (caps.get("thinking", {}).get("types") or {}).get("adaptive", {})):
            if not feature.get("supported"):
                raise ValueError(f"Batch/adaptive thinking is not available for {model}")
        if not all((caps.get("effort", {}).get(e) or {}).get("supported") for e in EFFORTS):
            raise ValueError(f"Effort options have changed for {model}; review before preparing a run")
        print(f"{model}: accessible; Batch/adaptive supported; max_tokens={body['max_tokens']}; efforts={','.join(EFFORTS)}")


def estimate(out):
    """Offline price scenarios using actual usage from the completed OpenAI runs."""
    report = {
        "generated_at": base.now(), "tasks_per_configuration": 6687,
        "pricing_source": PRICING_SOURCE, "pricing_checked_on": "2026-09-25",
        "batch_prices_usd_per_million_tokens": BATCH_RATES,
        "assumptions": [
            "Each Claude model is evaluated once on all 6687 tasks at one chosen effort.",
            "Scenarios reuse measured OpenAI input/output counts, including hidden reasoning.",
            "These are token-volume scenarios, not effort-level equivalences or confidence intervals.",
            "Claude tokenization and reasoning lengths differ; actual cost may lie outside this range.",
            "Input is priced uncached; no prompt caching, tools, or additional attempts are assumed.",
        ],
        "scenarios": [],
    }
    for model, effort in base.CONFIGS:
        path = ROOT / "benchmarks/oai" / model / f"{effort}.json"
        rows = base.read_json(path)
        if len(rows) != 6687 or any(r["raw_batch_result"] is None for r in rows):
            raise ValueError(f"OpenAI source run is incomplete: {path}")
        usages = [r["raw_batch_result"]["response"]["body"]["usage"] for r in rows]
        outputs = sorted(u["output_tokens"] for u in usages)
        inputs = sum(u["input_tokens"] for u in usages)
        total_output = sum(outputs)
        costs = {m: (inputs * p["input"] + total_output * p["output"]) / 1e6
                 for m, p in BATCH_RATES.items()}
        report["scenarios"].append({
            "source": str(path.relative_to(ROOT)), "source_sha256": base.sha256(path),
            "total_input_tokens": inputs, "total_output_tokens": total_output,
            "total_reasoning_tokens": sum((u.get("output_tokens_details") or {}).get("reasoning_tokens", 0) for u in usages),
            "mean_output_tokens": statistics.mean(outputs),
            "p90_output_tokens": outputs[math.ceil(.9 * len(outputs)) - 1],
            "max_output_tokens": max(outputs),
            "cost_per_claude_model_usd": {m: round(c, 2) for m, c in costs.items()},
            "all_three_models_total_usd": round(sum(costs.values()), 2),
        })
    path = out / "cost-estimate.json"
    base.atomic_json(path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def configuration(model, effort):
    if model not in MODELS or effort not in EFFORTS:
        raise ValueError(f"Unsupported model/effort: {model}:{effort}")
    return f"{model}-{effort}"


def request_params(task, model, effort):
    configuration(model, effort)
    return {
        "model": model, "max_tokens": MODEL_MAX_TOKENS,
        "messages": [{"role": "user", "content": base.render_vp_task(task, TEMPLATE)}],
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": effort},
        "tools": [], "tool_choice": {"type": "none"}, "stream": False,
    }


def batch_request(task, index, model, effort):
    return {"custom_id": f"task-{index:05d}", "params": request_params(task, model, effort)}


def new_record(task, index, request, run_id, slug):
    row = base.base_record(task, index, request, run_id, slug)
    row.update(provider="anthropic", thinking_text=None, stop_reason=None)
    return row


def prepare(out, configurations, dataset=base.DATASET, expected_count=6687):
    configurations = list(configurations)
    slugs = [configuration(*c) for c in configurations]
    if not slugs or len(set(slugs)) != len(slugs):
        raise ValueError("Choose at least one configuration, without duplicates")
    if base.state_path(out).exists():
        state = base.read_json(base.state_path(out))
        if set(state["configurations"]) != set(slugs) or state["max_tokens"] != MODEL_MAX_TOKENS:
            raise ValueError("Existing run has different configurations; refusing to mix runs")
        if state["prompt_template"] != "prompts/" + TEMPLATE or state["prompt_sha256"] != base.sha256(ROOT / "prompts" / TEMPLATE):
            raise ValueError("Existing run has a different prompt; refusing to mix runs")
        print(f"Already prepared: {state['run_id']}; no requests sent", flush=True)
        return state
    if any(base.configuration_paths(out, slug)["result"].exists() for slug in slugs):
        raise RuntimeError("Result files exist without a ledger; refusing to overwrite")
    tasks = base.read_json(dataset)
    if len(tasks) != expected_count or len({t["id"] for t in tasks}) != expected_count:
        raise ValueError(f"Expected {expected_count} unique tasks")
    if Path(dataset) == base.DATASET:
        source = ROOT / "data/finetune/task-data"
        if tasks != base.read_json(source / "finetune.json") + base.read_json(source / "validation.json"):
            raise ValueError("Dataset differs from finetune.json + validation.json")
    state = {
        "schema_version": 1, "provider": "anthropic", "transport": "batch",
        "run_id": "ant-" + uuid4().hex[:16], "created_at": base.now(),
        "dataset": str(dataset), "dataset_sha256": base.sha256(dataset),
        "task_count": len(tasks), "prompt_template": "prompts/" + TEMPLATE,
        "prompt_sha256": base.sha256(ROOT / "prompts" / TEMPLATE),
        "renderer_sha256": base.sha256(ROOT / "finetune/prompts.py"),
        "samples_per_task": 1, "sdk_max_retries": 0, "retry_failed_tasks": False,
        "continue_truncated_tasks": False, "reuse_previous_responses": False,
        "fresh_run": True, "max_tokens": MODEL_MAX_TOKENS,
        "output_limit_policy": "standard_model_maximum",
        "output_limit_note": "Anthropic requires max_tokens; 128000 is the standard model ceiling, not unlimited",
        "thinking": {"type": "adaptive", "display": "summarized"},
        "configurations": {},
    }
    base.atomic_json(out / "_batch/tasks.snapshot.json", tasks)
    base.atomic_bytes(out / "_batch/prompt.snapshot.txt", (ROOT / "prompts" / TEMPLATE).read_bytes())
    base.atomic_bytes(out / "_batch/renderer.snapshot.py", (ROOT / "finetune/prompts.py").read_bytes())
    for model, effort in configurations:
        slug = configuration(model, effort)
        paths = base.configuration_paths(out, slug)
        requests = [batch_request(t, i, model, effort) for i, t in enumerate(tasks)]
        payload = (json.dumps({"requests": requests}, ensure_ascii=False) + "\n").encode("utf-8")
        if len(requests) > 100000 or len(payload) >= 256000000:
            raise ValueError("Anthropic batch request exceeds size/count limits")
        input_path = paths["work"] / "input.json"
        base.atomic_bytes(input_path, payload)
        base.atomic_json(paths["result"], [new_record(t, i, r, state["run_id"], slug)
                                         for i, (t, r) in enumerate(zip(tasks, requests))])
        state["configurations"][slug] = {
            "model": model, "effort": effort, "status": "prepared", "task_count": len(tasks),
            "input_path": str(input_path.relative_to(out)), "input_sha256": base.sha256(input_path),
            "input_bytes": len(payload), "result_path": str(paths["result"].relative_to(out)),
            "meta_path": str(paths["meta"].relative_to(out)), "work_dir": str(paths["work"].relative_to(out)),
            "batch_id": None, "batch": None, "submit_attempted_at": None,
            "submission_error": None, "collected_at": None,
        }
        write_meta(out, state, slug)
        print(f"Prepared {slug}: {len(requests):,} requests; no API calls", flush=True)
    base.save_state(out, state)
    return state


def write_meta(out, state, slug, rows=None):
    cfg = state["configurations"][slug]
    meta = {k: v for k, v in state.items() if k != "configurations"}
    meta.update(configuration=slug, **cfg)
    meta.update(batch_prices_usd_per_million_tokens=BATCH_RATES[cfg["model"]],
                pricing_source=PRICING_SOURCE, pricing_checked_on="2026-09-25",
                result_body_location="raw_batch_result.result.message",
                per_task_headers_and_latency="Not exposed by Message Batches; null in records",
                thinking_text_note="Provider summary only; raw chain of thought is not returned")
    if rows is not None:
        meta["summary"] = {**base.summarize(rows), "final": cfg["collected_at"] is not None}
        usage = Counter()
        for row in rows:
            message = ((row.get("raw_batch_result") or {}).get("result") or {}).get("message") or {}
            u = message.get("usage") or {}
            for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
                usage[key] += u.get(key, 0) or 0
        meta["usage_totals"] = dict(usage)
        # No prompt caching is requested. Do not silently misprice an unexpected cached response.
        if not usage["cache_creation_input_tokens"] and not usage["cache_read_input_tokens"]:
            rates = BATCH_RATES[cfg["model"]]
            meta["estimated_cost_usd"] = (usage["input_tokens"] * rates["input"]
                                           + usage["output_tokens"] * rates["output"]) / 1e6
        else:
            meta["estimated_cost_usd"] = None
            meta["cost_note"] = "Unexpected cache usage: consult raw usage and provider pricing"
    base.atomic_json(base.configuration_paths(out, slug)["meta"], meta)


def update_pending(out, state, slug):
    cfg = state["configurations"][slug]
    path = out / cfg["result_path"]
    rows = base.read_json(path)
    if any(r["run_id"] != state["run_id"] for r in rows):
        raise ValueError("Result file belongs to a different run")
    for row in rows:
        if row["raw_batch_result"] is None:
            row.update(batch_id=cfg["batch_id"], batch_submitted_at=cfg["submit_attempted_at"],
                       status="submitted" if cfg["batch_id"] else cfg["status"],
                       error=cfg["submission_error"])
    base.atomic_json(path, rows)
    write_meta(out, state, slug)


def submit_config(client, out, state, slug):
    cfg = state["configurations"][slug]
    if cfg["batch_id"] or cfg["submit_attempted_at"]:
        print(f"Skip {slug}: already attempted; no new request", flush=True)
        return
    path = out / cfg["input_path"]
    if base.sha256(path) != cfg["input_sha256"]:
        raise ValueError("Prepared input changed")
    payload = base.read_json(path)
    cfg.update(submit_attempted_at=base.now(), status="submission_unknown")
    base.save_state(out, state)  # Durable before POST: a timeout must never cause a second attempt.
    try:
        raw = client.messages.batches.with_raw_response.create(requests=payload["requests"])
        batch = base.capture_json(out / cfg["work_dir"] / "create.http.json", raw)
        cfg.update(batch_id=batch["id"], batch=batch, status=batch["processing_status"])
        print(f"Submitted {slug}: {batch['id']} ({cfg['status']})", flush=True)
    except Exception as exc:
        cfg["submission_error"] = base.error_details(exc, client)
        print(f"{slug}: {type(exc).__name__}; recorded, no retry", flush=True)
    base.save_state(out, state)
    update_pending(out, state, slug)


def apply_result(row, raw, collected_at):
    row = copy.deepcopy(row)
    row.update(raw_batch_result=raw, collected_at=collected_at, output_text=None,
               thinking_text=None, answer=None, answer_normalized=None, is_correct=None,
               stop_reason=None, truncated=False, refusals=[], error=None)
    result = raw.get("result") or {}
    if result.get("type") != "succeeded":
        row.update(status="api_error", error=result.get("error") or {"code": result.get("type", "unknown_result")})
        return row
    message = result["message"]
    content = message.get("content") or []
    row["output_text"] = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    row["thinking_text"] = "\n".join(b.get("thinking", "") for b in content if b.get("type") == "thinking")
    row["stop_reason"] = message.get("stop_reason")
    row["truncated"] = row["stop_reason"] in {"max_tokens", "model_context_window_exceeded"}
    if row["stop_reason"] == "refusal":
        row["refusals"] = [row["output_text"]]
    # Only score assistant text: an answer in a thinking summary is not a final answer.
    row["answer"] = base.extract_answer(row["output_text"])
    row["answer_normalized"] = base.normalize(row["answer"]) if row["answer"] is not None else None
    row["is_correct"] = row["answer_normalized"] in {base.normalize(g) for g in row["task"]["gold_devanagari"]}
    row["status"] = ("incomplete" if row["truncated"] or row["stop_reason"] in {"pause_turn", "tool_use"}
                     else "refused" if row["refusals"] else "completed")
    return row


def assemble(rows, results, batch, collected_at):
    expected = {r["custom_id"] for r in rows}
    if len(expected) != len(rows):
        raise ValueError("Duplicate custom_id in prepared records")
    by_id = {}
    for raw in results:
        cid = raw.get("custom_id")
        if cid not in expected or cid in by_id:
            raise ValueError(f"Unexpected or duplicate custom_id: {cid!r}")
        by_id[cid] = raw
    assembled = []
    for original in rows:
        row = copy.deepcopy(original)
        row["batch_id"] = batch["id"]
        if row["custom_id"] in by_id:
            row = apply_result(row, by_id[row["custom_id"]], collected_at)
        else:
            row.update(status="batch_ended", collected_at=collected_at, output_text=None,
                       thinking_text=None, answer=None, answer_normalized=None, is_correct=None,
                       raw_batch_result=None, error={"code": "missing_batch_result"})
        assembled.append(row)
    return assembled


def download_results(client, work, batch):
    import httpx
    path = work / "results.jsonl"
    if path.exists():
        return path
    url = batch.get("results_url")
    parsed = urlparse(url or "")
    if parsed.scheme != "https" or parsed.netloc != "api.anthropic.com":
        raise ValueError("Missing or unexpected Anthropic results URL")
    # Retrieve the original bytes instead of projecting through SDK response models.
    response = client.get(url, cast_to=httpx.Response,
                          options={"headers": {"Accept": "application/binary"}, "timeout": 600.0})
    data = response.content
    for line in data.splitlines():
        if line.strip():
            json.loads(line)
    base.atomic_bytes(path, data)
    base.atomic_json(work / "results.http.json", {"received_at": base.now(), "status_code": response.status_code,
                     "headers": list(response.headers.multi_items()), "body_path": path.name,
                     "sha256": base.sha256(path)})
    return path


def collect(client, out, state):
    for slug, cfg in state["configurations"].items():
        if cfg["collected_at"]:
            continue
        work = out / cfg["work_dir"]
        # A saved creation receipt can repair an interrupted local state write without any POST.
        if not cfg["batch_id"] and cfg["submit_attempted_at"] and (work / "create.http.json").exists():
            batch = base.read_json(work / "create.http.json")["body"]
            cfg.update(batch_id=batch["id"], batch=batch, status=batch["processing_status"])
            base.save_state(out, state)
            update_pending(out, state, slug)
        if not cfg["batch_id"]:
            continue
        try:
            raw = client.messages.batches.with_raw_response.retrieve(cfg["batch_id"])
            batch = base.capture_json(work / "status.http.json", raw)
            with (work / "polls.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"received_at": base.now(), "body": batch}, ensure_ascii=False) + "\n")
            cfg.update(batch=batch, status=batch["processing_status"])
            base.save_state(out, state)
            if cfg["status"] != "ended":
                write_meta(out, state, slug)
                continue
            path = download_results(client, work, batch)
            results = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            original = base.read_json(out / cfg["result_path"])
            if any(r["run_id"] != state["run_id"] for r in original):
                raise ValueError("Result file belongs to a different run")
            at = base.now()
            rows = assemble(original, results, batch, at)
            base.atomic_json(out / cfg["result_path"], rows)
            cfg["collected_at"] = at
            cfg["last_collection_error"] = None
            # Commit metadata before marking collection complete in the durable ledger.
            write_meta(out, state, slug, rows)
            base.save_state(out, state)
            print(f"Collected {slug}: {json.dumps(base.summarize(rows))}", flush=True)
        except Exception as exc:
            cfg["collected_at"] = None
            cfg["last_collection_error"] = base.error_details(exc, client)
            base.save_state(out, state)
            print(f"{slug}: collection {type(exc).__name__}; no generation retry", flush=True)


def status_lines(state):
    lines = []
    for slug, cfg in state["configurations"].items():
        counts = (cfg.get("batch") or {}).get("request_counts") or {}
        lines.append(f"{slug}: {cfg['status']} | {cfg.get('batch_id') or '-'} | "
                     f"{counts.get('succeeded', 0)} succeeded, {counts.get('processing', 0)} processing, "
                     f"{counts.get('errored', 0)} errored, {counts.get('expired', 0)} expired, "
                     f"{counts.get('canceled', 0)} canceled" + (" | collected" if cfg["collected_at"] else ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "estimate", "prepare", "submit", "collect", "watch", "status"))
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks/ant")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--effort", choices=EFFORTS, help="Explicit effort for all three models (prepare only)")
    choice.add_argument("--config", action="append", metavar="MODEL:EFFORT",
                        help="Explicit configuration; repeat to select multiple (prepare only)")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.command == "estimate":
        estimate(out)
        return
    if args.command == "preflight":
        preflight(api_client(), out)
        return
    if args.command == "prepare":
        if not args.effort and not args.config:
            parser.error("prepare requires --effort or --config; no effort is chosen implicitly")
        configurations = ([(m, args.effort) for m in MODELS] if args.effort else
                          [tuple(value.rsplit(":", 1)) for value in args.config])
        if any(len(c) != 2 for c in configurations):
            parser.error("--config must have the form MODEL:EFFORT")
        with base.lock(out):
            prepare(out, configurations)
        return
    if args.command == "status":
        print(status_lines(base.read_json(base.state_path(out))))
        return
    client = api_client()
    if args.command == "submit":
        with base.lock(out):
            state = base.read_json(base.state_path(out))
            for slug in state["configurations"]:
                submit_config(client, out, state, slug)
            print(status_lines(state), flush=True)
        return
    last_status = None
    while True:
        with base.lock(out):
            state = base.read_json(base.state_path(out))
            collect(client, out, state)
            current = status_lines(state)
            if current != last_status:
                print(base.now() + "\n" + current, flush=True)
                last_status = current
            active = any(c["batch_id"] and not c["collected_at"] for c in state["configurations"].values())
        if args.command == "collect" or not active:
            break
        time.sleep(max(1, min(args.interval, 60)))


if __name__ == "__main__":
    main()
