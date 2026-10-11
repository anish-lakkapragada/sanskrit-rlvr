"""Input-only family-enriched240 subset, fixed before any pilot08 answers."""
from __future__ import annotations
import json, random, math
from collections import Counter,defaultdict
from itertools import combinations
from pathlib import Path
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,sha,now,status
from misc.vp_5d_candidate_4800_p18 import ProgressFlow,cell,digest
from misc.vp_cartesian_task import entry_scope_issue,oracle_issue,entries_by_code
from misc.vp_goal_validate import validate
P=OUT/'pilot-08/revision-01';SEED='vp-five-d-pilot08-astra-pairs-20261007-01'
REC=['causative_of_intensive','causative_of_intensive_luk','desiderative']
def read(p):return json.loads(p.read_text())
def rng(tag):return random.Random(SEED+':'+tag)
def apportion(source,n):
 total=sum(source.values());out={k:int(v*n//total) for k,v in source.items()};order=sorted(source,key=lambda k:(-(source[k]*n/total-out[k]),k))
 for k in order[:n-sum(out.values())]:out[k]+=1
 assert sum(out.values())==n;return out

def main():
 Q=P/'astra-subset';assert not Q.exists(),'Preserve frozen subset';es=entries_by_code();ts=read(P/'tasks.json');parent=read(P/'plan.json');assert len(ts)==2400
 assert all(not(entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)) for t in ts)
 target={};coarse={REC[0]:(60,57,17),REC[1]:(26,25,7),REC[2]:(22,26,0)}
 for rec,(lun,active,passive) in coarse.items():
  target[rec+'|Lun|Kartari']=lun
  for voice,n in [('Kartari',active),('Karmani',passive)]:
   src={c:q for c,q in parent['cell_counts'].items() if c.startswith(rec+'|') and '|Lun|' not in c and c.endswith('|'+voice)}
   if n:target.update(apportion(src,n))
 assert len(target)==42 and min(target.values())>0 and sum(target.values())==240
 classes=apportion(parent['gana_counts'],240);assert classes['Curadi']==14
 gt=dict(classes);del gt['Curadi'];gt['Curadi|Lun']=3;gt['Curadi|other']=11
 def gkey(t):return 'Curadi|'+('Lun' if t['morphology']['lakara']=='Lun' else 'other') if t['dhatu']['gana']=='Curadi' else t['dhatu']['gana']
 fam=defaultdict(list)
 for t in ts:fam[t['campaign']['root_family']].append(t)
 candidates=defaultdict(list)
 for f,tt in sorted(fam.items()):
  for a,b in combinations(sorted(tt,key=lambda t:t['id']),2):
   if a['morphology']['lakara']==b['morphology']['lakara']=='Lun':candidates[tuple(sorted([a['derivation']['recipe_id'],b['derivation']['recipe_id']]))].append((f,a,b))
 pq={(REC[0],REC[0]):26,(REC[1],REC[1]):9,(REC[0],REC[1]):8};selected=None
 for attempt in range(500):
  rr=rng('attempt:'+str(attempt));chosen=[];used=set();gc=Counter();cc=Counter()
  for pair,n in sorted(pq.items(),key=lambda x:len(candidates[x[0]])/x[1]):
   pool=list(candidates[pair]);rr.shuffle(pool);q=0
   for f,a,b in pool:
    if f in used or gc[gkey(a)]+2>gt[gkey(a)]:continue
    if any(cc[c]+v>target[c] for c,v in Counter([cell(a),cell(b)]).items()):continue
    chosen.extend([a,b]);used.add(f);gc[gkey(a)]+=2;cc.update([cell(a),cell(b)]);q+=1
    if q==n:break
   if q<n:break
  if len(chosen)!=86:continue
  chosenids={t['id'] for t in chosen};net=ProgressFlow();edges=[];counts=Counter(t['campaign']['root_family'] for t in chosen)
  for g,q in sorted(gt.items()):net.edge('s',('g',g),q-gc[g])
  fseq=sorted(fam);rr.shuffle(fseq)
  for rank,f in enumerate(fseq):
   tt=fam[f];g=gkey(tt[0]);assert len({gkey(t) for t in tt})==1
   net.edge(('g',g),('f',f),3-counts[f],0 if counts[f] else 1000+rank)
   pool=list(tt);rr.shuffle(pool)
   for t in pool:
    if t['id'] not in chosenids:edges.append((t,net.edge(('f',f),('c',cell(t)),1)))
  for c,q in sorted(target.items()):net.edge(('c',c),'t',q-cc[c])
  flow,cost=net.flow('s','t',154)
  if flow<154:continue
  selected=chosen+[t for t,e in edges if e[3]-e[1]];break
 assert selected is not None,'No feasible input-only subset within declared500 attempts'
 assert len(selected)==len({t['id'] for t in selected})==240
 assert Counter(cell(t) for t in selected)==Counter(target)
 assert Counter(t['dhatu']['gana'] for t in selected)==Counter(classes)
 sf=defaultdict(list)
 for t in selected:sf[t['campaign']['root_family']].append(t)
 pairtypes=Counter();pairrecipes=Counter();pairfamilies=defaultdict(set)
 for f,tt in sf.items():
  assert len(tt)<=3
  for a,b in combinations(tt,2):
   la,lb=a['morphology']['lakara'],b['morphology']['lakara'];cat='both_Lun' if la==lb=='Lun' else 'one_Lun' if 'Lun' in [la,lb] else 'different_non_Lun';pairtypes[cat]+=1;pairfamilies[cat].add(f)
   if cat=='both_Lun':pairrecipes['|'.join(sorted([a['derivation']['recipe_id'],b['derivation']['recipe_id']]))]+=1
 assert pairtypes['both_Lun']==43 and pairrecipes==Counter({'|'.join(k):v for k,v in pq.items()})
 # Keep each complete family together in a120-question transport, with seeded subset-sum.
 families=sorted(sf);rng('transport-families').shuffle(families);reachable={0:[]}
 for f in families:
  for n,ff in sorted(list(reachable.items()),reverse=True):
   z=n+len(sf[f])
   if z<=120 and z not in reachable:reachable[z]=ff+[f]
 chosenfamilies=set(reachable[120]);stages=[[t for f in families if (f in chosenfamilies)==(i==0) for t in sf[f]] for i in range(2)]
 Q.mkdir()
 for i,stage in enumerate(stages):rng('transport-order:'+str(i)).shuffle(stage);assert len(stage)==120;atomic_json(Q/f'chunk-{i+1:02}.tasks.json',stage)
 selected=sum(stages,[]);atomic_json(Q/'tasks.json',selected)
 eligiblepairfamilies={str(k):len({x[0] for x in v}) for k,v in candidates.items()}
 plan=dict(created_at=now(),panel='five-d-pilot-08-astra-pair',fixed_n=240,subset_of_fixed_primary_n=2400,source_tasks_sha256=sha(P/'tasks.json'),seed=SEED,successful_first_feasible_attempt=attempt,search_attempt_limit=500,phase='confirm_64k',effort='xhigh',max_output_tokens=65536,provider='OpenAI',policy='oracle-policy-20',adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),selection_script_sha256=sha(Path(__file__)),cell_counts=target,gana_counts=classes,recipe_counts=dict(Counter(t['derivation']['recipe_id'] for t in selected)),lakara_counts=dict(Counter(t['morphology']['lakara'] for t in selected)),prayoga_counts=dict(Counter(t['morphology']['prayoga'] for t in selected)),curadi_lun=3,curadi_non_lun=11,family_count=len(sf),max_questions_per_family=3,family_load_histogram=dict(Counter(len(tt) for tt in sf.values())),pair_counts=dict(pairtypes),pair_families={k:len(v) for k,v in pairfamilies.items()},Lun_pair_recipe_counts=dict(pairrecipes),eligible_parent_Lun_pair_families=eligiblepairfamilies,selection='First feasible seeded input-only selection of43distinct-family aorist pairs (26ordinary-intensive,9luk-intensive,8mixed), followed by integral exact joint/class-margin matching. Prefer one additional non-Lun question in these families, then seeded ranked control families, cap3. All22san aorists are single-aorist-family observations: no san-involving repeated-Lun pair exists in this primary allocation. No results, output lengths, prior errors or refusals are used.',representativeness='All42parent joint cells and all10classes supported, rounding exact240 quotas; Curadi includes3Lun and11non-Lun. Selection enriches pairable roots and caps3: it is not a uniform probability sample. Marginal weights cannot remove within-cell family-selection differences; report raw plus prespecified coarse/joint calibrated descriptive cost/completion, never claim design-unbiased accuracy or covariance.',purpose='Estimate cost, completion, provider ordering and repeated-Lun covariance at common65536 before any separately approved final evaluation. Whole-family uncertainty cannot certify transfer to up-to8forms/root or unobserved san pair classes.',analysis_hold='BothAstra120and allsixOpus400must settle before aggregate analysis. Paired240metrics do not replace Opus2400primary. No interim stopping or outcome-based additions.',transport='Two120chunks, complete selected families kept together; purely financial order fixed before answers, second afterfirstsettlement andfinancialgate.',paid_calls=0,final_n=None,benchmark_ready=False)
 atomic_json(Q/'plan.json',plan)
 audit=validate(selected,'development',allowed_families=set(sf));audit.update(exact_parent_task_metadata=True,all42joint_cells_supported=True,all10classes_supported=True,all10lakaras_supported=True,source_policy_hash=sha(OUT.parent/'oracle-policy-20.json'),no_extra_unique_questions=True,no_model_answers_read=True)
 pm={t['id']:t for t in ts};assert all(t==pm[t['id']] for t in selected)
 atomic_json(Q/'audit.json',audit)
 atomic_json(Q/'transport-plan.json',dict(fixed_n=240,chunks=[dict(order=i+1,n=120,tasks_path=str(Q/f'chunk-{i+1:02}.tasks.json'),sha256=sha(Q/f'chunk-{i+1:02}.tasks.json'),ids=[t['id'] for t in rows]) for i,rows in enumerate(stages)],families_disjoint_between_chunks=True,all_before_answers=True,no_interim_score_analysis=True))
 atomic_json(Q/'manifest.json',dict(created_at=now(),tasks_digest=digest(selected),files={name:dict(sha256=sha(Q/name),bytes=(Q/name).stat().st_size) for name in ['tasks.json','plan.json','audit.json','transport-plan.json','chunk-01.tasks.json','chunk-02.tasks.json']},parent_tasks_sha256=sha(P/'tasks.json'),n=240,paid_calls=0))
 print(json.dumps({k:plan[k] for k in ['successful_first_feasible_attempt','family_count','family_load_histogram','pair_counts','pair_families','Lun_pair_recipe_counts','recipe_counts','gana_counts']},indent=2))
 status('Pilot08 paired subset prepared','Fixed240same-input Astra questions preserve every joint cell and class, with43independent-family repeated-aorist pairs and Curadi aorist support. No answers read or paid calls.')
if __name__=='__main__':main()
