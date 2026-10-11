"""Input-only, read-only pre-outcome audit. Never opens answer/HTTP result files."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from misc import vp_goal as r
from misc.vp_cartesian_prompt_v1 import render
ROOT=Path.cwd();OUT=ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(OUT/'plan.json');ph=sha(OUT/'plan.json');state=r.load()
assert ph=='14bdcb0f9dce2d456850f733502c3d3512c44180abf3978ad38f68b046fd9af5'
assert plan['additional_cap_micro']==150000000 and plan['maximum_per_stage_micro']==32918000
assert plan['provider']=='OpenAI' and plan['model']=='gpt-6-astra' and plan['effort']=='xhigh' and plan['max_output_tokens']==65536
assert plan['service_tier']=='default' and plan['maximum_concurrency']==8
for f,h in plan['dependencies'].items():assert sha(ROOT/f)==h
pool=state['submission_pools'][plan['spending_pool']]
assert pool==dict(provider='OpenAI',cap_micro=150000000,job_ids=[x['id'] for x in plan['stages']],plan_sha256=ph)
assert plan['protected_allocation']==r.protected_allocations(state)
source,opus_original=r.verify_job(state['jobs'][plan['source_job']]);assert len(source)==200 and r.digest(source)==plan['source_tasks_digest']
opus_direct=[]
for i in range(1,6):
 t,q=r.verify_job(state['jobs'][f'opus-fast-simple4d-{i:02}']);opus_direct.extend(q)
assert [q['params']['messages'] for q in opus_direct]==[q['params']['messages'] for q in opus_original]
flat=[];allprompts=[];counts=[];proofs=[];effective=[];fingerprints={}
for index,stage in enumerate(plan['stages']):
 assert stage['start']==index*10 and stage['stop']==index*10+10 and stage['n']==10
 job=state['jobs'][stage['id']];ts,qs=r.verify_job(job);d=r.OUT/'jobs'/job['id']
 assert job['provider']=='OpenAI' and job['phase']=='confirm_64k' and job['transport']=='direct' and job['spending_pool_id']==plan['spending_pool']
 assert ts==source[index*10:index*10+10] and r.digest(ts)==stage['tasks_digest'] and sha(ROOT/stage['path'])==stage['sha256']
 cs=read(d/'input-counts.json');assert cs['requests_digest']==job['requests_digest'] and set(cs['counts'])=={q['custom_id'] for q in qs}
 assert len(cs['counts'])==10 and cs['maximum']==max(cs['counts'].values())<=1300
 assert all(type(n) is int and 0<n<=1300 for n in cs['counts'].values());counts.extend(cs['counts'].values())
 for n,(t,q) in enumerate(zip(ts,qs)):
  assert q==r.request(t,'OpenAI','confirm_64k',n)
  assert set(q)=={'custom_id','method','url','body'} and q['custom_id']==f'task-{n:05}'
  minimal=dict(task_type='cartesian_4d',dhatu={k:t['dhatu'][k] for k in ['aupadeshika','gana','artha']},morphology=t['morphology'])
  prompt=render(minimal);assert prompt==render(t)
  assert q['body']['input']==[{'role':'user','content':prompt}]==opus_original[index*10+n]['params']['messages']
  assert hashlib.sha256(prompt.encode()).hexdigest()==t['campaign']['prompt_sha256'];allprompts.append(prompt)
  # No task/gold metadata, hidden system/history, tools or attachments enter request body.
  assert set(q['body'])=={'model','input','reasoning','max_output_tokens','tools','tool_choice','store','stream','truncation'}
  p=d/(q['custom_id']+'.effective-request.json')
  if p.exists():
   ef=read(p);assert ef['body']==dict(q['body'],service_tier='default')
   assert ef['canonical_request_digest']==r.digest(q) and ef['effective_body_digest']==r.digest(ef['body'])
   intent=read(d/(q['custom_id']+'.intent.json'));assert intent['request_digest']==r.digest(q)
   effective.append(dict(job=job['id'],custom_id=q['custom_id'],path=str(p.relative_to(ROOT)),sha256=sha(p)))
 for name in ['tasks.json','requests.json','input-counts.json']:fingerprints[str((d/name).relative_to(ROOT))]=sha(d/name)
 flat.extend(ts);proofs.append(dict(job=job['id'],n=10,input_count_max=cs['maximum']))
assert len(plan['stages'])==20 and flat==source and len({t['id'] for t in flat})==len(set(allprompts))==200
assert sha(OUT/'plan.json')==ph
out=dict(created_at=datetime.now(timezone.utc).isoformat(),disposition='PASS: exact complete canonical request partition; observed effective requests match only the declared standard-tier augmentation',n=200,stages=20,source_task_digest=r.digest(source),plan_sha256=ph,pool=pool,protected_allocation_unchanged=True,model_visible_identity_with_original_and_direct_opus=200,public_only_rendering_without_gold_trace_task_id_code_campaign=200,exact_count_guards=200,counted_input_min=min(counts),counted_input_max=max(counts),input_allowance=1500,maximum_counted_input=1300,distinct_prompts=200,root_families=len({t['campaign']['root_family'] for t in flat}),distribution={k:dict(Counter(t['morphology'][k] for t in flat)) for k in ['lakara','prayoga','purusha','vacana']},observed_effective_requests=len(effective),effective_request_proofs=effective,canonical_file_fingerprints=fingerprints,stages_checked=proofs,limitations=['Effective receipts are a point-in-time input-only snapshot; later receipts were not awaited.','No HTTP response, result JSON, answer text or accuracy was opened.','This is protocol/input integrity, not completion, accuracy or source certification.'],paid_calls=0,ledger_mutations=0)
(OUT/'request-review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:out[k] for k in ['n','stages','root_families','counted_input_min','counted_input_max','observed_effective_requests','plan_sha256']},indent=2))
