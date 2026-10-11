"""Complete-panel analysis for the single-benchmark 4D/modification investigation."""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from misc import vp_goal as runner, oai_batch_eval as io
from misc.vp_cartesian_analyze import completed, metric
from misc.vp_cartesian_final_analyze import panel_statistics

OUT = runner.ROOT / 'benchmarks/parallel-search-20261007'
JOBS = {'four_d': ['opus-simple4d-90-01'],
        'modification': ['opus-modification-01', 'opus-modification-control-01']}
SEED = 2026100719
B = 20000


def target_key(task):
    return (task['campaign']['root_family'],
            tuple(task['morphology'][k] for k in ('lakara', 'prayoga', 'purusha', 'vacana')))


def paired(modification, controls):
    controls = {target_key(r['task']): r for r in controls}
    if len(controls) != len(modification):
        raise ValueError('Pairing must be one-to-one')
    families = defaultdict(lambda: np.zeros(7))
    transitions = Counter()
    used = set()
    for mod in modification:
        key = target_key(mod['task'])
        if key in used or key not in controls:
            raise ValueError('Duplicate or missing target pair')
        used.add(key)
        control = controls[key]
        for field in ('gold_slp1', 'gold_devanagari', 'dhatu', 'morphology'):
            if mod['task'][field] != control['task'][field]:
                raise ValueError('Paired target differs: ' + field)
        a, b = control['is_correct'] is True, mod['is_correct'] is True
        ua, ub = completed(control), completed(mod)
        families[key[0]] += (1, a, b, ua, ub, a and ua, b and ub)
        transitions[f'{int(a)}->{int(b)}'] += 1
    values = np.array(list(families.values()))
    total = values.sum(axis=0)
    rng = np.random.default_rng(SEED)
    draws = np.concatenate([values[rng.integers(0, len(values), size=(min(256, B-i), len(values)))].sum(axis=1)
                            for i in range(0, B, 256)])
    estimates = (draws[:, 2] - draws[:, 1]) / draws[:, 0]
    return {'n_pairs': len(modification), 'families': len(values),
            'direction': 'modification minus matched creation',
            'all_request_accuracy_difference': float((total[2] - total[1]) / total[0]),
            'family_bootstrap_95_interval': np.quantile(estimates, [.025, .975]).tolist(),
            'transitions_creation_to_modification': dict(transitions),
            'completion_difference': float((total[4] - total[3]) / total[0]),
            'usable_accuracy_difference': float(total[6]/total[4] - total[5]/total[3]) if total[3]*total[4] else None,
            'limitation': 'Paired development contrast; different input formats, not a causal isolation of one prompt token.'}


def describe(tasks, rows):
    stats = panel_statistics(tasks, rows, repetitions=B, seed=SEED)
    groups = defaultdict(list)
    for row in rows:
        t = row['task']
        fields = {'gana': t['dhatu']['gana'], 'target_lakara': t['morphology']['lakara'],
                  'cell': t['campaign'].get('sampling_cell', {}).get('label', 'unspecified')}
        if t['task_type'] == 'modification':
            fields['source_lakara'] = t['source_morphology']['lakara']
            fields['transition'] = t['source_morphology']['lakara'] + '→' + t['target_morphology']['lakara']
        for key, value in fields.items(): groups[key + '::' + value].append(row)
    wrong_families = {r['task']['campaign']['root_family'] for r in rows if completed(r) and r['is_correct'] is False}
    numerical_signal = bool(stats['all_results_present'] and not stats['unscored_results']
                            and stats['all_request']['accuracy'] < .9
                            and stats['completed_answer']['accuracy'] is not None
                            and stats['completed_answer']['accuracy'] < .9
                            and stats['missing_answer_accuracy_bounds'][1] < .9
                            and len(wrong_families) >= 5)
    return {'statistics': stats, 'groups': {k: metric(v) for k, v in sorted(groups.items())},
            'wrong_completed_families': len(wrong_families),
            'numerical_discovery_signal': numerical_signal,
            'source_review_required': True, 'benchmark_ready': False}


def analyze():
    state = runner.load()
    result = {'updated_at': io.now(), 'tracks': {}, 'benchmark_ready': False,
              'protocol': 'Opus5.5 xHigh/65536, one sample, no tools; complete frozen development panels only',
              'limitations': ['Adaptive development selection; no final holdout qualification.',
                              'Four-dimensional challenge uses English; matched modification/control use Sanskrit.',
                              'Report source-based corrections separately and symmetrically; do not rewrite raw results.']}
    for track, names in JOBS.items():
        jobs = [state['jobs'].get(name) for name in names]
        if not all(j and j.get('settled') and j.get('collected_at') for j in jobs):
            result['tracks'][track] = {'state': 'waiting_for_complete_panel',
                'jobs': [{'id': name, 'status': j.get('status') if j else 'not_submitted',
                          'provider_progress': j.get('batch', {}).get('request_counts') if j else None}
                         for name, j in zip(names, jobs)]}
            continue
        panels, sources = [], []
        for job in jobs:
            path = runner.OUT / 'jobs' / job['id']
            tasks, _ = runner.verify_job(job)
            rows = io.read_json(path / 'results.json')
            if job['phase'] != 'confirm_64k' or job['provider'] != 'Anthropic':
                raise ValueError('Unexpected protocol')
            if len(rows) != len(tasks): raise ValueError('Incomplete result panel')
            panel = describe(tasks, rows)
            panels.append((panel, rows))
            sources.append({'job': job['id'], 'tasks_digest': job['tasks_digest'],
                            'results_sha256': io.sha256(path / 'results.json'),
                            'cost_usd': job['actual_cost_upper_micro'] / 1e6})
        details = {'state': 'complete_pending_source_review', 'primary': panels[0][0], 'sources': sources}
        if track == 'modification':
            details.update(control=panels[1][0], paired=paired(panels[0][1], panels[1][1]))
        result['tracks'][track] = details
    io.atomic_json(OUT / 'analysis.json', result)
    return result


if __name__ == '__main__':
    value = analyze()
    print(json.dumps({k: {'state': v['state'], 'primary': v.get('primary', {}).get('statistics', {}).get('all_request')}
                      for k, v in value['tracks'].items()}, indent=2))
