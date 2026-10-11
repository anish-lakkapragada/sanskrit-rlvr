#!/usr/bin/env python3
"""Resumable, offline vLLM evaluation of the SFT and GRPO-r3 checkpoints."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io as string_io
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import abc_astra_eval as grade

PROTOCOL = {"samples_per_task": 4, "max_new_tokens": 4096, "max_model_len": 8192,
            "temperature": 0.9, "top_p": 1.0, "top_k": -1, "enable_thinking": False,
            "master_seed": 42, "dtype": "bfloat16", "tensor_parallel_size": 1,
            "tools": [], "generation_config": "vllm", "grading": "abc_astra_eval.grade unchanged"}
LABELS = {"sft-base": "Qwen3-4B SFT, 20M tokens, 67% Samayik",
          "grpo-r3": "GRPO-r3 final, step 731, on the SFT checkpoint"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def seed_for(task_id):
    return (int.from_bytes(hashlib.sha256(task_id.encode()).digest()[:4], "big") + PROTOCOL["master_seed"]) % (2**31)


def prepare(out):
    manifest_path = out / "manifest.json"
    if manifest_path.exists():
        return verify(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"created_at": grade.io.now(), "protocol": PROTOCOL, "models": LABELS,
                "tasks_per_model": 1200, "trials_per_model": 4800, "total_trials": 9600,
                "source_sha256": {}, "code_sha256": {}, "adapter_sha256": {},
                "benchmark_caveat": "Original A/B/C prompts and keys are preserved for comparison with Astra. C contains known meaning-template issues: 15 Janapada and 6 AsyaNivasa tasks. Scores measure agreement with the frozen key, not an independently corrected gold standard."}
    for family in "ABC":
        source = ROOT / "benchmarks/a-b-c" / f"VP-Bench-{family}-400.jsonl"
        target = out / "datasets" / source.name
        grade.io.atomic_bytes(target, source.read_bytes())
        manifest["source_sha256"][str(target.relative_to(out))] = digest(target)
    for rel in ["misc/abc_local_eval.py", "misc/abc_astra_eval.py", "misc/oai_batch_eval.py", "finetune/prompts.py"]:
        manifest["code_sha256"][rel] = digest(ROOT / rel)
    for label, directory in [("sft-base", "runs-final/sft-qwen3-4b-tb20m-samayik67/adapter"),
                             ("grpo-r3", "runs-final/grpo-r3-final/adapter")]:
        manifest["adapter_sha256"][label] = {p.name: digest(p) for p in (ROOT / directory).iterdir()
                                             if p.name in {"adapter_model.safetensors", "adapter_config.json"}}
    grade.io.atomic_json(manifest_path, manifest)
    summarize(out)
    return manifest


def verify(out):
    manifest = grade.io.read_json(out / "manifest.json")
    if manifest["protocol"] != PROTOCOL:
        raise ValueError("Generation protocol changed")
    for rel, expected in manifest["source_sha256"].items():
        if digest(out / rel) != expected:
            raise ValueError(f"Dataset changed: {rel}")
    for rel, expected in manifest["code_sha256"].items():
        if digest(ROOT / rel) != expected:
            raise ValueError(f"Frozen evaluation code changed: {rel}")
    return manifest


def tasks_for(out):
    tasks = [t for family in "ABC" for t in grade.read_jsonl(out / "datasets" / f"VP-Bench-{family}-400.jsonl")]
    if len(tasks) != 1200 or len({t["id"] for t in tasks}) != 1200:
        raise ValueError("Expected exactly 1,200 unique tasks")
    return tasks


def make_record(task, label, rendered, outputs, prompt_tokens):
    if len(outputs) != 4:
        raise ValueError("Expected four independent sampled outputs")
    trials = []
    for trial, output in enumerate(outputs, 1):
        trials.append({"task_id": task["id"], "family": task["family"], "trial": trial,
                       "model": label, "status": "completed", "output_text": output["text"],
                       "output_tokens": output["tokens"], "finish_reason": output["finish_reason"],
                       "stop_reason": output.get("stop_reason"), "truncated": output["finish_reason"] == "length",
                       **grade.grade(task, output["text"])})
    return {"task_id": task["id"], "family": task["family"], "model": label,
            "prompt": task["prompt"], "rendered_prompt": rendered, "prompt_tokens": prompt_tokens,
            "seed": seed_for(task["id"]), "protocol": PROTOCOL, "trials": trials, "saved_at": grade.io.now()}


def saved_records(out, label, tasks):
    expected = {t["id"]: t for t in tasks}
    records = {}
    for path in sorted((out / label / "samples").glob("*.json")):
        record = grade.io.read_json(path)
        tid = record["task_id"]
        if tid not in expected or tid in records or record["model"] != label or record["protocol"] != PROTOCOL:
            raise ValueError(f"Unexpected saved record: {path}")
        if record["prompt"] != expected[tid]["prompt"] or [r["trial"] for r in record["trials"]] != [1, 2, 3, 4]:
            raise ValueError(f"Saved trial identity mismatch: {path}")
        for row in record["trials"]:
            if row["is_correct"] != grade.grade(expected[tid], row["output_text"])["is_correct"]:
                raise ValueError(f"Saved grade mismatch: {path}")
        records[tid] = record
    return records


def summarize(out):
    manifest = grade.io.read_json(out / "manifest.json")
    tasks = tasks_for(out)
    summary = {"updated_at": grade.io.now(), "protocol": PROTOCOL,
               "benchmark_caveat": manifest["benchmark_caveat"], "models": {}}
    csv_rows = []
    for label in LABELS:
        records = saved_records(out, label, tasks)
        rows = [row for task in tasks if task["id"] in records for row in records[task["id"]]["trials"]]
        groups = {family: grade.metrics([t for t in tasks if t["family"] == family],
                                      [r for r in rows if r["family"] == family]) for family in "ABC"}
        groups["overall"] = grade.metrics(tasks, rows)
        summary["models"][label] = {"description": LABELS[label], "completed_tasks": len(records),
                                    "completed_trials": len(rows), "complete": len(records) == 1200,
                                    "output_tokens": sum(r["output_tokens"] for r in rows), "scores": groups}
        for family, score in groups.items():
            csv_rows.append({"model": label, "category": family, "tasks": score["tasks"],
                             "completed_trials": score["collected_trials"], "pass_at_1": score["mean_pass_at_1"],
                             "pass_at_4": score["pass_at_4"], "solved_at_4": score["tasks_solved_at_4"],
                             "truncated_trials": score["truncated_trials"]})
        if records:
            grade.write_jsonl(out / label / "outputs.jsonl", [dict(r, prompt=records[r["task_id"]]["prompt"]) for r in rows])
            per_task = []
            for task in tasks:
                if task["id"] not in records:
                    continue
                trials = records[task["id"]]["trials"]
                c = sum(r["is_correct"] for r in trials)
                per_task.append({"task_id": task["id"], "family": task["family"], "correct_trials": c,
                                 "pass_at_1": c / 4, "pass_at_4": int(c > 0),
                                 "trial_correct": [r["is_correct"] for r in trials],
                                 "output_tokens": [r["output_tokens"] for r in trials],
                                 "truncated_trials": sum(r["truncated"] for r in trials)})
            grade.write_jsonl(out / label / "per-task.jsonl", per_task)
    summary["complete"] = all(m["complete"] for m in summary["models"].values())
    grade.io.atomic_json(out / "summary.json", summary)
    stream = string_io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]))
    writer.writeheader()
    writer.writerows(csv_rows)
    grade.io.atomic_bytes(out / "summary.csv", stream.getvalue().encode())
    return summary


def generate(out, label, model, batch_tasks):
    verify(out)
    import torch
    import vllm
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    tasks = tasks_for(out)
    records = saved_records(out, label, tasks)
    todo = [t for t in tasks if t["id"] not in records]
    if not todo:
        summarize(out)
        return
    directory = out / label
    directory.mkdir(parents=True, exist_ok=True)
    grade.io.atomic_json(directory / "runtime.json", {"started_at": grade.io.now(), "model_path": str(model),
        "torch": torch.__version__, "vllm": vllm.__version__, "gpu": torch.cuda.get_device_name(0),
        "protocol": PROTOCOL, "batch_tasks": batch_tasks, "status": "loading_model"})
    tokenizer = AutoTokenizer.from_pretrained(str(model), trust_remote_code=False)
    llm = LLM(model=str(model), dtype="bfloat16", max_model_len=8192, gpu_memory_utilization=0.90,
              tensor_parallel_size=1, trust_remote_code=False, enforce_eager=True,
              generation_config="vllm", max_num_seqs=64, max_num_batched_tokens=8192, seed=42)
    started = time.monotonic()
    completed = len(records)
    for offset in range(0, len(todo), batch_tasks):
        batch = todo[offset:offset + batch_tasks]
        rendered = [tokenizer.apply_chat_template([{"role": "user", "content": t["prompt"]}],
                    tokenize=False, add_generation_prompt=True, enable_thinking=False) for t in batch]
        for task, prompt in zip(batch, rendered):
            if len(tokenizer.encode(prompt, add_special_tokens=False)) + PROTOCOL["max_new_tokens"] > 8192:
                raise ValueError(f"Prompt plus generation budget exceeds context: {task['id']}")
        params = [SamplingParams(n=4, temperature=0.9, top_p=1.0, top_k=-1, max_tokens=4096,
                                 seed=seed_for(task["id"])) for task in batch]
        results = llm.generate(rendered, params, use_tqdm=False)
        if len(results) != len(batch):
            raise ValueError("Missing generation results")
        for task, prompt, result in zip(batch, rendered, results):
            outputs = [{"text": r.text, "tokens": len(r.token_ids), "finish_reason": r.finish_reason,
                        "stop_reason": r.stop_reason} for r in sorted(result.outputs, key=lambda r: r.index)]
            record = make_record(task, label, prompt, outputs, len(result.prompt_token_ids))
            target = directory / "samples" / f"{task['id']}.json"
            if target.exists():
                raise ValueError("Refusing to overwrite a saved task")
            grade.io.atomic_json(target, record)
        completed += len(batch)
        progress = {"updated_at": grade.io.now(), "model": label, "completed_tasks": completed,
                    "total_tasks": len(tasks), "completed_trials": completed * 4,
                    "elapsed_generation_seconds": round(time.monotonic() - started, 1)}
        grade.io.atomic_json(directory / "progress.json", progress)
        print(json.dumps(progress), flush=True)
        if completed % 64 == 0 or completed == len(tasks):
            summarize(out)
    grade.io.atomic_json(directory / "done.json", {"completed_at": grade.io.now(), "tasks": 1200, "trials": 4800})
    summarize(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "generate", "summarize"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", choices=tuple(LABELS))
    parser.add_argument("--model", type=Path)
    parser.add_argument("--batch-tasks", type=int, default=16)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.command == "prepare":
        prepare(out)
    elif args.command == "summarize":
        verify(out)
        print(json.dumps(summarize(out), indent=2))
    else:
        if not args.label or not args.model:
            parser.error("generate requires --label and --model")
        with grade.io.lock(out / args.label):
            generate(out, args.label, args.model, args.batch_tasks)


if __name__ == "__main__":
    main()
