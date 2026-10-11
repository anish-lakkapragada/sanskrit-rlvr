"""Additive complete-development-panel audit; no provider calls or mutations."""
from pathlib import Path
import sys,json,hashlib,difflib
from collections import Counter,defaultdict
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(ROOT))
from misc.vp_5d_analyze_08_r2 import verify_panel,verify_results
from misc.vp_goal_validate import validate
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue
from misc.vp_cartesian_analyze import completed
from vidyut.lipi import transliterate,Scheme
PANEL=HERE.parent/'pilot-08/revision-02';JOBS=ROOT/'benchmarks/iterative-goal-20261006/jobs'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,x):(HERE/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def slp(r):return transliterate(r['answer'],Scheme.Devanagari,Scheme.Slp1) if isinstance(r['answer'],str) else None
def summary(rs):return {'n':len(rs),'correct':sum(r['is_correct'] is True for r in rs),'usable':sum(completed(r) for r in rs),'status':dict(Counter(r['status'] for r in rs))}
def pure_extra(t,a):
 if t['morphology']['lakara']!='Lun' or not a or not a.startswith('a'):return None
 for g in t['gold_slp1']:
  if g.startswith('a'):
   for k in range(1,6):
    if len(a)>k and 'a'+a[k+1:]==g:return {'removed_after_augment':a[1:k+1],'gold':g}
 return None

def main():
 decl=read(PANEL/'analysis-predeclaration.json');agg=read(PANEL/'aggregate-analysis.json');assert agg['all8settled_and_collected']
 fingerprints={}
 for name,h in decl['frozen_files'].items():fingerprints[str((PANEL/name).relative_to(ROOT))]=dict(expected=h,observed=sha(PANEL/name))
 for name,h in decl['analysis_dependencies'].items():fingerprints[name]=dict(expected=h,observed=sha(ROOT/name))
 assert all(v['expected']==v['observed'] for v in fingerprints.values())
 ts,ch,sub,ach=verify_panel(PANEL)
 validate(ts,'development')
 result_sources={str((JOBS/e['id']/'results.json').relative_to(ROOT)):sha(JOBS/e['id']/'results.json') for e in decl['expected_jobs']}
 results=[read(JOBS/e['id']/'results.json') for e in decl['expected_jobs']]
 opus,astra=verify_results(ch+ach,results)
 es=entries_by_code();issues=[{'id':t['id'],'reason':entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)} for t in ts];issues=[x for x in issues if x['reason']]
 assert not issues
 write('fingerprint-and-regeneration.json',dict(created_at=datetime.now(timezone.utc).isoformat(),complete_panel_released_by_parent=True,primary_n=len(ts),paired_n=len(sub),full_primary_shared_validation=True,exact_result_task_identity=True,all_fingerprints_match=True,fingerprints=fingerprints,result_sources=result_sources,aggregate_sha256=sha(PANEL/'aggregate-analysis.json'),policy_sha256=sha(HERE.parents[1]/'oracle-policy-21.json'),scope_exclusions=issues,model_answers_relabelled=False,paid_calls=0))
 inventory=[];groups={};rules={}
 for provider,rs in [('Opus',opus),('Astra',astra)]:
  cg=defaultdict(list);cr=defaultdict(list)
  good=[r for r in rs if r['is_correct'] is True]
  for i,r in enumerate(rs):
   t=r['task'];recipe=t['derivation']['recipe_id'];m=t['morphology'];a=slp(r)
   for k in [recipe,recipe+'|'+m['lakara'],recipe+'|'+m['prayoga'],t['dhatu']['gana']]:cg[k].append(r)
   for rule in t['campaign']['trace_rule_ids']:cr[rule].append(r)
   if r['is_correct'] is True:continue
   near=max(t['gold_slp1'],key=lambda g:difflib.SequenceMatcher(None,g,a or '').ratio())
   controls=sorted(good,key=lambda g:(g['task']['dhatu']['code']!=t['dhatu']['code'],g['task']['derivation']['recipe_id']!=recipe,g['task']['morphology']['lakara']!=m['lakara'],g['task']['dhatu']['gana']!=t['dhatu']['gana'],-len(set(g['task']['campaign']['trace_rule_ids'])&set(t['campaign']['trace_rule_ids'])),g['task']['id']))[:2]
   inventory.append(dict(provider=provider,index=i,id=t['id'],code=t['dhatu']['code'],citation=t['dhatu']['aupadeshika'],gana=t['dhatu']['gana'],artha=t['dhatu']['artha'],recipe=recipe,morphology=m,status=r['status'],usable=completed(r),answer=a,gold=t['gold_slp1'],pure_extra_after_augment=pure_extra(t,a),nearest_gold=near,edit_opcodes=difflib.SequenceMatcher(None,near,a or '').get_opcodes(),trace_rules=t['campaign']['trace_rule_ids'],matched_success_ids=[x['task']['id'] for x in controls],output_text=r['output_text'] if not completed(r) else None,refusals=r['refusals'],stop_reason=r.get('stop_reason')))
  groups[provider]={k:summary(rr) for k,rr in sorted(cg.items())}
  rules[provider]={k:summary(rr) for k,rr in sorted(cr.items())}
 om={r['task']['id']:r for r in opus}
 both=[]
 for r in astra:
  o=om[r['task']['id']]
  if completed(r) and completed(o) and not r['is_correct'] and not o['is_correct']:
   both.append(dict(id=r['task']['id'],code=r['task']['dhatu']['code'],recipe=r['task']['derivation']['recipe_id'],morphology=r['task']['morphology'],gold=r['task']['gold_slp1'],opus=slp(o),astra=slp(r),same_answer=slp(o)==slp(r)))
 write('disagreement-inventory.json',inventory);write('both-reference-disagreements.json',both)
 write('triage-summary.json',dict(primary=summary(opus),paired_astra=summary(astra),groups=groups,rule_presence=rules,pure_extra_after_augment=dict(Counter(x['provider'] for x in inventory if x['pure_extra_after_augment'])),both_wrong=len(both),both_same_wrong=sum(x['same_answer'] for x in both),limitations='Mechanical triage flags are hypotheses for source review, not gold certification or outcome reclassification.'))
 print(json.dumps({'Opus':summary(opus),'Astra':summary(astra),'pure_extra':dict(Counter(x['provider'] for x in inventory if x['pure_extra_after_augment'])),'both_wrong':len(both),'both_same_wrong':sum(x['same_answer'] for x in both)}))
if __name__=='__main__':main()
