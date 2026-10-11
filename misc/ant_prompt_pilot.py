#!/usr/bin/env python3
"""Five fixed-seed direct Opus 5.5 xhigh requests for the proposed v2 prompt.

One attempt per task, no retries. This pilot never updates benchmark results.
"""
import copy
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import ant_batch_eval as ant

base = ant.base
TEMPLATE = "v2/vp_task_eval.txt"
OUT = ROOT / "benchmarks/ant/claude-opus-5-5/_pilots/v2-xhigh-20260925"


def costs(rows):
    nominal = billed = 0.0
    waived_input = 0
    for row in rows:
        body = row.get("raw_response") or {}
        usage = body.get("usage") or {}
        i, o = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        cost = (i * 4 + o * 20) / 1e6
        nominal += cost
        category = (body.get("stop_details") or {}).get("category")
        # Anthropic does not bill pre-output refusals outside these three categories.
        if body.get("stop_reason") == "refusal" and o == 0 and category not in {"bio", "frontier_llm", "reasoning_extraction"}:
            waived_input += i
        else:
            billed += cost
    return {"nominal_usage_cost_usd": round(nominal, 9), "estimated_cost_usd": round(billed, 9),
            "input_tokens_excluded_for_unbilled_refusals": waived_input,
            "refusal_billing_source": "https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback#how-refusals-are-billed"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tasks = base.read_json(base.DATASET)
    indices = sorted(random.Random(20260925).sample(range(len(tasks)), 5))
    meta_path = OUT / "meta.json"
    if meta_path.exists():
        meta = base.read_json(meta_path)
        rows = base.read_json(OUT / "prepared.json")
    else:
        meta = {"run_id": "opus55-xhigh-v2-pilot-20260925", "created_at": base.now(),
                "model": "claude-opus-5-5", "effort": "xhigh", "transport": "direct",
                "prompt_template": "prompts/" + TEMPLATE,
                "prompt_sha256": base.sha256(ROOT / "prompts" / TEMPLATE),
                "dataset_sha256": base.sha256(base.DATASET), "task_indices": indices,
                "selection": "5 tasks sampled without replacement using random.Random(20260925)",
                "max_tokens": 128000, "sdk_max_retries": 0, "retry_failed_tasks": False,
                "direct_prices_usd_per_million_tokens": {"input": 4.0, "output": 20.0},
                "completed_at": None}
        rows = []
        for i in indices:
            task = tasks[i]
            params = ant.request_params(task, meta["model"], meta["effort"])
            params["messages"] = [{"role": "user", "content": base.render_vp_task(task, TEMPLATE)}]
            params["service_tier"] = "standard_only"
            assert "<thinking>" not in params["messages"][0]["content"]
            request = {"custom_id": f"task-{i:05d}", "method": "POST", "url": "/v1/messages", "body": params}
            row = ant.new_record(task, i, request, meta["run_id"], "claude-opus-5-5-xhigh")
            row.update(transport="direct", raw_response=None)
            rows.append(row)
        base.atomic_bytes(OUT / "prompt.snapshot.txt", (ROOT / "prompts" / TEMPLATE).read_bytes())
        base.atomic_json(OUT / "prepared.json", rows)
        base.atomic_json(OUT / "results.json", rows)
        base.atomic_json(meta_path, meta)
    client = ant.api_client()

    def evaluate(original):
        row = copy.deepcopy(original)
        cid = row["custom_id"]
        result_path = OUT / f"{cid}.json"
        if result_path.exists():
            return base.read_json(result_path)
        marker = OUT / f"{cid}.attempt.json"
        if marker.exists():
            row.update(status="unknown_outcome", error={"code": "attempt_already_recorded_no_retry"})
            return row
        attempted_at = base.now()
        with marker.open("x") as f:
            json.dump({"attempted_at": attempted_at, "request": row["request"]}, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        row["attempted_at"] = attempted_at
        start = time.monotonic()
        try:
            raw = client.messages.with_raw_response.create(**row["request"]["body"], timeout=600.0)
            body = base.capture_json(OUT / f"{cid}.http.json", raw)
            # Reuse scoring only; the saved record retains the native direct response.
            scored = ant.apply_result(row, {"custom_id": cid, "result": {"type": "succeeded", "message": body}}, base.now())
            row.update(scored)
            row.update(raw_batch_result=None, raw_response=body, http_status_code=raw.status_code,
                       response_headers=list(raw.headers.multi_items()), request_id=raw.headers.get("request-id"))
        except Exception as exc:
            row.update(status="api_error", error=base.error_details(exc, client), collected_at=base.now())
        row["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
        base.atomic_json(result_path, row)
        return row

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(evaluate, row) for row in rows]):
            row = future.result()
            results[row["custom_id"]] = row
            base.atomic_json(OUT / "results.json", [results.get(r["custom_id"], r) for r in rows])
            usage = (row.get("raw_response") or {}).get("usage") or {}
            print(json.dumps({"task_index": row["task_index"], "task_id": row["task_id"],
                  "status": row["status"], "stop_reason": row["stop_reason"], "output_text": row["output_text"],
                  "correct": row["is_correct"], "input_tokens": usage.get("input_tokens"),
                  "output_tokens": usage.get("output_tokens"), "error": row["error"]}, ensure_ascii=False), flush=True)
    final = [results[r["custom_id"]] for r in rows]
    usages = [(r.get("raw_response") or {}).get("usage") or {} for r in final]
    total_input = sum(u.get("input_tokens", 0) for u in usages)
    total_output = sum(u.get("output_tokens", 0) for u in usages)
    meta.update(completed_at=base.now(), summary=base.summarize(final),
                usage_totals={"input_tokens": total_input, "output_tokens": total_output},
                **costs(final))
    base.atomic_json(meta_path, meta)
    print(json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
