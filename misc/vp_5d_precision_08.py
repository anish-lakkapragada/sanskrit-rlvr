"""Allocation-specific variance forecasts for unfrozen grammar proposals."""
import json,math
from collections import Counter,defaultdict
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,sha,now,status
from misc.vp_5d_variance_06 import analyze as variance
from misc.vp_5d_cap_protocol_01 import variance_scenarios

P=OUT/'pilot-08-proposal'
def read(p):return json.loads(p.read_text())
def main():
    rows=[]
    for suffix in ['a','b']:rows+=read(ROOT/'benchmarks/iterative-goal-20261006/jobs'/f'opus-five-d-pilot-07-r1-{suffix}'/'results.json')
    assert len(rows)==2400
    dep=read(P/'full07-dependence.json')['residual_diagnostics']
    high=read(ROOT/'benchmarks/iterative-goal-20261006/jobs/astra-five-d-cap-development-01/results.json')
    results={}
    for name in ['san20_lun45','san15_lun42']:
        results[name]={}
        for scope,n in [('development',2400),('test',4800)]:
            w=read(P/(name+f'.{scope}-N{n}.allocation.json'));cases={}
            for fine in [True,False]:
                for smooth in [False,True]:
                    v=variance(rows,w,dep,fine,smooth);proj={}
                    for metric,e in v['estimates'].items():
                        d=dep[metric]['coarse'];proj[metric]={}
                        for label in ['point','upper95']:
                            rho={cat:x['correlation'] if label=='point' else x['bootstrap_percentile95'][1] for cat,x in d.items()}
                            value=e['independent_variance_sum']+e['allocation_mean_squared_sum']+sum(e['pair_covariance_coefficients'][cat]*rho[cat] for cat in e['pair_covariance_coefficients'])
                            proj[metric][label]=dict(transported_pair_rhos=rho,expected_family_sandwich_se_pp=100*math.sqrt(value*w['distinct_families']/(w['distinct_families']-1))/n)
                        coeff=sum(e['pair_covariance_coefficients'].values());base=e['independent_variance_sum']+e['allocation_mean_squared_sum']
                        proj[metric]['common_rho_sensitivity']=[dict(rho=r,expected_family_sandwich_se_pp=100*math.sqrt((base+coeff*r)*w['distinct_families']/(w['distinct_families']-1))/n) for r in [0,.1,.2,.3,.4]]
                    cases[f'{"fine" if fine else "coarse"}_{"smoothed" if smooth else "empirical"}']=dict(cell_moments=v,observed_Opus_covariance_transport=proj)
            result=dict(allocation_sha256=sha(P/(name+f'.{scope}-N{n}.allocation.json')),n=n,families=w['distinct_families'],opus_scenarios=cases)
            if scope=='test':
                result['astra_highcap_scenarios']={f'{"smoothed" if sm else "empirical"}_completion{comp}':variance_scenarios(high,w['cell_counts'],w,comp,sm) for sm in [False,True] for comp in [1.,.95]}
            results[name][scope]=result
    pair_counts=Counter();families=defaultdict(list)
    for row in rows:families[row['task']['campaign']['root_family']].append(row)
    for rr in families.values():
        for i,a in enumerate(rr):
            for b in rr[i+1:]:pair_counts['|'.join(sorted([a['task']['derivation']['recipe_id'],b['task']['derivation']['recipe_id']]))]+=1
    out=dict(created_at=now(),variants=results,full07_pair_counts_by_recipe=dict(pair_counts),limitations=['Only complete pilot07 is used. No new model calls or item-based membership selection.','Observed Opus correlations now include1352 repeated-Lun pairs, but do not establish covariance for changed recipe/class/root composition or a new65536 output protocol.','New san weight is based on160Opus and4Astra diagnostic questions; pairs involving san are sparse.','Upper95 values combine marginal correlation endpoints and are not a joint95% confidence bound.','Astra highcap covariance is wholly unobserved; all common-rho values are explicit sensitivities.','Unstratified family sandwich remains the final precision estimator alongside iid; no change of estimator is used to claim success.','Forecasts remain developmental and ignore model/adaptation uncertainty beyond the shown scenarios.'],benchmark_ready=False,paid_calls=0,no_final_membership_generated=True)
    atomic_json(P/'precision-forecasts.json',out)
    print(json.dumps({name:{scope:dict(n=v['n'],families=v['families'],opus={label:{m:round(s['point']['expected_family_sandwich_se_pp'],3) for m,s in z['observed_Opus_covariance_transport'].items()} for label,z in v['opus_scenarios'].items()},astra_rho02={label:{m:round(next(z['expected_sandwich_se_pp'] for z in e['common_rho_scenarios'] if z['assumed_common_rho']==.2),3) for m,e in x['estimates'].items()} for label,x in v.get('astra_highcap_scenarios',{}).items()}) for scope,v in scopes.items()} for name,scopes in results.items()},indent=2))
    status('Revised-mixture precision forecasts complete','Actual aggregate family allocations now have Opus empirical-repeat and Astra highcap correlation sensitivities. These are proposal forecasts, not a qualified benchmark or fixed final membership.')

if __name__=='__main__':main()
