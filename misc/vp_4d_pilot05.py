#!/usr/bin/env python3
"""Freeze 52 fresh tuples confirming an explicit short-vowel adanta predicate."""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,HISTORY,load_entries,family,name,write,sha,now,identity,row_identity
from misc.vp_4d_pilot02 import exposure
from misc.vp_4d_pilot04 import local_issue,COORDS,LAS
from misc.vp_4d_search03 import status,RUN_ID
from misc.vp_cartesian_task import entry_scope_issue,oracle_issue,make_task,validate_task
from misc.vp_cartesian_prompt_v1 import render
sys.path.insert(0,str(OUT/'_solver_deps'));import highspy
SEED=2026100705
QUOTAS={'Lun':13,'Lit':7,**{x:4 for x in LAS if x not in {'Lun','Lit'}}}
PRESENT_AND_AORIST={
 '10.0392':('SaWayati','aSaSaWat'),'10.0393':('SvaWayati','aSaSvaWat'),
 '10.0395':('vaWayati','avavaWat'),'10.0401':('pazayati','apapazat'),
 '10.0408':('kfpayati','acakfpat'),'10.0409':('SraTayati','aSaSraTat'),
 '10.0435':('kuRayati','acukuRat'),'10.0436':('guRayati','ajuguRat'),
 '10.0441':('gfhayate','ajagfhata'),'10.0461':('vawayati','avavawat'),
 '10.0475':('suKayati','asusuKat'),'10.0477':('rasayati','ararasat'),
 '10.0488':('vasayati','avavasat')}

def short(e):
 a=e.dhatu.aupadeshika
 if name(e.dhatu.gana)!='Curadi' or not a.endswith('a'):return False
 root=a[:-1]
 return len(root)>1 and root[-2] in 'aiufx' and root[-1] not in 'aAiIuUfFxXeEoO'

def main():
 target=OUT/'pilot-05.questions.json'
 if target.exists():raise RuntimeError('Frozen pilot05 must not be overwritten')
 es={e.code:e for e in load_entries()};assign=json.load(open(HISTORY/'family-split.json'))['families']
 status('Fresh short-vowel confirmation','Preparing all 13 eligible development families, four fresh questions each, with one aorist and three distinct non-aorist tenses per family. No question is chosen by its own model result.')
 controls=[]
 for code,expected_pair in PRESENT_AND_AORIST.items():
  for la,expected in zip(['Lat','Lun'],expected_pair):
   t=make_task(es[code],'source_control',dict(lakara=la,prayoga='Kartari',purusha='Prathama',vacana='Eka'))
   controls.append(dict(code=code,lakara=la,expected_slp1=expected,gold_slp1=t['gold_slp1'],passed=expected in t['gold_slp1'],evidence='Primary adanta lexical entry plus explicit 6.4.48/7.4.2/7.4.93 inference. Present forms printed directly in the cited subgroup where documented by pilot04; not all aorists are direct printed examples.'))
 assert all(c['passed'] for c in controls),[c for c in controls if not c['passed']]
 source=dict(created_at=now(),controls=controls,all_passed=True,total=26,source_urls=['https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०','https://jainqq.org/booktext/Dhatupradip/004319','https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.2.htm','https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.93.htm'],prior_audit='pilot-04.source-audit.json',full_independent_paradigm_certification=False)
 write(OUT/'pilot-05.source-audit.json',source)
 design=dict(created_at=now(),seed=SEED,predicate='Curadi dictionary citation ending in literal non-nasal a; after removing that final a, the immediately penultimate phoneme is a/i/u/r/vocalic-l (SLP1 aiufx) and the final phoneme is a consonant. Kartari, current shared and pilot04 source exclusions.',n=52,lakara_quotas=QUOTAS,family_rule='Include every eligible development family exactly four times: one Lun and three different non-Lun lakaras. No outcome-based lexical allowlist.',origin='The phonological refinement was inspected after pilot04 outcomes; this is a fresh-tuple confirmation of that exploratory hypothesis.',confirmation_gate='At most44 correct among52 completed answers (<=84.62%) with source-supported errors in at least5 families motivates continued calibration. Any target79–81% claim still requires broader diversity, independent test families, a larger sample and strongest-reference confirmation.',limits=['All52 belong to Curadi and only13 families. This is a mechanism confirmation, not a release mixture.','Repeated development families do not create independent family confirmation. Family-level uncertainty must be reported.','All pilot04 tasks and results remain unchanged; no final test member is selected by its own failure.'],benchmark_ready=False)
 write(OUT/'pilot-05.design.json',design)
 prior,exposure_files=exposure();rows=[];seen=set()
 # Freshly derive the entire development subset from the explicit lexical predicate.
 for e in es.values():
  if assign[family(e)]['split']!='development' or not short(e) or entry_scope_issue(e):continue
  for la in LAS:
   for pu in ['Prathama','Madhyama','Uttama']:
    for va in ['Eka','Dvi','Bahu']:
     m=dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va);t=make_task(e,'development',m)
     if not t or oracle_issue(t) or local_issue(t) or identity(t) in prior or identity(t) in seen:continue
     seen.add(identity(t));rows.append(dict(id=t['id'],code=e.code,family=family(e),**m))
 rows.sort(key=lambda r:hashlib.sha256(f'{SEED}:{r["id"]}'.encode()).hexdigest())
 assert {r['code'] for r in rows}==set(PRESENT_AND_AORIST)
 h=highspy.Highs()
 for k,v in [('output_flag',False),('threads',2),('random_seed',SEED),('time_limit',45.)]:h.setOptionValue(k,v)
 xs=[h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger) for r in rows]
 maps={k:defaultdict(list) for k in ['family','lakara','purusha','vacana','family_lakara']}
 for r,x in zip(rows,xs):
  for k in maps:maps[k][(r['family'],r['lakara']) if k=='family_lakara' else r[k]].append(x)
 h.addConstr(h.qsum(xs)==52)
 for vs in maps['family'].values():h.addConstr(h.qsum(vs)==4)
 for k,vs in maps['family_lakara'].items():h.addConstr(h.qsum(vs)==1 if k[1]=='Lun' else h.qsum(vs)<=1)
 for k,vs in maps['lakara'].items():h.addConstr(h.qsum(vs)==QUOTAS[k])
 for field in ['purusha','vacana']:
  for vs in maps[field].values():h.addConstr(h.qsum(vs)>=17);h.addConstr(h.qsum(vs)<=18)
 h.minimize(h.qsum((i+1)*x for i,x in enumerate(xs)));sol=h.getSolution();assert sol.value_valid,str(h.getModelStatus())
 chosen=[r for r,x in zip(rows,xs) if sol.col_value[int(x)]>.5];assert len(chosen)==52
 tasks=[]
 for r in chosen:
  e=es[r['code']];t=make_task(e,'development',{k:r[k] for k in COORDS});validate_task(t,e,'development')
  assert not entry_scope_issue(e) and not oracle_issue(t) and not local_issue(t) and identity(t) not in prior
  t['campaign'].update(panel='four-d-pilot-05',seed=SEED,sampling_cell={'label':'short_penultimate_adanta_confirmation','n':52,'predicate':design['predicate']},selection={'method':'All eligible grammar-defined development families; seeded constrained choice of fresh tuples, no model-answer filter.'})
  tasks.append(t)
 tasks.sort(key=lambda t:hashlib.sha256(f'{SEED}:order:{t["id"]}'.encode()).hexdigest())
 assert len({render(t) for t in tasks})==len({identity(t) for t in tasks})==52
 write(target,tasks)
 fm=Counter(t['campaign']['root_family'] for t in tasks);assert len(fm)==13 and set(fm.values())=={4}
 previous_families={t['campaign']['root_family'] for t in json.load(open(OUT/'pilot-04.questions.json'))}
 dist={k:dict(Counter(t['morphology'][k] for t in tasks)) for k in COORDS}
 manifest=dict(created_at=now(),run_id=RUN_ID,n=52,questions_sha256=sha(target),unique_families=13,max_tasks_per_family=4,families_repeated_from_pilot04=len(set(fm)&previous_families),distribution=dist,gana={'Curadi':52},generator_sha256=sha(__file__),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),source_audit_sha256=sha(OUT/'pilot-05.source-audit.json'),design_sha256=sha(OUT/'pilot-05.design.json'),family_split_sha256=sha(HISTORY/'family-split.json'),candidate_count=len(rows),solver_status=str(h.getModelStatus()),historical_exposure_files=exposure_files,questions_fresh=True,family_independent_confirmation=False,final_membership_selected=False,no_held_out_model_answers=True,benchmark_ready=False)
 write(OUT/'pilot-05.manifest.json',manifest)
 write(OUT/'pilot-05.audit.json',dict(created_at=now(),questions_sha256=sha(target),n=52,all_regenerated=True,shared_and_local_scope_passed=True,exact_four_coordinates=True,no_added_derivation=True,prior_visible_tuple_overlap=0,master_split_violations=0,unique_prompts=52,source_controls_passed=26,mechanical_audit_passed=True,full_independent_gold_certification=False))
 write(OUT/'experiment-request-05.json',dict(created_at=now(),request_id='four-d-pilot-05-opus',track='four_d',questions_path=str(target),questions_sha256=sha(target),n=52,unique_root_families=13,task_type='cartesian_4d',prompt_version='cartesian-4d-v1',provider='Anthropic',model='claude-opus-5-5',effort='xhigh',max_output_tokens=16384,phase='confirm_development_mechanism',split='development',purpose='Fresh-tuple confirmation of source-defined short-penultimate adanta conditioning, all13 eligible development families, one aorist plus three other tenses per family. Not a final release mixture or independent-family confirmation.',estimate={'maximum_reservation_usd':round(52*(1500*2/1e6+16384*10/1e6),6),'worker_paid_calls':0},audit_paths=[str(OUT/x) for x in ['pilot-05.design.json','pilot-05.manifest.json','pilot-05.audit.json','pilot-05.source-audit.json','pilot-04.disagreement-review.json']],needed_adapter_changes=[],paired_astra_recommendation={'submit_now':False,'condition':'Defer until source-supported Opus confirmation and a feasible diverse mixture exist.'},benchmark_ready=False))
 print(json.dumps({k:manifest[k] for k in ['n','questions_sha256','unique_families','families_repeated_from_pilot04','distribution','candidate_count']},indent=2))

if __name__=='__main__':main()
