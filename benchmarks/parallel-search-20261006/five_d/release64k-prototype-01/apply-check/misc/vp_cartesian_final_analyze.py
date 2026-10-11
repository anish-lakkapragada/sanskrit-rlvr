"""Offline analysis of a complete, frozen Cartesian release across payment stages.

Never selects, replaces, filters, or submits questions. Partial evaluations stay
partial even when an interim score happens to meet the target.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_cartesian_analyze import completed
from misc.vp_cartesian_release import audit_partition
from misc.vp_goal_stats import wilson


def panel_statistics(tasks, rows, *, repetitions=20000, seed=2026100708):
    """Retain zero-completion families in the completed-answer ratio estimator."""
    if repetitions < 1000:
        raise ValueError('Use at least 1000 bootstrap draws')
    expected = {t['id']: t for t in tasks}
    if len(expected) != len(tasks) or not tasks:
        raise ValueError('Fixed membership must be nonempty and unique')
    observed = {}
    for row in rows:
        key = row['task']['id']
        if key in observed or key not in expected or row['task'] != expected[key]:
            raise ValueError('Duplicate, unexpected, or changed final question')
        observed[key] = row
    clusters = defaultdict(lambda: np.zeros(4, dtype=np.int64))
    classes, statuses = {}, Counter()
    unscored = 0
    for key, task in expected.items():
        family = task['campaign']['root_family']
        gana = task['dhatu']['gana']
        if family in classes and classes[family] != gana:
            raise ValueError('A family cannot span root classes')
        classes[family] = gana
        row = observed.get(key)
        usable = bool(row and completed(row))
        correct = bool(row and row.get('is_correct') is True)
        unscored += int(row is not None and row.get('is_correct') not in (True, False))
        statuses[row['status'] if row else 'missing_result'] += 1
        clusters[family] += (correct, 1, correct and usable, usable)
    keys = sorted(clusters)
    values = np.array([clusters[k] for k in keys])
    g = len(keys)
    rng = np.random.default_rng(seed)
    draws, stratified = [], []
    groups = {c: np.array([i for i, k in enumerate(keys) if classes[k] == c])
              for c in sorted(set(classes.values()))}
    for start in range(0, repetitions, 256):
        size = min(256, repetitions - start)
        draws.append(values[rng.integers(0, g, size=(size, g))].sum(axis=1))
        batch = np.zeros((size, 4), dtype=np.int64)
        for indices in groups.values():
            batch += values[rng.choice(indices, size=(size, len(indices)))].sum(axis=1)
        stratified.append(batch)
    draws, stratified = np.concatenate(draws), np.concatenate(stratified)

    def ratio(a, b):
        numerator, denominator = int(values[:, a].sum()), int(values[:, b].sum())
        if not denominator:
            return {'n': 0, 'accuracy': None, 'root_cluster_sandwich_standard_error': None}
        p = numerator / denominator
        residuals = values[:, a] - p * values[:, b]
        sandwich = math.sqrt(g / (g - 1) * float(residuals @ residuals)) / denominator if g > 1 else None
        result = {'n': denominator, 'correct': numerator, 'accuracy': p,
                  'iid_standard_error': math.sqrt(p * (1 - p) / denominator),
                  'iid_wilson_95_interval': wilson(numerator, denominator),
                  'root_cluster_sandwich_standard_error': sandwich}
        for label, resampled in [('family_bootstrap', draws), ('class_stratified_family_bootstrap', stratified)]:
            valid = resampled[:, b] > 0
            estimates = resampled[valid, a] / resampled[valid, b]
            result[label] = {'standard_error': float(estimates.std(ddof=1)) if len(estimates) > 1 and g > 1 else None,
                             'percentile_95_interval': np.quantile(estimates, [.025, .975]).tolist() if g > 1 else None,
                             'valid_repetitions': len(estimates)}
        return result

    all_requests, answered = ratio(0, 1), ratio(2, 3)
    correct_complete = int(values[:, 2].sum())
    n_complete = int(values[:, 3].sum())
    return {'fixed_n': len(tasks), 'result_rows': len(rows), 'all_results_present': len(rows) == len(tasks),
            'unscored_results': unscored, 'statuses': dict(statuses),
            'truncated': sum(bool(r.get('truncated')) for r in rows),
            'root_families': g, 'families_per_class': {k: len(v) for k, v in groups.items()},
            'all_request': all_requests, 'completed_answer': answered,
            'missing_answer_accuracy_bounds': [correct_complete / len(tasks),
                (correct_complete + len(tasks) - n_complete) / len(tasks)],
            'bootstrap_repetitions': repetitions, 'bootstrap_seed': seed}


def numerical_gates(models):
    """Numerical checks alone cannot certify linguistic validity or diversity."""
    paired = set(models) == set(runner.PROVIDERS)
    complete = paired and all(m['all_results_present'] and not m['unscored_results'] for m in models.values())
    bounds = [max(m['missing_answer_accuracy_bounds'][i] for m in models.values()) for i in (0, 1)] if models else [None, None]
    accuracy = bool(complete and .79 <= bounds[0] <= bounds[1] <= .81)
    precision = bool(complete and all(
        m[label]['root_cluster_sandwich_standard_error'] is not None
        and m[label]['root_cluster_sandwich_standard_error'] < .01
        and m[label]['iid_standard_error'] < .01
        for m in models.values() for label in ('all_request', 'completed_answer')))
    return {'paired_references_complete': complete,
            'strongest_reference_missing_answer_bounds': bounds,
            'strongest_reference_target_met': accuracy,
            'both_references_precision_met': precision,
            'all_numerical_requirements_met': accuracy and precision}


def analyze(directory):
    directory = Path(directory)
    manifest = io.read_json(directory / 'manifest.json')
    if ('reference_models' in manifest or manifest.get('protocol_version') == 'common64k-v1'):
        if manifest.get('reference_models') != {p: v['model'] for p, v in runner.PROVIDERS.items()}:
            raise ValueError('Frozen reference models changed')
    tasks = io.read_json(directory / 'tasks.json')
    if io.sha256(directory / 'tasks.json') != manifest['frozen_tasks_sha256']:
        raise ValueError('Frozen task file changed')
    if io.sha256(directory / 'sampling-plan.json') != manifest['frozen_sampling_plan_sha256']:
        raise ValueError('Frozen sampling plan changed')
    if len(tasks) != manifest['fixed_n']:
        raise ValueError('Fixed N changed')
    stages = []
    for record in manifest['stages']:
        path = directory / record['path']
        stage_tasks = io.read_json(path)
        if io.sha256(path) != record['sha256'] or runner.digest(stage_tasks) != record['tasks_digest']:
            raise ValueError('Frozen stage changed')
        stages.append({'phase': record['phase'], 'tasks': stage_tasks})
    audit_partition(tasks, stages, manifest['track'], manifest.get('protocol_version', 'legacy16k-v1'))
    state = runner.load()
    from misc.vp_cartesian_release_protocol import require_complete_cohort
    selected = require_complete_cohort(state, manifest, io.sha256(directory/'manifest.json'), runner.PROVIDERS)
    for name, fingerprint in manifest['dependency_sha256'].items():
        if io.sha256(ROOT/name) != fingerprint:
            raise ValueError('Frozen release dependency changed: '+name)
    if io.sha256(ROOT/manifest['oracle_policy_path']) != manifest['oracle_policy_sha256']:
        raise ValueError('Frozen oracle policy changed')
    for phase, protocol in manifest.get('reference_protocol_by_phase', {}).items():
        if protocol != {'effort': runner.PHASES[phase][0], 'max_output_tokens': runner.PHASES[phase][1]}:
            raise ValueError('Frozen reference protocol changed')
    models, jobs_used = {}, {}
    for provider in runner.PROVIDERS:
        rows, jobs_used[provider] = [], []
        for job in selected[provider]:
            path = runner.OUT / 'jobs' / job['id'] / 'results.json'
            rows.extend(io.read_json(path))
            jobs_used[provider].append({'id': job['id'], 'results_sha256': io.sha256(path)})
        models[provider] = panel_statistics(tasks, rows)
    changed_dependencies = [name for name, digest in manifest['dependency_sha256'].items()
                            if io.sha256(ROOT / name) != digest]
    if io.sha256(ROOT / manifest['oracle_policy_path']) != manifest['oracle_policy_sha256']:
        changed_dependencies.append(manifest['oracle_policy_path'])
    gates = numerical_gates(models)
    result = {'created_at': io.now(), 'release_directory': str(directory.resolve()),
              'manifest_sha256': io.sha256(directory / 'manifest.json'),
              'analysis_sha256': io.sha256(Path(__file__)), 'fixed_n': manifest['fixed_n'],
              'models': models, 'jobs': jobs_used, 'numerical_gates': gates,
              'changed_dependencies_since_freeze': changed_dependencies,
              'benchmark_ready': False,
              'status': 'complete_numerical_analysis' if gates['paired_references_complete'] else 'incomplete_evaluation',
              'limits': ['All frozen questions remain in the primary denominator; no result-driven replacements or scope filtering.',
                         'Numerical gates do not certify linguistic validity, diversity, independent etymological families, or absence of training contamination.',
                         'Family statistics estimate sampling uncertainty, not stochastic variation between repeated model runs.',
                         'Class-stratified bootstrap is a sensitivity analysis; sparse class strata can have misleadingly small conditional variance.',
                         'Changed dependencies require review; this analyzer never authorizes a benchmark release.']}
    io.atomic_json(directory / 'reference-analysis.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release_directory', type=Path)
    args = parser.parse_args()
    result = analyze(args.release_directory)
    print({k: result[k] for k in ('status', 'fixed_n', 'numerical_gates', 'benchmark_ready')})
