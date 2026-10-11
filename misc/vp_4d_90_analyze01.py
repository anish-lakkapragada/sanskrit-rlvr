#!/usr/bin/env python3
"""Analyze a fully completed fixed 4D-90 pilot; no model calls or source edits."""
from collections import Counter, defaultdict
from pathlib import Path
import argparse, hashlib, json, math, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import write, now, sha
from misc.vp_cartesian_task import oracle_issue
OUT=ROOT/'benchmarks/parallel-search-20261007/four_d-90'
SEED=2026100790

def usable(r):return r['status']=='completed' and not r.get('truncated') and not r.get('refusals') and r.get('answer') is not None

def stats(rs):
 if not rs:return {'n':0}
 vals=[int(bool(r.get('is_correct')) and usable(r)) for r in rs];n=len(vals);p=sum(vals)/n
 groups=defaultdict(list)
 for r,y in zip(rs,vals):groups[r['task']['campaign']['root_family']].append(y)
 g=len(groups);ns=np.array([len(v) for v in groups.values()]);ys=np.array([sum(v) for v in groups.values()]);sse=float(np.square(ys-p*ns).sum())
 rng=np.random.default_rng(SEED);draw=rng.integers(0,g,size=(10000,g));boot=ys[draw].sum(axis=1)/ns[draw].sum(axis=1)
 return {'n':n,'correct':sum(vals),'accuracy':p,'families':g,'iid_standard_error':math.sqrt(p*(1-p)/n),'family_sandwich_standard_error':math.sqrt(g/(g-1)*sse/n**2) if g>1 else None,'family_bootstrap95':np.quantile(boot,[.025,.975]).tolist(),'wrong_or_missing_families':len({r['task']['campaign']['root_family'] for r,y in zip(rs,vals) if not y}),'wrong_usable_families':len({r['task']['campaign']['root_family'] for r,y in zip(rs,vals) if usable(r) and not y})}

def analyze(path):
 manifest=json.loads((OUT/'manifest.json').read_text());tasks=json.loads((OUT/'tasks.json').read_text());assert sha(OUT/'tasks.json')==manifest['questions_sha256']
 expected={t['id']:t for t in tasks};rs=json.loads(Path(path).read_text())
 assert isinstance(rs,list) and len(rs)==200 and len({r['task_id'] for r in rs})==200,'Complete fixed200 required'
 assert {r['task_id'] for r in rs}==set(expected)
 for r in rs:assert r['task']==expected[r['task_id']],'Frozen task mismatch'
 def summarize(rows):
  good=[r for r in rows if usable(r)];a=stats(rows);b=stats(good);unknown=len(rows)-len(good)
  return {'all_request':a,'usable':b,'refusals':sum(bool(r.get('refusals')) for r in rows),'truncations':sum(bool(r.get('truncated')) for r in rows),'unusable':unknown,'missing_answer_accuracy_bounds':[a['correct']/len(rows),(a['correct']+unknown)/len(rows)] if rows else None}
 raw=summarize(rs);exclusions=[{'id':r['task_id'],'reason':oracle_issue(r['task'])} for r in rs if oracle_issue(r['task'])]
 kept=[r for r in rs if not oracle_issue(r['task'])]
 groups={}
 for name in ['cell','lakara','gana']:
  by=defaultdict(list)
  for r in rs:
   t=r['task'];key=t['campaign']['sampling_cell']['label'] if name=='cell' else t['morphology'][name] if name=='lakara' else t['dhatu'][name]
   by[key].append(r)
  groups[name]={k:summarize(v) for k,v in by.items()}
 passes=(raw['all_request']['accuracy']<.9 and raw['usable'].get('accuracy',1)<.9 and raw['usable'].get('wrong_usable_families',0)>=5)
 return dict(created_at=now(),panel='4d-90-pilot01',questions_sha256=manifest['questions_sha256'],results_path=str(path),results_sha256=sha(path),analyzer_sha256=sha(__file__),raw=raw,groups=groups,current_scope_exclusions=exclusions,current_scope=summarize(kept) if kept else None,numerical_exploration_screen_passes=passes,source_supported_exploration_decision='Pending bounded disagreement/source review; numerical screen alone does not certify model errors.',benchmark_ready=False,limits=['200 development tasks,109 families;52% of questions are concentrated in13 short-adanta families.','No independent test or strongest-model ordering claim.','Empirical zero-variance cells do not establish population certainty.','Policy-filtered supplement does not replace frozen raw headline.'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('results');p.add_argument('--output',default=str(OUT/'analysis.json'));a=p.parse_args();out=Path(a.output)
 assert not out.exists(),'Preserve prior analyses';result=analyze(a.results);write(out,result);print(json.dumps({'raw':result['raw'],'numerical_exploration_screen_passes':result['numerical_exploration_screen_passes']},indent=2))
