"""Prospective complete-panel analysis of the ordinary 4D dictionary-tail screen."""
import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_cartesian_prompt_v1 import render
from misc.vp_goal_stats import wilson

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/parallel-search-20261006/four_d/ordinary-tail-08'
JOB = 'opus-four-d-pilot-08'
N = 96
FILES = ['panel.questions.json', 'panel-design.json', 'panel-mechanical-audit.json',
         'source-audit.json', 'novelty-audit.json', 'review.md']
DEPS = ['misc/vp_4d_tail08_analyze.py', 'misc/vp_4d_tail08_analyze_test.py',
        'misc/vp_cartesian_prompt_v1.py', 'misc/vp_goal_stats.py']


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def digest(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def save(p, x):
    if Path(p).exists():
        raise ValueError('Preserve existing artifact: ' + str(p))
    Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def completed(r):
    return r['status'] == 'completed' and r['answer'] is not None and not r['truncated']


def metric(rows):
    g = len(rows)
    usable = [r for r in rows if completed(r)]
    c = sum(r['is_correct'] is True for r in rows)
    cu = sum(r['is_correct'] is True for r in usable)

    def family_se(k, d):
        # One task per family: all fixed G units remain, including C_g=Y_g=0.
        return math.sqrt(g / (g - 1) * (k / d) * (1 - k / d) / d) if g > 1 and d else None

    def iid_se(k, d):
        return math.sqrt((k / d) * (1 - k / d) / d) if d else None

    return dict(n=g, correct=c, all_request_accuracy=c / g if g else None,
                usable=len(usable), usable_correct=cu,
                usable_accuracy=cu / len(usable) if usable else None,
                completion_bounds=[cu / g, (cu + g - len(usable)) / g] if g else None,
                all_request_wilson95=wilson(c, g) if g else None,
                usable_wilson95=wilson(cu, len(usable)) if usable else None,
                one_per_family_sandwich_se=family_se(c, g),
                usable_family_se=family_se(cu, len(usable)),
                all_request_iid_se=iid_se(c, g), usable_iid_se=iid_se(cu, len(usable)),
                family_units_in_variance=g, statuses=dict(Counter(r['status'] for r in rows)),
                truncated=sum(bool(r['truncated']) for r in rows),
                unparsed_completed=sum(r['status'] == 'completed' and r['answer'] is None
                                       and not r['truncated'] for r in rows))


def verify_panel(tasks, design):
    if len(tasks) != N or len({t['id'] for t in tasks}) != N:
        raise ValueError('Exactly 96 unique tasks required')
    if len({t['campaign']['root_family'] for t in tasks}) != N:
        raise ValueError('Exactly one question per family required')
    for t in tasks:
        if (t['task_type'] != 'cartesian_4d' or t.get('derivation') is not None
                or t['prompt_version'] != 'cartesian-4d-v1'
                or t['campaign']['split'] != 'development'
                or set(t['morphology']) != {'lakara', 'prayoga', 'purusha', 'vacana'}
                or t['morphology']['prayoga'] != 'Kartari'):
            raise ValueError('Exact 4D contract changed')
    observed = dict(class_counts=dict(Counter(t['dhatu']['gana'] for t in tasks)),
                    lakara_counts=dict(Counter(t['morphology']['lakara'] for t in tasks)),
                    person_number_counts=dict(Counter(t['morphology']['purusha'] + '|'
                        + t['morphology']['vacana'] for t in tasks)))
    if any(observed[k] != design[k] for k in observed):
        raise ValueError('Fixed panel quotas differ')


def verify_settled(state, declaration):
    j = state.get('jobs', {}).get(declaration['job_id'])
    if not j or not j.get('settled') or not j.get('collected_at'):
        raise ValueError('Entire named 96-question job must settle before result access')
    if any(j.get(k) != declaration[k] for k in ['provider', 'phase', 'n', 'tasks_digest']):
        raise ValueError('Registered protocol differs')
    return j


def verify_results(tasks, rows):
    tm = {t['id']: t for t in tasks}
    rm = {r['task']['id']: r for r in rows}
    if len(rows) != N or len(rm) != N or set(rm) != set(tm):
        raise ValueError('Incomplete, duplicate or changed result membership')
    for tid, r in rm.items():
        if r['task'] != tm[tid] or type(r.get('is_correct')) is not bool or r.get('task_id', tid) != tid:
            raise ValueError('Changed task metadata or unscored answer')
        if any(k not in r for k in ['status', 'answer', 'truncated']):
            raise ValueError('Missing completion metadata')


def summarize(rows):
    m = metric(rows)
    errors = [r for r in rows if completed(r) and r['is_correct'] is False]
    ef = {r['task']['campaign']['root_family'] for r in errors}
    eg = {r['task']['dhatu']['gana'] for r in errors}
    el = {r['task']['morphology']['lakara'] for r in errors}
    checks = dict(at_least90_usable=m['usable'] >= 90, at_least16_wrong_families=len(ef) >= 16,
                  at_least3_error_ganas=len(eg) >= 3, at_least4_error_lakaras=len(el) >= 4)
    labels = {'gana': lambda r: r['task']['dhatu']['gana'],
              'lakara': lambda r: r['task']['morphology']['lakara'],
              'person_number': lambda r: r['task']['morphology']['purusha'] + '|'
                                         + r['task']['morphology']['vacana']}
    groups = {field: {v: metric([r for r in rows if label(r) == v])
                     for v in sorted({label(r) for r in rows})}
              for field, label in labels.items()}
    return dict(metrics=m, families=len({r['task']['campaign']['root_family'] for r in rows}),
                trigger=dict(checks=checks, all_mechanical_conditions_met=all(checks.values()),
                             wrong_completed_families=len(ef), error_ganas=len(eg),
                             error_lakaras=len(el), source_audit_required=True,
                             release_advance_authorized=False), groups=groups, benchmark_ready=False)


def prepare():
    tasks, design = read(OUT / FILES[0]), read(OUT / FILES[1])
    verify_panel(tasks, design)
    save(OUT / 'analysis-predeclaration.json', dict(
        created_at=datetime.now(timezone.utc).isoformat(), job_id=JOB,
        provider='Anthropic', phase='confirm_64k', model='claude-opus-5-5', effort='xhigh',
        max_output_tokens=65536, n=N, families=N, tasks_digest=digest(tasks),
        files={f: sha(OUT / f) for f in FILES}, dependencies={f: sha(ROOT / f) for f in DEPS},
        completeness_gate='Settle and collect the entire 96-question named job before opening results. Verify exact inputs, requests and scored metadata. No partial analysis, retries or score stopping.',
        estimands='Accuracy of this fixed class/tense-balanced panel, all-request and usable separately; completion bounds and descriptive class, tense and person/number cells. These are not population-weighted accuracy estimates.',
        trigger=design['exploratory_trigger'],
        uncertainty='One question per family. All-request family SE is sqrt(p*(1-p)/(G-1)). Usable accuracy retains all G fixed families, including zero-completion units: sqrt(G/(G-1)*p*(1-p)/M), M usable. Also report plug-in iid SE and nominal Wilson95 intervals. G=96 overall, or the fixed subgroup count. Zero empirical SE at an endpoint is degeneracy, not certainty. The constrained seeded allocation has no established randomized population inclusion probabilities; family independence and iid Wilson coverage are approximations.',
        scope='Keep all 96 raw questions in the primary analysis. Any new source issue requires a separate symmetric audit including successes. No outcome-driven item dropping or direct failed-item promotion.',
        limits=design['limits'] + [
            'All 96 families have older ordinary input exposure. This tests current-effort coverage, not globally unexposed roots.',
            'All 96 must settle. Passing the distributed-error trigger only motivates grammar-defined follow-up and independent confirmation; it does not qualify a benchmark.'],
        no_paid_calls=True, benchmark_ready=False))
    print('Declaration SHA', sha(OUT / 'analysis-predeclaration.json'))


def analyze():
    d = read(OUT / 'analysis-predeclaration.json')
    # This gate precedes every model-result file read.
    j = verify_settled(read(ROOT / 'benchmarks/iterative-goal-20261006/ledger.json'), d)
    for base, table in [(OUT, d['files']), (ROOT, d['dependencies'])]:
        for f, h in table.items():
            if sha(base / f) != h:
                raise ValueError('Frozen dependency changed: ' + f)
    tasks, design = read(OUT / FILES[0]), read(OUT / FILES[1])
    verify_panel(tasks, design)
    jd = ROOT / 'benchmarks/iterative-goal-20261006/jobs' / d['job_id']
    if read(jd / 'tasks.json') != tasks:
        raise ValueError('Registered tasks differ')
    requests = read(jd / 'requests.json')
    if len(requests) != N or digest(requests) != j['requests_digest']:
        raise ValueError('Requests differ')
    for t, q in zip(tasks, requests):
        p = q['params']
        if (p['model'] != d['model'] or p['max_tokens'] != d['max_output_tokens']
                or p['output_config']['effort'] != d['effort']
                or p['messages'] != [dict(role='user', content=render(t))]):
            raise ValueError('Executed model protocol differs')
    rp = jd / 'results.json'
    rows = read(rp)
    verify_results(tasks, rows)
    out = summarize(rows)
    out.update(created_at=datetime.now(timezone.utc).isoformat(), all96_settled_and_collected=True,
               analysis_predeclaration_sha256=sha(OUT / 'analysis-predeclaration.json'),
               result_path=str(rp), result_sha256=sha(rp), raw_data_unchanged=True,
               uncertainty=d['uncertainty'], limits=d['limits'])
    save(OUT / 'analysis.json', out)
    print(json.dumps(out['trigger'], indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['prepare', 'analyze'])
    (prepare if p.parse_args().command == 'prepare' else analyze)()
