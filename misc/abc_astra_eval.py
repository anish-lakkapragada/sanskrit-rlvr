#!/usr/bin/env python3
"""Four independent, tool-free Astra xHigh trials for each frozen A/B/C task.

prepare is offline; submit creates three remote batches; watch retrieves and
grades them. Re-running submit never repeats an attempted batch creation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io
from vidyut.lipi import Scheme, transliterate

MODEL = "gpt-6-astra"
TRIALS = 4
MAX_OUTPUT = 65536
TERMINAL = {"completed", "failed", "expired", "cancelled"}
FIELDS = {"root", "lakara", "person", "number", "pada"}
LAKARAS = {"Lat", "Lit", "Lut", "Lrt", "Lot", "Lan", "VidhiLin", "AshirLin", "Lun", "Lrn"}


def norm(value):
    return unicodedata.normalize("NFC", value.strip())


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_jsonl(path, rows):
    io.atomic_bytes(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode())


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def root_spellings(analysis):
    variants = {norm(analysis["root"]), norm(analysis["root_iast"])}
    for alias in analysis["root_aliases_slp1"]:
        for scheme in (Scheme.Slp1, Scheme.Iast, Scheme.Devanagari):
            variants.add(norm(transliterate(alias, Scheme.Slp1, scheme)))
    return variants


def grade(task, text):
    """Exact output format; NFC and surrounding whitespace only; no LLM judge."""
    fail = lambda reason, answer=None: {"is_correct": False, "reason": reason, "answer": answer}
    if task["family"] != "A":
        match = re.fullmatch(r"\s*<answer>([^<>]+)</answer>\s*", text, flags=re.DOTALL)
        if not match:
            return fail("invalid_answer_format")
        answer = norm(match[1])
        accepted = {norm(v) for key in ("accepted_devanagari", "accepted_iast", "accepted_slp1") for v in task[key]}
        correct = answer in accepted
        return {"is_correct": correct, "reason": "correct" if correct else "wrong_form", "answer": answer}
    try:
        predicted = json.loads(text, object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        return fail("invalid_json")
    if not isinstance(predicted, list) or not predicted:
        return fail("invalid_analysis_array", predicted)
    for item in predicted:
        if (not isinstance(item, dict) or set(item) != FIELDS
                or not isinstance(item["root"], str) or not item["root"].strip()
                or not isinstance(item["lakara"], str) or item["lakara"] not in LAKARAS
                or type(item["person"]) is not int or item["person"] not in (1, 2, 3)
                or item["number"] not in ("singular", "dual", "plural")
                or item["pada"] not in ("P", "A")):
            return fail("invalid_analysis_schema", predicted)
    # The prompt asks for distinct analyses. Do not let duplicated predictions
    # cover multiple expected roots, even where accepted alias spellings overlap.
    signatures = [(norm(x["root"]), x["lakara"], x["person"], x["number"], x["pada"]) for x in predicted]
    if len(set(signatures)) != len(signatures):
        return fail("duplicate_analysis", predicted)
    gold = task["accepted_analyses"]
    if len(predicted) != len(gold):
        return fail("wrong_analysis_count", predicted)
    spellings = [root_spellings(g) for g in gold]
    edges = [[i for i, g in enumerate(gold)
              if norm(p["root"]) in spellings[i]
              and all(p[k] == g[k] for k in ("lakara", "person", "number", "pada"))]
             for p in predicted]
    matched = {}

    def match_one(index, seen):
        for target in edges[index]:
            if target in seen:
                continue
            seen.add(target)
            if target not in matched or match_one(matched[target], seen):
                matched[target] = index
                return True
        return False

    correct = all(match_one(i, set()) for i in range(len(predicted)))
    return {"is_correct": correct, "reason": "correct" if correct else "analysis_mismatch", "answer": predicted}


def request(task, trial):
    return {"custom_id": f"{task['id']}-t{trial}", "method": "POST", "url": "/v1/responses", "body": {
        "model": MODEL, "input": [{"role": "user", "content": task["prompt"]}],
        "reasoning": {"mode": "standard", "effort": "xhigh"},
        "max_output_tokens": MAX_OUTPUT, "tools": [], "tool_choice": "none",
        "store": False, "stream": False, "truncation": "disabled"}}


def save(out, state):
    state["updated_at"] = io.now()
    io.atomic_json(out / "state.json", state)


def verify(out, state):
    if state["runner_sha256"] != io.sha256(Path(__file__)):
        raise ValueError("Runner changed since preparation; preserve the frozen evaluation protocol")
    for cfg in state["families"].values():
        for field in ("dataset", "input"):
            if io.sha256(out / cfg[f"{field}_path"]) != cfg[f"{field}_sha256"]:
                raise ValueError(f"Frozen {field} changed")


def prepare(out, dataset):
    if (out / "state.json").exists():
        state = io.read_json(out / "state.json")
        verify(out, state)
        return state
    state = {"run_id": "abc-astra-xhigh-" + uuid4().hex[:12], "created_at": io.now(),
             "model": MODEL, "effort": "xhigh", "samples_per_task": TRIALS,
             "task_count": 1200, "request_count": 4800, "max_output_tokens": MAX_OUTPUT,
             "tools": [], "tool_choice": "none", "transport": "batch", "completion_window": "24h",
             "sdk_max_retries": 0, "runner_sha256": io.sha256(Path(__file__)),
             "grading": "Strict output format. A: complete unordered one-to-one analysis match with root aliases; B/C: any accepted form. NFC and outer whitespace only. Three scripts; no Harvard-Kyoto conversion. API failures remain unknown, with pass@4 bounds.",
             "families": {}}
    all_ids = set()
    for family in "ABC":
        source = dataset / f"VP-Bench-{family}-400.jsonl"
        tasks = read_jsonl(source)
        if len(tasks) != 400 or any(t["family"] != family for t in tasks):
            raise ValueError("Expected exactly 400 tasks per family")
        for task in tasks:
            if task["id"] in all_ids or "Harvard-Kyoto" in task["prompt"]:
                raise ValueError("Duplicate ID or stale prompt")
            all_ids.add(task["id"])
            example = json.dumps(task["answer"], ensure_ascii=False) if family == "A" else task["answer"]
            if not grade(task, example)["is_correct"]:
                raise ValueError(f"Gold answer fails grading: {task['id']}")
        snapshot = out / "datasets" / source.name
        io.atomic_bytes(snapshot, source.read_bytes())
        inp = out / family / "input.jsonl"
        write_jsonl(inp, [request(task, trial) for task in tasks for trial in range(1, TRIALS + 1)])
        state["families"][family] = {"dataset_path": str(snapshot.relative_to(out)), "dataset_sha256": io.sha256(snapshot),
            "input_path": str(inp.relative_to(out)), "input_sha256": io.sha256(inp),
            "tasks": 400, "requests": 1600, "input_file_id": None, "batch_id": None,
            "upload_attempted_at": None, "submit_attempted_at": None, "collected_at": None, "status": "prepared"}
    save(out, state)
    summarize(out, state)
    return state


def submit(client, out, state):
    verify(out, state)
    for family, cfg in state["families"].items():
        if cfg["batch_id"] or cfg["submit_attempted_at"]:
            continue
        try:
            if not cfg["input_file_id"]:
                if cfg["upload_attempted_at"]:
                    continue
                cfg.update(upload_attempted_at=io.now(), status="uploading")
                save(out, state)
                with (out / cfg["input_path"]).open("rb") as handle:
                    raw = client.files.with_raw_response.create(file=handle, purpose="batch")
                uploaded = io.capture_json(out / family / "upload.http.json", raw)
                cfg.update(input_file_id=uploaded["id"], status="uploaded")
                save(out, state)
            cfg.update(submit_attempted_at=io.now(), status="submission_unknown")
            save(out, state)
            raw = client.batches.with_raw_response.create(input_file_id=cfg["input_file_id"],
                endpoint="/v1/responses", completion_window="24h",
                metadata={"run_id": state["run_id"], "family": family, "model": MODEL,
                          "effort": "xhigh", "task_count": "400", "samples_per_task": "4",
                          "dataset_sha256": cfg["dataset_sha256"], "tools": "none"})
            batch = io.capture_json(out / family / "create.http.json", raw)
            cfg.update(batch_id=batch["id"], batch=batch, status=batch["status"])
            save(out, state)
            print(f"{family}: submitted {cfg['requests']} requests as {batch['id']} ({batch['status']})", flush=True)
        except Exception as exc:
            cfg["submission_error"] = io.error_details(exc, client)
            save(out, state)
            raise RuntimeError(f"{family}: {type(exc).__name__}; saved details; no automatic resubmission") from None
    summarize(out, state)


def recover(client, out, state, family, cfg):
    if cfg["batch_id"] or not cfg["submit_attempted_at"]:
        return
    receipt = out / family / "create.http.json"
    if receipt.exists():
        matches = [io.read_json(receipt)["body"]]
    else:
        matches = [b.model_dump(mode="json") for b in client.batches.list(limit=100)
                   if b.input_file_id == cfg["input_file_id"]
                   and (b.metadata or {}).get("run_id") == state["run_id"]]
    if len(matches) > 1:
        raise ValueError("Multiple matching batches; cannot reconcile automatically")
    if matches:
        batch = matches[0]
        cfg.update(batch_id=batch["id"], batch=batch, status=batch["status"])
        save(out, state)


def grade_result(task, trial, result):
    row = {"task_id": task["id"], "family": task["family"], "trial": trial,
           "custom_id": f"{task['id']}-t{trial}", "is_correct": None, "status": "missing_result"}
    if result is None:
        return row
    response = result.get("response") or {}
    body = response.get("body") or {}
    row.update(response_id=body.get("id"), request_id=response.get("request_id"), usage=body.get("usage"),
               response_status=body.get("status"), error=result.get("error") or body.get("error"))
    if response.get("status_code") != 200 or row["error"] or body.get("status") not in {"completed", "incomplete"}:
        row["status"] = "api_error"
        return row
    output = body.get("output") or []
    if body.get("model") != MODEL or any(x.get("type", "").endswith("_call") for x in output):
        row.update(status="protocol_error", error="Unexpected model or tool call")
        return row
    text = "\n".join(c.get("text", "") for item in output if item.get("type") == "message"
                     for c in item.get("content", []) if c.get("type") == "output_text")
    row.update(output_text=text, truncated=(body.get("incomplete_details") or {}).get("reason") == "max_output_tokens",
               status=body["status"], **grade(task, text))
    return row


def collect(client, out, state):
    verify(out, state)
    for family, cfg in state["families"].items():
        if cfg["collected_at"]:
            continue
        try:
            recover(client, out, state, family, cfg)
            if not cfg["batch_id"]:
                continue
            raw = client.batches.with_raw_response.retrieve(cfg["batch_id"])
            batch = io.capture_json(out / family / "status.http.json", raw)
            cfg.update(batch=batch, status=batch["status"])
            cfg.pop("collection_error", None)
            save(out, state)
            if batch["status"] not in TERMINAL:
                continue
            tasks = read_jsonl(out / cfg["dataset_path"])
            expected = {f"{t['id']}-t{trial}" for t in tasks for trial in range(1, TRIALS + 1)}
            results = {}
            for key in ("output_file_id", "error_file_id"):
                file_id = batch.get(key)
                if not file_id:
                    continue
                path = out / family / f"{file_id}.jsonl"
                if not path.exists():
                    raw = client.files.with_raw_response.content(file_id)
                    content = raw.http_response.content
                    for line in content.splitlines():
                        if line.strip():
                            json.loads(line)
                    io.atomic_bytes(path, content)
                for result in read_jsonl(path):
                    cid = result.get("custom_id")
                    if cid not in expected or cid in results:
                        raise ValueError("Unexpected or duplicate result ID")
                    results[cid] = result
            rows = [grade_result(t, trial, results.get(f"{t['id']}-t{trial}"))
                    for t in tasks for trial in range(1, TRIALS + 1)]
            ids = [r["response_id"] for r in rows if r.get("response_id")]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate generation response IDs")
            write_jsonl(out / family / "results.jsonl", rows)
            cfg["collected_at"] = io.now()
            save(out, state)
        except Exception as exc:
            cfg["collection_error"] = io.error_details(exc, client)
            save(out, state)
            print(f"{family}: collection {type(exc).__name__}; next poll will retry reads only", flush=True)
    return summarize(out, state)


def metrics(tasks, rows):
    by_id = {t["id"]: [] for t in tasks}
    for row in rows:
        by_id[row["task_id"]].append(row)
    solved = unresolved = four_scored = 0
    for attempts in by_id.values():
        success = any(r["is_correct"] is True for r in attempts)
        complete = len(attempts) == TRIALS and all(r["is_correct"] is not None for r in attempts)
        solved += success
        four_scored += complete
        unresolved += not success and not complete
    n = len(tasks)
    usage = Counter()
    for row in rows:
        u = row.get("usage") or {}
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            usage[field] += u.get(field, 0)
        usage["cached_input_tokens"] += (u.get("input_tokens_details") or {}).get("cached_tokens", 0)
        usage["reasoning_tokens"] += (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
    return {"tasks": n, "expected_trials": n * TRIALS, "collected_trials": len(rows),
            "tasks_with_four_scored_trials": four_scored, "tasks_solved_at_4": solved,
            "tasks_with_unresolved_pass_at_4": unresolved,
            "pass_at_4": solved / n if unresolved == 0 else None,
            "pass_at_4_lower_bound": solved / n, "pass_at_4_upper_bound": (solved + unresolved) / n,
            "mean_pass_at_1": sum(r["is_correct"] is True for r in rows) / (n * TRIALS) if four_scored == n else None,
            "statuses": dict(Counter(r["status"] for r in rows)),
            "truncated_trials": sum(r.get("truncated", False) for r in rows), "usage": dict(usage)}


def summarize(out, state):
    groups, all_tasks, all_rows = {}, [], []
    for family, cfg in state["families"].items():
        tasks = read_jsonl(out / cfg["dataset_path"])
        result_path = out / family / "results.jsonl"
        rows = read_jsonl(result_path) if result_path.exists() else []
        groups[family] = {"batch_id": cfg["batch_id"], "batch_status": cfg["status"],
                         "request_counts": (cfg.get("batch") or {}).get("request_counts"), **metrics(tasks, rows)}
        all_tasks.extend(tasks)
        all_rows.extend(rows)
    summary = {"run_id": state["run_id"], "updated_at": io.now(), "model": MODEL, "effort": "xhigh",
               "samples_per_task": TRIALS, "all_batches_collected": all(bool(c["collected_at"]) for c in state["families"].values()),
               "families": groups, "overall": metrics(all_tasks, all_rows)}
    io.atomic_json(out / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "submit", "collect", "watch", "status"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "benchmarks/a-b-c")
    parser.add_argument("--poll-seconds", type=int, default=60)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.command == "prepare":
        with io.lock(out):
            state = prepare(out, args.dataset)
        print(json.dumps({"run_id": state["run_id"], "tasks": 1200, "requests": 4800}))
        return
    if args.command == "status":
        print((out / "summary.json").read_text())
        return
    with io.api_client() as client:
        while True:
            with io.lock(out):
                state = io.read_json(out / "state.json")
                if args.command == "submit":
                    submit(client, out, state)
                    return
                summary = collect(client, out, state)
                print(io.now(), json.dumps({f: {"status": g["batch_status"], "counts": g["request_counts"]}
                                            for f, g in summary["families"].items()}), flush=True)
            if args.command != "watch" or summary["all_batches_collected"]:
                return
            time.sleep(max(5, min(args.poll_seconds, 60)))


if __name__ == "__main__":
    main()
