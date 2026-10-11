"""Compare existing input-only aggregate allocations under the same Astra scenarios."""
import json
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha
from misc.vp_5d_variance_06 import analyze,pairtype
from misc.vp_5d_audit_03 import current_issue
from misc import vp_campaign_candidates as old

def main():
 es={e.code:e for e in old.load_entries()};source=ROOT/'benchmarks/iterative-goal-20261006/jobs/astra-five-d-pilot-04-pair/results.json';rows=[r for r in json.loads(source.read_text()) if not current_issue(r['task'],es)];dp=OUT/'pilot-06.cross-panel-dependence.json';d=json.loads(dp.read_text())['models']['astra']['residual_diagnostics'];reports={}
 for filename in ['pilot-06.scale-witness-policy15-N4800.json','pilot-06.block-allocation-1_0.json','pilot-06.block-allocation-0_95.json']:
  p=OUT/filename;w=json.loads(p.read_text());pairs=Counter()
  for x in w['unordered_within_family_cell_pair_counts']:pairs[pairtype(x['cell_a'],x['cell_b'])]+=x['pairs']
  cases={f'{"fine" if fine else "coarse"}_{"smoothed" if smooth else "empirical"}':analyze(rows,w,d,fine,smooth) for fine in [True,False] for smooth in [False,True]};reports[filename]={'witness_sha256':sha(p),'pairs':dict(pairs),'distinct_families':w['distinct_families'],'cases':cases};print(filename,dict(pairs))
  for case,v in cases.items():
   print(case,{m:{'rho_limit':round(e['max_repeated_Lun_rho_for_expected_sandwich_sub1pp_at_observed_point_rhos'],4),'rho02':round(next(s['expected_unstratified_sandwich_se_pp'] for s in e['scenarios'] if s['observed_pair_rho_assumption']=='point' and s['unobserved_repeated_Lun_rho']==.2),4),'rho03':round(next(s['expected_unstratified_sandwich_se_pp'] for s in e['scenarios'] if s['observed_pair_rho_assumption']=='point' and s['unobserved_repeated_Lun_rho']==.3),4)} for m,e in v['estimates'].items()})
 atomic_json(OUT/'pilot-06.block-allocation-variance.json',dict(created_at=now(),source_sha256=sha(source),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),dependence_sha256=sha(dp),reports=reports,analytic_check='Equal-probability zero-covariance toy allocation matches iid and G/(G-1)-adjusted sandwich moments exactly.',no_final_membership_selected=True,warning='Allocation changes the family composition within grammar cells relative to paired calibration. Empirical Astra repeated-Lun dependence remains unidentified; scenarios are not precision guarantees. No estimator or gate was changed.'))
if __name__=='__main__':main()
