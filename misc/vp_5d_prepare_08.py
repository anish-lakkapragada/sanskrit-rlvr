"""Unpaid fixed2400 development confirmation, six immutable400 transports."""
from __future__ import annotations
import json,random,time,hashlib
from collections import Counter,defaultdict
from pathlib import Path
from misc.vp_5d_prepare_04 import ROOT,OUT,atomic_json,now,sha,status
from misc.vp_5d_prepare_03 import SOURCE_ROOTS
from misc.vp_5d_prepare_05 import UNRESOLVED
from misc.vp_5d_history_18 import history
from misc.vp_5d_pilot import SPLIT
from misc.vp_5d_novelty_04 import normalized
from misc.vp_5d_release_feasibility import Dinic
from misc.vp_5d_candidate_4800_p18 import ProgressFlow,digest,cell
from misc.vp_cartesian_task import make_task,entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v3 import render
from misc.vp_goal_validate import validate
from misc import vp_campaign_candidates as old
from vidyut.prakriya import Vyakarana
N=2400;CAP=8;LCAP=5;SEED='vp-five-d-pilot07-policy17-20261007-01';EXPECTED='f04e9fa535784bd0318d6a5bef38ccf024c240c444af0f1c771221e94262f838'
P=OUT/'pilot-08';PN=[(pu,va) for pu in ['Prathama','Madhyama','Uttama'] for va in ['Eka','Dvi','Bahu']]
def read(p):return json.loads(Path(p).read_text())
def rng(tag):return random.Random(SEED+':'+tag)
def main():
 assert not P.exists(),'Preserve existing pilot07; use an explicit revised script/path if repair needed'
 assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 srcp=OUT/'pilot-08-proposal-policy19/san20_lun45_fullcoverage.quota-proposal.json';src=read(srcp);src['recipe_operations']=read(OUT/'pilot-06.revision-01.plan.json')['recipe_operations'];sp=OUT/'development-confirmation-policy19.supply.json';supply=read(sp);assert supply['adapter_sha256']==EXPECTED
 used,hf,ha=history();assignment=read(SPLIT)['families'];es={}
 for e in old.load_entries():
  if assignment[old.family(e)]['split']=='development':es.setdefault(old.family(e),e)
 sources={x:dict(path=str(p),sha256=sha(p)) for x,p in dict(generator=Path(__file__),flow=ROOT/'misc/vp_5d_candidate_4800_p18.py',history_adapter=ROOT/'misc/vp_5d_history_18.py',source_plan=srcp,supply=sp,policy=OUT.parent/'oracle-policy-19.json',adapter=ROOT/'misc/vp_cartesian_task.py',renderer=ROOT/'misc/vp_cartesian_prompt_v3.py',validator=ROOT/'misc/vp_goal_validate.py',sanskrit_helper=ROOT/'misc/vp_sanskrit_prompt_v1.py',family_split=SPLIT,dictionary=old.TSV).items()}
 p=dict(created_at=now(),track='five_d',panel='five-d-pilot-08',status='prepared_unpaid_development_confirmation',n=N,fixed_development_n=N,split='development',oracle_policy='oracle-policy-19',prompt_version='cartesian-5d-v3-sanskrit',seed=SEED,recipe_operations=src['recipe_operations'],**{k:dict(src[k]) for k in ['recipe_counts','cell_counts','gana_counts','lakara_counts']},prayoga_counts={'Kartari':2160,'Karmani':240},person_counts={x:800 for x in ['Prathama','Madhyama','Uttama']},number_counts={x:800 for x in ['Eka','Dvi','Bahu']},person_number_counts={pu+'/'+va:266 if i==j else 267 for i,pu in enumerate(['Prathama','Madhyama','Uttama']) for j,va in enumerate(['Eka','Dvi','Bahu'])},maximum_tasks_per_family=CAP,maximum_Lun_per_family=LCAP,maximum_each_other_lakara_per_family=1,source_control_codes_excluded=sorted(SOURCE_ROOTS),unresolved_prospective_exclusions=UNRESOLVED,source_hashes=sources,
 allocation_objective=['Maximize eligible development-family coverage within the exact global class/joint quotas.','Minimize repeated family-lakara assignments; only Lun may repeat.','Minimize sum of squared family loads.'],tie_breaking='Seeded sorted input edges; no task outcomes read for membership.',PN_assignment='Exact global PN margins via integral flow, restricting each exact family/cell/PN tuple to one occurrence. Prefer unique PN per family; if that matching is infeasible, allow repeated PN across distinct cells only, preserving tuple novelty.',novelty='Exclude every normalized matching grammar tuple in both campaign ledgers. The development families are all previously exposed in broader campaigns; report current-recipe exposure separately.',
 phase='confirm_64k',effort='xhigh',max_output_tokens=65536,common_provider_protocol=True,reason='Fresh confirmation of56/24/20recipe percentages,45%Lun,10%passive and input-defined class coverage lift Curadi80to145/Bhvadi1600to1535, before committing scarce OpenAI funding. Recipe proportions and class quotas were chosen from aggregate development forecasts and supply, not individual mistakes. This common65536cap is four times prior primary and over three times the observed128k-diagnostic maximum, but actual64k behavior is unmeasured. This improves development calibration and Opus dependence evidence; it is not independent-family validation. Legacy6687 analysis inspected all dictionary families; new fitting excludes reserved-family legacy records. New campaign test separation is not a globally unseen-root claim.',
 analysis='Use canonical completed predicate. Report all-request, usable, missing-response bounds, iid and family sandwich SE, whole-family bootstrap sensitivity, recipe/tense/voice/class strata, family loads, and prior same-recipe exposure groups. No reweighting, trimming or new membership based on individual errors.',
 fixed_decision_rule='Analyze advancement only after all2400 primary requests AND the preselected240 paired Astra requests settle. The Opus2400 point screen is primary; paired240 is a deliberately family-enriched diagnostic and is not a population qualification. Advance this unchanged mixture toward separately approved final evaluation only if audited all-request and usable Opus point estimates and worst/best missing-response bounds are all within79–81%, with retained-scope validity resolved. Otherwise preserve this failed screen and do not claim target attainment. This is development confirmation, not a final qualification or independent-family replication. No interim score-based stopping, provider replay or answer-based replacement.',
 transport=dict(batches=6,questions_per_batch=400,order='Each joint cell is split across six chunks with counts differing by at most one; remainder slots go to the smallest current chunks with seeded ties. All2400 membership and six chunks plus the240paired subset are fixed before answers.',second_batch_condition='Submit each400chunk only after previous settlement and the coordinator financial gate; no interim score analysis or score-based stopping.',budget_failure='If fixed2400 cannot be completed within unchanged cumulative caps, report an incomplete confirmation and no qualification. Budget subdivisions are not inferential stages.'),
 evaluation_authorization='No provider submission or paid authorization created. Parent alone counts tokens, checks shared caps/reserves, submits and settles both chunks.',precision_limit='Larger N lowers iid variance, but repeated families and multiple aorists can keep family SE above1pp. Opus covariance does not identify Astra repeated-aorist covariance.',benchmark_ready=False,final_n=None,final_membership_approved=False,paid_calls=0,no_final_answers_read=True)
 P.mkdir();atomic_json(P/'plan.json',p);atomic_json(P/'historical-inputs.json',ha)
 rr=sorted(supply['rows'],key=lambda r:r['family']);rng('flow').shuffle(rr);net=ProgressFlow();ce=[];medium=N*CAP*CAP+1;large=N*(medium+CAP*CAP)+1;rc=rng('flow-edges')
 gs=sorted(p['gana_counts']);rc.shuffle(gs)
 for g in gs:net.edge('s',('g',g),p['gana_counts'][g])
 for i,row in enumerate(rr):
  f=('f',i);net.edge(('g',row['gana']),f,1,0)
  for j in range(2,CAP+1):net.edge(('g',row['gana']),f,1,large+2*j-1)
  masks=row['eligible_person_number_masks'];las=sorted({c.split('|')[1] for c in masks});rc.shuffle(las)
  for la in las:
   net.edge(f,('fl',i,la),1,0)
   for j in range(2,(LCAP if la=='Lun' else 1)+1):net.edge(f,('fl',i,la),1,medium)
  cc=sorted(masks);rc.shuffle(cc)
  for c in cc:ce.append((i,c,net.edge(('fl',i,c.split('|')[1]),('c',c),min(CAP,masks[c].bit_count()))))
 cc=sorted(p['cell_counts']);rc.shuffle(cc)
 for c in cc:net.edge(('c',c),'t',p['cell_counts'][c])
 flow,cost=net.flow('s','t',N);assert flow==N,(flow,N);occ=defaultdict(Counter)
 for i,c,e in ce:
  if e[3]-e[1]:occ[rr[i]['family']][c]+=e[3]-e[1]
 loads=Counter(sum(x.values()) for x in occ.values());g=len(occ);lunfamilies=sum(any('|Lun|' in c for c in x) for x in occ.values());repeat=p['lakara_counts']['Lun']-lunfamilies;ssq=sum(k*k*v for k,v in loads.items());assert cost==large*(N-g)+medium*repeat+ssq-g
 objective=dict(distinct_families=g,repeated_lakara_assignments=repeat,sum_squared_family_loads=ssq,cost=cost,large_cost=large,medium_cost=medium,family_load_histogram=dict(loads),ordered_objective_proof='large>N*(medium+cap²),medium>N*cap²: coverage dominates repeats, repeats dominate squared loads; integral min-cost flow.',no_model_outcomes_used=True);atomic_json(P/'allocation-objective.json',objective)
 masks={r['family']:r['eligible_person_number_masks'] for r in rr};groups=sorted((f,c,n) for f,cs in occ.items() for c,n in cs.items());rng('pn-groups').shuffle(groups);chosen=None
 for unique in [True,False]:
  pnnet=Dinic();edges=[];pnrng=rng('pn-unique' if unique else 'pn-relaxed')
  for i,(f,c,n) in enumerate(groups):
   pnnet.edge('s',('fc',i),n);bits=list(range(9));pnrng.shuffle(bits)
   for bit in bits:
    if masks[f][c]&(1<<bit):edges.append((i,bit,pnnet.edge(('fc',i),('fp',f,bit),1)))
  for f in sorted(occ):
   for bit in range(9):pnnet.edge(('fp',f,bit),('pn',bit),1 if unique else CAP)
  for bit,(pu,va) in enumerate(PN):pnnet.edge(('pn',bit),'t',p['person_number_counts'][pu+'/'+va])
  if pnnet.flow('s','t')==N:chosen=[(i,bit) for i,bit,e in edges if e[3]-e[1]];break
 assert chosen is not None,'Fresh exact balanced PN assignment infeasible'
 v=Vyakarana();bases={f:sorted({x.text for x in v.derive(es[f].dhatu)}) for f in occ};tasks=[]
 for i,bit in chosen:
  f,c,_=groups[i];rec,la,vo=c.split('|');pu,va=PN[bit];e=es[f];t=make_task(e,'development',dict(lakara=la,prayoga=vo,purusha=pu,vacana=va),rec,p['recipe_operations'][rec],prompt_version=p['prompt_version']);assert t and not(entry_scope_issue(e) or oracle_issue(t));assert normalized(t)[0] not in used
  t['campaign'].update(panel=p['panel'],plan_sha256=sha(P/'plan.json'),oracle_policy=p['oracle_policy'],lexical_bases=bases[f],selection_reason=p['tie_breaking'],sampling_cell={'recipe_id':rec,'lakaras':[la],'prayogas':[vo]},audit_status='Policy19, input-only novel tuple, source/control holds, full shared regeneration; no independent-family claim.')
  tasks.append(t)
 bycell=defaultdict(list)
 for t in tasks:bycell[cell(t)].append(t)
 stages=[[] for _ in range(6)]
 for c,ts in sorted(bycell.items()):
  rng('stage-cell:'+c).shuffle(ts);base,rem=divmod(len(ts),6);order=list(range(6));rng('stage-tie:'+c).shuffle(order);order.sort(key=lambda i:len(stages[i]));cursor=0
  for rank,i in enumerate(order):
   q=base+int(rank<rem);stages[i].extend(ts[cursor:cursor+q]);cursor+=q
  assert cursor==len(ts)
 for i,ts in enumerate(stages):rng('stage-order:'+str(i)).shuffle(ts);assert len(ts)==400;atomic_json(P/f'chunk-{i+1:02}.tasks.json',ts)
 tasks=[t for ts in stages for t in ts];atomic_json(P/'tasks.json',tasks)
 assert len(tasks)==len({t['id'] for t in tasks})==len({normalized(t)[0] for t in tasks})==N
 for field,key in [('gana_counts',lambda t:t['dhatu']['gana']),('cell_counts',cell),('recipe_counts',lambda t:t['derivation']['recipe_id']),('lakara_counts',lambda t:t['morphology']['lakara']),('prayoga_counts',lambda t:t['morphology']['prayoga']),('person_counts',lambda t:t['morphology']['purusha']),('number_counts',lambda t:t['morphology']['vacana']),('person_number_counts',lambda t:t['morphology']['purusha']+'/'+t['morphology']['vacana'])]:assert Counter(map(key,tasks))==Counter(p[field]),field
 pairs=Counter();familyrows=defaultdict(list)
 for t in tasks:familyrows[t['campaign']['root_family']].append(t)
 for f,ts in familyrows.items():
  q=Counter(t['morphology']['lakara'] for t in ts);assert len(ts)<=CAP and q['Lun']<=LCAP and all(n<=1 for la,n in q.items() if la!='Lun')
  for i,t in enumerate(ts):
   for u in ts[i+1:]:pairs[tuple(sorted((cell(t),cell(u))))]+=1
 audit=validate(tasks,'development',allowed_families=set(occ));audit.update(tasks_sha256=sha(P/'tasks.json'),plan_sha256=sha(P/'plan.json'),policy=p['oracle_policy']);atomic_json(P/'shared-regeneration-audit.json',audit)
 histused,histfamilies,hanew=history();assert all(normalized(t)[0] not in histused for t in tasks);assert set(occ)<=set(es)
 exposures={r:{s[0]+'|'+s[1] for s in used if s[2]==tuple(ops)} for r,ops in p['recipe_operations'].items()};anyrec=set().union(*exposures.values());anyops={s[0]+'|'+s[1] for s in used if s[2]}
 exposure=dict(all_master_development_families=len(es),all_eligible_development_families=supply['eligible_families'],selected_families=g,any_historical_family_exposure=len(set(occ)&histfamilies),no_historical_family_exposure=len(set(occ)-histfamilies),prior_current_recipe_family_exposure=len(set(occ)&anyrec),no_current_recipe_family_exposure=len(set(occ)-anyrec),prior_any_added_operations_family_exposure=len(set(occ)&anyops),prior_exposed_families_by_recipe={r:len(set(occ)&fs) for r,fs in exposures.items()},question_count_with_prior_same_recipe_family_exposure=sum(t['campaign']['root_family'] in exposures[t['derivation']['recipe_id']] for t in tasks),question_count_without_prior_same_recipe_family_exposure=sum(t['campaign']['root_family'] not in exposures[t['derivation']['recipe_id']] for t in tasks),meaning='Current recipe means exact ordered operations with matching no-prefix/no-selected-pada grammar shape. A new recipe exposure still reuses the lexical family.',tuples_overlapping_history=0,historical_input_snapshot=hanew)
 atomic_json(P/'exposure-and-novelty-audit.json',exposure)
 stats=dict(created_at=now(),passed=True,n=N,exact_joint_and_class_quotas=True,exact_PN_margins=True,unique_PN_per_family=unique,objective=objective,distinct_aorist_families=lunfamilies,family_pair_correlation_multiplier=ssq/N-1,family_class_counts=dict(Counter(es[f].dhatu.gana.name for f in occ)),aorist_family_load_histogram=dict(Counter(sum(t['morphology']['lakara']=='Lun' for t in ts) for ts in familyrows.values())),unordered_within_family_cell_pair_counts=[dict(cell_a=a,cell_b=b,pairs=n) for (a,b),n in sorted(pairs.items())]);atomic_json(P/'distribution-and-family-audit.json',stats)
 with (P/'prompts.jsonl').open('w') as fp:
  for t in tasks:
   text=render(t);assert hashlib.sha256(text.encode()).hexdigest()==t['campaign']['prompt_sha256'];fp.write(json.dumps(dict(id=t['id'],prompt=text),ensure_ascii=False)+'\n')
 atomic_json(P/'transport-plan.json',dict(fixed_n=N,all_membership_fixed_before_answers=True,no_interim_score_stopping=True,chunks=[dict(order=i+1,n=len(ts),tasks_path=str(P/f'chunk-{i+1:02}.tasks.json'),sha256=sha(P/f'chunk-{i+1:02}.tasks.json'),ids=[t['id'] for t in ts],cell_counts=dict(Counter(cell(t) for t in ts))) for i,ts in enumerate(stages)],combined_order_matches_tasks_file=True,second_only_after_first_settles=True,no_paid_authorization=True))
 assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 files=['plan.json','tasks.json',*[f'chunk-{i+1:02}.tasks.json' for i in range(6)],'transport-plan.json','shared-regeneration-audit.json','allocation-objective.json','distribution-and-family-audit.json','exposure-and-novelty-audit.json','prompts.jsonl']
 manifest=dict(created_at=now(),status=p['status'],n=N,source_hashes=sources,files={x:dict(sha256=sha(P/x),bytes=(P/x).stat().st_size) for x in files},tasks_digest=digest(tasks),shared_validation_passed=True,all_distribution_and_prompt_checks_passed=True,family_count=g,paid_calls=0,no_final_answers_read=True,benchmark_ready=False)
 atomic_json(P/'manifest.json',manifest);print(json.dumps(dict(n=N,families=g,objective=objective,exposure={k:v for k,v in exposure.items() if k!='historical_input_snapshot'},tasks_sha256=sha(P/'tasks.json'),manifest_sha256=sha(P/'manifest.json')),indent=2))
 status('Pilot 08 development candidate prepared',f'Prepared {N} fresh exact development tuples from {g} previously exposed families, in six fixed 400-question chunks. Exact grammar/class/PN quotas and shared validation pass. Unpaid; no interim score stopping or independent-family claim.')
if __name__=='__main__':main()
