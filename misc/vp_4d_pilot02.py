#!/usr/bin/env python3
"""Freeze a fresh 108-question 4D mechanism pilot. No paid calls."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,HISTORY,CELLS,identity,row_identity,load_entries,name,now,sha,write,source_rows,render
from misc.vp_campaign_candidates import family
from misc.vp_cartesian_task import entry_scope_issue,oracle_issue,make_task,validate_task
from misc.vp_4d_pilot02_audit import FOCUSED_CODES,CURADI_CONTROL_CODES,UNVERIFIED_AKUSMIYA,contrast_families,status,RUN_ID
sys.path.insert(0,str(OUT/'_solver_deps'))
import highspy

SEED=2026100702
LA_QUOTAS={'Lat':4,'Lit':4,'Lut':4,'Lrt':4,'Lot':4,'Lan':4,'VidhiLin':3,'AshirLin':3,'Lun':3,'Lrn':3}
CROSS_GANA={'Bhvadi':9,'Tudadi':7,'Divadi':7,'Kryadi':5,'Svadi':3,'Rudhadi':2,'Juhotyadi':2,'Adadi':1}
COORDS=['lakara','prayoga','purusha','vacana']


def ordering(row,label):
    return hashlib.sha256(f'{SEED}:{label}:{row["id"]}'.encode()).hexdigest()


def exposure():
    paths=[ROOT/'benchmarks/full-tasks.json',*sorted(HISTORY.glob('discovery-??.json')),
           *sorted((ROOT/'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json')),
           OUT/'pilot-01.questions.json']
    used=set();records=[]
    for path in paths:
        panel=json.loads(path.read_text())
        for task in panel:
            for t in task.get('forms',[task]):
                if 'dhatu' not in t or set(t.get('morphology',{}))!=set(COORDS):continue
                d=t.get('derivation',{})
                if d.get('sanadi') or d.get('prefixes'):continue
                used.add(identity(t))
        records.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path)})
    return used,records


def metadata_issue(row,entries):
    if entry_scope_issue(entries[row['code']]):return True
    t={'dhatu':{'code':row['code']},'morphology':{k:row[k] for k in COORDS},
       'campaign':{'trace_rule_ids':row['rules']}}
    return bool(oracle_issue(t))


def select(rows,label,entries,*,lakara_quotas=None,gana_quotas=None,family_cap=1,morphology_quotas=None):
    rows=sorted(rows,key=lambda r:ordering(r,label))
    h=highspy.Highs();h.setOptionValue('output_flag',False);h.setOptionValue('threads',2)
    h.setOptionValue('random_seed',SEED);h.setOptionValue('time_limit',45.)
    x=[h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger) for _ in rows]
    maps={k:defaultdict(list) for k in ['family','lakara','gana','purusha','vacana','morphology']}
    for r,v in zip(rows,x):
        d={**r,'gana':name(entries[r['code']].dhatu.gana),'morphology':tuple(r[k] for k in COORDS)}
        for k in maps:maps[k][d[k]].append(v)
    h.addConstr(h.qsum(x)==36)
    for vs in maps['family'].values():h.addConstr(h.qsum(vs)<=family_cap)
    for k in ['purusha','vacana']:
        for vs in maps[k].values():h.addConstr(h.qsum(vs)==12)
    for key,quota in [('lakara',lakara_quotas),('gana',gana_quotas),('morphology',morphology_quotas)]:
        if quota is None:continue
        for group,vs in maps[key].items():h.addConstr(h.qsum(vs)==quota.get(group,0))
        assert set(quota)<=set(maps[key]),(label,key,set(quota)-set(maps[key]))
    # Seeded outcome-independent priority; all grammatical quotas are fixed first.
    h.minimize(h.qsum((i+1)*v for i,v in enumerate(x)))
    sol=h.getSolution()
    assert sol.value_valid,(label,str(h.getModelStatus()),len(rows))
    chosen=[r for r,v in zip(rows,x) if sol.col_value[int(v)]>.5]
    assert len(chosen)==36,(label,len(chosen),str(h.getModelStatus()))
    assert max(Counter(r['family'] for r in chosen).values())<=family_cap
    return chosen,{'solver_status':str(h.getModelStatus()),'candidate_rows':len(rows),'selected':len(chosen)}


def clean_stats():
    path=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-four-d-pilot-01/results.json'
    results=json.loads(path.read_text())
    bycode={e.code:e for e in load_entries()}
    variants={
        'raw':lambda t:False,
        'shared_oracle_policy_only':lambda t:bool(entry_scope_issue(bycode[t['dhatu']['code']]) or oracle_issue(t)),
        'shared_policy_and_unverified_akusmiya_readings':lambda t:bool(entry_scope_issue(bycode[t['dhatu']['code']]) or oracle_issue(t) or t['dhatu']['code'] in UNVERIFIED_AKUSMIYA),
    }
    panels={}
    for label,reject in variants.items():
        kept=[r for r in results if not reject(r['task'])]
        usable=[r for r in kept if r['status']=='completed' and not r['truncated'] and not r['refusals'] and r['answer'] is not None]
        cells=defaultdict(list)
        for r in usable:cells[r['task']['campaign']['sampling_cell']['label']].append(r)
        panels[label]={'n':len(kept),'usable':len(usable),'correct':sum(r['is_correct'] for r in usable),
            'refusals':sum(bool(r['refusals']) for r in kept),'truncations':sum(r['truncated'] for r in kept),
            'usable_accuracy':sum(r['is_correct'] for r in usable)/len(usable),
            'excluded_task_ids':[r['task_id'] for r in results if reject(r['task'])],
            'usable_cells':{c:{'n':len(rs),'correct':sum(r['is_correct'] for r in rs),
                              'families':len({r['task']['campaign']['root_family'] for r in rs})} for c,rs in cells.items()}}
    data={'created_at':now(),'raw_results_path':str(path.relative_to(ROOT)),'raw_results_sha256':sha(path),
        'raw_task_sha256':sha(OUT/'pilot-01.questions.json'),'panels':panels,
        'policy':'Read-only post-discovery diagnostics. Raw pilot01 tasks, gold, responses, and headline scores are unchanged. Filters apply to successes and failures by grammatical/lexical rule. These subsets are not new independent accuracy measurements.'}
    assert panels['raw']['correct']==108 and panels['raw']['n']==120 and panels['raw']['usable']==118
    write(OUT/'pilot-01.clean-context-stats-02.json',data)


def main():
    target=OUT/'pilot-02.questions.json'
    if target.exists():raise RuntimeError('Pilot02 is frozen; do not overwrite')
    lexical=json.loads((OUT/'pilot-02.lexical-audit.json').read_text())
    assert lexical['all_source_examples_passed']
    entries={e.code:e for e in load_entries()}; contrasts=contrast_families(list(entries.values()))
    prior,exposure_files=exposure()
    status('Selecting fresh grammatical tuples','Freezing 36 licensed Akusmiya cases, 36 broad class-contrast cases, and 36 coordinate-matched controls.')
    rows=source_rows(entries)
    safe=[];seen=set();supply=defaultdict(list)
    for r in rows:
        if r['prayoga']!='Kartari' or metadata_issue(r,entries):continue
        e=entries[r['code']];g=name(e.dhatu.gana)
        if r['code'] in UNVERIFIED_AKUSMIYA:continue
        key=row_identity(r,entries)
        if key in seen:continue
        seen.add(key)
        if family(e) in contrasts and g!='Curadi' and r['lakara'] in {'Lat','Lan','Lot','VidhiLin'}:
            supply[r['split']].append(r)
        if r['split']=='development' and key not in prior:safe.append(r)
    # No test output forms are used; this is a grammar-column capacity census.
    census={s:{'unique_tuples':len(rs),'families':len({r['family'] for r in rs}),
        'by_gana':dict(Counter(name(entries[r['code']].dhatu.gana) for r in rs)),
        'at_family_caps':{str(k):sum(min(k,v) for v in Counter(r['family'] for r in rs).values()) for k in [3,5,6,10]}}
        for s,rs in supply.items()}
    aku,aku_solver=select([r for r in safe if r['code'] in FOCUSED_CODES],'akusmiya',entries,
        lakara_quotas=LA_QUOTAS,family_cap=4)
    used_families={r['family'] for r in aku}
    cross,cross_solver=select([r for r in safe if r['family'] in contrasts and name(entries[r['code']].dhatu.gana)!='Curadi'
        and r['lakara'] in {'Lat','Lan','Lot','VidhiLin'} and r['family'] not in used_families],
        'cross_gana',entries,lakara_quotas={x:9 for x in ['Lat','Lan','Lot','VidhiLin']},gana_quotas=CROSS_GANA)
    used_families|={r['family'] for r in cross}
    control_rows=[r for r in safe if r['family'] not in used_families and
        (r['code'] in CURADI_CONTROL_CODES or (name(entries[r['code']].dhatu.gana)!='Curadi' and r['family'] not in contrasts))]
    controls,control_solver=select(control_rows,'matched_controls',entries,
        gana_quotas={'Curadi':18,**{g:2 for g in ['Bhvadi','Adadi','Juhotyadi','Divadi','Svadi','Tudadi','Rudhadi','Tanadi','Kryadi']}},
        morphology_quotas=Counter(tuple(r[k] for k in COORDS) for r in aku))
    tasks=[]
    for label,selected in [('akusmiya_licensed',aku),('cross_gana_lexical_contrast',cross),('coordinate_matched_controls',controls)]:
        for r in selected:
            e=entries[r['code']]
            t=make_task(e,'development',{k:r[k] for k in COORDS})
            assert t is not None and not oracle_issue(t)
            t['campaign'].update({'panel':'four-d-pilot-02','seed':SEED,
                'sampling_cell':{'label':label,'prayogas':['Kartari'],
                    'lakaras':list(LA_QUOTAS) if label!='cross_gana_lexical_contrast' else ['Lat','Lan','Lot','VidhiLin']},
                'selection':{'method':'fixed grammar predicates, quotas, and seeded integer selection; no model-answer filter',
                    'cross_gana_citation_group':e.dhatu.aupadeshika.replace('\\','').replace('^','') if r['family'] in contrasts else None,
                    'intrinsic_antargana':name(e.dhatu.antargana) if e.dhatu.antargana is not None else None}})
            validate_task(t,e,'development')
            assert identity(t) not in prior
            tasks.append(t)
    tasks.sort(key=lambda t:hashlib.sha256(f'{SEED}:order:{t["id"]}'.encode()).hexdigest())
    assert len(tasks)==len({t['id'] for t in tasks})==len({render(t) for t in tasks})==108
    families=Counter(t['campaign']['root_family'] for t in tasks)
    distribution={k:dict(Counter(t['morphology'][k] for t in tasks)) for k in COORDS}
    distribution['gana']=dict(Counter(t['dhatu']['gana'] for t in tasks))
    assert len(distribution['gana'])==10 and len(distribution['lakara'])==10
    assert set(distribution['purusha'].values())=={36} and set(distribution['vacana'].values())=={36}
    write(target,tasks)
    manifest={'created_at':now(),'run_id':RUN_ID,'seed':SEED,'questions_sha256':sha(target),
        'n':len(tasks),'unique_families':len(families),'max_tasks_per_family':max(families.values()),
        'family_size_histogram':dict(Counter(families.values())),'distribution':distribution,
        'sampling_cells':{'akusmiya_licensed':36,'cross_gana_lexical_contrast':36,'coordinate_matched_controls':36},
        'solvers':{'akusmiya':aku_solver,'cross_gana':cross_solver,'controls':control_solver},
        'full_master_test_and_development_cross_gana_capacity':census,
        'lexical_audit_sha256':sha(OUT/'pilot-02.lexical-audit.json'),
        'generator_sha256':sha(__file__),'adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
        'family_split_sha256':sha(HISTORY/'family-split.json'),
        'historical_exposure_files':exposure_files,
        'scope':'Exactly dictionary dhatu + lakara/prayoga/purusha/vacana; unchanged v2 renderer. All Kartari to isolate lexical/class mechanisms.',
        'interpretation':'Mechanism probe, not a proposed release mixture. Curadi comprises 50%; the final release diversity constraints are unchanged.',
        'no_test_model_answers_read':True,'final_membership_selected':False,'benchmark_ready':False}
    write(OUT/'pilot-02.manifest.json',manifest)
    audit={'created_at':now(),'questions_sha256':sha(target),'regenerated':108,'unique_prompts':108,
        'unique_visible_tuples':108,'prior_exposure_overlap':0,'hidden_entry_scope_violations':0,
        'shared_oracle_quarantine_violations':0,'source_examples_passed':31,
        'scope_and_regeneration_passed':True,'full_independent_gold_certification':False,
        'lexical_audit_path':'pilot-02.lexical-audit.json','limits':lexical['limitations']}
    write(OUT/'pilot-02.audit.json',audit)
    request={'created_at':now(),'track':'four_d','request_id':'four-d-pilot-02-opus',
        'questions_path':str(target),'questions_sha256':sha(target),'n':108,'unique_root_families':len(families),
        'task_type':'cartesian_4d','prompt_version':'cartesian-4d-v1','provider':'Anthropic','model':'claude-opus-5-5',
        'effort':'xhigh','max_output_tokens':16384,'phase':'explore','split':'development',
        'purpose':'Test licensed Akusmiya ending restrictions and scalable cross-gana lexical homography, with coordinate-matched controls; no same-item failure selection.',
        'suggested_sampling':'Evaluate all 108 frozen questions; retain cell, class, tense, and family diagnostics. Review disagreements before any release-weight change.',
        'estimate':{'maximum_reservation_usd':round(108*(1500*2/1e6+16384*10/1e6),6),
            'calculation':'Conservative 1500 input tokens/task at current shared rates; coordinator must recompute under cumulative budget lock.',
            'worker_paid_calls':0,'planning_envelope_is_not_new_budget':True},
        'needed_adapter_changes':[],
        'audit_paths':[str(OUT/x) for x in ['pilot-02.audit.json','pilot-02.lexical-audit.json','pilot-02.manifest.json','pilot-01.clean-context-stats-02.json']],
        'paired_astra_recommendation':{'submit_now':False,'condition':'Pair the same frozen panel after Opus if the broad lexical-contrast or licensed Akusmiya mechanism shows signal and keys pass disagreement review.',
            'model':'gpt-6-astra','effort':'xhigh','max_output_tokens':16384,'maximum_reservation_usd':round(108*(1500*5/1e6+16384*25/1e6),6)},
        'benchmark_ready':False}
    clean_stats()
    write(OUT/'experiment-request-02.json',request)
    print(json.dumps({k:manifest[k] for k in ['n','questions_sha256','unique_families','max_tasks_per_family','distribution','full_master_test_and_development_cross_gana_capacity']},indent=2))


if __name__=='__main__':main()
