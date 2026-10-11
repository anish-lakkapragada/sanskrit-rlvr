"""Prospective allocation scenarios, readable only after the full pilot08 panel.

No selection, payment, policy mutation, or final membership. Conditional
development extrapolations are not measured final accuracy or precision.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from misc.vp_5d_analyze_08_r2 import verify_settled
from misc.vp_cartesian_analyze import completed
from misc import oai_batch_eval as io

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'benchmarks/parallel-search-20261006/five_d'
PANEL = BASE / 'pilot-08/revision-02'
SIZES = (3000, 3600, 4200, 4800)
CATEGORIES = ('both_Lun', 'one_Lun', 'different_non_Lun')


def cell(task):
    m = task['morphology']
    return '|'.join((task['derivation']['recipe_id'], m['lakara'], m['prayoga']))


def group(key, fine):
    recipe, lakara, voice = key.split('|')
    return key if fine else '|'.join((recipe, 'Lun' if lakara == 'Lun' else 'other', voice))


def category(a, b):
    a, b = a.split('|')[1], b.split('|')[1]
    return 'both_Lun' if a == b == 'Lun' else 'one_Lun' if 'Lun' in (a, b) else 'different_non_Lun'


def moments(rows, witness, *, fine, prior):
    """Four-state cell moments and exact allocation covariance coefficients."""
    states = ((1, 1), (0, 1), (1, 0), (0, 0))
    counts = defaultdict(Counter)
    for row in rows:
        counts[group(cell(row['task']), fine)][(int(row['is_correct'] is True), int(completed(row)))] += 1
    target = witness['cell_counts']
    missing = [c for c in target if not sum(counts[group(c, fine)].values())]
    if missing:
        return {'identified': False, 'unsupported_cells': missing,
                'unsupported_mass': sum(target[c] for c in missing) / witness['n']}
    probabilities = {}
    for c in target:
        observed = counts[group(c, fine)]
        denominator = sum(observed.values()) + 4 * prior
        probabilities[c] = [(observed[s] + prior) / denominator for s in states]
    n = witness['n']
    aggregate = [sum(target[c] * probabilities[c][i] for c in target) / n for i in range(4)]
    completion = aggregate[0] + aggregate[1]
    if not completion:
        return {'identified': False, 'reason': 'No usable answers'}
    accuracy, usable = aggregate[0] + aggregate[2], aggregate[0] / completion
    estimates = {}
    for label in ('recorded_all_correct', 'completed_ratio_influence'):
        z = [float(y) if label == 'recorded_all_correct' else c * (y - usable) / completion
             for y, c in states]
        centered, variance = {}, {}
        for c, probabilities_c in probabilities.items():
            mean = sum(p * value for p, value in zip(probabilities_c, z))
            centered[c] = mean - (accuracy if label == 'recorded_all_correct' else 0)
            variance[c] = max(0., sum(p * value**2 for p, value in zip(probabilities_c, z)) - mean**2)
        independent = sum(target[c] * variance[c] for c in target)
        squared_means = sum(target[c] * centered[c]**2 for c in target)
        coefficients = dict.fromkeys(CATEGORIES, 0.)
        for pair in witness['unordered_within_family_cell_pair_counts']:
            a, b, k = pair['cell_a'], pair['cell_b'], pair['pairs']
            squared_means += 2 * k * centered[a] * centered[b]
            coefficients[category(a, b)] += 2 * k * math.sqrt(variance[a] * variance[b])
        if squared_means < -1e-7:
            raise ValueError('Allocation implies negative squared family means')
        estimates[label] = {'independent_variance_sum': independent,
                            'allocation_mean_squared_sum': max(0., squared_means),
                            'pair_covariance_coefficients': coefficients}
    return {'identified': True, 'fine_cells': fine, 'prior_per_response_state': prior,
            'smallest_observed_cell': min(sum(counts[group(c, fine)].values()) for c in target),
            'projected_completion': completion, 'projected_all_accuracy': accuracy,
            'projected_usable_accuracy': usable,
            'projected_iid_se_pp': {'all': 100 * math.sqrt(accuracy * (1 - accuracy) / n),
                                    'usable': 100 * math.sqrt(usable * (1 - usable) / (n * completion))},
            'estimates': estimates}


def scenario(moment, witness, rhos):
    if any(not isinstance(rhos.get(k), (int, float)) or not math.isfinite(rhos[k])
           or not -1 <= rhos[k] <= 1 for k in CATEGORIES):
        return {'identified': False, 'reason': 'Missing or invalid pair correlation'}
    # This checks a conservative superset of all possible within-family blocks.
    coherent = True
    for total in range(1, witness['family_cap'] + 1):
        for lun in range(min(total, witness['aorist_per_family_cap']) + 1):
            other = total - lun
            a = 1 + (lun - 1) * rhos['both_Lun'] if lun else 1
            b = 1 + (other - 1) * rhos['different_non_Lun'] if other else 1
            if a < -1e-9 or b < -1e-9 or (lun and other and a * b < lun * other * rhos['one_Lun']**2 - 1e-9):
                coherent = False
    variance = moment['independent_variance_sum'] + sum(
        moment['pair_covariance_coefficients'][k] * rhos[k] for k in CATEGORIES)
    total_variance = variance + moment['allocation_mean_squared_sum']
    g, n = witness['distinct_families'], witness['n']
    return {'identified': True, 'rhos': rhos, 'valid_for_every_possible_family_block': coherent,
            'negative_variance': variance < 0 or total_variance < 0,
            'expected_sandwich_se_pp': 100 * math.sqrt(total_variance * g / (g - 1)) / n
            if total_variance >= 0 and g > 1 else None}


def analyze():
    declaration = io.read_json(PANEL / 'analysis-predeclaration.json')
    state = io.read_json(ROOT / 'benchmarks/iterative-goal-20261006/ledger.json')
    verify_settled(state, declaration)  # Must precede all aggregate/result reads.
    projection_declaration = io.read_json(BASE / 'pilot-08-scale-options-policy21/post08-scenarios-predeclaration.json')
    for path, digest in projection_declaration['dependency_sha256'].items():
        if io.sha256(ROOT / path) != digest:
            raise ValueError('Prospective scale dependency changed: ' + path)
    for path, digest in declaration['analysis_dependencies'].items():
        if io.sha256(ROOT / path) != digest:
            raise ValueError('Frozen pilot dependency changed: ' + path)
    aggregate = io.read_json(PANEL / 'aggregate-analysis.json')
    if not aggregate.get('all8settled_and_collected'):
        raise ValueError('A complete immutable pilot aggregate is required')
    if aggregate['analysis_predeclaration_sha256'] != io.sha256(PANEL / 'analysis-predeclaration.json'):
        raise ValueError('Aggregate declaration fingerprint differs')
    if aggregate['scope_exclusions']:
        raise ValueError('Scope changes require a new explicitly reviewed projection')
    rows = {'opus_primary': [], 'astra_paired': []}
    for source in aggregate['result_sources']:
        path = Path(source['path'])
        if io.sha256(path) != source['sha256']:
            raise ValueError('Pilot results changed')
        rows['opus_primary' if path.parent.name.startswith('opus-') else 'astra_paired'].extend(io.read_json(path))
    if len(rows['opus_primary']) != 2400 or len(rows['astra_paired']) != 240:
        raise ValueError('Wrong complete panel counts')
    options = {}
    for n in SIZES:
        wp = BASE / ('pilot-08-scale-policy21' if n == 4800 else 'pilot-08-scale-options-policy21') / f'N{n}.allocation.json'
        witness = io.read_json(wp)
        models = {}
        for model, rr in rows.items():
            cases = {}
            diagnostics = aggregate['raw']['dependence'][model]['residual_diagnostics']
            for fine in (False, True):
                for prior in (0., .5):
                    m = moments(rr, witness, fine=fine, prior=prior)
                    projections = {}
                    if m['identified']:
                        for label, mm in m['estimates'].items():
                            projections[label] = {}
                            for centering in ('coarse', 'fine'):
                                observed = diagnostics[label][centering]
                                for estimate in ('point', 'upper95'):
                                    rhos = {}
                                    for k in CATEGORIES:
                                        value = observed.get(k, {})
                                        interval = value.get('bootstrap_percentile95')
                                        rhos[k] = value.get('correlation') if estimate == 'point' else interval[1] if interval else None
                                    projections[label][centering + '_' + estimate] = scenario(mm, witness, rhos)
                            projections[label]['common_rho_sensitivity'] = [scenario(mm, witness, dict.fromkeys(CATEGORIES, rho))
                                                                          for rho in (0., .1, .2, .3, .4, .5)]
                    cases[f'{"fine" if fine else "coarse"}_prior{prior}'] = {'moments': m, 'projections': projections}
            costs = {}
            for weighting, value in aggregate['raw']['cost'][model]['standardized'].items():
                mean = value.get('calibrated_cost_mean')
                interval = (value.get('cost_whole_family_bootstrap') or {}).get('percentile95')
                costs[weighting] = {'conditional_mean_cost': n * mean if mean is not None else None,
                                    'conditional_cost_percentile95': [n * x for x in interval] if interval else None,
                                    'unsupported_mass': value['unsupported_target_mass']}
            models[model] = {'precision_scenarios': cases, 'cost_scenarios': costs}
        options[str(n)] = {'n': n, 'families': witness['distinct_families'], 'allocation_sha256': io.sha256(wp), 'models': models}
    result = {'created_at': io.now(), 'pilot_aggregate_sha256': io.sha256(PANEL / 'aggregate-analysis.json'),
              'projection_predeclaration_sha256': io.sha256(BASE / 'pilot-08-scale-options-policy21/post08-scenarios-predeclaration.json'),
              'pilot_advancement': aggregate['advancement'], 'options': options,
              'selected_n': None, 'benchmark_ready': False, 'paid_calls': 0,
              'limitations': [
                  'Astra is a deliberately enriched 240-question subset; conditional standardization does not identify population performance or remove selection bias.',
                  'Both models use the same prespecified empirical and smoothed, coarse and fine sensitivity cases. None replaces final measured SE.',
                  'Pair-correlation transport assumes stability across root families, class composition and family loads; paired Astra has only43 repeated-aorist families.',
                  'Upper95 scenarios combine marginal endpoints, not a joint95% bound. Some correlation scenarios are not coherent for every possible family block.',
                  'Cost intervals condition on observed development families and omit rare tails and adaptation uncertainty. They are not maximum cost guarantees.',
                  'Sizes3000/4200 round some joint cells by half a question. Cost means use the original pilot composition; maximum composition deviations are0.016667pp.',
                  'No final questions or RL questions are read. No N, membership, release, reserve revision or payment is authorized.'
              ]}
    destination = BASE / 'pilot-08-scale-options-policy21/post08-scenarios.json'
    if destination.exists():
        raise ValueError('Preserve the existing projection; make an explicit new version')
    io.atomic_json(destination, result)
    return destination


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(analyze())
