#!/usr/bin/env python
"""Capability-shift vector figure.

Each fine-tuned model is drawn as a VECTOR in a 2-D capability space:
    x = change in EN->SA translation chrF   (vs the base model)
    y = change in vidyut-prakriya pass@16   (vs the base model)

Every arrow starts at the model it was fine-tuned FROM, so the arrow is the
shift that training actually produced:
  * base Qwen3-4B sits at the origin (0, 0);
  * all SFT arms depart the origin;
  * GRPO vp_exact departs SFT-R1-epoch-2, which is the checkpoint it was
    actually trained on -- so its arrow shows what 600 GRPO steps bought.

The seven mixture arms are joined by a frontier line in upsampling order.

chrF/chrF++ are computed over TAG-COMPLIANT completions only (a missing
<translation> tag would otherwise be scored as an empty string and conflate
translation quality with format compliance).

    uv run --with matplotlib --with sacrebleu python misc/plot_capability_vectors.py
"""

import json
import glob
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from sacrebleu.metrics import CHRF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "misc" / "figures" / "capability-vectors.png"

# --- design tokens (validated default palette; slots 1-3 clear all-pairs) ----
C_MIX, C_RL, C_SINGLE = "#2a78d6", "#eb6834", "#1baf7a"
C_RL2 = "#8a5cd6"  # GRPO round 2 (departs the 2x mixture checkpoint)
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"

MIX = ["0.5", "1", "2", "4", "6", "8", "10"]
MODELS = {
    "base":        ("prevals/outputs/prompt-v1/base-capability-sweep/qwen__qwen3-4b/summary.json",
                    "runs-rescued/base-qwen3-4b"),
    "sft-r1-e2":   ("prevals/outputs/prompt-v1/sft-epoch2-eval/qwen__qwen3-4b/summary.json",
                    "runs-rescued/sft-qwen3-4b-opus-r1-epoch2"),
    "grpo":        ("prevals/outputs/prompt-v1/grpo-exact-final-eval/*/summary.json",
                    "runs-rescued/grpo-exact-qwen3-4b-sft"),
    "std-samayik": ("prevals/outputs/prompt-v1/sft-standard-samayik-vp-eval/qwen__qwen3-4b/summary.json",
                    "runs-rescued/sft-qwen3-4b-standard-samayik"),
    "std-flores":  ("prevals/outputs/prompt-v1/sft-standard-flores-200-vp-eval/qwen__qwen3-4b/summary.json",
                    "runs-rescued/sft-qwen3-4b-standard-flores-200"),
    **{f"mix-{a}": (f"prevals/outputs/prompt-v1/mix-upsample-{a}-vp-eval/qwen__qwen3-4b/summary.json",
                    f"runs-rescued/sft-qwen3-4b-mix-upsample-{a}") for a in MIX},
    # GRPO round 2 (clean re-measurement 2026-08-23): best-of-20 checkpoints,
    # fresh merged bases; translations live in evals-best-clean/, not evals/.
    "grpo2-exact": ("prevals/outputs/prompt-v1/grpo2-exact-best-clean-vp-eval/*/summary.json",
                    "runs-rescued/grpo-exact-qwen3-4b-sft-mix-upsample-2", "evals-best-clean"),
    "grpo2-chrf":  ("prevals/outputs/prompt-v1/grpo2-chrf-best-clean-vp-eval/*/summary.json",
                    "runs-rescued/grpo-chrf-qwen3-4b-sft-mix-upsample-2", "evals-best-clean"),
}

_chrf, _chrfpp = CHRF(), CHRF(word_order=2)


def tag_conditional_chrf(run_dir: str, dataset: str, evals_dir: str = "evals") -> float:
    """chrF over completions that actually emitted a <translation> tag."""
    p = ROOT / run_dir / evals_dir / f"final-{dataset}.json"
    samples = json.loads(p.read_text())["samples"]
    kept = [s for s in samples if s["hyp"]]
    return _chrf.corpus_score([s["hyp"] for s in kept], [[s["ref"] for s in kept]]).score


def load() -> dict:
    out = {}
    for name, spec in MODELS.items():
        spath, run = spec[0], spec[1]
        evals_dir = spec[2] if len(spec) > 2 else "evals"
        hits = glob.glob(str(ROOT / spath))
        p16 = json.loads(Path(hits[0]).read_text())["pass_at_k"]["16"] * 100
        out[name] = {
            "p16": p16,
            "samayik": tag_conditional_chrf(run, "samayik", evals_dir),
            "flores-200": tag_conditional_chrf(run, "flores-200", evals_dir),
        }
    return out


def draw(ax, D, dataset, title, xlim, single_labels, rl2_labels):
    base = D["base"]
    dx = lambda m: D[m][dataset] - base[dataset]
    dy = lambda m: D[m]["p16"] - base["p16"]
    pts = [(dx(f"mix-{a}"), dy(f"mix-{a}")) for a in MIX]

    ax.set_facecolor(SURFACE)
    ax.axhline(0, color=AXIS, lw=1, zorder=1)
    ax.axvline(0, color=AXIS, lw=1, zorder=1)
    ax.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)

    def arrow(a, tail, tip, color, lw=1.8, alpha=1.0, z=3):
        a.annotate("", xy=tip, xytext=tail, zorder=z,
                   arrowprops=dict(arrowstyle="-|>,head_width=0.20,head_length=0.45",
                                   color=color, lw=lw, alpha=alpha, shrinkA=0, shrinkB=0))

    # --- single-task SFT baselines (from origin) ---------------------------
    for m, lab, off, ha, va in single_labels:
        arrow(ax, (0, 0), (dx(m), dy(m)), C_SINGLE, alpha=0.9)
        ax.plot([dx(m)], [dy(m)], "o", ms=8, color=C_SINGLE, mec=SURFACE, mew=1.4, zorder=4)
        ax.annotate(lab, (dx(m), dy(m)), textcoords="offset points", xytext=off,
                    ha=ha, va=va, fontsize=9, color=INK2, zorder=6)

    # --- the RL step: departs SFT-R1-e2, not the origin. Markers kept small
    #     so the (very short) arrow between them is not swallowed by them.
    gdx, gdy = dx("grpo") - dx("sft-r1-e2"), dy("grpo") - dy("sft-r1-e2")
    arrow(ax, (dx("sft-r1-e2"), dy("sft-r1-e2")), (dx("grpo"), dy("grpo")),
          C_RL, lw=2.6, z=8)
    ax.plot([dx("grpo")], [dy("grpo")], "o", ms=6, color=C_RL, mec=SURFACE, mew=1.2, zorder=9)
    ax.annotate(f"GRPO vp_exact — 600 RL steps\nΔ = {gdx:+.2f} chrF,  {gdy:+.2f} pp",
                (dx("grpo"), dy("grpo")), textcoords="offset points", xytext=(10, 26),
                ha="left", va="bottom", fontsize=9, color=C_RL, zorder=9,
                arrowprops=dict(arrowstyle="-", color=C_RL, lw=0.9, alpha=0.8,
                                shrinkA=2, shrinkB=4))

    # --- GRPO round 2: both arms depart the 2x mixture checkpoint. The true
    #     deltas are sub-pixel at this scale (|Δ| <= 0.6 chrF, <= 1.2 pp), so
    #     the arrows are drawn magnified x8 — direction exact, tip at 8x the
    #     true displacement, true Δ printed on each label.
    # Labels are pinned at fixed AXES-FRACTION spots in the empty mid-right band
    # (all data in these panels lives at y<8 or y>77, x<len(cluster)), with thin
    # leaders to each arrow tip — placement is independent of data geometry.
    G2_SCALE = 12
    tail = (dx("mix-2"), dy("mix-2"))
    for m, lab, frac in rl2_labels:
        g2dx, g2dy = dx(m) - tail[0], dy(m) - tail[1]
        tip = (tail[0] + G2_SCALE * g2dx, tail[1] + G2_SCALE * g2dy)
        arrow(ax, tail, tip, C_RL2, lw=3.0, z=8)
        ax.annotate(f"{lab} ×{G2_SCALE}\nΔ = {g2dx:+.2f} chrF,  {g2dy:+.2f} pp",
                    xy=tip, xycoords="data",
                    xytext=frac, textcoords="axes fraction",
                    ha="right", va="top", fontsize=9, color=C_RL2, zorder=9,
                    arrowprops=dict(arrowstyle="-", color=C_RL2, lw=0.9, alpha=0.8,
                                    shrinkA=2, shrinkB=3))

    # --- mixture sweep: faint arrows from origin + solid frontier ----------
    for (x, y) in pts:
        arrow(ax, (0, 0), (x, y), C_MIX, lw=1.2, alpha=0.28, z=2)
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=C_MIX, lw=2.4,
            alpha=0.95, zorder=4, solid_capstyle="round")
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "o", ms=8, color=C_MIX,
            mec=SURFACE, mew=1.4, zorder=5)

    # --- base model at the origin -----------------------------------------
    ax.plot([0], [0], "o", ms=11, color=SURFACE, mec=INK, mew=2, zorder=6)
    ax.annotate("base Qwen3-4B  (0, 0)", (0, 0), textcoords="offset points",
                xytext=(11, -13), ha="left", va="top", fontsize=9,
                color=INK, fontweight="bold", zorder=7)

    ax.set_xlim(*xlim)
    ax.set_ylim(-8, 104)
    ax.set_title(title, fontsize=11, color=INK, pad=9, loc="left")
    ax.set_xlabel(f"Δ translation chrF vs base   ({dataset})", fontsize=10, color=INK2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)


def draw_zoom(ax, D, dataset, title, offsets, xlim, source_file):
    """Detail panel: the mixture frontier alone, with room for direct labels."""
    base = D["base"]
    dx = lambda m: D[m][dataset] - base[dataset]
    dy = lambda m: D[m]["p16"] - base["p16"]
    pts = [(dx(f"mix-{a}"), dy(f"mix-{a}")) for a in MIX]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]

    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)

    # VERTICAL bars: where the single-task translation SFTs land on the x axis.
    # Out-of-range ones become an edge marker so the frontier keeps its scale.
    for m, lab in [("std-samayik", "SFT samayik-only"), ("std-flores", "SFT flores-only")]:
        v = dx(m)
        if xlim[0] < v < xlim[1]:
            ax.axvline(v, color=C_SINGLE, lw=1.5, ls=(0, (5, 4)), alpha=0.85, zorder=1)
            ax.annotate(f"{lab}  chrF {D[m][dataset]:.2f}", (v, 0.015),
                        xycoords=("data", "axes fraction"), textcoords="offset points",
                        xytext=(-5, 0), rotation=90, ha="right", va="bottom",
                        fontsize=8.5, color=C_SINGLE, zorder=6)
        else:
            arrow = "→" if v >= xlim[1] else "←"
            ax.annotate(f"{lab} {arrow} off-scale at Δ{v:+.2f} (chrF {D[m][dataset]:.2f})",
                        (0.008, 0.02), xycoords="axes fraction", ha="left", va="bottom",
                        fontsize=8.5, color=C_SINGLE, alpha=0.95, zorder=6)

    # horizontal reference lines: the RL model and its SFT parent on pass@16
    for m, lab, col in [("grpo", "GRPO vp_exact pass@16", C_RL),
                        ("sft-r1-e2", "SFT R1 epoch 2 pass@16", C_SINGLE)]:
        ax.axhline(dy(m), color=col, lw=1.5, ls=(0, (5, 4)), alpha=0.85, zorder=1)
        ax.annotate(f"{lab} = {D[m]['p16']:.2f}", (0.008, dy(m)), xycoords=("axes fraction", "data"),
                    textcoords="offset points", xytext=(0, 4), ha="left", va="bottom",
                    fontsize=8.5, color=col, zorder=6)

    ax.plot(xs, ys, "-", color=C_MIX, lw=2.6, zorder=3, solid_capstyle="round")
    ax.plot(xs, ys, "o", ms=10, color=C_MIX, mec=SURFACE, mew=1.6, zorder=4)
    for i, a in enumerate(MIX):
        knee = a == "2"
        ox, oy = offsets[a]
        ax.annotate(f"{a}×" + ("  ← knee" if knee else ""), (xs[i], ys[i]),
                    textcoords="offset points", xytext=(ox, oy),
                    ha="left" if ox > 0 else ("right" if ox < 0 else "center"),
                    va="bottom" if oy > 0 else ("top" if oy < 0 else "center"),
                    fontsize=10, color=INK if knee else INK2,
                    fontweight="bold" if knee else "normal", zorder=6)

    my = (max(ys) - min(ys)) * 0.14 + 1.2
    ax.set_xlim(*xlim)
    ax.set_ylim(min(ys) - my, max(ys) + my)

    ax.set_title(title, fontsize=11, color=INK, pad=9, loc="left")
    ax.set_title(f"chrF from {source_file}", fontsize=8, color=MUTED,
                 pad=9, loc="right", family="monospace")
    ax.set_xlabel(f"Δ translation chrF vs base   ({dataset})", fontsize=10, color=INK2)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=9)


def main():
    D = load()
    # x-spans 45 : 28 in both rows, and width_ratios matched to them, so one
    # chrF unit is the same physical width in all four panels.
    fig, axes = plt.subplots(2, 2, figsize=(16.5, 13.2),
                             gridspec_kw=dict(height_ratios=[1.15, 1],
                                              width_ratios=[45, 28]))
    fig.patch.set_facecolor(SURFACE)

    draw(axes[0][0], D, "samayik", "Samayik  ·  in-domain for the mixture arms",
         xlim=(-11, 34),
         single_labels=[
             ("std-samayik", "SFT samayik-only", (0, 13), "center", "bottom"),
             ("std-flores", "SFT flores-only", (0, 13), "center", "bottom"),
             ("sft-r1-e2", "SFT R1 epoch 2\n(morphology-only)", (10, -14), "left", "top"),
         ],
         rl2_labels=[
             ("grpo2-chrf",  "GRPO r2 vp_chrf", (0.985, 0.74)),
             ("grpo2-exact", "GRPO r2 vp_exact", (0.985, 0.63)),
         ])
    draw(axes[0][1], D, "flores-200", "FLORES-200  ·  out-of-domain, held out of all training",
         xlim=(-13, 15),
         single_labels=[
             ("std-samayik", "SFT samayik-only", (-8, 13), "center", "bottom"),
             ("std-flores", "SFT flores-only", (8, 13), "center", "bottom"),
             ("sft-r1-e2", "SFT R1 epoch 2\n(morphology-only)", (10, -14), "left", "top"),
         ],
         rl2_labels=[
             ("grpo2-chrf",  "GRPO r2 vp_chrf", (0.985, 0.74)),
             ("grpo2-exact", "GRPO r2 vp_exact", (0.985, 0.63)),
         ])
    axes[0][0].set_ylabel("Δ vidyut-prakriya pass@16 vs base   (percentage points)",
                          fontsize=10, color=INK2)
    axes[0][1].tick_params(labelleft=False)

    draw_zoom(axes[1][0], D, "samayik", "Mixture frontier  ·  Samayik",
              offsets={"0.5": (0, -16), "1": (12, -4), "2": (10, 6),
                       "4": (-4, -17), "6": (10, -8), "8": (6, 11), "10": (-8, 9)},
              xlim=(19.0, 27.2), source_file="data/eval/samayik.json")
    draw_zoom(axes[1][1], D, "flores-200", "Mixture frontier  ·  FLORES-200",
              offsets={"0.5": (0, -16), "1": (12, 8), "2": (11, 3),
                       "4": (6, -15), "6": (11, -7), "8": (12, 1), "10": (-10, 9)},
              xlim=(-0.30, 4.80), source_file="data/eval/flores-200.json")
    axes[1][0].set_ylabel("Δ vidyut-prakriya pass@16 vs base   (percentage points)",
                          fontsize=10, color=INK2)

    handles = [
        Line2D([], [], color=C_MIX, lw=2.4, marker="o", ms=8, mec=SURFACE, mew=1.4,
               label="Mixture sweep — translation + morphology traces; frontier joins upsample ratios"),
        Line2D([], [], color=C_RL, lw=2.6, marker="o", ms=7, mec=SURFACE, mew=1.2,
               label="GRPO vp_exact — vector measured from its parent, SFT R1 epoch 2"),
        Line2D([], [], color=C_RL2, lw=2.6, marker="o", ms=7, mec=SURFACE, mew=1.2,
               label="GRPO round 2 (vp_exact / vp_chrf) — from their parent, 2× mixture; arrows ×12, true Δ printed"),
        Line2D([], [], color=C_SINGLE, lw=1.8, marker="o", ms=8, mec=SURFACE, mew=1.4,
               label="Single-task SFT baselines"),
        Line2D([], [], color=INK, lw=0, marker="o", ms=9, mfc=SURFACE, mew=2,
               label="base Qwen3-4B (origin)"),
    ]
    fig.legend(handles=handles, loc="upper left", ncol=2, frameon=False,
               fontsize=9.5, labelcolor=INK2, bbox_to_anchor=(0.005, 0.962),
               handletextpad=0.7, columnspacing=2.6)
    fig.suptitle("Direction and magnitude of capability shift from the base model",
                 fontsize=15, color=INK, x=0.005, ha="left", y=0.992, fontweight="bold")
    fig.text(0.005, 0.971,
             "Up = better Sanskrit grammar derivation · Right = better English→Sanskrit translation. "
             "Every arrow starts at the checkpoint the model was fine-tuned from.",
             fontsize=10, color=INK2, ha="left", va="top")
    fig.text(0.005, 0.012,
             "chrF over tag-compliant completions only (500 seed-42 pairs per dataset, temp 0.2, 4096 max new tokens). "
             "pass@16 on 669 held-out dhatu tasks × 16 samples; pass = exact match.  "
             "Base pass@16 is 0.00% (0/128 solved in the base-capability sweep), so Δpass@16 equals absolute pass@16.  "
             "Mixture arms use LoRA r=64; earlier baselines r=32.  "
             "GRPO r2 = best-of-20 probe checkpoints, re-measured on fresh merged bases (2026-08-23).",
             fontsize=8, color=MUTED, ha="left", va="bottom")
    fig.subplots_adjust(left=0.055, right=0.995, top=0.895, bottom=0.055,
                        wspace=0.07, hspace=0.30)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, facecolor=SURFACE)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
