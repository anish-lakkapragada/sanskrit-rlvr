#!/usr/bin/env python3
"""One round of a prompt-development campaign capped at 100 direct attempts.

Opus 5.5 xhigh only, no retries. All rounds and unsuccessful responses persist.
Use fixed tasks for prompt comparisons and fresh tasks for additional checks.
"""
import argparse
import copy
import difflib
import json
import os
import random
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import ant_batch_eval as ant
from misc.ant_prompt_pilot import costs

base = ant.base
OUT = ROOT / "benchmarks/ant/claude-opus-5-5/_pilots/faithful-prompt-20260925"
LIMIT = 100


def campaign():
    if (OUT / "state.json").exists():
        return base.read_json(OUT / "state.json")
    prior = base.read_json(ROOT / "benchmarks/ant/claude-opus-5-5/_pilots/prompt-loop-20260925/state.json")
    tasks = base.read_json(base.DATASET)
    fixed = prior["task_indices"]
    fresh = [i for i in range(len(tasks)) if i not in fixed]
    random.Random(2026092502).shuffle(fresh)
    state = {
        "run_id": "opus55-xhigh-faithful-prompt-20260925", "created_at": base.now(),
        "max_requests": LIMIT, "reserved_requests": 0, "attempted_requests": 0,
        "dataset_sha256": base.sha256(base.DATASET), "fixed_task_indices": fixed,
        "fresh_task_pool": fresh[:LIMIT], "model": "claude-opus-5-5", "effort": "xhigh",
        "max_tokens": 128000, "transport": "direct", "sdk_max_retries": 0,
        "retry_failed_tasks": False, "purpose": "Prompt development; not a benchmark run",
        "reference_template": "v2/vp_task_eval.txt", "rounds": {},
    }
    base.atomic_json(OUT / "tasks.snapshot.json", tasks)
    base.atomic_bytes(OUT / "reference-prompt.txt", (ROOT / "prompts/v2/vp_task_eval.txt").read_bytes())
    base.atomic_json(OUT / "state.json", state)
    return state


def run_round(label, template, sample, count, prepare_only=False, include_task_indices=()):
    if not re.fullmatch(r"[a-z0-9-]+", label):
        raise ValueError("Use a simple unique round label")
    state = campaign()
    include_task_indices = sorted(set(include_task_indices))
    if sample == "challenge":
        if not include_task_indices or len(include_task_indices) > count:
            raise ValueError("Challenge rounds require explicit included task indices")
    elif include_task_indices:
        raise ValueError("Explicit task indices require a challenge round")
    work = OUT / label
    prompt_path = ROOT / "prompts" / template
    prompt_hash = base.sha256(prompt_path)
    if label in state["rounds"]:
        meta = state["rounds"][label]
        if (meta["template"], meta["prompt_sha256"], meta["sample"], meta["task_count"]) != (template, prompt_hash, sample, count):
            raise ValueError("Cannot change an existing round")
        if meta.get("included_task_indices", []) != include_task_indices:
            raise ValueError("Cannot change an existing round's task selection")
        if meta.get("completed_at"):
            print(json.dumps(meta, ensure_ascii=False), flush=True)
            return
        rows = base.read_json(work / "prepared.json")
    else:
        if not 1 <= count <= LIMIT or state["reserved_requests"] + count > LIMIT:
            raise ValueError("This round would exceed the 100-request budget")
        if any(not r.get("completed_at") for r in state["rounds"].values()):
            raise ValueError("Complete the current round first")
        tasks = base.read_json(OUT / "tasks.snapshot.json")
        if sample == "fixed":
            indices = state["fixed_task_indices"]
            if count != len(indices):
                raise ValueError("Fixed comparisons use all ten development tasks")
        else:
            used = {i for r in state["rounds"].values() for i in r["task_indices"]}
            if any(i not in used for i in include_task_indices):
                raise ValueError("Challenge inclusions must refer to previously tested tasks")
            indices = include_task_indices + [i for i in state["fresh_task_pool"] if i not in used][:count-len(include_task_indices)]
            if len(indices) != count:
                raise ValueError("Insufficient fresh tasks")
        rows = []
        for i in indices:
            task = tasks[i]
            params = ant.request_params(task, state["model"], state["effort"])
            params["messages"] = [{"role": "user", "content": base.render_vp_task(task, template)}]
            params["service_tier"] = "standard_only"
            assert "<thinking>" not in params["messages"][0]["content"]
            request = {"custom_id": f"task-{i:05d}", "method": "POST", "url": "/v1/messages", "body": params}
            row = ant.new_record(task, i, request, f"{state['run_id']}-{label}", "claude-opus-5-5-xhigh")
            row.update(transport="direct", raw_response=None, pilot_round=label)
            rows.append(row)
        reference = (OUT / "reference-prompt.txt").read_text()
        candidate = prompt_path.read_text()
        matcher = difflib.SequenceMatcher(None, reference.split(), candidate.split(), autojunk=False)
        meta = {
            "label": label, "template": template, "prompt_sha256": prompt_hash,
            "sample": sample, "task_count": count, "task_indices": indices,
            "included_task_indices": include_task_indices,
            "created_at": base.now(), "completed_at": None,
            "reference_word_count": len(reference.split()), "candidate_word_count": len(candidate.split()),
            "unchanged_reference_words": sum(block.size for block in matcher.get_matching_blocks()),
            "word_sequence_similarity": matcher.ratio(),
        }
        base.atomic_bytes(work / "prompt.snapshot.txt", prompt_path.read_bytes())
        base.atomic_bytes(work / "prompt.diff", "".join(difflib.unified_diff(reference.splitlines(True), candidate.splitlines(True), fromfile="reference", tofile=template)).encode())
        base.atomic_json(work / "prepared.json", rows)
        base.atomic_json(work / "results.json", rows)
        # Reserve the whole round before any calls; failures still consume a slot.
        state["rounds"][label] = meta
        state["reserved_requests"] += count
        assert state["reserved_requests"] <= LIMIT
        base.atomic_json(OUT / "state.json", state)
    if prepare_only:
        print(json.dumps({"prepared": label, "requests": len(rows), "reserved_requests": state["reserved_requests"]}), flush=True)
        return
    client = ant.api_client()
    assert client.max_retries == 0

    def evaluate(original):
        row = copy.deepcopy(original)
        cid = row["custom_id"]
        result_path, marker, receipt = (work / f"{cid}{suffix}" for suffix in (".json", ".attempt.json", ".http.json"))
        if result_path.exists():
            return base.read_json(result_path)
        if marker.exists() and not receipt.exists():
            row.update(status="unknown_outcome", error={"code": "attempt_already_recorded_no_retry"})
            base.atomic_json(result_path, row)
            return row
        start = time.monotonic()
        try:
            if receipt.exists():
                saved = base.read_json(receipt)
                body = saved["body"]
                row["attempted_at"] = base.read_json(marker)["attempted_at"]
            else:
                row["attempted_at"] = base.now()
                with marker.open("x") as f:
                    json.dump({"attempted_at": row["attempted_at"], "request": row["request"]}, f, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                raw = client.messages.with_raw_response.create(**row["request"]["body"], timeout=600.0)
                body = base.capture_json(receipt, raw)
                saved = base.read_json(receipt)
            row.update(ant.apply_result(row, {"custom_id": cid, "result": {"type": "succeeded", "message": body}}, base.now()))
            row.update(raw_batch_result=None, raw_response=body, http_status_code=saved["status_code"],
                       response_headers=saved["headers"], request_id=dict(saved["headers"]).get("request-id"))
        except Exception as exc:
            row.update(status="api_error", error=base.error_details(exc, client), collected_at=base.now())
        row["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
        base.atomic_json(result_path, row)
        return row

    results = {}
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            for future in as_completed([pool.submit(evaluate, r) for r in rows]):
                row = future.result()
                results[row["custom_id"]] = row
                base.atomic_json(work / "results.json", [results.get(r["custom_id"], r) for r in rows])
                body = row.get("raw_response") or {}
                print(json.dumps({"round": label, "task_index": row["task_index"], "status": row["status"],
                    "category": (body.get("stop_details") or {}).get("category"), "answer": row["answer"],
                    "correct": row["is_correct"], "output_tokens": (body.get("usage") or {}).get("output_tokens"),
                    "error": row["error"]}, ensure_ascii=False), flush=True)
    finally:
        client.close()
    final = [results[r["custom_id"]] for r in rows]
    categories = Counter(((r.get("raw_response") or {}).get("stop_details") or {}).get("category", "uncategorized")
                         for r in final if r["status"] == "refused")
    valid = sum(r["status"] == "completed" and r["answer"] is not None for r in final)
    usage = [(r.get("raw_response") or {}).get("usage") or {} for r in final]
    meta.update(completed_at=base.now(), summary=base.summarize(final), refusal_categories=dict(categories),
                refusal_count=sum(categories.values()), valid_answer_count=valid, passes_check=valid == count,
                usage_totals={k: sum(u.get(k, 0) for u in usage) for k in ("input_tokens", "output_tokens")}, **costs(final))
    base.atomic_json(work / "meta.json", meta)
    state["rounds"][label] = meta
    state["attempted_requests"] = len(list(OUT.glob("*/task-*.attempt.json")))
    assert state["attempted_requests"] <= state["reserved_requests"] <= LIMIT
    state["estimated_total_cost_usd"] = sum(r.get("estimated_cost_usd", 0) for r in state["rounds"].values())
    base.atomic_json(OUT / "state.json", state)
    print(json.dumps(meta, ensure_ascii=False), flush=True)
    print(json.dumps({"attempted_requests": state["attempted_requests"], "remaining_requests": LIMIT-state["reserved_requests"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--sample", choices=("fixed", "fresh", "challenge"), default="fixed")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--include-task-index", type=int, action="append", default=[])
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    with base.lock(OUT):
        run_round(args.label, args.template, args.sample, args.count, args.prepare_only, args.include_task_index)
