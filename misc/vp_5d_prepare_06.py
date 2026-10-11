"""Policy13 prospective45%-aorist panel; input-only census and selection."""
from __future__ import annotations
import json,math,random,time
from collections import Counter
from pathlib import Path
from misc.vp_5d_prepare_04 import ROOT,OUT,RECIPES,FAMILY_GANAS,PN,status,atomic_json,now,sha
from misc.vp_5d_prepare_03 import SOURCE_ROOTS,task_for
from misc.vp_5d_pilot import entries,SPLIT
from misc.vp_5d_prepare_05 import history,UNRESOLVED,VERSION
from misc.vp_5d_novelty_04 import normalized
from misc.vp_5d_release_feasibility import MinCost,Dinic,apportion
from misc.vp_cartesian_task import make_task,validate_task
from misc.vp_goal_validate import validate
from vidyut.prakriya import Vyakarana
from misc import vp_campaign_candidates as old
SEED=202610070906

def quotas(n,lun_fraction=.45):
    baseline=json.loads((OUT/'pilot-04.plan.json').read_text())
    lun=round(n*lun_fraction);recipes=apportion(baseline['recipe_counts'],n)
    tense={'Lun':lun,**apportion({l:q for l,q in baseline['lakara_counts'].items() if l!='Lun'},n-lun)}
    joint={};net=MinCost();edges=[]
    for r,nr in recipes.items():net.edge('s',('r',r),nr-sum(math.floor(nr*nl/n) for nl in tense.values()))
    for l,nl in tense.items():net.edge(('l',l),'t',nl-sum(math.floor(nr*nl/n) for nr in recipes.values()))
    for r,nr in recipes.items():
        for l,nl in tense.items():
            ideal=nr*nl/n;joint[r,l]=math.floor(ideal)
            edges.append((r,l,net.edge(('r',r),('l',l),1,round(10000*(1-(ideal%1))))))
    need=n-sum(joint.values());assert net.flow('s','t',need)[0]==need
    for r,l,e in edges:joint[r,l]+=e[3]-e[1]
    passive=round(n*.1);pas=apportion({c:q for c,q in baseline['cell_counts'].items() if c.endswith('|Karmani')},passive);cells={}
    for (r,l),q in joint.items():
        pp=pas.get(r+'|'+l+'|Karmani',0);assert pp<=q
        cells[r+'|'+l+'|Kartari']=q-pp
        if pp:cells[r+'|'+l+'|Karmani']=pp
    fg=apportion(FAMILY_GANAS,n//2)
    # Rare classes remain represented; actual supply caps will be applied uniformly.
    pn={ '/'.join(x):n//9+(i< n%9) for i,x in enumerate(PN)}
    if n%9==6:pn={'/'.join(x):n//9+(i not in {0,4,8}) for i,x in enumerate(PN)}
    return dict(n=n,recipe_counts=recipes,lakara_counts=tense,passive_count=passive,cell_counts=cells,family_count=n//2,family_gana_counts=fg,gana_counts={g:2*q for g,q in fg.items()},person_number_counts=pn)

def census():
    es=entries();v=Vyakarana();bases={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in es.items()};used,hf,ha=history()
    candidates={};reject=Counter();last=time.monotonic();cells=quotas(720)['cell_counts']
    for i,(f,e) in enumerate(es.items(),1):
        if e.code in SOURCE_ROOTS or e.code in UNRESOLVED:continue
        cc=[]
        for c in cells:
            r,l,vo=c.split('|');t,issue=task_for(e,r,dict(lakara=l,prayoga=vo,purusha='Prathama',vacana='Eka'),bases)
            if issue:reject[issue]+=1
            elif any((e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(RECIPES[r]),l,vo,pu,va) not in used for pu,va in PN):cc.append(c)
        if len({c.split('|')[1] for c in cc})>=2:candidates[f]=cc
        if time.monotonic()-last>45:
            status('Checking pilot06 input supply',f'Assessed {i}/{len(es)} development families under policy13. Checking exact fresh tuples and two distinct tenses; no model outcomes read for membership.');last=time.monotonic()
    out=dict(created_at=now(),policy='oracle-policy-13',shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),history_audit=ha,candidates=candidates,rejections=dict(reject),source_holds=UNRESOLVED,bases=bases)
    atomic_json(OUT/'pilot-06.development-supply.json',out)
    print(json.dumps({'families':len(candidates),'aorist_by_recipe':{r:sum(r+'|Lun|Kartari' in cc for cc in candidates.values()) for r in RECIPES},'aorist_union':sum(any('|Lun|' in c for c in cc) for cc in candidates.values())},indent=2))

def assign(p,candidates,es,seen_families,rng):
    fg=p['family_gana_counts'];nl=p['lakara_counts']['Lun'];n=p['n']
    lp={g:[f for f in candidates if old.name(es[f].dhatu.gana)==g and any('|Lun|' in c for c in candidates[f])] for g in fg}
    # Class quotas are fixed before membership; report infeasible instead of silently changing.
    lq=apportion(fg,nl)
    while any(lq[g]>min(fg[g],len(lp[g])) for g in lq):
        for g in lq:lq[g]=min(lq[g],fg[g],len(lp[g]))
        need=nl-sum(lq.values());choices=[g for g in lq if lq[g]<min(fg[g],len(lp[g]))]
        if not choices:raise RuntimeError('Insufficient distinct aorist families under class quota')
        for g in sorted(choices,key=lambda g:(lq[g]/fg[g],g))[:need]:lq[g]+=1
    for attempt in range(200):
        net=Dinic();edges=[]
        for g,q in lq.items():
            net.edge('s',('g',g),q);pool=list(lp[g]);rng.shuffle(pool);pool.sort(key=lambda f:f in seen_families)
            for f in pool:
                net.edge(('g',g),('f',f),1);cc=[c for c in candidates[f] if '|Lun|' in c];rng.shuffle(cc)
                for c in cc:edges.append((f,c,net.edge(('f',f),('c',c),1)))
        for c,q in p['cell_counts'].items():
            if '|Lun|' in c:net.edge(('c',c),'t',q)
        fl=net.flow('s','t')
        if fl!=nl:raise RuntimeError(f'Aorist recipe flow {fl}/{nl}')
        aa=[(f,c) for f,c,e in edges if e[3]-e[1]];lf={f for f,c in aa};chosen=sorted(lf)
        for g,q in fg.items():
            pool=[f for f in candidates if f not in lf and old.name(es[f].dhatu.gana)==g and len({c.split('|')[1] for c in candidates[f] if '|Lun|' not in c and (g=='Curadi' or c.split('|')[0]!='desiderative')})>=2]
            rng.shuffle(pool);pool.sort(key=lambda f:f in seen_families)
            if len(pool)<q-lq[g]:raise RuntimeError('Non-aorist class supply '+g)
            chosen.extend(pool[:q-lq[g]])
        rng.shuffle(chosen);net=Dinic();edges=[]
        for f in chosen:
            net.edge('s',('f',f),1 if f in lf else 2)
            las=sorted({c.split('|')[1] for c in candidates[f] if '|Lun|' not in c});rng.shuffle(las)
            for la in las:net.edge(('f',f),('fl',f,la),1)
            cc=[c for c in candidates[f] if '|Lun|' not in c];rng.shuffle(cc)
            for c in cc:edges.append((f,c,net.edge(('fl',f,c.split('|')[1]),('c',c),1)))
        for c,q in p['cell_counts'].items():
            if '|Lun|' not in c:net.edge(('c',c),'t',q)
        if net.flow('s','t')==n-nl:return aa+[(f,c) for f,c,e in edges if e[3]-e[1]],chosen,lq,attempt
    raise RuntimeError('Non-aorist pairing flow failed')

def feasibility():
    raw=json.loads((OUT/'pilot-06.development-supply.json').read_text());assert raw['shared_adapter_sha256']==sha(ROOT/'misc/vp_cartesian_task.py')
    es=entries();cc=raw['candidates'];out=[]
    for n in [600,720]:
        p=quotas(n)
        try:
            aa,chosen,lq,attempt=assign(p,cc,es,set(),random.Random(SEED))
            out.append({'design':p,'feasible':True,'families':len(chosen),'aorist_families':p['lakara_counts']['Lun'],'aorist_family_classes':lq,'allocation_attempt':attempt,'membership_retained':False})
        except RuntimeError as e:out.append({'design':p,'feasible':False,'reason':str(e)})
    data=dict(created_at=now(),policy='oracle-policy-13',shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),supply_sha256=sha(OUT/'pilot-06.development-supply.json'),checks=out,no_model_answers_read=True,no_membership_retained=True)
    atomic_json(OUT/'pilot-06.size-feasibility.json',data);print(json.dumps([{k:v for k,v in x.items() if k!='design'}|{'n':x['design']['n']} for x in out],indent=2))


def plan():
    path=OUT/'pilot-06.plan.json'
    if path.exists():raise RuntimeError('Preserve frozen plan')
    p=quotas(600);original=p['family_gana_counts'];p['family_gana_counts']=dict(zip(FAMILY_GANAS,[200,11,2,21,4,30,6,2,14,10]));p['gana_counts']={g:2*q for g,q in p['family_gana_counts'].items()}
    prior=json.loads((OUT/'pilot-05.plan.json').read_text())
    p.update(frozen_at=now(),seed=SEED,split='development',oracle_policy='oracle-policy-13',prompt_version=VERSION,recipe_operations=RECIPES,tasks_per_family=2,
      previous_panel_family_gana_counts=FAMILY_GANAS,initial_proportionally_scaled_family_gana_counts=original,
      class_adjustment_reason='Proportional scaling fails exact aorist recipe flow:262/270 for600 and302/324 for720. Revised600 class quotas reflect input-only source-qualified supply, retain all ten classes, and use less Bhvadi concentration than the720 alternative. Each family contributes exactly two distinct tenses.',
      forecast_scope='The80.51% pooled completed forecast standardizes recipe×lakara×voice only. It DOES NOT adjust for changed class proportions, changed aorist-eligible family composition or historical family exposure; no class-invariance or randomized-comparability claim is made.',
      alternatives='720 with324 aorist families is feasible only after larger class shifts, including255/360 Bhvadi families. Its nested aorists require about302 of311 available intensive-aorist families.600 is chosen for greater sampling latitude and bounded cost, not from any unseen outcome.',
      unresolved_prospective_exclusions=UNRESOLVED,source_control_codes_excluded=sorted(SOURCE_ROOTS),
      sampling_algorithm='Seeded selection uses dictionary inputs, grammar eligibility and prior input exposure only. Allocate270 distinct aorist families across fixed class quotas with recipe flow, then30 other families; give every family two distinct lakaras. Exact recipe×tense×voice cells and balanced person/number margins use flow. Prefer families absent from named5D01–05 within eligible strata. Exclude every normalized comparable tuple from both campaign ledgers. Never use individual model correctness.',
      family_allocation_tradeoff='270/300 families must be aorist-eligible;252 have a nested aorist. This changes eligible-family composition and limits transport of earlier reweighted forecasts. Non-aorist coverage remains55%.',
      reason='Raise Lun from40% to45% as one broad grammatical intervention supported by repeated extra-reduplication errors across roots and both v3 panels. Preserve the three recipe weights, ten tenses, ten classes and10% passive. Existing reduplication under6.1.8/11 distinguishes the active causal-aorist setting; mere chain length is not the difficulty claim.',
      primary_estimand='Fixed600-question distribution: unweighted all-request and completion-conditioned scores in parallel; worst/best missing-response bounds.',
      comparator='Within-panel fixed reweighting to original pilot04 recipe×tense×voice cells under the same v3 renderer. It does not adjust for class/family composition and is not independent replication.',
      uncertainty='Family sandwich and10000 seeded whole-family bootstrap replicates, preserving both questions per family and zero-completion families. Also iid SE and class-stratified bootstrap sensitivity.600 is calibration and cannot establish sub1pp precision. Future final qualification must check both iid and family sandwich SE<.01 for both references.',
      fixed_decision_rule=prior['fixed_decision_rule'].replace('this panel','this600-question panel'),
      history_policy='Exact new normalized grammar tuples, not necessarily new families. All historical task/component inputs from both campaign ledgers are compared; no held-out model answers are read.',
      benchmark_ready=False)
    assert sum(p['gana_counts'].values())==p['n'];atomic_json(path,p)
    status('Pilot06 grammar and advance criteria frozen','Frozen600-question plan:270 aorists,60 passives,400/160/40 recipes and all ten classes/tenses.300 families each receive two distinct tenses. The forecast does not adjust for the documented class-composition change. No answers used for membership.')

def generate():
    pp=OUT/'pilot-06.plan.json';output=OUT/'pilot-06.tasks.json'
    if output.exists():raise RuntimeError('Preserve frozen membership')
    p=json.loads(pp.read_text());raw=json.loads((OUT/'pilot-06.development-supply.json').read_text());assert raw['shared_adapter_sha256']==sha(ROOT/'misc/vp_cartesian_task.py')
    used,historical_families,ha=history();assert all(ha[k]==raw['history_audit'][k] for k in ['task_files','counts','unique_matching_tuples']),'Historical input tasks changed: refresh input-only census before membership'
    es=entries();candidates=raw['candidates'];bases=raw['bases'];rng=random.Random(p['seed'])
    prior=[t for panel in ['01','02','03','04','05'] for t in json.loads((OUT/f'pilot-{panel}.tasks.json').read_text())];seen_families={t['campaign']['root_family'] for t in prior}
    assigned,chosen,lq,attempt=assign(p,candidates,es,seen_families,rng);rng.shuffle(assigned);net=Dinic();edges=[]
    for i,(f,c) in enumerate(assigned):
        net.edge('s',('slot',i),1);r,l,vo=c.split('|');options=list(PN);rng.shuffle(options)
        for pu,va in options:
            e=es[f];sig=(e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(RECIPES[r]),l,vo,pu,va)
            if sig not in used:edges.append((i,pu,va,net.edge(('slot',i),('pn',pu,va),1)))
    for pv,q in p['person_number_counts'].items():net.edge(('pn',*pv.split('/')),'t',q)
    assert net.flow('s','t')==p['n'],'Fresh balanced PN flow failed'
    tasks=[]
    for i,pu,va,ed in edges:
        if not ed[3]-ed[1]:continue
        f,c=assigned[i];r,l,vo=c.split('|');e=es[f];m=dict(lakara=l,prayoga=vo,purusha=pu,vacana=va)
        probe,issue=task_for(e,r,m,bases);assert not issue,issue
        t=make_task(e,'development',m,r,RECIPES[r],prompt_version=VERSION);assert t['gold_slp1']==probe['gold_slp1']
        t['campaign'].update(panel='five-d-pilot-06',slot=i,plan_sha256=sha(pp),oracle_policy='oracle-policy-13',lexical_bases=bases[f],selection_reason=p['sampling_algorithm'],sampling_cell={'recipe_id':r,'lakaras':[l],'prayogas':[vo]},audit_status='Current shared policy13, prospective source holds and independent recipe controls; complete rare forms are not all separately attested.')
        assert normalized(t)[0] not in used;validate_task(t,e,'development');tasks.append(t)
    rng.shuffle(tasks);assert len(tasks)==len({normalized(t)[0] for t in tasks})==p['n']
    assert Counter(t['campaign']['root_family'] for t in tasks)==Counter({f:2 for f in chosen})
    assert Counter(t['dhatu']['gana'] for t in tasks)==Counter(p['gana_counts'])
    assert Counter(t['derivation']['recipe_id']+'|'+t['morphology']['lakara']+'|'+t['morphology']['prayoga'] for t in tasks)==Counter(p['cell_counts'])
    assert Counter(t['morphology']['purusha']+'/'+t['morphology']['vacana'] for t in tasks)==Counter(p['person_number_counts'])
    for f in chosen:assert len({t['morphology']['lakara'] for t in tasks if t['campaign']['root_family']==f})==2
    audit=validate(tasks,'development');atomic_json(output,tasks);atomic_json(OUT/'pilot-06.runner-audit.json',audit)
    ha.update(created_at=now(),task_sha256=sha(output),n=p['n'],overlap_count=0,all_questions_fresh=True,normalization='Exact visible citation and class, ordered Sanadi, all four coordinates; recursively inspect historical bundled forms, exclude prefixed or specified-pada shapes, ignore prompt versions and task IDs.',families_absent_from_all_historical_inputs=len(set(chosen)-historical_families),families_previously_in_historical_inputs=len(set(chosen)&historical_families),model_results_read_for_selection=False)
    atomic_json(OUT/'pilot-06.novelty-audit.json',ha)
    manifest=dict(created_at=now(),n=p['n'],family_count=len(chosen),family_load_histogram={'2':len(chosen)},distinct_lakaras_per_family=True,aorist_family_count=p['lakara_counts']['Lun'],aorist_family_gana_counts=lq,gana_counts=p['gana_counts'],recipe_counts=p['recipe_counts'],lakara_counts=p['lakara_counts'],voice_counts=dict(Counter(t['morphology']['prayoga'] for t in tasks)),person_number_counts=p['person_number_counts'],new_families_vs_named_five_d_01_to05=len(set(chosen)-seen_families),reused_families_vs_named_five_d_01_to05=len(set(chosen)&seen_families),task_sha256=sha(output),plan_sha256=sha(pp),script_sha256=sha(Path(__file__)),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),prompt_helper_sha256=sha(ROOT/'misc/vp_cartesian_prompt_v3.py'),sanskrit_helper_sha256=sha(ROOT/'misc/vp_sanskrit_prompt_v1.py'),family_split_sha256=sha(SPLIT),dictionary_sha256=sha(old.TSV),unresolved_prospective_exclusions=UNRESOLVED,prompt_version=VERSION,policy='oracle-policy-13',all_tasks_validated=True,status='Frozen for independent coordinator validation; no paid calls.',benchmark_ready=False)
    atomic_json(OUT/'pilot-06.manifest.json',manifest)
    priorplan=json.loads((OUT/'pilot-04.plan.json').read_text());spec=dict(created_at=now(),task_sha256=sha(output),family_bootstrap_seed=202610070906,family_bootstrap_replicates=10000,primary=p['primary_estimand'],original_mix_comparator={'target':'Pilot04 original recipe×tense×voice cells under v3','per_question_fixed_weights':{c:priorplan['cell_counts'][c]/480*p['n']/q for c,q in p['cell_counts'].items()},'warning':p['forecast_scope']},prespecified_groups=['recipe','lakara','voice','gana','recipe by aorist/non-aorist','recipe by voice','recipe by lakara by voice'],decision_rule=p['fixed_decision_rule'],uncertainty=p['uncertainty'],no_questionwise_error_selection=True,benchmark_ready=False)
    atomic_json(OUT/'pilot-06.analysis-predeclaration.json',spec)
    request=dict(created_at=now(),track='five_d',label='opus-five-d-pilot-06',n=p['n'],phase='fresh_development_confirmation',status='ready_for_coordinator_review_not_submitted',task_file=str(output),task_file_sha256=sha(output),split='development',provider='Anthropic',reference_model='Opus5.5',reasoning_effort='xhigh',max_output_tokens=16384,prompt_version=VERSION,task_type='cartesian_5d',plan=str(pp),manifest=str(OUT/'pilot-06.manifest.json'),audit=str(OUT/'pilot-06.runner-audit.json'),worker_paid_calls=0,astra_pair='No additional OpenAI calls requested; pending Astra04 must settle and coordinator controls funding.',benchmark_ready=False)
    atomic_json(OUT/'pilot-06.experiment-request.json',request)
    status('Pilot06 membership frozen; completing independent controls',f'Prepared600 fresh normalized tuples from300 families, with270 distinct aorist families and60 passives. All shared policy13 validations passed. {manifest["new_families_vs_named_five_d_01_to05"]} families are absent from named earlier5D panels. No paid calls.')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('command',choices=['census','feasibility','plan','generate']);args=a.parse_args();globals()[args.command]()
