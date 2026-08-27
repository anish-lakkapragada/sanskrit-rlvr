#!/usr/bin/env python
"""Capability plot for the fixed-token-budget mixture campaign.

x = delta samayik chrF (TAG-CONDITIONAL, eval/samayik-eval.json) vs the base
model; y = delta vp-task pass@16 (percentage points, 669x16 on
eval/vp-eval.json) vs base. Base Qwen3-4B is the origin of both axes.

Color = token budget, marker shape = samayik share, and the line through each
budget's mixture points is its frontier. The 0%-samayik (pure morphology
trace) arms are drawn only as dashed pass@16 LEVEL lines: their chrF sits ~30
points left of everything else, so plotting them as points would squash the
mixtures into a corner, and the interesting question about them is only
"how much task capability does an all-trace budget buy?".

Usage: uv run --with matplotlib python misc/mixture_campaign/plot_mixture_vectors.py
Missing arms are skipped so the figure can be regenerated incrementally.
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
# Four silhouettes that stay distinct at a glance and in grayscale/CVD:
# round / blocky / pointy / spiky.
MARKER = {100: ("o", 13), 67: ("s", 12), 50: ("^", 15), 33: ("*", 22)}
MIX_SHARES = (100, 67, 50, 33)
_CHRF = CHRF()


def samayik_chrf_tagcond(root: Path, run_dir: str):
    f = root / run_dir / "evals-final" / "final-samayik.json"
    if not f.exists():
        return None
    samples = json.loads(f.read_text())["samples"]
    kept = [s for s in samples if s["hyp"]]
    if not kept:
        return 0.0
    return _CHRF.corpus_score([s["hyp"] for s in kept],
                              [[s["ref"] for s in kept]]).score


def passk(root: Path, suite: str, k: str):
    hits = glob.glob(str(root / "data-mixture" / suite / "*" / "summary.json"))
    if not hits:
        return None
    return 100 * json.loads(Path(hits[0]).read_text())["pass_at_k"][k]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="runs-final")
    ap.add_argument("--out", default="misc/figures/data-mixture-vectors.png")
    ap.add_argument("--metric", default="16", choices=["1", "16"],
                    help="pass@k for the y-axis")
    args = ap.parse_args()
    K = args.metric
    # full-set GRPO round-3 final numbers per metric
    GRPO_Y = {"16": 87.89, "1": 62.45}[K]
    root = Path(args.root)

    base_chrf = samayik_chrf_tagcond(root, "base-qwen3-4b")
    base_p16 = passk(root, "dm-base-qwen3-4b", K)
    assert base_chrf is not None and base_p16 is not None, "base evals missing"

    mixtures, levels = {}, {}
    for budget in SERIES:
        for share in MIX_SHARES:
            c = samayik_chrf_tagcond(root, f"sft-qwen3-4b-tb{budget}-samayik{share}")
            p = passk(root, f"dm-tb{budget}-samayik{share}", K)
            if c is not None and p is not None:
                mixtures[(budget, share)] = (c - base_chrf, p - base_p16)
        p0 = passk(root, f"dm-tb{budget}-samayik0", K)
        if p0 is not None:
            levels[budget] = p0 - base_p16

    fig, ax = plt.subplots(figsize=(12.4, 8.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    for budget, color in SERIES.items():
        if budget in levels:
            ax.axhline(levels[budget], color=color, lw=1.8, ls=(0, (7, 5)),
                       alpha=0.75, zorder=1)

    xs_all = []
    for budget, color in SERIES.items():
        seq = [(s, *mixtures[(budget, s)]) for s in MIX_SHARES
               if (budget, s) in mixtures]
        if not seq:
            continue
        xs_all += [p[1] for p in seq]
        if len(seq) > 1:
            ax.plot([p[1] for p in seq], [p[2] for p in seq], color=color,
                    lw=2.5, zorder=2, solid_capstyle="round")
        for share, x, y in seq:
            m, size = MARKER[share]
            ax.plot([x], [y], marker=m, ms=size, color=color, lw=0,
                    markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=3)

    # Room on the right for the level-line callouts.
    lo, hi = min(xs_all), max(xs_all)
    ax.set_xlim(lo - 0.7, hi + 1.7)
    ax.margins(y=0.13)

    # Value callouts on the dashed levels: alternate x by rank so vertically
    # close lines never share a label column; a surface bbox masks the dashes.
    for rank, (budget, y) in enumerate(sorted(levels.items(), key=lambda kv: kv[1])):
        x = ax.get_xlim()[1] - (0.15 if rank % 2 == 0 else 2.6)
        ax.text(x, y, f"{budget[:-1]}M · 0% samayik: {y + base_p16:.1f}%", ha="right",
                va="center", fontsize=9, color=INK2, zorder=4,
                bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.6))

    # GRPO round-3 final policy (one vp_exact epoch on the 20M-67% arm):
    # full-set 62.45 pass@1 / 87.89 pass@16 / samayik chrF 41.27 tag-cond.
    gx, gy = 41.27 - base_chrf, GRPO_Y - base_p16
    if ("20m", 67) in mixtures:
        px, py = mixtures[("20m", 67)]
        ax.annotate("", xy=(gx, gy), xytext=(px, py),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6,
                                    shrinkA=6, shrinkB=7, mutation_scale=13))
    ax.plot([gx], [gy], marker="P", ms=15, color=INK,
            markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=5)
    ax.annotate(f"GRPO r3 (1 epoch on 20M·67%)\npass@{K} {GRPO_Y:.1f} · chrF intact",
                (gx, gy), xytext=(gx + 0.55, gy - 11), fontsize=9, color=INK,
                ha="left")

    ax.axhline(0, color=AXIS, lw=1, zorder=1)
    ax.grid(color=GRID, lw=0.6, zorder=0)
    for spine in ax.spines.values():
        spine.set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=10)

    ax.set_xlabel("Δ Samayik chrF vs base   (tag-conditional, 750-pair eval)",
                  color=INK2, fontsize=11, labelpad=9)
    ax.set_ylabel(f"Δ vp-task pass@{K} vs base   (percentage points, 669 × 16)",
                  color=INK2, fontsize=11, labelpad=9)
    ax.set_title("SFT data-mixture capability gains over base — fixed token budgets",
                 color=INK, fontsize=14, pad=16)

    budget_key = [Line2D([], [], color=c, lw=3, label=f"{b[:-1]}M tokens")
                  for b, c in SERIES.items()]
    share_key = [Line2D([], [], color=MUTED, lw=0, marker=MARKER[s][0],
                        ms=MARKER[s][1] * 0.85, markeredgecolor=SURFACE,
                        markeredgewidth=1.4, label=f"{s}% samayik")
                 for s in MIX_SHARES]
    share_key.append(Line2D([], [], color=MUTED, lw=1.8, ls=(0, (7, 5)),
                            label=f"0% samayik (pass@{K} level)"))

    leg1 = ax.legend(handles=budget_key, loc="upper left", frameon=False,
                     fontsize=11, title="token budget", title_fontsize=10,
                     bbox_to_anchor=(0.015, 0.44), labelcolor=INK2)
    leg1.get_title().set_color(MUTED)
    ax.add_artist(leg1)
    leg2 = ax.legend(handles=share_key, loc="upper left", frameon=False,
                     fontsize=11, title="samayik share of the budget",
                     title_fontsize=10, bbox_to_anchor=(0.015, 0.28),
                     labelcolor=INK2)
    leg2.get_title().set_color(MUTED)

    fig.text(0.5, 0.012,
             f"base Qwen3-4B = origin (Samayik chrF {base_chrf:.2f}, "
             f"pass@{K} {base_p16:.2f}%); dashed levels are the pure-trace arms, "
             f"whose Samayik chrF lands ~30 points left of this view",
             ha="center", color=MUTED, fontsize=9)

    fig.subplots_adjust(left=0.075, right=0.985, top=0.915, bottom=0.115)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=SURFACE, bbox_inches="tight")
    print(f"wrote {out} ({len(mixtures)} mixture points, {len(levels)} level "
          f"lines; base origin = chrF {base_chrf:.2f}, pass@16 {base_p16:.2f}%)")


if __name__ == "__main__":
    main()
