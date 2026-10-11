"""Paired development performance, missingness, cost and future-design sensitivities."""
from __future__ import annotations
import json,math
from collections import Counter,defaultdict
import numpy as np
from misc.vp_5d_prepare_04 import ROOT,OUT,atomic_json,now,sha,status
from misc.vp_5d_metrics import summarize,completed
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_analyze_06 import ratio
from misc import vp_campaign_candidates as old

def cell(r):
 t=r['task'];m=t['morphology'];return '|'.join((t['derivation']['recipe_id'],m['lakara'],m['prayoga']))
def usage_cost(r):
 u=r['raw_batch_result']['response']['body']['usage'];assert not u.get('input_tokens_details',{}).get('cached_tokens',0)
 return (u['input_tokens']*5+u['output_tokens']*25)/1e6

def forecast(rows,target):
 counts=Counter(cell(r) for r in rows);assert set(target)<=set(counts);n=sum(target.values());cs=defaultdict(lambda:np.zeros(5));cost=0
 for r in rows:
  w=target[cell(r)]/counts[cell(r)];c=int(completed(r));s=int(bool(r['is_correct']));cs[r['task']['campaign']['root_family']]+=w*np.array([s,c*s,c,1,usage_cost(r)]);cost+=w*usage_cost(r)
 values=np.array(list(cs.values()));g=len(values);boot=np.random.default_rng(202610070910).multinomial(g,[1/g]*g,10000);total=values.sum(0)
 return dict(standardization='Fixed target recipe x exact lakara x voice cells. No adjustment for changed class or eligible-family composition.',cells=len(target),minimum_observed_cell=min(counts[c] for c in target),all_requests=ratio(values,0,3,boot),usable_completed=ratio(values,1,2,boot),completion_rate=total[2]/total[3],missing_response_bounds=[total[1]/total[3],(total[1]+total[3]-total[2])/total[3]],mean_cost_usd=cost/n,cost_bootstrap=ratio(values,4,3,boot),warning='Costs and dependence are development extrapolations at the existing16384-token cap. No observed final cost, guaranteed sub1pp precision, or qualified final membership.')

def main():
 es={e.code:e for e in old.load_entries()};ap=ROOT/'benchmarks/iterative-goal-20261006/jobs/astra-five-d-pilot-04-pair/results.json';op=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-04/results.json';araw=json.loads(ap.read_text());oraw=json.loads(op.read_text());a=[r for r in araw if not current_issue(r['task'],es)];om={r['task']['id']:r for r in oraw};o=[om[r['task']['id']] for r in a];joint=[r for r in a if completed(r) and completed(om[r['task']['id']])];totalcost=sum(map(usage_cost,araw));assert abs(totalcost-103.942430)<1e-8
 groups=defaultdict(list)
 for r in a:
  t=r['task'];m=t['morphology']
  for k,v in [('recipe',t['derivation']['recipe_id']),('lakara',m['lakara']),('voice',m['prayoga']),('gana',t['dhatu']['gana']),('joint',cell(r))]:groups[k+'::'+v].append(r)
 strata={k:{'summary':summarize(rs),'mean_cost_usd':sum(map(usage_cost,rs))/len(rs),'mean_output_tokens':sum(x['raw_batch_result']['response']['body']['usage']['output_tokens'] for x in rs)/len(rs)} for k,rs in groups.items()}
 p=json.loads((OUT/'pilot-06.revision-01.plan.json').read_text());future=forecast(a,p['cell_counts']);base=forecast(a,Counter(cell(r) for r in a));c=future['completion_rate'];pc=future['usable_completed']['accuracy'];pa=future['all_requests']['accuracy'];ncost=future['mean_cost_usd'];budget=2000-713.027475
 projections=[]
 witnesses=json.loads((OUT/'pilot-06.scale-analysis-policy14.json').read_text())['balanced_designs']
 for n in [2400,2880,3360,3840,4800,6000]:
  w=next((w for w in witnesses if w['n']==n),None)
  wp=OUT/f'pilot-06.scale-witness-policy15-N{n}.json'
  if wp.exists():w=json.loads(wp.read_text())
  q=dict(n=n,projected_cost_usd=n*ncost,projected_openai_total_usd=713.027475+n*ncost,headroom_before_capcheck_or_other_work=budget-n*ncost,projected_usable=n*c,iid_se_all_pp=100*math.sqrt(pa*(1-pa)/n),iid_se_completed_pp=100*math.sqrt(pc*(1-pc)/(n*c)))
  if w and w.get('feasible'):
   f=w['family_pair_correlation_multiplier'];q.update(family_factor=f,assumed_common_rho_sensitivity={str(rho):{'all_se_pp':100*math.sqrt(pa*(1-pa)/n*(1+f*rho)),'completed_se_pp':100*math.sqrt(pc*(1-pc)/(n*c)*(1+f*rho))} for rho in [0,.05,.1,.15,.2,.3,.4]},largest_common_rho_for_both_sub1pp=min((.0001*n/(pa*(1-pa))-1)/f,(.0001*n*c/(pc*(1-pc))-1)/f))
  projections.append(q)
 correct_trunc=[dict(id=r['task']['id'],answer=r['answer'],status=r['status'],truncated=r['truncated'],current_scope=not current_issue(r['task'],es)) for r in araw if r['is_correct'] and not completed(r)]
 stats=json.loads((OUT/'pilot-04.analysis-opus-astra.json').read_text());metrics={k:v['current_scope'] for k,v in stats['models'].items()}
 out=dict(created_at=now(),policy='oracle-policy-15',shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),sources={'astra':sha(ap),'opus':sha(op)},same_eligible_inputs=len(a),paired=stats['paired'],raw_astra=summarize(araw),current_astra=summarize(a),current_opus=summarize(o),canonical_correct_but_truncated_rows=correct_trunc,metrics=metrics,strata=strata,observed_all480_cost_usd=totalcost,observed_mean_cost_usd=totalcost/480,current_mean_cost_usd=sum(map(usage_cost,a))/len(a),current_mix_forecast_check=base,revised45percent_lun10percent_passive_forecast=future,fixed_n_projections=projections,precision_caveat='Completed-ratio sensitivity uses expected usable N and an assumed common family rho. It does not identify final sandwich variance: repeated-Lun covariance and within-family missingness remain unmeasured for Astra.',cap_sensitivity='Fifty current eligible responses truncate at16384; one nevertheless has a correct parsed answer and remains missing in usable metrics. A higher-cap paired diagnostic can characterize censoring, but is not a replacement or a second primary score. No claim that increasing the cap leaves cost or accuracy unchanged.',budget_caveat='Uses coordinator-provided cumulative settled OpenAI713.027475, before any new cap diagnostic or other-track reserve. Only parent can authorize protected-funding changes. Raw worst-case reservations remain stagewise.',benchmark_ready=False,no_final_membership_selected=True,no_heldout_answers_read=True,paid_calls=0)
 atomic_json(OUT/'pilot-04.astra-cost-precision-review.json',out)
 print(json.dumps({'current_astra':out['current_astra'],'future':future,'projections':projections},indent=2));status('Astra pairing and release-cost sensitivity complete','Current policy15 pairs469questions: Astra304/419 usable versus Opus396/468. Fifty Astra truncations require missingness and cap sensitivity. Joint-cell45%-aorist cost and precision projections are saved; fixedN and final membership remain unset.')
if __name__=='__main__':main()
