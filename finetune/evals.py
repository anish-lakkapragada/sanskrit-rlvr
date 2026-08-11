"""Checkpoint evaluation suite. GPU-agnostic: everything works through a
``generate_fn(prompts, n, temperature, max_new_tokens) -> list[list[str]]``
abstraction (n completions per prompt), so the same code runs against the
trainer's vLLM engine, HF ``model.generate``, or a stub in tests.

Run ``python -m finetune.evals`` for the CPU-only self-test.
"""

import math
import random
from itertools import combinations

import numpy as np

from finetune.prompts import (
    extract_answer, extract_translation, render_translation, render_vp_task,
)


# --------------------------------------------------------------------------
# Pass@K
# --------------------------------------------------------------------------

def pass_at_k_estimate(n: int, c: int, k: int) -> float:
    """Unbiased pass@k (Chen et al. 2021): 1 - C(n-c, k) / C(n, k)."""
    if k > n:
        raise ValueError(f"k={k} > n={n} samples")
    if c == 0:
        return 0.0
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def reward_snapshot(rewards: list[float]) -> dict:
    arr = np.asarray([r for r in rewards if r is not None], dtype=float)
    if arr.size == 0:
        return {"n": 0, "mean": None, "std": None, "hist_bins": [], "hist_counts": []}
    counts, bins = np.histogram(arr, bins=20)
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "hist_bins": [float(b) for b in bins],
        "hist_counts": [int(c) for c in counts],
    }


def eval_pass_at_k(generate_fn, tasks: list[dict], reward_fn, *, ks: list[int],
                   samples_per_prompt: int, pass_threshold: float,
                   temperature: float, max_new_tokens: int,
                   num_prompts: int, rng: random.Random,
                   template: str = "v0/vp_task.txt"):
    """Sample tasks, draw n completions each, score with the SAME registry
    reward used in training, and report pass@k for each k plus the reward
    distribution and answer-tag compliance. ``template`` must match the
    prompt the model was trained on (SFT runs use the v1 corpus template)."""
    chosen = rng.sample(tasks, min(num_prompts, len(tasks)))
    prompts = [render_vp_task(t, template=template) for t in chosen]
    completions = generate_fn(prompts, samples_per_prompt, temperature, max_new_tokens)

    # One flat reward call, mirroring TRL's batching.
    flat_prompts, flat_completions, cols = [], [], {
        "id": [], "dhatu": [], "morphology": [],
        "gold_slp1": [], "gold_devanagari": [],
    }
    for task, prompt, comps in zip(chosen, prompts, completions):
        for c in comps:
            flat_prompts.append(prompt)
            flat_completions.append(c)
            for key in cols:
                cols[key].append(task[key])
    flat_rewards = reward_fn(flat_prompts, flat_completions, **cols)

    per_task, samples, i = [], [], 0
    for task, comps in zip(chosen, completions):
        rewards = flat_rewards[i:i + len(comps)]
        i += len(comps)
        c_pass = sum(1 for r in rewards if r is not None and r >= pass_threshold)
        per_task.append((len(comps), c_pass))
        samples.append({"id": task["id"], "completions": comps, "rewards": rewards})

    metrics = {
        f"pass_at_{k}": float(np.mean([pass_at_k_estimate(n, c, k) for n, c in per_task]))
        for k in ks
    }
    metrics["answer_tag_rate"] = float(np.mean(
        [1.0 if extract_answer(c) else 0.0 for c in flat_completions]))
    metrics["reward_snapshot"] = reward_snapshot(flat_rewards)
    return metrics, samples


# --------------------------------------------------------------------------
# Samayik chrF / chrF++
# --------------------------------------------------------------------------

def eval_samayik(generate_fn, pairs: list[dict], *, num_samples: int,
                 temperature: float, max_new_tokens: int, rng: random.Random):
    """EN->SA translation on a seeded Samayik subsample; chrF and chrF++ on
    the <translation>-extracted text (missing tags score as empty string,
    with compliance reported separately)."""
    from sacrebleu.metrics import CHRF

    chosen = rng.sample(pairs, min(num_samples, len(pairs)))
    prompts = [render_translation(p["en"]) for p in chosen]
    completions = generate_fn(prompts, 1, temperature, max_new_tokens)

    hyps, samples, tagged = [], [], 0
    for pair, comps in zip(chosen, completions):
        completion = comps[0]
        translation = extract_translation(completion)
        if translation:
            tagged += 1
        hyps.append(translation or "")
        samples.append({"en": pair["en"], "ref": pair["sa"],
                        "hyp": translation, "raw": completion})
    refs = [p["sa"] for p in chosen]

    metrics = {
        "chrf": float(CHRF().corpus_score(hyps, [refs]).score),
        "chrf_pp": float(CHRF(word_order=2).corpus_score(hyps, [refs]).score),
        "translation_tag_rate": tagged / len(chosen) if chosen else 0.0,
        "n": len(chosen),
    }
    return metrics, samples


# --------------------------------------------------------------------------
# Entropy helper (HF-generate scores; torch imported lazily)
# --------------------------------------------------------------------------

def mean_token_entropy(scores) -> float:
    """Mean per-token entropy (nats) from HF generate(..., output_scores=True)."""
    import torch

    ents = []
    for step_scores in scores:
        logp = torch.log_softmax(step_scores.float(), dim=-1)
        ents.append(-(logp.exp() * logp).nansum(-1).mean().item())
    return float(np.mean(ents)) if ents else 0.0


# --------------------------------------------------------------------------
# Self-test (CPU only): python -m finetune.evals
# --------------------------------------------------------------------------

def _brute_force_pass_at_k(n, c, k, trials=20000, seed=0):
    rng = random.Random(seed)
    outcomes = [1] * c + [0] * (n - c)
    hits = 0
    for _ in range(trials):
        if any(rng.sample(outcomes, k)):
            hits += 1
    return hits / trials


if __name__ == "__main__":
    # pass@k estimator vs brute force
    for n, c, k in [(8, 0, 4), (8, 8, 1), (8, 3, 2), (8, 1, 8), (10, 4, 3)]:
        exact = pass_at_k_estimate(n, c, k)
        approx = _brute_force_pass_at_k(n, c, k)
        assert abs(exact - approx) < 0.02, (n, c, k, exact, approx)
    print("pass@k estimator OK")

    # tag extraction
    assert extract_answer("<thinking>x</thinking><answer> भवति </answer>") == "भवति"
    assert extract_answer("no tags here") is None
    assert extract_answer("<answer>a</answer><answer>b</answer>") is None
    assert extract_translation("<translation>रामः वनं गच्छति।</translation>") == "रामः वनं गच्छति।"
    print("tag extraction OK")

    # end-to-end with a stub generator + the placeholder reward
    from finetune.data import load_vp_tasks
    from finetune.rewards import get

    tasks = load_vp_tasks("data/finetune/task-data/validation.json")
    stub = lambda prompts, n, temperature, max_new_tokens: [
        [f"<thinking>hm</thinking><answer>{t}</answer>"] * n for t in range(len(prompts))
    ]
    metrics, samples = eval_pass_at_k(
        stub, tasks, get("example"), ks=[1, 2], samples_per_prompt=2,
        pass_threshold=0.5, temperature=0.9, max_new_tokens=64,
        num_prompts=5, rng=random.Random(0))
    assert metrics["pass_at_1"] == 0.0 and metrics["answer_tag_rate"] == 1.0
    print("eval_pass_at_k OK:", {k: v for k, v in metrics.items() if k != "reward_snapshot"})

    from finetune.data import load_samayik_pairs
    pairs = load_samayik_pairs("data/eval/samayik.json")
    stub_tr = lambda prompts, n, temperature, max_new_tokens: [
        ["<thinking>...</thinking><translation>रामः वनं गच्छति।</translation>"] for _ in prompts
    ]
    metrics, _ = eval_samayik(stub_tr, pairs, num_samples=4, temperature=0.2,
                              max_new_tokens=64, rng=random.Random(0))
    assert metrics["translation_tag_rate"] == 1.0 and 0 <= metrics["chrf"] <= 100
    print("eval_samayik OK:", metrics)
    print("all self-tests passed")
