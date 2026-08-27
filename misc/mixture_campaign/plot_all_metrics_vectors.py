#!/usr/bin/env python
"""Quad capability plot for the fixed-token-budget mixture campaign.

Four panels, one per Samayik translation metric on the x-axis (delta vs base):
chrF and chrF++ (tag-conditional, sacrebleu over final-samayik.json samples)
and GEMBA-DA_ref / GEMBA-MQM (judge claude-opus-5, misc/gemba/results/summary.json).
y (shared) = delta vp-task pass@K vs base (percentage points, 669x16).

Visual language matches plot_mixture_vectors.py: color = token budget, marker
shape = samayik share, dashed horizontal lines = the 0%-samayik arms' pass@K
levels (their translation scores sit far left of the mixtures on every metric),
black "P" = GRPO round-3 final with an arrow from its 20M-67% SFT start. The
four near-vertical arrows are the point of the figure: RL moves straight up on
every translation metric.

Usage:
  uv run --with matplotlib python misc/mixture_campaign/plot_all_metrics_vectors.py \
      --metric 16 --out misc/figures/all-metrics/data-mixture-vectors.png
"""

import argparse
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from sacrebleu.metrics import CHRF

SURFACE, GRID, AXIS = "#fcfcfb", "#e1e0d9", "#c3c2b7"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
SERIES = {"10m": "#2a78d6", "15m": "#eb6834", "20m": "#1baf7a"}
MARKER = {100: ("o", 11), 67: ("s", 10), 50: ("^", 13), 33: ("*", 18)}
MIX_SHARES = (100, 67, 50, 33)
CHRF6, CHRFPP = CHRF(), CHRF(word_order=2)

GRPO_DIR = "runs-final/grpo-r3-finals-results/finals/final731-translation"
GEMBA_SUMMARY = Path("misc/gemba/results/summary.json")
# full-set GRPO round-3 final pass rates (669x16), as in the single-metric figure
GRPO_PASS = {"16": 87.89, "1": 62.45}

PANELS = [  # (title, x-label stub, extractor key)
    ("Samayik chrF", "Δ chrF (tag-conditional)", "chrf"),
    ("Samayik chrF++", "Δ chrF++ (tag-conditional)", "chrfpp"),
    ("GEMBA-DA_ref", "Δ DA_ref mean (0–100, judge: Opus 5)", "da"),
    ("GEMBA-MQM", "Δ MQM mean (−25…0, judge: Opus 5)", "mqm"),
]


def chrf_pair(eval_dir: str):
    f = Path(eval_dir) / "final-samayik.json"
    if not f.exists():
        return None
    kept = [s for s in json.loads(f.read_text())["samples"] if s["hyp"]]
    if not kept:
        return (0.0, 0.0)
    hyps, refs = [s["hyp"] for s in kept], [[s["ref"] for s in kept]]
    return (CHRF6.corpus_score(hyps, refs).score, CHRFPP.corpus_score(hyps, refs).score)


def passk(suite: str, k: str):
    hits = glob.glob(f"runs-final/data-mixture/{suite}/*/summary.json")
    if not hits:
        return None
    return 100 * json.loads(Path(hits[0]).read_text())["pass_at_k"][k]


def load_models():
    """model key -> dict(chrf, chrfpp, da, mqm) translation metrics (Samayik)."""
    gemba = json.loads(GEMBA_SUMMARY.read_text())["summary"]

    def entry(gemba_key, eval_dir):
        pair = chrf_pair(eval_dir)
        return {"chrf": pair[0], "chrfpp": pair[1],
                "da": gemba[f"da|smk|{gemba_key}"]["mean"],
                "mqm": gemba[f"mqm|smk|{gemba_key}"]["mean"]}

    models = {"base": entry("base", "runs-final/base-qwen3-4b/evals-final")}
    for b in (10, 15, 20):
        for s in (100, 67, 50, 33, 0):
            models[f"t{b}s{s}"] = entry(
                f"t{b}s{s}", f"runs-final/sft-qwen3-4b-tb{b}m-samayik{s}/evals-final")
    models["grpo"] = entry("grpo", GRPO_DIR)
    return models


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--metric", default="16", choices=["1", "16"])
    ap.add_argument("--out", default="misc/figures/all-metrics/data-mixture-vectors.png")
    args = ap.parse_args()
    K = args.metric

    models = load_models()
    base_p = passk("dm-base-qwen3-4b", K)
    assert base_p is not None, "base pass@k eval missing"
    pk = {"base": base_p, "grpo": GRPO_PASS[K]}
    for b in (10, 15, 20):
        for s in (100, 67, 50, 33, 0):
            p = passk(f"dm-tb{b}m-samayik{s}", K)
            if p is not None:
                pk[f"t{b}s{s}"] = p

    fig, axes = plt.subplots(2, 2, figsize=(15.5, 10.8), dpi=200, sharey=True)
    fig.patch.set_facecolor(SURFACE)

    levels = {b: pk[f"t{b}s0"] - base_p for b in (10, 15, 20) if f"t{b}s0" in pk}

    for pi, (ax, (title, xlabel, mkey)) in enumerate(zip(axes.flat, PANELS)):
        ax.set_facecolor(SURFACE)
        base_x = models["base"][mkey]

        for b, y in levels.items():
            ax.axhline(y, color=SERIES[f"{b}m"], lw=1.6, ls=(0, (7, 5)),
                       alpha=0.75, zorder=1)

        xs_all = []
        for b in (10, 15, 20):
            color = SERIES[f"{b}m"]
            seq = [(s, models[f"t{b}s{s}"][mkey] - base_x, pk[f"t{b}s{s}"] - base_p)
                   for s in MIX_SHARES if f"t{b}s{s}" in pk]
            xs_all += [p[1] for p in seq]
            if len(seq) > 1:
                ax.plot([p[1] for p in seq], [p[2] for p in seq], color=color,
                        lw=2.2, zorder=2, solid_capstyle="round")
            for s, x, y in seq:
                m, size = MARKER[s]
                ax.plot([x], [y], marker=m, ms=size, color=color, lw=0,
                        markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=3)

        gx = models["grpo"][mkey] - base_x
        gy = GRPO_PASS[K] - base_p
        sx = models["t20s67"][mkey] - base_x
        sy = pk["t20s67"] - base_p
        ax.annotate("", xy=(gx, gy), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.5,
                                    shrinkA=5, shrinkB=6, mutation_scale=12))
        ax.plot([gx], [gy], marker="P", ms=13, color=INK,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=5)
        ax.annotate("GRPO r3", (gx, gy), xytext=(gx, gy - 10), fontsize=9,
                    color=INK, ha="center", zorder=6,
                    bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.2))

        lo, hi = min(xs_all), max(xs_all)
        pad = 0.10 * (hi - lo) or 1.0
        ax.set_xlim(lo - pad, hi + pad)
        ax.margins(y=0.14)
        ax.axhline(0, color=AXIS, lw=1, zorder=1)
        ax.grid(color=GRID, lw=0.6, zorder=0)
        for spine in ax.spines.values():
            spine.set_color(AXIS)
        ax.tick_params(colors=MUTED, labelsize=9.5)
        ax.set_title(title, color=INK, fontsize=12, pad=8)
        ax.set_xlabel(xlabel + f"   (base = {base_x:.2f})", color=INK2,
                      fontsize=10, labelpad=7)
        if pi % 2 == 0:
            ax.set_ylabel(f"Δ vp-task pass@{K} vs base (pp)", color=INK2,
                          fontsize=10.5, labelpad=8)

    handles = ([Line2D([], [], color=c, lw=3, label=f"{b[:-1]}M tokens")
                for b, c in SERIES.items()]
               + [Line2D([], [], color=MUTED, lw=0, marker=MARKER[s][0],
                         ms=MARKER[s][1] * 0.8, markeredgecolor=SURFACE,
                         markeredgewidth=1.2, label=f"{s}% samayik")
                  for s in MIX_SHARES]
               + [Line2D([], [], color=MUTED, lw=1.6, ls=(0, (7, 5)),
                         label=f"0% samayik (pass@{K} level)"),
                  Line2D([], [], color=INK, lw=0, marker="P", ms=10,
                         markeredgecolor=SURFACE, label="GRPO r3 final")])
    leg = fig.legend(handles=handles, loc="lower center", ncol=9, frameon=False,
                     fontsize=9.5, bbox_to_anchor=(0.5, 0.015))
    for t in leg.get_texts():
        t.set_color(INK2)

    fig.suptitle("Mixture capability gains over base across four translation metrics"
                 f" — Samayik, y = Δ vp pass@{K}", color=INK, fontsize=14.5, y=0.985)
    fig.text(0.5, 0.058,
             "base Qwen3-4B = origin per panel; dashed lines = pure-trace (0% samayik) arms, whose "
             "translation scores sit far left of every panel; GEMBA judge = claude-opus-5",
             ha="center", color=MUTED, fontsize=9)
    fig.subplots_adjust(left=0.055, right=0.985, top=0.925, bottom=0.115,
                        hspace=0.30, wspace=0.06)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=SURFACE, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
