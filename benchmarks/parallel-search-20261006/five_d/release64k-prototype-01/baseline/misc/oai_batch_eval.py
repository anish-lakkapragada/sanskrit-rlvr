#!/usr/bin/env python3
"""Single-rollout morphology evaluation through OpenAI Batch / Responses.

prepare is offline. submit uploads and creates each batch at most once.
collect/watch only retrieve existing jobs; they never generate or resubmit.
See benchmarks/oai/README.md for the artifact format and commands.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import sys
import time
import unicodedata
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finetune.prompts import extract_answer, render_vp_task

CONFIGS = (
    ("gpt-6-astra", "xhigh"),
    ("gpt-6-astra", "high"),
    ("gpt-6-sol", "xhigh"),
)
TEMPLATE = "v1/vp_task_eval.txt"
DATASET = ROOT / "benchmarks/full-tasks.json"
TERMINAL = {"completed", "failed", "expired", "cancelled"}
BATCH_RATES = {
    "gpt-6-astra": {"input": 5.0, "cached_input": 0.5, "cache_write": 6.25, "output": 25.0},
    "gpt-6-sol": {"input": 1.0, "cached_input": 0.1, "cache_write": 1.25, "output": 5.0},
}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


@contextmanager
def lock(out):
    (out / "_batch").mkdir(parents=True, exist_ok=True)
    with (out / "_batch/lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another batch command is updating this output directory") from None
        yield


def state_path(out):
    return out / "_batch/state.json"


def configuration_paths(out, slug):
    model, effort = slug.rsplit("-", 1)
    directory = out / model
    return {
        "result": directory / f"{effort}.json",
        "meta": directory / f"{effort}.meta.json",
        "work": directory / "_batch" / effort,
    }


def migrate_layout(out):
    """Move existing artifacts only; preserve every submitted batch and request."""
    state = read_json(state_path(out))
    migrated = []
    # Validate all destinations before moving anything. An interrupted move can
    # be resumed: the source will be absent and its destination already present.
    moves = []
    for slug in state["configurations"]:
        paths = configuration_paths(out, slug)
        for src, dst in ((out / f"{slug}.json", paths["result"]),
                         (out / f"{slug}.meta.json", paths["meta"]),
                         (out / "_batch" / slug, paths["work"])):
            if src.exists() and dst.exists():
                raise RuntimeError(f"Both source and destination exist: {src}, {dst}")
            if not src.exists() and not dst.exists():
                raise FileNotFoundError(f"Missing artifact: {src} / {dst}")
            moves.append((src, dst))
    for src, dst in moves:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            migrated.append({"from": str(src.relative_to(out)), "to": str(dst.relative_to(out))})
    for slug, cfg in state["configurations"].items():
        paths = configuration_paths(out, slug)
        cfg["input_path"] = str((paths["work"] / "input.jsonl").relative_to(out))
        cfg["result_path"] = str(paths["result"].relative_to(out))
        cfg["meta_path"] = str(paths["meta"].relative_to(out))
        cfg["work_dir"] = str(paths["work"].relative_to(out))
        if sha256(out / cfg["input_path"]) != cfg["input_sha256"]:
            raise ValueError(f"Input hash changed while moving {slug}")
        # Preserve completed summaries and usage instead of recreating metadata.
        meta = read_json(paths["meta"])
        for key in ("input_path", "result_path", "meta_path", "work_dir"):
            meta[key] = cfg[key]
        atomic_json(paths["meta"], meta)
    state["layout_version"] = 2
    save_state(out, state)
    if migrated:
        atomic_json(out / "_batch/layout-migration.json", {"migrated_at": now(), "moves": migrated})
    print(f"Model folders ready; moved {len(migrated)} artifacts without submitting requests", flush=True)


def save_state(out, state):
    state["updated_at"] = now()
    atomic_json(state_path(out), state)


def request_body(task, model, effort, max_output_tokens=2048):
    body = {
        "model": model,
        "input": [{"role": "user", "content": render_vp_task(task, TEMPLATE)}],
        "reasoning": {"mode": "standard", "effort": effort},
        "tools": [],
        "tool_choice": "none",
        "store": False,
        "stream": False,
        "truncation": "disabled",
    }
    if max_output_tokens is not None:
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer or None")
        body["max_output_tokens"] = max_output_tokens
    return body


def batch_request(task, index, model, effort, max_output_tokens=2048):
    return {"custom_id": f"task-{index:05d}", "method": "POST", "url": "/v1/responses",
            "body": request_body(task, model, effort, max_output_tokens)}


def base_record(task, index, request, run_id, slug):
    return {
        "schema_version": 1, "run_id": run_id, "configuration": slug,
        "task_index": index, "task_id": task["id"], "task": task,
        "sample_index": 0, "attempt_number": 1, "transport": "batch",
        "custom_id": request["custom_id"], "request": request,
        "status": "prepared", "batch_id": None, "batch_submitted_at": None,
        "collected_at": None, "latency_ms": None, "response_headers": None,
        "raw_batch_result": None, "output_text": None, "answer": None,
        "answer_normalized": None, "is_correct": None,
        "truncated": False, "refusals": [], "error": None,
    }


def prepare(out, max_output_tokens=2048):
    if state_path(out).exists():
        state = read_json(state_path(out))
        if state["max_output_tokens"] != max_output_tokens:
            raise ValueError("Existing run has a different output limit; refusing to reuse it")
        print(f"Already prepared: {state['run_id']}; existing submissions are preserved", flush=True)
        return state
    if any((out / f"{model}-{effort}.json").exists()
           or configuration_paths(out, f"{model}-{effort}")["result"].exists()
           for model, effort in CONFIGS):
        raise RuntimeError("Result files exist without state; refusing to overwrite or duplicate a run")
    tasks = read_json(DATASET)
    sources = [ROOT / "data/finetune/task-data" / f"{split}.json" for split in ("finetune", "validation")]
    if tasks != read_json(sources[0]) + read_json(sources[1]):
        raise ValueError("full-tasks.json is not exactly finetune.json + validation.json")
    if len(tasks) != 6687 or len({t["id"] for t in tasks}) != 6687:
        raise ValueError("Expected 6,687 unique tasks")
    run_id = "vp-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    state = {
        "schema_version": 1, "layout_version": 2, "run_id": run_id, "created_at": now(),
        "dataset": str(DATASET.relative_to(ROOT)), "dataset_sha256": sha256(DATASET),
        "task_count": len(tasks), "prompt_template": "prompts/" + TEMPLATE,
        "prompt_sha256": sha256(ROOT / "prompts" / TEMPLATE),
        "renderer_sha256": sha256(ROOT / "finetune/prompts.py"),
        "samples_per_task": 1, "max_output_tokens": max_output_tokens, "sdk_max_retries": 0,
        "output_limit_policy": ("no_explicit_limit" if max_output_tokens is None else "explicit_limit"),
        "output_limit_note": ("max_output_tokens omitted from every request; provider/model limits still apply"
                              if max_output_tokens is None else "Combined reasoning and visible output token cap"),
        "fresh_run": True, "uniform_request_cap": True, "transport": "batch",
        "reuse_previous_responses": False,
        "retry_failed_tasks": False, "continue_truncated_tasks": False,
        "input_tokens_per_task_budget_estimate": 460,
        "configurations": {},
    }
    atomic_json(out / "_batch/tasks.snapshot.json", tasks)
    atomic_bytes(out / "_batch/prompt.snapshot.txt", (ROOT / "prompts" / TEMPLATE).read_bytes())
    atomic_bytes(out / "_batch/renderer.snapshot.py", (ROOT / "finetune/prompts.py").read_bytes())
    for model, effort in CONFIGS:
        slug = f"{model}-{effort}"
        paths = configuration_paths(out, slug)
        requests = [batch_request(t, i, model, effort, max_output_tokens) for i, t in enumerate(tasks)]
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in requests).encode("utf-8")
        if len(payload) >= 200_000_000:
            raise ValueError("Batch input exceeds the 200 MB limit")
        input_path = paths["work"] / "input.jsonl"
        atomic_bytes(input_path, payload)
        atomic_bytes(paths["work"] / "example-prompt.txt", requests[0]["body"]["input"][0]["content"].encode("utf-8"))
        atomic_json(paths["result"], [base_record(t, i, r, run_id, slug) for i, (t, r) in enumerate(zip(tasks, requests))])
        state["configurations"][slug] = {
            "model": model, "effort": effort, "status": "prepared",
            "input_path": str(input_path.relative_to(out)), "input_sha256": sha256(input_path),
            "result_path": str(paths["result"].relative_to(out)),
            "meta_path": str(paths["meta"].relative_to(out)),
            "work_dir": str(paths["work"].relative_to(out)),
            "input_bytes": len(payload), "task_count": len(tasks),
            "input_file_id": None, "batch_id": None, "batch": None,
            "upload_attempted_at": None, "submit_attempted_at": None,
            "collected_at": None, "submission_error": None,
        }
        write_meta(out, state, slug)
        print(f"Prepared {slug}: {len(requests):,} requests, {len(payload) / 1e6:.2f} MB", flush=True)
    save_state(out, state)
    return state


def api_client():
    from dotenv import dotenv_values
    from openai import OpenAI
    key = dotenv_values(ROOT / ".env").get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing from the repository .env")
    # Pin the authorized provider and do not inherit a different API base URL.
    return OpenAI(api_key=key, base_url="https://api.openai.com/v1", max_retries=0, timeout=60.0)


def redact(value, key):
    """Errors occasionally echo a bad credential; never persist that credential."""
    if isinstance(value, str):
        return value.replace(key, "[REDACTED]") if key else value
    if isinstance(value, dict):
        return {k: redact(v, key) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, key) for v in value]
    return value


def error_details(exc, client):
    response = getattr(exc, "response", None)
    result = {"type": type(exc).__name__, "message": str(exc),
              "status_code": getattr(exc, "status_code", None),
              "request_id": getattr(exc, "request_id", None)}
    if response is not None:
        result["headers"] = list(response.headers.multi_items())
        try:
            result["body"] = response.json()
        except ValueError:
            result["body_text"] = response.text
    return redact(result, client.api_key)


def capture_json(path, raw):
    """Capture raw JSON, including unknown fields, without SDK model projection."""
    body = raw.http_response.json()
    atomic_json(path, {"received_at": now(), "status_code": raw.status_code,
                       "headers": list(raw.headers.multi_items()), "body": body})
    return body


def update_pending_records(out, slug, cfg):
    result_path = configuration_paths(out, slug)["result"]
    rows = read_json(result_path)
    for row in rows:
        if row["raw_batch_result"] is not None:
            continue
        row["batch_id"] = cfg["batch_id"]
        row["batch_submitted_at"] = cfg["submit_attempted_at"]
        row["status"] = "submitted" if cfg["batch_id"] else cfg["status"]
        row["error"] = cfg.get("submission_error")
    atomic_json(result_path, rows)


def submit_config(client, out, state, slug):
    """Persist an attempt before each POST, and never replay an attempted POST."""
    cfg = state["configurations"][slug]
    work = configuration_paths(out, slug)["work"]
    if cfg["batch_id"] or cfg["submit_attempted_at"] or cfg.get("submission_error"):
        print(f"Skip {slug}: already submitted/attempted ({cfg['status']})", flush=True)
        return
    input_path = out / cfg["input_path"]
    if sha256(input_path) != cfg["input_sha256"]:
        raise ValueError(f"Prepared input changed: {input_path}")
    try:
        if not cfg["input_file_id"]:
            if cfg["upload_attempted_at"]:
                print(f"Skip {slug}: an earlier upload has an unknown outcome; no retry", flush=True)
                return
            cfg["upload_attempted_at"] = now()
            cfg["status"] = "uploading"
            save_state(out, state)
            with input_path.open("rb") as f:
                raw = client.files.with_raw_response.create(file=f, purpose="batch")
            uploaded = capture_json(work / "upload.http.json", raw)
            cfg["input_file_id"] = uploaded["id"]
            cfg["status"] = "uploaded"
            save_state(out, state)
        cfg["submit_attempted_at"] = now()
        cfg["status"] = "submission_unknown"
        save_state(out, state)
        raw = client.batches.with_raw_response.create(
            input_file_id=cfg["input_file_id"], endpoint="/v1/responses", completion_window="24h",
            metadata={"run_id": state["run_id"], "configuration": slug,
                      "dataset_sha256": state["dataset_sha256"], "prompt_sha256": state["prompt_sha256"],
                      "task_count": str(state["task_count"]), "samples_per_task": "1", "retries": "0"},
        )
        batch = capture_json(work / "create.http.json", raw)
        cfg.update(batch_id=batch["id"], batch=batch, status=batch["status"])
        save_state(out, state)
        print(f"Submitted {slug}: {batch['id']} ({batch['status']})", flush=True)
    except Exception as exc:
        cfg["submission_error"] = error_details(exc, client)
        cfg["status"] = "submission_unknown" if cfg["submit_attempted_at"] else "upload_failed"
        save_state(out, state)
        print(f"{slug}: {type(exc).__name__}; recorded, no retry", flush=True)
    update_pending_records(out, slug, cfg)
    write_meta(out, state, slug)


def recover_created_batch(client, out, state, slug):
    """Read-only recovery after a crash/timeout; it never issues a creation POST."""
    cfg = state["configurations"][slug]
    if cfg["batch_id"] or not cfg["submit_attempted_at"]:
        return
    work = configuration_paths(out, slug)["work"]
    cached = work / "create.http.json"
    candidates = []
    if cached.exists():
        candidates = [read_json(cached)["body"]]
    else:
        after = None
        while True:
            kwargs = {"limit": 100, **({"after": after} if after else {})}
            raw = client.batches.with_raw_response.list(**kwargs)
            page = capture_json(work / f"recovery-{uuid4().hex}.http.json", raw)
            candidates.extend(b for b in page["data"] if b.get("input_file_id") == cfg["input_file_id"]
                              and (b.get("metadata") or {}).get("run_id") == state["run_id"])
            if not page.get("has_more") or not page["data"]:
                break
            after = page["data"][-1]["id"]
    if len(candidates) > 1:
        raise RuntimeError(f"Multiple batches match {slug}; manual reconciliation required")
    if candidates:
        batch = candidates[0]
        cfg.update(batch_id=batch["id"], batch=batch, status=batch["status"])
        cfg["recovered_at"] = now()
        save_state(out, state)
        update_pending_records(out, slug, cfg)


def normalize(text):
    return unicodedata.normalize("NFC", text.strip())


def apply_result(row, result, collected_at):
    row = copy.deepcopy(row)
    row["raw_batch_result"] = result
    row["collected_at"] = collected_at
    response = result.get("response") or {}
    body = response.get("body")
    body = body if isinstance(body, dict) else {}
    output = body.get("output") or []
    texts, refusals = [], []
    for item in output:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") == "output_text":
                texts.append(content.get("text", ""))
            elif content.get("type") == "refusal":
                refusals.append(content.get("refusal", ""))
    row["output_text"] = "".join(texts)
    row["refusals"] = refusals
    row["truncated"] = (body.get("incomplete_details") or {}).get("reason") == "max_output_tokens"
    # A failed API attempt is distinct from a model producing the wrong/no answer.
    failure = result.get("error") or body.get("error")
    if response.get("status_code") != 200 or body.get("status") in {"failed", "cancelled"} or failure:
        row.update(status="api_error", is_correct=None,
                   error=failure or {"code": "http_error", "status_code": response.get("status_code")})
        return row
    row["answer"] = extract_answer(row["output_text"])
    row["answer_normalized"] = normalize(row["answer"]) if row["answer"] is not None else None
    row["is_correct"] = row["answer_normalized"] in {normalize(g) for g in row["task"]["gold_devanagari"]}
    row["status"] = "incomplete" if body.get("status") == "incomplete" else ("refused" if refusals else "completed")
    row["error"] = None
    return row


def assemble(rows, results, batch, collected_at):
    by_id = {}
    expected = {r["custom_id"] for r in rows}
    for result in results:
        cid = result.get("custom_id")
        if cid not in expected or cid in by_id:
            raise ValueError(f"Unexpected or duplicate batch custom_id: {cid!r}")
        by_id[cid] = result
    assembled = []
    for original in rows:
        row = copy.deepcopy(original)
        row["batch_id"] = batch["id"]
        if row["custom_id"] in by_id:
            row = apply_result(row, by_id[row["custom_id"]], collected_at)
        else:
            row.update(status="batch_" + batch["status"], is_correct=None, collected_at=collected_at,
                       error={"code": "missing_batch_result", "batch_status": batch["status"],
                              "batch_errors": batch.get("errors")})
        assembled.append(row)
    return assembled


def summarize(rows):
    statuses = Counter(r["status"] for r in rows)
    correct = sum(r["is_correct"] is True for r in rows)
    return {"task_count": len(rows), "correct": correct,
            "incorrect_or_no_answer": sum(r["is_correct"] is False for r in rows),
            "unscored": sum(r["is_correct"] is None for r in rows),
            "pass_at_1_all_tasks": correct / len(rows) if rows else None,
            "truncated": sum(r["truncated"] for r in rows), "statuses": dict(statuses)}


def write_meta(out, state, slug, rows=None):
    cfg = state["configurations"][slug]
    meta = {k: v for k, v in state.items() if k != "configurations"}
    meta.update(configuration=slug, **cfg)
    meta["batch_prices_usd_per_million_tokens"] = BATCH_RATES[cfg["model"]]
    meta["pricing_source"] = "https://developers.openai.com/api/docs/pricing"
    meta["pricing_checked_on"] = "2026-09-24"
    meta["per_task_headers_and_latency"] = "Not exposed by Batch API; null in task records"
    meta["result_body_location"] = "raw_batch_result.response.body"
    if rows is not None:
        meta["summary"] = summarize(rows)
        meta["summary"]["final"] = cfg["collected_at"] is not None
        usage = Counter()
        for row in rows:
            body = ((row.get("raw_batch_result") or {}).get("response") or {}).get("body") or {}
            if not isinstance(body, dict):
                continue
            u = body.get("usage") or {}
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                usage[key] += u.get(key, 0)
            usage["reasoning_tokens"] += (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
            usage["cached_input_tokens"] += (u.get("input_tokens_details") or {}).get("cached_tokens", 0)
        meta["usage_totals"] = dict(usage)
    atomic_json(configuration_paths(out, slug)["meta"], meta)


def download_file(client, out, slug, file_id):
    path = configuration_paths(out, slug)["work"] / (file_id + ".jsonl")
    if path.exists():
        return path
    raw = client.files.with_raw_response.content(file_id)
    content = raw.http_response.content
    # Validate before marking a file downloaded, preserving error bodies separately.
    for line in content.splitlines():
        if line.strip():
            json.loads(line)
    atomic_bytes(path, content)
    atomic_json(path.with_suffix(".http.json"), {"received_at": now(), "status_code": raw.status_code,
                "headers": list(raw.headers.multi_items()), "file_id": file_id,
                "body_path": path.name, "sha256": sha256(path)})
    return path


def collect(client, out, state):
    for slug, cfg in state["configurations"].items():
        paths = configuration_paths(out, slug)
        if cfg["collected_at"]:
            continue
        if not cfg["batch_id"]:
            if cfg["submit_attempted_at"] and not cfg.get("recovery_checked_at"):
                recover_created_batch(client, out, state, slug)
                cfg["recovery_checked_at"] = now()
                save_state(out, state)
            if not cfg["batch_id"]:
                continue
        try:
            raw = client.batches.with_raw_response.retrieve(cfg["batch_id"])
            batch = capture_json(paths["work"] / "status.http.json", raw)
            event = {"received_at": now(), "headers": list(raw.headers.multi_items()), "body": batch}
            with (paths["work"] / "polls.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
            cfg.update(batch=batch, status=batch["status"])
            save_state(out, state)
            if batch["status"] not in TERMINAL:
                write_meta(out, state, slug)
                continue
            results = []
            for key in ("output_file_id", "error_file_id"):
                if batch.get(key):
                    path = download_file(client, out, slug, batch[key])
                    results.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            collected_at = now()
            rows = assemble(read_json(paths["result"]), results, batch, collected_at)
            atomic_json(paths["result"], rows)
            cfg["collected_at"] = collected_at
            save_state(out, state)
            write_meta(out, state, slug, rows)
            print(f"Collected {slug}: {json.dumps(summarize(rows))}", flush=True)
        except Exception as exc:
            # No retries within an operation and no inference resubmission. A later
            # watch cycle may read status/files again; GETs do not generate answers.
            cfg["last_collection_error"] = error_details(exc, client)
            save_state(out, state)
            print(f"{slug}: collection {type(exc).__name__}; no task resubmission", flush=True)


def status_lines(state):
    lines = []
    for slug, cfg in state["configurations"].items():
        counts = (cfg.get("batch") or {}).get("request_counts") or {}
        lines.append(f"{slug}: {cfg['status']} | {cfg.get('batch_id') or '-'} | "
                     f"{counts.get('completed', 0)} completed, {counts.get('failed', 0)} failed"
                     + (" | collected" if cfg["collected_at"] else ""))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "submit", "collect", "watch", "status", "migrate-layout"))
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks/oai")
    parser.add_argument("--interval", type=int, default=60)
    limits = parser.add_mutually_exclusive_group()
    limits.add_argument("--max-output-tokens", type=int, default=2048,
                        help="Output cap for prepare (legacy default: 2048)")
    limits.add_argument("--no-output-limit", action="store_true",
                        help="For prepare: omit max_output_tokens entirely; provider limits still apply")
    args = parser.parse_args()
    out = args.out.resolve()
    if args.command == "migrate-layout":
        with lock(out):
            migrate_layout(out)
        return
    if args.command == "prepare":
        with lock(out):
            prepare(out, None if args.no_output_limit else args.max_output_tokens)
        return
    if args.command == "status":
        print(status_lines(read_json(state_path(out))))
        return
    client = api_client()
    if args.command == "submit":
        with lock(out):
            state = read_json(state_path(out))
            for slug in state["configurations"]:
                submit_config(client, out, state, slug)
            print(status_lines(state), flush=True)
        return
    last_status = None
    while True:
        with lock(out):
            state = read_json(state_path(out))
            collect(client, out, state)
            current = status_lines(state)
            if current != last_status:
                print(now() + "\n" + current, flush=True)
                last_status = current
            active = any(c["batch_id"] and not c["collected_at"] for c in state["configurations"].values())
        if args.command == "collect" or not active:
            break
        time.sleep(max(1, min(args.interval, 60)))


if __name__ == "__main__":
    main()
