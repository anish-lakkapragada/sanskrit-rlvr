"""Build the morphology buckets, run resumable GRPO evaluations, and summarize.

Run from the repository root. Raw generations belong under ignored runs/;
the task lists and summary under benchmarks/ are small, reviewable artifacts.
"""

import argparse
import hashlib
import json
import math
import os
import random
import time
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCORES = {
    "lakara": {"Lat": 1, "Lan": 2, "Lot": 2, "VidhiLin": 2, "Lit": 3,
               "Lrt": 3, "Lut": 4, "Lun": 4, "AshirLin": 5, "Lrn": 5},
    "prayoga": {"Kartari": 1, "Karmani": 2, "Bhave": 4},
    "purusha": {"Prathama": 1, "Madhyama": 3, "Uttama": 3},
    "vacana": {"Eka": 1, "Bahu": 2, "Dvi": 4},
}
LABELS = ("easy", "medium", "hard")
KS = (1, 2, 4, 8, 16)
PROTOCOL = {"samples_per_prompt": 16, "temperature": 0.9, "top_p": 1.0,
            "max_new_tokens": 4096, "enable_thinking": False, "seed": 42,
            "dtype": "bfloat16", "prompt": "v1/vp_task_eval.txt",
            "metric": "NFC-normalized exact match of the extracted answer"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def task_score(task):
    return sum(SCORES[k][task["morphology"][k]] for k in SCORES) / 4


def bucket(task):
    value = task_score(task)
    return "easy" if value <= 2 else "medium" if value <= 3 else "hard"


def load_pool():
    tasks, origins = [], {}
    base = ROOT / "data/finetune/task-data"
    for split in ("finetune", "validation"):
        for task in json.loads((base / f"{split}.json").read_text()):
            if task["id"] in origins:
                raise ValueError(f"Duplicate task: {task['id']}")
            tasks.append(task)
            origins[task["id"]] = split
    return tasks, origins


def prepare(args):
    tasks, origins = load_pool()
    metadata = json.loads((ROOT / "data/finetune/task-data/metadata.json").read_text())
    assert all(set(v) == set(SCORES[k]) for k, v in metadata["coordinate_space"].items())
    assert len(tasks) == 6687
    for label in LABELS:
        write_json(ROOT / f"benchmarks/{label}/tasks.json", [t for t in tasks if bucket(t) == label])
    shuffled = list(tasks)
    random.Random(PROTOCOL["seed"]).shuffle(shuffled)
    for shard in range(args.shards):
        write_json(Path(args.run_dir) / f"tasks-{shard}.json", shuffled[shard::args.shards])
    manifest = {
        "scores": SCORES, "cutoffs": {"easy": "mean <= 2", "medium": "2 < mean <= 3", "hard": "mean > 3"},
        "protocol": PROTOCOL, "model": "GRPO-r3 final step 731", "shards": args.shards,
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [
            ROOT / "data/finetune/task-data/finetune.json", ROOT / "data/finetune/task-data/validation.json",
            ROOT / "prompts/v1/vp_task_eval.txt",
            ROOT / "runs-final/grpo-r3-final/adapter/adapter_model.safetensors",
            ROOT / "runs-final/sft-qwen3-4b-tb20m-samayik67/adapter/adapter_model.safetensors"]},
        "counts": {label: dict(Counter(origins[t["id"]] for t in tasks if bucket(t) == label)) for label in LABELS},
        "tasks": [{"id": t["id"], "source_split": origins[t["id"]], "mean_score": task_score(t),
                   "bucket": bucket(t)} for t in tasks],
    }
    write_json(ROOT / "benchmarks/manifest.json", manifest)
    write_json(Path(args.run_dir) / "manifest.json", manifest)
    print(json.dumps({"total": len(tasks), "counts": manifest["counts"], "hashes": manifest["source_sha256"]}, indent=2))


def read_jsonl(path, repair=False):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("rb+") as f:
        while True:
            start = f.tell()
            line = f.readline()
            if not line:
                break
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                if repair and not f.read(1):
                    f.seek(start)
                    f.truncate()
                    break
                raise
            rows.append(row)
    return rows


def generate(args):
    from finetune.prompts import extract_answer, render_vp_task
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    import torch
    import vllm

    tasks = json.loads(Path(args.tasks).read_text())
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = {t["id"]: t for t in tasks}
    saved = read_jsonl(target, repair=True)
    done = set()
    for row in saved:
        tid = row["input_task"]["id"]
        assert tid not in done and row["input_task"] == expected[tid]
        assert len(row["outputs"]) == len(row["exact_answers"]) == 16
        assert row["protocol"] == PROTOCOL
        done.add(tid)
    todo = [t for t in tasks if t["id"] not in done]
    provenance = {"protocol": PROTOCOL, "model": args.model, "task_file_sha256": digest(args.tasks),
                  "torch": torch.__version__, "vllm": vllm.__version__, "gpu": torch.cuda.get_device_name(0)}
    write_json(target.with_suffix(".provenance.json"), provenance)
    if not todo:
        write_json(target.with_suffix(".done.json"), {"tasks": len(tasks), "sha256": digest(target)})
        return
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", "FLASH_ATTN")
    os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    llm = LLM(model=args.model, dtype="bfloat16", max_model_len=8192,
              gpu_memory_utilization=0.90, tensor_parallel_size=1, trust_remote_code=False)
    params = SamplingParams(n=16, temperature=0.9, top_p=1.0, max_tokens=4096, seed=42)
    norm = lambda s: unicodedata.normalize("NFC", s).strip()
    start = time.monotonic()
    completed_now = 0
    total_tokens = 0
    with target.open("a", buffering=1) as f:
        for offset in range(0, len(todo), args.batch_tasks):
            batch = todo[offset:offset + args.batch_tasks]
            prompts = [render_vp_task(t, PROTOCOL["prompt"]) for t in batch]
            rendered = [tokenizer.apply_chat_template([{"role": "user", "content": p}],
                        tokenize=False, add_generation_prompt=True, enable_thinking=False) for p in prompts]
            outputs = llm.generate(rendered, params, use_tqdm=True)
            assert len(outputs) == len(batch)
            for task, prompt, result in zip(batch, prompts, outputs):
                assert len(result.outputs) == 16
                texts = [o.text for o in result.outputs]
                answers = [extract_answer(o) for o in texts]
                gold = {norm(g) for g in task["gold_devanagari"]}
                correct = [a is not None and norm(a) in gold for a in answers]
                tokens = [len(o.token_ids) for o in result.outputs]
                record = {"input_task": task, "prompt": prompt, "outputs": texts,
                          "output_devanagari": answers, "exact_answers": correct,
                          "output_tokens": tokens, "finish_reasons": [o.finish_reason for o in result.outputs],
                          "protocol": PROTOCOL}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_tokens += sum(tokens)
            f.flush()
            os.fsync(f.fileno())
            completed_now += len(batch)
            progress = {"completed": len(done) + completed_now, "total": len(tasks),
                        "elapsed_s": round(time.monotonic() - start, 1), "output_tokens": total_tokens,
                        "output_tokens_per_s": round(total_tokens / (time.monotonic() - start), 1)}
            write_json(target.with_suffix(".progress.json"), progress)
            print(json.dumps(progress), flush=True)
    write_json(target.with_suffix(".done.json"), {"tasks": len(tasks), "sha256": digest(target), **progress})


def pass_k(n, c, k):
    return 1.0 if n - c < k else 1.0 - math.comb(n - c, k) / math.comb(n, k)


def aggregate(tasks, rows, origins, resamples=20000):
    # Dictionary entries with the same citation and conjugation class can
    # share forms, even when they have different IDs or meanings.
    root_key = lambda t: (t["dhatu"]["aupadeshika"], t["dhatu"]["gana"])
    roots = sorted({root_key(t) for t in tasks})
    ridx = {r: i for i, r in enumerate(roots)}
    counts = np.zeros((len(roots), 3), dtype=int)
    sums = np.zeros((len(roots), 3, len(KS)))
    successes = np.zeros(3, dtype=int)
    for t in tasks:
        row = rows[t["id"]]
        j = LABELS.index(bucket(t))
        r = ridx[root_key(t)]
        n = len(row["exact_answers"])
        c = sum(row["exact_answers"])
        counts[r, j] += 1
        successes[j] += c
        sums[r, j] += [pass_k(n, c, k) for k in KS]
    ns = counts.sum(axis=0)
    estimates = sums.sum(axis=0) / ns[:, None]
    # Resample whole dhatus jointly across buckets, preserving cross-bucket covariance.
    rng = np.random.default_rng(42)
    boots = []
    for offset in range(0, resamples, 250):
        w = rng.multinomial(len(roots), np.full(len(roots), 1 / len(roots)),
                            size=min(250, resamples - offset))
        denominator = w @ counts
        assert (denominator > 0).all()
        boots.append((w @ sums.reshape(len(roots), -1)).reshape(-1, 3, len(KS)) / denominator[:, :, None])
    boot = np.concatenate(boots)
    result = {"n_tasks": len(tasks), "n_dhatus": len({t["dhatu"]["code"] for t in tasks}),
              "n_bootstrap_clusters": len(roots), "segments": {}, "differences": {}}
    for j, name in enumerate(LABELS):
        result["segments"][name] = {
            "tasks": int(ns[j]),
            "dhatus": len({t["dhatu"]["code"] for t in tasks if bucket(t) == name}),
            "bootstrap_clusters": int((counts[:, j] > 0).sum()),
            "completions": int(ns[j] * 16), "successful_completions": int(successes[j]),
            "pass_at_k": {str(k): {"estimate": float(estimates[j, q]),
                                   "se": float(boot[:, j, q].std(ddof=1)),
                                   "ci95": np.quantile(boot[:, j, q], [.025, .975]).tolist()}
                          for q, k in enumerate(KS)}}
    for a, b in ((0, 1), (1, 2), (0, 2)):
        delta = boot[:, a, 0] - boot[:, b, 0]
        result["differences"][f"{LABELS[a]}-{LABELS[b]}"] = {
            "estimate": float(estimates[a, 0] - estimates[b, 0]), "se": float(delta.std(ddof=1)),
            "ci95": np.quantile(delta, [.025, .975]).tolist()}
    return result


def report(args):
    from finetune.prompts import extract_answer, render_vp_task
    tasks, origins = load_pool()
    expected = {t["id"]: t for t in tasks}
    run_dir = Path(args.run_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["protocol"] == PROTOCOL
    assert manifest["scores"] == SCORES
    for name, expected_hash in manifest["source_sha256"].items():
        assert digest(ROOT / name) == expected_hash, f"Source changed: {name}"
    rows = {}
    source_files = []
    worker_provenance = []
    norm = lambda s: unicodedata.normalize("NFC", s).strip()
    for path in sorted(run_dir.glob("samples-*.jsonl")):
        file_hash = digest(path)
        done = json.loads(path.with_suffix(".done.json").read_text())
        provenance = json.loads(path.with_suffix(".provenance.json").read_text())
        assert file_hash == done["sha256"], f"Output checksum mismatch: {path}"
        assert provenance["protocol"] == PROTOCOL
        source_files.append({"file": str(path), "sha256": file_hash, "tasks": done["tasks"]})
        worker_provenance.append(provenance)
        for row in read_jsonl(path):
            t = row["input_task"]
            assert t["id"] not in rows and t == expected[t["id"]]
            assert row["protocol"] == PROTOCOL
            assert row["prompt"] == render_vp_task(t, PROTOCOL["prompt"])
            assert len(row["outputs"]) == len(row["exact_answers"]) == 16
            answers = [extract_answer(o) for o in row["outputs"]]
            assert answers == row["output_devanagari"]
            correct = [a is not None and norm(a) in {norm(g) for g in t["gold_devanagari"]} for a in answers]
            assert correct == row["exact_answers"]
            rows[t["id"]] = row
    assert set(rows) == set(expected), f"Coverage incomplete: {len(rows)}/{len(expected)}"
    result = {"model": "GRPO-r3 final step 731", "protocol": PROTOCOL,
              "cutoffs": {"easy": "mean <= 2", "medium": "2 < mean <= 3", "hard": "mean > 3"},
              "uncertainty": {"method": "percentile bootstrap of (dhatu citation, gana) clusters", "resamples": 20000,
                              "seed": 42, "note": "Conditional on this fixed checkpoint and these fixed cutoffs; not adjusted for earlier cutoff selection."},
              "source_files": source_files, "worker_provenance": worker_provenance,
              "model_sha256": json.loads((run_dir / "model-ready.json").read_text()),
              "source_sha256": manifest["source_sha256"], "cohorts": {}}
    total_completions = sum(len(r["outputs"]) for r in rows.values())
    result["coverage"] = {
        "tasks": len(rows), "completions": total_completions,
        "missing_answers": sum(a is None for r in rows.values() for a in r["output_devanagari"]),
        "length_limited_completions": sum(x == "length" for r in rows.values() for x in r["finish_reasons"]),
        "output_tokens": sum(sum(r["output_tokens"]) for r in rows.values()),
    }
    assert len(source_files) == manifest["shards"]
    assert sum(s["tasks"] for s in source_files) == len(tasks)
    assert total_completions == len(tasks) * 16
    for name in ("all", "finetune", "validation"):
        cohort = [t for t in tasks if name == "all" or origins[t["id"]] == name]
        result["cohorts"][name] = aggregate(cohort, rows, origins)
    gaps = result["cohorts"]["all"]["differences"]
    if all(g["ci95"][0] <= 0 <= g["ci95"][1] for g in gaps.values()):
        result["finding"] = (
            "None of the three pairwise pass@1 gaps has a 95% confidence interval "
            "excluding zero. The full pool does not validate these cutoffs as "
            "clearly separated difficulty tiers."
        )
    elif all(gaps[k]["ci95"][0] > 0 for k in ("easy-medium", "medium-hard")):
        result["finding"] = "Both adjacent pass@1 gaps have 95% confidence intervals above zero on the full pool."
    else:
        result["finding"] = "The full pool does not establish three clearly separated, ordered pass@1 difficulty tiers at these cutoffs."
    out = ROOT / "benchmarks/results/grpo-r3-full.json"
    write_json(out, result)
    write_json(ROOT / "benchmarks/results/grpo-r3-per-task.json", {
        "model": result["model"], "protocol": PROTOCOL,
        "tasks": [{"id": t["id"], "source_split": origins[t["id"]],
                   "mean_score": task_score(t), "bucket": bucket(t),
                   "attempts": 16, "exact_successes": sum(rows[t["id"]]["exact_answers"])}
                  for t in tasks],
    })
    lines = ["# GRPO-r3 full morphology evaluation", "",
             result["finding"], "",
             "Final step 731; 16 fresh attempts per task; cutoffs: easy <= 2, medium (2, 3], hard > 3.",
             "95% confidence intervals use 20,000 whole-root bootstrap resamples, grouping dictionary entries that share the same citation and gana. SE is one bootstrap standard error, in percentage points. Intervals are conditional on fixed cutoffs selected using earlier validation results.",
             "The full pool includes 6,018 original-finetune tasks and 669 original-validation tasks. The pooled result is not an estimate on entirely unseen tasks.",
             "There are 2,229 dictionary entry IDs but 2,162 distinct citation/gana groups. Eleven citation/gana groups occur in both original splits, affecting 33 validation tasks.",
             f"Verified coverage: {len(rows):,} unique tasks and {total_completions:,} fresh completions, with saved output checksums, prompts, and exact-answer scoring checked.", ""]
    for cohort, data in result["cohorts"].items():
        lines += [f"## {cohort} ({data['n_tasks']} tasks)", "",
                  "| Bucket | Tasks | Pass@1 | SE (pp) | 95% CI | Pass@16 (95% CI) |", "|---|---:|---:|---:|---|---|"]
        for label in LABELS:
            d = data["segments"][label]; p = d["pass_at_k"]["1"]; q = d["pass_at_k"]["16"]
            lines.append(f"| {label} | {d['tasks']} | {p['estimate']*100:.2f}% | {p['se']*100:.2f} | [{p['ci95'][0]*100:.2f}, {p['ci95'][1]*100:.2f}] | {q['estimate']*100:.2f}% [{q['ci95'][0]*100:.2f}, {q['ci95'][1]*100:.2f}] |")
        lines += ["", "Pass@1 differences (percentage points):", ""]
        for label, d in data["differences"].items():
            lines.append(f"- {label}: {d['estimate']*100:.2f}; 95% CI [{d['ci95'][0]*100:.2f}, {d['ci95'][1]*100:.2f}]")
        lines.append("")
    lines += ["Per-task success counts: [grpo-r3-per-task.json](grpo-r3-per-task.json).", ""]
    (ROOT / "benchmarks/results/grpo-r3-full.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--run-dir", required=True)
    prep.add_argument("--shards", type=int, default=4)
    run = sub.add_parser("run")
    run.add_argument("--tasks", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--batch-tasks", type=int, default=64)
    rep = sub.add_parser("report")
    rep.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    {"prepare": prepare, "run": generate, "report": report}[args.command](args)


if __name__ == "__main__":
    main()
