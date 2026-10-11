"""Exhaustively fit mean-score boundaries to saved GRPO-r3 pass@1 results.

Uses all completed tasks; no model inference. Existing benchmark definitions
and the original evaluation report remain available for comparison.
"""

import itertools
import json
import math
from pathlib import Path

import numpy as np

from misc.benchmark_full_eval import ROOT, digest, load_pool, task_score, write_json


def main():
    source = ROOT / "benchmarks/results/grpo-r3-per-task.json"
    saved = json.loads(source.read_text())
    rows = {t["id"]: t for t in saved["tasks"]}
    tasks, origins = load_pool()
    assert len(rows) == len(tasks) == len(saved["tasks"]) == 6687
    assert set(rows) == {t["id"] for t in tasks}
    scores = sorted({t["mean_score"] for t in rows.values()})
    roots = sorted({(t["dhatu"]["aupadeshika"], t["dhatu"]["gana"]) for t in tasks})
    ridx = {r: i for i, r in enumerate(roots)}
    sidx = {s: i for i, s in enumerate(scores)}
    counts = np.zeros((len(roots), len(scores)), dtype=int)
    sums = np.zeros_like(counts, dtype=float)
    for task in tasks:
        row = rows[task["id"]]
        assert row["mean_score"] == task_score(task)
        assert row["source_split"] == origins[task["id"]]
        assert row["attempts"] == 16 and 0 <= row["exact_successes"] <= 16
        i = ridx[(task["dhatu"]["aupadeshika"], task["dhatu"]["gana"])]
        j = sidx[row["mean_score"]]
        counts[i, j] += 1
        sums[i, j] += row["exact_successes"] / row["attempts"]

    # One set of root resamples covers all score boundaries and preserves
    # dependence between tasks and between candidate bucket differences.
    rng = np.random.default_rng(42)
    boot_counts, boot_sums = [], []
    for _ in range(80):
        w = rng.multinomial(len(roots), np.full(len(roots), 1 / len(roots)), size=250)
        boot_counts.append(w @ counts)
        boot_sums.append(w @ sums)
    bc = np.cumsum(np.concatenate(boot_counts), axis=1)
    bs = np.cumsum(np.concatenate(boot_sums), axis=1)
    c = np.cumsum(counts.sum(axis=0))
    s = np.cumsum(sums.sum(axis=0))

    def interval(estimate, bootstrap):
        return {"estimate": float(estimate), "se": float(bootstrap.std(ddof=1)),
                "ci95": np.quantile(bootstrap, [.025, .975]).tolist()}

    candidates = []
    for i, j in itertools.combinations(range(len(scores) - 1), 2):
        n = np.array([c[i], c[j] - c[i], c[-1] - c[j]])
        p = np.array([s[i], s[j] - s[i], s[-1] - s[j]]) / n
        bn = np.column_stack([bc[:, i], bc[:, j] - bc[:, i], bc[:, -1] - bc[:, j]])
        assert (bn > 0).all()
        bp = np.column_stack([bs[:, i], bs[:, j] - bs[:, i], bs[:, -1] - bs[:, j]]) / bn
        gaps = np.array([p[0] - p[1], p[1] - p[2]])
        candidates.append({
            "easy_max": scores[i], "medium_max": scores[j],
            "minimum_adjacent_gap": float(min(gaps)),
            "segments": {name: {"tasks": int(n[k]), "share": float(n[k] / len(tasks)),
                                 "pass_at_1": interval(p[k], bp[:, k])}
                         for k, name in enumerate(("easy", "medium", "hard"))},
            "differences": {name: interval(p[a] - p[b], bp[:, a] - bp[:, b])
                            for name, a, b in (("easy-medium", 0, 1), ("medium-hard", 1, 2),
                                               ("easy-hard", 0, 2))},
        })
    candidates.sort(key=lambda x: (x["minimum_adjacent_gap"],
                                   x["differences"]["easy-hard"]["estimate"],
                                   min(d["tasks"] for d in x["segments"].values())), reverse=True)

    def best(min_tasks):
        return next(x for x in candidates if min(d["tasks"] for d in x["segments"].values()) >= min_tasks)

    minimum = math.ceil(.05 * len(tasks))
    recommended = best(minimum)
    old = next(x for x in candidates if (x["easy_max"], x["medium_max"]) == (2, 3))
    previous = json.loads((ROOT / "benchmarks/results/grpo-r3-full.json").read_text())
    # Independent score-bin aggregation must reproduce the previous full-pool
    # point estimates, root-bootstrap SEs, and intervals at the old cutoffs.
    assert previous["cutoffs"] == {"easy": "mean <= 2", "medium": "2 < mean <= 3", "hard": "mean > 3"}
    for name in ("easy", "medium", "hard"):
        ref = previous["cohorts"]["all"]["segments"][name]["pass_at_k"]["1"]
        actual = old["segments"][name]["pass_at_1"]
        assert abs(ref["estimate"] - actual["estimate"]) < 1e-12
        assert abs(ref["se"] - actual["se"]) < 1e-12
        assert np.allclose(ref["ci95"], actual["ci95"], atol=1e-12, rtol=0)

    result = {
        "model": saved["model"], "tasks": len(tasks), "source_sha256": digest(source),
        "objective": "Maximize min(pass@1_easy - pass@1_medium, pass@1_medium - pass@1_hard).",
        "tie_breakers": ["larger easy-hard gap", "larger smallest bucket"],
        "rule": "easy: mean <= easy_max; medium: easy_max < mean <= medium_max; hard: mean > medium_max",
        "n_candidates": len(candidates),
        "uncertainty": {"resamples": 20000, "seed": 42, "root_clusters": len(roots),
                        "method": "percentile bootstrap of (citation, gana) clusters",
                        "note": "Descriptive intervals conditional on chosen cutoffs; not adjusted for threshold selection on these same outcomes."},
        "per_score": [{"score": score, "tasks": int(counts[:, i].sum()),
                       "pass_at_1": float(sums[:, i].sum() / counts[:, i].sum())}
                      for i, score in enumerate(scores)],
        "unrestricted_best": best(1), "recommended_minimum_tasks": minimum,
        "recommended": recommended, "previous": old,
        "sensitivity": {str(n): best(n) for n in (50, 100, 200, minimum, math.ceil(.1 * len(tasks)), math.ceil(.2 * len(tasks)))},
        "all_candidates": candidates,
    }
    target = ROOT / "benchmarks/results/grpo-r3-threshold-search.json"
    write_json(target, result)
    lines = ["# GRPO-r3 mean-score threshold search", "",
             "All 66 distinct boundary pairs were evaluated on all 6,687 tasks using their 16 saved completions. No new inference was needed.",
             "The objective maximizes the smaller of the easy–medium and medium–hard pass@1 gaps, preserving the order of the mean score.",
             "The recommended solution requires at least 5% of tasks in each bucket (335 tasks). The same pair wins with minimum bucket sizes of 50, 100, or 200 tasks.",
             "SE and 95% confidence intervals use 20,000 root-group bootstrap resamples. They are descriptive and do not adjust for selecting thresholds on these same results.", ""]
    for label, winner in (("Recommended", recommended), ("Unrestricted maximum", best(1)), ("At least 10% per bucket", best(math.ceil(.1 * len(tasks))))):
        a, b = winner["easy_max"], winner["medium_max"]
        lines += [f"## {label}: {a:g}, {b:g}", "",
                  "| Bucket | Mean score | Tasks | Share | Pass@1 | SE (pp) | 95% CI |",
                  "|---|---|---:|---:|---:|---:|---|"]
        for name, rule in (("easy", f"≤ {a:g}"), ("medium", f"{a:g} < mean ≤ {b:g}"), ("hard", f"> {b:g}")):
            d = winner["segments"][name]; p = d["pass_at_1"]
            lines.append(f"| {name} | {rule} | {d['tasks']} | {d['share']*100:.2f}% | {p['estimate']*100:.2f}% | {p['se']*100:.2f} | [{p['ci95'][0]*100:.2f}, {p['ci95'][1]*100:.2f}] |")
        lines += ["", f"Smallest adjacent gap: **{100*winner['minimum_adjacent_gap']:.2f} percentage points**.", ""]
        for name, d in winner["differences"].items():
            lines.append(f"- {name}: {d['estimate']*100:.2f} pp; 95% CI [{d['ci95'][0]*100:.2f}, {d['ci95'][1]*100:.2f}].")
        lines.append("")
    lines += ["The original cutoffs remain in the original evaluation files. The search results provide the proposed replacement boundaries; all candidates and score-level accuracies are in the accompanying JSON.", ""]
    target.with_suffix(".md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
