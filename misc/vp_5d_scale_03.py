"""Audit grammar supply and family-dependent precision for pilot03 weights."""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc.vp_5d_prepare_03 import OUT,SPLIT,RECIPES,GANAS,LAKARAS,EXCLUDED_RULES,old,lexical_issue,status,slots,atomic_json,now,sha
from misc.vp_cartesian_task import oracle_issue,entry_scope_issue
from misc.vp_5d_release_feasibility import Dinic,MinCost,apportion
from misc.vp_5d_calibration_analysis_02 import summarize
from vidyut.prakriya import Vyakarana,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana

PN=list(itertools.product(['Prathama','Madhyama','Uttama'],['Eka','Dvi','Bahu']))
WEIGHTS=Counter('|'.join((s['recipe'],s['morphology']['lakara'],s['morphology']['prayoga'])) for s in slots())


def census():
    path=OUT/'pilot-03.scale-supply.json'
    if path.exists():raise RuntimeError('Preserve existing supply census')
    start=time.monotonic();assignment=json.loads(SPLIT.read_text())['families'];es={}
    for e in old.load_entries():
        if assignment[old.family(e)]['split']=='test':es.setdefault(old.family(e),e)
    v=Vyakarana();bases={f:sorted({p.text for p in v.derive(e.dhatu)}) for f,e in es.items()}
    rows=[];reject=Counter();attempted=0;accepted=0
    for index,(family,e) in enumerate(es.items(),1):
        masks={}
        for recipe,ops in RECIPES.items():
            issue=lexical_issue(e,recipe,bases)
            if issue:reject['family_recipe:'+issue]+=1;continue
            d=e.dhatu.with_sanadi([getattr(Sanadi,x) for x in ops])
            for cell in WEIGHTS:
                rec,la,voice=cell.split('|')
                if rec!=recipe:continue
                mask=0
                for bit,(pu,va) in enumerate(PN):
                    attempted+=1
                    ps=v.derive(Pada.Tinanta(dhatu=d,lakara=getattr(Lakara,la),prayoga=getattr(Prayoga,voice),
                        purusha=getattr(Purusha,pu),vacana=getattr(Vacana,va)))
                    if not ps:reject['tuple:empty_engine_derivation']+=1;continue
                    if len({p.text for p in ps})>64:reject['tuple:more_than64variants']+=1;continue
                    rules={h.code for p in ps for h in p.history if old.name(h.source)=='Ashtadhyayi'}
                    probe={'dhatu':{'code':e.code},'morphology':dict(lakara=la,prayoga=voice,purusha=pu,vacana=va),
                        'campaign':{'trace_rule_ids':list(rules)},'derivation':{'sanadi':ops}}
                    issue=oracle_issue(probe)
                    if not issue and len(ops)>1 and rules&EXCLUDED_RULES:issue='extended_nested_rule_quarantine'
                    if issue:reject['tuple:'+issue]+=1;continue
                    mask|=1<<bit;accepted+=1
                if mask:masks[cell]=mask
        rows.append({'family':family,'gana':old.name(e.dhatu.gana),'eligible_person_number_masks':masks})
        if index%100==0:
            status('Checking scale under frozen grammar weights',f'Assessed{index}/1000 reserved-test families for input availability only;{accepted:,} accepted tuples. No model answers or final membership read/selected.')
            print(json.dumps({'families':index,'accepted':accepted,'seconds':round(time.monotonic()-start,1)}),flush=True)
    # RL roots remain separately allocated; a present-active probe measures available families only.
    rl={}
    for e in old.load_entries():
        if assignment[old.family(e)]['split']=='rl_train':rl.setdefault(old.family(e),e)
    rb={f:sorted({p.text for p in v.derive(e.dhatu)}) for f,e in rl.items()}
    from misc.vp_5d_prepare_03 import task_for
    rl_counts={r:sum(task_for(e,r,dict(lakara='Lat',prayoga='Kartari',purusha='Prathama',vacana='Eka'),rb,'rl_train')[0] is not None for e in rl.values()) for r in RECIPES}
    atomic_json(path,{'created_at':now(),'vp_version':__import__('vidyut').__version__,'rows':rows,
        'attempted_tuples':attempted,'accepted_tuples':accepted,'rejections':dict(reject),'elapsed_seconds':time.monotonic()-start,
        'policy':'Shared policy04 plus nested quarantine extended to intensive-luk→causative.',
        'rl_training':{'reserved_families':len(rl),'eligible_families_in_present_active_probe':rl_counts,
            'limitation':'Probe only; no final RL task membership generated.'},
        'family_split_sha256':sha(SPLIT),'dictionary_sha256':sha(old.TSV),'script_sha256':sha(Path(__file__)),
        'no_model_results_read':True,'no_gold_forms_retained':True,'no_final_membership_selected':True})


def capacity(rows,n,cap,strict,optimize=False):
    quotas=apportion(WEIGHTS,n);gq=apportion(GANAS,n) if strict else None
    net=MinCost() if optimize else Dinic();source='source';sink='sink';edges={};cells=[]
    if gq:
        for g,q in gq.items():net.edge(source,('g',g),q)
    for i,row in enumerate(rows):
        fn=('f',i);start=('g',row['gana']) if gq else source
        edges[i]=[net.edge(start,fn,1,0),net.edge(start,fn,cap-1,1)] if optimize else [net.edge(start,fn,cap)]
        for cell,mask in row['eligible_person_number_masks'].items():
            if cell in quotas:cells.append(net.edge(fn,('c',cell),min(cap,mask.bit_count())))
    for c,q in quotas.items():net.edge(('c',c),sink,q)
    maximum=net.flow(source,sink,n)[0] if optimize else net.flow(source,sink)
    loads=Counter(sum(e[3]-e[1] for e in ee) for ee in edges.values());loads.pop(0,None)
    out={'n':n,'family_cap':cap,'gana_weights':'pilot03' if strict else 'relaxed',
        'maximum_allocatable':maximum,'feasible':maximum==n,'distinct_families':sum(loads.values()),'family_load_histogram':dict(loads)}
    if optimize and maximum==n:
        factor=sum(k*k*v for k,v in loads.items())/n-1
        out.update(family_pair_correlation_multiplier=factor,
            se_pp_at79_by_assumed_intraclass_correlation={str(rho):100*math.sqrt(.79*.21/n*(1+factor*rho)) for rho in [0,.05,.1,.2,.3,.5,1]},
            largest_rho_compatible_with_se_below1pp=((.0001*n/(.79*.21))-1)/factor if factor else None,
            all_nine_person_number_options_per_nonempty_cell=all(mask==511 for row in rows for mask in row['eligible_person_number_masks'].values()))
    return out


def analyze():
    source=OUT/'pilot-03.scale-supply.json';data=json.loads(source.read_text());rows=data['rows']
    recipe=defaultdict(lambda:{'families':set(),'tuples':0,'gana_families':Counter()})
    for row in rows:
        seen=set()
        for c,mask in row['eligible_person_number_masks'].items():
            r=c.split('|')[0];recipe[r]['families'].add(row['family']);recipe[r]['tuples']+=mask.bit_count()
            if r not in seen:recipe[r]['gana_families'][row['gana']]+=1;seen.add(r)
    summaries={r:{'families':len(v['families']),'tuples':v['tuples'],'gana_families':dict(v['gana_families'])} for r,v in recipe.items()}
    checks=[];optimized=[]
    for n in [1000,1660,2000,2400]:
        for strict in [True,False]:
            for cap in range(1,7):
                result=capacity(rows,n,cap,strict);checks.append(result)
                if result['feasible']:
                    optimized.append(capacity(rows,n,cap,strict,True));break
    report={'created_at':now(),'source_sha256':sha(source),'recipe_supply':summaries,
        'accepted_tuples':data['accepted_tuples'],'rl_training':data['rl_training'],
        'capacity_checks':checks,'family_optimized_feasible_designs':optimized,
        'interpretation':['The original cap2/1601 proposal does not transport automatically to this intensive-heavy menu.',
            'A strict1pp SE at79% needs at least1660 IID observations; displayed family correlations are sensitivity assumptions, not measured values.',
            'Model responses within a root family may be dependent. No current pilot establishes final cluster SE or strongest-reference79–81% accuracy.',
            'Class quotas in this developmental pilot are not a mandatory final distribution; both exact-pilot and relaxed-class feasibility are shown.',
            'All results are supply witnesses only, with no exported final task or family membership. Existing test/development/RL split remains unchanged.']}
    atomic_json(OUT/'pilot-03.scale-analysis.json',report)
    print(json.dumps({'recipes':summaries,'optimized':optimized},indent=2))


def cross_panel():
    es={e.code:e for e in old.load_entries()};panels={};excluded=[]
    for panel in ['01','02']:
        rs=json.loads((ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-{panel}/results.json').read_text());kept=[]
        for r in rs:
            t=r['task'];assert t['campaign']['split']=='development'
            issue=entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)
            if issue:excluded.append({'panel':panel,'id':t['id'],'reason':issue})
            else:kept.append(r)
        panels[panel]=kept
    v=Vyakarana();bases={code:sorted({p.text for p in v.derive(e.dhatu)}) for code,e in es.items()};groups={}
    for panel,rs in dict(panels,pooled=panels['01']+panels['02']).items():
        cells=defaultdict(list)
        for r in rs:
            t=r['task'];recipe=t['derivation']['recipe_id'];m=t['morphology'];rules=set(t['campaign']['trace_rule_ids'])
            vowels=''.join(c for c in bases[t['dhatu']['code']][0] if c in 'aAiIuUfFxXeEoO')
            keys=['recipe::'+recipe,'lakara::'+m['lakara'],'recipe_lakara::'+recipe+'|'+m['lakara'],
                'recipe_voice::'+recipe+'|'+m['prayoga'],'recipe_vowel::'+recipe+'|'+vowels]
            if recipe=='causative_of_intensive':
                keys+=['mechanism::'+('aorist' if m['lakara']=='Lun' else 'other_lakaras'),
                    'mechanism::'+('short_i_u_or_long_r' if vowels in {'i','u','F'} else 'other_vowels'),
                    'mechanism::'+('ya_deletion' if '6.4.49' in rules else 'ya_retained')]
            for key in keys:cells[key].append(r)
        groups[panel]={k:summarize(rs) for k,rs in cells.items()}
    pooled=groups['pooled'];a=pooled['mechanism::aorist'];b=pooled['mechanism::other_lakaras'];weighted=.25*a['completed_accuracy']+.75*b['completed_accuracy']
    report={'created_at':now(),'policy':'oracle-policy-04','excluded':excluded,
        'panels':{k:summarize(v) for k,v in panels.items()},'pooled':summarize(panels['01']+panels['02']),'groups':groups,
        'main_recipe_25pct_aorist_reweighting':{'estimate':weighted,
            'naive_se':math.sqrt(.25**2*a['completed_accuracy']*(1-a['completed_accuracy'])/a['completed']+.75**2*b['completed_accuracy']*(1-b['completed_accuracy'])/b['completed']),
            'warning':'Posthoc developmental reweighting with8 aorist answers, altered class/voice mix, family reuse and unmeasured new-recipe performance. Not an expected pilot score or evidence of final target attainment.'},
        'findings':['Policy04 does not change intensive→causative64/77, including2/8 aorist and62/69 non-aorist.',
            'Stem-preservation errors recur in multiple tenses and vowel groups. Neither short-vowel membership nor one rare root establishes a broad target group.',
            'The first intensive-luk79% result did not replicate; its policy04 pooled result is65/73.',
            'Pilot03 independently tests preserved reduplication at25% aorist and contrasting causal strengthening across all other lakaras.',
            'No earlier individual errors are selected into pilot03; all180 inputs are new and153 root families are absent from the earlier5D panels.'],
        'old_saved_panels_changed':False,'heldout_model_answers_read':False}
    atomic_json(OUT/'pilot-03.cross-panel-analysis.json',report)
    print(json.dumps({'panels':report['panels'],'reweighting':report['main_recipe_25pct_aorist_reweighting']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['census','analyze','cross-panel']);a=p.parse_args()
    {'census':census,'analyze':analyze,'cross-panel':cross_panel}[a.command]()
