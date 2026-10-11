"""Frozen eight-job pilot08 analysis. No APIs and no partial outcome analysis.

Prepare before any answers. Analyze only after sixOpus400 and twoAstra120 jobs
are settled and collected, with exact frozen task metadata and partitions.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from misc.vp_5d_prepare_04 import ROOT,OUT,atomic_json,now,sha
from misc.vp_5d_novelty_04 import normalized
from misc.vp_5d_candidate_4800_p18 import digest,cell
from misc.vp_5d_analyze_07 import describe,screen
from misc.vp_5d_dependence_06 import analyze as dependence
from misc.vp_5d_cap_protocol_01 import cost,usage,distribution
from misc.vp_cartesian_analyze import completed,metric
from misc.vp_cartesian_task import entry_scope_issue,oracle_issue,entries_by_code
JOBS=[(f'opus-five-d-pilot-08-{i:02}',400,'Anthropic') for i in range(1,7)]+[(f'astra-five-d-pilot-08-{i:02}',120,'OpenAI') for i in range(1,3)]
DEPS=['misc/vp_5d_analyze_08_r1.py','misc/vp_cartesian_visibility.py','misc/vp_5d_analyze_07.py','misc/vp_5d_dependence_06.py','misc/vp_5d_dependence_05.py','misc/vp_5d_metrics.py','misc/vp_5d_cap_protocol_01.py','misc/vp_cartesian_final_analyze.py','misc/vp_cartesian_analyze.py','misc/vp_goal_stats.py']
B=20000;SEED=202610071208

def read(p):return json.loads(Path(p).read_text())
def verify_directory(p,n,nchunks,chunkn):
 manifest=read(p/'manifest.json')
 for f,rec in manifest['files'].items():
  if sha(p/f)!=rec['sha256']:raise ValueError('Frozen file changed: '+str(p/f))
 ts=read(p/'tasks.json');tr=read(p/'transport-plan.json');chunks=[]
 if len(ts)!=n or len(tr['chunks'])!=nchunks:raise ValueError('Incorrect fixedN/partition')
 for ch in tr['chunks']:
  path=Path(ch['tasks_path'])
  if sha(path)!=ch['sha256']:raise ValueError('Chunk digest changed')
  rows=read(path)
  if len(rows)!=chunkn or [t['id'] for t in rows]!=ch['ids']:raise ValueError('Chunk membership/order changed')
  chunks.append(rows)
 if sum(chunks,[])!=ts or len({t['id'] for t in ts})!=n:raise ValueError('Non-disjoint ordered partition')
 if any(t['campaign']['split']!='development' for t in ts):raise ValueError('Only development tasks allowed')
 return ts,chunks

def verify_panel(p):
 ts,ch=verify_directory(p,2400,6,400);sub,ach=verify_directory(p/'astra-subset',240,2,120);mapping={t['id']:t for t in ts}
 if any(t!=mapping.get(t['id']) for t in sub):raise ValueError('Paired task metadata not identical')
 if read(p/'plan.json')['max_output_tokens']!=65536 or read(p/'astra-subset/plan.json')['max_output_tokens']!=65536:raise ValueError('Common64k protocol changed')
 return ts,ch,sub,ach

def prepare(p):
 p=p.resolve();dest=p/'analysis-predeclaration.json'
 if dest.exists():raise ValueError('Preserve existing analysis declaration')
 ts,ch,sub,ach=verify_panel(p);prior=set();exposure=read(p/'exposure-and-novelty-audit.json')
 for rec in exposure['historical_input_snapshot']['task_files']:
  path=Path(rec['path'])
  if sha(path)!=rec['sha256']:raise ValueError('Historical input snapshot changed')
  for t in read(path):
   k=normalized(t)[0]
   if k is not None:prior.add((k[0]+'|'+k[1],tuple(k[2])))
 groups={t['id']:dict(family=t['campaign']['root_family'],recipe=t['derivation']['recipe_id'],previously_exposed_same_recipe=(t['campaign']['root_family'],tuple(t['derivation']['sanadi'])) in prior) for t in ts}
 if sum(g['previously_exposed_same_recipe'] for g in groups.values())!=exposure['question_count_with_prior_same_recipe_family_exposure']:raise ValueError('Exposure classification mismatch')
 atomic_json(p/'analysis-exposure-groups.json',groups)
 files=['tasks.json','plan.json','manifest.json','transport-plan.json','analysis-exposure-groups.json','source-rule-delta-audit.json']+['astra-subset/'+s for s in ['tasks.json','plan.json','manifest.json','transport-plan.json','audit.json']]
 decl=dict(analyzer_module='misc.vp_5d_analyze_08_r1',created_at=now(),fixed_primary_n=2400,fixed_paired_n=240,phase='confirm_64k',effort='xhigh',max_output_tokens=65536,common_provider_ceiling=True,expected_jobs=[dict(id=j,n=n,provider=provider,tasks_digest=digest(c)) for (j,n,provider),c in zip(JOBS,ch+ach)],frozen_files={f:sha(p/f) for f in files},analysis_dependencies={f:sha(ROOT/f) for f in DEPS},bootstrap_repetitions=B,bootstrap_seed=SEED,completed_predicate='Canonical status completed AND parsed answer non-null AND not truncated; missing families remain in ratio-influence denominator.',primary='Full frozen2400Opus; all-request, usable, missing-response bounds, iid and family sandwich SE, whole-family and class-stratified bootstrap. Paired240raw and calibrated diagnostics are reported separately and never substituted for this primary screen.',hold='Require all8namedjobs settled and collected before reading any result file. Exact metadata, unique IDs, disjoint partitions and paired identity required. No interim analysis, score-based stopping or replacement.',advancement_rule=read(p/'plan.json')['fixed_decision_rule'],numerical_screen='Primary all-request and usable accuracies AND both missing-response bounds all in[.79,.81] without rounding, all results present, no infrastructure-unscored rows. Source validity remains independently reviewed; no automatic qualification. Paired reference reversal or material unmodeled completion requires coordinator review.',current_scope='Preserve full frozen2400/240raw; uniformly apply current shared entry/oracle predicates to both provider outcomes and report IDs/reasons and supplemental scores. No silent relabeling or membership change.',paired_estimands='Exact-question Opus/Astra all-request difference, usable ratio difference, completion difference; resample entire shared families jointly with replacement, retaining zero-completion families. Report transition tables and raw cohort statistics. Intentional family enrichment means these are conditional diagnostic comparisons, not unbiased population accuracy.',covariance='Both references: raw plus coarse and exact joint-centered family-equal symmetric pair correlation, full-family bootstrap conditional on fitted means. Report repeatedLun, mixed and differentnonLun, support by unordered recipe pair.43Lunpair families identify only nested recipe pairs; san-involving repeatedLun remains unobserved. Coarse/fine differences and bootstrap limits show sensitivity; do not choose estimator to pass.',cost='Raw paid cost and token distributions plus prespecified coarse recipe×Lun/nonLun×voice and full42joint-cell calibrated means to the frozen2400 proportions. Entire-family multiplier bootstrap with refitted within-cell ratios; report invalid empty-cell replicates and unknown excluded-cell mass, and label conditional/unidentified extrapolation. No class-raked tiny-sample cost claim. Multiply by prospective4800 only as scenario, not funding authorization.',precision='Report both iid and family sandwichSE for both providers. Finalqualification, if later approved, keeps bothSE<.01 for bothreferences and fixedmembership/N decided before finalanswers. This developmentpanel is not required to pass finalSEgate.',exposure='All671developmentfamilies reused. Legacy6687analysis inspected all dictionaryfamilies including later testreserve. Current exacttuple novelty and newcampaignfamilyseparation are not never-exposed-root claims.',selection_caveats=read(p/'astra-subset/plan.json')['representativeness'],benchmark_ready=False,final_membership_approved=False,paid_calls=0)
 atomic_json(dest,decl);print(json.dumps(dict(path=str(dest),sha256=sha(dest),analyzer_sha256=sha(Path(__file__))),indent=2))

def verify_settled(state,decl):
 for e in decl['expected_jobs']:
  j=state.get('jobs',{}).get(e['id'])
  if not j or not j.get('settled') or not j.get('collected_at'):raise ValueError('All8jobs must settle and collect before any result reads: '+e['id'])
  if any(j.get(k)!=e[k] for k in ['n','provider','tasks_digest']) or j.get('phase')!='confirm_64k':raise ValueError('Registered job/protocol differs: '+e['id'])

def verify_results(chunks,results):
 if len(chunks)!=8 or len(results)!=8:raise ValueError('All8result chunks required')
 out=[]
 for ts,rr in zip(chunks,results):
  mapping={t['id']:t for t in ts};rm={r['task']['id']:r for r in rr}
  if len(rr)!=len(ts) or len(rm)!=len(rr) or set(rm)!=set(mapping):raise ValueError('Missing, duplicate or wrong result membership')
  if any(r['task']!=mapping[r['task']['id']] for r in rr):raise ValueError('Result task metadata changed')
  out.append([rm[t['id']] for t in ts])
 return sum(out[:6],[]),sum(out[6:],[])

def family_weights(rows,repetitions=B):
 fs=sorted({r['task']['campaign']['root_family'] for r in rows});idx={f:i for i,f in enumerate(fs)}
 return fs,idx,np.random.default_rng(SEED).multinomial(len(fs),[1/len(fs)]*len(fs),repetitions)

def interval(x):
 x=np.asarray(x);good=x[np.isfinite(x)]
 return dict(valid_replicates=len(good),invalid_replicates=len(x)-len(good),standard_error=float(np.std(good,ddof=1)) if len(good)>1 else None,percentile95=np.quantile(good,[.025,.975]).tolist() if len(good) else None)

def paired(opus,astra,repetitions=B):
 if not opus or len(opus)!=len(astra) or any(a['task']!=b['task'] for a,b in zip(opus,astra)):raise ValueError('Invalid exact pairs')
 fs,idx,w=family_weights(opus,repetitions);x=np.zeros((len(fs),7));trans=Counter()
 for a,b in zip(opus,astra):
  f=idx[a['task']['campaign']['root_family']];ca,cb=completed(a),completed(b);ya,yb=a['is_correct'] is True,b['is_correct'] is True
  x[f]+=np.array([1,ya,yb,ca,cb,ca and ya,cb and yb],dtype=float);trans[f'{int(ya)}->{int(yb)}']+=1
 s=x.sum(0);draw=w@x
 with np.errstate(divide='ignore',invalid='ignore'):
  differences={'recorded_all_accuracy':(s[2]-s[1])/s[0],'completion':(s[4]-s[3])/s[0],'usable_accuracy':s[6]/s[4]-s[5]/s[3] if s[3]*s[4] else None}
  boot={'recorded_all_accuracy':(draw[:,2]-draw[:,1])/draw[:,0],'completion':(draw[:,4]-draw[:,3])/draw[:,0],'usable_accuracy':draw[:,6]/draw[:,4]-draw[:,5]/draw[:,3]}
 return dict(n=len(opus),families=len(fs),difference_direction='Astra minus Opus',differences=differences,whole_family_bootstrap={k:interval(v) for k,v in boot.items()},transitions_opus_to_astra=dict(trans),opus=metric(opus),astra=metric(astra),conditional_diagnostic_only=True)

def covariance(rows):
 # Dependence helper uses canonical completion through immutable vp_5d_metrics.
 rr=[dict(r,_panel='08') for r in rows]
 if not rr or not any(completed(r) for r in rr):return dict(reason='No usable answers for ratio influence')
 report=dependence(rr);support=defaultdict(Counter);families=defaultdict(list)
 for r in rows:families[r['task']['campaign']['root_family']].append(r)
 for f,rs in families.items():
  for i,a in enumerate(rs):
   for b in rs[i+1:]:
    if a['task']['morphology']['lakara']==b['task']['morphology']['lakara']=='Lun':support['|'.join(sorted([a['task']['derivation']['recipe_id'],b['task']['derivation']['recipe_id']]))][f]+=1
 report['repeated_Lun_recipe_support']={k:dict(pairs=sum(c.values()),families=len(c)) for k,c in support.items()}
 return report

def costs(rows,provider,target,repetitions=B):
 if not rows:return dict(reason='No retained rows')
 available=[];missing=[]
 for r in rows:
  try:cost(r,provider);usage(r,provider);available.append(r)
  except (KeyError,TypeError):missing.append(r['task']['id'])
 if not available:return dict(missing_usage_ids=missing,reason='No usage')
 fs,idx,w=family_weights(available,repetitions);n=len(available);estimates={}
 for fine in [False,True]:
  def key(t):
   c=cell(t).split('|');return '|'.join(c if fine else [c[0],'Lun' if c[1]=='Lun' else 'other',c[2]])
  groups=defaultdict(list);tc=Counter()
  for r in available:groups[key(r['task'])].append(r)
  for c,q in target.items():
   a=c.split('|');tc['|'.join(a if fine else [a[0],'Lun' if a[1]=='Lun' else 'other',a[2]])]+=q
  mean=completion=0.;draw=np.zeros(repetitions);complete_draw=np.zeros(repetitions);supported=sum(q for c,q in tc.items() if c in groups);cells={}
  for c,rs in groups.items():
   if c not in tc:continue
   v=np.zeros((len(fs),3))
   for r in rs:v[idx[r['task']['campaign']['root_family']]]+=np.array([1,cost(r,provider),int(completed(r))])
   s=v.sum(0);b=w@v;weight=tc[c]/sum(tc.values());mean+=weight*s[1]/s[0];completion+=weight*s[2]/s[0]
   with np.errstate(divide='ignore',invalid='ignore'):draw+=weight*b[:,1]/b[:,0];complete_draw+=weight*b[:,2]/b[:,0]
   cells[c]=dict(sample_n=len(rs),families=len({r['task']['campaign']['root_family'] for r in rs}),target_n=tc[c],mean_cost=s[1]/s[0],completion=s[2]/s[0])
  allsupport=supported==sum(tc.values())
  estimates['joint' if fine else 'coarse']=dict(all_target_cells_supported=allsupport,unsupported_target_mass=1-supported/sum(tc.values()),calibrated_cost_mean=mean if allsupport else None,calibrated_completion=completion if allsupport else None,cost_whole_family_bootstrap=interval(draw) if allsupport else None,completion_whole_family_bootstrap=interval(complete_draw) if allsupport else None,prospective4800_cost=4800*mean if allsupport else None,cells=cells,caveat='Conditional standardization only. Deterministic family enrichment, zero-probability/small cells and changed root composition are not corrected by these marginal weights. Empty-cell bootstrap replicates are counted, never filled or used to switch estimators.')
 return dict(n=n,missing_usage_ids=missing,total_usage_cost=sum(cost(r,provider) for r in available),raw_cost_distribution=distribution([cost(r,provider) for r in available]),input_token_distribution=distribution([usage(r,provider)['input_tokens'] for r in available]),output_token_distribution=distribution([usage(r,provider)['output_tokens'] for r in available]),outputs_at_or_above_cap=sum(usage(r,provider)['output_tokens']>=65536 for r in available),standardized=estimates)

def analyze(p):
 p=p.resolve();decl=read(p/'analysis-predeclaration.json')
 # This guard precedes opening any result. It is intentionally independent of provider outcome.
 state=read(ROOT/'benchmarks/iterative-goal-20261006/ledger.json');verify_settled(state,decl)
 for f,d in decl['frozen_files'].items():
  if sha(p/f)!=d:raise ValueError('Frozen input changed: '+f)
 for f,d in decl['analysis_dependencies'].items():
  if sha(ROOT/f)!=d:raise ValueError('Frozen analysis dependency changed: '+f)
 ts,ch,sub,ach=verify_panel(p);paths=[ROOT/'benchmarks/iterative-goal-20261006/jobs'/j/'results.json' for j,_,_ in JOBS]
 if not all(x.is_file() for x in paths):raise ValueError('All8complete result files required')
 op,ast=verify_results(ch+ach,[read(x) for x in paths]);om={r['task']['id']:r for r in op};paired_op=[om[t['id']] for t in sub];groups=read(p/'analysis-exposure-groups.json');es=entries_by_code();exclusions=[];keep=set()
 for t in ts:
  issue=entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)
  if issue:exclusions.append(dict(id=t['id'],reason=issue))
  else:keep.add(t['id'])
 out=dict(created_at=now(),analysis_predeclaration_sha256=sha(p/'analysis-predeclaration.json'),all8settled_and_collected=True,result_sources=[dict(path=str(x),sha256=sha(x)) for x in paths],recorded_costs={j:state['jobs'][j].get('actual_cost_upper_micro',0)/1e6 for j,_,_ in JOBS},current_scope_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),scope_exclusions=exclusions,original_results_changed=False,benchmark_ready=False)
 for label,ids in [('raw',{t['id'] for t in ts}),('current_scope_supplement',keep)]:
  oo=[r for r in op if r['task']['id'] in ids];aa=[r for r in ast if r['task']['id'] in ids];po=[r for r in paired_op if r['task']['id'] in ids];target=Counter(cell(r['task']) for r in oo)
  if not oo or not aa:out[label]=dict(reason='Empty retained panel',numerical_screen=False);continue
  out[label]=dict(opus_primary=describe([r['task'] for r in oo],oo,groups,decl),paired_opus=describe([r['task'] for r in po],po,groups,decl),paired_astra=describe([r['task'] for r in aa],aa,groups,decl),paired_difference=paired(po,aa),dependence={name:covariance(rows) for name,rows in [('opus_primary',oo),('opus_paired',po),('astra_paired',aa)]},cost={name:costs(rows,provider,target) for name,provider,rows in [('opus_primary','Anthropic',oo),('opus_paired','Anthropic',po),('astra_paired','OpenAI',aa)]})
 out['advancement']=dict(raw_opus_numerical_screen=out['raw']['opus_primary']['numerical_screen'],current_scope_opus_numerical_screen=out['current_scope_supplement'].get('opus_primary',{}).get('numerical_screen',False),validity_review_required=True,paired_reference_order_review_required=True,authorized=False)
 out['limitations']=['Adaptive grammar mix based on prior development outcomes; intervals omit that selection uncertainty.','Same-recipe exposure groups are observational and composition-confounded; all lexical families historically exposed.','Paired subset intentionally enriches43Lunpair families and has no sanLunpair support; covariance transport to finalallocation and largerloads remains uncertain.','65536is a prospective common ceiling, not a relabeling of16k/128k records.','No finalN/membership or funding is authorized by these diagnostics.']
 dest=p/'aggregate-analysis.json'
 if dest.exists():raise ValueError('Preserve existing aggregate; new supplemental version required')
 atomic_json(dest,out);print(json.dumps(dict(output=str(dest),advancement=out['advancement']),indent=2))

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','analyze']);parser.add_argument('directory',type=Path);args=parser.parse_args()
 if args.command=='prepare':prepare(args.directory)
 else:analyze(args.directory)
