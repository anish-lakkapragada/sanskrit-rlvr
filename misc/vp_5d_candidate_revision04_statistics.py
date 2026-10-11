"""Allocation cost/variance scenarios using only named development results."""
import json,math
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_metrics import completed,summarize
from misc.vp_5d_astra04_review import forecast
from misc.vp_5d_dependence_06 import analyze as dependence
from misc.vp_5d_variance_06 import analyze as variance
from misc import vp_campaign_candidates as old
D=OUT/'candidate-4800/revision-04'
def main():
 es={e.code:e for e in old.load_entries()};rows={};paths={}
 for key,name in [('astra','astra-five-d-pilot-04-pair'),('opus','opus-five-d-pilot-06')]:
  p=ROOT/'benchmarks/iterative-goal-20261006/jobs'/name/'results.json';raw=json.loads(p.read_text());rs=[r for r in raw if not current_issue(r['task'],es)]
  for r in rs:r['_panel']='04' if key=='astra' else '06'
  rows[key]=rs;paths[key]=dict(path=str(p),sha256=sha(p),current_n=len(rs),excluded_ids=[r['task']['id'] for r in raw if current_issue(r['task'],es)])
 plan=json.loads((D/'sampling-plan.json').read_text());m=json.loads((D/'manifest.json').read_text());fs=m['family_statistics'];dep=dependence(rows['astra']);fc=forecast(rows['astra'],plan['cell_counts']);w=dict(n=4800,cell_counts=plan['cell_counts'],distinct_families=fs['distinct_families'],family_cap=8,aorist_per_family_cap=5,unordered_within_family_cell_pair_counts=fs['unordered_within_family_cell_pair_counts'])
 scenarios={f'{"fine" if fine else "coarse"}_{"smoothed" if sm else "empirical"}':variance(rows['astra'],w,dep['residual_diagnostics'],fine,sm) for fine in [True,False] for sm in [False,True]}
 common={};pbase=sum(completed(r) and r['is_correct'] for r in rows['opus'])/sum(completed(r) for r in rows['opus']);completion=sum(completed(r) for r in rows['opus'])/len(rows['opus']);factor=fs['family_pair_correlation_multiplier']
 for rho in [0,.05,.1,.15,.2,.3,.4]:common[str(rho)]=dict(usable_se_pp=100*math.sqrt(pbase*(1-pbase)/(4800*completion)*(1+factor*rho)),assumed_common_rho=rho)
 cost=4800*fc['mean_cost_usd'];out=dict(created_at=now(),policy='oracle-policy-18',sources=paths,candidate_manifest_sha256=sha(D/'manifest.json'),candidate_tasks_sha256=sha(D/'tasks.json'),family_statistics=fs,current_development_summaries={k:summarize(v) for k,v in rows.items()},astra_current_scope_dependence=dep,astra_revised_mixture_forecast=fc,astra_allocation_specific_variance_sensitivity=scenarios,opus_common_rho_sensitivity=common,opus_sensitivity_note='Uses audited pilot06 usable p and completion, with candidate family-load factor and assumed common correlations. This is not an empirical estimate of unseen candidate family covariance.',cost_projection=dict(n=4800,existing_16384_cap_mean_usd=fc['mean_cost_usd'],projected_primary_astra_cost_usd=cost,lifetime_baseline_before_diagnostic_usd=713.027475,projected_lifetime_before_diagnostic_usd=713.027475+cost,headroom_before_cap_diagnostic_or_other_spend_usd=2000-713.027475-cost,conditional_only=True,caveat='Expected cost only, before settled cap diagnostic and other work, contingent on documented reserve reallocation. Actual token usage can leave the fixed evaluation incomplete; cumulative provider caps do not change.'),limitations=['No candidate model answers exist or were accessed. Development evidence only.','Exact recipe×tense×voice standardization does not adjust class changes or unseen-family composition.','Astra repeated-Lun correlation is unidentified. The scenario grid is not a promised precision result.','Observed cap loss and a future cap change can alter cost, correctness and covariance; parent owns the diagnostic/protocol decision.','Both iid and observed family-sandwich SE must pass at the fixed approved N for both references; no score-dependent membership or extension.'],paid_calls=0,final_n_approved=False,final_membership_approved=False)
 atomic_json(D/'cost-variance-assessment.json',out)
 print(json.dumps(dict(current_summaries=out['current_development_summaries'],cost=out['cost_projection'],family_count=fs['distinct_families'],family_factor=factor,astra_rho02={k:{metric:next(z['expected_unstratified_sandwich_se_pp'] for z in e['scenarios'] if z['observed_pair_rho_assumption']=='point' and z['unobserved_repeated_Lun_rho']==.2) for metric,e in v['estimates'].items()} for k,v in scenarios.items()}),indent=2))
 status('Revision 04 precision and cost assessed','Updated candidate family covariance and cost scenarios using policy 18 development scope. These remain conditional forecasts; the cap diagnostic, reserve allocation and final protocol are coordinator decisions.')
if __name__=='__main__':main()
