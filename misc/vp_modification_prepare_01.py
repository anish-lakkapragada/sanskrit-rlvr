"""Freeze input-selected matched modification/control development pilot; no APIs."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import copy,hashlib,json,sys,time,heapq,math,random
from misc import vp_modification_task_v1 as mod
from misc.vp_modification_prompt_v1 import render
from misc.vp_5d_novelty_04 import normalized,walk
from misc.vp_goal_validate import validate
ROOT=mod.ROOT;OUT=ROOT/'benchmarks/parallel-search-20261007/modification-01';SEED=202610071907
SOURCE=['Lat','Lit','Lan','Lun'];TARGET=['Lat','Lit','Lut','Lrt','Lot','Lan','VidhiLin','AshirLin','Lun','Lrn']
PNS=[(p,n) for p in ['Prathama','Madhyama','Uttama'] for n in ['Eka','Dvi','Bahu']]
def now():return datetime.now(timezone.utc).isoformat()
def write(name,x):(OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def rank(*x):return int(hashlib.sha256(json.dumps([SEED,*x],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:14],16)
def morphology(lak,pn):return dict(lakara=lak,prayoga='Kartari',purusha=pn[0],vacana=pn[1])
def status(text):write('status.json',dict(run_id='modification-01',state='running',updated_at=now(),phase=text,benchmark_ready=False))
class MinCost:
    def __init__(self):
        self.adj=defaultdict(list)
    def edge(self,u,v,cap,cost=0):
        a=[v,cap,None,cap,cost];b=[u,0,a,0,-cost];a[2]=b
        self.adj[u].append(a);self.adj[v].append(b)
        return a
    def flow(self,s,t,limit):
        potential=defaultdict(int);flow=cost=serial=0
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
                        dist[v]=nd;parent[v]=(u,e)
                        heapq.heappush(heap,(nd,serial,v));serial+=1
            if t not in dist:break
            for node,d in dist.items():potential[node]+=d
            aug=limit-flow;node=t
            while node!=s:
                prev,e=parent[node];aug=min(aug,e[1]);node=prev
            node=t
            while node!=s:
                prev,e=parent[node];e[1]-=aug;e[2][1]+=aug;cost+=aug*e[4];node=prev
            flow+=aug
        return flow,cost


def main():
 start=time.monotonic();assert not (OUT/'tasks.json').exists(),'Preserve frozen tasks'
 status('Building 36 complete inverse profiles')
 profiles=[]
 for lak in SOURCE:
  for pn in PNS:
   m=morphology(lak,pn);ix=mod.inverse(mod.signature(m));profiles.append(dict(morphology=m,keys=ix,shadow_all_dictionary_keys=mod.shadow_inverse(mod.signature(m))))
 write('inverse-index.json',dict(scope='Canonical full engine unions for all source-eligible classical dictionary entries across every split; not all Sanskrit.',profiles=profiles))
 hist=set();files=[]
 for directory in ['creation-campaign-20261006','iterative-goal-20261006']:
  base=ROOT/'benchmarks'/directory;ledger=json.loads((base/'ledger.json').read_text())
  for job in ledger['jobs']:
   path=base/'jobs'/job/'tasks.json'
   if not path.exists():raise ValueError('Missing historical input '+str(path))
   old=json.loads(path.read_text());files.append(dict(path=str(path.relative_to(ROOT)),sha256=mod.sha(path),n=len(old)))
   for top in old:
    for t in walk(top):
     k,err=normalized(t)
     if not err:hist.add(k)
 status('Selecting fresh strict-single-family paired candidates')
 byfam=defaultdict(list)
 for code,e in mod.inventory().items():
  f=mod.family(e)
  if mod.assignments()[f]['split']=='development':byfam[f].append(code)
 candidates=[];excluded=Counter();family_classes={}
 for f,codes in sorted(byfam.items()):
  pn=PNS[rank(f,'pn')%9];family_classes[f]=str(mod.inventory()[codes[0]].dhatu.gana).split('.')[-1]
  # Stable dictionary choice; every colliding code is still checked below.
  for source in SOURCE:
   sm=morphology(source,pn);options=[]
   for code in sorted(codes):
    st=mod.ordinary(code,mod.signature(sm))
    if st:
     for word in st['gold_devanagari']:
      hits=mod.analyses(word,sm)
      if mod.shadow_inverse(mod.signature(sm)).get(word,[])!=hits:excluded['excluded_or_uncertain_shadow_collision']+=1;continue
      fams={mod.family(mod.inventory()[c]) for c in hits};splits={mod.assignments()[q]['split'] for q in fams}
      if len(splits)>1:excluded['cross_split_source_key']+=1;continue
      if fams!={f}:excluded['multiple_source_families']+=1;continue
      options.append((rank(f,source,word),word,hits,code))
   options=sorted({(r,w,tuple(h),c) for r,w,h,c in options})
   if not options:excluded['no_source_form_with_one_family']+=1;continue
   for target in TARGET:
    if target==source:continue
    tm=morphology(target,pn);chosen=None
    for _,word,hits,code in options:
     ts=[mod.ordinary(c,mod.signature(tm)) for c in hits]
     if any(t is None for t in ts):excluded['candidate_analysis_target_scope']+=1;continue
     if len({tuple(t['gold_slp1']) for t in ts})!=1:excluded['candidate_analysis_target_union_disagreement']+=1;continue
     if word in ts[0]['gold_devanagari']:excluded['source_equals_an_accepted_target']+=1;continue
     control=mod.ordinary(code,mod.signature(tm));sig,_=normalized(control)
     if sig in hist:excluded['historical_exact_target_tuple']+=1;continue
     chosen=dict(family=f,gana=control['dhatu']['gana'],pn=pn,source=source,target=target,word=word,codes=list(hits),control=control,source_morphology=sm,target_morphology=tm);break
    if chosen:candidates.append(chosen)
 if not candidates:raise ValueError('No valid candidates')
 fams=sorted({x['family'] for x in candidates});gcounts=Counter(next(x['gana'] for x in candidates if x['family']==f) for f in fams);classes=sorted(gcounts)
 classq={g:min(2,n) for g,n in gcounts.items()};remaining=200-sum(classq.values());weights={g:gcounts[g]-classq[g] for g in classes};den=sum(weights.values())
 raw={g:remaining*weights[g]/den for g in classes}
 for g in classes:classq[g]+=int(raw[g])
 for g in sorted(classes,key=lambda g:(-(raw[g]-int(raw[g])),g))[:200-sum(classq.values())]:classq[g]+=1
 pnq={pn:22+(i<2) for i,pn in enumerate(PNS)}
 # Freeze a source-by-target joint table and balanced PN slots before allocation.
 joint={}
 for target in TARGET:
  for source in SOURCE:
   if source==target:continue
   joint[(source,target)]=(5 if target not in SOURCE else (6 if (SOURCE.index(source)-SOURCE.index(target))%4==1 else 7))
 assert all(sum(q for (s,t),q in joint.items() if s==x)==50 for x in SOURCE)
 assert all(sum(q for (s,t),q in joint.items() if t==x)==20 for x in TARGET)
 slots=[k for k,q in sorted(joint.items()) for _ in range(q)]
 random.Random(SEED).shuffle(slots)
 cellq=Counter((source,target,PNS[i%9]) for i,(source,target) in enumerate(slots))
 flow=MinCost();edges=[]
 for gana,q in sorted(classq.items()):flow.edge('SOURCE',('g',gana),q)
 for f in fams:
  gana=next(x['gana'] for x in candidates if x['family']==f)
  flow.edge(('g',gana),('f',f),1)
 for key,q in sorted(cellq.items()):flow.edge(('cell',key),'SINK',q)
 for x in sorted(candidates,key=lambda x:rank(x['family'],x['source'],x['target'],x['word'])):
  key=(x['source'],x['target'],x['pn'])
  if key in cellq:
   edge=flow.edge(('f',x['family']),('cell',key),1,rank(x['family'],x['source'],x['target'],x['word'])%1000000);edges.append((x,edge))
 status('Solving exact input-only source/target/class/PN quotas')
 solved_n,solved_cost=flow.flow('SOURCE','SINK',200)
 if solved_n!=200:raise ValueError('Exact allocation infeasible: '+str(solved_n))
 selected=[x for x,e in edges if e[3]-e[1]==1];assert len(selected)==200
 selected.sort(key=lambda x:rank(x['family'],'order'))
 deps={str(p.relative_to(ROOT)):mod.sha(p) for p in [mod.POLICY,mod.DICT,mod.SPLIT,ROOT/'misc/vp_cartesian_task.py',ROOT/'misc/vp_modification_prompt_v1.py',ROOT/'misc/vp_modification_task_v1.py',OUT/'inverse-index.json']}
 tasks=[];controls=[];collisions=[]
 for x in selected:
  c=copy.deepcopy(x['control']);pub=dict(source_form_devanagari=x['word'],source_morphology=x['source_morphology'],target_morphology=x['target_morphology']);ident=mod.task_id(pub)
  c['campaign'].update(panel='modification-control-01',paired_modification_id=ident);controls.append(c)
  task=dict(id=ident,task_type='modification',prompt_version='modification-v1',**pub,dhatu=copy.deepcopy(c['dhatu']),morphology=copy.deepcopy(c['morphology']),gold_slp1=c['gold_slp1'],gold_devanagari=c['gold_devanagari'],campaign=dict(root_family=x['family'],split='development',construction='word_modification',trace_rule_ids=c['campaign']['trace_rule_ids'],panel='modification-01',control_task_id=c['id']),modification_audit=dict(candidate_codes=x['codes'],source_key=mod.public_key(x['word'],x['source_morphology']),dependencies=deps))
  task['campaign']['prompt_sha256']=hashlib.sha256(render(task).encode()).hexdigest();mod.validate_task(task,'development');tasks.append(task)
  collisions.append(dict(id=ident,source_key=task['modification_audit']['source_key'],candidate_codes=x['codes'],candidate_families=[x['family']],split='development',full_target_union_identical=True,source_distinct_from_every_target=True))
 validate(controls,'development');assert len({t['campaign']['root_family'] for t in tasks})==200
 for t,c in zip(tasks,controls):assert t['gold_slp1']==c['gold_slp1'] and t['gold_devanagari']==c['gold_devanagari']
 # Verify renderer independence from every private field, not just absence of labels.
 for t in tasks:
  public={k:t[k] for k in ['source_form_devanagari','source_morphology','target_morphology']};assert render(t)==render(public)
 write('tasks.json',tasks);write('controls.json',controls)
 (OUT/'prompts.jsonl').write_text(''.join(json.dumps(dict(id=t['id'],prompt=render(t),public_input={k:t[k] for k in ['source_form_devanagari','source_morphology','target_morphology']}),ensure_ascii=False)+'\n' for t in tasks))
 write('collision-audit.json',dict(created_at=now(),inventory_entries=len(mod.inventory()),inventory_family_counts=dict(Counter(mod.assignments()[mod.family(e)]['split'] for e in mod.inventory().values())),source_profiles=len(profiles),source_keys=sum(len(p['keys']) for p in profiles),inverse_sha256=mod.sha(OUT/'inverse-index.json'),strict_single_family=True,shadow_index_all_dictionary_entries=len(mod.entries_by_code()),excluded_source_analyses_block_keys=True,source_and_target_policy='Policy21 plus unresolved04.0137/10.0023 and any canonical vowel+r+C spelling-coverage hold',scope='All canonical source outputs of the audited source-eligible dictionary inventory across all splits. Not universal Sanskrit uniqueness; no model outcomes inspected.',excluded_candidate_attempt_counts=dict(excluded),eligible_development_families=len(fams),selected=collisions))
 write('novelty-audit.json',dict(scope='Immutable input files from both campaign ledgers, including component forms; no results read',files=files,unique_historical_tuples=len(hist),selected_target_overlap=0,selection_uses_model_errors=False,legacy_family_exposure='Development families may have prior exact and legacy exposure; only selected target tuples are fresh.'))
 plan=dict(created_at=now(),status='frozen_development_inputs_pending_parent_review',n=200,matched_control_n=200,seed=SEED,task_type='modification',prompt_version='modification-v1',source_tense_quotas={s:50 for s in SOURCE},target_tense_quotas={t:20 for t in TARGET},class_quotas=classq,pn_quotas={'|'.join(pn):q for pn,q in pnq.items()},family_count=200,voice='Kartari',changed_coordinates=['lakara'],source_and_target_surface_differ=True,model='claude-opus-5-5',effort='xhigh',max_output_tokens=65536,expected_jobs=['opus-modification-01','opus-modification-control-01'],selection='Seeded per-family PN; complete inverse lookup; source/target validity and exact-target novelty; Integral min-cost flow chooses200distinctfamilies with exact source/target/class/PN margins. Class quotas minimum2 per available class then proportional remaining family supply, largest remainders. A fixed source-target joint table and shuffled balancedPNslots give exact margins; random input hashes are edge costs. No model outcomes.',solver=dict(method='integral min-cost flow',flow=solved_n,objective=solved_cost),source_target_joint_quotas={s+'|'+t:q for (s,t),q in joint.items()},limitations=['Only source4tenses and Kartari tested; all10targettenses.','Dictionary-inventory and current engine source-form unions bound ambiguity detection; no claim of universal Sanskrit uniqueness.','Accepted target union does not require preserving a separately chosen pada; no pada choice is a public coordinate.','200developmentquestions do not meet finalprecision or establish benchmarkqualification.'],benchmark_ready=False,paid_calls=0)
 write('plan.json',plan)
 write('analysis-predeclaration.json',dict(created_at=now(),fixed_n=200,expected_jobs=plan['expected_jobs'],hold='Require both complete200-question arms settled and collected before paired analysis; no interim membership or score stopping.',exact_pairing='Ordered modification/control IDs; same full target gold union;200distinct dictionary families.',metrics=['all-request accuracy','usable accuracy under shared completed predicate','completion and missing-answer bounds','paired correctness transition table','paired accuracy difference with whole-family bootstrap','iid and family SE','source tense, target tense, class and PN strata'],no_automatic_qualification=True,raw_results_immutable=True,current_scope='Any later independent source predicate applies symmetrically to both arms and every outcome; supplemental scope only, never silently overwrite raw.'))
 files=['tasks.json','controls.json','prompts.jsonl','plan.json','collision-audit.json','novelty-audit.json','inverse-index.json','analysis-predeclaration.json']
 write('manifest.json',dict(created_at=now(),n=200,control_n=200,files={name:mod.sha(OUT/name) for name in files},dependencies=deps,generator_sha256=mod.sha(Path(__file__)),validation='All200modifications fully collision/regeneration checked;200controls pass shared validator; allpublicprompts independent of privatefields; exactpairedgold;200distinctfamilies',elapsed_seconds=time.monotonic()-start,paid_calls=0,benchmark_ready=False))
 print(json.dumps(dict(n=200,families=200,eligible_families=len(fams),candidate_edges=len(candidates),classes=classq,elapsed_seconds=time.monotonic()-start,tasks_sha256=mod.sha(OUT/'tasks.json'),controls_sha256=mod.sha(OUT/'controls.json'))))
if __name__=='__main__':main()
