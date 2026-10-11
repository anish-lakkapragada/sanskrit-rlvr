"""Bounded ordinary4D gap inventory; no APIs, reserved outcomes or pilot08 reads."""
import json
import hashlib
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_4d_coverage05 import (
    ROOT, B, COORDS, read, sha, key, metadata, issue, repeat_mechanism, stats)
from misc.vp_cartesian_task import entries_by_code, make_task
from misc.vp_campaign_candidates import family, name

OUT = B / 'four_d/coverage-gap-06'


def matches(r, label):
    rules = set(r['rules'])
    if label == 'pushadi_aNg_aorist':
        return r['prayoga']=='Kartari' and r['lakara']=='Lun' and '3.1.55' in rules
    if label == 'passive_cin_third_singular':
        return r['prayoga']=='Karmani' and r['lakara']=='Lun' and '3.1.66' in rules
    if label == 'present_passive_yak':
        return r['prayoga']=='Karmani' and r['lakara'] in {'Lat','Lan','VidhiLin'} and '3.1.67' in rules
    if label == 'passive_yak_with_base_change':
        return matches(r,'present_passive_yak') and bool(rules & {'6.1.15','6.1.16','6.4.24','6.4.37','6.4.38','6.4.51','6.4.63','6.4.64','6.4.65'})
    if label == 'vowel_initial_past_augmentation':
        return r['prayoga']=='Kartari' and r['lakara'] in {'Lan','Lun','Lrn'} and '6.4.72' in rules
    if label == 'nonimperative_us_vowel_resolution':
        return r['lakara']!='Lot' and '6.1.96' in rules
    if label == 'nonimperative_final_cluster_resolution':
        return r['prayoga']=='Kartari' and r['lakara'] in {'Lan','Lun'} and bool(rules & {'8.2.23','8.2.24'})
    raise ValueError(label)


LABELS = ['pushadi_aNg_aorist', 'passive_cin_third_singular',
          'present_passive_yak', 'passive_yak_with_base_change',
          'vowel_initial_past_augmentation', 'nonimperative_us_vowel_resolution',
          'nonimperative_final_cluster_resolution']


def main():
    assert not (OUT/'inventory.json').exists()
    es = entries_by_code()
    split = read(ROOT/'benchmarks/creation-campaign-20261006/family-split.json')['families']
    stamp = datetime.now(timezone.utc).isoformat()
    # Predicates and analysis scope fixed before loading any historical labels.
    design = dict(created_at=stamp, predicates=LABELS, predicate_script_sha256=sha(Path(__file__)),
        scope='Source21 plus preexisting local precautions. Candidate supply excludes Bhave, uses the earlier exact Karmani transitivity allowlist, and removes already studied adanta/perfect/dhvam/specialized-iT/Kutadi mechanisms. No renamed imperative probe.',
        intended_output='Rank source-defined remaining coverage gaps; at most one paid proposal only if independently justified. No predictor fitting or individual-failure selection.',
        history='Current six xHigh input panels versus broader legacy input coverage. Historical High/4096 aggregate evidence uses only the already development-filtered surrogate cache, freshly scope-gated; no model output text or reserved-family outcomes.',
        bhave='Coordinator has already audited Bhave; do not duplicate or add it.',
        no_pilot08_outcomes=True, no_paid_calls=True)
    (OUT/'design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n')
    cohorts = {'development':{},'test':{}}
    dbpath = ROOT/'benchmarks/creation-campaign-20261006/candidates.sqlite'
    db = sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
    for row in db.execute("SELECT * FROM candidates WHERE split IN ('development','test')"):
        tid,fam,spl,code,la,pr,pu,va,gold,rules,steps,variants=row
        e=es[code]
        assert split[family(e)]['split']==spl
        m=dict(id=tid,code=code,family=fam,gana=name(e.dhatu.gana),
               **dict(zip(COORDS,[la,pr,pu,va])),rules=json.loads(rules))
        if not any(matches(m,l) for l in LABELS):continue
        t=dict(id=tid,dhatu=dict(code=code,aupadeshika=e.dhatu.aupadeshika,gana=name(e.dhatu.gana)),
               morphology={k:m[k] for k in COORDS},gold_slp1=json.loads(gold),
               campaign=dict(root_family=fam,trace_rule_ids=m['rules']))
        if issue(t,e) or repeat_mechanism(m):continue
        cohorts[spl].setdefault(key(t),m)
    db.close()
    current={}; inputs=[]
    for i in range(1,7):
        p=ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-four-d-pilot-{i:02d}/tasks.json'
        inputs.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
        for old in read(p):
            e=es[old['dhatu']['code']]
            assert split[family(e)]['split']=='development'
            fresh=make_task(e,'development',old['morphology']) if not __import__('misc.vp_cartesian_task',fromlist=['entry_scope_issue']).entry_scope_issue(e) else None
            if not fresh or issue(fresh,e):continue
            current[key(fresh)]=metadata(fresh)
    history=read(B/'four_d/coverage-05/broader-legacy-metadata.json')
    # Cached labels are explicitly development-only; guard every row before use.
    cache=read(B/'four_d/surrogate-04.development-features.json')
    labeled={'high':[],'xhigh':[]}; removed=Counter()
    from misc.vp_cartesian_task import entry_scope_issue
    for fidelity,rows in cache.items():
        for old in rows:
            e=es[old['code']]
            assert split[family(e)]['split']=='development'
            if entry_scope_issue(e):removed[fidelity+':entry_scope']+=1;continue
            features=dict(s.split('=',1) for s in old['features'] if not s.startswith('trace='))
            m={k:features[k] for k in COORDS}
            t=make_task(e,'development',m)
            if not t or issue(t,e):removed[fidelity+':oracle_or_local_scope']+=1;continue
            r=metadata(t)
            if repeat_mechanism(r):continue
            if not any(matches(r,l) for l in LABELS):continue
            r.update(error=old['error'],panel=old['panel'])
            labeled[fidelity].append(r)
    # Pilot06 is fully settled and known100%; include only its cached fixed result analysis,
    # with no access to any other result file or pilot08 outcome.
    six=read(B/'four_d/coverage-05/pilot-06.analysis.json')
    assert six['roles']['target']['correct']==48 and six['roles']['control']['correct']==48
    for t in read(ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-four-d-pilot-06/tasks.json'):
        r=metadata(t)
        if not repeat_mechanism(r) and any(matches(r,l) for l in LABELS):
            labeled['xhigh'].append(dict(r,error=0,panel='pilot06_64k'))
    result=[]
    for label in LABELS:
        selected={s:[r for r in rs.values() if matches(r,label)] for s,rs in cohorts.items()}
        ev={}
        for fidelity,rows in labeled.items():
            rr=[r for r in rows if matches(r,label)]
            ev[fidelity]=dict(n=len(rr),correct=sum(not r['error'] for r in rr),
                families=len({r['family'] for r in rr}),error_families=len({r['family'] for r in rr if r['error']}),
                panels=dict(Counter(r['panel'] for r in rr)))
        result.append(dict(label=label,supply={s:stats(rr) for s,rr in selected.items()},
            current_six_inputs=stats([r for r in current.values() if matches(r,label)]),
            broader_legacy_inputs=stats([r for r in history if matches(r,label)]),
            completed_development_evidence=ev,
            development_examples=[dict(code=r['code'],gana=r['gana'],**{k:r[k]for k in COORDS})for r in selected['development'][:5]]))
    # Fresh full derivation audit of every counted candidate family at one input per label.
    checks=[]
    for label in LABELS:
        for spl, rows in cohorts.items():
            seen=set()
            for r in rows.values():
                if not matches(r,label) or r['family']in seen:continue
                seen.add(r['family']);t=make_task(es[r['code']],spl,{k:r[k]for k in COORDS})
                assert t and not issue(t,es[r['code']]) and matches(metadata(t),label)
                checks.append(dict(label=label,split=spl,family=r['family'],id=t['id']))
    out=dict(created_at=stamp,policy='oracle-policy-21',predicates=result,
        input_sources=inputs,script_sha256=sha(Path(__file__)),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),
        legacy_metadata_sha256=sha(B/'four_d/coverage-05/broader-legacy-metadata.json'),
        historical_development_cache_sha256=sha(B/'four_d/surrogate-04.development-features.json'),
        cache_scope_exclusions=dict(removed),fresh_family_predicate_checks=len(checks),
        source_limits='Passive supply is a conservative lower census under the old exact meaning allowlist, not a proof that other meanings are intransitive. Historical exposure includes broader meanings; completed evidence remains within current candidate meaning scope.',
        fidelity='Historical High/4096 and current xHigh/16384 are separate. Pilot06 alone uses xHigh/65536. None is a new reserved-family accuracy estimate.',
        no_reserved_model_answers=True,no_pilot08_outcomes=True,no_paid_calls=True,benchmark_ready=False)
    (OUT/'inventory.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    (OUT/'family-predicate-regeneration.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
