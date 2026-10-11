"""Policy21 exact two-tuple repair preserving a proved optimal allocation."""
from copy import deepcopy
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json
from misc.vp_5d_prepare_04 import ROOT,OUT,now,sha,atomic_json,status
from misc.vp_5d_candidate_4800_p18 import digest,cell
from misc.vp_5d_history_18 import history
from misc.vp_5d_novelty_04 import normalized
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue,make_task
from misc.vp_cartesian_prompt_v3 import render
from misc.vp_goal_validate import validate
from vidyut.prakriya import Vyakarana
A=OUT/'pilot-08/revision-01';P=OUT/'pilot-08/revision-02';EXPECTED='f5bfab6f3fc27b7c83bbd6987bede73501592a9568fda32a0371bd8e23b7febd'
def read(p):return json.loads(p.read_text())
def main():
 assert not P.exists();assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 ts=read(A/'tasks.json');sub=read(A/'astra-subset/tasks.json');plan=read(A/'plan.json');es=entries_by_code();used,hf,history_audit=history();loads=Counter(t['campaign']['root_family'] for t in ts)
 bad=[t for t in ts if entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)];assert len(bad)==1 and bad[0]['id']=='cart5-95a72032f74081e76f462424';bad=bad[0];assert bad in sub and loads[bad['campaign']['root_family']]==1
 candidates=sorted([t for t in sub if t['dhatu']['gana']=='Curadi' and t['derivation']['sanadi']==['san'] and t['morphology']['lakara']!='Lun' and loads[t['campaign']['root_family']]==1],key=lambda t:hashlib.sha256((plan['seed']+':minimal-source-repair:'+t['id']).encode()).hexdigest());checks=[];found=None
 for partner in candidates:
  first=make_task(es[bad['dhatu']['code']],'development',partner['morphology'],'desiderative',['san'],prompt_version=plan['prompt_version']);second=make_task(es[partner['dhatu']['code']],'development',bad['morphology'],'desiderative',['san'],prompt_version=plan['prompt_version']);issues=[]
  for t in [first,second]:
   if not t:issues.append('No form');continue
   issue=entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)
   if issue:issues.append(issue)
   if normalized(t)[0] in used:issues.append('Historical exact tuple')
  checks.append(dict(partner_id=partner['id'],code=partner['dhatu']['code'],issues=issues))
  if not issues:found=(partner,first,second);break
 assert found;partner,first,second=found;assert partner['id']=='cart5-3407cf02c7272a95e35aa5d2'
 P.mkdir();np=deepcopy(plan);np.update(created_at=now(),panel='five-d-pilot-08-r2',oracle_policy='oracle-policy-21',minimal_repair=dict(predecessor_tasks_sha256=sha(A/'tasks.json'),predecessor_plan_sha256=sha(A/'plan.json'),affected_id=bad['id'],partner_id=partner['id'],selection='First current-policy-valid fresh swap among Curadi san non-Lun singleton families already in paired240, ordered by SHA256(original_seed+minimal-source-repair+partnerID). No outcomes used.',task_changes=2,optimality='The new feasible set is a subset of the old one. A feasible repair reaches exactly the old maximum coverage, minimum repetitions and minimum squared loads, so it remains globally optimal. Retaining the affected singleton family and exact tense quotas requires at least two changed tuples; this repair attains that lower bound.'))
 np['source_hashes']['generator']=dict(path=str(Path(__file__)),sha256=sha(Path(__file__)))
 np['source_hashes']['source_plan']=dict(path=str(A/'plan.json'),sha256=sha(A/'plan.json'))
 for key,path in [('supply',OUT/'development-confirmation-policy21.supply.json'),('policy',OUT.parent/'oracle-policy-21.json'),('adapter',ROOT/'misc/vp_cartesian_task.py')]:np['source_hashes'][key]=dict(path=str(path),sha256=sha(path))
 atomic_json(P/'plan.json',np);atomic_json(P/'historical-inputs.json',history_audit)
 v=Vyakarana();mapping={};replacement={bad['id']:second,partner['id']:first}
 for t in ts:
  z=deepcopy(replacement.get(t['id'],t));campaign={**deepcopy(t['campaign']),**z['campaign']};campaign.update(panel=np['panel'],plan_sha256=sha(P/'plan.json'),oracle_policy=np['oracle_policy'],audit_status='Policy21; minimal input-only source repair, full regeneration and historical novelty checks.')
  if t['id'] in replacement:campaign['lexical_bases']=sorted({q.text for q in v.derive(es[z['dhatu']['code']].dhatu)})
  z['campaign']=campaign;mapping[t['id']]=z
 stages=[]
 for i,chunk in enumerate(read(A/'transport-plan.json')['chunks']):
  rows=[mapping[t['id']] for t in read(Path(chunk['tasks_path']))];assert len(rows)==400;stages.append(rows);atomic_json(P/f'chunk-{i+1:02}.tasks.json',rows)
 new=sum(stages,[]);assert len(new)==len({t['id'] for t in new})==len({normalized(t)[0] for t in new})==2400
 assert all(normalized(t)[0] not in used for t in new)
 def features(tasks):
  return {k:dict(Counter(f(t) for t in tasks)) for k,f in dict(cell=cell,gana=lambda t:t['dhatu']['gana'],family=lambda t:t['campaign']['root_family'],PN=lambda t:(t['morphology']['purusha'],t['morphology']['vacana'])).items()}
 assert features(ts)==features(new)
 for old,newchunk in zip(read(A/'transport-plan.json')['chunks'],stages):
  ot=read(Path(old['tasks_path']));assert Counter(cell(t) for t in ot)==Counter(cell(t) for t in newchunk);assert Counter(tuple(t['morphology'].values()) for t in ot)==Counter(tuple(t['morphology'].values()) for t in newchunk)
 atomic_json(P/'tasks.json',new);tr=deepcopy(read(A/'transport-plan.json'));tr['chunks']=[dict(order=i+1,n=400,tasks_path=str(P/f'chunk-{i+1:02}.tasks.json'),sha256=sha(P/f'chunk-{i+1:02}.tasks.json'),ids=[t['id'] for t in c],cell_counts=dict(Counter(cell(t) for t in c))) for i,c in enumerate(stages)];atomic_json(P/'transport-plan.json',tr)
 atomic_json(P/'allocation-objective.json',read(A/'allocation-objective.json'));atomic_json(P/'distribution-and-family-audit.json',read(A/'distribution-and-family-audit.json'))
 # Family recipe exposures are unchanged because the same singleton families still use san.
 exposure=read(A/'exposure-and-novelty-audit.json');exposure['historical_input_snapshot']=history_audit;atomic_json(P/'exposure-and-novelty-audit.json',exposure)
 audit=validate(new,'development',allowed_families=set(loads));audit.update(tasks_sha256=sha(P/'tasks.json'),plan_sha256=sha(P/'plan.json'),policy='oracle-policy-21');atomic_json(P/'shared-regeneration-audit.json',audit)
 with (P/'prompts.jsonl').open('w') as f:
  for t in new:
   prompt=render(t);assert hashlib.sha256(prompt.encode()).hexdigest()==t['campaign']['prompt_sha256'];f.write(json.dumps(dict(id=t['id'],prompt=prompt),ensure_ascii=False)+'\n')
 files=['plan.json','tasks.json',*[f'chunk-{i+1:02}.tasks.json' for i in range(6)],'transport-plan.json','allocation-objective.json','distribution-and-family-audit.json','exposure-and-novelty-audit.json','shared-regeneration-audit.json','prompts.jsonl']
 atomic_json(P/'manifest.json',dict(created_at=now(),status='unpaid_minimal_source_repair',n=2400,family_count=670,source_hashes=np['source_hashes'],files={f:dict(sha256=sha(P/f),bytes=(P/f).stat().st_size) for f in files},tasks_digest=digest(new),shared_validation_passed=True,all_distribution_and_prompt_checks_passed=True,paid_calls=0,no_final_answers_read=True,benchmark_ready=False))
 Q=P/'astra-subset';Q.mkdir();ss=[]
 for i,oldchunk in enumerate(read(A/'astra-subset/transport-plan.json')['chunks']):
  rows=[mapping[t['id']] for t in read(Path(oldchunk['tasks_path']))];ss.append(rows);atomic_json(Q/f'chunk-{i+1:02}.tasks.json',rows)
 newsub=sum(ss,[]);assert features(sub)==features(newsub);atomic_json(Q/'tasks.json',newsub)
 sp=deepcopy(read(A/'astra-subset/plan.json'));sp.update(created_at=now(),policy='oracle-policy-21',adapter_sha256=EXPECTED,source_tasks_sha256=sha(P/'tasks.json'),selection_script_sha256=sha(Path(__file__)),minimal_repair=np['minimal_repair']);atomic_json(Q/'plan.json',sp)
 audit=validate(newsub,'development');audit.update(exact_parent_task_metadata=True,all42joint_cells_supported=True,all10classes_supported=True,all10lakaras_supported=True,source_policy_hash=sha(OUT.parent/'oracle-policy-21.json'),no_extra_unique_questions=True,no_model_answers_read=True);atomic_json(Q/'audit.json',audit)
 strans=deepcopy(read(A/'astra-subset/transport-plan.json'));strans['chunks']=[dict(order=i+1,n=120,tasks_path=str(Q/f'chunk-{i+1:02}.tasks.json'),sha256=sha(Q/f'chunk-{i+1:02}.tasks.json'),ids=[t['id'] for t in c]) for i,c in enumerate(ss)];atomic_json(Q/'transport-plan.json',strans)
 atomic_json(Q/'manifest.json',dict(created_at=now(),tasks_digest=digest(newsub),files={f:dict(sha256=sha(Q/f),bytes=(Q/f).stat().st_size) for f in ['tasks.json','plan.json','audit.json','transport-plan.json','chunk-01.tasks.json','chunk-02.tasks.json']},parent_tasks_sha256=sha(P/'tasks.json'),n=240,paid_calls=0))
 shared={t['id'] for t in ts}&{t['id'] for t in new};assert len(shared)==2398 and len({t['id'] for t in sub}&{t['id'] for t in newsub})==238
 om={t['id']:t for t in ts};nm={t['id']:t for t in new}
 for tid in shared:
  for k in ['dhatu','morphology','derivation','gold_slp1','gold_devanagari','prompt_version']:assert om[tid][k]==nm[tid][k]
  assert om[tid]['campaign']['prompt_sha256']==nm[tid]['campaign']['prompt_sha256']
 atomic_json(P/'minimal-repair-audit.json',dict(created_at=now(),policy='oracle-policy-21',adapter_sha256=EXPECTED,predecessor_primary_sha256=sha(A/'tasks.json'),revised_primary_sha256=sha(P/'tasks.json'),predecessor_subset_sha256=sha(A/'astra-subset/tasks.json'),revised_subset_sha256=sha(Q/'tasks.json'),primary_shared_ids=2398,subset_shared_ids=238,old_to_new_ids={k:t['id'] for k,t in replacement.items()},deterministic_partner_checks=checks,all_primary_quota_PN_family_loads_unchanged=True,all_chunk_morphology_counts_unchanged=True,all_subset_cells_classes_and_family_pair_support_unchanged=True,all_three_global_optimal_objectives_unchanged=True,objective=read(P/'allocation-objective.json'),minimum_changed_tuples=2,optimality_proof=np['minimal_repair']['optimality'],all_shared_grammar_gold_prompts_unchanged=True,no_model_answers_read=True,paid_calls=0))
 assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 print(json.dumps(dict(primary_sha256=sha(P/'tasks.json'),subset_sha256=sha(Q/'tasks.json'),minimal_repair_sha256=sha(P/'minimal-repair-audit.json'),changed=2),indent=2))
 status('Policy21 minimal repair prepared','Revision02 replaces exactly two primary and paired tuples, retaining all families, quotas, PN margins, chunk counts and optimal allocation objectives. All forms regenerate; no paid calls.')
if __name__=='__main__':main()
