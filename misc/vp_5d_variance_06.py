"""4800 allocation-specific Astra variance sensitivity, development moments only."""
from __future__ import annotations
import json,math
from collections import Counter,defaultdict
import numpy as np
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,sha,now,status
from misc.vp_5d_metrics import completed
from misc.vp_5d_audit_03 import current_issue
from misc import vp_campaign_candidates as old

def cell(r):
 t=r['task'];m=t['morphology'];return '|'.join((t['derivation']['recipe_id'],m['lakara'],m['prayoga']))
def coarse(c):
 r,l,v=c.split('|');return '|'.join((r,'Lun' if l=='Lun' else 'other',v))
def pairtype(a,b):
 la=a.split('|')[1];lb=b.split('|')[1];return 'both_Lun' if la==lb=='Lun' else 'one_Lun' if 'Lun' in [la,lb] else 'different_non_Lun'

def analyze(rows,w,diagnostics,fine,smooth):
 groups=defaultdict(list)
 for r in rows:groups[cell(r) if fine else coarse(cell(r))].append(r)
 target=w['cell_counts'];n=w['n'];g=w['distinct_families'];paircounts=w['unordered_within_family_cell_pair_counts'];prob={};denoms={}
 # Four categorical states preserve the parsed-correct truncated observation.
 states=[(1,1),(0,1),(1,0),(0,0)]
 for cellname in target:
  rr=groups[cellname if fine else coarse(cellname)];cnt=Counter((int(bool(r['is_correct'])),int(completed(r))) for r in rr);prior=.5 if smooth else 0;den=len(rr)+4*prior
  prob[cellname]=np.array([(cnt[s]+prior)/den for s in states]);denoms[cellname]=len(rr)
 y=np.array([s for s,c in states]);comp=np.array([c for s,c in states]);uc=y*comp
 total=sum(q*prob[c] for c,q in target.items());C=float(total@comp/n);P=float(total@uc/(n*C));A=float(total@y/n)
 out={}
 for metric in ['recorded_all_correct','completed_ratio_influence']:
  zz=y if metric=='recorded_all_correct' else comp*(y-P)/C
  means={c:float(p@zz)-(A if metric=='recorded_all_correct' else 0) for c,p in prob.items()}
  variances={c:float(p@(zz*zz)-(p@zz)**2) for c,p in prob.items()}
  independent=sum(target[c]*variances[c] for c in target)
  meansq=sum(target[c]*means[c]**2 for c in target)+sum(2*x['pairs']*means[x['cell_a']]*means[x['cell_b']] for x in paircounts)
  assert meansq>=-1e-8
  cats=Counter();coeff=Counter()
  for x in paircounts:
   a=x['cell_a'];b=x['cell_b'];cat=pairtype(a,b);cats[cat]+=x['pairs'];coeff[cat]+=2*x['pairs']*math.sqrt(variances[a]*variances[b])
  observed=diagnostics[metric]['coarse'];scenarios=[]
  for label in ['point','upper95']:
   rho={cat:observed[cat]['correlation'] if label=='point' else observed[cat]['bootstrap_percentile95'][1] for cat in ['one_Lun','different_non_Lun']}
   for rl in [0,.1,.2,.3,.4,.5]:
    cr={**rho,'both_Lun':rl};v=independent+sum(coeff[k]*cr[k] for k in coeff);sandwich=(v+meansq)*g/(g-1)
    # Pair-type correlations must describe a positive semidefinite block matrix.
    # Check every possible split through max family cap (conservative supersets).
    feasible=True
    for l in range(1,w['aorist_per_family_cap']+1):
     for k in range(1,w['family_cap']-l+1):
      if (1+(l-1)*rl)*(1+(k-1)*rho['different_non_Lun'])+1e-9<l*k*rho['one_Lun']**2:feasible=False
    scenarios.append(dict(observed_pair_rho_assumption=label,unobserved_repeated_Lun_rho=rl,rhos=cr,valid_for_every_possible_family_block=feasible,conditional_sampling_se_pp=100*math.sqrt(v)/n,expected_unstratified_sandwich_se_pp=100*math.sqrt(sandwich)/n))
  known=independent+meansq+sum(coeff[k]*observed[k]['correlation'] for k in ['one_Lun','different_non_Lun'])
  threshold=(.0001*n*n*(g-1)/g-known)/coeff['both_Lun']
  out[metric]=dict(independent_variance_sum=independent,allocation_mean_squared_sum=meansq,pair_counts=dict(cats),pair_covariance_coefficients=dict(coeff),scenarios=scenarios,max_repeated_Lun_rho_for_expected_sandwich_sub1pp_at_observed_point_rhos=threshold)
 return dict(moment_cells='exact recipe x tense x voice' if fine else 'recipe x aorist/other x voice',moment_smoothing='Dirichlet0.5 per four response states' if smooth else 'empirical proportions',smallest_observed_cell=min(denoms.values()),projected_completion=C,projected_all_accuracy=A,projected_usable_accuracy=P,estimates=out)

def main():
 es={e.code:e for e in old.load_entries()};p=ROOT/'benchmarks/iterative-goal-20261006/jobs/astra-five-d-pilot-04-pair/results.json';rs=[r for r in json.loads(p.read_text()) if not current_issue(r['task'],es)];wp=OUT/'pilot-06.scale-witness-policy15-N4800.json';w=json.loads(wp.read_text());dp=OUT/'pilot-06.cross-panel-dependence.json';d=json.loads(dp.read_text())['models']['astra']['residual_diagnostics']
 cases={f'{"fine" if fine else "coarse"}_{"smoothed" if smooth else "empirical"}':analyze(rs,w,d,fine,smooth) for fine in [True,False] for smooth in [False,True]}
 out=dict(created_at=now(),policy='oracle-policy-15',shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),source_sha256=sha(p),witness_sha256=sha(wp),dependence_sha256=sha(dp),n=4800,distinct_families=w['distinct_families'],cases=cases,method='Use cell-specific observed four-state correctness/completion probabilities. Completed-score influence is C_i(Y_i-P)/mean(C); it includes missing rows. Sum within-cell variances plus twice each aggregate within-family cell-pair covariance. Assign observed coarse residual correlations separately to mixed-Lun and different-nonLun pairs; sweep unobserved repeated-Lun correlation. Expected unstratified sandwich additionally includes squared family mean contributions from the exact grammar allocation and the G/(G-1) correction.',limitations=['No final model answers or final membership selected. This is a single input-only aggregate flow witness.','Correlations need not transport across new families, same-tense repetition, class mix or task loads. Repeated-Lun Astra covariance is unidentified.','Fitted fine cell probabilities are sparse and have zero-variance cells; coarse and Dirichlet-smoothed analyses show that sensitivity rather than concealing it.','Bootstrap upper endpoints are separate marginal intervals, not a joint95% confidence region.','Expected sandwich is a scenario, not a promised realization or a replacement for the frozen final analyzer.','Some very-low repeated-Lun rho scenarios are not positive-semidefinite for every potential family block and are flagged, not claimed coherent generative models.'],no_final_membership_selected=True,no_heldout_answers_read=True,paid_calls=0)
 atomic_json(OUT/'pilot-06.astra-allocation-variance.json',out)
 print(json.dumps({k:{metric:{'max_rho':e['max_repeated_Lun_rho_for_expected_sandwich_sub1pp_at_observed_point_rhos'],'rho02':next(z['expected_unstratified_sandwich_se_pp'] for z in e['scenarios'] if z['observed_pair_rho_assumption']=='point' and z['unobserved_repeated_Lun_rho']==.2),'rho03':next(z['expected_unstratified_sandwich_se_pp'] for z in e['scenarios'] if z['observed_pair_rho_assumption']=='point' and z['unobserved_repeated_Lun_rho']==.3)} for metric,e in case['estimates'].items()} for k,case in cases.items()},indent=2));status('Astra allocation-specific precision assessed','The4800-family allocation now uses actual Astra cell variance, completion loss and observed cross-tense covariance, with repeated-Lun covariance left as a sensitivity. FinalN is not frozen; uncertainty and shared-budget headroom remain material.')
if __name__=='__main__':main()
