"""Predeclared raw/current-scope confirmation statistics; development answers only."""
from __future__ import annotations
import argparse
import json
import math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from misc.vp_5d_pilot import OUT,atomic_json,now,sha
from misc.vp_5d_metrics import summarize,completed
from misc.vp_cartesian_task import entry_scope_issue,oracle_issue
from misc import vp_campaign_candidates as old

ROOT=Path(__file__).resolve().parents[1]

def ratio(cluster,a,b,boot):
    aa=cluster[:,a];bb=cluster[:,b];den=bb.sum()
    if not den:return {'accuracy':None,'reason':'No completed weighted observations'}
    p=aa.sum()/den;g=len(aa);u=aa-p*bb
    se=math.sqrt(g/(g-1)*float(u@u))/den if g>1 else None
    num=boot@aa;denom=boot@bb;est=num[denom>0]/denom[denom>0]
    return {'accuracy':float(p),'family_cluster_sandwich_se':float(se) if se is not None else None,
      'family_bootstrap_se':float(est.std(ddof=1)),'family_bootstrap_percentile95':[float(x) for x in np.quantile(est,[.025,.975])],
      'bootstrap_valid_replicates':len(est)}

def estimate(rs,weights):
    clusters=defaultdict(lambda:np.zeros(8));paired=defaultdict(list)
    for r in rs:
        t=r['task'];key=t['derivation']['recipe_id']+'|'+t['morphology']['lakara']+'|'+t['morphology']['prayoga'];w=weights[key]
        complete=float(completed(r));correct=float(r['is_correct'] is True);usable_correct=complete*correct;f=t['campaign']['root_family']
        clusters[f]+=np.array([correct,usable_correct,complete,1,w*correct,w*usable_correct,w*complete,w]);paired[f].append(r)
    values=np.array(list(clusters.values()));g=len(values)
    boot=np.random.default_rng(202610070705).multinomial(g,[1/g]*g,size=10000)
    diagnostic={}
    for label,only_complete in [('all_request',False),('jointly_completed',True)]:
        pairs=[r for r in paired.values() if len(r)==2 and (not only_complete or all(completed(x) for x in r))]
        table=Counter('/'.join(str(int(completed(x) and bool(x['is_correct']))) for x in r) for r in pairs)
        diagnostic[label]={'families_with_two_retained_questions':len(pairs),'pair_correctness_table':dict(table),
          'agreement':sum(v for k,v in table.items() if k in {'0/0','1/1'})/len(pairs) if pairs else None}
    groups=defaultdict(list)
    for r in rs:
        t=r['task'];m=t['morphology'];recipe=t['derivation']['recipe_id']
        for key,value in [('recipe',recipe),('lakara',m['lakara']),('voice',m['prayoga']),('gana',t['dhatu']['gana']),
          ('recipe_aorist',recipe+'|'+('aorist' if m['lakara']=='Lun' else 'other'))]:groups[key+'::'+value].append(r)
    return {'summary':summarize(rs),'primary_all_requests':ratio(values,0,3,boot),'primary_completed':ratio(values,1,2,boot),
      'pilot04_mix_under_v3_all_requests':ratio(values,4,7,boot),'pilot04_mix_under_v3_completed':ratio(values,5,6,boot),
      'family_pair_diagnostics':diagnostic,'groups':{k:summarize(v) for k,v in groups.items()},
      'statuses':dict(Counter(r['status'] for r in rs)),'truncations':sum(bool(r['truncated']) for r in rs),
      'refusals':sum(r['status']=='refused' for r in rs),'family_load_histogram':dict(Counter(len(v) for v in paired.values()))}

def main(paths):
    frozen={t['id']:t for t in json.loads((OUT/'pilot-05.tasks.json').read_text())};es={e.code:e for e in old.load_entries()}
    spec=json.loads((OUT/'pilot-05.analysis-predeclaration.json').read_text());weights=spec['original_mix_comparator']['per_question_fixed_weights'];models={};maps={}
    for path in paths:
        data=json.loads(path.read_text());assert len(data)==480
        assert {r['task']['id'] for r in data}==set(frozen)
        for r in data:
            assert r['task']['campaign']['split']=='development'
            assert r['task']['gold_slp1']==frozen[r['task']['id']]['gold_slp1']
            assert r['task']['prompt_version']=='cartesian-5d-v3-sanskrit'
        excluded=[];kept=[]
        for r in data:
            t=r['task'];issue=entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)
            if issue:excluded.append({'id':t['id'],'reason':issue,'status':r['status'],'correct':r['is_correct']})
            else:kept.append(r)
        label=path.parent.name;models[label]={'source':str(path),'sha256':sha(path),'raw':estimate(data,weights),'current_scope':estimate(kept,weights),'excluded':excluded}
        maps[label]={r['task']['id']:r for r in kept}
    paired=None
    if len(maps)==2:
        (a,am),(b,bm)=maps.items();ids=set(am)&set(bm);joint=[i for i in ids if completed(am[i]) and completed(bm[i])]
        table=Counter(f'{int(bool(am[i]["is_correct"]))}/{int(bool(bm[i]["is_correct"]))}' for i in joint)
        paired={'model_order':[a,b],'same_eligible_questions':len(ids),'jointly_completed':len(joint),'joint_correctness_table':dict(table),
          'warning':'Separate completion/truncation/refusal patterns can change completed-only model comparisons.'}
    report={'created_at':now(),'task_sha256':sha(OUT/'pilot-05.tasks.json'),'analysis_predeclaration_sha256':sha(OUT/'pilot-05.analysis-predeclaration.json'),
      'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'completion_predicate':'misc.vp_cartesian_analyze.completed: completed status, non-null parsed answer and not truncated','models':models,'paired':paired,
      'limitations':['Development-adaptive grammar weights; sampling intervals do not include adaptation or oracle uncertainty.',
        'Pilot04 and pilot05 share v3, but grammar weights, family eligibility and prospective source holds differ; standardization is not a randomized causal comparison.',
        '240 two-question families do not independently establish release precision across other family allocations.',
        'All-request and completed-only results remain parallel; refusals/truncations are not silently converted into linguistic errors or discarded to meet a target.'],
      'raw_records_changed':False,'benchmark_ready':False}
    name='pilot-05.analysis-'+('-'.join(p.parent.name.split('-')[0] for p in paths))+'.json';atomic_json(OUT/name,report)
    print(json.dumps({'output':str(OUT/name),'models':{k:{scope:v[scope]['summary'] for scope in ['raw','current_scope']} for k,v in models.items()},'paired':paired},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('results',nargs='+',type=Path);a=p.parse_args();main(a.results)
