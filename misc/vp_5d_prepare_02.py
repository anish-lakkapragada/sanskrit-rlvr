"""Prepare clean development panels without paid calls or final membership."""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_5d_pilot import OUT,RECIPES,EXCLUDED_RULES,LAKARAS,SPLIT,atomic_json,now,sha,entries as development_entries,signature,prior_signatures,task_for
from misc.vp_goal_validate import validate
from misc.vp_cartesian_task import entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v1 import render
from vidyut.prakriya import Vyakarana

RUN='pilot-preparation-02'


def status(phase,message):
    atomic_json(OUT/'status.json',{'track':'five_d','run_id':RUN,'updated_at':now(),
        'state':'running','phase':phase,'message':message,'benchmark_ready':False})
    with (OUT/'progress.md').open('a') as f:f.write(f'- {now()}: {message}\n')


def ambiguities(entries):
    groups=defaultdict(list)
    for e in entries.values():groups[(e.dhatu.aupadeshika,old.name(e.dhatu.gana),e.artha)].append(e)
    return {e.code for es in groups.values() if len({str(e.dhatu.antargana) for e in es})>1 for e in es}


def exclusions(task,entry,ambiguous):
    why=[]
    for issue in [entry_scope_issue(entry),oracle_issue(task)]:
        if issue:why.append(issue)
    assert entry.code not in ambiguous or entry_scope_issue(entry)
    return why


def subset():
    original=OUT/'pilot-01.tasks.json';tasks=json.loads(original.read_text())
    entries={e.code:e for e in old.load_entries()};ambiguous=ambiguities(entries)
    rows=[];kept=[]
    for t in tasks:
        why=exclusions(t,entries[t['dhatu']['code']],ambiguous)
        rows.append({'id':t['id'],'dhatu_code':t['dhatu']['code'],'included':not why,'exclusion_reasons':why})
        if not why:kept.append(t)
    path=OUT/'pilot-01.audited-pair.tasks.json'
    if path.exists():assert json.loads(path.read_text())==kept
    else:atomic_json(path,kept)
    audit=validate(kept,'development')
    atomic_json(OUT/'pilot-01.audited-pair.runner-audit.json',audit)
    # Selection above never reads model answers. This post-selection summary is dev-only.
    results_path=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-01/results.json'
    results=json.loads(results_path.read_text());ids={t['id'] for t in kept}
    def score(rs):
        completed=sum(r['status']=='completed' for r in rs);correct=sum(bool(r['is_correct']) for r in rs)
        return {'requests':len(rs),'completed':completed,'correct':correct,
            'refused':sum(r['status']=='refused' for r in rs),
            'completed_accuracy':correct/completed,'all_request_accuracy':correct/len(rs)}
    manifest={'created_at':now(),'run_id':RUN,'panel':'pilot-01-audited-pair','n':len(kept),
        'root_families':len({t['campaign']['root_family'] for t in kept}),
        'source_tasks':str(original),'source_tasks_sha256':sha(original),
        'task_file':str(path),'task_file_sha256':sha(path),
        'script_sha256':sha(Path(__file__)),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
        'selection_policy':'Apply the adopted construction exclusions to every original task without consulting its correctness; retained task records are byte-for-byte-equivalent JSON objects.',
        'id_reason_map':rows,'removed':sum(not r['included'] for r in rows),
        'exclusion_reason_counts':dict(Counter(x for r in rows for x in r['exclusion_reasons'])),
        'ambiguous_dictionary_codes':sorted(ambiguous),'original_scores':score(results),
        'audited_subset_opus_scores':score([r for r in results if r['task']['id'] in ids]),
        'original_results_sha256':sha(results_path),'raw_originals_modified':False,
        'distribution':{'recipe':dict(Counter(t['derivation']['recipe_id'] for t in kept)),
            'lakara':dict(Counter(t['morphology']['lakara'] for t in kept)),
            'gana':dict(Counter(t['dhatu']['gana'] for t in kept))},
        'remaining_review':'Three nested inference-supported forms retain their original keys pending expanded source review; no known correction has been established. They are not removed merely because Opus missed them.',
        'benchmark_ready':False}
    atomic_json(OUT/'pilot-01.audited-pair.manifest.json',manifest)
    request={'created_at':now(),'track':'five_d','label':'astra-five-d-pilot-01-audited-pair',
        'phase':'paired_development_pilot','status':'ready_for_coordinator_review_not_submitted',
        'task_file':str(path),'relative_task_file':str(path.relative_to(ROOT)),
        'task_file_sha256':sha(path),'n':len(kept),'split':'development','provider':'OpenAI',
        'reference_model':'GPT-6 Astra','reasoning_effort':'xhigh','max_output_tokens':16384,
        'prompt_version':'cartesian-5d-v1','task_type':'cartesian_5d',
        'manifest':str(OUT/'pilot-01.audited-pair.manifest.json'),
        'audit':str(OUT/'pilot-01.audited-pair.runner-audit.json'),
        'rationale':'Pair the already measured Opus development pilot after applying all adopted grammar-scope exclusions, independent of original correctness. Keep refusal and grammar metrics separate.',
        'adapter_needs':'Existing Cartesian adapter; retained prompts and gold are unchanged.',
        'worker_paid_calls':0,'spending_authority':'Coordinator only under cumulative shared caps.'}
    atomic_json(OUT/'pilot-01.audited-pair.experiment-request.json',request)
    status('Audited paired subset ready',f'Prepared {len(kept)} unchanged tasks for paired Astra evaluation; removed {len(tasks)-len(kept)} by adopted grammar exclusions irrespective of correctness. Original results remain immutable.')
    print(json.dumps({'n':len(kept),'removed':[r for r in rows if not r['included']],
        'scores':manifest['audited_subset_opus_scores'],'request':str(OUT/'pilot-01.audited-pair.experiment-request.json')},indent=2))


def fresh_slots():
    slots=[]
    passive_lakaras={'Lat','Lut','Lrt','Lan','Lot','VidhiLin'}
    for recipe,cycles in [('intensive_luk',6),('causative_of_intensive',5)]:
        for cycle in range(cycles):
            for la in LAKARAS:
                passive=(recipe=='causative_of_intensive' and la in passive_lakaras
                    and (la not in {'Lat','Lut','Lot'} or cycle<4))
                slots.append({'recipe':recipe,'lakara':la,'prayoga':'Karmani' if passive else 'Kartari'})
    for la in ['Lat','Lut','Lot','VidhiLin','Lun']:
        slots.append({'recipe':'desiderative_of_causative_of_intensive','lakara':la,
            'prayoga':'Karmani' if la in {'Lat','Lut','Lot'} else 'Kartari'})
    for la in ['Lit','Lrt','Lan','AshirLin','Lrn']:
        slots.append({'recipe':'desiderative','lakara':la,'prayoga':'Kartari'})
    for i,s in enumerate(slots):
        s['morphology']={'lakara':s.pop('lakara'),'prayoga':s.pop('prayoga'),
            'purusha':['Prathama','Madhyama','Uttama'][i%3],
            'vacana':['Eka','Dvi','Bahu'][(i//3+i)%3]}
    return slots


def fresh():
    plan_path=OUT/'pilot-02.plan.json';plan=json.loads(plan_path.read_text())
    path=OUT/'pilot-02.tasks.json'
    if path.exists():raise RuntimeError('Fresh panel membership is already frozen')
    review=json.loads((OUT/'pilot-02.nested-source-review.json').read_text())
    assert len(review['reviews'])==3 and not review['new_quarantines']
    es=development_entries();v=Vyakarana()
    bases={f:sorted({p.text for p in v.derive(e.dhatu)}) for f,e in es.items()}
    previous=json.loads((OUT/'pilot-01.tasks.json').read_text())
    prior_families={t['campaign']['root_family'] for t in previous}
    used_before=prior_signatures()|{signature(t) for t in previous}
    for code,ops,voice,person in [
        ('01.1164',['yaNluk'],'Kartari','Prathama'),
        ('02.0059',['yaN','Ric'],'Kartari','Uttama'),
        ('02.0059',['yaN','Ric','san'],'Kartari','Uttama')]:
        e=next(e for e in old.load_entries() if e.code==code)
        used_before.add((e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(ops),'Lat',voice,person,'Eka'))
    for row in review['reviews']:
        e=next(e for e in old.load_entries() if e.code==row['dhatu_code'])
        for c in row['component_controls']:
            used_before.add((e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(c['sanadi']),c['lakara'],c['prayoga'],c['purusha'],c['vacana']))
    slots=fresh_slots();rng=random.Random(plan['seed']);reject=Counter();tasks=None
    assert Counter(s['recipe'] for s in slots)==plan['recipe_counts']
    for coordinate,expected in [('lakara','lakara_quotas'),('prayoga','voice_quotas'),('purusha','purusha_counts'),('vacana','vacana_counts')]:
        assert Counter(s['morphology'][coordinate] for s in slots)==plan[expected]
    for attempt in range(100):
        free=list(range(120));assigned={}
        for gana in ['Curadi','Tanadi','Juhotyadi','Svadi','Rudhadi','Adadi','Kryadi','Divadi','Tudadi','Bhvadi']:
            candidates=[i for i in free if gana!='Curadi' or slots[i]['recipe']=='desiderative']
            if gana in {'Tanadi','Juhotyadi'}:
                candidates=[i for i in candidates if slots[i]['recipe']=='intensive_luk']
            for i in rng.sample(candidates,plan['gana_quotas'][gana]):
                assigned[i]=gana;free.remove(i)
        chosen=[];families=set();rank={i:rng.random() for i in range(120)}
        order=sorted(range(120),key=lambda i:(sum(old.name(e.dhatu.gana)==assigned[i] for e in es.values()),rank[i]))
        for i in order:
            slot=slots[i]
            candidates=[e for f,e in es.items() if f not in families and old.name(e.dhatu.gana)==assigned[i]]
            rng.shuffle(candidates)
            candidates.sort(key=lambda e:old.family(e) in prior_families)
            for e in candidates:
                issue=entry_scope_issue(e)
                if issue:reject[issue]+=1;continue
                task,issue=task_for(e,slot['recipe'],slot['morphology'],bases)
                if task is None:reject[issue]+=1;continue
                issue=oracle_issue(task)
                if issue:reject[issue]+=1;continue
                if signature(task) in used_before:reject['previous_development_tuple_or_source_control']+=1;continue
                task['campaign'].update(panel='five-d-pilot-02',slot=i,
                    sampling_cell={'recipe_id':slot['recipe'],'lakaras':[slot['morphology']['lakara']],
                        'prayogas':[slot['morphology']['prayoga']],
                        'exclude_rules':sorted(EXCLUDED_RULES) if len(RECIPES[slot['recipe']]['sanadi'])>1 else [],
                        'exclude_ganas':['Curadi'] if RECIPES[slot['recipe']]['sanadi'][0] in {'yaN','yaNluk'} else []},
                    selection_reason='Frozen pilot-02 quotas and seed; grammar and tuple novelty only; prefer families absent from pilot01.',
                    lexical_bases=bases[old.family(e)],plan_sha256=sha(plan_path),
                    oracle_policy='Shared entry_scope_issue and oracle_issue; adopted coordinator policy 02')
                chosen.append(task);families.add(old.family(e));break
            else:break
        if len(chosen)==120:tasks=chosen;break
    if tasks is None:raise RuntimeError('Declared pilot-02 quotas have insufficient grammatical supply')
    rng.shuffle(tasks);atomic_json(path,tasks)
    audit=validate(tasks,'development')
    atomic_json(OUT/'pilot-02.runner-audit.json',audit)
    distribution={k:dict(Counter(t['morphology'][k] for t in tasks)) for k in ['lakara','prayoga','purusha','vacana']}
    distribution.update(recipe=dict(Counter(t['derivation']['recipe_id'] for t in tasks)),
        gana=dict(Counter(t['dhatu']['gana'] for t in tasks)),
        person_number=dict(Counter(t['morphology']['purusha']+'/'+t['morphology']['vacana'] for t in tasks)),
        gold_variants=dict(Counter(len(t['gold_slp1']) for t in tasks)))
    assert distribution['gana']==plan['gana_quotas']
    assert all(signature(t) not in used_before for t in tasks)
    assert len(families)==120 and len({t['campaign']['prompt_sha256'] for t in tasks})==120
    assert max(distribution['person_number'].values())-min(distribution['person_number'].values())<=1
    for t in tasks:
        assert not entry_scope_issue(es[t['campaign']['root_family']]) and not oracle_issue(t)
        assert t['derivation']['prefixes']==[] and set(t['morphology'])=={'lakara','prayoga','purusha','vacana'}
        assert 'Sanskrit verbal root (dhatu,' in render(t)
    manifest={'created_at':now(),'run_id':RUN,'panel':'pilot-02','n':120,'root_families':120,
        'families_absent_from_pilot01':len(families-prior_families),'families_reused_from_pilot01':len(families&prior_families),
        'fresh_tuple_count':120,'seed':plan['seed'],'plan_sha256':sha(plan_path),'task_file':str(path),
        'task_file_sha256':sha(path),'generator_sha256':sha(Path(__file__)),
        'lexical_helper_sha256':sha(ROOT/'misc/vp_5d_pilot.py'),
        'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
        'renderer_sha256':sha(ROOT/'misc/vp_cartesian_prompt_v1.py'),
        'dictionary_sha256':sha(old.TSV),'family_split_sha256':sha(SPLIT),
        'distribution':distribution,'class_assignment_attempts':attempt+1,'sampling_rejections':dict(reject),
        'prior_tuple_signatures':len(used_before),'benchmark_ready':False,
        'scope':'Development calibration only; fixed before any pilot02 model answers. All shared scope and oracle quarantines enforced.',
        'source_review':'pilot-02.nested-source-review.json'}
    atomic_json(OUT/'pilot-02.manifest.json',manifest)
    atomic_json(OUT/'pilot-02.prompts.json',[{'id':t['id'],'prompt':render(t)} for t in tasks])
    request={'created_at':now(),'track':'five_d','label':'opus-five-d-pilot-02',
        'phase':'fresh_development_pilot','status':'ready_for_coordinator_review_not_submitted',
        'task_file':str(path),'relative_task_file':str(path.relative_to(ROOT)),
        'task_file_sha256':sha(path),'n':120,'split':'development','provider':'Anthropic',
        'reference_model':'Opus 5.5','reasoning_effort':'xhigh','max_output_tokens':16384,
        'prompt_version':'cartesian-5d-v1','task_type':'cartesian_5d',
        'recipe_menu':plan['recipe_operations'],'recipe_counts':plan['recipe_counts'],
        'manifest':str(OUT/'pilot-02.manifest.json'),'plan':str(plan_path),
        'audit':str(OUT/'pilot-02.runner-audit.json'),
        'source_review':str(OUT/'pilot-02.nested-source-review.json'),
        'rationale':plan['reason'],'development_uncertainty':plan['development_heuristic'],
        'pairing_recommendation':{'provider':'OpenAI','reference_model':'GPT-6 Astra','same_tasks':True,
            'condition':'After Opus results and any necessary disagreement review; coordinator may pair concurrently if clean-scope review suffices under the shared budget.'},
        'adapter_needs':'Existing cartesian_5d adapter and frozen v1 renderer; no extra coordinates.',
        'worker_paid_calls':0,'spending_authority':'Coordinator only under cumulative shared caps.'}
    atomic_json(OUT/'pilot-02.experiment-request.json',request)
    status('Fresh pilot generated and validated',f'All 120 fresh tasks passed the shared full validator and adopted exclusions; {len(families-prior_families)} families are new relative to pilot01. Completing source-control and manifest checks.')
    print(json.dumps({'n':120,'new_families':len(families-prior_families),'distribution':distribution,
        'request':str(OUT/'pilot-02.experiment-request.json')},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['subset','fresh']);a=p.parse_args()
    subset() if a.command=='subset' else fresh()
