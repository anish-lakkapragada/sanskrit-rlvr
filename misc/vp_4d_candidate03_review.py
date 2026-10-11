"""Independent input-only audit of frozen 5D candidate revision03; no paid calls."""
import collections, datetime, hashlib, json, time
from pathlib import Path
from misc.vp_campaign_candidates import load_entries, family
from misc.vp_cartesian_task import entry_scope_issue, oracle_issue, validate_task
from misc.vp_cartesian_prompt_v3 import render
from misc.vp_sanskrit_prompt_v1 import root_fields

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'benchmarks/parallel-search-20261006'
C=P/'five_d/candidate-4800/revision-03'
OUT=P/'four_d/candidate03-independent-review.json'
EXPECTED='2d15b6a62718d6ea0531686fc1eb4a1d91223f3d6baf705108f8088bc37dd031'
def read(p):
    assert Path(p).name!='results.json', 'No model answer files allowed'
    return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def cell(t):return '|'.join((t['derivation']['recipe_id'],t['morphology']['lakara'],t['morphology']['prayoga']))
def signature(t):
    h=t.get('dhatu') or {};m=t.get('morphology') or {};d=t.get('derivation') or {}
    if any(x.get('prefixes') for x in [t,h,m,d]):return None
    if any(x.get(k) not in [None,'',[]] for x in [t,h,m,d] for k in ['dhatu_pada','pada']):return None
    keys=['lakara','prayoga','purusha','vacana']
    if not h.get('aupadeshika') or not h.get('gana') or not all(m.get(k) for k in keys):return None
    return (h['aupadeshika'],h['gana'],tuple(d.get('sanadi') or []),*(m[k] for k in keys))
def walk(t):
    yield t
    for child in t.get('forms') or []:yield from walk(child)

started=now();tasks=read(C/'tasks.json');plan=read(C/'sampling-plan.json');manifest=read(C/'manifest.json')
assert sha(C/'tasks.json')==EXPECTED
entries={e.code:e for e in load_entries()}
assignments=read(ROOT/'benchmarks/creation-campaign-20261006/family-split.json')['families']
master=collections.defaultdict(set)
for f,row in assignments.items():master[row['split']].add(f)
file_checks={n:sha(C/n)==row['sha256'] and (C/n).stat().st_size==row['bytes'] for n,row in manifest['files'].items()}
source_checks={n:sha(row['path'])==row['sha256'] for n,row in plan['source_hashes'].items()}
assert all(file_checks.values()) and all(source_checks.values())
assert plan['source_hashes']==manifest['source_hashes']
assert sha(ROOT/'misc/vp_cartesian_task.py')=='86a9e2dce069a8fdb64c8c8e359120d499a60c4d4d5e1f926f0b51199f4474a5'
assert len(tasks)==4800
ids=set();sigs=set();texts=set();groups=collections.defaultdict(list);last=time.monotonic()
prompts=[json.loads(line) for line in (C/'prompts.jsonl').read_text().splitlines()]
assert len(prompts)==len(tasks)
excluded=set(plan['source_control_codes_excluded'])|set(plan['unresolved_prospective_exclusions'])
for i,t in enumerate(tasks):
    e=entries[t['dhatu']['code']];f=family(e)
    assert t['task_type']=='cartesian_5d' and t['prompt_version']=='cartesian-5d-v3-sanskrit'
    assert set(t['morphology'])=={'lakara','prayoga','purusha','vacana'}
    assert set(t['derivation'])=={'recipe_id','sanadi','prefixes','order'}
    assert not e.dhatu.prefixes and not e.dhatu.sanadi and not t['derivation']['prefixes']
    assert t['derivation']['order']=='innermost_to_outermost'
    assert t['derivation']['sanadi']==plan['recipe_operations'][t['derivation']['recipe_id']]
    assert not entry_scope_issue(e) and not oracle_issue(t) and e.code not in excluded
    assert f==t['campaign']['root_family'] and f in master['test'] and t['campaign']['split']=='test'
    assert f not in master['development'] and f not in master['rl_train']
    assert t['campaign']['plan_sha256']==sha(C/'sampling-plan.json') and t['campaign']['oracle_policy']=='oracle-policy-17'
    sig=signature(t);assert sig and sig not in sigs and t['id'] not in ids
    sigs.add(sig);ids.add(t['id']);groups[f].append(t)
    text=render(t);assert text not in texts and root_fields(t['dhatu']) in text;texts.add(text)
    assert all(text.count(label)==1 for label in ['लकारः —','प्रयोगः —','पुरुषः —','वचनम् —','सनादिप्रत्ययाः (क्रमेण) —'])
    assert 'सिद्धेषु रूपेष्वेकमेव' in text and '<answer></answer>' in text
    assert prompts[i]=={'id':t['id'],'prompt':text}
    assert hashlib.sha256(text.encode()).hexdigest()==t['campaign']['prompt_sha256']
    validate_task(t,e,'test')  # Full engine regeneration and accepted-union/transliteration checks.
    if time.monotonic()-last>35:
        msg=f'{now()}: Independent revision03 audit regenerated {i+1}/4800 tasks; contract, source policy and prompt checks pass so far.'
        print(msg,flush=True)
        with (P/'four_d/progress.md').open('a') as out:out.write('\n- '+msg+'\n')
        last=time.monotonic()

dist={
 'recipe_counts':dict(collections.Counter(t['derivation']['recipe_id'] for t in tasks)),
 'cell_counts':dict(collections.Counter(cell(t) for t in tasks)),
 'gana_counts':dict(collections.Counter(t['dhatu']['gana'] for t in tasks)),
 'lakara_counts':dict(collections.Counter(t['morphology']['lakara'] for t in tasks)),
 'prayoga_counts':dict(collections.Counter(t['morphology']['prayoga'] for t in tasks)),
 'person_counts':dict(collections.Counter(t['morphology']['purusha'] for t in tasks)),
 'number_counts':dict(collections.Counter(t['morphology']['vacana'] for t in tasks)),
 'person_number_counts':dict(collections.Counter(t['morphology']['purusha']+'/'+t['morphology']['vacana'] for t in tasks))}
assert all(v==plan[k] for k,v in dist.items())
loads=collections.Counter(len(ts) for ts in groups.values());lun=collections.Counter(sum(t['morphology']['lakara']=='Lun' for t in ts) for ts in groups.values())
for ts in groups.values():
    counts=collections.Counter(t['morphology']['lakara'] for t in ts)
    assert len(ts)<=8 and counts['Lun']<=5 and all(n<=1 for k,n in counts.items() if k!='Lun')
for row in read(C/'family-assignments.json'):
    ts=groups[row['family']];assert row['tasks']==len(ts) and row['cells']==dict(collections.Counter(cell(t) for t in ts))
    assert all(t['dhatu']['code']==row['code'] and t['dhatu']['gana']==row['gana'] for t in ts)
assert len(read(C/'family-assignments.json'))==len(groups)
byid={t['id']:t for t in tasks};alloc=read(C/'allocation.json');assert len(alloc)==len(tasks)
assert {r['id'] for r in alloc}==ids
for r in alloc:
    t=byid[r['id']]
    assert r=={'id':t['id'],'family':t['campaign']['root_family'],'code':t['dhatu']['code'],'gana':t['dhatu']['gana'],'cell':cell(t),'purusha':t['morphology']['purusha'],'vacana':t['morphology']['vacana']}
ssq=sum(k*k*v for k,v in loads.items());repeated=2160-(len(groups)-lun.get(0,0));obj=read(C/'allocation-objective.json')
assert obj['distinct_families']==len(groups) and obj['repeated_lakara_assignments']==repeated and obj['sum_squared_family_loads']==ssq
assert obj['cost']==obj['large_cost']*(4800-len(groups))+obj['medium_cost']*repeated+ssq-len(groups)
history=set();hf=set();files=[];ledger_hashes=[];count=0
for directory in ['creation-campaign-20261006','iterative-goal-20261006']:
    lp=ROOT/'benchmarks'/directory/'ledger.json';ledger=read(lp);ledger_hashes.append({'path':str(lp),'sha256':sha(lp)})
    for name in ledger['jobs']:
        path=lp.parent/'jobs'/name/'tasks.json';rows=read(path);files.append({'path':str(path),'sha256':sha(path),'n':len(rows)})
        for t in rows:
            for row in walk(t):
                count+=1
                sig=signature(row)
                if sig:history.add(sig)
                camp=row.get('campaign') or {}
                if camp.get('root_family'):hf.add(camp['root_family'])
                hf.update(camp.get('root_families') or [])
                h=row.get('dhatu') or {}
                if h.get('aupadeshika') and h.get('gana'):hf.add(h['aupadeshika']+'|'+h['gana'])
tuple_hits=[t['id'] for t in tasks if signature(t) in history];family_hits=sorted(set(groups)&hf)
assert not tuple_hits and not family_hits
old=read(C.parent/'revision-01/tasks.json');rnow=set().union(*(set(t['campaign']['trace_rule_ids']) for t in tasks));rold=set().union(*(set(t['campaign']['trace_rule_ids']) for t in old))
out={'created_at':now(),'started_at':started,'status':'mechanical_checks_complete_source_review_pending','candidate_path':str(C),'tasks_sha256':EXPECTED,'script_sha256':sha(__file__),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'policy':'oracle-policy-17','mechanical_passed':True,'regenerated_tasks':len(tasks),'unique_ids':len(ids),'unique_grammar_tuples':len(sigs),'unique_prompts':len(texts),'manifest_file_checks':file_checks,'plan_source_hash_checks':source_checks,'contract':'Dictionary citation/gana/meaning plus exactly four coordinates and one of three explicit ordered recipes; no explicit or inherited prefixes or independently selected pada.','distributions':dist,'family_statistics':{'selected_test_families':len(groups),'master_split_sizes':{k:len(v) for k,v in master.items()},'family_load_histogram':dict(loads),'aorist_load_histogram_including_zero':dict(lun),'sum_squared_loads':ssq,'family_pair_correlation_multiplier':ssq/4800-1,'repeated_aorist_assignments':repeated,'maximum_family_load':max(loads),'maximum_aorist_family_load':max(lun),'allocation_records_match':True,'objective_cost_identity_matches':True,'rl_and_development_overlap':0},'history_input_novelty':{'ledger_hashes':ledger_hashes,'task_input_files':files,'task_or_component_records':count,'normalized_unique_finite_tuples':len(history),'historical_family_ids':len(hf),'tuple_overlaps':tuple_hits,'family_overlaps':family_hits,'normalization':'Citation+gana, ordered operations, four coordinates; ignore task ID/prompt version; compare only no-prefix/no-specified-pada shapes. Also inspect nested form inputs and all root-family fields.','scope':'Only input files in both campaign ledgers; ledger metadata can change as unrelated jobs settle.'},'new_trace_rules_vs_revision01':sorted(rnow-rold),'source_review':None,'paid_calls':0,'model_answer_files_read':False,'shared_files_modified':False,'final_approval':False,'benchmark_ready':False,'limits':['Mechanical regeneration is not complete independent Sanskrit certification.','This input audit does not establish reference accuracy, completion or family-adjusted precision.','Exact dictionary citation/class defines the master split; etymological or broader lexical families may cross it.','Historical novelty means the recorded campaign inputs, not proof of absence from model pretraining.','No global allocation solver rerun; verify resulting constraints, records and cost identity only.']}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':True,'tasks':len(tasks),'families':len(groups),'historical_files':len(files),'historical_records':count,'new_trace_rules':sorted(rnow-rold)},indent=2))
