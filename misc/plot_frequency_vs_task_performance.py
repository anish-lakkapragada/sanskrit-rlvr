"""Plot all morphology options against GRPO-r3 outcomes and explore clusters.

Run from the repo root with:
uv run --no-project --with numpy --with matplotlib --with scipy \
  --with scikit-learn --with adjustText python -m misc.plot_frequency_vs_task_performance
"""

import itertools
import json
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from adjustText import adjust_text
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

from misc.benchmark_full_eval import ROOT, SCORES, digest, load_pool, task_score, write_json


SEED = 42
RESAMPLES = 20000
CLUSTER_RESAMPLES = 200
LOW, HIGH, MID, INK = "#c14d47", "#15847e", "#bd831d", "#263c53"
DIMENSIONS = {
    "lakara": "Lakara · tense / mood",
    "prayoga": "Prayoga · voice",
    "purusha": "Purusha · person",
    "vacana": "Vacana · number",
}


def gmm(x, k, n_init=30):
    # Rates live on [0, 1]; the variance floor corresponds to 1 percentage point.
    return GaussianMixture(n_components=k, covariance_type="spherical",
                           n_init=n_init, random_state=SEED, reg_covar=1e-4).fit(x)


def summarize(estimate, bootstrap, tasks):
    return {"tasks": int(tasks), "pass_at_1": float(estimate),
            "se": float(bootstrap.std(ddof=1)),
            "ci95": np.quantile(bootstrap, [.025, .975]).tolist()}


def analyze():
    source = ROOT / "benchmarks/results/grpo-r3-per-task.json"
    saved = json.loads(source.read_text())
    tasks, origins = load_pool()
    rows = {r["id"]: r for r in saved["tasks"]}
    assert len(rows) == len(tasks) == len(saved["tasks"]) == 6687
    assert set(rows) == {t["id"] for t in tasks}
    metadata = json.loads((ROOT / "data/finetune/task-data/metadata.json").read_text())
    assert all(set(v) == set(SCORES[k]) for k, v in metadata["coordinate_space"].items())
    roots = sorted({(t["dhatu"]["aupadeshika"], t["dhatu"]["gana"]) for t in tasks})
    ridx = {r: i for i, r in enumerate(roots)}
    columns = [("all", "all")]
    columns += [(dim, option) for dim, options in SCORES.items() for option in options]
    columns += [("interaction", (la, pr)) for la in SCORES["lakara"] for pr in SCORES["prayoga"]]
    cidx = {key: i for i, key in enumerate(columns)}
    counts = np.zeros((len(roots), len(columns)), dtype=int)
    sums = np.zeros_like(counts, dtype=float)
    for task in tasks:
        row = rows[task["id"]]
        assert row["source_split"] == origins[task["id"]]
        assert row["mean_score"] == task_score(task)
        assert row["attempts"] == 16 and 0 <= row["exact_successes"] <= 16
        i = ridx[(task["dhatu"]["aupadeshika"], task["dhatu"]["gana"])]
        m = task["morphology"]
        keys = [("all", "all"), *((dim, m[dim]) for dim in SCORES),
                ("interaction", (m["lakara"], m["prayoga"]))]
        for key in keys:
            j = cidx[key]
            counts[i, j] += 1
            sums[i, j] += row["exact_successes"] / row["attempts"]
    n = counts.sum(axis=0)
    p = sums.sum(axis=0) / n
    assert n[0] == len(tasks)
    for dim, options in SCORES.items():
        js = [cidx[dim, option] for option in options]
        assert n[js].sum() == len(tasks)
        assert np.isclose((n[js] * p[js]).sum() / len(tasks), p[0])
    rng = np.random.default_rng(SEED)
    bc, bs = [], []
    for _ in range(RESAMPLES // 250):
        w = rng.multinomial(len(roots), np.full(len(roots), 1 / len(roots)), size=250)
        bc.append(w @ counts)
        bs.append(w @ sums)
    bc, bs = np.concatenate(bc), np.concatenate(bs)
    assert (bc > 0).all()
    bp = bs / bc

    options = {}
    for dim, names in SCORES.items():
        options[dim] = {}
        for name, score in names.items():
            j = cidx[dim, name]
            options[dim][name] = {"rarity_score": score, "dataset_share": n[j] / len(tasks),
                                  **summarize(p[j], bp[:, j], n[j])}
    interactions = []
    for la, pr in itertools.product(SCORES["lakara"], SCORES["prayoga"]):
        j = cidx["interaction", (la, pr)]
        interactions.append({"lakara": la, "prayoga": pr, **summarize(p[j], bp[:, j], n[j])})

    names = list(SCORES["lakara"])
    js = [cidx["lakara", name] for name in names]
    x = p[js, None]
    fits = [gmm(x, k) for k in range(1, 5)]
    bics = [fit.bic(x) for fit in fits]
    selected = int(np.argmin(bics))
    fit = fits[selected]
    order = np.argsort(fit.means_.ravel())
    label_map = {int(original): int(rank) for rank, original in enumerate(order)}
    labels = np.array([label_map[int(label)] for label in fit.predict(x)])
    groups = []
    for label in range(selected + 1):
        members = [name for i, name in enumerate(names) if labels[i] == label]
        ids = [cidx["lakara", name] for name in members]
        group_n = n[ids].sum()
        boot = bs[:, ids].sum(axis=1) / bc[:, ids].sum(axis=1)
        groups.append({"members": members, **summarize((n[ids] * p[ids]).sum() / group_n, boot, group_n)})

    # A second clustering criterion exposes sensitivity to how groups are defined.
    alternatives = []
    for k in range(2, 6):
        km = KMeans(n_clusters=k, n_init=50, random_state=SEED).fit(x, sample_weight=n[js])
        partitions = [[names[i] for i in range(len(names)) if km.labels_[i] == label]
                      for label in np.argsort(km.cluster_centers_.ravel())]
        alternatives.append({"k": k, "silhouette": float(silhouette_score(x, km.labels_)),
                             "groups": partitions})
    alternative = max(alternatives, key=lambda item: item["silhouette"])

    # Resample whole roots and repeat model selection, including the one-group null.
    chosen = Counter()
    coassignment = np.zeros((len(names), len(names)))
    for b in np.linspace(0, RESAMPLES - 1, CLUSTER_RESAMPLES, dtype=int):
        bx = bp[b, js, None]
        boot_fits = [gmm(bx, k, n_init=5) for k in range(1, 5)]
        winner = int(np.argmin([f.bic(bx) for f in boot_fits]))
        chosen[winner + 1] += 1
        blabels = boot_fits[winner].predict(bx)
        coassignment += blabels[:, None] == blabels[None, :]
    coassignment /= CLUSTER_RESAMPLES
    result = {
        "model": saved["model"], "tasks": len(tasks), "attempts_per_task": 16,
        "source_sha256": {str(path.relative_to(ROOT)): digest(path) for path in (
            source, ROOT / "data/finetune/task-data/finetune.json",
            ROOT / "data/finetune/task-data/validation.json",
            ROOT / "data/finetune/task-data/metadata.json")},
        "frequency_note": "Rarity scores are the existing heuristic usage-frequency categories, not measured corpus frequencies. Dataset share is the observed fraction of these 6,687 tasks.",
        "uncertainty": {"method": "Percentile bootstrap of whole (dhatu citation, gana) groups",
                        "root_groups": len(roots), "resamples": RESAMPLES, "seed": SEED},
        "overall": summarize(p[0], bp[:, 0], n[0]), "options": options,
        "lakara_prayoga": interactions,
        "clustering": {
            "unit": "10 lakara option-level pass@1 means; each option has equal weight in GMM fitting",
            "method": "1D Gaussian mixture; BIC selects K from 1..4; variance floor 0.0001; 30 initializations",
            "candidate_bic": {str(k): float(bic) for k, bic in enumerate(bics, 1)},
            "selected_k": selected + 1, "groups": groups,
            "alternative_method": "Task-count-weighted K-means, K=2..5; select largest unweighted option-level silhouette",
            "kmeans_candidates": alternatives, "kmeans_best": alternative,
            "bootstrap_model_selection": {"resamples": CLUSTER_RESAMPLES, "gmm_initializations": 5,
                                          "k_counts": {str(k): chosen[k] for k in range(1, 5)},
                                          "option_order": names, "coassignment_probability": coassignment.tolist()},
            "interpretation": "Exploratory performance groups fitted to these same outcomes, not independently validated difficulty labels. AshirLin changes groups between GMM and K-means. Other dimensions have only three options, so no mixture model is fitted to them. Pooled data include original training tasks.",
        },
    }
    return result


def draw(result):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.titlesize": 17, "axes.labelsize": 12,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#c9d3dc", "text.color": INK,
                         "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK})
    fig = plt.figure(figsize=(22, 28), facecolor="#f8fafc")
    grid = fig.add_gridspec(5, 2, left=.065, right=.975, top=.905, bottom=.11,
                           hspace=.60, wspace=.22, height_ratios=[1, 1, 1, 1, 1.55])
    fig.suptitle("Frequency vs. morphology task performance", x=.065, y=.983,
                 ha="left", fontsize=32, fontweight="bold")
    fig.text(.065, .961, "GRPO-r3 · all 6,687 tasks · 16 completions/task · 106,992 completions",
             fontsize=17)
    fig.text(.065, .943, "Each dot is one morphology option. Bars: 95% intervals from 20,000 root-group bootstrap resamples. Dashed line: overall pass@1.", fontsize=12)
    legend = [Line2D([], [], marker="o", linestyle="", color=LOW, label="Lower-performing lakaras"),
              Line2D([], [], marker="o", linestyle="", color=HIGH, label="Higher-performing lakaras"),
              Line2D([], [], marker="o", linestyle="", color=MID, label="AshirLin: grouping depends on method")]
    fig.legend(handles=legend, loc="upper left", bbox_to_anchor=(.06, .936), frameon=False, ncol=3, fontsize=12)
    overall = 100 * result["overall"]["pass_at_1"]
    low_names = set(result["clustering"]["groups"][0]["members"])
    def color(dim, name):
        if dim != "lakara":
            return INK
        return MID if name == "AshirLin" else LOW if name in low_names else HIGH

    for row, (dim, title) in enumerate(DIMENSIONS.items()):
        items = result["options"][dim]
        names = list(items)
        for col in range(2):
            ax = fig.add_subplot(grid[row, col], facecolor="white")
            ax.set_title(title + (" | usage rarity" if col == 0 else " | dataset frequency"), loc="left", pad=17, fontweight="bold")
            x = np.array([items[name]["rarity_score"] if col == 0 else 100 * items[name]["dataset_share"] for name in names], dtype=float)
            if col == 0:
                for value in np.unique(x):
                    ties = np.flatnonzero(x == value)
                    if len(ties) > 1:
                        x[ties] += np.linspace(-.10, .10, len(ties))
                ax.set_xlim(.55, 5.45)
                ax.set_xticks(range(1, 6))
                ax.set_xlabel("Existing rarity score: 1 = frequent → 5 = rare")
            else:
                span = max(np.ptp(x), 1)
                ax.set_xlim(x.min() - .45 * span, x.max() + .45 * span)
                ax.set_xlabel("Share of the 6,687 tasks (%) · observed dataset frequency")
            ax.set_ylim(0, 101)
            ax.set_yticks(range(0, 101, 20))
            ax.set_ylabel("Pass@1 (%)")
            ax.grid(axis="y", color="#e5eaf0", zorder=0)
            ax.axhline(overall, color="#8494a6", linestyle=(0, (5, 4)), linewidth=1.1)
            ax.text(.985, .015, f"Overall {overall:.2f}%", transform=ax.transAxes, ha="right", fontsize=10, color="#67788c")
            texts = []
            ys = []
            for name, xx in zip(names, x):
                d = items[name]
                y = 100 * d["pass_at_1"]
                ys.append(y)
                ci = 100 * np.array(d["ci95"])
                c = color(dim, name)
                ax.errorbar(xx, y, yerr=[[y - ci[0]], [ci[1] - y]], fmt="none", ecolor=c,
                            elinewidth=1.7, capsize=4, zorder=3)
                ax.scatter(xx, y, s=15 + .008 * d["tasks"], color=c, edgecolor="white", linewidth=.7, zorder=4)
                texts.append(ax.text(xx, y + 5, f"{name}  {y:.1f}%\nn={d['tasks']:,}",
                                     ha="center", fontsize=11, linespacing=1.25, color=c,
                                     bbox={"facecolor": "white", "edgecolor": "none", "alpha": .88, "pad": 1.2}, zorder=5))
            np.random.seed(SEED)
            adjust_text(texts, x=x, y=ys, ax=ax, expand=(1.1, 1.15),
                        force_static=(.3, .5), force_text=(.4, .6),
                        arrowprops={"arrowstyle": "-", "color": "#a4b0be", "lw": .8},
                        min_arrow_len=5, iter_lim=250)

    # Interaction heatmap: every task appears in exactly one of these 30 cells.
    ax = fig.add_subplot(grid[4, 0], facecolor="white")
    ax.set_title("Where performance separates: lakara × prayoga", loc="left", pad=18, fontweight="bold")
    ordered = sorted(SCORES["lakara"], key=lambda name: result["options"]["lakara"][name]["pass_at_1"])
    voices = list(SCORES["prayoga"])
    cells = {(d["lakara"], d["prayoga"]): d for d in result["lakara_prayoga"]}
    values = np.array([[100 * cells[la, pr]["pass_at_1"] for pr in voices] for la in ordered])
    im = ax.imshow(values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(voices)), voices)
    ax.set_yticks(range(len(ordered)), ordered)
    ax.set_xlabel("Prayoga · each cell shows pass@1 and task count")
    for i, la in enumerate(ordered):
        for j, pr in enumerate(voices):
            d = cells[la, pr]
            ax.text(j, i, f"{100*d['pass_at_1']:.1f}%   ·   n={d['tasks']}", ha="center", va="center", fontsize=11, color="#172b36")
    ax.axhline(2.5, color="white", linewidth=3)
    for label in ax.get_yticklabels():
        label.set_color(color("lakara", label.get_text()))
    fig.colorbar(im, ax=ax, fraction=.025, pad=.025, label="Pass@1 (%)")

    # Keep a one-group candidate: this search does not force three difficulty tiers.
    subgrid = grid[4, 1].subgridspec(2, 1, height_ratios=[1.3, 1], hspace=.72)
    group_ax = fig.add_subplot(subgrid[0], facecolor="white")
    group_ax.set_title("Exploratory clusters of lakara accuracy", loc="left", fontweight="bold", pad=18)
    groups = result["clustering"]["groups"]
    for i, d in enumerate(groups):
        y = d["pass_at_1"] * 100
        ci = np.array(d["ci95"]) * 100
        c = LOW if i == 0 else HIGH
        group_ax.bar(i, y, width=.48, color=c, alpha=.88)
        group_ax.errorbar(i, y, yerr=[[y-ci[0]], [ci[1]-y]], fmt="none", color=INK, capsize=6, lw=1.7)
        group_ax.text(i, y + 5, f"{y:.2f}% · n={d['tasks']:,}", ha="center", fontsize=13, fontweight="bold", color=c)
    group_ax.set_ylim(0, 100)
    group_ax.set_xlim(-.6, len(groups)-.4)
    group_ax.set_ylabel("Pass@1 (%)")
    group_ax.set_xticks(range(len(groups)), ["Lower group\nLit · Lun · AshirLin", "Higher group\nThe other 7 lakaras"])
    group_ax.grid(axis="y", alpha=.15)
    group_ax.set_axisbelow(True)
    bic_ax = fig.add_subplot(subgrid[1], facecolor="white")
    bics = result["clustering"]["candidate_bic"]
    best = result["clustering"]["selected_k"]
    delta = np.array(list(bics.values())) - min(bics.values())
    bic_ax.bar(range(1, 5), delta, color=[HIGH if k == best else "#b6c4d1" for k in range(1, 5)], width=.5)
    bic_ax.scatter([best], [0], marker="*", s=180, color=HIGH, zorder=4)
    for k, value in enumerate(delta, 1):
        bic_ax.text(k, value + .25, f"{value:.2f}", ha="center", fontsize=11)
    bic_ax.set_ylim(-.5, max(delta) + 2)
    bic_ax.set_xticks(range(1, 5))
    bic_ax.set_xlabel("Number of Gaussian mixture groups (K)")
    bic_ax.set_ylabel("BIC above best\nLower is better")
    bic_ax.set_title(f"BIC selects K={best} from 1–4; only 10 option means", loc="left", fontsize=13, pad=12)

    choices = result["clustering"]["bootstrap_model_selection"]["k_counts"]
    bootstrap_text = " / ".join(f"K={k}: {v/CLUSTER_RESAMPLES:.0%}" for k, v in choices.items())
    notes = [
        "READING THE FREQUENCY AXES",
        "Left: the earlier 1–5 usage-rarity estimates, not measured corpus frequencies. Small horizontal offsets separate tied scores.",
        "Right: actual task share. Options are almost balanced by construction; these shares do not measure real-world Sanskrit usage. Dot area scales with task count.",
        "CLUSTER CHECK",
        f"GMM favors two broad performance groups. Repeating BIC selection on 200 root bootstraps: {bootstrap_text}.",
        "Weighted K-means also favors two groups, but places AshirLin in the higher group: its membership is method-sensitive. Lit and Lun remain the low core.",
        "Groups are exploratory and fitted to these outcomes. Group intervals condition on selected membership. Pooled data include 6,018 original training tasks.",
    ]
    for i, note in enumerate(notes):
        fig.text(.065, .087 - i * .0108, note, fontsize=10.8 if i not in (0, 3) else 11.5,
                 fontweight="bold" if i in (0, 3) else "normal", color=INK)
    target = ROOT / "benchmarks/frequency-vs-task-performance.png"
    fig.savefig(target, dpi=200, facecolor=fig.get_facecolor(), metadata={"Description": "All 6687 GRPO-r3 tasks, morphology frequency scores and observed task share versus pass@1, with exploratory lakara clustering."})
    plt.close(fig)
    return target


def write_report(result):
    lines = ["# Frequency versus task performance", "",
             "All 6,687 tasks and 106,992 saved completions are included. Pass@1 is the average of each task's 16-attempt success fraction.", "",
             result["frequency_note"], "",
             "Intervals use 20,000 bootstrap resamples of entire (citation, gana) root groups. These are marginal comparisons, not controlled causal effects.", "",
             "| Dimension | Option | Rarity | Tasks | Dataset share | Pass@1 | 95% CI |",
             "|---|---|---:|---:|---:|---:|---|"]
    for dim, options in result["options"].items():
        for name, d in options.items():
            lines.append(f"| {dim} | {name} | {d['rarity_score']} | {d['tasks']} | {100*d['dataset_share']:.2f}% | {100*d['pass_at_1']:.2f}% | {100*d['ci95'][0]:.2f}–{100*d['ci95'][1]:.2f}% |")
    c = result["clustering"]
    lines += ["", "## Exploratory clustering", "", c["unit"], "", c["method"], "",
              f"Selected K: **{c['selected_k']}**. Candidate BIC values: `{c['candidate_bic']}`.", ""]
    for group in c["groups"]:
        lines.append(f"- {', '.join(group['members'])}: **{100*group['pass_at_1']:.2f}%**, n={group['tasks']}; 95% CI {100*group['ci95'][0]:.2f}–{100*group['ci95'][1]:.2f}%.")
    lines += ["", f"Across {CLUSTER_RESAMPLES} root-bootstrap repeats, selected K counts: `{c['bootstrap_model_selection']['k_counts']}`.", "",
              c["alternative_method"], "", f"Best K-means result: `{c['kmeans_best']}`.", "",
              c["interpretation"], "",
              "The displayed pooled group rates weight tasks equally; GMM fitting weights the ten lakara option means equally. Cluster intervals condition on selected membership.", "",
              "The figure also shows all 30 lakara × prayoga cells; task counts, rates, and intervals are in the accompanying JSON.", "",
              "Reproduce with the command in `misc/plot_frequency_vs_task_performance.py`.", ""]
    (ROOT / "benchmarks/results/frequency-vs-task-performance.md").write_text("\n".join(lines))


def main():
    result = analyze()
    write_json(ROOT / "benchmarks/results/frequency-vs-task-performance.json", result)
    write_report(result)
    target = draw(result)
    print(json.dumps({"plot": str(target), "tasks": result["tasks"], "overall": result["overall"],
                      "cluster_bic": result["clustering"]["candidate_bic"],
                      "groups": result["clustering"]["groups"],
                      "bootstrap_k": result["clustering"]["bootstrap_model_selection"]["k_counts"]}, indent=2))


if __name__ == "__main__":
    main()
