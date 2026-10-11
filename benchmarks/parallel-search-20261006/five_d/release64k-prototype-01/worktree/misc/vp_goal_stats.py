"""Uncertainty for a fixed benchmark: unique tasks and root-cluster resampling.

These are sampling-uncertainty estimates, not the variance of repeated model
calls. Exploration panels must never be presented as independent final tests.
"""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import NormalDist

import numpy as np


def wilson(correct, n, confidence=0.95, one_sided=False):
    if n <= 0 or not 0 <= correct <= n:
        raise ValueError("Invalid Bernoulli counts")
    z = NormalDist().inv_cdf(confidence if one_sided else (1 + confidence) / 2)
    p, zz = correct / n, z * z
    center = (p + zz / (2 * n)) / (1 + zz / n)
    radius = z * math.sqrt(p * (1 - p) / n + zz / (4 * n * n)) / (1 + zz / n)
    return [max(0.0, center - radius), min(1.0, center + radius)]


def accuracy_uncertainty(rows, *, repetitions=20000, seed=20261011):
    """Unweighted accuracy; sample root families jointly across all cells.

    Membership and weights are fixed inputs. A bootstrap draw samples the same
    number of families with replacement and retains every task in each family.
    The ratio of correct to total handles unequal family sizes. This preserves
    within-root dependence but does not establish independence between roots.
    """
    if not rows or repetitions < 1000:
        raise ValueError("Need scored rows and at least 1000 bootstrap draws")
    ids = [r["task"]["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Repeated completions do not increase unique task N")
    grouped = defaultdict(lambda: [0, 0])
    family_cohorts = {}
    has_multi_root = False
    for r in rows:
        if r.get("is_correct") not in (True, False):
            raise ValueError("Unscored infrastructure failures need reconciliation")
        root = r["task"]["campaign"]["root_family"]
        families = r['task']['campaign'].get('root_families', [root])
        has_multi_root |= len(families) > 1
        for family in families:
            if family in family_cohorts and family_cohorts[family] != root:
                raise ValueError('Overlapping dhatu cohorts require a dependency-aware uncertainty estimator')
            family_cohorts[family] = root
        grouped[root][0] += int(r["is_correct"])
        grouped[root][1] += 1
    counts = np.array([grouped[k] for k in sorted(grouped)], dtype=np.int64)
    k, n, correct = len(counts), len(rows), int(counts[:, 0].sum())
    p = correct / n
    rng = np.random.default_rng(seed)
    samples = []
    # Small chunks bound memory when a later release contains many families.
    for start in range(0, repetitions, 256):
        draws = counts[rng.integers(0, k, size=(min(256, repetitions - start), k))].sum(axis=1)
        samples.extend((draws[:, 0] / draws[:, 1]).tolist())
    cluster_se = float(np.std(samples, ddof=1)) if k > 1 else None
    residuals = counts[:, 0] - p * counts[:, 1]
    sandwich_se = math.sqrt(k / (k - 1) * float(residuals @ residuals)) / n if k > 1 else None
    iid_se = math.sqrt(p * (1 - p) / n)
    inflation = cluster_se ** 2 / iid_se ** 2 if iid_se > 0 and cluster_se is not None else None
    return {
        "n_unique": n, "root_families": len(family_cohorts), "correct": correct, "accuracy": p,
        "resampling_clusters": k,
        "resampling_unit": "disjoint dhatu cohorts" if has_multi_root else "dhatu family",
        "iid_standard_error": iid_se,
        "iid_wilson_95_interval": wilson(correct, n),
        "iid_wilson_95_one_sided_upper": wilson(correct, n, one_sided=True)[1],
        "root_cluster_bootstrap_standard_error": cluster_se,
        "root_cluster_sandwich_standard_error": sandwich_se,
        "root_cluster_bootstrap_95_interval": np.quantile(samples, [0.025, 0.975]).tolist() if k > 1 else None,
        "estimated_design_effect": inflation,
        "bootstrap_seed": seed, "bootstrap_repetitions": repetitions,
        "iid_n_for_strictly_below_one_percentage_point_se_at_observed_p": math.floor(p * (1 - p) / 0.0001) + 1,
        "iid_worst_case_n_for_strictly_below_one_percentage_point_se": 2501,
        "limitations": [
            "This estimates sampling uncertainty over tasks/families, not stochastic run-to-run variability.",
            "An observed SE below 1pp is not a guarantee for other models or generator distributions.",
            "Cluster intervals can degenerate when every family has the same result; inspect the Wilson interval too.",
            "The design effect cannot be assumed stable when increasing forms per root or changing task mixtures.",
            "Exploratory construction selection requires separate frozen validation; these intervals do not correct for selection."
        ],
    }
