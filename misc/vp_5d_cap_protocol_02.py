"""Prospective common65536 option and concise funding/precision handoff.

Uses saved completed-development aggregates only; no model result files or API.
"""
import json,math
import numpy as np
from misc.vp_5d_prepare_04 import OUT,ROOT,now,sha,atomic_json,status
from misc.vp_5d_variance_06 import coarse

def main():
    source=OUT/'cap-protocol-assessment-01.json';old=json.loads(source.read_text())
    target=OUT/'cap-protocol-assessment-02.json';assert not target.exists()
    candidate=OUT/'candidate-4800/revision-04';manifest=json.loads((candidate/'manifest.json').read_text())
    fs=manifest['family_statistics'];cells=old['standardized_diagnostic']['strata'];keys=sorted(cells);idx={c:i for i,c in enumerate(keys)}
    counts=np.array([cells[c]['candidate_n'] for c in keys]);weights=counts/4800
    M=np.diag(counts.astype(float))
    for pair in fs['unordered_within_family_cell_pair_counts']:
        i,j=idx[coarse(pair['cell_a'])],idx[coarse(pair['cell_b'])];n=pair['pairs']
        M[i,j]+=n;M[j,i]+=n
    Q=M-np.diag(counts)
    rng=np.random.default_rng(202610071128)
    draws=np.column_stack([rng.beta(cells[c]['high_correct']+.5,cells[c]['n']-cells[c]['high_correct']+.5,20000) for c in keys])
    p=(draws@weights)[:,None];moment_uncertainty=[]
    for completion in [1.,.95]:
        for metric in ['all','usable']:
            if metric=='all':mu=completion*(draws-p);v=completion*draws*(1-completion*draws)
            else:mu=draws-p;v=(draws*(1-p)**2+(1-draws)*p*p)/completion-mu*mu
            meansq=np.einsum('bi,ij,bj->b',mu,M,mu);vv=v@counts;sd=np.sqrt(v);coef=np.einsum('bi,ij,bj->b',sd,Q,sd)
            for rho in [.1,.2,.3,.4]:
                se=100*np.sqrt((vv+meansq+rho*coef)*929/928)/4800
                moment_uncertainty.append(dict(assumed_completion=completion,metric=metric,assumed_common_rho=rho,conditional_expected_se_pp_median=float(np.median(se)),conditional_expected_se_pp_interval95=np.quantile(se,[.025,.975]).tolist(),conditional_posterior_fraction_expected_se_above1pp=float(np.mean(se>=1))))
    mean=old['cost_forecast']['funding']['direct_coarse']['mean_per_task'];headroom=old['cost_forecast']['funding']['direct_coarse']['point_headroom'];remaining=old['cost_forecast']['remaining_openai'];caps=[]
    for cap in [16384,65536,128000]:
        oai=(1500*5+cap*25)/1e6;ant=(1500*2+cap*10)/1e6
        caps.append(dict(cap=cap,common_provider_ceiling=True,observed_Astra_runs_at_this_cap=60 if cap==128000 else 480 if cap==16384 else 0,
          observed_diagnostic_max_output_tokens=20577,cap_to_observed_max_ratio=cap/20577,
          maximum_reserved_input_tokens=1500,OpenAI_max_cost_per_task=oai,Anthropic_max_cost_per_task=ant,
          OpenAI_max_reservation_50=50*oai,OpenAI_max_reservation_100=100*oai,OpenAI_max_reservation_500=500*oai,
          Anthropic_max_reservation_500=500*ant,
          extra_fraction_at_cap_task_cost_exhausting_point_headroom=max(0,(remaining/4800-mean)/(oai-mean)) if oai>mean else None,
          largest_OpenAI_chunk_with_all_current_remaining_funds=math.floor(remaining/oai),
          largest_last_chunk_at_observed4800_mean_and_headroom=math.floor(headroom/(oai-mean)) if oai>mean else None,
          reservation_caveat='Ignores other protected reserves and pending work; not payment authorization. Last-chunk calculation is conditional on the forecast mean and unchanged remaining budget.'))
    common64=dict(option='Common65536 for both providers',recommendation='Preferred prospective compromise for a separately approved final protocol.',reason='Same ceiling for both references, four times the current primary cap, and3.185 times the largest observed128k diagnostic output. It reduces maximum-reservation pressure relative128k without choosing a cap to preserve low accuracy.',evidence_limit='No actual65536 runs are observed. Replaying the observed token lengths would clip none, but models may react to the ceiling and reruns are stochastic. This is not an equivalence test or a guarantee of completion, cost, or strongest-model79–81 attainment.',cost_transport='Use128k observed-usage forecasts only conditionally; mean and tail behavior at65536 are not measured.',verification='Freeze cap, effort, prompt, fixed N, input order, stage membership and analyzer before final calls. Analyze actual all/usable/bounds and both-model precision at that protocol.')
    recommendation='Prefer a common65536-token ceiling prospectively if the coordinator funds and approves the complete fixed evaluation. It improves parity and gives substantial margin over observed usage while reducing worst-case reservations. N4800 remains plausible at observed mean costs but is not guaranteed to finish within caps or meet sub1pp precision. Do not spend another small Opus cap probe solely to certify equivalence: it would not resolve the narrow target, tail risk or Astra family covariance. Await the complete fixed2400 Opus confirmation, then make the explicit funding/protocol decision; preserve failed or incomplete evaluation outcomes.'
    out={**old,'created_at':now(),'supersedes_recommendation_only_from':str(source),'source_assessment_sha256':sha(source),
      'assessment_script_sha256':sha(__import__('pathlib').Path(__file__)),
      'recommendation':recommendation,
      'protocol_options':[common64,dict(option='Common128000 for both providers',recommendation='Defensible higher ceiling if worst-case staging and tail exposure are accepted.',reason='The Astra diagnostic directly used128k and all60 completed; common ceiling keeps parity.',evidence_limit='Opus128k remains untested; performance and costs are not guaranteed. At current residual headroom, small final transport chunks are needed for full maximum-cost reservations.'),dict(option='Astra128000/Opus16384',recommendation='Useful sensitivity protocol; less attractive than a common higher ceiling for primary parity.',evidence_limit='Only Astra has highcap evidence. Distinct limits must be explicit and cannot establish strongest-model equivalence.'),dict(option='Common16384',recommendation='Do not treat as an adequately uncensored sole reference protocol.',reason='Astra omitted10/60 diagnostic answers; recovered subset accuracy4/10 differs from40/50 baseline usable. Completed-only accuracy masks informative missingness.')],
      'prospective_reservations':caps,
      'moment_uncertainty_sensitivity':dict(method='Independent Jeffreys Beta(.5,.5) per coarse correctness cell,20k draws; actual candidate cell-pair matrix, fixed assumed rho and completion. Descriptive model-based sensitivity, not a frequentist confidence bound or measured final precision.',results=moment_uncertainty),
      'additional_probe_decision':'No new paid request proposed. A second60-question cap comparison cannot certify a1pp target or identify within-family Astra dependence; it is not necessary solely to justify the common65536 ceiling.',
      'budget_as_of_coordinator_request':dict(OpenAI_settled=727.478150,Anthropic_settled=188.615334,Anthropic_fixed2400_confirmation_pending=True,no_partial_confirmation_data_read=True),
      'final_n_approved':False,'benchmark_ready':False}
    out['limitations'].append('All128k-derived65536 forecasts are conditional transport scenarios;65536 is not an observed experiment. Parent alone can version the currently16384 final runner protocol.')
    atomic_json(target,out)
    summary=dict(created_at=now(),source=str(target),source_sha256=sha(target),recommended_prospective_common_cap=65536,observed_highcap=128000,observed_diagnostic_n=60,observed_highcap_max_tokens=20577,observed_highcap_truncations=0,existing_lowcap_diagnostic_truncations=10,current_candidate_n=4800,fixed_final_n_approved=False,budget_as_of=out['budget_as_of_coordinator_request'],funding=old['cost_forecast']['funding'],remaining_openai=remaining,maximum_fundable_mean_per_question=remaining/4800,prospective_reservations=caps,observed_tail_support_limit='Bootstrap only sees outputs through20577; unseen tails can defeat the point forecast.',additional128k_tail_fraction_exhausting_point_headroom=old['cost_forecast']['unobserved_tail_sensitivity'][-1]['extra_tail_fraction_exhausting_point_headroom'],read_partial_pilot07=False,paid_calls=0)
    atomic_json(OUT/'cap-protocol-assessment-02.cost-summary.json',summary)
    print(json.dumps(dict(recommendation=recommendation,reservations=caps,moment_uncertainty_at_rho02=[x for x in moment_uncertainty if x['assumed_common_rho']==.2]),indent=2))
    status('Common-cap recommendation ready','Saved common65536 versus128k options, exact reservation pressure, candidate-weighted costs and highcap variance sensitivities. No actual65536 experiment or sub1pp guarantee is claimed; no partialpilot07 results read.')

if __name__=='__main__':main()
