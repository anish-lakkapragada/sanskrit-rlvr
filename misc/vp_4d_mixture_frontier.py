#!/usr/bin/env python3
"""Optimistic aggregate allocation bounds, never a final question selection."""
from collections import Counter,defaultdict
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,write,now,sha,load_entries,name,source_rows,row_identity
from misc.vp_4d_pilot02 import metadata_issue
from misc.vp_4d_pilot03 import CELLS03,marker_groups,eligible
from misc.vp_4d_pilot04 import local_issue
from misc.vp_4d_pilot05 import short
from misc.vp_4d_search03 import status
sys.path.insert(0,str(OUT/'_solver_deps'));import highspy
RATES={
 'prespecified':{'adanta_short_Lun':56/64,'adanta_other_Lun':56/64,'adanta_short_other':56/64,'adanta_other_other':56/64,'dhvam':47/48,'background03':1.},
 'exploratory_refinement':{'adanta_short_Lun':9/11,'adanta_other_Lun':10/13,'adanta_short_other':14/17,'adanta_other_other':23/23,'dhvam':47/48,'background03':1.},
 'fresh_confirmation_refinement':{'adanta_short_Lun':12/13,'adanta_other_Lun':10/13,'adanta_short_other':31/39,'adanta_other_other':23/23,'dhvam':47/48,'background03':1.}}

def main():
 status('Mixture feasibility frontier','Quantifying optimistic grammar-cell allocation bounds across sample sizes, family caps and class shares. These are sensitivity analyses, not estimates of unseen-item performance or final membership.')
 es={e.code:e for e in load_entries()};groups=marker_groups(es);rows={}
 for r in json.load(open(OUT/'pilot-04.candidate-metadata.json')):
  if r['split']!='test' or metadata_issue(r,es):continue
  label='dhvam'
  if r['cell']=='adanta_curadi':label='adanta_'+('short' if short(es[r['code']]) else 'other')+('_Lun' if r['lakara']=='Lun' else '_other')
  rows[row_identity(r,es)]={**r,'cell':label,'gana':name(es[r['code']].dhatu.gana)}
 for r in source_rows(es):
  if r['split']!='test' or r['prayoga']!='Kartari' or metadata_issue(r,es):continue
  shallow={'dhatu':{'code':r['code']},'morphology':{k:r[k] for k in ['lakara','prayoga','purusha','vacana']},'campaign':{'trace_rule_ids':r['rules']}}
  if local_issue(shallow):continue
  if not any(eligible(r,c,es,groups) for c in CELLS03):continue
  key=row_identity(r,es)
  if key not in rows:rows[key]={**r,'cell':'background03','gana':name(es[r['code']].dhatu.gana)}
 capacity=Counter((r['family'],r['gana'],r['lakara'],r['cell']) for r in rows.values());keys=list(capacity)
 supply={cell:dict(tuples=sum(n for k,n in capacity.items() if k[3]==cell),families=len({k[0] for k in keys if k[3]==cell}),gana=dict(Counter(r['gana'] for r in rows.values() if r['cell']==cell))) for cell in RATES['prespecified']}
 def solve(n,cap,curadi_cap,spread,model,substantial=False):
  h=highspy.Highs();h.setOptionValue('output_flag',False);h.setOptionValue('threads',2)
  xs=[h.addVariable(lb=0,ub=capacity[k]) for k in keys]
  maps={name:defaultdict(list) for name in ['family','gana','lakara','cell']}
  for k,x in zip(keys,xs):
   for i,field in enumerate(maps):maps[field][k[i]].append(x)
  h.addConstr(h.qsum(xs)==n)
  if cap is not None:
   for vs in maps['family'].values():h.addConstr(h.qsum(vs)<=cap)
  h.addConstr(h.qsum(maps['gana']['Curadi'])<=n*curadi_cap)
  if spread:
   # Illustrative floors, not user mandates; also report unrestricted bounds.
   for vs in maps['gana'].values():h.addConstr(h.qsum(vs)>=1)
   for vs in maps['lakara'].values():h.addConstr(h.qsum(vs)>=n*.01)
   h.addConstr(h.qsum(maps['lakara']['Lun'])<=n*.25)
   if substantial:
    ys=[]
    for vs in maps['gana'].values():
     y=h.addVariable(lb=0,ub=1,type=highspy.HighsVarType.kInteger);ys.append(y)
     h.addConstr(h.qsum(vs)>=n*.05*y)
    h.addConstr(h.qsum(ys)>=5)
  h.minimize(h.qsum(RATES[model][k[3]]*x for k,x in zip(keys,xs)))
  sol=h.getSolution();result=dict(n=n,family_cap=cap,curadi_share_cap=curadi_cap,spread_floors=spread,five_classes_at_least_five_percent=substantial,evidence_model=model,status=str(h.getModelStatus()))
  if 'Optimal' not in str(h.getModelStatus()):return result
  vv=[sol.col_value[int(x)] for x in xs]
  result.update(optimistic_accuracy_bound=sum(RATES[model][k[3]]*v for k,v in zip(keys,vv))/n,allocated_family_count=sum(sum(v for k,v in zip(keys,vv) if k[0]==fam)>1e-6 for fam in maps['family']),allocation_by_cell={cell:round(sum(v for k,v in zip(keys,vv) if k[3]==cell),6) for cell in maps['cell']},allocation_by_gana={g:round(sum(v for k,v in zip(keys,vv) if k[1]==g),6) for g in maps['gana']},allocation_by_lakara={la:round(sum(v for k,v in zip(keys,vv) if k[2]==la),6) for la in maps['lakara']})
  return result
 results=[]
 for n in [500,1000,1660]:
  for model in RATES:
   results.append(solve(n,None,1.,False,model))
   for cap in [3,6,10,None]:
    for share in [.5,.75,1.]:results.append(solve(n,cap,share,True,model))
   results.append(solve(n,None,1.,True,model,True))
   results.append(solve(n,6,1.,True,model,True))
 data=dict(created_at=now(),method='Aggregate allocation optimization over test metadata capacities by family/gana/lakara/grammar cell. Question counts are continuously relaxed; substantial-class coverage adds binary class selectors. No test model answers or per-question outcomes are loaded. Only aggregate allocations are saved; no final membership is selected.',reference_rates=RATES,reference_details={'adanta':'Pilot04 56/64 source-supported broad cell. Exploratory refinement uses post-hoc phonological/tense slices with n11,13,17,23. Fresh-confirmation refinement replaces only the short-vowel rates with pilot05: aorist 12/13 and non-aorist 31/39. The other-stem aorist rate 10/13 remains unconfirmed and post hoc. All rates have large uncertainty.','pilot05':'52 fresh tuples from 13 development families, 12 reused from pilot04. The non-aorist slice has estimated family-cluster SE 8.04 percentage points; transfer to 14 disjoint test families is unmeasured.','dhvam':'Pilot04 47/48, one supported error.','background03':'175/175 after shared restrictions and sensitivity omission of the unresolved stim disagreement. This is a point estimate, not certainty or a new independent measurement.'},diversity_interpretation='No numerical class cap, family cap or equal tense quota is attributed to the user. Unrestricted cases expose best concentration. Spread cases require at least one item in every available gana, >=1% in each lakara, <=25% aorist, and varying family/class caps. Additional substantial-coverage cases require >=5% in at least five classes. These are explicit sensitivity designs, not user mandates. Gana representation alone is weak diversity, so resulting class shares must be shown.',revision='r2 adds the fresh pilot05 short-vowel confirmation rates under policy11. Earlier r1 and exploratory artifacts remain unchanged; no frozen questions or prior results are modified.',supply=supply,total_test_metadata_tuples=len(rows),total_test_families=len({r['family'] for r in rows.values()}),results=results,limits=['The relaxation permits fractional tasks, so it is optimistic relative to an actual integer panel.','Fixed empirical cell rates are not known test accuracies. Adaptive discovery, small cells and family correlation make these bounds unsuitable for proving statistical impossibility.','The counted predicate union is not the full search universe. New source-clean mechanisms may change the frontier.','Metadata source scope is screened by the shared policy plus local exclusions; representative controls do not fully certify every potential test paradigm.'],generator_sha256=sha(__file__),worker_paid_calls=0,benchmark_ready=False)
 write(OUT/'pilot-04.mixture-frontier-r2.json',data)
 print('supply',json.dumps(supply))
 for r in results:
  if r['evidence_model']=='fresh_confirmation_refinement' and (r['n']==1000 or not r['spread_floors']):print({k:r[k] for k in ['n','family_cap','curadi_share_cap','spread_floors','status']},r.get('optimistic_accuracy_bound'))

if __name__=='__main__':main()
