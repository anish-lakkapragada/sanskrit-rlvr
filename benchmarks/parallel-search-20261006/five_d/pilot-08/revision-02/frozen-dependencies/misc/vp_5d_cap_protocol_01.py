"""Prospective cap/cost/precision assessment; only completed named development jobs.

Never reads pilot07 or any candidate model answers. No shared/frozen file edits.
"""
from __future__ import annotations
import json,math
from collections import Counter,defaultdict
import numpy as np
from misc.vp_5d_prepare_04 import OUT,ROOT,now,sha,atomic_json,status
from misc.vp_5d_metrics import completed,summarize
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_variance_06 import cell,coarse,pairtype
from misc import vp_campaign_candidates as old

B=20000;SEED=202610071122;N=4800
OAI_SETTLED=727.478150;ANT_SETTLED=188.615334

def read(path):return json.loads(path.read_text())
def usage(row,provider='OpenAI'):
    if provider=='OpenAI':return row['raw_batch_result']['response']['body']['usage']
    return row['raw_batch_result']['result']['message']['usage']
def cost(row,provider='OpenAI'):
    u=usage(row,provider);a,b=(5,25) if provider=='OpenAI' else (2,10)
    return (a*u['input_tokens']+b*u['output_tokens'])/1e6
def distribution(values):
    x=np.array(values,dtype=float)
    return dict(n=len(x),mean=float(x.mean()),sd=float(x.std(ddof=1)),quantiles={str(q):float(np.quantile(x,q)) for q in [0,.25,.5,.75,.9,.95,.99,1]})
def mean_bootstrap_summary(draws):
    return dict(mean=float(np.mean(draws)),standard_error=float(np.std(draws,ddof=1)),percentile95=np.quantile(draws,[.025,.975]).tolist(),one_sided95_upper=float(np.quantile(draws,.95)))

def variance_scenarios(rows,target,fs,completion,smooth):
    groups=defaultdict(list)
    for r in rows:groups[coarse(cell(r))].append(r)
    probs={}
    for c in target:
        rr=groups[coarse(c)];k=sum(r['is_correct'] is True for r in rr)
        probs[c]=(k+.5)/(len(rr)+1) if smooth else k/len(rr)
    p=sum(target[c]*probs[c] for c in target)/N;a=completion*p;g=fs['distinct_families']
    pairs=fs['unordered_within_family_cell_pair_counts'];outputs={}
    for metric in ['recorded_all_correct','completed_ratio_influence']:
        if metric=='recorded_all_correct':
            means={c:completion*probs[c]-a for c in target}
            var={c:completion*probs[c]*(1-completion*probs[c]) for c in target}
        else:
            means={c:probs[c]-p for c in target}
            var={c:(probs[c]*(1-p)**2+(1-probs[c])*p*p)/completion-means[c]**2 for c in target}
        independent=sum(target[c]*var[c] for c in target)
        meansq=sum(target[c]*means[c]**2 for c in target)+sum(2*x['pairs']*means[x['cell_a']]*means[x['cell_b']] for x in pairs)
        assert meansq>=-1e-8
        coeff=Counter()
        for x in pairs:coeff[pairtype(x['cell_a'],x['cell_b'])]+=2*x['pairs']*math.sqrt(var[x['cell_a']]*var[x['cell_b']])
        common=[]
        for rho in [0,.05,.1,.15,.2,.25,.3,.4]:
            se=math.sqrt((independent+meansq+rho*sum(coeff.values()))*g/(g-1))/N
            common.append(dict(assumed_common_rho=rho,expected_sandwich_se_pp=100*se))
        pairgrid=[]
        for mixed,non in [(0,0),(.15,.10),(.30,.17),(.45,.30)]:
            for lun in [0,.1,.2,.3,.4,.5]:
                valid=all((1+(l-1)*lun)*(1+(k-1)*non)+1e-9>=l*k*mixed*mixed for l in range(1,6) for k in range(1,9-l))
                v=independent+meansq+coeff['both_Lun']*lun+coeff['one_Lun']*mixed+coeff['different_non_Lun']*non
                pairgrid.append(dict(repeated_Lun_rho=lun,mixed_rho=mixed,non_Lun_rho=non,positive_semidefinite_for_all_cap8_5_blocks=valid,expected_sandwich_se_pp=100*math.sqrt(v*g/(g-1))/N))
        outputs[metric]=dict(independent_variance_sum=independent,allocation_mean_squared_sum=meansq,pair_covariance_coefficients=dict(coeff),common_rho_scenarios=common,pair_type_scenarios=pairgrid,maximum_common_rho_for_expected_sub1pp=(.0001*N*N*(g-1)/g-independent-meansq)/sum(coeff.values()))
    return dict(moment_estimator='Jeffreys Beta(.5,.5) per coarse correctness cell' if smooth else 'empirical coarse correctness proportions',coarse_cells=len(groups),minimum_cell_n=min(map(len,groups.values())),assumed_completion=completion,projected_all_accuracy=a,projected_usable_accuracy=p,iid_all_se_pp=100*math.sqrt(a*(1-a)/N),iid_usable_se_pp=100*math.sqrt(p*(1-p)/(N*completion)),expected_missing_response_bounds=[a,a+1-completion],estimates=outputs)

def main():
    output=OUT/'cap-protocol-assessment-01.json'
    assert not output.exists(),'Preserve versioned assessment'
    es={e.code:e for e in old.load_entries()};sources={};datasets={}
    for label,job in [('high','astra-five-d-cap-development-01'),('baseline','astra-five-d-pilot-04-pair'),('opus04','opus-five-d-pilot-04'),('opus06','opus-five-d-pilot-06')]:
        assert '07' not in job
        path=ROOT/'benchmarks/iterative-goal-20261006/jobs'/job/'results.json'
        raw=read(path);datasets[label]=[r for r in raw if not current_issue(r['task'],es)]
        sources[label]=dict(path=str(path),sha256=sha(path),raw_n=len(raw),current_n=len(datasets[label]))
    high=datasets['high'];base=datasets['baseline'];bm={r['task']['id']:r for r in base};paired=[bm[r['task']['id']] for r in high]
    assert len(high)==60 and all(completed(r) for r in high)
    assert all(x['task']==y['task'] for x,y in zip(high,paired))
    assert abs(sum(cost(r) for r in high)-14.450675)<1e-8
    candidate=OUT/'candidate-4800/revision-04';plan=read(candidate/'sampling-plan.json');manifest=read(candidate/'manifest.json');target=plan['cell_counts'];fs=manifest['family_statistics']
    assert sum(target.values())==N
    coarse_target=Counter()
    for c,q in target.items():coarse_target[coarse(c)]+=q
    groups=defaultdict(list)
    for a,b in zip(high,paired):groups[coarse(cell(a))].append((a,b))
    weights={c:q/N for c,q in coarse_target.items()};rng=np.random.default_rng(SEED)
    mean=delta=success=complete_base=correct_base=usable_correct_base=0
    highdraw=np.zeros(B);deltadraw=np.zeros(B);accdraw=np.zeros(B);strata={}
    sd={}
    for c,rs in groups.items():
        hc=np.array([cost(a) for a,b in rs]);bc=np.array([cost(b) for a,b in rs]);yy=np.array([float(a['is_correct'] is True) for a,b in rs]);dd=hc-bc;n=len(rs);w=weights[c]
        indexes=rng.integers(0,n,size=(B,n))
        highdraw+=w*hc[indexes].mean(1);deltadraw+=w*dd[indexes].mean(1);accdraw+=w*yy[indexes].mean(1)
        mean+=w*hc.mean();delta+=w*dd.mean();success+=w*yy.mean()
        complete_base+=w*sum(completed(b) for a,b in rs)/n
        correct_base+=w*sum(b['is_correct'] is True for a,b in rs)/n
        usable_correct_base+=w*sum(completed(b) and b['is_correct'] is True for a,b in rs)/n
        sd[c]=hc.std(ddof=1)
        strata[c]=dict(n=n,candidate_n=coarse_target[c],weight=w,high_cost_mean=float(hc.mean()),baseline_cost_mean=float(bc.mean()),paired_cost_difference=float(dd.mean()),high_correct=int(yy.sum()),high_output_tokens=distribution([usage(a)['output_tokens'] for a,b in rs]))
    # Anchored sensitivity: exact recipe×tense×voice baseline plus a coarse paired cap increment.
    fine=defaultdict(list)
    for r in base:fine[cell(r)].append(r)
    assert set(target)<=set(fine)
    anchor=0.;influence=defaultdict(float)
    for c,q in target.items():
        rs=fine[c];mu=sum(cost(r) for r in rs)/len(rs);anchor+=q/N*mu
        for r in rs:influence[r['task']['campaign']['root_family']]+=q/N/len(rs)*(cost(r)-mu)
    for c,rs in groups.items():
        mu=sum(cost(a)-cost(b) for a,b in rs)/len(rs)
        for a,b in rs:influence[a['task']['campaign']['root_family']]+=weights[c]/len(rs)*(cost(a)-cost(b)-mu)
    fv=np.array(list(influence.values()));g=len(fv);anchor_mean=anchor+delta
    anchor_se=math.sqrt(g/(g-1)*float(fv@fv))
    anchor_draw=anchor_mean+rng.multinomial(g,[1/g]*g,size=B)@fv
    funding={};remaining=2000-OAI_SETTLED
    # Predictive variation conditional on learned cell moments, separate from mean uncertainty.
    fine_sd={c:sd[coarse(c)] for c in target}
    varind=sum(q*fine_sd[c]**2 for c,q in target.items())
    covcoef=sum(2*x['pairs']*fine_sd[x['cell_a']]*fine_sd[x['cell_b']] for x in fs['unordered_within_family_cell_pair_counts'])
    for label,draws,point in [('direct_coarse',highdraw,mean),('fine_baseline_plus_coarse_paired_increment',anchor_draw,anchor_mean)]:
        sensitivity=[]
        for rho in [0,.2,.4]:
            conditional_sd=math.sqrt(varind+rho*covcoef)
            totals=N*draws+rng.normal(0,conditional_sd,size=B)
            sensitivity.append(dict(assumed_within_family_cost_rho=rho,conditional_final_total_cost_sd=conditional_sd,bootstrap_plus_predictive_total_cost95=np.quantile(totals,[.025,.975]).tolist(),conditional_fraction_over_remaining_budget=float(np.mean(totals>remaining))))
        funding[label]=dict(mean_per_task=point,projected_final_cost=N*point,projected_lifetime=OAI_SETTLED+N*point,point_headroom=remaining-N*point,mean_uncertainty=mean_bootstrap_summary(draws),mean_only_lifetime95=(OAI_SETTLED+N*np.quantile(draws,[.025,.975])).tolist(),largest_n_at_point_mean=math.floor(remaining/point),largest_n_at_one_sided95_mean=math.floor(remaining/np.quantile(draws,.95)),predictive_sensitivity=sensitivity)
    mean_input=sum(usage(r)['input_tokens'] for r in high)/60
    tail=[]
    for tokens in [32000,64000,128000]:
        tailcost=(mean_input*5+tokens*25)/1e6
        tail.append(dict(output_tokens=tokens,task_cost=tailcost,extra_tail_fraction_exhausting_point_headroom=max(0,(remaining/N-mean)/(tailcost-mean)),mixtures=[dict(tail_fraction=q,projected_final_cost=N*((1-q)*mean+q*tailcost),projected_lifetime=OAI_SETTLED+N*((1-q)*mean+q*tailcost)) for q in [.005,.01,.02,.05]]))
    variances={f'{"smoothed" if sm else "empirical"}_completion{comp}':variance_scenarios(high,target,fs,comp,sm) for sm in [False,True] for comp in [1.,.95]}
    # Existing Opus16k usage provides a scale, not evidence for the unrun128k arm.
    op=datasets['opus06'];og=defaultdict(list)
    for r in op:og[cell(r)].append(r)
    opus_mean=sum(q/N*sum(cost(r,'Anthropic') for r in og[c])/len(og[c]) for c,q in target.items())
    opus=dict(current_pilot06=summarize(op),usage16k=distribution([usage(r,'Anthropic')['output_tokens'] for r in op]),mean16k_cost_standardized_to_candidate=opus_mean,projected4800_cost_at_existing_usage=N*opus_mean,remaining_after_settled_before_pending_confirmation=1000-ANT_SETTLED,pending_fixed2400_maximum_total_reservation=400.416,pending_fixed2400_naive_usage_forecast=4*13.753878,common128k_cost_unmeasured=True,
      caveat='No pilot07 rows read. Opus128k has not been run on this diagnostic;16k usage cannot establish128k accuracy, tail behavior, or whether the strongest-model target remains calibrated.')
    finecovered={cell(r) for r in high};budget_ceiling=remaining/N
    report=dict(created_at=now(),policy='oracle-policy-18',sources=sources,candidate_tasks_sha256=sha(candidate/'tasks.json'),candidate_plan_sha256=sha(candidate/'sampling-plan.json'),assessment_script_sha256=sha(__import__('pathlib').Path(__file__)),
      source_scope=dict(all60_highcap_questions_current_scope=True,highcap_unique_families=60,current_baseline_n=len(base),candidate_families=fs['distinct_families'],exact_candidate_cells=len(target),observed_diagnostic_exact_cells=len(finecovered),candidate_questions_in_unobserved_exact_cells=sum(q for c,q in target.items() if c not in finecovered),class_adjustment=False),
      raw_diagnostic=dict(high=summarize(high),baseline_same_inputs=summarize(paired),observed_high_output_tokens=distribution([usage(r)['output_tokens'] for r in high]),observed_high_cost=distribution([cost(r) for r in high]),high_outputs_exceeding16384=sum(usage(r)['output_tokens']>16384 for r in high),one_sided95_missing_probability_upper_after_zero_of60=1-.05**(1/60),total_high_cost=sum(cost(r) for r in high)),
      standardized_diagnostic=dict(method='Exact candidate joint quotas aggregated to eight recipe×aorist/other×voice strata; no correction for within-non-Lun tense or class composition.',all_high_accuracy=success,high_accuracy_bootstrap=mean_bootstrap_summary(accdraw),baseline_recorded_all=correct_base,baseline_usable=usable_correct_base/complete_base,baseline_completion=complete_base,strata=strata),
      cost_forecast=dict(primary='Direct coarse standardization; anchored fine-baseline correction is sensitivity, not a choice made to pass funding.',fine_baseline_16k_point_mean=anchor,coarse_paired_cap_cost_increment=delta,anchored_family_influence_se=anchor_se,funding=funding,remaining_openai=remaining,maximum4800_average_cost_for_cap=budget_ceiling,openai_settled=OAI_SETTLED,anthropic_settled=ANT_SETTLED,bootstrap_repetitions=B,bootstrap_seed=SEED,unobserved_tail_sensitivity=tail,coarse_moment_predictive_independent_variance_sum=varind,coarse_moment_predictive_family_covariance_coefficient=covcoef),
      precision_scenarios=variances,opus_common_cap_option=opus,
      protocol_options=[dict(option='Astra128k + Opus16384',status='Evidence-supported Astra elicitation repair; distinct provider caps must be declared.',benefit='All60 diagnostic responses completed; missing hard questions are restored to the estimand.',limits='Astra accuracy gain is uncertain; no within-family highcap covariance, no full-population guarantee. Opus16k remains the current calibration protocol.'),dict(option='Both providers128k',status='Prospective common-ceiling option requiring coordinator protocol and funding approval plus Opus sensitivity evidence.',benefit='Same output ceiling and fewer censoring-based comparison concerns.',limits='Opus highcap effect unmeasured. Existing600/2400 calibration is16k and does not automatically certify strongest-model target at128k.'),dict(option='Keep both16384',status='Not recommended as the sole adequate-reference protocol given observed Astra censoring.',limits='Current Astra completion-conditioned score selectively excludes difficult questions. Bounds and cap diagnostic must accompany any16k budget-constrained result; it is not evidence that stronger elicitation is equivalent.')],
      recommendation='Prefer Astra128k over16384 for the primary prospective reference if the coordinator accepts and funds a fixed-N run. N4800 is plausible at observed means but not securely funded at bootstrap upper means or under a small unobserved long-output tail; do not call it guaranteed fundable. Do not lower N merely to obtain an affordable score if both-model precision then lacks a credible route. Keep final N/protocol unapproved until full2400 Opus confirmation and explicit funding/precision decision. Common128k is reasonable only with prospective Opus sensitivity evidence, not assumed equivalence.',
      limitations=['60 distinct diagnostic families provide no within-family highcap covariance. All rho values are assumptions, not transported estimates.','Coarse cells have2–18 observations; only26 of42 exact target cells are sampled. Sparse empirical zeros and a smoothed sensitivity are both reported.','Cost bootstrap conditions on observed support and transport of coarse moments; it cannot bound unobserved extreme token tails. Reported exceedance fractions are conditional simulation results, not guaranteed budget-risk probabilities.','Anchored correction assumes cap-cost increments transport within coarse cells; its family influence bootstrap includes overlap with baseline but does not solve unknown class/family composition.','Completion=.95 is a sensitivity near the zero-of60 one-sided upper missingness bound, not a forecast. The precision model assumes equal missing probability within coarse cells; actual informative missingness could be worse.','Expected sandwich values preserve the original estimator and actual candidate allocation; no estimator is selected to force a pass.','Both references need actual iid and family sandwich SE<1pp after complete fixed-N evaluation; scenario passage is not qualification.','Mean-token forecasts and small transport chunks cannot guarantee full fixed N within lifetime caps. Current final runner phases remain16384; any128k primary protocol requires explicit parent-owned versioning before freeze.','No partialpilot07 or final answer data were accessed. No frozen files, shared scripts or ledger were changed.'],paid_calls=0,final_n_approved=False,final_membership_approved=False,benchmark_ready=False)
    atomic_json(output,report)
    print(json.dumps(dict(output=str(output),standardized_high_accuracy=success,coarse_mean=mean,anchor_mean=anchor_mean,funding=funding,precision={k:{metric:next(s['expected_sandwich_se_pp'] for s in v['estimates'][metric]['common_rho_scenarios'] if s['assumed_common_rho']==.2) for metric in v['estimates']} for k,v in variances.items()}),indent=2))
    status('High-cap protocol evidence assessed','Completed prospective cost/variance scenarios from the60 settled cap pairs and exact candidate04 quotas. No partialpilot07 results read; funding and covariance uncertainty remain explicit, with no final protocol approved.')

if __name__=='__main__':main()
