#!/usr/bin/env python3
"""At most five prompt revisions, ten fixed tasks each, one direct attempt each.

Each invocation runs one explicitly supplied prompt revision. Request settings
are fixed at Opus 5.5 xhigh; results never overwrite full benchmark artifacts.
"""
import argparse
import copy
import json
import os
import random
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
OUT = ROOT / "benchmarks/ant/claude-opus-5-5/_pilots/prompt-loop-20260925"
MAX_ITERATIONS = 5


def load_campaign(out):
    path = out / "state.json"
    if path.exists():
        return base.read_json(path)
    tasks = base.read_json(base.DATASET)
    prior = base.read_json(ROOT / "benchmarks/ant/claude-opus-5-5/_pilots/v2-xhigh-20260925/results.json")
    indices = [r["task_index"] for r in prior]
    rng = random.Random(20260925)
    for voice in ("Kartari", "Karmani", "Bhave"):
        if not any(tasks[i]["morphology"]["prayoga"] == voice for i in indices):
            indices.append(rng.choice([i for i, t in enumerate(tasks)
                                       if t["morphology"]["prayoga"] == voice and i not in indices]))
    indices += rng.sample([i for i in range(len(tasks)) if i not in indices], 10 - len(indices))
    indices.sort()
    state = {"run_id": "opus55-xhigh-prompt-loop-20260925", "created_at": base.now(),
             "max_iterations": MAX_ITERATIONS, "tasks_per_iteration": 10,
             "task_indices": indices, "dataset_sha256": base.sha256(base.DATASET),
             "selection": "Earlier five pilot tasks, add missing voices, then fixed-seed random fill; unchanged across revisions",
             "model": "claude-opus-5-5", "effort": "xhigh", "max_tokens": 128000,
             "transport": "direct", "sdk_max_retries": 0, "retry_failed_tasks": False,
             "purpose": "Prompt development; not an independent benchmark accuracy estimate",
             "iterations": {}}
    base.atomic_json(out / "tasks.snapshot.json", [tasks[i] for i in indices])
    base.atomic_json(path, state)
    return state


def run_iteration(out, iteration, template):
    state = load_campaign(out)
    if not 1 <= iteration <= MAX_ITERATIONS:
        raise ValueError("At most five iterations are authorized")
    if any(v.get("passes_check") for v in state["iterations"].values()):
        print("The goal was reached; no additional requests sent", flush=True)
        return
    for previous in range(1, iteration):
        if not state["iterations"].get(str(previous), {}).get("completed_at"):
            raise ValueError("Finish the preceding iteration before starting another")
    work = out / f"iteration-{iteration}"
    if str(iteration) in state["iterations"]:
        meta = state["iterations"][str(iteration)]
        if meta["template"] != template or meta["prompt_sha256"] != base.sha256(ROOT / "prompts" / template):
            raise ValueError("Cannot change an already prepared iteration")
        if meta.get("completed_at"):
            print(json.dumps(meta, ensure_ascii=False), flush=True)
            return
        rows = base.read_json(work / "prepared.json")
    else:
        prompt_hash = base.sha256(ROOT / "prompts" / template)
        if any(v["prompt_sha256"] == prompt_hash for v in state["iterations"].values()):
            raise ValueError("Each iteration must test a new prompt revision")
        tasks = base.read_json(out / "tasks.snapshot.json")
        rows = []
        for i, task in zip(state["task_indices"], tasks):
            params = ant.request_params(task, state["model"], state["effort"])
            params["messages"] = [{"role": "user", "content": base.render_vp_task(task, template)}]
            params["service_tier"] = "standard_only"
            assert "<thinking>" not in params["messages"][0]["content"]
            request = {"custom_id": f"task-{i:05d}", "method": "POST", "url": "/v1/messages", "body": params}
            row = ant.new_record(task, i, request, f"{state['run_id']}-iteration-{iteration}", "claude-opus-5-5-xhigh")
            row.update(transport="direct", raw_response=None, pilot_iteration=iteration)
            rows.append(row)
        assert len(rows) == 10 and len({r["task_id"] for r in rows}) == 10
        meta = {"iteration": iteration, "template": template, "prompt_sha256": prompt_hash,
                "created_at": base.now(), "completed_at": None}
        base.atomic_bytes(work / "prompt.snapshot.txt", (ROOT / "prompts" / template).read_bytes())
        base.atomic_json(work / "prepared.json", rows)
        base.atomic_json(work / "results.json", rows)
        state["iterations"][str(iteration)] = meta
        base.atomic_json(out / "state.json", state)
    client = ant.api_client()

    def evaluate(original):
        row = copy.deepcopy(original)
        cid = row["custom_id"]
        result_path, marker, receipt = (work / f"{cid}{suffix}" for suffix in (".json", ".attempt.json", ".http.json"))
        if result_path.exists():
            return base.read_json(result_path)
        if marker.exists() and not receipt.exists():
            row.update(status="unknown_outcome", error={"code": "attempt_already_recorded_no_retry"})
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
            scored = ant.apply_result(row, {"custom_id": cid, "result": {"type": "succeeded", "message": body}}, base.now())
            row.update(scored)
            row.update(raw_batch_result=None, raw_response=body, http_status_code=saved["status_code"],
                       response_headers=saved["headers"], request_id=dict(saved["headers"]).get("request-id"))
        except Exception as exc:
            row.update(status="api_error", error=base.error_details(exc, client), collected_at=base.now())
        row["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
        base.atomic_json(result_path, row)
        return row

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(evaluate, r) for r in rows]):
            row = future.result()
            results[row["custom_id"]] = row
            base.atomic_json(work / "results.json", [results.get(r["custom_id"], r) for r in rows])
            body = row.get("raw_response") or {}
            print(json.dumps({"iteration": iteration, "task_index": row["task_index"], "status": row["status"],
                  "category": (body.get("stop_details") or {}).get("category"), "answer": row["answer"],
                  "correct": row["is_correct"], "output_tokens": (body.get("usage") or {}).get("output_tokens"),
                  "error": row["error"]}, ensure_ascii=False), flush=True)
    final = [results[r["custom_id"]] for r in rows]
    categories = Counter((r["raw_response"].get("stop_details") or {}).get("category", "uncategorized")
                         for r in final if r["status"] == "refused")
    valid = sum(r["status"] == "completed" and r["answer"] is not None for r in final)
    meta.update(completed_at=base.now(), summary=base.summarize(final), refusal_categories=dict(categories),
                refusal_count=sum(categories.values()), valid_answer_count=valid, passes_check=valid == 10,
                **costs(final))
    base.atomic_json(work / "meta.json", meta)
    state["iterations"][str(iteration)] = meta
    state["estimated_total_cost_usd"] = sum(v.get("estimated_cost_usd", 0) for v in state["iterations"].values())
    if meta["passes_check"]:
        state.update(status="passed_pilot", selected_template=template, completed_at=base.now())
    elif iteration == MAX_ITERATIONS:
        state.update(status="iteration_limit_reached", completed_at=base.now())
    else:
        state["status"] = "awaiting_next_revision"
    base.atomic_json(out / "state.json", state)
    client.close()
    print(json.dumps(meta, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iteration", type=int, required=True, choices=range(1, 6))
    parser.add_argument("--template", required=True)
    args = parser.parse_args()
    with base.lock(OUT):
        run_iteration(OUT, args.iteration, args.template)
