"""Complete-panel-only analysis of the proposed ordinary4D ciN discovery."""
import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_cartesian_prompt_v1 import render
from misc.vp_goal_stats import wilson

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'benchmarks/parallel-search-20261006/four_d/coverage-gap-06'
JOB='opus-four-d-pilot-07'
N=46
FILES=['cin-candidate-inputs.json','cin-discovery-design.json','cin-branches.json',
       'cin-source-receipt.json','cin-source-audit.json','cin-novelty-audit.json']
DEPS=['misc/vp_4d_gap06_analyze.py','misc/vp_cartesian_prompt_v1.py','misc/vp_goal_stats.py']


def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()


def save(p,x):
    if Path(p).exists():raise ValueError('Preserve existing artifact: '+str(p))
    Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def completed(r):
    return r['status']=='completed' and r['answer'] is not None and not r['truncated']


def metric(rows):
    n=len(rows); us=[r for r in rows if completed(r)]
    c=sum(r['is_correct'] is True for r in rows);cu=sum(r['is_correct'] is True for r in us)
    def se(k,d):
        return math.sqrt((k/d)*(1-k/d)/(d-1)) if d>1 else None
    return dict(n=n,correct=c,all_request_accuracy=c/n if n else None,
        usable=len(us),usable_correct=cu,usable_accuracy=cu/len(us) if us else None,
        completion_bounds=[cu/n,(cu+n-len(us))/n] if n else None,
        all_request_wilson95=wilson(c,n) if n else None,
        usable_wilson95=wilson(cu,len(us)) if us else None,
        one_per_family_sandwich_se=se(c,n),usable_family_se=se(cu,len(us)),
        statuses=dict(Counter(r['status'] for r in rows)),
        truncated=sum(bool(r['truncated']) for r in rows),
        unparsed_completed=sum(r['status']=='completed' and r['answer'] is None and not r['truncated'] for r in rows))


def verify_panel(tasks,branches):
    if len(tasks)!=N or len({t['id'] for t in tasks})!=N or len(branches)!=N:
        raise ValueError('Exactly46 unique tasks and branch descriptors required')
    bm={b['id']:b for b in branches}
    if len(bm)!=N or set(bm)!={t['id'] for t in tasks}:
        raise ValueError('Branch membership differs')
    if len({t['campaign']['root_family'] for t in tasks})!=N:
        raise ValueError('Exactly one question per lexical family required')
    for t in tasks:
        if (t['task_type']!='cartesian_4d' or t.get('derivation') is not None
                or t['campaign']['split']!='development'
                or t['morphology']!=dict(lakara='Lun',prayoga='Karmani',purusha='Prathama',vacana='Eka')
                or t['campaign']['root_family']!=bm[t['id']]['family']
                or t['dhatu']['gana']!=bm[t['id']]['gana']):
            raise ValueError('Question contract changed')


def verify_settled(state,decl):
    j=state.get('jobs',{}).get(decl['job_id'])
    if not j or not j.get('settled') or not j.get('collected_at'):
        raise ValueError('Entire named46-question job must settle before result access')
    if any(j.get(k)!=decl[k] for k in ['provider','phase','n','tasks_digest']):
        raise ValueError('Registered protocol differs')
    return j


def verify_results(tasks,rows):
    tm={t['id']:t for t in tasks};rm={r['task']['id']:r for r in rows}
    if len(rows)!=N or len(rm)!=N or set(rm)!=set(tm):
        raise ValueError('Incomplete, duplicate or changed result membership')
    for tid,r in rm.items():
        if r['task']!=tm[tid] or type(r.get('is_correct')) is not bool or r.get('task_id',tid)!=tid:
            raise ValueError('Changed task metadata or unscored answer')
        if any(k not in r for k in ['status','answer','truncated']):
            raise ValueError('Missing completion metadata')


def summarize(rows,branches):
    bm={b['id']:b for b in branches};m=metric(rows)
    errors=[r for r in rows if completed(r) and r['is_correct'] is False]
    ef={r['task']['campaign']['root_family'] for r in errors}
    eg={r['task']['dhatu']['gana'] for r in errors}
    eb={bm[r['task']['id']]['branch'] for r in errors}
    checks=dict(at_least44_usable=m['usable']>=44,at_least8_wrong_families=len(ef)>=8,
        at_least3_error_ganas=len(eg)>=3,at_least2_error_branches=len(eb)>=2)
    groups={field:{v:metric([r for r in rows if bm[r['task']['id']][field]==v])
        for v in sorted({b[field] for b in branches})} for field in ['gana','branch']}
    return dict(metrics=m,families=len({r['task']['campaign']['root_family'] for r in rows}),
        trigger=dict(checks=checks,all_mechanical_conditions_met=all(checks.values()),
            wrong_completed_families=len(ef),error_ganas=len(eg),error_branches=len(eb),
            source_audit_required=True,release_advance_authorized=False),groups=groups,
        benchmark_ready=False)


def prepare():
    ts,bs=read(OUT/FILES[0]),read(OUT/FILES[2]);verify_panel(ts,bs)
    save(OUT/'cin-analysis-predeclaration.json',dict(created_at=now(),job_id=JOB,
        provider='Anthropic',phase='confirm_64k',model='claude-opus-5-5',effort='xhigh',
        max_output_tokens=65536,n=N,families=N,tasks_digest=digest(ts),
        files={f:sha(OUT/f) for f in FILES},dependencies={f:sha(ROOT/f) for f in DEPS},
        completeness_gate='Settle and collect the entire46-question named job before opening results; verify exact inputs, request protocol and scored metadata. No partial analysis, retries or score stopping.',
        estimands='Report immutable all-request and usable accuracies separately, missing-response identification bounds, completion status and descriptive fixed gana/branch cells.',
        trigger=read(OUT/'cin-discovery-design.json')['exploratory_trigger'],
        uncertainty='One question per family: unstratified family sandwich equals the sample Bernoulli SE. Also report nominal Wilson95 intervals. No claimed randomized population inclusion probabilities or independence across morphologically related families. A zero empirical SE at all-success/all-failure is degeneracy, not certainty.',
        scope='Keep all46 raw questions in the primary analysis. Any new source issue requires a separate symmetric audit over successes and failures; no outcome-driven item dropping.',
        limits=['All46 are Lun/Karmani/Prathama/Eka, with eight classes and no matched model controls.',
                'At79% the nominal iidSE with46 questions is about6.0pp; this is discovery, not final calibration.',
                'Only80test tuples/80families under this conservative predicate; no500+ orsub1pp claim.',
                'Fresh exact tuples do not imply globally unseen lexical families. Older High/4096 evidence is a separate fidelity.'],
        no_paid_calls=True,benchmark_ready=False))
    print('Declaration SHA',sha(OUT/'cin-analysis-predeclaration.json'))


def analyze():
    d=read(OUT/'cin-analysis-predeclaration.json')
    j=verify_settled(read(ROOT/'benchmarks/iterative-goal-20261006/ledger.json'),d)
    for base,table in [(OUT,d['files']),(ROOT,d['dependencies'])]:
        for f,h in table.items():
            if sha(base/f)!=h:raise ValueError('Frozen dependency changed: '+f)
    ts,bs=read(OUT/FILES[0]),read(OUT/FILES[2]);verify_panel(ts,bs)
    jd=ROOT/'benchmarks/iterative-goal-20261006/jobs'/d['job_id']
    if read(jd/'tasks.json')!=ts:raise ValueError('Registered tasks differ')
    qs=read(jd/'requests.json')
    if len(qs)!=N or digest(qs)!=j['requests_digest']:raise ValueError('Requests differ')
    for t,q in zip(ts,qs):
        p=q['params']
        if (p['model']!=d['model'] or p['max_tokens']!=d['max_output_tokens']
                or p['output_config']['effort']!=d['effort']
                or p['messages']!=[dict(role='user',content=render(t))]):
            raise ValueError('Executed model protocol differs')
    rp=jd/'results.json';rs=read(rp);verify_results(ts,rs)
    out=summarize(rs,bs);out.update(created_at=now(),all46_settled_and_collected=True,
        analysis_predeclaration_sha256=sha(OUT/'cin-analysis-predeclaration.json'),
        result_path=str(rp),result_sha256=sha(rp),raw_data_unchanged=True,
        uncertainty=d['uncertainty'],limits=d['limits'])
    save(OUT/'cin-analysis.json',out)
    print(json.dumps(out['trigger'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','analyze'])
    (prepare if p.parse_args().command=='prepare' else analyze)()
