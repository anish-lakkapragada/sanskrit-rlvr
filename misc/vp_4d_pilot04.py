#!/usr/bin/env python3
"""Fresh dictionary-wide 4D mechanism pilot; offline and no model answers."""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,HISTORY,write,now,sha,load_entries,name,family,identity,row_identity
from misc.vp_4d_pilot02 import exposure
from misc.vp_4d_search03 import status,RUN_ID
from misc.vp_cartesian_task import make_task,validate_task,entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v1 import render
sys.path.insert(0,str(OUT/'_solver_deps'));import highspy
SEED=2026100704
COORDS=['lakara','prayoga','purusha','vacana']
LAS=['Lat','Lit','Lut','Lrt','Lot','Lan','VidhiLin','AshirLin','Lun','Lrn']
LOCAL_CODES={'10.0400','10.0490','10.0492','04.0137',*(f'02.{i:04d}' for i in range(71,76)),*(f'05.{i:04d}' for i in range(13,16))}
CELLS04=[
 {'label':'adanta_curadi','n':64,'predicate':'Dictionary Curadi citation ends in literal non-nasal a; Kartari; source and shared exclusions apply.','family_cap':3,'minimum_families':26,'lakara_quotas':{'Lun':24,**{x:5 for x in LAS if x not in {'Lit','Lun'}}},'purusha_min':20,'purusha_max':23,'vacana_min':20,'vacana_max':23},
 {'label':'nonpresent_dhvam','n':48,'predicate':'Non-Curadi Kartari Madhyama Bahu, Lit/AshirLin/Lun; trace 8.3.78 or 8.3.79; source and shared exclusions apply.','family_cap':1,'minimum_families':48,'lakara_quotas':{'Lit':24,'AshirLin':22,'Lun':2},'gana_max':36,'minimum_ganas':5},
]

def local_issue(t):
 m=t['morphology'];c=t['dhatu']['code'];rs=set(t['campaign']['trace_rule_ids'])
 return c in LOCAL_CODES or (c=='10.0412' and m['lakara']=='Lun') or (c=='04.0029' and m['lakara']=='Lit' and m['purusha']=='Madhyama' and m['vacana']=='Bahu' and '6.4.63' in rs)

def cell_for(e,m,rules):
 if name(e.dhatu.gana)=='Curadi' and e.dhatu.aupadeshika.endswith('a'):
  return 'adanta_curadi'
 if name(e.dhatu.gana)!='Curadi' and m['lakara'] in {'Lit','AshirLin','Lun'} and m['purusha']=='Madhyama' and m['vacana']=='Bahu' and set(rules)&{'8.3.78','8.3.79'}:
  return 'nonpresent_dhvam'

def catalog(es,assignments):
 rows=[];seen=set();derived=0;issues=Counter()
 for e in sorted(es.values(),key=lambda e:e.code):
  if entry_scope_issue(e) or e.code in LOCAL_CODES:continue
  adanta=name(e.dhatu.gana)=='Curadi' and e.dhatu.aupadeshika.endswith('a')
  if name(e.dhatu.gana)=='Curadi' and not adanta:continue
  ms=[dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va) for la in LAS for pu in ['Prathama','Madhyama','Uttama'] for va in ['Eka','Dvi','Bahu']] if adanta else [dict(lakara=la,prayoga='Kartari',purusha='Madhyama',vacana='Bahu') for la in ['Lit','AshirLin','Lun']]
  spl=assignments[family(e)]['split']
  for m in ms:
   t=make_task(e,spl,m);derived+=1
   if not t:issues['no_forms']+=1;continue
   if oracle_issue(t):issues['shared_oracle']+=1;continue
   if local_issue(t):issues['local_source_uncertainty']+=1;continue
   rules=t['campaign']['trace_rule_ids'];label=cell_for(e,m,rules)
   if not label:continue
   key=identity(t)
   if key in seen:continue
   seen.add(key)
   rows.append(dict(id=t['id'],family=family(e),code=e.code,split=spl,cell=label,rules=rules,**m))
 return rows,dict(dictionary_derivations=derived,unique_metadata_rows=len(rows),rejected=dict(issues),method='Regenerate all in-scope dictionary families in development/test/RL for the two fixed mechanism predicates; not restricted to the old candidate database. Only lexical identity, coordinates and rule metadata are retained. No held-out model answers are read.')

def stats(rs,es):
 fm=Counter(r['family'] for r in rs)
 return dict(tuples=len(rs),families=len(fm),at_family_caps={str(k):sum(min(k,n) for n in fm.values()) for k in [1,3,5,6,10]},gana=dict(Counter(name(es[r['code']].dhatu.gana) for r in rs)),lakara=dict(Counter(r['lakara'] for r in rs)))

def solve(rs,c,es):
 rs=sorted(rs,key=lambda r:hashlib.sha256(f'{SEED}:{c["label"]}:{r["id"]}'.encode()).hexdigest())
 h=highspy.Highs()
 for k,v in [('output_flag',False),('threads',2),('random_seed',SEED),('time_limit',45.)]:h.setOptionValue(k,v)
 xs=[h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger) for r in rs]
 maps={k:defaultdict(list) for k in ['family','lakara','purusha','vacana','gana']}
 for r,x in zip(rs,xs):
  for k in maps:maps[k][name(es[r['code']].dhatu.gana) if k=='gana' else r[k]].append(x)
 h.addConstr(h.qsum(xs)==c['n']);ys=[]
 for vs in maps['family'].values():
  y=h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger);ys.append(y)
  h.addConstr(h.qsum(vs)<=c['family_cap']*y);h.addConstr(h.qsum(vs)>=y)
 h.addConstr(h.qsum(ys)>=c['minimum_families'])
 for la,vs in maps['lakara'].items():h.addConstr(h.qsum(vs)==c['lakara_quotas'].get(la,0))
 assert set(c['lakara_quotas'])<=set(maps['lakara'])
 for field in ['purusha','vacana']:
  if field+'_min' in c:
   for vs in maps[field].values():
    h.addConstr(h.qsum(vs)>=c[field+'_min']);h.addConstr(h.qsum(vs)<=c[field+'_max'])
 if 'gana_max' in c:
  gs=[]
  for vs in maps['gana'].values():
   z=h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger);gs.append(z)
   h.addConstr(h.qsum(vs)<=c['gana_max']*z);h.addConstr(h.qsum(vs)>=z)
  h.addConstr(h.qsum(gs)>=c['minimum_ganas'])
 h.minimize(h.qsum((i+1)*x for i,x in enumerate(xs)));sol=h.getSolution()
 assert sol.value_valid,(c['label'],str(h.getModelStatus()),len(rs))
 chosen=[r for r,x in zip(rs,xs) if sol.col_value[int(x)]>.5]
 assert len(chosen)==c['n'],(c['label'],len(chosen),str(h.getModelStatus()))
 return chosen,dict(status=str(h.getModelStatus()),candidate_rows=len(rs),candidate_families=len(maps['family']))

def main():
 target=OUT/'pilot-04.questions.json'
 if target.exists():raise RuntimeError('Frozen pilot04 must not be overwritten')
 source=OUT/'pilot-04.source-audit.json';assert json.load(open(source))['all_passed']
 design=dict(created_at=now(),seed=SEED,cells=CELLS04,local_exclusion_codes=sorted(LOCAL_CODES),additional_local_predicates=['10.0412 AND Lun','04.0029 AND Lit AND Madhyama AND Bahu AND trace 6.4.63'],selection='Fixed grammar predicates, seeded constrained selection, no fresh model outcomes. Development family split only.',discovery_trigger={'adanta_curadi':'At least 8 source-supported errors across at least 6 families among 64 completed answers.','nonpresent_dhvam':'At least 6 source-supported errors across at least 6 families among 48 completed answers.'},interpretation='Exploratory interaction probe; reaching a trigger only motivates independent confirmation. A 79–81% final benchmark and sub-1pp standard error require a larger diverse independent panel. No final question selection by own failures.',benchmark_ready=False)
 write(OUT/'pilot-04.design.json',design)
 status('Regenerating new predicate universe','Generating dictionary-wide metadata for adanta Curadi and nonpresent dhvam across all master splits; retaining no held-out model outputs.')
 es={e.code:e for e in load_entries()};assign=json.load(open(HISTORY/'family-split.json'))['families']
 rows,generation=catalog(es,assign);write(OUT/'pilot-04.candidate-metadata.json',rows)
 prior,exposure_files=exposure()
 for p in [OUT/'pilot-02.questions.json',OUT/'pilot-03-r1.questions.json']:
  prior.update(identity(t) for t in json.load(open(p)))
  if not any(x['path']==str(p.relative_to(ROOT)) for x in exposure_files):exposure_files.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
 fresh=[r for r in rows if r['split']=='development' and row_identity(r,es) not in prior]
 status('Selecting pilot04','Freezing two source-audited interaction cells with fresh development tuples, family caps and less than 25% aorists.')
 tasks=[];solvers={};selected={}
 for c in CELLS04:
  chosen,solvers[c['label']]=solve([r for r in fresh if r['cell']==c['label']],c,es);selected[c['label']]=chosen
  for r in chosen:
   e=es[r['code']];t=make_task(e,'development',{k:r[k] for k in COORDS})
   assert t and not entry_scope_issue(e) and not oracle_issue(t) and not local_issue(t)
   validate_task(t,e,'development');assert identity(t) not in prior
   t['campaign'].update(panel='four-d-pilot-04',seed=SEED,sampling_cell=c,selection={'method':'Fixed grammar predicates and seeded constrained optimization; no model-answer filter.'})
   tasks.append(t)
 tasks.sort(key=lambda t:hashlib.sha256(f'{SEED}:order:{t["id"]}'.encode()).hexdigest())
 n=len(tasks);assert n==112 and len({t['id'] for t in tasks})==len({render(t) for t in tasks})==len({identity(t) for t in tasks})==n
 fm=Counter(t['campaign']['root_family'] for t in tasks)
 dist={k:dict(Counter(t['morphology'][k] for t in tasks)) for k in COORDS};dist['gana']=dict(Counter(t['dhatu']['gana'] for t in tasks))
 assert len(dist['lakara'])==10 and dist['lakara']['Lun']/n<=.25
 write(target,tasks)
 manifest=dict(created_at=now(),run_id=RUN_ID,seed=SEED,n=n,questions_sha256=sha(target),unique_families=len(fm),max_tasks_per_family=max(fm.values()),family_size_histogram=dict(Counter(fm.values())),distribution=dist,sampling_cells=CELLS04,cell_details={c['label']:stats(selected[c['label']],es) for c in CELLS04},solvers=solvers,supply={c['label']:{spl:stats([r for r in rows if r['cell']==c['label'] and r['split']==spl],es) for spl in ['development','test','rl_train']} for c in CELLS04},fresh_development_supply={c['label']:stats([r for r in fresh if r['cell']==c['label']],es) for c in CELLS04},generation=generation,generator_sha256=sha(__file__),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),source_audit_sha256=sha(source),design_sha256=sha(OUT/'pilot-04.design.json'),family_split_sha256=sha(HISTORY/'family-split.json'),historical_exposure_files=exposure_files,oracle_policy_path='benchmarks/parallel-search-20261006/oracle-policy-08.json',interpretation='64/112 Curadi and 48/112 second-person plural is intentional mechanism-probe concentration. It is not a final release mixture. Prior dhvam aorist development exposure is nearly exhausted; only two fresh aorist tuples remain, so most of that cell tests transfer to perfect/benedictive.',scope='Dictionary dhatu plus exactly lakara/prayoga/purusha/vacana, unchanged frozen renderer; no added derivation/prefix/pada.',no_test_model_answers_read=True,final_membership_selected=False,benchmark_ready=False)
 write(OUT/'pilot-04.manifest.json',manifest)
 write(OUT/'pilot-04.audit.json',dict(created_at=now(),questions_sha256=sha(target),regenerated=n,unique_prompts=n,unique_visible_tuples=n,prior_exposure_overlap=0,scope_violations=0,shared_oracle_violations=0,local_source_exclusion_violations=0,master_split_violations=0,source_examples_passed=33,mechanical_audit_passed=True,full_independent_gold_certification=False,limits=json.load(open(source))['limits']))
 write(OUT/'experiment-request-04.json',dict(created_at=now(),request_id='four-d-pilot-04-opus',track='four_d',questions_path=str(target),questions_sha256=sha(target),n=n,unique_root_families=len(fm),task_type='cartesian_4d',prompt_version='cartesian-4d-v1',provider='Anthropic',model='claude-opus-5-5',effort='xhigh',max_output_tokens=16384,phase='explore',split='development',purpose='Test adanta Curadi original-vowel conditioning and nonpresent dhvam junctions. These are exploratory grammar hypotheses, not target-level accuracy evidence.',suggested_sampling='Evaluate all 112 frozen questions; source-audit disagreements before interpreting errors. Do not promote individual failed questions into the final test.',estimate={'maximum_reservation_usd':round(n*(1500*2/1e6+16384*10/1e6),6),'worker_paid_calls':0,'calculation':'Conservative 1500 input tokens per task; coordinator recomputes under shared cumulative budget lock.'},audit_paths=[str(OUT/x) for x in ['pilot-04.audit.json','pilot-04.source-audit.json','pilot-04.manifest.json','pilot-04.design.json','search-04.ding-dhvam-variant-audit.json']],needed_adapter_changes=[],paired_astra_recommendation={'submit_now':False,'condition':'Only if Opus shows source-supported multi-family errors sufficient to justify further development.'},benchmark_ready=False))
 print(json.dumps({k:manifest[k] for k in ['n','questions_sha256','unique_families','distribution','solvers','fresh_development_supply']},indent=2))

if __name__=='__main__':main()
