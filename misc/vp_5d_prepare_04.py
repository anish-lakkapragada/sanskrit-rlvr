"""Fresh 480-question development confirmation; no provider calls or ledger writes."""
from __future__ import annotations
import argparse
import json
import random
from collections import Counter
from pathlib import Path
from misc.vp_5d_prepare_03 import RECIPES, SOURCE_ROOTS, PASSIVE, task_for
from misc.vp_5d_pilot import OUT, SPLIT, VOWELS, entries, prior_signatures, signature, atomic_json, now, sha
from misc.vp_5d_release_feasibility import Dinic
from misc.vp_cartesian_task import make_task, validate_task
from misc.vp_goal_validate import validate
from misc import vp_campaign_candidates as old
from vidyut.prakriya import Vyakarana

ROOT=Path(__file__).resolve().parents[1]
FAMILY_GANAS={'Bhvadi':150,'Adadi':10,'Juhotyadi':2,'Divadi':24,'Svadi':4,
 'Tudadi':24,'Rudhadi':5,'Tanadi':2,'Kryadi':11,'Curadi':8}
JOINT={'Lun':(96,38,10),'Lat':(40,16,4),'VidhiLin':(40,16,4),'Lit':(21,8,2),
 'Lut':(21,8,2),'Lrt':(21,8,2),'Lot':(21,8,2),'Lan':(20,9,2),
 'AshirLin':(20,9,2),'Lrn':(20,8,2)}
PN=[(p,v) for p in ['Prathama','Madhyama','Uttama'] for v in ['Eka','Dvi','Bahu']]
SEED=202610070704

def status(phase,message):
    p=OUT/'status.json';s=json.loads(p.read_text());s.update(updated_at=now(),state='running',
      phase=phase,message=message,benchmark_ready=False);atomic_json(p,s)
    with (OUT/'progress.md').open('a') as f:f.write('\n- '+s['updated_at']+': '+message+'\n')

def plan():
    path=OUT/'pilot-04.plan.json'
    if path.exists():raise RuntimeError('Preserve frozen grammar plan')
    cells={}
    for la,counts in JOINT.items():
        for recipe,n in zip(RECIPES,counts):
            passive=n//2 if recipe!='desiderative' and la in PASSIVE else 0
            cells[recipe+'|'+la+'|Kartari']=n-passive
            if passive:cells[recipe+'|'+la+'|Karmani']=passive
    pn={'/'.join(x):54 if i in {0,4,8} else 53 for i,x in enumerate(PN)}
    data={'frozen_at':now(),'seed':SEED,'n':480,'family_count':240,'tasks_per_family':2,
      'recipe_operations':RECIPES,'recipe_counts':dict(zip(RECIPES,[320,128,32])),
      'lakara_counts':{la:sum(q) for la,q in JOINT.items()},'family_gana_counts':FAMILY_GANAS,
      'gana_counts':{k:2*v for k,v in FAMILY_GANAS.items()},'cell_counts':cells,'person_number_counts':pn,
      'split':'development','oracle_policy':'oracle-policy-08','prompt_version':'pending paired wording diagnostic',
      'family_policy':'Two different lakaras per family; exclude all previous exact development tuples and source-control roots; prioritize unexposed families with seeded order, never model errors.',
      'reason':'Preserve the three audited recipe proportions. Increase aorist to30% and present/optative to12.5% each, testing inherited reduplication and intensive stem preservation across distinct grammatical settings. Remaining45% spans all seven other lakaras.',
      'class_reason':'Classes follow eligible supply, retaining all ten. Scarce Juhotyadi and Tanadi each contribute two families; no invalid Vedic inputs are used to force balance.',
      'primary_estimand':'Accuracy under these fixed cells, reported on all requests and conditional on completion in parallel.',
      'comparator_estimand':'Original pilot03 recipe/tense/voice mix standardized using pilot04 per-cell outcomes; report both all-request and completion-conditioned estimates. This is a within-panel reweighting comparator, not independent replication of pilot03.',
      'uncertainty_plan':'Family-cluster bootstrap resamples the240 families and preserves each two-task cluster; report raw iid SE only as a diagnostic. Report family pair agreement/correlation cautiously because paired questions deliberately use different lakaras. For standardized estimates, preserve target cell weights and flag bootstrap draws with empty completed cells.',
      'precision_limit':'480 observations have about1.86pp iid SE at79%, before family dependence. This development panel cannot establish sub1pp release precision or tightly certify79–81%.',
      'selection_history':'Recipe/tense weights are development-adaptive, frozen before any pilot04 answers. Earlier individual failures never determine question membership.',
      'source_reviews':['pilot-03.source-audit.json','pilot-03.recipe-extension-review.json','pilot-03.oracle-addendum.json','pilot-03.semantic-san-audit.json'],
      'source_control_codes_excluded':sorted(SOURCE_ROOTS),'benchmark_ready':False}
    assert sum(cells.values())==480 and sum(FAMILY_GANAS.values())==240
    atomic_json(path,data);status('Pilot04 grammar weights frozen','Frozen480-question confirmation grammar:320 intensive→causative,128 intensive-luk→causative,32 desiderative;144 aorists,60 present,60 optative;240 families with two different tenses each. Prompt wording remains pending.')

def generate():
    output=OUT/'pilot-04.provisional.tasks.json'
    if output.exists():raise RuntimeError('Preserve provisional membership')
    planpath=OUT/'pilot-04.plan.json';p=json.loads(planpath.read_text());rng=random.Random(p['seed'])
    es=entries();v=Vyakarana();bases={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in es.items()}
    prior=[t for panel in ['01','02','03'] for t in json.loads((OUT/f'pilot-{panel}.tasks.json').read_text())]
    seen_families={t['campaign']['root_family'] for t in prior};used=prior_signatures()|{signature(t) for t in prior}
    candidates={};reject=Counter()
    for family,e in es.items():
        if e.code in SOURCE_ROOTS:continue
        choices=[]
        for cell in p['cell_counts']:
            recipe,la,voice=cell.split('|');t,issue=task_for(e,recipe,dict(lakara=la,prayoga=voice,purusha='Prathama',vacana='Eka'),bases)
            if issue:reject[issue]+=1
            else:choices.append(cell)
        if len({c.split('|')[1] for c in choices})>=2:candidates[family]=choices
    status('Assigning fresh confirmation families',f'Current policy08 yields {len(candidates)} eligible development families across the frozen cells; assigning240 families with two distinct tenses and no previously evaluated tuple.')
    assigned=None
    for attempt in range(100):
        chosen=[]
        for gana,count in FAMILY_GANAS.items():
            # The 448 causal slots require intensive-eligible families. Curadi supplies
            # eight desiderative-only families; avoid filling other classes with
            # fresh polysyllabic families that cannot occupy the frozen causal cells.
            pool=[f for f in candidates if old.name(es[f].dhatu.gana)==gana and
                (gana=='Curadi' or len({c.split('|')[1] for c in candidates[f]
                    if c.split('|')[0]!='desiderative'})>=2)]
            rng.shuffle(pool);pool.sort(key=lambda f:f in seen_families)
            if len(pool)<count:raise RuntimeError('Insufficient family quota for '+gana)
            chosen.extend(pool[:count])
        rng.shuffle(chosen);net=Dinic();edges=[]
        for f in chosen:
            net.edge('s',('f',f),2)
            las=sorted({c.split('|')[1] for c in candidates[f]});rng.shuffle(las)
            for la in las:net.edge(('f',f),('fl',f,la),1)
            cc=list(candidates[f]);rng.shuffle(cc)
            for c in cc:edges.append((f,c,net.edge(('fl',f,c.split('|')[1]),('c',c),1)))
        for c,n in p['cell_counts'].items():net.edge(('c',c),'t',n)
        if net.flow('s','t')==480:
            assigned=[(f,c) for f,c,e in edges if e[3]-e[1]];break
    if assigned is None:raise RuntimeError('Family-cell quota flow failed')
    # A second flow balances person/number globally and forbids all old exact tuples.
    rng.shuffle(assigned);net=Dinic();edges=[]
    for i,(f,c) in enumerate(assigned):
        net.edge('s',('s',i),1);recipe,la,voice=c.split('|');options=list(PN);rng.shuffle(options)
        for pu,va in options:
            e=es[f];sig=(e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(RECIPES[recipe]),la,voice,pu,va)
            if sig not in used:edges.append((i,pu,va,net.edge(('s',i),('pn',pu,va),1)))
    for (pu,va),n in [(tuple(k.split('/')),v) for k,v in p['person_number_counts'].items()]:net.edge(('pn',pu,va),'t',n)
    if net.flow('s','t')!=480:raise RuntimeError('Fresh person-number assignment failed')
    tasks=[]
    for i,pu,va,edge in edges:
        if not edge[3]-edge[1]:continue
        family,cell=assigned[i];recipe,la,voice=cell.split('|');e=es[family]
        t,issue=task_for(e,recipe,dict(lakara=la,prayoga=voice,purusha=pu,vacana=va),bases)
        if issue:raise RuntimeError('Assigned actual PN fails policy: '+issue)
        t['campaign'].update(panel='five-d-pilot-04',slot=i,plan_sha256=sha(planpath),oracle_policy='oracle-policy-08',
          lexical_bases=bases[family],selection_reason=p['family_policy'],sampling_cell={'recipe_id':recipe,'lakaras':[la],'prayogas':[voice]},
          audit_status='Shared policy08 regeneration and primary component-source review; complete rare forms are not independently exhaustively attested.')
        assert signature(t) not in used
        validate_task(t,e,'development');tasks.append(t)
    assert len(tasks)==len({signature(t) for t in tasks})==480
    assert Counter(t['campaign']['root_family'] for t in tasks)==Counter({f:2 for f in chosen})
    assert Counter(t['dhatu']['gana'] for t in tasks)==Counter(p['gana_counts'])
    assert Counter(t['derivation']['recipe_id']+'|'+t['morphology']['lakara']+'|'+t['morphology']['prayoga'] for t in tasks)==Counter(p['cell_counts'])
    rng.shuffle(tasks);audit=validate(tasks,'development')
    atomic_json(output,tasks);atomic_json(OUT/'pilot-04.provisional.runner-audit.json',audit)
    manifest={'created_at':now(),'n':480,'families':240,'family_load_histogram':{'2':240},
      'new_families_vs_prior_five_d_panels':sum(f not in seen_families for f in chosen),
      'reused_families_vs_prior_five_d_panels':sum(f in seen_families for f in chosen),
      'all480_exact_questions_fresh':True,'every_family_has_two_distinct_lakaras':True,
      'task_file_sha256':sha(output),'plan_sha256':sha(planpath),'generator_sha256':sha(Path(__file__)),
      'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'family_split_sha256':sha(SPLIT),
      'dictionary_sha256':sha(old.TSV),'candidate_scope_rejections':dict(reject),
      'distributions':{k:dict(Counter(t['morphology'][k] for t in tasks)) for k in ['lakara','prayoga','purusha','vacana']},
      'recipe_counts':dict(Counter(t['derivation']['recipe_id'] for t in tasks)),
      'gana_counts':dict(Counter(t['dhatu']['gana'] for t in tasks)),
      'lexical_vowels':dict(Counter(''.join(c for c in t['campaign']['lexical_bases'][0] if c in VOWELS) for t in tasks)),
      'gold_variants':dict(Counter(len(t['gold_slp1']) for t in tasks)),
      'status':'Membership fixed; prompt version pending coordinator wording diagnostic. No paid calls.',
      'heldout_answers_read':False,'benchmark_ready':False}
    atomic_json(OUT/'pilot-04.provisional.manifest.json',manifest)
    status('Fresh confirmation membership constructed',f'Prepared480 new questions from240 families: {manifest["new_families_vs_prior_five_d_panels"]} families absent from earlier5D panels and {manifest["reused_families_vs_prior_five_d_panels"]} reused on new inputs. Shared validation passed. Waiting only for final prompt-version decision before request handoff.')
    print(json.dumps(manifest,indent=2))

def freeze(version):
    out=OUT/'pilot-04.tasks.json'
    if out.exists():raise RuntimeError('Preserve final frozen panel')
    tasks=json.loads((OUT/'pilot-04.provisional.tasks.json').read_text());es=entries()
    for t in tasks:
        e=es[t['campaign']['root_family']]
        rebuilt=make_task(e,'development',t['morphology'],t['derivation']['recipe_id'],t['derivation']['sanadi'],prompt_version=version)
        assert rebuilt['id']==t['id'] and rebuilt['gold_slp1']==t['gold_slp1']
        t['prompt_version']=version;t['campaign']['prompt_sha256']=rebuilt['campaign']['prompt_sha256'];validate_task(t,e,'development')
    audit=validate(tasks,'development');atomic_json(out,tasks);atomic_json(OUT/'pilot-04.runner-audit.json',audit)
    manifest=json.loads((OUT/'pilot-04.provisional.manifest.json').read_text());manifest.update(frozen_at=now(),prompt_version=version,
      task_file_sha256=sha(out),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),status='Frozen and ready for coordinator validation; not submitted.')
    atomic_json(OUT/'pilot-04.manifest.json',manifest)
    request={'created_at':now(),'track':'five_d','label':'opus-five-d-pilot-04','n':480,'phase':'fresh_development_confirmation',
      'status':'ready_for_coordinator_review_not_submitted','task_file':str(out),'task_file_sha256':sha(out),'split':'development',
      'provider':'Anthropic','reference_model':'Opus5.5','reasoning_effort':'xhigh','max_output_tokens':16384,
      'prompt_version':version,'task_type':'cartesian_5d','plan':str(OUT/'pilot-04.plan.json'),
      'manifest':str(OUT/'pilot-04.manifest.json'),'audit':str(OUT/'pilot-04.runner-audit.json'),
      'worker_paid_calls':0,'spending_authority':'Coordinator only under shared cumulative caps.','benchmark_ready':False}
    atomic_json(OUT/'pilot-04.experiment-request.json',request);print(json.dumps(request,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['plan','generate','freeze']);p.add_argument('--prompt-version',choices=['cartesian-5d-v1','cartesian-5d-v2-verb']);a=p.parse_args()
    if a.command=='plan':plan()
    elif a.command=='generate':generate()
    else:
        if not a.prompt_version:p.error('freeze requires coordinator-selected --prompt-version')
        freeze(a.prompt_version)
