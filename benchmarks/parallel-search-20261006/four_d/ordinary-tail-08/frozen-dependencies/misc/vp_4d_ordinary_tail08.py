"""Input-only ordinary dictionary-tail census; no model results or provider APIs."""
import hashlib,json,sqlite3
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

from misc.vp_4d_coverage05 import ROOT,B,COORDS,read,sha,key,metadata,issue,repeat_mechanism,stats
from misc.vp_cartesian_task import entries_by_code,make_task
from misc.vp_campaign_candidates import family,name

OUT=B/'four_d/ordinary-tail-08'


def save(n,d):
    p=OUT/n;assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def ending_region(r):
    rs=set(r['rules']);la=r['lakara']
    labels=[]
    if la=='Lut' and rs & {'7.4.50','7.4.51','7.4.52','6.4.143'}:labels.append('periphrastic_future_ending_changes')
    if la in {'VidhiLin','AshirLin'} and rs & {'3.4.105','3.4.106','3.4.108'}:labels.append('ling_personal_ending_changes')
    if la=='Lun' and rs & {'7.3.96','8.2.28','3.4.109'}:labels.append('sigmatic_aorist_ending_changes')
    return labels


def ordinary(r):
    return r['prayoga']=='Kartari' and r['lakara'] not in {'Lot','Lit'} and not repeat_mechanism(r)


def main():
    es=entries_by_code();split=read(ROOT/'benchmarks/creation-campaign-20261006/family-split.json')['families']
    save('design.json',dict(created_at=datetime.now(timezone.utc).isoformat(),run_id='ordinary-tail-08',policy='oracle-policy-21',
        objective='Measure broad ordinary dictionary family and tense coverage. No model outcome, learned predictor or failure selection.',
        domain='Shared21 plus existing local holds. Broad tail restricts to Kartari, excludes allLit/allLot plus previously examined adanta/dhvam/specialized-it/Kutadi contexts. No added derivation, prefix, selected pada or dialect.',
        comparisons=['Current six completed xHigh panels:01–06, inputs only','Historical ordinary inputs from original6687 and both campaign directories, including zero-operation metadata','Pending pilot07 input footprint separately, with no outcomes'],
        primary_tail='Families with no eligible input in the six completed xHigh panels, intersected with the broad ordinary domain. Report absent family×tense coverage separately; do not claim individual rules are new.',
        optional_diagnostic='At most96 fresh questions from96 currently untested development families. Six-class coverage follows actual family supply; no requirement to invent all-ten-class support. A broad unknown-region screen is not a difficulty forecast or final calibration.',
        no_paid_calls=True,no_model_answers=True,benchmark_ready=False))
    universes={'development':{},'test':{}}
    dbpath=ROOT/'benchmarks/creation-campaign-20261006/candidates.sqlite'
    db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
    for tid,fam,spl,code,la,pr,pu,va,gold,rules,steps,variants in db.execute("SELECT * FROM candidates WHERE split IN ('development','test')"):
        e=es[code];assert split[family(e)]['split']==spl
        t=dict(id=tid,dhatu=dict(code=code,aupadeshika=e.dhatu.aupadeshika,gana=name(e.dhatu.gana)),
            morphology=dict(zip(COORDS,[la,pr,pu,va])),gold_slp1=json.loads(gold),
            campaign=dict(root_family=fam,trace_rule_ids=json.loads(rules)))
        if not issue(t,e):universes[spl].setdefault(key(t),metadata(t))
    db.close()
    current={};current_sources=[]
    for i in range(1,7):
        p=ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-four-d-pilot-{i:02d}/tasks.json'
        current_sources.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
        for t in read(p):
            assert split[family(es[t['dhatu']['code']])]['split']=='development'
            if not issue(t,es[t['dhatu']['code']]):current[key(t)]=metadata(t)
    cf={r['family'] for r in current.values()};cft={(r['family'],r['lakara']) for r in current.values()}
    history={};history_keys=set();sources=[]
    paths=[ROOT/'benchmarks/full-tasks.json']
    for folder in ['creation-campaign-20261006','iterative-goal-20261006']:
        paths+=sorted((ROOT/'benchmarks'/folder/'jobs').glob('*/tasks.json'))
    for p in paths:
        ordinary_rows=0
        for top in read(p):
            for t in top.get('forms',[top]):
                if not isinstance(t,dict) or 'dhatu' not in t or set(t.get('morphology',{}))!=set(COORDS):continue
                der=t.get('derivation') or {}
                if der.get('sanadi') or der.get('prefixes'):continue
                if any(o.get(k) not in (None,'',[]) for o in [t,t['dhatu'],t['morphology']] for k in ['prefixes','sanadi','pada','dhatu_pada']):continue
                ordinary_rows+=1;history_keys.add(key(t))
                code=t['dhatu'].get('code')
                if code not in es or split[family(es[code])]['split']!='development':continue
                k=key(t)
                if k in universes['development']:history[k]=universes['development'][k]
        sources.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),ordinary_rows=ordinary_rows))
    subsets={}
    for spl,u in universes.items():
        broad=[r for r in u.values() if ordinary(r)]
        subsets[spl]=dict(full=stats(list(u.values())),broad=stats(broad))
        if spl=='development':
            unseen=[r for r in broad if r['family'] not in cf]
            fresh=[r for k,r in u.items() if ordinary(r) and r['family'] not in cf and k not in history_keys]
            subsets[spl].update(unseen_family=stats(unseen),fresh_unseen_family=stats(fresh),
                unseen_family_class_counts=dict(Counter(next(r['gana']for r in unseen if r['family']==f) for f in {r['family']for r in unseen})),
                unseen_family_lakara=stats([r for r in broad if (r['family'],r['lakara']) not in cft]))
            save('fresh-tail-metadata.json',fresh)
    regions={}
    for label in ['periphrastic_future_ending_changes','ling_personal_ending_changes','sigmatic_aorist_ending_changes']:
        regions[label]=dict(supply={spl:stats([r for r in u.values() if ordinary(r) and label in ending_region(r)])for spl,u in universes.items()},
            current_six=stats([r for r in current.values() if ordinary(r) and label in ending_region(r)]),
            broader_history=stats([r for r in history.values() if ordinary(r) and label in ending_region(r)]))
    historical_tail=[r for r in history.values() if ordinary(r) and r['family'] not in cf]
    pending=read(B/'four_d/coverage-gap-06/cin-candidate-inputs.json')
    # Finite sentinels certify metadata still matches installed policy/engine.
    sentinels=sorted(fresh,key=lambda r:hashlib.sha256(r['id'].encode()).hexdigest())[:128]
    for r in sentinels:
        t=make_task(es[r['code']],'development',{k:r[k]for k in COORDS})
        assert t and not issue(t,es[r['code']]) and t['campaign']['trace_rule_ids']==r['rules']
    out=dict(created_at=datetime.now(timezone.utc).isoformat(),policy='oracle-policy-21',
        source_hashes=dict(script=sha(Path(__file__)),adapter=sha(ROOT/'misc/vp_cartesian_task.py'),master_split=sha(ROOT/'benchmarks/creation-campaign-20261006/family-split.json'),database=sha(dbpath)),
        cohorts=subsets,current_six=stats(list(current.values())),current_family_class_counts=dict(Counter(next(r['gana']for r in current.values() if r['family']==f)for f in cf)),
        historical_tail_inputs=stats(historical_tail),broad_ending_regions=regions,
        pending_cin_families=len({t['campaign']['root_family']for t in pending}),
        pending_cin_overlap_unseen_tail_families=len({t['campaign']['root_family']for t in pending}&{r['family']for r in fresh}),
        current_sources=current_sources,history_sources=sources,sentinel_regeneration=128,
        no_model_answers_read=True,no_paid_calls=True,benchmark_ready=False)
    save('inventory.json',out)
    print(json.dumps({k:out[k]for k in ['cohorts','current_six','historical_tail_inputs','broad_ending_regions','pending_cin_overlap_unseen_tail_families']},indent=2))


if __name__=='__main__':main()
