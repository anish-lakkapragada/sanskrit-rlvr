"""Input-selected development output-limit diagnostic; never submits requests.

The selector reads tasks and scope policy only. Analysis is paired by exact task,
keeps incomplete answers separate, and never pools the diagnostic into a final.
"""
from __future__ import annotations

import argparse
import hashlib
import random
from collections import Counter

import numpy as np

from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_campaign_candidates import load_entries
from misc.vp_cartesian_analyze import completed, metric
from misc.vp_cartesian_task import entry_scope_issue, oracle_issue
from misc.vp_goal_validate import validate

OUT = runner.ROOT / 'benchmarks/parallel-search-20261006/five_d'
STEM = 'astra-cap-development-01'
JOB = 'astra-five-d-cap-development-01'
BASELINE = 'astra-five-d-pilot-04-pair'
SEED = 'vp-cap-inputs-20261007-01'
QUOTAS = {
    ('causative_of_intensive', True, 'Kartari'): 18,
    ('causative_of_intensive', False, 'Kartari'): 18,
    ('causative_of_intensive', False, 'Karmani'): 4,
    ('causative_of_intensive_luk', True, 'Kartari'): 7,
    ('causative_of_intensive_luk', False, 'Kartari'): 7,
    ('causative_of_intensive_luk', False, 'Karmani'): 2,
    ('desiderative', True, 'Kartari'): 2,
    ('desiderative', False, 'Kartari'): 2,
}


def cell(task):
    return (task['campaign']['construction'], task['morphology']['lakara'] == 'Lun',
            task['morphology']['prayoga'])


def select(tasks):
    ordered = sorted(tasks, key=lambda t: t['id'])
    lakaras = {t['morphology']['lakara'] for t in ordered} - {'Lun'}
    keys = sorted(QUOTAS, key=lambda k: sum(cell(t) == k for t in ordered)/QUOTAS[k])
    for attempt in range(10000):
        rng = random.Random(SEED+':'+str(attempt))
        shuffled = list(ordered); rng.shuffle(shuffled)
        chosen, families = [], set()
        for key in keys:
            n = 0
            for t in shuffled:
                family = t['campaign']['root_family']
                if cell(t) == key and family not in families:
                    chosen.append(t); families.add(family); n += 1
                    if n == QUOTAS[key]:
                        break
        counts = Counter(t['morphology']['lakara'] for t in chosen)
        if Counter(map(cell, chosen)) == Counter(QUOTAS) and all(2 <= counts[k] <= 7 for k in lakaras):
            assert len(families) == 60
            return sorted(chosen, key=lambda t: hashlib.sha256((SEED+t['id']).encode()).hexdigest())
    raise ValueError('Input-only cap panel allocation exhausted its fixed search bound')


def prepare():
    paths = {name: OUT / f'{STEM}.{name}.json' for name in ['tasks','plan','audit']}
    if any(p.exists() for p in paths.values()):
        raise ValueError('Frozen diagnostic already exists; never silently replace it')
    source = runner.OUT / 'jobs' / BASELINE / 'tasks.json'
    entries = {e.code: e for e in load_entries()}
    eligible = [t for t in io.read_json(source)
                if not (entry_scope_issue(entries[t['dhatu']['code']]) or oracle_issue(t))]
    tasks = select(eligible)
    audit = validate(tasks, 'development')
    io.atomic_json(paths['tasks'], tasks)
    io.atomic_json(paths['audit'], audit)
    plan = {
        'created_at': io.now(), 'job': JOB, 'n': 60, 'family_count': 60,
        'provider': 'OpenAI', 'phase': 'cap_check_development', 'effort': 'xhigh',
        'max_output_tokens': 128000, 'baseline_output_tokens': 16384,
        'seed': SEED, 'source_tasks': str(source), 'source_sha256': io.sha256(source),
        'tasks_sha256': io.sha256(paths['tasks']), 'tasks_digest': runner.digest(tasks),
        'selector_analyzer_sha256': io.sha256(__file__),
        'oracle_policy': 'oracle-policy-15',
        'oracle_code_sha256': io.sha256(runner.ROOT/'misc/vp_cartesian_task.py'),
        'eligible_input_pool': len(eligible),
        'quotas': [{'recipe':k[0], 'aorist':k[1], 'voice':k[2], 'n':v} for k,v in QUOTAS.items()],
        'lakara_counts': dict(Counter(t['morphology']['lakara'] for t in tasks)),
        'class_counts': dict(Counter(t['dhatu']['gana'] for t in tasks)),
        'selection': 'Input-only seeded allocation, one question per family. Exactly 45% aorist, 10% passive and 40/16/4 recipes; at least two of every other tense. No prior correctness, truncation, refusals, or output tokens used by selection.',
        'purpose': 'Paired output-limit diagnostic before final membership. Estimate changes in missingness, recorded-all accuracy, usable accuracy, cost, and reference ordering on these exact inputs.',
        'analysis': 'Preserve all 60 pairs. Report both limits separately, paired transitions and bootstrap difference, and same-question Opus baseline. No replacements, score-driven stopping, or pooling with a primary panel. Sampling is not uniform over the full generator; no precise final-population performance claim.',
        'decision': 'Any reference-order reversal or material gain requires revisiting the final protocol before freeze. Failure to observe a gain is not proof of equivalence. Remaining sensitivity allowance is 40 questions for this provider, shared with any final cap check.',
        'budget_max_usd': 60*(1500*5+128000*25)/1e6,
        'split': 'development', 'benchmark_ready': False,
    }
    io.atomic_json(paths['plan'], plan)
    return plan


def paired_analysis(before, after):
    if len(before) != len(after) or not before:
        raise ValueError('Missing paired records')
    for a,b in zip(before, after):
        if a['task'] != b['task']:
            raise ValueError('Paired input changed')
    delta = np.array([int(b['is_correct'] is True)-int(a['is_correct'] is True)
                      for a,b in zip(before, after)])
    rng = np.random.default_rng(20261007)
    means = delta[rng.integers(0,len(delta),(20000,len(delta)))].mean(axis=1)
    return {'baseline': metric(before), 'higher_cap': metric(after),
            'recorded_accuracy_difference': float(delta.mean()),
            'paired_bootstrap_difference_95': np.quantile(means,[.025,.975]).tolist(),
            'wrong_or_missing_to_correct': int((delta == 1).sum()),
            'correct_to_wrong_or_missing': int((delta == -1).sum()),
            'baseline_incomplete': sum(not completed(r) for r in before),
            'newly_completed': sum(not completed(a) and completed(b) for a,b in zip(before,after)),
            'newly_incomplete': sum(completed(a) and not completed(b) for a,b in zip(before,after))}


def analyze():
    plan = io.read_json(OUT/f'{STEM}.plan.json')
    tasks = io.read_json(OUT/f'{STEM}.tasks.json')
    assert runner.digest(tasks) == plan['tasks_digest']
    assert io.sha256(__file__) == plan['selector_analyzer_sha256']
    state = runner.load()
    assert state['jobs'][JOB].get('collected_at'), 'Diagnostic still pending'
    def aligned(job):
        source = io.read_json(runner.OUT/'jobs'/job/'results.json')
        rows = {r['task_id']:r for r in source}
        if len(rows) != len(source):
            raise ValueError('Duplicate diagnostic records')
        result = [rows[t['id']] for t in tasks]
        assert all(t == r['task'] for t,r in zip(tasks,result))
        return result
    before,after,opus = aligned(BASELINE),aligned(JOB),aligned('opus-five-d-pilot-04')
    result = {'created_at':io.now(), 'paired':paired_analysis(before,after),
              'opus_16k_same_questions':metric(opus),
              'baseline_incomplete_subset':paired_analysis(
                  [a for a in before if not completed(a)],
                  [b for a,b in zip(before,after) if not completed(a)]) if any(not completed(a) for a in before) else None,
              'actual_cost_upper_usd':state['jobs'][JOB]['actual_cost_upper_micro']/1e6,
              'limits':plan['analysis'], 'benchmark_ready':False}
    io.atomic_json(OUT/f'{STEM}.analysis.json',result)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['prepare','analyze'])
    args=parser.parse_args()
    print(prepare() if args.action == 'prepare' else analyze())
