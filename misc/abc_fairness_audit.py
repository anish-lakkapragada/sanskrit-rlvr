#!/usr/bin/env python3
"""Read-only rescore diagnostics for ABC; official generations/grades stay frozen."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.abc_astra_eval import grade
from finetune.prompts import extract_answer


def load_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def final_array(text):
    """One JSON array ending the response, optionally before a closing code fence.

    No schema repair, numeric/string conversion, or gold-dependent selection.
    """
    text = text.strip()
    if text.endswith("```"):
        text = text[:-3].rstrip()
    decoder, found = json.JSONDecoder(), []
    for i, character in enumerate(text):
        if character != "[":
            continue
        try:
            value, end = decoder.raw_decode(text[i:])
        except (ValueError, RecursionError):
            continue
        if isinstance(value, list) and not text[i + end:].strip():
            found.append(value)
    return json.dumps(found[0], ensure_ascii=False) if len(found) == 1 else None


def stats(rows, field="is_correct"):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["task_id"]].append(bool(row[field]))
    assert all(len(v) == 4 for v in grouped.values())
    return {"tasks": len(grouped), "trials": len(rows),
            "correct_trials": sum(sum(v) for v in grouped.values()),
            "pass_at_1": sum(sum(v) for v in grouped.values()) / len(rows),
            "solved_at_4": sum(any(v) for v in grouped.values()),
            "pass_at_4": sum(any(v) for v in grouped.values()) / len(grouped)}


class ReportData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "study-data":
            self.capture = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)


def main():
    base = ROOT / "benchmarks/a-b-c"
    sources = [base / f"VP-Bench-{f}-400.jsonl" for f in "ABC"]
    tasks = {t["id"]: t for path in sources for t in load_rows(path)}
    result = {"purpose": "Diagnostic only; no official scores, prompts, membership, or raw outputs changed.",
              "extraction": {"A": "One complete JSON array at response end, optional closing code fence; no schema repair.",
                             "B_C": "Existing original VP extract_answer: one answer block anywhere; unchanged ABC accepted forms."},
              "models": {}, "original_report": {}}
    for label in ["sft-base", "grpo-r3", "astra"]:
        if label == "astra":
            paths = [base / "runs/astra-xhigh-pass4-20261010" / f / "results.jsonl" for f in "ABC"]
        else:
            paths = [base / "runs/sft-grpo-pass4-20261010" / label / "outputs.jsonl"]
        sources.extend(paths)
        rows = [r for path in paths for r in load_rows(path)]
        assert len(rows) == 4800 and len({(r["task_id"], r["trial"]) for r in rows}) == 4800
        families = {}
        for family in "ABC":
            selected = [r for r in rows if r["family"] == family]
            assert len(selected) == 1600
            diagnostics, reasons, examples = [], Counter(), []
            for row in selected:
                text = row["output_text"]
                assert grade(tasks[row["task_id"]], text)["is_correct"] == row["is_correct"]
                answer = final_array(text) if family == "A" else extract_answer(text)
                evaluation = {"is_correct": False, "reason": "no_unambiguous_extracted_answer"}
                if answer is not None:
                    evaluation = grade(tasks[row["task_id"]], answer if family == "A" else f"<answer>{answer}</answer>")
                reasons[evaluation["reason"]] += 1
                diagnostics.append(dict(row, diagnostic_correct=evaluation["is_correct"]))
                if evaluation["is_correct"] and not row["is_correct"]:
                    examples.append({"task_id": row["task_id"], "trial": row["trial"], "extracted": answer})
            families[family] = {"official": stats(selected), "diagnostic": stats(diagnostics, "diagnostic_correct"),
                "official_reasons": dict(Counter(r["reason"] for r in selected)),
                "diagnostic_reasons": dict(reasons), "empty": sum(not r["output_text"].strip() for r in selected),
                "truncated": sum(r["truncated"] for r in selected), "recovered_examples": examples[:5]}
        if label == "astra":
            for family in ["A", "C"]:
                groups = defaultdict(list)
                for row in rows:
                    if row["family"] != family:
                        continue
                    task = tasks[row["task_id"]]
                    if family == "A":
                        key = "multiple_analyses" if len(task["accepted_analyses"]) > 1 else "single_analysis"
                    else:
                        key = "previously_flagged_meaning_templates" if task["semantic_category"] in {"Janapada", "AsyaNivasa"} else "other_templates"
                    groups[key].append(row)
                families[family]["descriptive_slices_not_revised_scores"] = {k: stats(v) for k, v in groups.items()}
        result["models"][label] = families

    report_path = ROOT / "benchmarks/report.html"
    parser = ReportData()
    parser.feed(report_path.read_text())
    report = json.loads("".join(parser.parts))
    sources.append(report_path)
    result["original_report"]["generated_at"] = report["generated_at"]
    result["original_report"]["method"] = report["method"]
    for cohort in ["all", "validation", "clean_validation"]:
        result["original_report"][cohort] = {
            model["id"]: metric for model, metric in zip(report["models"], report["cohorts"][cohort]["overall"])
            if model["id"] in {"sft-67", "grpo-r3", "gpt-6-astra-xhigh", "claude-opus-5-5-xhigh"}}
    archived = ROOT / "benchmarks/archive/results/grpo-r3-per-task.json"
    sources.append(archived)
    by_id = {r["id"]: r for r in json.loads(archived.read_text())["tasks"]}
    for cohort in ["validation", "clean_validation"]:
        subset = [t for t in report["tasks"] if t["split"] == "validation" and (cohort != "clean_validation" or not t["shared_root"])]
        estimates = []
        for task in subset:
            row = by_id[task["id"]]
            n, c = row["attempts"], row["exact_successes"]
            estimates.append(1.0 if n - c < 4 else 1 - math.comb(n - c, 4) / math.comb(n, 4))
        result["original_report"][cohort]["grpo-r3"]["pass_at_4_estimated_from_16"] = sum(estimates) / len(estimates)
    result["original_report"]["limitations"] = [
        "Archived checkpoint pass@1 averages 16 samples; frontier runs have one sample per task.",
        "Different prompt versions and decoding protocols; these are historical comparisons, not a new matched experiment.",
        "All-tasks GRPO includes original training tasks; prefer the validation or disjoint citation+class validation view.",
        "The report flags 1,972 Bhave requests outside third singular. New prototype excludes Bhave as a whole."]
    sources.extend([Path(__file__).resolve(), ROOT / "misc/abc_astra_eval.py", ROOT / "finetune/prompts.py"])
    result["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    out = base / "analysis/fairness-review.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
