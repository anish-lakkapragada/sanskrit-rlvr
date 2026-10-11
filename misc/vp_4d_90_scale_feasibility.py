#!/usr/bin/env python3
"""Offline dictionary census and proposed allocations. Never reads held-out outcomes."""
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
import hashlib, json, math, statistics, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import HISTORY, load_entries, family, name, identity, sha, now, write
from misc.vp_4d_pilot04 import local_issue, LOCAL_CODES, LAS, COORDS
from misc.vp_4d_pilot05 import short
from misc.vp_cartesian_task import make_task, entry_scope_issue, oracle_issue, validate_task
OUT=ROOT/'benchmarks/parallel-search-20261007/four_d-90'
SEED='scale-feasibility-20261007'
CELLS=['short_adanta_non_aorist','other_adanta_aorist','broad_non_curadi']
WEIGHTS=[.52,.08,.40]
RATES=[84/104,12/16,79/80]

def key(x):return hashlib.sha256((SEED+':'+str(x)).encode()).hexdigest()
def stat(rows):
 f=Counter(r['family'] for r in rows)
 return dict(tuples=len(rows),families=len(f),family_capacity=dict(sorted(f.items())),capacity_at_family_cap={str(k):sum(min(k,v) for v in f.values()) for k in [1,3,5,8,10,20,40,60,81]},by_tense=dict(Counter(r['lakara'] for r in rows)),by_class=dict(Counter(r['gana'] for r in rows)))

def main():
 es={e.code:e for e in load_entries()};split_path=HISTORY/'family-split.json';split_blob=json.load(open(split_path));assign=split_blob['families']
 reserve_path=ROOT/'benchmarks/iterative-goal-20261006/test-family-reserve.json';reserve=json.load(open(reserve_path));initial=set(reserve['initial_release_families'])
 inputs=sorted((ROOT/'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json'))
 seen_tuples=set();job_families=set();job_test_families=set();dev_family_mismatch=[]
 for path in inputs:
  for outer in json.load(open(path)):
   for t in outer.get('forms',[outer]):
    if 'dhatu' not in t:continue
    f=t.get('campaign',{}).get('root_family') or (t['dhatu']['aupadeshika']+'|'+t['dhatu']['gana'])
    job_families.add(f)
    if f in assign and assign[f]['split']=='test':job_test_families.add(f)
    if set(t.get('morphology',{}))==set(COORDS) and not t.get('derivation',{}).get('sanadi') and not t.get('derivation',{}).get('prefixes'):seen_tuples.add(identity(t))
 legacy_paths=[ROOT/'benchmarks/full-tasks.json',*sorted(HISTORY.glob('discovery-??.json'))]
 legacy_families=set()
 for path in legacy_paths:
  for t in json.load(open(path)):
   if 'dhatu' not in t:continue
   legacy_families.add(t['dhatu']['aupadeshika']+'|'+t['dhatu']['gana'])
   if set(t.get('morphology',{}))==set(COORDS):seen_tuples.add(identity(t))
 rows=[];extras=[];seen=set();reject=Counter();entry_reject=[]
 for e in es.values():
  g=name(e.dhatu.gana);f=family(e);spl=assign[f]['split'];adanta=g=='Curadi' and e.dhatu.aupadeshika.endswith('a')
  issue=entry_scope_issue(e) or ('prior local source hold' if e.code in LOCAL_CODES else None)
  if issue:entry_reject.append(dict(code=e.code,family=f,split=spl,reason=issue));continue
  if g=='Curadi' and not adanta:continue
  for la in LAS:
   for pu in ['Prathama','Madhyama','Uttama']:
    for va in ['Eka','Dvi','Bahu']:
     m=dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va)
     t=make_task(e,spl,m)
     if not t:reject['no_forms']+=1;continue
     issue=oracle_issue(t) or ('prior local tuple source hold' if local_issue(t) else None)
     if issue:reject[str(issue)]+=1;continue
     ident=identity(t)
     if ident in seen:continue
     seen.add(ident)
     cell='broad_non_curadi' if not adanta else 'short_adanta_non_aorist' if short(e) and la!='Lun' else 'other_adanta_aorist' if not short(e) and la=='Lun' else 'short_adanta_aorist' if short(e) else 'other_adanta_non_aorist'
     r=dict(id=t['id'],code=e.code,family=f,split=spl,gana=g,cell=cell,fresh_tuple=ident not in seen_tuples,family_in_registered_jobs=f in job_families,family_in_legacy=f in legacy_families,initial_test_release=f in initial,**m)
     (rows if cell in CELLS else extras).append(r)
 census={}
 for spl in ['development','test','rl_train']:
  census[spl]={c:stat([r for r in rows if r['split']==spl and r['cell']==c]) for c in CELLS}
 census['test_fresh_tuples']={c:stat([r for r in rows if r['split']=='test' and r['cell']==c and r['fresh_tuple']]) for c in CELLS}
 census['test_no_registered_family']={c:stat([r for r in rows if r['split']=='test' and r['cell']==c and not r['family_in_registered_jobs'] and r['fresh_tuple']]) for c in CELLS}
 for label,flag in [('test_initial',True),('test_future',False)]:census[label]={c:stat([r for r in rows if r['split']=='test' and r['cell']==c and r['initial_test_release']==flag and r['fresh_tuple']]) for c in CELLS}
 supplemental={spl:{c:stat([r for r in extras if r['split']==spl and r['cell']==c]) for c in ['short_adanta_aorist','other_adanta_non_aorist']} for spl in ['development','test','rl_train']}
 result_rows=[]
 for i in range(1,6):result_rows+=json.load(open(ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-fast-simple4d-{i:02d}/results.json'))
 family_rates={};dependence={}
 for c in CELLS:
  fs=defaultdict(list)
  for r in result_rows:
   if r['task']['campaign']['sampling_cell']['label']==c:fs[r['task']['campaign']['root_family']].append(int(r['is_correct']))
  rates=[sum(v)/len(v) for v in fs.values()];family_rates[c]=rates
  s2=statistics.variance(rates);cellp=sum(map(sum,fs.values()))/sum(map(len,fs.values()));dep=dict(families=len(fs),family_mean_variance=s2,family_mean_se=math.sqrt(s2/len(fs)),family_rates={f:sum(v)/len(v) for f,v in fs.items()})
  if len(set(map(len,fs.values())))==1 and len(next(iter(fs.values())))>1:
   m=len(next(iter(fs.values())));msb=m*s2;msw=sum(sum((y-sum(v)/len(v))**2 for y in v) for v in fs.values())/(len(fs)*(m-1));rho=(msb-msw)/(msb+(m-1)*msw)
   dep.update(balanced_anova_intraclass_correlation=rho,within_family_variance=msw,between_family_variance_estimate=max(0,(msb-msw)/m))
  dependence[c]=dep
 candidates={};selected_metadata={}
 for n in [500,1000,1250,1800]:
  target=dict(zip(CELLS,[round(n*w) for w in WEIGHTS]));selected=[]
  for c,num in target.items():
   eligible=[r for r in rows if r['split']=='test' and r['cell']==c and r['fresh_tuple'] and not r['family_in_registered_jobs']]
   fc=Counter();fl=Counter();la=Counter();pc=Counter();vc=Counter();gc=Counter()
   for _ in range(num):
    if not eligible:break
    r=min(eligible,key=lambda r:(fc[r['family']],fl[(r['family'],r['lakara'])],la[r['lakara']],gc[r['gana']],pc[r['purusha']]+vc[r['vacana']],key(r['id'])))
    selected.append(r);eligible.remove(r);fc[r['family']]+=1;fl[(r['family'],r['lakara'])]+=1;la[r['lakara']]+=1;pc[r['purusha']]+=1;vc[r['vacana']]+=1;gc[r['gana']]+=1
  assert len(selected)==n,(n,len(selected));assert len({r['id'] for r in selected})==n
  for r in selected:
   t=make_task(es[r['code']],'test',{k:r[k] for k in COORDS});validate_task(t,es[r['code']],'test');assert not oracle_issue(t) and not local_issue(t) and identity(t) not in seen_tuples
  per_cell={c:stat([r for r in selected if r['cell']==c]) for c in CELLS};p=sum(w*q for w,q in zip(WEIGHTS,RATES))
  family_projection_var=sum(w*w*statistics.variance(family_rates[c])/per_cell[c]['families'] for w,c in zip(WEIGHTS,CELLS))
  tau=dependence[CELLS[0]]['between_family_variance_estimate'];family_floor=.52*math.sqrt(tau/per_cell[CELLS[0]]['families'])
  candidates[str(n)]=dict(n=n,cell_quotas=target,cells=per_cell,all_tense_counts=dict(Counter(r['lakara'] for r in selected)),all_class_counts=dict(Counter(r['gana'] for r in selected)),family_count=len({r['family'] for r in selected}),max_family_load=max(Counter(r['family'] for r in selected).values()),conditional_mean_forecast=p,iid_se_at_forecast=math.sqrt(p*(1-p)/n),fixed_stratum_bernoulli_se=math.sqrt(sum(w*q*(1-q) for w,q in zip(WEIGHTS,RATES))/n),family_mean_transport_se=math.sqrt(family_projection_var),short_cell_random_effect_floor=family_floor,task_ids_path=f'scale-candidate-{n}-metadata.json',no_paid_evaluation=True)
  selected_metadata[n]=selected
 # Precision requirements for an unknown Bernoulli population, without cluster correction.
 iid_requirements={str(p):int(Decimal(str(p))*(1-Decimal(str(p)))/Decimal('.0001'))+1 for p in [.8,.85,.875,.89,.9,.5]}
 family_required=math.ceil(.52**2*dependence[CELLS[0]]['between_family_variance_estimate']/.01**2)
 dependencies=[split_path,reserve_path,ROOT/'misc/vp_cartesian_task.py',ROOT/'misc/vp_4d_pilot04.py',ROOT/'misc/vp_4d_pilot05.py',ROOT/'benchmarks/parallel-search-20261006/oracle-policy-21.json',OUT/'tasks.json',Path(__file__)]
 obj=dict(created_at=now(),scope='Offline fresh dictionary census; Kartari exact4D; no held-out model outcomes accessed; allocations are proposals, not benchmark freezes.',census=census,supplemental=supplemental,entry_holds=entry_reject,tuple_rejections=dict(reject),exposure=dict(registered_input_files=len(inputs),registered_test_families=sorted(job_test_families),legacy_family_count=len(legacy_families),split_prior_exposure=split_blob['prior_exposure'],warning='Fresh relative to registered job input families and exact tuples; legacy analysis inspected families before master split, so these are not never-seen lexical families.'),development_rates=dict(zip(CELLS,RATES)),dependence=dependence,candidate_allocations=candidates,iid_n_for_strict_se_below_one_pp=iid_requirements,short_families_needed_for_own_weighted_random_effect_below_one_pp=family_required,dependencies=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in dependencies],inputs=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in inputs+legacy_paths],all_generated_gold_sets_retained_by_oracle=True,shared_files_changed=False,paid_calls=0,benchmark_ready=False)
 write(OUT/'scale-feasibility.json',obj)
 for n,sel in selected_metadata.items():write(OUT/f'scale-candidate-{n}-metadata.json',sel)
 print(json.dumps({'census':{s:{c:(d['families'],d['tuples']) for c,d in v.items()} for s,v in census.items()},'registered_test_families':len(job_test_families),'candidates':{n:{k:v[k] for k in ['family_count','max_family_load','conditional_mean_forecast','iid_se_at_forecast','fixed_stratum_bernoulli_se','family_mean_transport_se','short_cell_random_effect_floor']} for n,v in candidates.items()},'dependence':dependence,'iid_n':iid_requirements,'family_needed':family_required},indent=2))
if __name__=='__main__':main()
