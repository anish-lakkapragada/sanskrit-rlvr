#!/usr/bin/env python3
"""Offline freeze of a bounded 200-question exact-4D diagnostic; no API calls."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import HISTORY, OUT as OLD, load_entries, family, name, identity, row_identity, source_rows, write, now, sha
from misc.vp_4d_pilot02 import exposure
from misc.vp_4d_pilot04 import local_issue, LOCAL_CODES, COORDS, LAS
from misc.vp_4d_pilot05 import short, PRESENT_AND_AORIST
from misc.vp_4d_pilot04_audit import CONTROLS
from misc.vp_cartesian_task import make_task, validate_task, entry_scope_issue, oracle_issue
from misc.vp_cartesian_prompt_v1 import render
sys.path.insert(0,str(OLD/'_solver_deps'));import highspy
OUT=ROOT/'benchmarks/parallel-search-20261007/four_d-90'; SEED=2026100790
CELL_N={'short_adanta_non_aorist':104,'other_adanta_aorist':16,'broad_non_curadi':80}
SHORT_Q={'Lat':12,'Lit':12,'Lut':12,'Lrt':12,'Lot':12,'Lan':11,'VidhiLin':11,'AshirLin':11,'Lrn':11}
GANA_Q={'Bhvadi':22,'Divadi':14,'Tudadi':12,'Adadi':8,'Svadi':8,'Kryadi':8,'Rudhadi':4,'Juhotyadi':2,'Tanadi':2}
def order(row,label='candidate'):
 return hashlib.sha256(f'{SEED}:{label}:{row["id"]}'.encode()).hexdigest()
def scope(t,e):return entry_scope_issue(e) or oracle_issue(t) or local_issue(t)
def main():
 assert not (OUT/'tasks.json').exists(),'Frozen artifacts cannot be replaced'
 OUT.mkdir(parents=True,exist_ok=True)
 entries={e.code:e for e in load_entries()};assign=json.load(open(HISTORY/'family-split.json'))['families']
 prior,history=exposure();registered={r['path'] for r in history}
 for p in sorted(set(OLD.glob('**/*questions*.json')) | set(OLD.glob('**/tasks.json'))):
  rel=str(p.relative_to(ROOT))
  if rel in registered:continue
  blob=json.loads(p.read_text())
  if not isinstance(blob,list):continue
  n=0
  for task in blob:
   for t in task.get('forms',[task]):
    if 'dhatu' not in t or set(t.get('morphology',{}))!=set(COORDS):continue
    if t.get('derivation',{}).get('sanadi') or t.get('derivation',{}).get('prefixes'):continue
    prior.add(identity(t));n+=1
  if n: history.append(dict(path=rel,sha256=sha(p)));registered.add(rel)
 audit_controls=[]
 for code,expected in PRESENT_AND_AORIST.items():
  for la,gold in zip(['Lat','Lun'],expected):
   t=make_task(entries[code],'source_control',dict(lakara=la,prayoga='Kartari',purusha='Prathama',vacana='Eka'))
   audit_controls.append(dict(code=code,lakara=la,expected=gold,actual=t['gold_slp1'],passed=gold in t['gold_slp1'],source='pilot-05.source-audit.json: direct adanta lexical support and explicit general-rule inference'))
 for code,la,pu,va,golds,url,level in CONTROLS:
  if not code.startswith('10.'):continue
  t=make_task(entries[code],'source_control',dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va))
  audit_controls.append(dict(code=code,lakara=la,expected=golds,actual=t['gold_slp1'],passed=set(golds)<=set(t['gold_slp1']),source_url=url,evidence_level=level))
 assert all(c['passed'] for c in audit_controls)
 rows=[];task_cache={};seen=set();excluded=Counter()
 def add(e,m,label):
  t=make_task(e,'development',m)
  if not t:excluded['no_forms']+=1;return
  issue=scope(t,e)
  if issue:excluded[str(issue)]+=1;return
  ident=identity(t)
  if ident in prior:excluded['historical_visible_tuple']+=1;return
  if ident in seen:return
  seen.add(ident);task_cache[t['id']]=t
  rows.append(dict(id=t['id'],code=e.code,family=family(e),gana=name(e.dhatu.gana),cell=label,**m))
 eligible_short=set();eligible_other=set()
 for e in entries.values():
  if assign[family(e)]['split']!='development' or entry_scope_issue(e) or e.code in LOCAL_CODES:continue
  if name(e.dhatu.gana)!='Curadi' or not e.dhatu.aupadeshika.endswith('a'):continue
  if short(e):label='short_adanta_non_aorist';lakaras=list(SHORT_Q);eligible_short.add(family(e))
  else:label='other_adanta_aorist';lakaras=['Lun']
  before=len(rows)
  for la in lakaras:
   for pu in ['Prathama','Madhyama','Uttama']:
    for va in ['Eka','Dvi','Bahu']:add(e,dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va),label)
  if not short(e) and len(rows)>before:eligible_other.add(family(e))
 assert len(eligible_short)==13 and len(eligible_other)==16,(eligible_short,eligible_other)
 # The broad controls are sampled independently of historical correctness. Reuse
 # the complete dictionary candidate catalog only as an index; every gold is regenerated.
 broad=defaultdict(list)
 for r in source_rows(entries):
  e=entries[r['code']];g=name(e.dhatu.gana)
  if r['split']!='development' or g=='Curadi' or r['prayoga']!='Kartari' or entry_scope_issue(e) or e.code in LOCAL_CODES:continue
  if row_identity(r,entries) in prior:continue
  broad[(g,r['lakara'])].append(r)
 # Seeded 50-per-class/tense candidate limits keep this a quick diagnostic;
 # no historical model outcomes enter the rank. All tiny-class rows are eligible.
 for key,candidates in sorted(broad.items()):
  for r in sorted(candidates,key=order)[:50]:add(entries[r['code']],{k:r[k] for k in COORDS},'broad_non_curadi')
 rows.sort(key=order)
 h=highspy.Highs()
 for k,v in [('output_flag',False),('threads',2),('random_seed',SEED),('time_limit',45.)]:h.setOptionValue(k,v)
 xs=[h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger) for _ in rows]
 maps={k:defaultdict(list) for k in ['cell','family','cell_lakara','cell_gana','family_lakara','purusha','vacana']}
 for r,x in zip(rows,xs):
  for k in maps:
   value=(r['cell'],r['lakara']) if k=='cell_lakara' else (r['cell'],r['gana']) if k=='cell_gana' else (r['family'],r['lakara']) if k=='family_lakara' else r[k]
   maps[k][value].append(x)
 h.addConstr(h.qsum(xs)==200)
 for c,n in CELL_N.items():h.addConstr(h.qsum(maps['cell'][c])==n)
 for f,vs in maps['family'].items():h.addConstr(h.qsum(vs)==8 if f in eligible_short else h.qsum(vs)==1 if f in eligible_other else h.qsum(vs)<=1)
 for (f,la),vs in maps['family_lakara'].items():
  if f in eligible_short:h.addConstr(h.qsum(vs)<=1)
 for (c,la),vs in maps['cell_lakara'].items():h.addConstr(h.qsum(vs)==SHORT_Q.get(la,0) if c=='short_adanta_non_aorist' else h.qsum(vs)==16 if c=='other_adanta_aorist' else h.qsum(vs)==8)
 for g,n in GANA_Q.items():h.addConstr(h.qsum(maps['cell_gana'][('broad_non_curadi',g)])==n)
 for k in ['purusha','vacana']:
  for vs in maps[k].values():h.addConstr(h.qsum(vs)>=66);h.addConstr(h.qsum(vs)<=67)
 h.minimize(h.qsum((i+1)*x for i,x in enumerate(xs)));sol=h.getSolution()
 assert sol.value_valid and str(h.getModelStatus()) in {'HighsModelStatus.kOptimal','HighsModelStatus.kTimeLimit'},str(h.getModelStatus())
 chosen=[r for r,x in zip(rows,xs) if sol.col_value[int(x)]>.5];assert len(chosen)==200
 tasks=[]
 for r in chosen:
  e=entries[r['code']];t=make_task(e,'development',{k:r[k] for k in COORDS});validate_task(t,e,'development');assert not scope(t,e) and identity(t) not in prior
  assert t['gold_slp1']==task_cache[t['id']]['gold_slp1'] and t['gold_devanagari']==task_cache[t['id']]['gold_devanagari']
  t['campaign'].update(panel='4d-90-pilot01',seed=SEED,sampling_cell={'label':r['cell']},selection={'method':'Fixed grammar predicates, include every eligible hard-predicate family, seeded fresh tuple allocation. No question selected by its own outcome.'})
  tasks.append(t)
 tasks.sort(key=lambda t:order(t,'display'))
 assert len({identity(t) for t in tasks})==len({render(t) for t in tasks})==200
 counts=Counter(t['campaign']['root_family'] for t in tasks);assert len(counts)==109 and max(counts.values())==8
 distribution={k:dict(Counter(t['morphology'][k] for t in tasks)) for k in COORDS};distribution['gana']=dict(Counter(t['dhatu']['gana'] for t in tasks))
 source_paths=[OLD/'pilot-04.source-audit.json',OLD/'pilot-05.source-audit.json',OLD/'pilot-05.disagreement-review.json',OLD/'pilot-04.mixture-frontier-r3-policy13.json']
 deps=[ROOT/'misc/vp_cartesian_task.py',ROOT/'misc/vp_cartesian_prompt_v1.py',ROOT/'misc/vp_cartesian_prompt_v2.py',ROOT/'misc/vp_cartesian_prompt_v3.py',ROOT/'misc/vp_compositional.py',ROOT/'misc/vp_campaign_candidates.py',ROOT/'finetune/prompts.py',ROOT/'prompts/v2/vp_task_eval.txt',HISTORY/'family-split.json',ROOT/'benchmarks/parallel-search-20261006/oracle-policy-21.json',Path(__file__),ROOT/'misc/vp_4d_pilot.py',ROOT/'misc/vp_4d_pilot02.py',ROOT/'misc/vp_4d_pilot04.py',ROOT/'misc/vp_4d_pilot05.py',ROOT/'misc/vp_4d_pilot04_audit.py',*source_paths]
 plan=dict(created_at=now(),panel='4d-90-pilot01',purpose='One bounded development diagnostic for a single simple exact4D benchmark below90%; not a final benchmark or precise population estimate.',n=200,seed=SEED,scope='Dictionary dhatu plus exactly lakara/prayoga/purusha/vacana; no added derivation, prefixes or independently selected pada. All VP accepted gold alternatives preserved.',protocol=dict(provider='Anthropic',model='claude-opus-5-5',effort='xhigh',max_output_tokens=65536,prompt_version='cartesian-4d-v1'),cells=[dict(label='short_adanta_non_aorist',n=104,families=13,predicate='Curadi citation ends in literal non-nasal a; remove that a and require the penultimate remaining phoneme in SLP1 aiufx, followed by a consonant. Kartari, non-Lun, current shared and local source exclusions.',selection='Every eligible development family exactly8 times, each in8 distinct non-aorist tenses.'),dict(label='other_adanta_aorist',n=16,families=16,predicate='Other literal-a-final Curadi citations, Kartari Lun, current shared and local source exclusions.',selection='Every eligible development family once; the uncertain sUca aorist is excluded uniformly.'),dict(label='broad_non_curadi',n=80,families=80,predicate='Current-policy classical dictionary entries outside Curadi, Kartari; current shared and local exclusions.',selection='One task per family, all9 remaining classes, exactly8 per tense; independent seeded controls with no outcome filter.')],distribution=distribution,forecast=dict(accuracy=(104*31/39+16*10/13+80)/200,status='Conditional transport of small historical16k cells; not a measured or calibrated forecast.',cell_rates={'short_adanta_non_aorist':'31/39, 13 development families, ~8.04pp family SE','other_adanta_aorist':'10/13, exploratory post-hoc old cell; unconfirmed','broad_non_curadi':'1.0 planning assumption from recent easy probes'},assumptions=['Accuracy rates transfer across new tuples and 16k to64k; unproven.','Mixture deliberately concentrates60% in Curadi;104/200 questions use only13 families.']),predeclared_decision={'advance_exploration':'All-request AND usable accuracy below90%, with source-supported errors across at least5 families. Review refusals/truncations and gold disputes before interpretation. This only motivates larger validation.','close_this_mixture':'Accuracy>=90% or apparent difficulty explained by unresolved gold/format issues means this bounded mixture does not provide the desired signal.','no_final_qualification':'200 development tasks cannot certify top-model ordering, sub1pp sampling error, independent held-out performance or general Sanskrit coverage.'},reporting=['All-request and usable accuracy; refusals, truncations and missing-answer bounds.','iid and unstratified family-sandwich SE plus family-bootstrap interval; all cells, tense and class breakdowns.','Raw frozen results preserved; any grammatical exclusion applies uniformly by predicate to success and failure, reported additively.'],family_supply={'short_predicate':{'development':13,'test':14,'rl_train':9},'other_adanta_aorist_test_families':25,'source':'Dictionary/family-split census with current scope; no held-out model answers read.','scale_limit':'Keeping52% of a1000-question benchmark in short-adanta would place520 questions across just14 test families, averaging37.1 each. This is a serious independent-family and RL-generalization bottleneck; repeated forms do not create sub1pp independent precision.'},benchmark_ready=False)
 write(OUT/'plan.json',plan);write(OUT/'tasks.json',tasks);write(OUT/'source-controls.json',dict(created_at=now(),checks=audit_controls,all_passed=True,limits='Representative direct controls plus general-rule inference; not independent full-paradigm certification. Every disagreement requires bounded source review.',prior_source_files=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in source_paths]))
 audit=dict(created_at=now(),n=200,unique_prompts=200,unique_visible_tuples=200,all_regenerated=True,all_gold_variants_preserved=True,source_controls_passed=len(audit_controls),exact_four_coordinates=True,all_development_split=True,prior_visible_tuple_overlap=0,policy21_exclusions_in_selected=0,local_source_exclusions_in_selected=0,unique_families=len(counts),family_histogram=dict(Counter(counts.values())),max_family_load=max(counts.values()),historical_inputs=history,candidate_counts=dict(Counter(r['cell'] for r in rows)),excluded_during_generation=dict(excluded),solver_status=str(h.getModelStatus()),full_independent_grammar_certification=False,benchmark_ready=False)
 write(OUT/'audit.json',audit)
 manifest=dict(created_at=now(),panel='4d-90-pilot01',n=200,unique_families=len(counts),questions_sha256=sha(OUT/'tasks.json'),plan_sha256=sha(OUT/'plan.json'),audit_sha256=sha(OUT/'audit.json'),source_controls_sha256=sha(OUT/'source-controls.json'),dependencies=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in deps],historical_inputs=history,worker_paid_calls=0,benchmark_ready=False)
 write(OUT/'manifest.json',manifest)
 write(OUT/'experiment-request.json',dict(created_at=now(),request_id='4d-90-pilot01-opus',track='four_d',questions_path=str(OUT/'tasks.json'),questions_sha256=sha(OUT/'tasks.json'),n=200,task_type='cartesian_4d',prompt_version='cartesian-4d-v1',provider='Anthropic',model='claude-opus-5-5',effort='xhigh',max_output_tokens=65536,phase='explore',split='development',purpose=plan['purpose'],audit_paths=[str(OUT/f) for f in ['plan.json','manifest.json','audit.json','source-controls.json']],estimate={'maximum_reservation_usd':200*(1500*2/1e6+65536*10/1e6),'input_token_assumption':1500,'worker_paid_calls':0},benchmark_ready=False))
 print(json.dumps({'tasks_sha256':manifest['questions_sha256'],'n':200,'families':len(counts),'distribution':distribution,'candidate_counts':audit['candidate_counts'],'controls':len(audit_controls),'forecast':plan['forecast']['accuracy']},indent=2))
if __name__=='__main__':main()
