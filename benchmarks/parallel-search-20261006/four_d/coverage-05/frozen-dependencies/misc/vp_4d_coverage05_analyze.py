"""Frozen 96-question paired athematic diagnostic; no APIs or partial analysis."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from misc.vp_cartesian_analyze import completed, metric
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_goal_stats import wilson

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/parallel-search-20261006/four_d/coverage-05'
JOB = 'opus-four-d-pilot-06'
B = 20000
SEED = 202610070506
FILES = ['pilot-06.questions.json', 'pilot-06.pairs.json', 'pilot-06.manifest.json',
         'athematic-panel-design-r1.json']
DEPS = ['misc/vp_4d_coverage05_analyze.py', 'misc/vp_cartesian_analyze.py',
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


def now():
    return datetime.now(timezone.utc).isoformat()


def verify_panel(tasks, pairs):
    mapping = {t['id']: t for t in tasks}
    if len(tasks) != 96 or len(mapping) != 96 or len(pairs) != 48:
        raise ValueError('Exactly96 unique tasks and48 pairs required')
    seen, families = set(), set()
    for p in pairs:
        if p['family'] in families:
            raise ValueError('Pairs must be disjoint lexical families')
        families.add(p['family'])
        try:
            t, c = mapping[p['target_id']], mapping[p['control_id']]
        except KeyError as e:
            raise ValueError('Missing paired task') from e
        for role, r in [('target', t), ('control', c)]:
            if r['id'] in seen:
                raise ValueError('Repeated paired membership')
            seen.add(r['id'])
            camp = r['campaign']
            if (r['task_type'] != 'cartesian_4d' or r.get('derivation') is not None
                    or camp['split'] != 'development' or camp['root_family'] != p['family']
                    or camp['coverage05'] != dict(pair_id=p['pair_id'], role=role, source_branch=p['branch'])):
                raise ValueError('Pair contract differs')
        if (t['dhatu'] != c['dhatu'] or t['morphology']['lakara'] != 'Lot'
                or c['morphology']['lakara'] not in {'Lat', 'Lan', 'VidhiLin'}
                or {k:v for k,v in t['morphology'].items() if k!='lakara'}
                != {k:v for k,v in c['morphology'].items() if k!='lakara'}):
            raise ValueError('Only lakara may differ within each pair')
    if seen != set(mapping):
        raise ValueError('Incomplete paired membership')


def prepare():
    tasks, pairs = read(OUT/FILES[0]), read(OUT/FILES[1])
    verify_panel(tasks, pairs)
    d = read(OUT/'athematic-panel-design-r1.json')
    decl = dict(created_at=now(), job_id=JOB, provider='Anthropic', phase='confirm_64k',
        model='claude-opus-5-5', effort='xhigh', max_output_tokens=65536,
        n=96, target_n=48, control_n=48, families=48, tasks_digest=digest(tasks),
        files={f:sha(OUT/f) for f in FILES}, dependencies={f:sha(ROOT/f) for f in DEPS},
        numpy_version=np.__version__, bootstrap_repetitions=B, bootstrap_seed=SEED,
        completeness_gate='One named96-question job must be settled and collected before any model-result file is opened. Reject missing/duplicate IDs, changed task metadata, unscored rows and changed request protocol. No interim results or score stopping.',
        estimands='Keep target and control all-request and usable accuracy separate. Target-minus-control all-request difference is primary contrast; usable ratio difference and both-completed-pair difference are separate diagnostics with explicit denominators.',
        missingness='All-request accuracy uses immutable recorded is_correct. Nonusable answers, including truncated parsed answers, are unknown for completion bounds. Subtract role bounds in opposite order for target-minus-control identification bounds; these are not confidence intervals.',
        uncertainty='Resample all48 whole lexical-family pairs jointly, retaining zero-completion families and mismatched completion. Report20000-draw percentile95 intervals/SE and invalid denominator draws; also ratio-influence sandwichSE and Wilson role intervals. No stratified-estimator switch, no population-weight claim.',
        trigger=d['exploratory_trigger'],
        trigger_missingness='Wrong means usable completed and recorded incorrect. Require44usable per role,8wrong target families,3error ganas,2error branches and at least4more wrong targets than controls. Also report worst-case excess after every missing control is treated as wrong. A mechanical trigger is provisional if that robust excess is below4; source validity remains required.',
        grouping='Prespecified gana, source branch, control tense and number. Descriptive only; no individual-error selection or post-hoc release promotion.',
        scope='Freeze96raw tasks and policy21 eligibility. Any later grammatical exclusion requires a separate symmetric source audit; never silently modify this primary aggregate or trigger.',
        limits=['One target per family permits48independent family units only under a superpopulation independence assumption; dictionary families may still share morphology.',
                'Seeded constrained selection has no claimed population inclusion probabilities. Intervals describe this mechanism panel and omit coverage-hypothesis selection uncertainty.',
                'At80% and48independent targets iidSE is about5.8pp; this is a diagnostic, not final calibration.',
                'Only156test targets/78families exist under the broader interaction predicate; no500+ orsub1pp claim.'],
        no_paid_calls=True, benchmark_ready=False)
    save(OUT/'analysis-predeclaration.json', decl)
    print(json.dumps(dict(path=str(OUT/'analysis-predeclaration.json'),sha256=sha(OUT/'analysis-predeclaration.json'))))


def verify_settled(state, decl):
    j = state.get('jobs', {}).get(decl['job_id'])
    if not j or not j.get('settled') or not j.get('collected_at'):
        raise ValueError('Complete named96-question job must settle and collect before any result read')
    if any(j.get(k) != decl[k] for k in ['provider', 'phase', 'n', 'tasks_digest']):
        raise ValueError('Registered job differs from frozen analysis')
    return j


def verify_results(tasks, rows):
    tm = {t['id']:t for t in tasks}
    rm = {r['task']['id']:r for r in rows}
    if len(rows) != 96 or len(rm) != 96 or set(rm) != set(tm):
        raise ValueError('Missing, duplicate or wrong96-question membership')
    for tid, r in rm.items():
        if (r['task'] != tm[tid] or type(r.get('is_correct')) is not bool
                or r.get('task_id',tid)!=tid):
            raise ValueError('Changed task metadata or unscored result')
        for k in ['status', 'answer', 'truncated']:
            if k not in r:
                raise ValueError('Missing completion metadata')
    return rm


def interval(x):
    x = np.asarray(x, dtype=float)
    good = x[np.isfinite(x)]
    return dict(valid_replicates=len(good), invalid_replicates=len(x)-len(good),
        standard_error=float(np.std(good, ddof=1)) if len(good)>1 else None,
        percentile95=np.quantile(good,[.025,.975]).tolist() if len(good) else None)


def ratio_sandwich(y, n):
    den = float(n.sum()); k = len(y)
    if den == 0 or k < 2:
        return None
    p = float(y.sum())/den
    return math.sqrt(k/(k-1)*float(((y-p*n)**2).sum()))/den


def summarize(rows, pairs, repetitions=B):
    rm = {r['task']['id']:r for r in rows}
    targets = [rm[p['target_id']] for p in pairs]
    controls = [rm[p['control_id']] for p in pairs]
    x = np.array([[int(t['is_correct'] is True), int(c['is_correct'] is True),
                   int(completed(t)), int(completed(c))] for t,c in zip(targets,controls)],dtype=float)
    # Columns: recorded target/control correctness, completion, usable correctness,
    # both-completed correctness and both-completed count.
    both = x[:,2]*x[:,3]
    x = np.column_stack([x, x[:,0]*x[:,2], x[:,1]*x[:,3], x[:,0]*both, x[:,1]*both, both])
    k = len(pairs); s=x.sum(axis=0)
    w=np.random.default_rng(SEED).multinomial(k,[1/k]*k,repetitions)
    draws=w@x
    with np.errstate(divide='ignore',invalid='ignore'):
        values=dict(all_request=(s[0]-s[1])/k,
            usable_ratio=(s[4]/s[2]-s[5]/s[3]) if s[2]*s[3] else None,
            both_completed_pairs=(s[6]-s[7])/s[8] if s[8] else None,
            completion=(s[2]-s[3])/k)
        boot=dict(all_request=(draws[:,0]-draws[:,1])/k,
            usable_ratio=draws[:,4]/draws[:,2]-draws[:,5]/draws[:,3],
            both_completed_pairs=(draws[:,6]-draws[:,7])/draws[:,8],
            completion=(draws[:,2]-draws[:,3])/k)
        role_boot={'target':(draws[:,0]/k,draws[:,4]/draws[:,2]),
                   'control':(draws[:,1]/k,draws[:,5]/draws[:,3])}
    roles={}
    for label, rs, yi, ni, ui in [('target',targets,0,2,4),('control',controls,1,3,5)]:
        z=metric(rs)
        z.update(all_request_wilson95=wilson(z['correct'],k),
            usable_wilson95=wilson(z['completed_correct'],z['completed']) if z['completed'] else None,
            whole_family_bootstrap=dict(all_request=interval(role_boot[label][0]),usable=interval(role_boot[label][1])),
            family_sandwich_se=dict(all_request=ratio_sandwich(x[:,yi],np.ones(k)),usable=ratio_sandwich(x[:,ui],x[:,ni])))
        roles[label]=z
    tb,cb=[roles[z]['completed_response_bounds_on_all_questions'] for z in ['target','control']]
    errors=[p for p,t in zip(pairs,targets) if completed(t) and t['is_correct'] is False]
    wc=sum(completed(c) and c['is_correct'] is False for c in controls)
    excess=len(errors)-wc
    check=dict(target_usable_at_least44=roles['target']['completed']>=44,
        control_usable_at_least44=roles['control']['completed']>=44,
        wrong_target_families_at_least8=len(errors)>=8,
        target_error_ganas_at_least3=len({p['gana'] for p in errors})>=3,
        target_error_branches_at_least2=len({p['branch'] for p in errors})>=2,
        excess_wrong_targets_at_least4=excess>=4)
    grouped={}
    for field in ['gana','branch','control_tense','vacana']:
        def cell(p):
            if field in {'gana','branch'}:return p[field]
            return rm[p['control_id']]['task']['morphology']['lakara' if field=='control_tense' else 'vacana']
        grouped[field]={v:dict(families=sum(cell(p)==v for p in pairs),
            target=metric([rm[p['target_id']] for p in pairs if cell(p)==v]),
            control=metric([rm[p['control_id']] for p in pairs if cell(p)==v]),
            wrong_target_families=sum(cell(p)==v for p in errors)) for v in sorted({cell(p) for p in pairs})}
    return dict(n=2*k,families=k,roles=roles,
        paired=dict(difference_direction='target minus control',point_estimates=values,
            completion_pattern_counts=dict(Counter(f'{int(completed(t))}/{int(completed(c))}' for t,c in zip(targets,controls))),
            both_completed_pairs=int(s[8]),whole_family_bootstrap={a:interval(v) for a,v in boot.items()},
            missing_response_difference_bounds=[tb[0]-cb[1],tb[1]-cb[0]],bounds_are_not_confidence_intervals=True),
        trigger=dict(checks=check,all_mechanical_conditions_met=all(check.values()),
            wrong_completed_target_families=len(errors),wrong_completed_control_families=wc,
            wrong_target_error_ganas=len({p['gana'] for p in errors}),wrong_target_error_branches=len({p['branch'] for p in errors}),
            excess_wrong_completed_targets=excess,
            worst_case_excess_with_missing_controls_wrong=excess-(k-roles['control']['completed']),
            missingness_robust=excess-(k-roles['control']['completed'])>=4,
            source_audit_required=True,release_advance_authorized=False),
        groups=grouped,benchmark_ready=False)


def analyze():
    decl=read(OUT/'analysis-predeclaration.json')
    # This gate must precede opening any results, including another campaign.
    state=read(ROOT/'benchmarks/iterative-goal-20261006/ledger.json')
    job=verify_settled(state,decl)
    for base, table in [(OUT,decl['files']),(ROOT,decl['dependencies'])]:
        for f,h in table.items():
            if sha(base/f)!=h:raise ValueError('Frozen dependency changed: '+f)
    tasks,pairs=read(OUT/FILES[0]),read(OUT/FILES[1]);verify_panel(tasks,pairs)
    jobdir=ROOT/'benchmarks/iterative-goal-20261006/jobs'/decl['job_id']
    if read(jobdir/'tasks.json')!=tasks:raise ValueError('Registered tasks differ')
    requests=read(jobdir/'requests.json')
    if digest(requests)!=job['requests_digest'] or len(requests)!=96:raise ValueError('Request digest differs')
    for t,r in zip(tasks,requests):
        p=r['params']
        if (p['model']!=decl['model'] or p['max_tokens']!=decl['max_output_tokens']
                or p['output_config']['effort']!=decl['effort']
                or p['messages']!=[dict(role='user',content=render(t))]):
            raise ValueError('Executed reference protocol differs')
    path=jobdir/'results.json';rows=read(path);verify_results(tasks,rows)
    out=summarize(rows,pairs)
    out.update(created_at=now(),all96_settled_and_collected=True,
        analysis_predeclaration_sha256=sha(OUT/'analysis-predeclaration.json'),
        result_path=str(path),result_sha256=sha(path),raw_data_unchanged=True,
        caveats=decl['limits'])
    save(OUT/'pilot-06.analysis.json',out)
    print(json.dumps(dict(output=str(OUT/'pilot-06.analysis.json'),trigger=out['trigger']),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','analyze'])
    args=parser.parse_args()
    (prepare if args.command=='prepare' else analyze)()
