"""Input-only independent v2 review; no provider or model-output reads."""
from pathlib import Path
import collections,copy,datetime,hashlib,json,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import load_entries
from misc.vp_cartesian_task import make_task,validate_task,entry_scope_issue,oracle_issue
from misc.vp_4d_pilot04 import local_issue
from misc.vp_cartesian_prompt_v1 import render
from finetune.prompts import slp1_to_devanagari
BASE=ROOT/'benchmarks/parallel-search-20261007/four_d-90';OUT=BASE/'candidate-1250-v2';OLD=BASE/'candidate-1250-source-filtered'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stable(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
coords=('lakara','prayoga','purusha','vacana')
def family(t):return t['dhatu']['aupadeshika']+'|'+t['dhatu']['gana']
def key(t):return (t['dhatu']['aupadeshika'],t['dhatu']['gana'],*(t['morphology'][k] for k in coords))
def rows(p):
 for outer in read(p):
  yield from outer.get('forms',[outer])
tasks=read(OUT/'tasks.json');prev=read(OLD/'tasks.json');manifest=read(OUT/'manifest.json');audit=read(OUT/'replacement-audit.json');policy=read(OUT/'source-policy.json');clar=read(BASE/'reading-clarification.json')
tm={t['id']:t for t in tasks};pm={t['id']:t for t in prev};oldids=set(pm);newids=set(tm);retained=oldids&newids;removed=oldids-newids;added=newids-oldids
assert len(tasks)==len(tm)==1250 and len(retained)==1246 and len(removed)==len(added)==4
assert all(tm[i]==pm[i] for i in retained)
assert removed==set(audit['removed_ids'])=={r['id'] for r in clar['affected_items']['10.0108']}
assert added==set(audit['added_ids'])
assert all(pm[i]['dhatu']['code']=='10.0108' for i in removed)
assert len({key(t) for t in tasks})==1250
public={x['id']:x['prompt'] for x in read(OUT/'public-prompts.json')};assert set(public)==newids and len(set(public.values()))==1250
entries={e.code:e for e in load_entries()};regen=[]
for t in tasks:
 assert t['task_type']=='cartesian_4d' and t['prompt_version']=='cartesian-4d-v1'
 assert set(t['morphology'])==set(coords) and t['morphology']['prayoga']=='Kartari'
 assert 'derivation' not in t and not any(k in t['dhatu'] for k in ('sanadi','prefixes','pada'))
 assert not entry_scope_issue(entries[t['dhatu']['code']]) and not oracle_issue(t) and not local_issue(t)
 assert t['campaign']['root_family']==family(t) and t['campaign']['split']=='test'
 assert render(t)==public[t['id']]
 stripped={k:v for k,v in t.items() if k not in ('campaign','gold_slp1','gold_devanagari')}
 assert render(stripped)==public[t['id']]
 if t['id'] in added:
  expected=make_task(entries[t['dhatu']['code']],'test',t['morphology']);validate_task(t,entries[t['dhatu']['code']],'test')
  z=copy.deepcopy(t)
  for k in ('panel','sampling_cell','selection'):z['campaign'].pop(k,None)
  assert z==expected
  assert t['morphology']['lakara']=='Lun' and t['campaign']['sampling_cell']['label']=='other_adanta_aorist'
  assert family(t) in {family(p) for p in prev if p['dhatu']['code']!='10.0108' and p['campaign']['sampling_cell']['label']=='other_adanta_aorist'}
  regen.append({'id':t['id'],'code':t['dhatu']['code'],'family':family(t),'morphology':t['morphology'],'gold_slp1':t['gold_slp1'],'gold_devanagari':t['gold_devanagari'],'prompt_sha256':hashlib.sha256(public[t['id']].encode()).hexdigest(),'exact_regeneration':True})
predicates=policy['previous_holds']['predicates']+[policy['additional_exclusion']]
for t in tasks:
 for p in predicates:
  held=t['dhatu']['code']==p['code'] and p['lakara'] in ('all',t['morphology']['lakara'])
  if 'sampling_cell' in p:held=held and t['campaign']['sampling_cell']['label']==p['sampling_cell']
  assert not held
assert sum(t['dhatu']['code']=='10.0481' for t in tasks)==47
assert policy['retained_lexical_reading']==clar['findings']['10.0481']['public_declaration']
assert policy['previous_holds']==read(BASE/'test-source-hold-predeclaration.json')
assert policy['clarification_sha256']==sha(BASE/'reading-clarification.json')
fc=collections.Counter(family(t) for t in tasks);dist={k:dict(collections.Counter(t['morphology'][k] for t in tasks)) for k in coords};dist['gana']=dict(collections.Counter(t['dhatu']['gana'] for t in tasks));comp=dict(collections.Counter(t['campaign']['sampling_cell']['label'] for t in tasks))
assert manifest['distribution']==dist and manifest['composition']==comp and manifest['families']==len(fc)==535 and manifest['max_questions_per_family']==max(fc.values())==47
assert manifest['n']==1250 and manifest['source_held_questions_replaced']==16 and manifest['source_classification_replacements']==4
for field,p in [('tasks_sha256',OUT/'tasks.json'),('public_prompts_sha256',OUT/'public-prompts.json'),('source_policy_sha256',OUT/'source-policy.json'),('previous_proposal_sha256',OLD/'tasks.json')]:assert manifest[field]==sha(p)
for rel,h in manifest['dependencies'].items():assert sha(ROOT/rel)==h,(rel,'dependency changed')
current_paths=sorted((ROOT/'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json'))+sorted((ROOT/'benchmarks/creation-campaign-20261006/jobs').glob('*/tasks.json'))+[ROOT/'benchmarks/full-tasks.json',*sorted((ROOT/'benchmarks/creation-campaign-20261006').glob('discovery-??.json'))]
assert {str(p.relative_to(ROOT)) for p in current_paths}=={r['path'] for r in audit['all_inputs']}
for record in audit['all_inputs']+manifest['inputs']:assert sha(ROOT/record['path'])==record['sha256']
history=set();registered_families=set();nrows=0
for path in current_paths:
 for t in rows(path):
  nrows+=1
  if 'dhatu' not in t:continue
  if '/jobs/' in str(path):
   if 'aupadeshika' in t['dhatu']:registered_families.add(family(t))
   for member in t['dhatu'].get('members',[]):registered_families.add(member['aupadeshika']+'|'+member['gana'])
   registered_families.update(t.get('campaign',{}).get('root_families',[]))
  if 'aupadeshika' not in t['dhatu']:continue
  d=t.get('derivation',{});m=t.get('morphology',{})
  if set(m)==set(coords) and not d.get('sanadi') and not d.get('prefixes') and not d.get('pada') and not t['dhatu'].get('pada'):
   history.add(key(t))
assert not ({key(t) for t in tasks}&history)
assert not (set(fc)&registered_families)
assign=read(ROOT/'benchmarks/creation-campaign-20261006/family-split.json')['families'];assert all(assign[f]['split']=='test' for f in fc)
rlpath=BASE/'rl-supply/strict-citation-option/training-inventory-metadata.json';rl=read(rlpath)
rlfam={r['family'] for r in rl};rlcit={r['aupadeshika'] for r in rl};rlkeys={(r['aupadeshika'],r['gana'],*(r[k] for k in coords)) for r in rl};rldevacit={slp1_to_devanagari(x) for x in rlcit};rlprompt={r['prompt_sha256'] for r in rl}
assert not (set(fc)&rlfam)
assert not ({t['dhatu']['aupadeshika'] for t in tasks}&rlcit)
assert not ({slp1_to_devanagari(t['dhatu']['aupadeshika']) for t in tasks}&rldevacit)
assert not ({key(t) for t in tasks}&rlkeys)
assert not ({hashlib.sha256(p.encode()).hexdigest() for p in public.values()}&rlprompt)
assert sha(OLD/'tasks.json')=='d271d2a7ba9ad7b8b3caaf3f945cf7251c06f47aabfca41ec5c8e499481cf97b'
manifest_only=set(r['path'] for r in manifest['inputs']);audit_set=set(r['path'] for r in audit['all_inputs'])
result={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mechanical_review_passed':True,'scope':'Independent input-only v1/v2 comparison, four replacement regenerations, all prompts/holds/metadata, registered-history and strict-RL separation. No model outputs read.','inputs':{str(p.relative_to(ROOT)):sha(p) for p in [OUT/'tasks.json',OUT/'public-prompts.json',OUT/'manifest.json',OUT/'source-policy.json',OUT/'replacement-audit.json',OLD/'tasks.json',OLD/'independent-input-review.json',BASE/'reading-clarification.json',rlpath,ROOT/'misc/vp_4d_candidate_lexical_revision.py',Path(__file__)]},'retained_full_objects_unchanged':1246,'removed_ids':sorted(removed),'added':regen,'all_1250_prompts_rerender_exactly':True,'gold_campaign_removal_does_not_change_any_prompt':True,'no_extra_coordinates_operations_prefixes_selected_pada':True,'all_source_holds_uniform':True,'Cada47_retained_with_exact_declared_reading':True,'counts':{'n':1250,'families':len(fc),'max_per_family':max(fc.values()),'composition':comp,'distribution':dist},'history':{'input_files':len(current_paths),'records':nrows,'ordinary_unique_tuples':len(history),'registered_families':len(registered_families),'candidate_tuple_overlap':0,'candidate_registered_family_overlap':0,'all_candidate_families_master_test':True,'all_input_file_hashes_match':True},'strict_rl':{'inventory_rows':len(rl),'families':len(rlfam),'candidate_family_overlap':0,'candidate_exact_raw_citation_overlap':0,'candidate_rendered_citation_overlap':0,'candidate_tuple_overlap':0,'candidate_prompt_hash_overlap':0},'manifest_provenance_note':{'manifest_input_paths':len(manifest_only),'replacement_audit_input_paths':len(audit_set),'recorded_only_in_replacement_audit':sorted(audit_set-manifest_only),'assessment':'The final manifest and replacement audit both cover all116 current input paths; the earlier provenance presentation difference was corrected before this final review.'},'source_certification_passed':False,'full1250_source_certification_claimed':False,'limitations':['The four keys regenerate exactly; this is not independent philological certification of all finite forms or all licensed spellings.','Full v1 source and family-dependence limitations carry forward.','Strict RL inventory is an unexecuted prospective training option; no training or model calls were performed.','Legacy discovery inspected all dictionary families before the master split; exact tuple/campaign separation does not establish never-inspected lexical families.'],'paid_calls':0,'model_outputs_read':False,'frozen_inputs_changed':False,'benchmark_ready':False}
(OUT/'independent-input-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('mechanical_review_passed','retained_full_objects_unchanged','counts','history','strict_rl','manifest_provenance_note')},ensure_ascii=False,indent=2));print('review_json_sha256',sha(OUT/'independent-input-review.json'))
