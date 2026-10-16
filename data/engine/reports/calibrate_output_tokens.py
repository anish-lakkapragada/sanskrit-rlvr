"""Run the 20 saved prompts on Astra xHigh without a client output-token cap.

This makes paid API requests. Run only when authorized:
    uv run --with httpx --with python-dotenv python \
        data/engine/reports/calibrate_output_tokens.py

One completion per prompt, no automatic retries. Responses and exact requests
are saved before summarizing provider-reported usage, including reasoning.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import time

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = ROOT / "data/engine/prompts/v2/samples"
MODEL = "gpt-6-astra"


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def summarize(records):
    billed = [r for r in records if r.get("usage")]
    complete = [r for r in billed if r["status"] == "completed"]
    output = [r["usage"]["output_tokens"] for r in billed]
    reasoning = [r["usage"].get("output_tokens_details", {}).get("reasoning_tokens", 0) for r in billed]
    return {
        "requests": len(records), "requests_with_usage": len(billed),
        "completed": len(complete), "incomplete_or_error": len(records) - len(complete),
        "mean_input_tokens": statistics.mean(r["usage"]["input_tokens"] for r in billed) if billed else None,
        "mean_output_tokens": statistics.mean(output) if output else None,
        "median_output_tokens": statistics.median(output) if output else None,
        "min_output_tokens": min(output) if output else None,
        "max_output_tokens": max(output) if output else None,
        "mean_reasoning_tokens": statistics.mean(reasoning) if reasoning else None,
        "mean_non_reasoning_output_tokens": statistics.mean(o - r for o, r in zip(output, reasoning)) if output else None,
        "total_input_tokens": sum(r["usage"]["input_tokens"] for r in billed),
        "total_output_tokens": sum(output), "total_reasoning_tokens": sum(reasoning),
        "usage_based_cost_usd": round(sum(r["usage_based_cost_usd"] for r in billed), 8),
        "completed_mean_output_tokens": statistics.mean(r["usage"]["output_tokens"] for r in complete) if complete else None,
    }


def main():
    key = dotenv_values(ROOT / ".env").get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing from the repository .env and environment")
    manifest_bytes = (SAMPLES / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    tasks = []
    snapshot_files = {"manifest.json": manifest_bytes}
    for family, dataset in manifest["datasets"].items():
        assert len(dataset["samples"]) == 5, family
        for sample in dataset["samples"]:
            path = SAMPLES / sample["path"]
            prompt = path.read_text()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == sample["prompt_sha256"], path
            assert not sample.get("warnings"), sample["task_id"]
            answer = (SAMPLES / sample["answer_path"]).read_bytes()
            assert hashlib.sha256(answer).hexdigest() == sample["answer_sha256"]
            assert json.loads(answer)["id"] == sample["task_id"]
            snapshot_files[sample["path"]] = prompt.encode()
            snapshot_files[sample["answer_path"]] = answer
            tasks.append({"family": family, "sample": path.parent.name, "task_id": sample["task_id"],
                          "prompt_path": str(path.relative_to(ROOT)), "prompt_sha256": digest,
                          "request": {"model": MODEL, "input": [{"role": "user", "content": prompt}],
                                      "reasoning": {"effort": "xhigh"}, "service_tier": "default",
                                      "store": False, "stream": True}})
    assert len(tasks) == 20
    started = datetime.now(timezone.utc)
    output_dir = ROOT / "data/datasets/calibration" / f"astra-xhigh-samples-{started.strftime('%Y%m%dT%H%M%SZ')}"
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, contents in snapshot_files.items():
        path = output_dir / "sample-snapshot" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
    settings = {"started_at": started.isoformat(), "model": MODEL, "reasoning_effort": "xhigh",
                "max_output_tokens": "omitted; model/provider maximum still applies", "service_tier": "default",
                "sample_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "sample_snapshot": "sample-snapshot/manifest.json",
                "expected_requests": 20, "automatic_retries": 0,
                "rates_usd_per_million_tokens": {"input": 10, "cached_input": 1, "output": 50},
                "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6-astra",
                "meaning_of_output": "Provider usage.output_tokens, already including reasoning; do not add reasoning twice.",
                "sampling_note": "The existing five saved samples per family; one response each. Overall mean weights families equally."}
    save(output_dir / "run.json", settings)
    print(f"Run directory: {output_dir}", flush=True)

    def run(task):
        name = f"{task['family']}-{task['sample']}"
        save(output_dir / f"{name}.request.json", task)
        result = {k: v for k, v in task.items() if k != "request"}
        result["started_at"] = datetime.now(timezone.utc).isoformat()
        save(output_dir / f"{name}.started.json", result)
        start = time.monotonic()
        try:
            timeout = httpx.Timeout(1800, connect=30)
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                with client.stream("POST", "https://api.openai.com/v1/responses",
                                   headers={"Authorization": f"Bearer {key}"}, json=task["request"]) as response:
                    result["http_status"] = response.status_code
                    result["request_id"] = response.headers.get("x-request-id")
                    if response.status_code != 200:
                        result.update(status="http_error", error=response.read().decode(errors="replace").replace(key, "[REDACTED]"))
                    else:
                        final = None
                        for line in response.iter_lines():
                            if not line.startswith("data:"):
                                continue
                            payload = line[5:].strip()
                            if payload == "[DONE]":
                                continue
                            event = json.loads(payload)
                            if event.get("type") == "response.created":
                                result["response_id"] = event["response"]["id"]
                                save(output_dir / f"{name}.started.json", result)
                            if event.get("type") in {"response.completed", "response.incomplete", "response.failed"}:
                                final = event["response"]
                            if event.get("type") == "error":
                                result["stream_error"] = event
                        if final is None:
                            result["status"] = "missing_terminal_event"
                        else:
                            save(output_dir / f"{name}.response.json", final)
                            result.update(response_id=final["id"], status=final["status"],
                                          model=final["model"], service_tier=final.get("service_tier"),
                                          reasoning=final.get("reasoning"),
                                          effective_max_output_tokens=final.get("max_output_tokens"),
                                          incomplete_details=final.get("incomplete_details"), usage=final.get("usage"))
                            usage = final.get("usage")
                            if usage:
                                cached = usage.get("input_tokens_details", {}).get("cached_tokens", 0)
                                result["usage_based_cost_usd"] = ((usage["input_tokens"] - cached) * 10 + cached + usage["output_tokens"] * 50) / 1e6
                            text = "".join(block.get("text", "") for item in final.get("output", [])
                                           if item.get("type") == "message" for block in item.get("content", [])
                                           if block.get("type") == "output_text")
                            (output_dir / f"{name}.output.txt").write_text(text)
        except Exception as exc:
            result.update(status="transport_error", error_type=type(exc).__name__, error=str(exc).replace(key, "[REDACTED]"))
        result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        save(output_dir / f"{name}.result.json", result)
        print(f"{name}: {result['status']}, output_tokens={(result.get('usage') or {}).get('output_tokens', 'unknown')}", flush=True)
        return result

    # The first real sample checks access and parameters without an extra paid probe.
    records = [run(tasks[0])]
    if records[0]["status"] == "completed":
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(run, task) for task in tasks[1:]]
            for future in as_completed(futures):
                records.append(future.result())
                save(output_dir / "results.json", sorted(records, key=lambda r: (r["family"], r["sample"])))
    records.sort(key=lambda r: (r["family"], r["sample"]))
    save(output_dir / "results.json", records)
    summary = {**settings, "finished_at": datetime.now(timezone.utc).isoformat(),
               "overall": summarize(records),
               "by_task": {family: summarize([r for r in records if r["family"] == family])
                           for family in manifest["datasets"]}}
    save(output_dir / "summary.json", summary)
    print(json.dumps({"summary_path": str(output_dir / "summary.json"), "overall": summary["overall"],
                      "by_task": summary["by_task"]}, indent=2), flush=True)
    if len(records) != 20 or any(r["status"] != "completed" for r in records):
        raise SystemExit("Calibration incomplete; inspect saved receipts before retrying any request.")


if __name__ == "__main__":
    main()
