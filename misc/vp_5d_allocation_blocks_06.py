"""Input-only block-preference allocation alternatives; no final identities exported."""
import json,random,math
from collections import Counter,defaultdict
from misc.vp_5d_prepare_04 import OUT,atomic_json,now,status
from misc.vp_5d_release_feasibility import MinCost,apportion

def alternative(rows,p,seed,fraction):
 n=4800;cap=8;lcap=5;rng=random.Random(seed);quota=apportion(p['cell_counts'],n);gq=apportion(p['gana_counts'],n)
 net=MinCost();fe={};ce=[];block_edges=[];medium=n*cap*cap+1;large=n*(medium+cap*cap)+1
 for g,q in gq.items():net.edge('s',('g',g),q)
 preference_counts=Counter()
 for i,row in enumerate(rows):
  mask=row['eligible_person_number_masks'];nested_lun=any(c.endswith('|Lun|Kartari') and not c.startswith('desiderative|') for c in mask);pref='Lun' if nested_lun and rng.random()<fraction else 'other';preference_counts[row['gana']+'|'+pref]+=1
  f=('f',i);fe[i]=[net.edge(('g',row['gana']),f,1,0)]+[net.edge(('g',row['gana']),f,1,large+2*j-1) for j in range(2,cap+1)]
  for block,bcap in [('Lun',lcap),('other',cap)]:
   # Off-block assignments are minimized after maximizing represented families.
   e=net.edge(f,('b',i,block),bcap,0 if block==pref else medium);block_edges.append((i,block,pref,e))
  for la in sorted({c.split('|')[1] for c in mask if c in quota}):net.edge(('b',i,'Lun' if la=='Lun' else 'other'),('fl',i,la),lcap if la=='Lun' else 1)
  for c,mask in mask.items():
   if c in quota:ce.append((i,c,net.edge(('fl',i,c.split('|')[1]),('c',c),min(cap,mask.bit_count()))))
 for c,q in quota.items():net.edge(('c',c),'t',q)
 flow=net.flow('s','t',n)[0];assert flow==n
 occupied=defaultdict(Counter)
 for i,c,e in ce:
  k=e[3]-e[1]
  if k:occupied[i][c]+=k
 loads=Counter(sum(v.values()) for v in occupied.values());paircells=Counter();pairtypes=Counter();blockloads=Counter();lunloads=Counter()
 for cells in occupied.values():
  ll=sum(k for c,k in cells.items() if '|Lun|' in c);nn=sum(cells.values())-ll;blockloads[(ll,nn)]+=1
  if ll:lunloads[ll]+=1
  cc=sorted(cells)
  for a,c in enumerate(cc):
   paircells[c,c]+=cells[c]*(cells[c]-1)//2
   for d in cc[a+1:]:paircells[c,d]+=cells[c]*cells[d]
 for (c,d),v in paircells.items():
  a='|Lun|' in c;b='|Lun|' in d;pairtypes['both_Lun' if a and b else 'one_Lun' if a or b else 'different_non_Lun']+=v
 assert all(e[3]-e[1]<=9 for i,c,e in ce)
 o=dict(n=n,seed=seed,preference_fraction_of_nested_aorist_capable=fraction,family_cap=cap,aorist_per_family_cap=lcap,non_aorist_same_lakara_per_family_cap=1,feasible=True,distinct_families=len(occupied),family_load_histogram=dict(loads),family_pair_correlation_multiplier=sum(k*k*v for k,v in loads.items())/n-1,cell_counts=quota,gana_counts=gq,unordered_within_family_cell_pair_counts=[dict(cell_a=c,cell_b=d,pairs=k) for (c,d),k in sorted(paircells.items()) if k],pair_type_counts=dict(pairtypes),family_Lun_other_load_histogram={f'{l}/{o}':k for (l,o),k in sorted(blockloads.items())},aorist_family_load_histogram=dict(lunloads),distinct_aorist_families=sum(lunloads.values()),repeated_aorist_questions_beyond_one_per_family=sum((k-1)*v for k,v in lunloads.items()),families_with_mixed_tense_blocks=sum(v for (l,o),v in blockloads.items() if l and o),off_preference_assignments=sum(e[3]-e[1] for i,b,pref,e in block_edges if b!=pref),input_preference_counts=dict(preference_counts),objective='Same exact global joint and class quotas, max8 forms and5aorists per family, non-aorist lakaras unique. Maximize distinct families, then minimize assignments outside a seeded input-eligibility block preference, then balance total loads. This heuristic is not guaranteed globally minimal mixed-pair covariance.',balanced_PN_supply=True,PN_proof='Every exact family/recipe/tense/voice cell carries<=9 assignments with all9 PN choices; global cyclic PN within consecutive cell groups preserves uniqueness and balance.',no_final_membership_exported=True,no_model_answers_read=True)
 return o

def main():
 rows=json.loads((OUT/'pilot-06.scale-supply-policy15.json').read_text())['rows'];p=json.loads((OUT/'pilot-06.revision-01.plan.json').read_text())
 for frac,seed in [(1.0,202610070915),(.95,202610070916)]:
  status('Testing input-only tense-block allocation',f'Preserving all4800 joint-cell and class quotas while discouraging mixed aorist/non-aorist pairs within roots; seeded nested-aorist block preference fraction{frac}. No final membership selected.')
  out=alternative(rows,p,seed,frac);name=f'pilot-06.block-allocation-{str(frac).replace(".","_")}.json';atomic_json(OUT/name,out);print(json.dumps({k:out[k] for k in ['distinct_families','family_pair_correlation_multiplier','pair_type_counts','families_with_mixed_tense_blocks','distinct_aorist_families','off_preference_assignments']}),flush=True)
if __name__=='__main__':main()
