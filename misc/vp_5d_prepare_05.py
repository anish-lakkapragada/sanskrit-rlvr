"""Fresh 40%-aorist development confirmation. Input-only seeded membership."""
from __future__ import annotations
import json,random,time
from collections import Counter,defaultdict
from pathlib import Path
from misc.vp_5d_prepare_04 import ROOT,OUT,RECIPES,FAMILY_GANAS,PN,status,atomic_json,now,sha
from misc.vp_5d_prepare_03 import SOURCE_ROOTS,task_for
from misc.vp_5d_pilot import entries,SPLIT,VOWELS,signature
from misc.vp_5d_novelty_04 import normalized,walk
from misc.vp_5d_candidate_05 import quotas,estimate
from misc.vp_5d_release_feasibility import Dinic,apportion
from misc.vp_cartesian_task import make_task,validate_task
from misc.vp_goal_validate import validate
from vidyut.prakriya import Vyakarana
from misc import vp_campaign_candidates as old

SEED=202610070805
VERSION='cartesian-5d-v3-sanskrit'
UNRESOLVED={'04.0137':'stim lexical s/z variant unresolved','10.0023':'urja entry/source scope unresolved'}

def history():
    seen=set();families=set();files=[];ledgers=[];counts=Counter()
    for directory in ['creation-campaign-20261006','iterative-goal-20261006']:
        lp=ROOT/'benchmarks'/directory/'ledger.json';ledger=json.loads(lp.read_text());ledgers.append({'path':str(lp),'sha256':sha(lp)})
        for name in ledger['jobs']:
            p=lp.parent/'jobs'/name/'tasks.json';ts=json.loads(p.read_text());files.append({'path':str(p),'sha256':sha(p),'top_level_tasks':len(ts)})
            for t in ts:
                for row in walk(t):
                    counts['records']+=1;sig,issue=normalized(row)
                    if issue:counts[issue]+=1
                    else:seen.add(sig);counts['matching_shape_records']+=1
                    f=row.get('campaign',{}).get('root_family')
                    if f:families.add(f)
    return seen,families,{'ledgers':ledgers,'task_files':files,'counts':dict(counts),'unique_matching_tuples':len(seen)}

def plan():
    p=OUT/'pilot-05.plan.json'
    if p.exists():raise RuntimeError('Preserve frozen plan')
    d=quotas(192,48)
    d.update(frozen_at=now(),seed=SEED,split='development',oracle_policy='oracle-policy-11',prompt_version=VERSION,
      recipe_operations=RECIPES,family_count=240,tasks_per_family=2,family_gana_counts=FAMILY_GANAS,
      gana_counts={k:2*v for k,v in FAMILY_GANAS.items()},person_number_counts={'/'.join(x):54 if i in {0,4,8} else 53 for i,x in enumerate(PN)},
      unresolved_prospective_exclusions=UNRESOLVED,source_control_codes_excluded=sorted(SOURCE_ROOTS),
      sampling_algorithm='Seeded selection uses only dictionary inputs, grammatical eligibility and historical input exposure. Designate192 distinct families to receive one Lun each; apportion those families across the fixed class quotas subject to available supply. Choose48 additional families for two different non-Lun forms. Allocate exact recipe/tense/voice and person/number margins with flow. Prefer families absent from named prior5D panels within grammatical strata. Never use model error labels.',
      family_allocation_tradeoff='192/240 families must be Lun-eligible to keep two distinct lakaras per family at40% Lun. This changes family composition relative to pilot04 and adds uncertainty to reweighted predictions; fresh confirmation is required.',
      freshness='Exclude every normalized matching finite tuple in both historical campaign ledgers, including nested form records. No prefixes or separately selected pada; ignore task IDs and prompt versions when comparing tuples.',
      reason='Increase active causal-aorist coverage to40% while retaining60% across all nine other lakaras; reduce passive to10% and preserve three recipe proportions. Grammar sources distinguish causal Kartari can/reduplication from passive yak and atmanepada. Passive ease is an empirical hypothesis, not a grammatical theorem.',
      primary_estimand='Fixed480-question joint recipe/tense/voice distribution; report all-request accuracy and completion-conditioned accuracy in parallel.',
      comparator='Reweight within this v3 panel to pilot04 original joint cells. This is a development comparator, not independent validation of old accuracy.',
      uncertainty='Family cluster sandwich and10000 seeded family bootstrap replicates, preserving both questions per family. Report iid diagnostic, missing-response bounds, and sparse-cell uncertainty; no claim of sub1pp precision from480.',
      fixed_decision_rule='Keep this panel unchanged after evaluation. Advance this grammar mixture as a candidate for an independent larger final evaluation only if audited all-request and completed Opus point estimates are both within79–81%, the worst/best missing-response bounds stay within79–81%, and disagreement audit leaves no unresolved validity issue in the retained scope. Otherwise do not claim target attainment; any further development uses a separately frozen grammar-defined plan and fresh tuples. No accuracy-based trimming, replacement, stopping, or reweighting can make this panel qualify. Point-estimate passage is developmental and does not certify population accuracy or precision. Astra pairing is coordinator-controlled after the current pair settles and this mixture is promising.',
      benchmark_ready=False)
    atomic_json(p,d)
    status('Pilot05 grammar weights frozen','Frozen fresh480 design:192 aorists,48 passives, unchanged320/128/32 recipes, all ten lakaras/classes. Two distinct lakaras per family; stim and urja prospectively held for source uncertainty. No model answers used for membership.')

def generate():
    output=OUT/'pilot-05.tasks.json'
    if output.exists():raise RuntimeError('Preserve frozen membership')
    pp=OUT/'pilot-05.plan.json';p=json.loads(pp.read_text());rng=random.Random(p['seed']);used,historical_families,ha=history()
    es=entries();v=Vyakarana();bases={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in es.items()}
    seen_families={t['campaign']['root_family'] for panel in ['01','02','03','04'] for t in json.loads((OUT/f'pilot-{panel}.tasks.json').read_text())}
    candidates={};reject=Counter();last=time.monotonic()
    for i,(f,e) in enumerate(es.items(),1):
        if e.code in SOURCE_ROOTS or e.code in UNRESOLVED:continue
        cc=[]
        for c in p['cell_counts']:
            r,l,vo=c.split('|');t,issue=task_for(e,r,dict(lakara=l,prayoga=vo,purusha='Prathama',vacana='Eka'),bases)
            if issue:reject[issue]+=1
            elif any((e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(RECIPES[r]),l,vo,pu,va) not in used for pu,va in PN):cc.append(c)
        if len({c.split('|')[1] for c in cc})>=2:candidates[f]=cc
        if time.monotonic()-last>45:
            status('Checking fresh pilot05 grammatical supply',f'Assessed {i}/{len(es)} development families under policy11 and the prospective source holds. No answers read for selection.');last=time.monotonic()
    # Reserve exactly one aorist per192 selected families. Cap class apportionment
    # by actual eligible family supply before seeded recipe matching.
    lun_pool={g:[f for f in candidates if old.name(es[f].dhatu.gana)==g and any('|Lun|' in c for c in candidates[f])] for g in FAMILY_GANAS}
    lq=apportion(FAMILY_GANAS,192)
    while any(lq[g]>min(FAMILY_GANAS[g],len(lun_pool[g])) for g in lq):
        for g in lq:
            cap=min(FAMILY_GANAS[g],len(lun_pool[g]));lq[g]=min(lq[g],cap)
        need=192-sum(lq.values())
        choices=[g for g in lq if lq[g]<min(FAMILY_GANAS[g],len(lun_pool[g]))]
        if not choices:raise RuntimeError('Insufficient distinct aorist families')
        for g in sorted(choices,key=lambda g:(lq[g]/FAMILY_GANAS[g],g))[:need]:lq[g]+=1
    assigned=None;chosen=None;lun_families=None
    for attempt in range(200):
        net=Dinic();edges=[]
        for g,n in lq.items():
            net.edge('s',('g',g),n);pool=list(lun_pool[g]);rng.shuffle(pool);pool.sort(key=lambda f:f in seen_families)
            for f in pool:
                net.edge(('g',g),('f',f),1);cc=[c for c in candidates[f] if '|Lun|' in c];rng.shuffle(cc)
                for c in cc:edges.append((f,c,net.edge(('f',f),('c',c),1)))
        for c,n in p['cell_counts'].items():
            if '|Lun|' in c:net.edge(('c',c),'t',n)
        if net.flow('s','t')!=192:raise RuntimeError('Class/apportioned aorist recipe flow fails')
        aa=[(f,c) for f,c,e in edges if e[3]-e[1]];lf={f for f,c in aa};selected=list(lf)
        for g,n in FAMILY_GANAS.items():
            pool=[f for f in candidates if f not in lf and old.name(es[f].dhatu.gana)==g and
              len({c.split('|')[1] for c in candidates[f] if '|Lun|' not in c and (g=='Curadi' or c.split('|')[0]!='desiderative')})>=2]
            rng.shuffle(pool);pool.sort(key=lambda f:f in seen_families)
            if len(pool)<n-lq[g]:raise RuntimeError('Insufficient non-aorist family supply '+g)
            selected.extend(pool[:n-lq[g]])
        rng.shuffle(selected);net=Dinic();edges=[]
        for f in selected:
            net.edge('s',('f',f),1 if f in lf else 2)
            las=sorted({c.split('|')[1] for c in candidates[f] if '|Lun|' not in c});rng.shuffle(las)
            for la in las:net.edge(('f',f),('fl',f,la),1)
            cc=[c for c in candidates[f] if '|Lun|' not in c];rng.shuffle(cc)
            for c in cc:edges.append((f,c,net.edge(('fl',f,c.split('|')[1]),('c',c),1)))
        for c,n in p['cell_counts'].items():
            if '|Lun|' not in c:net.edge(('c',c),'t',n)
        if net.flow('s','t')==288:
            assigned=aa+[(f,c) for f,c,e in edges if e[3]-e[1]];chosen=selected;lun_families=lf;break
    if assigned is None:raise RuntimeError('Non-aorist paired family flow failed')
    rng.shuffle(assigned);net=Dinic();edges=[]
    for i,(f,c) in enumerate(assigned):
        net.edge('s',('slot',i),1);r,l,vo=c.split('|');options=list(PN);rng.shuffle(options)
        for pu,va in options:
            e=es[f];sig=(e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(RECIPES[r]),l,vo,pu,va)
            if sig not in used:edges.append((i,pu,va,net.edge(('slot',i),('pn',pu,va),1)))
    for pv,n in p['person_number_counts'].items():net.edge(('pn',*pv.split('/')),'t',n)
    if net.flow('s','t')!=480:raise RuntimeError('Fresh balanced PN flow failed')
    tasks=[]
    for i,pu,va,eedge in edges:
        if not eedge[3]-eedge[1]:continue
        f,c=assigned[i];r,l,vo=c.split('|');e=es[f];m=dict(lakara=l,prayoga=vo,purusha=pu,vacana=va)
        probe,issue=task_for(e,r,m,bases);assert not issue,issue
        t=make_task(e,'development',m,r,RECIPES[r],prompt_version=VERSION);assert t['gold_slp1']==probe['gold_slp1']
        t['campaign'].update(panel='five-d-pilot-05',slot=i,plan_sha256=sha(pp),oracle_policy='oracle-policy-11',lexical_bases=bases[f],selection_reason=p['sampling_algorithm'],sampling_cell={'recipe_id':r,'lakaras':[l],'prayogas':[vo]},audit_status='Shared policy11 and prospective source holds; recipe source controls reviewed, complete rare forms not independently exhaustively attested.')
        assert normalized(t)[0] not in used;validate_task(t,e,'development');tasks.append(t)
    rng.shuffle(tasks);assert len(tasks)==len({normalized(t)[0] for t in tasks})==480
    assert Counter(t['campaign']['root_family'] for t in tasks)==Counter({f:2 for f in chosen})
    assert Counter(t['dhatu']['gana'] for t in tasks)==Counter(p['gana_counts'])
    assert Counter(t['derivation']['recipe_id']+'|'+t['morphology']['lakara']+'|'+t['morphology']['prayoga'] for t in tasks)==Counter(p['cell_counts'])
    audit=validate(tasks,'development');atomic_json(output,tasks);atomic_json(OUT/'pilot-05.runner-audit.json',audit)
    for f in chosen:assert len({t['morphology']['lakara'] for t in tasks if t['campaign']['root_family']==f})==2
    ha.update(created_at=now(),task_sha256=sha(output),n=480,overlap_count=0,all_questions_fresh=True,normalization='Exact visible dhatu citation and class, ordered sanadi, all four coordinates; exclude prefixes and separately specified pada; recursively inspect historical bundled forms; ignore prompt versions and IDs.',families_absent_from_all_historical_inputs=len(set(chosen)-historical_families),families_previously_in_historical_inputs=len(set(chosen)&historical_families),model_results_read_for_selection=False)
    atomic_json(OUT/'pilot-05.novelty-audit.json',ha)
    manifest={'created_at':now(),'n':480,'family_count':240,'family_load_histogram':{'2':240},'distinct_lakaras_per_family':True,'aorist_family_count':192,'aorist_family_gana_counts':lq,'gana_counts':p['gana_counts'],'recipe_counts':p['recipe_counts'],'lakara_counts':p['lakara_counts'],'voice_counts':dict(Counter(t['morphology']['prayoga'] for t in tasks)),'person_number_counts':dict(Counter(t['morphology']['purusha']+'/'+t['morphology']['vacana'] for t in tasks)),'new_families_vs_named_five_d_01_to04':len(set(chosen)-seen_families),'reused_families_vs_named_five_d_01_to04':len(set(chosen)&seen_families),'task_sha256':sha(output),'plan_sha256':sha(pp),'script_sha256':sha(Path(__file__)),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'prompt_helper_sha256':sha(ROOT/'misc/vp_cartesian_prompt_v3.py'),'sanskrit_helper_sha256':sha(ROOT/'misc/vp_sanskrit_prompt_v1.py'),'family_split_sha256':sha(SPLIT),'dictionary_sha256':sha(old.TSV),'candidate_scope_rejections':dict(reject),'unresolved_prospective_exclusions':UNRESOLVED,'all_tasks_validated':True,'prompt_version':VERSION,'policy':'oracle-policy-11','status':'Frozen for coordinator validation; worker has not submitted.','benchmark_ready':False}
    atomic_json(OUT/'pilot-05.manifest.json',manifest)
    request={'created_at':now(),'track':'five_d','label':'opus-five-d-pilot-05','n':480,'phase':'fresh_development_confirmation','status':'ready_for_coordinator_review_not_submitted','task_file':str(output),'task_file_sha256':sha(output),'split':'development','provider':'Anthropic','reference_model':'Opus5.5','reasoning_effort':'xhigh','max_output_tokens':16384,'prompt_version':VERSION,'task_type':'cartesian_5d','plan':str(pp),'manifest':str(OUT/'pilot-05.manifest.json'),'audit':str(OUT/'pilot-05.runner-audit.json'),'worker_paid_calls':0,'astra_pair':'Hold until previous480 completes and coordinator judges this fresh Opus mixture promising.','benchmark_ready':False}
    atomic_json(OUT/'pilot-05.experiment-request.json',request)
    status('Pilot05 frozen for coordinator review',f'Prepared480 fresh normalized questions,240 families,192 distinct aorist families and48 passives; all policy11 and shared validations passed. {manifest["new_families_vs_named_five_d_01_to04"]} families are absent from named earlier5D panels. No paid calls.')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('command',choices=['plan','generate']);args=a.parse_args()
    {'plan':plan,'generate':generate}[args.command]()
