"""Current-policy aggregate class/diversity proposals; no selected tasks or calls."""
import json
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_5d_propose_08 import quotas,forecast,cap_forecast,read
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_dependence_06 import analyze as dependence
from misc import vp_campaign_candidates as old
P=OUT/'pilot-08-proposal-policy20'
EXPECTED='a7908917f2f5a711a29d116ce314467d807c8418581644b6ece27423c6753d08'

def main():
    assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
    assert not (P/'counterfactual-forecasts.json').exists();P.mkdir(exist_ok=True)
    entries={e.code:e for e in old.load_entries()};raw=[];sources=[]
    for suffix in ['a','b']:
        path=ROOT/'benchmarks/iterative-goal-20261006/jobs'/f'opus-five-d-pilot-07-r1-{suffix}'/'results.json';r=read(path);assert len(r)==1200;raw+=r;sources.append(dict(path=str(path),sha256=sha(path)))
    tasks=read(OUT/'pilot-07/revision-01/tasks.json');assert len(raw)==2400 and {r['task']['id'] for r in raw}=={t['id'] for t in tasks}
    rows=[r for r in raw if not current_issue(r['task'],entries)];excluded=[dict(id=r['task']['id'],reason=current_issue(r['task'],entries),correct=r['is_correct'],status=r['status']) for r in raw if current_issue(r['task'],entries)]
    assert len(rows)<2388 and len(excluded)>12
    hp=ROOT/'benchmarks/iterative-goal-20261006/jobs/astra-five-d-cap-development-01/results.json';highraw=read(hp);high=[r for r in highraw if not current_issue(r['task'],entries)];assert len(highraw)==60 and len(high)==59
    variants={}
    choices=[('san20_lun45_fullcoverage',[56,24,20],45,True)]
    for name,recipes,lun,lift in choices:
        plan=quotas(recipes,lun);plan.update(policy='oracle-policy-20',adapter_sha256=EXPECTED,source_policy_sha256=sha(OUT.parent/'oracle-policy-20.json'))
        if lift:
            plan['gana_counts'].update(Curadi=145,Bhvadi=1535)
            plan['class_rationale']='145Curadi permits one task from every eligible development Curadi family; Bhvadi reduced65, others unchanged. Proportional4800class quotas (290Curadi/3070Bhvadi) preserve the same confirmation/final class composition and can cover all203eligible test Curadi families. No class chosen by errors.'
        variants[name]=dict(plan=plan,joint_only=forecast(rows,plan),joint_and_class=forecast(rows,plan,True),astra_highcap_transport=cap_forecast(high,plan))
        variants[name]['astra_highcap_transport'].update(n=59,scope='Policy20 supplemental59; raw60 remains unchanged. One exactsource-invalid08.0007 row excluded uniformly.',warning='128k59-question coarse-cell transport to prospective65536. San is4observations; class changes are not adjusted. No highcap family dependence is measured.')
        atomic_json(P/(name+'.quota-proposal.json'),plan)
    for r in rows:r['_panel']='07'
    atomic_json(P/'full07-dependence.json',dependence(rows))
    out=dict(created_at=now(),policy='oracle-policy-20',adapter_sha256=EXPECTED,sources=sources,raw_n=2400,current_n=len(rows),source_exclusions=excluded,raw_scores_unchanged=True,astra_highcap_raw_n=60,astra_highcap_current_n=59,astra_highcap_source_sha256=sha(hp),variants=variants,not_frozen=True,no_tasks_generated=True,paid_calls=0,benchmark_ready=False)
    atomic_json(P/'counterfactual-forecasts.json',out)
    print(json.dumps({name:dict(joint={k:round(v['accuracy']*100,4) for k,v in x['joint_only']['estimates'].items()},raked={k:round(v['accuracy']*100,4) for k,v in x['joint_and_class']['estimates'].items()},raked_bounds=[round(v*100,4) for v in x['joint_and_class']['missing_response_bounds']],raked_SEpp={k:round(v['family_sandwich_se']*100,4) for k,v in x['joint_and_class']['estimates'].items()},max_weight=x['joint_and_class']['fit']['maximum_weight'],astra_cost=x['astra_highcap_transport']['mean_cost']) for name,x in variants.items()},indent=2))
    status('Policy20 class-coverage forecasts ready','Uniform source exclusions applied to the full2400 and separate59-cap supplement. Compared supply-defined Curadi coverage and broad aorist variations; exact new membership remains unselected.')

if __name__=='__main__':main()
