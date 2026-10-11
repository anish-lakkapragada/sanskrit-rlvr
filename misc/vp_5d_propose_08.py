"""Bounded aggregate grammar-mixture forecasts after the FULL failed pilot07.

No item outcomes select membership. This creates quota proposals, not tasks.
"""
from __future__ import annotations
import json,math
from collections import Counter,defaultdict
import numpy as np
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_cartesian_analyze import completed
from misc.vp_5d_variance_06 import cell,coarse
from misc.vp_5d_dependence_06 import analyze as dependence
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_cap_protocol_01 import cost
from misc import vp_campaign_candidates as old

P=OUT/'pilot-08-proposal';REC=['causative_of_intensive','causative_of_intensive_luk','desiderative']

def read(p):return json.loads(p.read_text())
def apportion(weights,total,unit=2):
    assert total%unit==0
    total//=unit;s=sum(weights.values());raw={k:total*v/s for k,v in weights.items()};out={k:math.floor(x) for k,x in raw.items()}
    for k in sorted(raw,key=lambda k:(-(raw[k]-out[k]),k))[:total-sum(out.values())]:out[k]+=1
    return {k:v*unit for k,v in out.items()}

def quotas(recipe_percent,lun_percent):
    oldp=read(OUT/'pilot-07/revision-01/plan.json');rc={r:round(2400*q/100) for r,q in zip(REC,recipe_percent)}
    lc=apportion(rc,round(2400*lun_percent/100));pc=apportion({r:rc[r] for r in REC[:2]},240)
    cells={}
    for r in REC:
        source={c:n for c,n in oldp['cell_counts'].items() if c.startswith(r+'|')};nl=Counter();pa=Counter()
        for c,n in source.items():
            _,la,vo=c.split('|')
            if la!='Lun':nl[la]+=n
            if vo=='Karmani':pa[la]+=n
        nt=apportion(nl,rc[r]-lc[r]);pv=apportion(pa,pc[r]) if r in pc else {}
        cells[r+'|Lun|Kartari']=lc[r]
        for la,n in nt.items():
            assert n>pv.get(la,0)
            cells[r+'|'+la+'|Kartari']=n-pv.get(la,0)
            if pv.get(la,0):cells[r+'|'+la+'|Karmani']=pv[la]
    assert sum(cells.values())==2400 and sum(n for c,n in cells.items() if '|Lun|' in c)==round(24*lun_percent)
    return dict(n=2400,recipe_counts=rc,cell_counts=cells,gana_counts=oldp['gana_counts'],lakara_counts=dict(Counter({la:sum(n for c,n in cells.items() if c.split('|')[1]==la) for la in oldp['lakara_counts']})),prayoga_counts={'Kartari':2160,'Karmani':240},recipe_percent=recipe_percent,Lun_percent=lun_percent,source_non_Lun_profiles='Preserve prior conditional non-Lun tense proportions within each recipe by even largest-remainder apportionment; assign10% global passive across nested recipes proportional to their recipe weights, and preserve each recipe passive-tense profile. All42 joint cells remain positive.',phase='confirm_64k',effort='xhigh',max_output_tokens=65536,transport=dict(fixed_n=2400,chunks=6,n_each=400,sequence='Each next chunk only after previous settlement and financial gate. No interim score analysis or stopping. Partition not yet generated.'),status='unfrozen_quota_proposal',all_classes_and_lakaras_preserved=True,maximum_tasks_per_family=8,maximum_Lun_per_family=5,maximum_each_other_lakara_per_family=1)

def fit_weights(rows,plan,class_adjust):
    groups=defaultdict(list);classes=defaultdict(list)
    for i,r in enumerate(rows):groups[cell(r)].append(i);classes[r['task']['dhatu']['gana']].append(i)
    w=np.ones(len(rows));target=plan['cell_counts'];n=plan['n'];iterations=0
    for iteration in range(10000 if class_adjust else 1):
        for c,ii in groups.items():w[ii]*=target[c]/w[ii].sum()
        if class_adjust:
            for c,ii in classes.items():w[ii]*=plan['gana_counts'][c]/w[ii].sum()
        err=max(abs(w[ii].sum()-target[c]) for c,ii in groups.items());iterations=iteration+1
        if err<1e-7:break
    return w,dict(method='Iterative proportional fitting to joint recipe×tense×voice AND class margins' if class_adjust else 'Exact joint recipe×tense×voice standardization',converged=bool(err<1e-6),iterations=iterations,maximum_joint_margin_error=float(err),minimum_weight=float(w.min()),maximum_weight=float(w.max()),effective_question_weight_n=float(w.sum()**2/(w@w)),class_margins={c:float(w[ii].sum()) for c,ii in classes.items()},joint_class_interactions='No full joint×class target is declared; raking preserves observed interactions. This is an observational sensitivity, not identification of missing joint×class cells.')

def forecast(rows,plan,class_adjust=False):
    w,fit=fit_weights(rows,plan,class_adjust);families=sorted({r['task']['campaign']['root_family'] for r in rows});fi={f:i for i,f in enumerate(families)};v=np.zeros((len(families),4))
    for r,ww in zip(rows,w):
        y=int(r['is_correct'] is True);c=int(completed(r));v[fi[r['task']['campaign']['root_family']]]+=ww*np.array([y,c*y,c,1])
    b=np.random.default_rng(202610071208).multinomial(len(v),[1/len(v)]*len(v),10000);est={}
    for name,a,d in [('all',0,3),('usable',1,2)]:
        num=v[:,a].sum();den=v[:,d].sum();p=num/den;u=v[:,a]-p*v[:,d];z=(b@v[:,a])/(b@v[:,d])
        est[name]=dict(accuracy=float(p),family_sandwich_se=float(math.sqrt(len(v)/(len(v)-1)*float(u@u))/den),family_bootstrap_interval95=np.quantile(z,[.025,.975]).tolist())
    totals=v.sum(0)
    return dict(fit=fit,estimates=est,missing_response_bounds=[float(totals[1]/totals[3]),float((totals[1]+totals[3]-totals[2])/totals[3])],completion=float(totals[2]/totals[3]),weighted_cost_at_existing16k=float(sum(ww*cost(r,'Anthropic') for r,ww in zip(rows,w))/w.sum()),warning='Exploratory reweighting of failed16k development panel. Future common65536 cap is unmeasured. Family intervals omit mixture-selection and root-composition uncertainty.')

def cap_forecast(high,plan):
    groups=defaultdict(list);target=Counter()
    for r in high:groups[coarse(cell(r))].append(r)
    for c,n in plan['cell_counts'].items():target[coarse(c)]+=n
    rng=np.random.default_rng(202610071209);draw=np.zeros(20000);mean=acc=0
    for c,n in target.items():
        rs=groups[c];x=np.array([cost(r) for r in rs]);y=np.array([r['is_correct'] is True for r in rs]);w=n/2400;mean+=w*x.mean();acc+=w*y.mean();draw+=w*x[rng.integers(0,len(rs),(20000,len(rs)))].mean(1)
    return dict(mean_cost=float(mean),cost_bootstrap95=np.quantile(draw,[.025,.975]).tolist(),accuracy=float(acc),n=60,minimum_source_cell=min(map(len,groups.values())),projection4800_cost=float(4800*mean),lifetime4800=float(727.478150+4800*mean),projection6000_cost=float(6000*mean),lifetime6000=float(727.478150+6000*mean),warning='128k60-question coarse-cell transport to prospective65536. San is only4observations; increasing its weight magnifies uncertainty. No class adjustment or highcap family dependence measured.')

def main():
    assert not (P/'counterfactual-forecasts.json').exists();P.mkdir(exist_ok=True);entries={e.code:e for e in old.load_entries()};sources=[];rows=[]
    for suffix in ['a','b']:
        path=ROOT/'benchmarks/iterative-goal-20261006/jobs'/f'opus-five-d-pilot-07-r1-{suffix}'/'results.json';rr=read(path);assert len(rr)==1200;rows.extend(rr);sources.append(dict(path=str(path),sha256=sha(path)))
    frozen=read(OUT/'pilot-07/revision-01/tasks.json');assert {r['task']['id'] for r in rows}=={t['id'] for t in frozen};assert len(rows)==2400
    assert all(not current_issue(r['task'],entries) for r in rows),'Wait for uniform policy reanalysis if scope changes'
    hpath=ROOT/'benchmarks/iterative-goal-20261006/jobs/astra-five-d-cap-development-01/results.json';high=read(hpath);assert len(high)==60
    variants={}
    for name,recipe,lun in [('san20_lun45',[56,24,20],45),('san15_lun42',[60,25,15],42),('san15_lun40',[60,25,15],40),('san20_lun42',[56,24,20],42),('original_lun37',[200/3,80/3,20/3],37)]:
        p=quotas(recipe,lun);variants[name]=dict(plan=p,joint_only=forecast(rows,p),joint_and_class=forecast(rows,p,True),astra_highcap_transport=cap_forecast(high,p));atomic_json(P/(name+'.quota-proposal.json'),p)
    for r in rows:r['_panel']='07'
    dep=dependence(rows);atomic_json(P/'full07-dependence.json',dep)
    out=dict(created_at=now(),status='aggregate_proposals_not_frozen',sources=sources,baseline_analysis_sha256=sha(OUT/'pilot-07/revision-01/aggregate-analysis.json'),astra_highcap_source_sha256=sha(hpath),policy='oracle-policy-18',adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),variants=variants,selection_rule='Compare broad grammar designs before new membership; never use individual item errors for allocation. No tasks selected by this script.',final_membership_generated=False,paid_calls=0,benchmark_ready=False)
    atomic_json(P/'counterfactual-forecasts.json',out)
    print(json.dumps({k:dict(joint={x:s['accuracy'] for x,s in v['joint_only']['estimates'].items()},raked={x:s['accuracy'] for x,s in v['joint_and_class']['estimates'].items()},raking=v['joint_and_class']['fit'],astra=v['astra_highcap_transport']) for k,v in variants.items()},indent=2))
    status('Pilot08 grammar counterfactuals assessed','Compared five recipe/aorist mixtures on the full2400 panel, with joint-cell and class-raked sensitivities and highcap cost extrapolations. Proportions and membership remain unfrozen pending coordinator review.')

if __name__=='__main__':main()
