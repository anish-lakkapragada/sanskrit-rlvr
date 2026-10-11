"""Offline, policy-aware pilot summaries and same-question reference comparisons."""
from __future__ import annotations

import itertools
from collections import Counter
from pathlib import Path

from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_campaign_candidates import load_entries
from misc.vp_cartesian_task import entry_scope_issue, oracle_issue
from misc.vp_goal_stats import accuracy_uncertainty

OUT = runner.ROOT / 'benchmarks/parallel-search-20261006'
# Record the code loaded into this process, not a later file edit that a long-lived
# collector has not imported. A fresh process will invalidate an older snapshot.
SCOPE_POLICY_HASH = io.sha256(runner.ROOT / 'misc/vp_cartesian_task.py')


def completed(row):
    return row['status'] == 'completed' and row['answer'] is not None and not row['truncated']


def metric(rows):
    usable = [r for r in rows if completed(r)]
    correct = sum(r['is_correct'] is True for r in rows)
    usable_correct = sum(r['is_correct'] is True for r in usable)
    return {'n': len(rows), 'correct': correct,
            'all_request_accuracy': correct / len(rows) if rows else None,
            'completed': len(usable), 'completed_correct': usable_correct,
            'completed_accuracy': usable_correct / len(usable) if usable else None,
            'completed_response_bounds_on_all_questions':
                [usable_correct / len(rows),
                 (usable_correct + len(rows) - len(usable)) / len(rows)] if rows else None,
            'statuses': dict(Counter(r['status'] for r in rows)),
            'truncated': sum(bool(r['truncated']) for r in rows),
            'families': len({r['task']['campaign']['root_family'] for r in rows})}


def grouped(rows, field):
    def key(row):
        task = row['task']
        if field == 'recipe':
            return task['campaign']['construction']
        if field == 'gana':
            return task['dhatu']['gana']
        if field == 'sampling_cell':
            return task['campaign'].get('sampling_cell', {}).get('label', 'unspecified')
        return task['morphology'][field]
    return {k: metric([r for r in rows if key(r) == k]) for k in sorted({key(r) for r in rows})}


def analyze():
    state = runner.load()
    jobs = [j for j in state['jobs'].values() if j.get('collected_at')
            and j['phase'] in {'explore', 'confirm'}
            and ('-four-d-' in j['id'] or '-five-d-' in j['id'])]
    source = {j['id']: io.sha256(runner.OUT / 'jobs' / j['id'] / 'results.json') for j in jobs}
    source['analyzer'] = io.sha256(Path(__file__))
    source['statistics'] = io.sha256(runner.ROOT / 'misc/vp_goal_stats.py')
    source['scope_policy_code'] = SCOPE_POLICY_HASH
    path = OUT / 'development-results.json'
    if path.exists() and io.read_json(path).get('sources') == source:
        return io.read_json(path)
    entries = {e.code: e for e in load_entries()}
    experiments, retained = {}, {}
    for job in jobs:
        rows = io.read_json(runner.OUT / 'jobs' / job['id'] / 'results.json')
        kept, excluded = [], []
        for row in rows:
            task = row['task']
            issue = entry_scope_issue(entries[task['dhatu']['code']]) or oracle_issue(task)
            if issue:
                excluded.append({'id': task['id'], 'reason': issue})
            else:
                kept.append(row)
        retained[job['id']] = {r['task_id']: r for r in kept}
        usable = [r for r in kept if completed(r)]
        experiments[job['id']] = {
            'provider': job['provider'], 'task_type': rows[0]['task']['task_type'],
            'raw': metric(rows), 'within_current_scope': metric(kept), 'excluded': excluded,
            'strata': {field: grouped(kept, field) for field in
                       ['recipe', 'lakara', 'prayoga', 'gana', 'sampling_cell']},
            'completed_uncertainty': accuracy_uncertainty(usable, repetitions=5000) if usable else None,
            'cost_upper_usd': job['actual_cost_upper_micro'] / 1e6,
            'limits': 'Development estimates. Scope eligibility is not complete gold certification. '
                      'Original scores are immutable; exclusions apply equally to successes and failures. '
                      'Completed-response bounds treat every refused, incomplete or missing answer as '
                      'unknown and range from all of them wrong to all of them correct; they are not confidence intervals.'}
    pairs = []
    for left, right in itertools.combinations(experiments, 2):
        if experiments[left]['provider'] == experiments[right]['provider']:
            continue
        common = sorted(retained[left].keys() & retained[right].keys())
        if not common:
            continue
        a = [retained[left][key] for key in common]
        b = [retained[right][key] for key in common]
        for x, y in zip(a, b):
            if x['task'] != y['task']:
                raise ValueError('Paired task metadata differs: ' + x['task_id'])
        both = [(x, y) for x, y in zip(a, b) if completed(x) and completed(y)]
        pairs.append({'left': left, 'right': right, 'n_identical_questions': len(common),
                      'left_on_same_questions': metric(a), 'right_on_same_questions': metric(b),
                      'n_both_completed': len(both),
                      'left_only_correct_when_both_complete': sum(x['is_correct'] and not y['is_correct'] for x, y in both),
                      'right_only_correct_when_both_complete': sum(y['is_correct'] and not x['is_correct'] for x, y in both),
                      'both_correct_when_both_complete': sum(x['is_correct'] and y['is_correct'] for x, y in both),
                      'both_wrong_when_both_complete': sum(not x['is_correct'] and not y['is_correct'] for x, y in both)})
    result = {'updated_at': io.now(), 'sources': source, 'experiments': experiments,
              'paired_comparisons': pairs, 'benchmark_ready': False,
              'limits': 'No held-out evaluation or selection-adjusted inference. Reused tasks in model pairing '
                        'do not increase independent N. Refusal-conditioned accuracy can have missing-answer bias.'}
    io.atomic_json(path, result)
    return result


if __name__ == '__main__':
    result = analyze()
    print({job: data['within_current_scope'] for job, data in result['experiments'].items()})
