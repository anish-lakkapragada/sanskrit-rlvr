#!/usr/bin/env python3
"""Freeze180fresh4Dgrammar-mechanism tasks. Offline, no provider calls."""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,HISTORY,write,now,sha,load_entries,name,family,source_rows,row_identity,identity,matches,CELLS
from misc.vp_4d_pilot02 import exposure,metadata_issue
from misc.vp_4d_search03 import status,RUN_ID,lexical_base
from misc.vp_cartesian_task import make_task,validate_task,entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v1 import render
from vidyut.prakriya import Vyakarana
sys.path.insert(0,str(OUT/'_solver_deps'));import highspy
SEED=2026100703
COORDS=['lakara','prayoga','purusha','vacana']
POSITIVE={'6.4.120','6.4.121','6.4.122','6.4.125'}
SPECIAL={f'7.2.{i}' for i in [36,37,38,44,45,48,57,59,60,70]}
CELLS03=[
 {'label':'same_gana_marker_contrast','n':60,'lakaras':['Lat','Lit','Lut','Lrt','Lot','Lan','VidhiLin','AshirLin','Lun','Lrn'],'prayogas':['Kartari'],'exclude_ganas':['Curadi'],'exclude_rules':['6.4.123'],'family_cap':1,'lakara_quotas':{x:6 for x in ['Lat','Lit','Lut','Lrt','Lot','Lan','VidhiLin','AshirLin','Lun','Lrn']},'subtype_quotas':{'accent_contrast':15,'anubandha_contrast':45},'max_gana_count':56},
 {'label':'weak_perfect_alternation','n':60,'lakaras':['Lit'],'prayogas':['Kartari'],'exclude_ganas':['Curadi'],'exclude_rules':['6.4.123'],'family_cap':2,'require_rules_any':sorted(POSITIVE|{'6.4.126'}),'subtype_quotas':{'positive_e_or_optional_e':30,'prohibition':30},'max_gana_count':40,'minimum_families':45},
 {'label':'special_it_nonpresent','n':60,'lakaras':['Lut','Lrt','Lrn'],'prayogas':['Kartari'],'exclude_ganas':['Curadi'],'exclude_rules':['6.4.123'],'family_cap':2,'lakara_quotas':{'Lut':24,'Lrt':18,'Lrn':18},'require_rules_any':sorted(SPECIAL),'max_gana_count':24,'minimum_families':30},
]
def sortkey(r,label):return hashlib.sha256(f'{SEED}:{label}:{r["id"]}'.encode()).hexdigest()
def marker_groups(es):
 groups=defaultdict(list);vy=Vyakarana()
 for e in es.values():
  if entry_scope_issue(e):continue
  b=lexical_base(e,vy)
  if b:groups[b,name(e.dhatu.gana)].append(e)
 out={}
 for (base,gana),xs in groups.items():
  if len({e.dhatu.aupadeshika for e in xs})<=1:continue
  for e in xs:
   deaccent=lambda x:x.replace('\\','').replace('^','')
   accent=any(x.dhatu.aupadeshika!=e.dhatu.aupadeshika and deaccent(x.dhatu.aupadeshika)==deaccent(e.dhatu.aupadeshika) for x in xs)
   out[family(e)]={'base':base,'gana':gana,'subtype':'accent_contrast' if accent else 'anubandha_contrast','counterpart_codes':[x.code for x in xs if x.dhatu.aupadeshika!=e.dhatu.aupadeshika]}
 return out

def eligible(r,c,es,groups):
 if not matches(r,c,es):return False
 return c['label']!='same_gana_marker_contrast' or r['family'] in groups

def subtype(r,c,groups):
 if c['label']=='same_gana_marker_contrast':return groups[r['family']]['subtype']
 if c['label']=='weak_perfect_alternation':return 'positive_e_or_optional_e' if set(r['rules'])&POSITIVE else 'prohibition'
 return 'special_it'

def solve(rs,c,es,groups):
 rs=sorted(rs,key=lambda r:sortkey(r,c['label']));h=highspy.Highs()
 for k,v in [('output_flag',False),('threads',2),('random_seed',SEED),('time_limit',45.)]:h.setOptionValue(k,v)
 x=[h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger) for r in rs]
 maps={k:defaultdict(list) for k in ['family','lakara','gana','purusha','vacana','subtype']}
 for r,v in zip(rs,x):
  attrs={**r,'gana':name(es[r['code']].dhatu.gana),'subtype':subtype(r,c,groups)}
  for k in maps:maps[k][attrs[k]].append(v)
 h.addConstr(h.qsum(x)==c['n'])
 ys=[]
 for vs in maps['family'].values():
  y=h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger);ys.append(y)
  h.addConstr(h.qsum(vs)<=c['family_cap']*y);h.addConstr(h.qsum(vs)>=y)
 if c.get('minimum_families'):h.addConstr(h.qsum(ys)>=c['minimum_families'])
 for field in ['purusha','vacana']:
  for vs in maps[field].values():h.addConstr(h.qsum(vs)==c['n']//3)
 for vs in maps['gana'].values():h.addConstr(h.qsum(vs)<=c['max_gana_count'])
 for field in ['lakara','subtype']:
  q=c.get(field+'_quotas')
  if q:
   assert set(q)<=set(maps[field]),(c['label'],field,set(q)-set(maps[field]))
   for k,vs in maps[field].items():h.addConstr(h.qsum(vs)==q.get(k,0))
 h.minimize(h.qsum((i+1)*v for i,v in enumerate(x)));sol=h.getSolution()
 assert sol.value_valid,(c['label'],str(h.getModelStatus()),len(rs))
 chosen=[r for r,v in zip(rs,x) if sol.col_value[int(v)]>.5]
 assert len(chosen)==c['n'],(c['label'],str(h.getModelStatus()),len(chosen))
 return chosen,dict(solver_status=str(h.getModelStatus()),candidate_rows=len(rs),candidate_families=len(maps['family']),selected=len(chosen))

def stats(rs,es):
 fam=Counter(r['family'] for r in rs)
 return dict(tuples=len(rs),families=len(fam),capacity_at_family_caps={str(k):sum(min(k,n) for n in fam.values()) for k in [3,5,6,10]},gana=dict(Counter(name(es[r['code']].dhatu.gana) for r in rs)),lakara=dict(Counter(r['lakara'] for r in rs)))

def main():
 target=OUT/'pilot-03.questions.json'
 if target.exists():raise RuntimeError('Frozenpilot03mustnotbeoverwritten')
 assert json.load(open(OUT/'pilot-03.source-audit.json'))['all_passed']
 status('Selecting pilot03','Freezing three new mechanisms with outcome-independent grammar predicates, fresh visible tuples, explicit source controls and no test-output inspection.')
 es={e.code:e for e in load_entries()};groups=marker_groups(es);used,exposure_files=exposure()
 # Already frozen prior pilot files may not yet have evaluation copies.
 for p in [OUT/'pilot-01.questions.json',OUT/'pilot-02.questions.json']:
  used.update(identity(t) for t in json.load(open(p)))
  if not any(x['path']==str(p.relative_to(ROOT)) for x in exposure_files):exposure_files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
 seen=set();safe=[];fresh=[]
 for r in source_rows(es):
  if metadata_issue(r,es):continue
  key=row_identity(r,es)
  if key in seen:continue
  seen.add(key);safe.append(r)
  if r['split']=='development' and key not in used:fresh.append(r)
 supply={c['label']:{spl:stats([r for r in safe if r['split']==spl and eligible(r,c,es,groups)],es) for spl in ['development','test']} for c in CELLS03}
 selected={};solvers={};families_used=set()
 # Smallest mechanism first; no scores influence the ordering.
 for idx in [2,0,1]:
  c=CELLS03[idx]
  rs=[r for r in fresh if r['family'] not in families_used and eligible(r,c,es,groups)]
  chosen,solver=solve(rs,c,es,groups);selected[c['label']]=chosen;solvers[c['label']]=solver
  families_used.update(r['family'] for r in chosen)
 tasks=[]
 for c in CELLS03:
  for r in selected[c['label']]:
   e=es[r['code']];t=make_task(e,'development',{k:r[k] for k in COORDS})
   assert t and not oracle_issue(t)
   selection={'method':'fixed metadata/rule predicates and seeded constrained optimization, without model outputs','mechanism_subtype':subtype(r,c,groups)}
   if c['label']=='same_gana_marker_contrast':selection['marker_group']=groups[r['family']]
   t['campaign'].update(panel='four-d-pilot-03',seed=SEED,sampling_cell=c,selection=selection)
   validate_task(t,e,'development');assert identity(t) not in used;tasks.append(t)
 tasks.sort(key=lambda t:hashlib.sha256(f'{SEED}:order:{t["id"]}'.encode()).hexdigest())
 assert len(tasks)==len({t['id'] for t in tasks})==len({render(t) for t in tasks})==180
 assert len({identity(t) for t in tasks})==180
 fm=Counter(t['campaign']['root_family'] for t in tasks);dist={k:dict(Counter(t['morphology'][k] for t in tasks)) for k in COORDS};dist['gana']=dict(Counter(t['dhatu']['gana'] for t in tasks))
 # Supply census inspects only lexical, coordinate and trace metadata, not test gold.
 newtest=[r for r in safe if r['split']=='test' and any(eligible(r,c,es,groups) for c in CELLS03)]
 oldtest={row_identity(r,es) for r in safe if r['split']=='test' and any(matches(r,c,es) for c in CELLS)}
 newoutside=[r for r in newtest if row_identity(r,es) not in oldtest]
 write(target,tasks)
 manifest=dict(created_at=now(),run_id=RUN_ID,seed=SEED,questions_sha256=sha(target),n=len(tasks),unique_families=len(fm),max_tasks_per_family=max(fm.values()),family_size_histogram=dict(Counter(fm.values())),distribution=dist,sampling_cells=CELLS03,solvers=solvers,supply=supply,new_predicate_test_union=stats(newtest,es),new_predicate_test_outside_pilot01_rule_union=stats(newoutside,es),cell_details={c['label']:dict(n=c['n'],families=len({r['family'] for r in selected[c['label']]}),subtypes=dict(Counter(subtype(r,c,groups) for r in selected[c['label']])),ganas=dict(Counter(name(es[r['code']].dhatu.gana) for r in selected[c['label']]))) for c in CELLS03},generator_sha256=sha(__file__),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),source_audit_sha256=sha(OUT/'pilot-03.source-audit.json'),family_split_sha256=sha(HISTORY/'family-split.json'),oracle_policy_path='benchmarks/parallel-search-20261006/oracle-policy-04.json',historical_exposure_files=exposure_files,scope='Exactly dictionary dhatu plus lakara/prayoga/purusha/vacana, unchanged renderer, no added recipe/prefix/pada.',no_test_model_answers_read=True,final_membership_selected=False,benchmark_ready=False)
 write(OUT/'pilot-03.manifest.json',manifest)
 write(OUT/'pilot-03.audit.json',dict(created_at=now(),questions_sha256=sha(target),regenerated=180,unique_prompts=180,unique_visible_tuples=180,prior_exposure_overlap=0,hidden_scope_violations=0,shared_oracle_quarantine_violations=0,master_split_violations=0,source_examples_passed=35,scope_and_regeneration_passed=True,full_independent_gold_certification=False,limits=json.load(open(OUT/'pilot-03.source-audit.json'))['limits']))
 write(OUT/'experiment-request-03.json',dict(created_at=now(),track='four_d',request_id='four-d-pilot-03-opus',questions_path=str(target),questions_sha256=sha(target),n=180,unique_root_families=len(fm),task_type='cartesian_4d',prompt_version='cartesian-4d-v1',provider='Anthropic',model='claude-opus-5-5',effort='xhigh',max_output_tokens=16384,phase='explore',split='development',purpose='Test three genuinely new lexical/rule predicates: same-gana marker contrasts, weak-perfect e/loss alternation, and specialized nonpresent it. No outcome-based item selection.',suggested_sampling='Evaluate all180frozenquestions; report mechanism/subtype/family results and investigate disagreements before changing weights.',estimate=dict(maximum_reservation_usd=round(180*(1500*2/1e6+16384*10/1e6),6),worker_paid_calls=0,calculation='Conservative1500inputtokens/task. Coordinator must recompute under cumulative budget lock.'),needed_adapter_changes=[],audit_paths=[str(OUT/x) for x in ['pilot-03.audit.json','pilot-03.source-audit.json','pilot-03.manifest.json','pilot-02.disagreement-review.json']],paired_astra_recommendation=dict(submit_now=False,condition='Pair only if Opus shows source-supported error signal across multiple fresh families and oracle audit passes.',model='gpt-6-astra',effort='xhigh',max_output_tokens=16384),benchmark_ready=False))
 print(json.dumps({k:manifest[k] for k in ['questions_sha256','n','unique_families','distribution','cell_details','new_predicate_test_union','new_predicate_test_outside_pilot01_rule_union']},indent=2))
if __name__=='__main__':main()
