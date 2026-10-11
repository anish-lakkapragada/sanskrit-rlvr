"""Additive offline review; reads direct response text, never writes source records."""
import json,hashlib,re,unicodedata
from pathlib import Path
from collections import Counter
from misc.vp_modification_prompt_v1 import render as render_mod
from misc.vp_cartesian_prompt_v3 import render as render_ctl
from misc.vp_modification_task_v1 import validate_task
from misc.vp_4d_pilot import load_entries
from misc.vp_cartesian_task import make_task
from misc.oai_batch_eval import extract_answer,normalize
ROOT=Path.cwd();OUT=ROOT/'benchmarks/parallel-search-20261007/modification-01'
J=ROOT/'benchmarks/iterative-goal-20261006/jobs'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda a:hashlib.sha256(json.dumps(a,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
plan=read(ROOT/'benchmarks/parallel-search-20261007/acceleration/plan.json')
original={'modification':read(OUT/'tasks.json'),'control':read(OUT/'controls.json')}
rows={};fingerprints={};proofs=Counter();provider_ids=[];examples=[]
for arm in original:
 flat=[];rr=[]
 for st in [s for s in plan['stages'] if s['arm']==arm]:
  inp=ROOT/st['path'];assert sha(inp)==st['sha256'];ts=read(inp);d=J/st['id'];rs=read(d/'results.json');qs=read(d/'requests.json');assert ts==read(d/'tasks.json');assert len(ts)==len(rs)==len(qs)==40
  for f in [inp,d/'tasks.json',d/'results.json',d/'requests.json']:fingerprints[str(f.relative_to(ROOT))]=sha(f)
  for i,(t,r,q) in enumerate(zip(ts,rs,qs)):
   assert t==r['task'] and t['id']==r['task_id'] and r['request']==q and r['custom_id']==q['custom_id']==f'task-{i:05}'
   assert read(d/f'task-{i:05}.intent.json')['request_digest']==digest(q)
   prm=q['params'];assert set(prm)=={'model','max_tokens','messages','thinking','output_config','tools','tool_choice','stream'}
   assert prm['model']=='claude-opus-5-5' and prm['max_tokens']==65536 and prm['tools']==[] and prm['tool_choice']=={'type':'none'} and prm['output_config']=={'effort':'xhigh'}
   if arm=='modification':
    public={k:t[k] for k in ['source_form_devanagari','source_morphology','target_morphology']}
    prompt=render_mod(public);assert prompt==render_mod(t)
    assert t['source_form_devanagari'] not in t['gold_devanagari']
    validate_task(t,'development');proofs['modification_full_regeneration_collision_validation']+=1
   else:prompt=render_ctl(t)
   assert prm['messages']==[{'role':'user','content':prompt}]
   assert hashlib.sha256(prompt.encode()).hexdigest()==t['campaign']['prompt_sha256']
   raw=read(d/f'task-{i:05}.result.json');http=read(d/f'task-{i:05}.http.json');msg=raw['result']['message']
   assert raw==r['raw_batch_result'] and http['status_code']==200 and http['body']==msg
   assert raw['custom_id']==q['custom_id'] and raw['result']['type']=='succeeded' and msg['stop_reason']=='end_turn'
   provider_ids.append(msg['id']);text=''.join(c.get('text','') for c in msg['content'] if c['type']=='text')
   assert text==r['output_text'];a=extract_answer(text);assert a==r['answer'];grade=normalize(a) in {normalize(g) for g in t['gold_devanagari']}
   # A second, stricter implementation: exactly one answer tag and no surrounding prose.
   match=re.fullmatch(r'\s*<answer>([^<>]+)</answer>\s*',text);assert match
   independent=unicodedata.normalize('NFC',match.group(1).strip()) in {unicodedata.normalize('NFC',g.strip()) for g in t['gold_devanagari']}
   assert grade==independent==r['is_correct']
   assert r['status']=='completed' and not r['truncated']
   proofs[arm+'_correct']+=grade;proofs[arm+'_requests_raw_texts_regraded']+=1
  flat.extend(ts);rr.extend(rs)
 assert flat==original[arm];assert len({t['id'] for t in flat})==200;rows[arm]={r['task_id']:r for r in rr}
assert len(set(provider_ids))==400
controls=rows['control'];paired=Counter();retained=Counter();es={e.code:e for e in load_entries()}
for t in original['modification']:
 c=controls[t['campaign']['control_task_id']];m=rows['modification'][t['id']];ct=c['task']
 assert t['gold_devanagari']==ct['gold_devanagari'] and t['gold_slp1']==ct['gold_slp1'] and t['target_morphology']==ct['morphology'] and t['dhatu']==ct['dhatu']
 regenerated=make_task(es[ct['dhatu']['code']],'development',ct['morphology'],prompt_version=ct['prompt_version']);assert regenerated['gold_devanagari']==ct['gold_devanagari']
 paired[f"mod{int(m['is_correct'])}_control{int(c['is_correct'])}"]+=1
 if t['dhatu']['code']!='10.0400':retained['n']+=1;retained['modification_correct']+=m['is_correct'];retained['control_correct']+=c['is_correct']
 if not c['is_correct'] or t['dhatu']['code']=='10.0400':examples.append(dict(code=t['dhatu']['code'],root=t['dhatu']['aupadeshika'],source=t['source_form_devanagari'],source_morphology=t['source_morphology'],target_morphology=t['target_morphology'],gold=t['gold_devanagari'],control_output=c['output_text'],modification_output=m['output_text'],modification_id=t['id'],control_id=ct['id'],prospective_scope_hold=t['dhatu']['code']=='10.0400'))
result=dict(proofs=dict(proofs),distinct_provider_message_ids=len(set(provider_ids)),identical_gold_pairs=200,paired_transition_counts=dict(paired),source_hold_sensitivity=dict(retained),fingerprints=fingerprints,examples=examples,no_frozen_or_raw_files_modified=True)
(OUT/'direct-result-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['fingerprints','examples']},indent=2))
