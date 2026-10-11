"""Export complete creation prompts and score answers with the benchmark metric.

The legacy VP training renderer does not display sanadi, prefixes or pada.
Consumers of this export must use its messages/prompt fields directly.
No model requests or training runs are made by this module.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finetune.prompts import extract_answer
from misc import oai_batch_eval as io, vp_goal as c
from misc.vp_goal_validate import RENDERERS, validate


def exact_reward(completion, gold_devanagari):
    answer = extract_answer(completion) if isinstance(completion, str) else None
    if answer is None:
        return 0.0
    normalize = lambda s: unicodedata.normalize("NFC", s.strip())
    return float(normalize(answer) in {normalize(g) for g in gold_devanagari})


def task_reward(completion, task):
    if task.get('task_type') in {'finite_paradigm','finite_contrast','finite_bundle'}:
        from misc.vp_goal_paradigm import grade
        return float(grade(task, completion)['is_correct'])
    return exact_reward(completion, task['gold_devanagari'])


def export(tasks_path, output, split="rl_train"):
    if output.exists() or output.with_suffix(".manifest.json").exists():
        raise ValueError("Export exists; do not overwrite a versioned dataset")
    tasks = io.read_json(tasks_path)
    audit = validate(tasks, split)
    rows = []
    for task in tasks:
        prompt = RENDERERS[task.get("prompt_version", "composition-v1")](task)
        rows.append({"id": task["id"], "prompt": prompt,
            "messages": [{"role": "user", "content": prompt}],
            "gold_devanagari": task["gold_devanagari"], "gold_slp1": task["gold_slp1"],
            "root_family": task["campaign"]["root_family"], "split": split,
            "construction": task["campaign"]["construction"],
            "prompt_version": task.get("prompt_version", "composition-v1"),
            "task": task})
    # Gold/reference fields belong in the reward function, never the model input.
    io.atomic_bytes(output, ("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)).encode())
    manifest = {"created_at": io.now(), "status": "candidate_training_data" if split == "rl_train" else "unreleased_research_export",
        "n": len(rows), "split": split, "audit": audit,
        "source_tasks_sha256": io.sha256(tasks_path), "jsonl_sha256": io.sha256(output),
        "exporter_sha256": io.sha256(Path(__file__)),
        "dependency_sha256": {str(path.relative_to(ROOT)): io.sha256(path) for path in (
            ROOT / "finetune/prompts.py", ROOT / "prompts/v2/vp_task_eval.txt",
            ROOT / "misc/vp_compositional.py", ROOT / "misc/vp_finite_pada.py",
            ROOT / "misc/vp_goal_tasks.py", ROOT / "misc/vp_goal_grammar.py",
            ROOT / "misc/vp_goal_validate.py", ROOT / "misc/vp_cartesian_task.py",
            ROOT / "misc/vp_sanskrit_prompt_v1.py",
            ROOT / "data/finetune/task-data/vidyut_dhatupatha_5.tsv",
            c.HISTORY / "family-split.json")},
        "prompt_renderer_sha256": {version: io.sha256(Path(sys.modules[fn.__module__].__file__))
                                    for version, fn in RENDERERS.items() if any(r["prompt_version"] == version for r in rows)},
        "reward": "Use task_reward(completion, task): a one-form task accepts any gold variant; a paradigm requires a valid row-keyed JSON object with every requested form correct. Binary 0/1; no thinking-block requirement.",
        "model_input": "Use only messages (or prompt). Keep gold fields and task metadata in the verifier, not the input.",
        "training_integration": "The legacy root-only VP prompt renderer omits these operations. Consume the exported prompts directly; no training configuration has been changed or launched.",
        "limits": "Exact citation-plus-gana split, not an etymological lemma split. Existing checkpoints are not certified clean. This export does not certify final benchmark difficulty or every generated key."}
    io.atomic_json(output.with_suffix(".manifest.json"), manifest)
    return manifest


def score(dataset, completions):
    """Require complete, unique IDs so missing responses cannot disappear."""
    if not dataset:
        raise ValueError("Dataset cannot be empty")
    tasks = {t["id"]: t for t in dataset}
    if len(tasks) != len(dataset):
        raise ValueError("Dataset IDs must be unique")
    answers = {r["id"]: r["completion"] for r in completions}
    if len(answers) != len(completions) or set(answers) != set(tasks):
        raise ValueError("Completion IDs must cover the dataset exactly once; use empty text for no answer")
    grades = {tid: task_reward(answers[tid], task.get('task', task)) for tid, task in tasks.items()}
    return {"n": len(grades), "correct": int(sum(grades.values())),
            "accuracy": sum(grades.values()) / len(grades), "grades": grades}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    e = sub.add_parser("export")
    e.add_argument("tasks", type=Path)
    e.add_argument("output", type=Path)
    e.add_argument("--split", choices=["rl_train", "development", "test"], default="rl_train")
    s = sub.add_parser("score")
    s.add_argument("dataset", type=Path)
    s.add_argument("completions", type=Path)
    s.add_argument("output", type=Path)
    a = p.parse_args()
    if a.command == "export":
        result = export(a.tasks, a.output, a.split)
    else:
        read_jsonl = lambda path: [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        result = score(read_jsonl(a.dataset), read_jsonl(a.completions))
        io.atomic_json(a.output, result)
    print(json.dumps({k: v for k, v in result.items() if k in {"n", "split", "accuracy", "correct", "status"}}))
