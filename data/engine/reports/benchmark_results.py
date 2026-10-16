"""Build the standalone results page from completed v3 benchmark runs.

Run from any directory: python3 data/engine/reports/benchmark_results.py
Only reads local results; never calls a model API.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "data/benchmark/results"
FAMILIES = ["tinanta", "taddhitanta", "krdanta", "subanta"]
MODELS = {
    "astra-xhigh": ("GPT-6 Astra", "Astra", "openai"),
    "sol-xhigh": ("GPT-6 Sol", "Sol", "openai"),
    "luna-xhigh": ("GPT-6 Luna", "Luna", "openai"),
    "opus55-xhigh": ("Claude Opus 5.5", "Opus 5.5", "anthropic"),
    "sonnet55-xhigh": ("Claude Sonnet 5.5", "Sonnet 5.5", "anthropic"),
    "haiku55-xhigh": ("Claude Haiku 5.5", "Haiku 5.5", "anthropic"),
    "gemini4-argon-high": ("Gemini 4 Argon", "Argon", "google"),
    "gemini38-flash-high": ("Gemini 3.8 Flash", "Flash", "google"),
}


def quantiles(values):
    """Descriptive percentiles, with linear interpolation between observations."""
    values = sorted(values)
    if not values:
        raise ValueError("A distribution needs at least one observation")

    def at(q):
        index = (len(values) - 1) * q
        lo = math.floor(index)
        hi = math.ceil(index)
        return values[lo] + (values[hi] - values[lo]) * (index - lo)

    return {"min": values[0], "p10": at(.1), "q1": at(.25), "median": at(.5),
            "q3": at(.75), "p90": at(.9), "p99": at(.99), "max": values[-1]}


def comparison_stats(vectors):
    """Count paired outcomes on identical, ordered tasks; no extra model calls."""
    ids = list(vectors)
    sizes = {len(v) for v in vectors.values()}
    if not ids or len(sizes) != 1 or not next(iter(sizes)):
        raise ValueError("Comparison requires nonempty, aligned task vectors")
    if any(value not in (0, 1) for v in vectors.values() for value in v):
        raise ValueError("Comparison outcomes must be binary")
    n = next(iter(sizes))
    consensus = [0] * (len(ids) + 1)
    for task in zip(*vectors.values()):
        consensus[sum(task)] += 1
    return {"ids": ids, "n": n, "correct": [sum(vectors[k]) for k in ids],
            "consensus": consensus,
            "wins": [[sum(a and not b for a, b in zip(vectors[i], vectors[j]))
                      for j in ids] for i in ids]}


def summarize(rows):
    """Use every selected task, including refusals and truncated responses."""
    n = len(rows)
    metrics = {
        "tokens": [(r.get("usage") or {}).get("output_tokens") for r in rows],
        "duration": [r.get("elapsed_ms") / 1000 if r.get("elapsed_ms") is not None else None for r in rows],
        "cost": [r.get("cost_usd") for r in rows],
    }
    result = {
        "n": n,
        "correct": sum(r.get("correct") is True for r in rows),
        "strictCorrect": sum(r.get("correct") is True and r.get("format_ok") is True for r in rows),
        "formatFailures": sum(r.get("format_ok") is not True for r in rows),
        "statuses": dict(Counter(r["status"] for r in rows)),
        "mean": {},
        "median": {},
        "metricCounts": {},
        "distribution": {},
    }
    result["answer"] = 100 * result["correct"] / n
    result["strict"] = 100 * result["strictCorrect"] / n
    for key, values in metrics.items():
        known = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
        if len(known) != n:
            raise ValueError(f"Missing {key} for {n - len(known)} selected results; do not silently exclude rows")
        result["mean"][key] = statistics.mean(known)
        result["median"][key] = statistics.median(known)
        result["metricCounts"][key] = len(known)
        result["distribution"][key] = quantiles(known)
    return result


def build_data():
    sources = {}
    for family in FAMILIES:
        path = ROOT / "data/benchmark" / family / f"{family}.json"
        sources[family] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": json.loads(path.read_text())}
    models = []
    outcomes = {f: {score: {} for score in ("answer", "strict")} for f in FAMILIES}
    for folder, (label, short, provider) in MODELS.items():
        path = RESULTS / folder
        manifest = json.loads((path / "manifest.json").read_text())
        if manifest["execution"]["state"] != "completed" or manifest["prompt_version"] != "v3":
            raise ValueError(f"{folder} is not a completed v3 run")
        if manifest["provider"] != ("google_vertex_ai" if provider == "google" else provider):
            raise ValueError(f"Unexpected provider for {folder}")
        recorded_hashes = {Path(r["path"]).name: r["sha256"] for r in manifest["verification"]["result_files"]}
        pinned_datasets = {task["family"]: task["dataset"]["sha256"] for task in manifest["tasks"]}
        summaries = {}
        fingerprints = {}
        pooled = []
        for family in FAMILIES:
            raw = (path / f"{family}.json").read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != recorded_hashes[f"{family}.json"]:
                raise ValueError(f"Result hash mismatch: {folder}/{family}")
            if sources[family]["sha256"] != pinned_datasets[family]:
                raise ValueError(f"Source hash mismatch: {folder}/{family}")
            rows = json.loads(raw)
            ids = [row["task_id"] for row in rows]
            source_ids = [row.get("task_id", row.get("id")) for row in sources[family]["rows"]]
            if len(rows) != 5000 or len(set(ids)) != 5000 or ids != source_ids:
                raise ValueError(f"Incomplete or misordered family: {folder}/{family}")
            # Recheck membership independently of stored score flags.
            for row, source in zip(rows, sources[family]["rows"]):
                expected = (row["answer"] is not None and row["answer"] in source["gold_devanagari"]) if row["status"] == "completed" else None
                if row["correct"] != expected:
                    raise ValueError(f"Score mismatch: {folder}/{row['task_id']}")
            summaries[family] = summarize(rows)
            fingerprints[family] = digest
            outcomes[family]["answer"][folder] = bytearray(r["correct"] is True for r in rows)
            outcomes[family]["strict"][folder] = bytearray(r["correct"] is True and r["format_ok"] is True for r in rows)
            # Retain only the fields required for pooled statistics, not response text.
            pooled.extend({k: r[k] for k in ("correct", "format_ok", "status", "elapsed_ms", "cost_usd")}
                          | {"usage": {"output_tokens": (r.get("usage") or {}).get("output_tokens")}}
                          for r in rows)
        summary = manifest.get("summary", manifest["execution"].get("progress", {}))
        models.append({
            "id": folder, "label": label, "short": short, "provider": provider,
            "model": manifest["model"] if provider == "google" else manifest["request_defaults"]["model"],
            "effort": manifest["request_defaults"]["generationConfig"]["thinkingConfig"]["thinkingLevel"].lower() if provider == "google" else "xhigh",
            "finishedAt": manifest["finished_at"], "families": summaries,
            "pooled": summarize(pooled),
            "familyScoreSd": {score: statistics.pstdev(summaries[f][score] for f in FAMILIES)
                              for score in ("answer", "strict")},
            "knownRunCost": summary["known_cost_usd"],
            "unknownCostAttempts": summary["unknown_cost_attempts"],
            "hashes": fingerprints,
        })
    comparisons = {f: {score: comparison_stats(outcomes[f][score]) for score in ("answer", "strict")}
                   for f in FAMILIES}
    comparisons["all"] = {
        score: comparison_stats({model: b"".join(bytes(outcomes[f][score][model]) for f in FAMILIES)
                                 for model in MODELS}) for score in ("answer", "strict")}
    return {
        "schemaVersion": 2, "promptVersion": "v3", "families": FAMILIES,
        "tasksPerFamily": 5000, "tasksPerModel": 20000,
        "updatedAt": max(m["finishedAt"] for m in models),
        "models": models,
        "comparisons": comparisons,
        "standardDeviation": {"unit": "percentage points", "population": "four task-family accuracy scores",
                              "ddof": 0, "meaning": "Descriptive variation across families, not uncertainty from repeated runs."},
    }


def main():
    data = build_data()
    template = Path(__file__).with_name("benchmark_results.template.html").read_text()
    script = Path(__file__).with_name("benchmark_results.js").read_text()
    script += "\n" + Path(__file__).with_name("benchmark_results.figures.js").read_text()
    extra_css = Path(__file__).with_name("benchmark_results.css").read_text()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    if template.count("__BENCHMARK_DATA__") != 1:
        raise ValueError("Expected exactly one data placeholder")
    if template.count("__BENCHMARK_JS__") != 1:
        raise ValueError("Expected exactly one script placeholder")
    if template.count("__BENCHMARK_CSS__") != 1:
        raise ValueError("Expected exactly one style placeholder")
    destination = RESULTS / "summaries/results.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(template.replace("__BENCHMARK_DATA__", payload)
                           .replace("__MODEL_COUNT__", str(len(data["models"])))
                           .replace("__BENCHMARK_CSS__", extra_css)
                           .replace("__BENCHMARK_JS__", script))
    print(f"Wrote {destination.relative_to(ROOT)} ({destination.stat().st_size:,} bytes)")
    print(f"Verified {len(data['models'])} models, {len(data['models']) * len(FAMILIES)} result files, {len(data['models']) * data['tasksPerModel']:,} selected responses.")


if __name__ == "__main__":
    main()
