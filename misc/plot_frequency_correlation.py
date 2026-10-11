"""Render corpus-frequency correlations against saved GRPO-r3 task outcomes.

uv run --no-project --with numpy --with scipy --with matplotlib \
  python -m misc.plot_frequency_correlation

The command delegates to benchmarks/frequency-analysis/plot_frequency_correlation.py.
Legacy heuristic helpers below are retained for the archived earlier analysis.
"""

import json
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr, spearmanr

from misc.benchmark_full_eval import ROOT, SCORES, digest, load_pool, task_score, write_json


RESAMPLES = 10000
SEED = 42
RARITY = ["mean_rarity", *SCORES]
NAMES = {"mean_rarity": "Mean of all four scores", "lakara": "Lakara", "prayoga": "Prayoga",
         "purusha": "Purusha", "vacana": "Vacana"}
COLORS = {"mean_rarity": "#253d56", "lakara": "#277fa5", "prayoga": "#c77327",
          "purusha": "#865aaf", "vacana": "#219780"}


def moments(cells, values):
    """Exact Pearson/Spearman from weighted discrete joint distributions.

    Ranks, including ties, are recomputed separately in every bootstrap sample.
    This does not hold original ranks fixed while resampling.
    """
    weights = cells / cells.sum(axis=(1, 2), keepdims=True)
    px, py = weights.sum(axis=2), weights.sum(axis=1)
    y = np.arange(17) / 16
    mx, my = px @ values, py @ y
    vx, vy = px @ (values ** 2) - mx ** 2, py @ (y ** 2) - my ** 2
    cov = np.einsum("bij,i,j->b", weights, values, y) - mx * my
    pearson = cov / np.sqrt(vx * vy)
    rx = np.cumsum(px, axis=1) - .5 * px
    ry = np.cumsum(py, axis=1) - .5 * py
    rxc, ryc = rx - .5, ry - .5
    spearman = (np.einsum("bij,bi,bj->b", weights, rxc, ryc)
                / np.sqrt((px * rxc ** 2).sum(1) * (py * ryc ** 2).sum(1)))
    slopes = cov / vx
    nx = cells.sum(axis=2)
    bin_means = np.divide(cells @ y, nx, out=np.full_like(nx, np.nan), where=nx > 0)
    return {"pearson": pearson, "spearman": spearman, "slope": slopes,
            "intercept": my - slopes * mx, "bin_means": bin_means}


def interval(value, bootstrap):
    assert np.isfinite(bootstrap).all()
    return {"estimate": float(value), "se": float(np.std(bootstrap, ddof=1)),
            "ci95": np.quantile(bootstrap, [.025, .975]).tolist()}


def cohort_analysis(tasks, rows, features, mask, cohort):
    indices = np.flatnonzero(mask)
    selected = [tasks[i] for i in indices]
    roots = sorted({(t["dhatu"]["aupadeshika"], t["dhatu"]["gana"]) for t in selected})
    ridx = {key: i for i, key in enumerate(roots)}
    r = np.array([ridx[t["dhatu"]["aupadeshika"], t["dhatu"]["gana"]] for t in selected])
    c = np.array([rows[t["id"]]["exact_successes"] for t in selected])
    joint_blocks, specs = [], {}
    offset = 0
    for name, all_values in features.items():
        values, xidx = np.unique(all_values[indices], return_inverse=True)
        joint = np.zeros((len(roots), len(values), 17))
        np.add.at(joint, (r, xidx, c), 1)
        block = joint.reshape(len(roots), -1)
        joint_blocks.append(block)
        specs[name] = {"values": values, "start": offset, "end": offset + block.shape[1],
                       "point_cells": joint.sum(axis=0)[None]}
        offset += block.shape[1]
    matrix = np.concatenate(joint_blocks, axis=1)
    point, boots = {}, {}
    for name, spec in specs.items():
        point[name] = moments(spec["point_cells"], spec["values"])
        x, y = features[name][indices], c / 16
        assert np.isclose(point[name]["pearson"][0], pearsonr(x, y).statistic, atol=1e-12)
        assert np.isclose(point[name]["spearman"][0], spearmanr(x, y).statistic, atol=1e-12)
        boots[name] = {key: [] for key in point[name]}
    rng = np.random.default_rng(SEED)
    for batch in range(RESAMPLES // 250):
        w = rng.multinomial(len(roots), np.full(len(roots), 1 / len(roots)), size=250).astype(float)
        resampled = w @ matrix
        for name, spec in specs.items():
            cells = resampled[:, spec["start"]:spec["end"]].reshape(250, len(spec["values"]), 17)
            calculated = moments(cells, spec["values"])
            for key, values in calculated.items():
                boots[name][key].append(values)
            # Independent check on actual expanded bootstrap observations.
            if batch == 0 and name in RARITY:
                sx, sy = np.indices(cells[0].shape)
                repeats = cells[0].astype(int).ravel()
                bx = np.repeat(spec["values"][sx.ravel()], repeats)
                by = np.repeat(sy.ravel() / 16, repeats)
                assert np.isclose(calculated["spearman"][0], spearmanr(bx, by).statistic, atol=1e-12)
    estimates = {}
    for name, spec in specs.items():
        boot = {key: np.concatenate(chunks) for key, chunks in boots[name].items()}
        d = {key: interval(point[name][key][0], boot[key])
             for key in ("pearson", "spearman", "slope", "intercept")}
        if name in RARITY and cohort == "all":
            assert np.isfinite(boot["bin_means"]).all()
            nx = spec["point_cells"][0].sum(axis=1)
            d["bins"] = [{"value": float(value), "tasks": int(nx[i]),
                           **interval(point[name]["bin_means"][0, i], boot["bin_means"][:, i])}
                          for i, value in enumerate(spec["values"])]
        if name == "mean_rarity":
            grid = np.linspace(spec["values"].min(), spec["values"].max(), 100)
            predictions = boot["intercept"][:, None] + boot["slope"][:, None] * grid[None]
            d["linear_trend"] = {"x": grid.tolist(),
                                  "y": (point[name]["intercept"][0] + point[name]["slope"][0] * grid).tolist(),
                                  "ci95": np.quantile(predictions, [.025, .975], axis=0).tolist()}
        estimates[name] = d
    print(f"Completed {cohort}: {len(indices)} tasks, {len(roots)} root groups", flush=True)
    return {"tasks": len(indices), "root_groups": len(roots), "features": estimates}


def analyze():
    source = ROOT / "benchmarks/results/grpo-r3-per-task.json"
    saved = json.loads(source.read_text())
    rows = {r["id"]: r for r in saved["tasks"]}
    tasks, origins = load_pool()
    assert len(rows) == len(saved["tasks"]) == len(tasks) == 6687
    assert set(rows) == {t["id"] for t in tasks}
    for t in tasks:
        r = rows[t["id"]]
        assert r["attempts"] == 16 and 0 <= r["exact_successes"] <= 16
        assert r["mean_score"] == task_score(t) and r["source_split"] == origins[t["id"]]
    features = {"mean_rarity": np.array([task_score(t) for t in tasks])}
    for dim in SCORES:
        features[dim] = np.array([SCORES[dim][t["morphology"][dim]] for t in tasks], dtype=float)
    for dim in SCORES:
        counts = Counter(t["morphology"][dim] for t in tasks)
        features[f"dataset_frequency_{dim}"] = np.array([counts[t["morphology"][dim]] / len(tasks) for t in tasks])
    # Input/reference descriptors are checked without modifying their definitions.
    features["reference_length_slp1"] = np.array([np.median([len(g) for g in t["gold_slp1"]]) for t in tasks])
    features["accepted_form_count"] = np.array([len(t["gold_slp1"]) for t in tasks], dtype=float)
    cohorts = {}
    for cohort in ("all", "validation"):
        mask = np.array([cohort == "all" or origins[t["id"]] == cohort for t in tasks])
        cohorts[cohort] = cohort_analysis(tasks, rows, features, mask, cohort)
    # Preserve option-mean statistics separately: their unit is not an individual task.
    option_correlations = {}
    y = np.array([rows[t["id"]]["exact_successes"] / 16 for t in tasks])
    for dim in SCORES:
        names = list(SCORES[dim])
        means = [np.mean([y[i] for i, t in enumerate(tasks) if t["morphology"][dim] == name]) for name in names]
        x = [SCORES[dim][name] for name in names]
        option_correlations[dim] = {"options": len(names), "pearson": float(pearsonr(x, means).statistic),
                                    "spearman": float(spearmanr(x, means).statistic)}
    return {
        "model": saved["model"], "tasks": len(tasks), "samples_per_task": 16,
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in (
            source, ROOT / "data/finetune/task-data/finetune.json",
            ROOT / "data/finetune/task-data/validation.json", ROOT / "misc/benchmark_full_eval.py")},
        "fixed_rarity_scores": SCORES,
        "method": {"unit": "One task, with outcome = successes / 16; all tasks weighted equally",
                   "primary_statistic": "Spearman rank correlation; tied ranks recomputed within each bootstrap",
                   "secondary_statistic": "Pearson linear correlation; slope in probability per score unit",
                   "uncertainty": f"{RESAMPLES} percentile bootstrap resamples of whole (dhatu citation, gana) groups, within each cohort; seed {SEED}",
                   "scores": "Existing heuristic usage-rarity scores kept fixed; 1 = frequent, 5 = rare. Negative correlations support the frequency hypothesis.",
                   "dataset_frequency": "Fixed observed option share in the full 6687-task pool; measured task composition, not natural-language or model-training frequency. Positive correlations would mean more represented options perform better.",
                   "limits": "Observational correlations for one model. Pooled data include training tasks. Original validation outcomes were already inspected, so they are not a new untouched confirmation set. Intervals are pointwise, not simultaneous or adjusted for exploratory feature inspection."},
        "cohorts": cohorts, "option_mean_correlations": option_correlations,
        "auxiliary_features": {"reference_length_slp1": "Median number of SLP1 characters across accepted forms; not tokenizer length or syllable count",
                               "accepted_form_count": "Number of accepted reference forms; not proof of linguistic irregularity or a causal difficulty measure"},
    }


def forest(ax, cohort, keys, title, positive_expected=False):
    ax.set_title(title, loc="left", fontsize=17, fontweight="bold", pad=18)
    ax.axvline(0, color="#768a9e", lw=1.2)
    ax.axvspan(0 if positive_expected else -.36, .24 if positive_expected else 0, color="#eaf3f8", zorder=0)
    for i, key in enumerate(keys):
        stat = cohort["features"][key]["spearman"]
        value, (lo, hi) = stat["estimate"], stat["ci95"]
        dim = key.replace("dataset_frequency_", "")
        ax.errorbar(value, i, xerr=[[value-lo], [hi-value]], fmt="o", color=COLORS[dim],
                    capsize=5, markersize=7, elinewidth=2, zorder=3)
        ax.text(.465, i, f"{value:+.3f}  [{lo:+.3f}, {hi:+.3f}]", ha="right", va="center", fontsize=10.5)
    ax.set_yticks(range(len(keys)), ["Mean rarity" if k == "mean_rarity" else NAMES[k.replace("dataset_frequency_", "")] for k in keys])
    ax.set_ylim(len(keys)-.4, -.65)
    ax.set_xlim(-.36, .48)
    ax.set_xticks([-.3, -.2, -.1, 0, .1, .2])
    ax.set_xlabel("Task-level Spearman ρ · point estimate and 95% interval")
    ax.grid(axis="x", color="#e6ebf0", zorder=0)
    ax.spines[["top", "right"]].set_visible(False)


def draw(result):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.labelsize": 12, "axes.edgecolor": "#bccbd6",
                         "axes.spines.top": False, "axes.spines.right": False,
                         "text.color": "#253d56", "axes.labelcolor": "#253d56"})
    fig = plt.figure(figsize=(22, 22), facecolor="#f8fafc")
    grid = fig.add_gridspec(3, 2, left=.08, right=.97, bottom=.14, top=.86,
                           height_ratios=[1.15, 1, 1.1], hspace=.56, wspace=.35)
    fig.suptitle("Does frequency explain performance?", x=.08, y=.975, ha="left", fontsize=34, fontweight="bold")
    fig.text(.08, .937, "GRPO-r3 · 6,687 tasks · 16 attempts/task · fixed input scores, task-level correlations", fontsize=17)
    fig.text(.08, .912, "Overall rarity has very little task-level association with pass@1. Lakara and prayoga have opposite trends.", fontsize=18, fontweight="bold")
    all_data, validation = result["cohorts"]["all"], result["cohorts"]["validation"]
    mean = all_data["features"]["mean_rarity"]
    ax = fig.add_subplot(grid[0, :], facecolor="white")
    ax.set_title("Combined rarity: all tasks, grouped only by their existing mean score", loc="left", fontsize=18, fontweight="bold", pad=20)
    bins = mean["bins"]
    xs = np.array([d["value"] for d in bins])
    ys = np.array([d["estimate"] * 100 for d in bins])
    cis = np.array([d["ci95"] for d in bins]) * 100
    ax.errorbar(xs, ys, yerr=[ys-cis[:, 0], cis[:, 1]-ys], fmt="o-", lw=1.5,
                color="#277fa5", capsize=5, markersize=6, label="Observed pass@1 at each score")
    trend = mean["linear_trend"]
    ax.plot(trend["x"], np.array(trend["y"]) * 100, color="#c77327", lw=2, ls="--", label="Linear fit across individual tasks")
    ax.fill_between(trend["x"], np.array(trend["ci95"])[0]*100, np.array(trend["ci95"])[1]*100,
                    color="#c77327", alpha=.13, label="95% interval for fitted mean")
    for x, y, ci, d in zip(xs, ys, cis, bins):
        ax.text(x, ci[1] + 2.4, f"{y:.1f}%\nn={d['tasks']:,}", ha="center", fontsize=10, linespacing=1.35)
    rho, pearson = mean["spearman"], mean["pearson"]
    summary = (f"Spearman ρ = {rho['estimate']:+.3f}  [{rho['ci95'][0]:+.3f}, {rho['ci95'][1]:+.3f}]\n"
               f"Pearson r = {pearson['estimate']:+.3f}  [{pearson['ci95'][0]:+.3f}, {pearson['ci95'][1]:+.3f}]\n"
               f"Linear R² = {100*pearson['estimate']**2:.3f}%")
    ax.text(.985, .04, summary, transform=ax.transAxes, ha="right", va="bottom", fontsize=13,
            bbox={"facecolor": "white", "edgecolor": "#dce5ec", "pad": 10})
    ax.legend(loc="lower left", frameon=False, fontsize=11)
    ax.set_ylim(0, 101)
    ax.set_xlim(.85, 4.15)
    ax.set_xticks(xs)
    ax.set_xlabel("Mean of the four rarity scores · left = more frequent, right = rarer")
    ax.set_ylabel("Pass@1 (%)")
    ax.grid(axis="y", color="#e5ebf0")

    forest(fig.add_subplot(grid[1, 0], facecolor="white"), all_data, RARITY,
           "Rarity correlations · all 6,687 tasks")
    forest(fig.add_subplot(grid[1, 1], facecolor="white"), validation, RARITY,
           "Same fixed scores · 669 original validation tasks")

    ax = fig.add_subplot(grid[2, 0], facecolor="white")
    ax.set_title("Why the average hides the relationship", loc="left", fontsize=17, fontweight="bold", pad=18)
    for dim in SCORES:
        bins = all_data["features"][dim]["bins"]
        xs = np.array([d["value"] for d in bins])
        ys = np.array([d["estimate"] for d in bins])*100
        cis = np.array([d["ci95"] for d in bins])*100
        ax.errorbar(xs, ys, yerr=[ys-cis[:, 0], cis[:, 1]-ys], fmt="o-", capsize=4,
                    color=COLORS[dim], lw=2, markersize=6, label=NAMES[dim])
    ax.set_ylim(0, 100)
    ax.set_xticks(range(1, 6))
    ax.set_xlabel("Existing rarity score · 1 = frequent → 5 = rare")
    ax.set_ylabel("Pass@1 (%) · options with equal scores pooled")
    ax.grid(axis="y", color="#e5ebf0")
    ax.legend(loc="lower left", frameon=False, ncol=2, fontsize=11)
    forest(fig.add_subplot(grid[2, 1], facecolor="white"), all_data,
           [f"dataset_frequency_{dim}" for dim in SCORES],
           "Actual task share · a different frequency measure", positive_expected=True)

    notes = [
        "INTERPRETATION",
        "Rarity panels: negative ρ supports 'rarer is harder'; positive ρ contradicts it. Frequency-of-task panels: the expected sign is positive.",
        "The 1–5 scores are heuristic estimates, not measured Sanskrit corpus frequency. Task shares are nearly balanced by random sampling.",
        "Lakara identity matters beyond this score: Lit and Lrt both score 3, yet average 27.1% and 74.1% pass@1, respectively.",
        "Across the 10 lakara option averages, rarity has Spearman ρ = −0.718; across individual tasks, ρ = −0.199. The unit of comparison matters.",
        f"Intervals resample whole verb-root groups {RESAMPLES:,} times. Correlations weight tasks equally; correlating only the category means answers a different question.",
        "Pooled results include 6,018 original training tasks. Original validation results were already inspected; they are not an untouched confirmation set.",
        "The earlier outcome-based clusters describe this run. They do not independently validate frequency or define general benchmark difficulty.",
    ]
    for i, note in enumerate(notes):
        fig.text(.08, .103 - i*.0123, note, fontsize=11.5 if i == 0 else 11,
                 fontweight="bold" if i == 0 else "normal")
    target = ROOT / "benchmarks/frequency-correlation.png"
    fig.savefig(target, dpi=200, facecolor=fig.get_facecolor(), metadata={"Description": "Fixed rarity scores and observed task frequencies versus GRPO-r3 pass@1, task-level correlations and root-bootstrap confidence intervals."})
    plt.close(fig)
    return target


def write_report(result):
    lines = ["# Do fixed frequency proxies explain performance?", "",
             "This analysis holds the existing inputs fixed and measures their relationship with GRPO-r3 pass@1. It does not derive difficulty labels from outcomes.", "",
             "The rarity scores are heuristic estimates, not corpus frequency measurements. The task generator samples morphology coordinates randomly; small differences in task share are not natural Sanskrit usage frequency.", "",
             "All 6,687 tasks and their 16 completions are used. Primary statistic: task-level Spearman correlation. A negative coefficient supports the proposed rarity–difficulty relationship.", "",
             result["method"]["uncertainty"], "", "## Fixed rarity scores", "",
             "| Feature | All tasks: Spearman ρ [95% CI] | Original validation: ρ [95% CI] | All tasks: Pearson r |",
             "|---|---|---|---:|"]
    def fmt(stat):
        return f"{stat['estimate']:+.3f} [{stat['ci95'][0]:+.3f}, {stat['ci95'][1]:+.3f}]"
    for key in RARITY:
        a = result["cohorts"]["all"]["features"][key]
        v = result["cohorts"]["validation"]["features"][key]
        lines.append(f"| {NAMES[key]} | {fmt(a['spearman'])} | {fmt(v['spearman'])} | {a['pearson']['estimate']:+.3f} |")
    r = result["cohorts"]["all"]["features"]["mean_rarity"]["pearson"]["estimate"]
    lines += ["", f"The overall linear fit explains **{100*r*r:.3f}%** of the variance in observed per-task success fractions. This is descriptive R² for one predictor, not a causal effect or cross-validated prediction score.", "",
              "Lakara has a modest task-level association in the expected direction; prayoga points in the opposite direction. Purusha and vacana contribute little marginal ordering. Taking their mean obscures these differences.", "",
              "A direct counterexample: Lit and Lrt both have rarity score 3, while their pass@1 is 27.14% and 74.13%.", "",
              "## Frequency within the task pool", "",
              "Here positive correlations would support 'more represented options perform better'. The predictor is the fixed observed option share within all 6,687 tasks, not training-token or corpus frequency.", "",
              "| Dimension | All tasks: Spearman ρ [95% CI] | Original validation: ρ [95% CI] |", "|---|---|---|"]
    for dim in SCORES:
        key = f"dataset_frequency_{dim}"
        a = result["cohorts"]["all"]["features"][key]["spearman"]
        v = result["cohorts"]["validation"]["features"][key]["spearman"]
        lines.append(f"| {NAMES[dim]} | {fmt(a)} | {fmt(v)} |")
    lines += ["", "## Aggregation changes the question", "",
              "Across only the ten lakara option means, rarity versus mean accuracy has Spearman ρ = "
              f"{result['option_mean_correlations']['lakara']['spearman']:.3f}; across individual tasks it is "
              f"{result['cohorts']['all']['features']['lakara']['spearman']['estimate']:.3f}. Averaging suppresses within-option variation. Neither statistic measures actual corpus usage. Three-point correlations for the other dimensions should not be interpreted as strong task-level prediction.", "",
              "## Other fixed descriptors checked (exploratory)", "",
              "| Descriptor | All tasks: Spearman ρ [95% CI] | Original validation: ρ [95% CI] |", "|---|---|---|"]
    for key, description in result["auxiliary_features"].items():
        a = result["cohorts"]["all"]["features"][key]["spearman"]
        v = result["cohorts"]["validation"]["features"][key]["spearman"]
        lines.append(f"| {description} | {fmt(a)} | {fmt(v)} |")
    lines += ["", "These extra descriptors were inspected exploratorily. Number of acceptable forms could be a proxy for properties of the paradigm, but the correlation does not establish that explanation. No bins or scores were changed in response to these results.", "",
              "## Implication for benchmark design", "",
              "Use fixed linguistic categories such as lakara and prayoga to describe runs. The current mean rarity score is not supported as a useful general difficulty ordering for this checkpoint.", "",
              "For a frequency-based hypothesis, obtain root/form or morphology frequencies from an independent Sanskrit corpus or documented training distribution; fix the frequency measure and cutoffs before evaluating an untouched confirmation set. Predeclare any structural-complexity measure as a separate hypothesis. Test consistency across checkpoints rather than tuning categories to maximize a single run's gaps.", "",
              "The previous fitted clusters and optimized thresholds are descriptive analyses of these same outcomes; their separation is not independent validation of a difficulty benchmark.", "",
              result["method"]["limits"], "",
              "Reproduce with the command at the top of `misc/plot_frequency_correlation.py`.", ""]
    (ROOT / "benchmarks/results/frequency-correlation.md").write_text("\n".join(lines))


def main():
    import runpy
    import sys
    folder = ROOT / "benchmarks/frequency-analysis"
    sys.path.insert(0, str(folder))
    runpy.run_path(str(folder / "plot_frequency_correlation.py"), run_name="__main__")


if __name__ == "__main__":
    main()
