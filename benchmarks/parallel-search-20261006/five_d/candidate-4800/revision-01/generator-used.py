"""Build/recheck an unpaid, unevaluated 4800-question policy15 test candidate.

This selects candidate inputs only. It never reads model result files, submits
requests, installs a release gate, or approves final evaluation membership/N.
"""
from __future__ import annotations
import argparse,hashlib,heapq,json,math,random,time
from collections import Counter,defaultdict
from pathlib import Path
from misc.vp_5d_prepare_04 import ROOT,OUT,atomic_json,now,sha,status
from misc.vp_5d_pilot import SPLIT
from misc.vp_5d_prepare_03 import SOURCE_ROOTS
from misc.vp_5d_prepare_05 import UNRESOLVED,history
from misc.vp_5d_novelty_04 import normalized
from misc.vp_5d_release_feasibility import MinCost
from misc.vp_cartesian_task import make_task,entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v3 import render
from misc.vp_sanskrit_prompt_v1 import root_fields
from misc.vp_goal_validate import validate
from misc import vp_campaign_candidates as old
from vidyut.prakriya import Vyakarana

N=4800;CAP=8;LCAP=5;VERSION='cartesian-5d-v3-sanskrit'
SEED='vp-five-d-candidate-4800-policy15-20261007-01'
EXPECTED_POLICY='7c653b7216e4797b27eaae25949463dcbc28e306a803da7c33a451481da71162'
SOURCES={
 'source_plan':OUT/'pilot-06.revision-01.plan.json',
 'supply':OUT/'pilot-06.scale-supply-policy15.json',
 'supply_policy15_proof':OUT/'pilot-06.supply-policy15-addendum.json',
 'policy':OUT.parent/'oracle-policy-15.json',
 'adapter':ROOT/'misc/vp_cartesian_task.py',
 'validator':ROOT/'misc/vp_goal_validate.py',
 'renderer':ROOT/'misc/vp_cartesian_prompt_v3.py',
 'sanskrit_helper':ROOT/'misc/vp_sanskrit_prompt_v1.py',
 'dictionary':old.TSV,'family_split':SPLIT,
 'flow_implementation':ROOT/'misc/vp_5d_release_feasibility.py',
 'generator':Path(__file__),
}

def read(p):return json.loads(Path(p).read_text())
def cell(t):return '|'.join((t['derivation']['recipe_id'],t['morphology']['lakara'],t['morphology']['prayoga']))
def digest(tasks):return hashlib.sha256(json.dumps(tasks,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def tagged_rng(seed,tag):return random.Random(seed+':'+tag)

class ProgressFlow(MinCost):
 def flow(self,s,t,limit):
  potential=defaultdict(int);flow=cost=serial=0;last=time.monotonic()
  while flow<limit:
   dist={s:0};parent={};heap=[(0,serial,s)];serial+=1
   while heap:
    du,_,u=heapq.heappop(heap)
    if du!=dist[u]:continue
    for e in self.adj[u]:
     v,cap,_,_,c=e
     if not cap:continue
     nd=du+c+potential[u]-potential[v]
     if nd<dist.get(v,math.inf):
      dist[v]=nd;parent[v]=(u,e);heapq.heappush(heap,(nd,serial,v));serial+=1
   if t not in dist:break
   for node,d in dist.items():potential[node]+=d
   aug=limit-flow;node=t
   while node!=s:
    prev,e=parent[node];aug=min(aug,e[1]);node=prev
   node=t
   while node!=s:
    prev,e=parent[node];e[1]-=aug;e[2][1]+=aug;cost+=aug*e[4];node=prev
   flow+=aug
   if time.monotonic()-last>25:
    status('Allocating provisional4800 candidate',f'Input-only minimum-cost flow has assigned {flow}/{limit} slots, prioritizing family coverage, then fewer repeated lakaras, then balanced loads. No provider calls or final evaluation approval.');last=time.monotonic()
  return flow,cost

def plan(output,seed):
 assert sha(SOURCES['adapter'])==EXPECTED_POLICY,'Policy changed; do not silently revise this candidate'
 src=read(SOURCES['source_plan']);supply=read(SOURCES['supply']);assert supply['shared_adapter_sha256']==EXPECTED_POLICY
 assert supply['family_split_sha256']==sha(SPLIT) and supply['dictionary_sha256']==sha(old.TSV)
 assert src['n']==600 and N==8*src['n']
 p=dict(created_at=now(),track='five_d',status='provisional_unevaluated_release_candidate',candidate_n=N,n=N,fixed_n=None,
  final_n_approved=False,final_membership_approved=False,evaluation_protocol_approved=False,benchmark_ready=False,seed=seed,
  split='test',policy='oracle-policy-15',prompt_version=VERSION,recipe_operations=src['recipe_operations'],
  recipe_counts={k:8*v for k,v in src['recipe_counts'].items()},cell_counts={k:8*v for k,v in src['cell_counts'].items()},
  gana_counts={k:8*v for k,v in src['gana_counts'].items()},lakara_counts={k:8*v for k,v in src['lakara_counts'].items()},
  prayoga_counts={'Kartari':4320,'Karmani':480},person_counts={k:1600 for k in ['Prathama','Madhyama','Uttama']},number_counts={k:1600 for k in ['Eka','Dvi','Bahu']},
  person_number_counts={p+'/'+v:534 if i==j else 533 for i,p in enumerate(['Prathama','Madhyama','Uttama']) for j,v in enumerate(['Eka','Dvi','Bahu'])},
  maximum_tasks_per_family=CAP,maximum_Lun_per_family=LCAP,maximum_each_other_lakara_per_family=1,
  source_control_codes_excluded=sorted(SOURCE_ROOTS),unresolved_prospective_exclusions=UNRESOLVED,
  source_hashes={k:dict(path=str(v),sha256=sha(v)) for k,v in SOURCES.items()},
  source_scope='Current policy15 plus source-control roots and unresolved stim04.0137/urja10.0023 exclusions; all selected inputs must regenerate identically and pass the shared test validator.',
  task_shape='Dictionary dhatu citation/class/meaning + lakara/prayoga/purusha/vacana + one ordered recipe from the three-item menu; return one accepted Devanagari finite form. No prefixes, separate pada, synthetic roots, nominal output or additional hidden choices.',
  recipe_rationale={
   'causative_of_intensive':'yaN then Ric tests intensive-stem preservation when the intensive suffix is deleted before the outer causative. Existing reduplication matters in causal Lun; chain length alone is not the difficulty rationale.',
   'causative_of_intensive_luk':'Independent yaNluk then Ric contrasts the surviving intensive stem and subsequent ordinary causative behavior; source-audited marker/gana/lexical transfer gates apply.',
   'desiderative':'san provides an independently licensed shorter recipe and broader root/class coverage; all its tasks are active and its weight remains1/15.'},
  grammar_rationale='Exactly8x the audited pilot06 global joint and class counts:45%Lun,55% across other9lakaras,10%passive, three recipes and all10classes. No per-item model errors or final responses enter selection.',
  family_allocation_objective=['Maximize distinct eligible test families under exact joint/class quotas.','Minimize repeated family-lakara assignments beyond the first; only Lun may repeat.','Minimize sum of squared total family loads.'],
  tie_breaking='Independent seeded streams shuffle a sorted input-family list, class/cell/tense edge insertion order, PN family/cell ordering and final task order. Integer costs fix the three objective priorities; insertion order only breaks ties. No block preference is used.',
  PN_assignment='For each selected family, permute its occupied cells with a seeded stream and assign consecutive positions of a global9-option cycle; every family has<=8tasks, so even repeated exact cells receive unique PN. The first3cycle positions are a shuffled diagonal matching and the remaining6 are shuffled, yielding exact1600person/number margins and PN534on diagonal,533elsewhere.',
  novelty_rule='Compare normalized grammar tuples and family IDs against all task/component INPUT files in both campaign ledgers. No results or model-answer files read; reject any candidate tuple previously present.',
  comparison_limit='Global quotas match the passed development panel, but test families differ and now contribute up to8forms and5aorists. The300 two-distinct-tense development family allocation does not identify difficulty or precision for these larger loads.',
  statistical_target=dict(point_accuracy_target=[.79,.81],precision_standard_error_lt=.01,qualified=False,gate='If separately approved and evaluated, require strongest-reference all/usable scores and missing-response bounds within79–81, and both iid and family-sandwich SE<.01 for both references. Preserve raw/current-scope results and report bootstrap sensitivities.'),
  point_accuracy_target=[.79,.81],precision_standard_error_lt=.01,
  evaluation_hold='No release gate, authorization fragment, submitted job or approved finalN/protocol is created. Parent owns the60-question development cap diagnostic, cumulative funding and eventual final freeze. This file is a reviewable candidate sampling plan only.',
  current_risks='Prior Astra revised-mixture forecast is$0.24006/question, or$1152.31for4800 before cap-diagnostic implications. Realistic family/response-completion scenarios straddle1pp. Neither cost nor precision is guaranteed.',
  paid_calls=0,model_answers_read_for_selection=False,no_final_model_answers_read=True)
 output.mkdir(parents=True);atomic_json(output/'sampling-plan.json',p);return p,supply

def allocate(supply,p):
 rng=tagged_rng(p['seed'],'flow');rows=sorted(supply['rows'],key=lambda r:r['family']);rng.shuffle(rows)
 n=p['n'];net=ProgressFlow();fe={};le={};ce=[];medium=n*CAP*CAP+1;large=n*(medium+CAP*CAP)+1
 classes=sorted(p['gana_counts']);rng.shuffle(classes)
 for g in classes:net.edge('s',('g',g),p['gana_counts'][g])
 for i,row in enumerate(rows):
  f=('f',i);fe[i]=[net.edge(('g',row['gana']),f,1,0)]+[net.edge(('g',row['gana']),f,1,large+2*j-1) for j in range(2,CAP+1)]
  masks=row['eligible_person_number_masks'];las=sorted({c.split('|')[1] for c in masks if c in p['cell_counts']});rng.shuffle(las)
  for la in las:
   lc=LCAP if la=='Lun' else 1;le[i,la]=[net.edge(f,('fl',i,la),1,0)]+[net.edge(f,('fl',i,la),1,medium) for j in range(2,lc+1)]
  cc=sorted(c for c in masks if c in p['cell_counts']);rng.shuffle(cc)
  for c in cc:
   assert masks[c]==511,'PN proof requires full masks; do not silently relax'
   ce.append((i,c,net.edge(('fl',i,c.split('|')[1]),('c',c),min(CAP,masks[c].bit_count()))))
 cells=sorted(p['cell_counts']);rng.shuffle(cells)
 for c in cells:net.edge(('c',c),'t',p['cell_counts'][c])
 flow,cost=net.flow('s','t',n);assert flow==n
 occupied=defaultdict(Counter)
 for i,c,e in ce:
  count=e[3]-e[1]
  if count:occupied[rows[i]['family']][c]+=count
 loads=Counter(sum(v.values()) for v in occupied.values());distinct=len(occupied);repeat=sum(sum(v for c,v in cc.items() if '|Lun|' in c)>0 for cc in occupied.values());repeat=p['lakara_counts']['Lun']-repeat;ssq=sum(m*m*k for m,k in loads.items())
 assert cost==large*(n-distinct)+medium*repeat+ssq-distinct
 prior=read(OUT/'pilot-06.scale-witness-policy15-N4800.json');prior_obj=[prior['distinct_families'],prior['repeated_aorist_questions_beyond_one_per_family'],round(n*(1+prior['family_pair_correlation_multiplier']))]
 assert [distinct,repeat,ssq]==prior_obj,'Seeded ties changed the supposedly exact optimal objective'
 objective=dict(flow=flow,cost=cost,large_cost=large,medium_cost=medium,distinct_families=distinct,repeated_lakara_assignments=repeat,sum_squared_family_loads=ssq,family_load_histogram=dict(loads),comparison_to_previous_aggregate_witness=prior_obj,matched_original_objective=True,cost_identity='large*(N-families)+medium*repeated_lakaras+sum_squared_loads-families',priority_proof='medium>N*cap^2 bounds all possible tertiary variation; large>N*(medium+cap^2) bounds all secondary+tertiary variation. Exact integral min-cost flow therefore gives the ordered objective.',no_block_preference=True)
 return dict(occupied),objective

def build(output,seed):
 output=Path(output)
 if output.exists():raise RuntimeError('Preserve existing candidate directory; use a new explicit path')
 p,supply=plan(output,seed);used,hf,ha=history();atomic_json(output/'history-input-snapshot.json',ha)
 assignments=json.loads(SPLIT.read_text())['families'];es={}
 for e in old.load_entries():
  if assignments[old.family(e)]['split']=='test':es.setdefault(old.family(e),e)
 assert len(es)==1000
 held=set(SOURCE_ROOTS)|set(UNRESOLVED)
 assert all(not r['eligible_person_number_masks'] for r in supply['rows'] if es[r['family']].code in held)
 occupied,objective=allocate(supply,p);atomic_json(output/'allocation-objective.json',objective)
 status('Generating provisional4800 task forms',f'Original allocation objective reached {objective["distinct_families"]} test families and {objective["repeated_lakara_assignments"]} repeated aorist assignments. Now generating actual4,800 forms with balanced person and number; unpaid candidate only.')
 rng=tagged_rng(seed,'pn');diagonal=[('Prathama','Eka'),('Madhyama','Dvi'),('Uttama','Bahu')];rng.shuffle(diagonal)
 rest=[(pu,va) for pu in ['Prathama','Madhyama','Uttama'] for va in ['Eka','Dvi','Bahu'] if (pu,va) not in diagonal];rng.shuffle(rest);pn=diagonal+rest
 families=sorted(occupied);rng.shuffle(families);cursor=0;tasks=[];allocation=[];v=Vyakarana();bases={f:sorted({q.text for q in v.derive(es[f].dhatu)}) for f in families};last=time.monotonic()
 for f in families:
  slots=[c for c in sorted(occupied[f]) for _ in range(occupied[f][c])];rng.shuffle(slots);assert len(slots)<=CAP
  for c in slots:
   pu,va=pn[cursor%9];cursor+=1;rec,la,vo=c.split('|');e=es[f];assert e.code not in held
   t=make_task(e,'test',dict(lakara=la,prayoga=vo,purusha=pu,vacana=va),rec,p['recipe_operations'][rec],prompt_version=VERSION)
   assert t is not None and not(entry_scope_issue(e) or oracle_issue(t))
   sig,issue=normalized(t);assert not issue and sig not in used
   t['campaign'].update(panel='five-d-candidate-4800',candidate_status='provisional_unevaluated_not_finally_approved',plan_sha256=sha(output/'sampling-plan.json'),oracle_policy='oracle-policy-15',lexical_bases=bases[f],selection_reason='Input-only exact-cost allocation: maximize family coverage, minimize repeated lakaras, balance loads; seeded ties and cyclic balanced PN. No model outcomes used.',sampling_cell={'recipe_id':rec,'lakaras':[la],'prayogas':[vo]},audit_status='Shared policy15 and prospective source/control exclusions; mechanically regenerated accepted union. Full rare forms are not all independently printed; no empirical qualification.')
   tasks.append(t);allocation.append(dict(id=t['id'],family=f,code=e.code,gana=t['dhatu']['gana'],cell=c,purusha=pu,vacana=va))
   if time.monotonic()-last>25:status('Generating provisional4800 task forms',f'Generated {len(tasks)}/4800 actual candidate forms; all remain input-selected, under policy15, with no prior tuple overlap.');last=time.monotonic()
 tagged_rng(seed,'task-order').shuffle(tasks)
 assert sha(SOURCES['adapter'])==EXPECTED_POLICY
 atomic_json(output/'tasks.json',tasks);atomic_json(output/'allocation.json',allocation)
 atomic_json(output/'family-assignments.json',[dict(family=f,code=es[f].code,gana=old.name(es[f].dhatu.gana),tasks=sum(occupied[f].values()),cells=dict(occupied[f])) for f in sorted(occupied)])
 audit=validate(tasks,'test',allowed_families=set(occupied));audit.update(candidate_status=p['status'],tasks_sha256=sha(output/'tasks.json'),sampling_plan_sha256=sha(output/'sampling-plan.json'),shared_adapter_sha256=sha(SOURCES['adapter']),source_scope_policy='oracle-policy-15',final_membership_approved=False,paid_calls=0);atomic_json(output/'shared-regeneration-audit.json',audit)
 checks=verify_tasks(tasks,p,occupied,es);atomic_json(output/'distribution-and-prompt-audit.json',checks)
 used_after,hf_after,ha_after=history();overlap=[t['id'] for t in tasks if normalized(t)[0] in used_after];assert not overlap and not(set(occupied)&hf_after)
 novelty=dict(created_at=now(),tasks_sha256=sha(output/'tasks.json'),**ha_after,overlap_count=0,overlaps=[],distinct_candidate_families=len(occupied),families_present_in_prior_campaign_inputs=0,scope='All task/component INPUT files from both campaign ledgers, across all phases; no result files or model answers read.',normalized_shape='Exact dictionary citation+class, ordered recipe, all4coordinates, no prefixes or specified pada; prompt version and taskID ignored.',model_answers_read=False);atomic_json(output/'novelty-audit.json',novelty)
 with (output/'prompts.jsonl').open('w') as f:
  for t in tasks:f.write(json.dumps({'id':t['id'],'prompt':render(t)},ensure_ascii=False)+'\n')
 controls=[]
 for c in read(OUT/'pilot-03.source-audit.json')['direct_checks']:
  ee=next(e for e in old.load_entries() if e.code==c['code']);t=make_task(ee,'source_control',c['morphology'],'source_control',c['sanadi'],prompt_version=VERSION);assert c['expected'] in t['gold_slp1'];controls.append({**c,'current_gold_slp1':t['gold_slp1'],'passed':True,'excluded_from_candidate':all(x['dhatu']['code']!=c['code'] for x in tasks)})
 atomic_json(output/'recipe-control-audit.json',dict(created_at=now(),policy='oracle-policy-15',checks=controls,scope='Previously independently printed primary recipe controls rechecked; not exhaustive full-form attestation.',source_artifact_sha256=sha(OUT/'pilot-03.source-audit.json')))
 assert sha(SOURCES['adapter'])==EXPECTED_POLICY
 manifest=dict(created_at=now(),status=p['status'],track='five_d',candidate_n=N,final_n=None,final_n_approved=False,final_membership_approved=False,evaluation_protocol_approved=False,benchmark_ready=False,all_tasks_regenerated=True,all_distribution_and_prompt_checks_passed=True,objective=objective,distributions=checks['distributions'],family_statistics=checks['family_statistics'],source_hashes=p['source_hashes'],files={name:dict(sha256=sha(output/name),bytes=(output/name).stat().st_size) for name in ['sampling-plan.json','tasks.json','allocation.json','family-assignments.json','allocation-objective.json','shared-regeneration-audit.json','distribution-and-prompt-audit.json','history-input-snapshot.json','novelty-audit.json','recipe-control-audit.json','prompts.jsonl']},tasks_digest=digest(tasks),no_release_gate_created=True,no_authorization_fragment_created=True,no_paid_calls=True,no_model_answer_files_read=True,scope='Full1000-family master test reserve, with source/uncertainty holds.462RL families remain disjoint. This is a reviewable unevaluated candidate; parent must approve finalN/protocol/funding and enforce cross-track allocation before final release.',limits=p['comparison_limit']+' '+p['current_risks']);atomic_json(output/'manifest.json',manifest)
 write_readme(output,p,manifest)
 status('Provisional4800 candidate ready for review',f'Created 4,800 actual test tasks from {len(occupied)} families, preserving all pilot06-scaled joint/class quotas and person-number balance. Full shared regeneration, prompt, source-control and historical-input novelty audits pass. Unpaid and unevaluated; finalN/protocol/funding remain unapproved.')
 print(json.dumps({'output':str(output),'task_sha256':sha(output/'tasks.json'),'tasks_digest':digest(tasks),'plan_sha256':sha(output/'sampling-plan.json'),'families':len(occupied),'manifest_sha256':sha(output/'manifest.json')},indent=2))

def verify_tasks(tasks,p,occupied,es):
 assert len(tasks)==len({t['id'] for t in tasks})==N
 assert len({normalized(t)[0] for t in tasks})==N
 assert Counter(cell(t) for t in tasks)==Counter(p['cell_counts'])
 assert Counter(t['dhatu']['gana'] for t in tasks)==Counter(p['gana_counts'])
 assert Counter(t['derivation']['recipe_id'] for t in tasks)==Counter(p['recipe_counts'])
 assert Counter(t['morphology']['lakara'] for t in tasks)==Counter(p['lakara_counts'])
 assert Counter(t['morphology']['prayoga'] for t in tasks)==Counter(p['prayoga_counts'])
 assert Counter(t['morphology']['purusha'] for t in tasks)==Counter(p['person_counts'])
 assert Counter(t['morphology']['vacana'] for t in tasks)==Counter(p['number_counts'])
 assert Counter(t['morphology']['purusha']+'/'+t['morphology']['vacana'] for t in tasks)==Counter(p['person_number_counts'])
 grouped=defaultdict(list);prompts=set();paircells=Counter()
 for t in tasks:
  txt=render(t);assert root_fields(t['dhatu']) in txt
  assert all(txt.count(label)==1 for label in ['लकारः —','प्रयोगः —','पुरुषः —','वचनम् —','सनादिप्रत्ययाः (क्रमेण) —'])
  assert 'सिद्धेषु रूपेष्वेकमेव' in txt and '<answer></answer>' in txt
  assert hashlib.sha256(txt.encode()).hexdigest()==t['campaign']['prompt_sha256']
  assert txt not in prompts;prompts.add(txt)
  assert len(t['morphology'])==4 and t['derivation']['prefixes']==[] and t['derivation']['sanadi']==p['recipe_operations'][t['derivation']['recipe_id']]
  assert t['dhatu']['code'] not in set(p['source_control_codes_excluded'])|set(p['unresolved_prospective_exclusions'])
  grouped[t['campaign']['root_family']].append(t)
 for f,ts in grouped.items():
  assert len(ts)<=CAP and Counter(cell(t) for t in ts)==occupied[f]
  counts=Counter(t['morphology']['lakara'] for t in ts);assert counts['Lun']<=LCAP
  assert all(v<=1 for k,v in counts.items() if k!='Lun')
  for i,t in enumerate(ts):
   for u in ts[i+1:]:paircells[tuple(sorted((cell(t),cell(u))))]+=1
 loads=Counter(len(ts) for ts in grouped.values());lunloads=Counter(sum(t['morphology']['lakara']=='Lun' for t in ts) for ts in grouped.values());lunloads.pop(0,None)
 fs=dict(distinct_families=len(grouped),family_load_histogram=dict(loads),family_gana_counts=dict(Counter(es[f].dhatu.gana.name for f in grouped)),maximum_tasks_per_family=max(loads),aorist_family_load_histogram=dict(lunloads),distinct_aorist_families=sum(lunloads.values()),repeated_aorist_assignments=sum((k-1)*v for k,v in lunloads.items()),family_pair_correlation_multiplier=sum(k*k*v for k,v in loads.items())/N-1,unordered_within_family_cell_pair_counts=[dict(cell_a=a,cell_b=b,pairs=n) for (a,b),n in sorted(paircells.items())])
 return dict(created_at=now(),n=N,passed=True,distributions=dict(recipes=p['recipe_counts'],joint_cells=p['cell_counts'],gana=p['gana_counts'],lakara=p['lakara_counts'],prayoga=p['prayoga_counts'],purusha=p['person_counts'],vacana=p['number_counts'],person_number=p['person_number_counts']),family_statistics=fs,all_prompts_recomputed=True,all_prompts_single_accepted_form=True,exact4coordinates_plus_one_ordered_recipe=True,all_forms_regenerated_separately_by_shared_validator=True)

def write_readme(output,p,m):
 fs=m['family_statistics'];(output/'README.md').write_text(f'''# Unevaluated 5D release candidate: 4,800 questions

**Provisional, unpaid and unevaluated. Final N, reference protocol, funding and final membership are not approved.** No release gate, authorization fragment or paid job was created.

The candidate contains 4,800 actual dictionary-root tasks from {fs['distinct_families']} master-test families, disjoint from all 462 RL families and all historical campaign task-input families. Each question supplies the dictionary citation/class/meaning, four inflection coordinates, and one ordered recipe, requesting one accepted Devanagari finite form.

Every global count is exactly 8 times the confirmed pilot06 plan: 3,200 yaN→Ric,1,280 yaNluk→Ric and 320 san;2,160 Lun (45%),2,640 across the other nine lakaras,480 passive (10%), and all ten classes. Every person and number has1,600 tasks. The nine PN cells have 533 each, with 534 on the three diagonal cells.

Input-only seeded min-cost flow maximizes distinct family coverage, then minimizes repeated family-lakara assignments, then balances family loads. It uses the original allocation objective, with **no block preference**. Each family contributes at most 8 tasks and 5 aorists; every other tense appears at most once per family. The selected allocation has {fs['distinct_aorist_families']} aorist families and{fs['repeated_aorist_assignments']} aorist assignments beyond the first per family. The integer objective matches the previous aggregate witness; seed only resolves equally optimal input allocations.

The two intensive recipes test inherited reduplication and stem preservation under distinct suffix-deletion histories; san supplies a shorter licensed contrast and broader roots. Mere chain length is not the difficulty rationale. Policy15 and the explicit source-control/stim/urja holds apply. Recipe controls were rechecked, but every full rare form is not independently printed in an external source.

[Tasks](tasks.json), [sampling plan](sampling-plan.json), [manifest](manifest.json), [shared regeneration audit](shared-regeneration-audit.json), [distribution/prompt audit](distribution-and-prompt-audit.json), [source recipe controls](recipe-control-audit.json), [input novelty audit](novelty-audit.json), and [readable prompt records](prompts.jsonl) make this candidate reviewable. [Family assignments](family-assignments.json) record the actual candidate allocation.

TaskSHA256: `{m['files']['tasks.json']['sha256']}`. PlanSHA256: `{m['files']['sampling-plan.json']['sha256']}`. Reusable generator: `misc/vp_5d_candidate_4800.py`; the plan fingerprints its code and all shared dependencies.

No model-answer files were read. Existing development scores motivated only the global predeclared grammar distribution; no item errors select membership. All prior tasks/scores/hashes remain unchanged. Both-model accuracy, completion, cap sensitivity, family dependence and the cumulative budget remain coordinator decisions before any final freeze. At the current forecast N=4,800 is fundable but sub1pp is uncertain; generating this candidate does not resolve that risk.
''')

def recheck(output):
 output=Path(output);p=read(output/'sampling-plan.json');m=read(output/'manifest.json');tasks=read(output/'tasks.json')
 for name,spec in m['files'].items():assert sha(output/name)==spec['sha256'],'Candidate file changed: '+name
 assert sha(SOURCES['adapter'])==EXPECTED_POLICY
 assert digest(tasks)==m['tasks_digest']
 assignments=read(output/'family-assignments.json');occupied={x['family']:Counter(x['cells']) for x in assignments};es={old.family(e):e for e in old.load_entries() if old.family(e) in occupied}
 audit=validate(tasks,'test',allowed_families=set(occupied));checks=verify_tasks(tasks,p,occupied,es);assert json.loads(json.dumps(checks['family_statistics']))==m['family_statistics']
 print(json.dumps({'passed':True,'n':audit['n'],'families':len(occupied),'tasks_sha256':sha(output/'tasks.json'),'final_membership_approved':False},indent=2))

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['build','recheck']);a.add_argument('--output',type=Path,default=OUT/'candidate-4800');a.add_argument('--seed',default=SEED);args=a.parse_args();build(args.output,args.seed) if args.action=='build' else recheck(args.output)
