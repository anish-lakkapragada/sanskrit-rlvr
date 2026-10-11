"""Bounded new-input source-context screen; reads input artifacts only."""
import json
from pathlib import Path
from collections import Counter
from misc.vp_5d_prepare_04 import ROOT,OUT,sha,now,atomic_json,status
from misc.vp_5d_history_18 import history
from misc.vp_5d_candidate_nested_audit import traces
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue,make_task
from misc.vp_5d_prepare_03 import SOURCE_ROOTS
from misc.vp_5d_prepare_05 import UNRESOLVED
P=OUT/'pilot-08'
def read(p):return json.loads(p.read_text())
def context(ts):return Counter((t.get('derivation',{}).get('recipe_id'),r) for t in ts for r in t.get('campaign',{}).get('trace_rule_ids',[]))
def main():
 assert not(P/'source-rule-delta-audit.json').exists();ts=read(P/'tasks.json');_,_,h=history();es=entries_by_code()
 paths=sorted({Path(p['path']) for p in h['task_files'] if 'five-d' in p['path']}|{OUT/'candidate-4800/revision-04/tasks.json',OUT/'pilot-07/tasks.json',OUT/'pilot-07/revision-01/tasks.json'})
 prior=[t for p in paths for t in read(p)];prior=[t for t in prior if 'dhatu' in t and not(entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t))]
 ctx=context(prior);new=context(ts);delta=set(new)-set(ctx);rules={r for _,r in new}-{r for _,r in ctx};controls=[]
 for t in ts:
  hit=[r for r in t['campaign']['trace_rule_ids'] if (t['derivation']['recipe_id'],r) in delta]
  if hit:controls.append(dict(id=t['id'],code=t['dhatu']['code'],sanadi=t['derivation']['sanadi'],morphology=t['morphology'],rules=hit,derivations=traces(t['dhatu']['code'],t['derivation']['sanadi'],t['morphology'])))
 sourcechecks=[]
 for check in read(OUT/'pilot-03.source-audit.json')['direct_checks']:
  t=make_task(es[check['code']],'source_control',check['morphology'],'source_control',check['sanadi'],prompt_version='cartesian-5d-v3-sanskrit');assert check['expected'] in t['gold_slp1'];sourcechecks.append({**check,'current_gold_slp1':t['gold_slp1'],'passed':True})
 assert all(t['dhatu']['code'] not in set(SOURCE_ROOTS)|set(UNRESOLVED) and not(entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)) for t in ts)
 report=dict(created_at=now(),policy='oracle-policy-19',policy_sha256=sha(OUT.parent/'oracle-policy-19.json'),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),tasks_sha256=sha(P/'tasks.json'),previous_input_sources=[dict(path=str(p),sha256=sha(p)) for p in paths],current_scope_previous_tasks=len(prior),new_rule_ids=sorted(rules),new_recipe_rule_contexts=[dict(recipe=r,rule=x,n=new[r,x]) for r,x in sorted(delta)],new_context_controls=controls,independent_printed_recipe_controls=sourcechecks,all_source_and_unresolved_codes_excluded=True,no_model_answers_read=True,scope='Rule-ID coverage and printed primary recipe controls are bounded diagnostics, not exhaustive proof of all rare forms. Current shared policy applies outcome-independently; any new concrete concern is independently resolved before payment.',paid_calls=0)
 atomic_json(P/'source-rule-delta-audit.json',report)
 print(json.dumps({k:report[k] for k in ['new_rule_ids','new_recipe_rule_contexts','current_scope_previous_tasks']},indent=2))
if __name__=='__main__':main()
