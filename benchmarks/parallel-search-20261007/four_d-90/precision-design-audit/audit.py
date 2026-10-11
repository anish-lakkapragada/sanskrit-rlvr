"""Development-only precision estimands. Never opens live final responses/ledger."""
from pathlib import Path
from collections import Counter,defaultdict
import datetime,hashlib,json,math,sys
import numpy as np
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=Path(__file__).resolve().parent
from misc.vp_cartesian_final_analyze import panel_statistics
from misc.vp_cartesian_analyze import completed
BASE=ROOT/'benchmarks/parallel-search-20261007';JOBS=ROOT/'benchmarks/iterative-goal-20261006/jobs'
CELLS=['short_adanta_non_aorist','other_adanta_aorist','broad_non_curadi'];W=np.array([.52,.08,.40]);REPS=100000;SEED=2026100802
INPUTS={}
def read(p):
    assert 'final1800' not in str(p) and not ('candidate-1800' in str(p) and p.name!='manifest.json')
    INPUTS[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text())
def summary(draws):return {'se':float(np.std(draws,ddof=1)),'percentile_95_interval':np.quantile(draws,[.025,.975]).tolist(),'repetitions':len(draws)}
def bootstrap(values,groups,rng):
    totals=[];weights=[]
    for start in range(0,REPS,256):
        b=min(256,REPS-start);res=np.zeros((b,3));celln=np.zeros((b,3))
        for ix in groups:
            picked=ix[rng.integers(0,len(ix),(b,len(ix)))];batch=values[picked]
            res+=batch[:,:,:3].sum(axis=1);celln+=batch[:,:,3:].sum(axis=1)
        totals.append(res);weights.append(celln/res[:,2,None])
    v=np.concatenate(totals);return v[:,:2]/v[:,2,None],np.concatenate(weights)
def main():
    tasks=read(BASE/'four_d-90/tasks.json');manifest=read(BASE/'four_d-90/candidate-1800-v1/manifest.json')
    astra=[];opus=[]
    for i in range(1,21):astra+=read(JOBS/f'astra-simple4d-direct-{i:02d}/results.json')
    for i in range(1,6):opus+=read(JOBS/f'opus-fast-simple4d-{i:02d}/results.json')
    models={'Opus':opus,'Astra':astra}
    assert all(len(rs)==200 and [r['task'] for r in rs]==tasks and all(completed(r) for r in rs) for rs in models.values())
    assert all(t['campaign']['split']=='development' for t in tasks)
    assert dict(Counter(t['campaign']['sampling_cell']['label'] for t in tasks))==dict(zip(CELLS,[104,16,80]))
    assert np.allclose([manifest['composition'][h]/1800 for h in CELLS],W)
    families=defaultdict(list)
    for i,t in enumerate(tasks):families[t['campaign']['root_family']].append(i)
    ks=sorted(families);vals=[];fg=[];fh=[]
    for f in ks:
        ix=families[f];ts=[tasks[i] for i in ix];cs={t['campaign']['sampling_cell']['label'] for t in ts};assert len(cs)==1
        h=CELLS.index(next(iter(cs)));nh=[0,0,0];nh[h]=len(ix)
        vals.append([sum(opus[i]['is_correct'] for i in ix),sum(astra[i]['is_correct'] for i in ix),len(ix),*nh]);fg.append(ts[0]['dhatu']['gana']);fh.append(h)
    vals=np.array(vals,dtype=float);rng=np.random.default_rng(SEED)
    unrestricted,unrestricted_weights=bootstrap(vals,[np.arange(len(ks))],rng)
    class_groups=[np.flatnonzero(np.array(fg)==g) for g in sorted(set(fg))]
    class_draws,class_weights=bootstrap(vals,class_groups,rng)
    fixed=np.zeros((REPS,2));cells={};sandwich=np.zeros(2);iid_strata=np.zeros(2);analytic_boot=np.zeros(2)
    for h,c in enumerate(CELLS):
        ix=np.flatnonzero(np.array(fh)==h);v=vals[ix,:3];g=len(ix);n=v[:,2].sum();p=v[:,:2].sum(axis=0)/n
        assert len(set(v[:,2]))==1
        residual=v[:,:2]-p*v[:,2,None]
        variance=g/(g-1)*np.sum(residual**2,axis=0)/(n*n)
        sandwich+=W[h]**2*variance
        analytic_boot+=W[h]**2*np.sum(residual**2,axis=0)/(n*n)
        iid_strata+=W[h]**2*p*(1-p)/n
        for start in range(0,REPS,256):
            b=min(256,REPS-start);s=v[rng.integers(0,g,(b,g))].sum(axis=1)
            fixed[start:start+b]+=W[h]*s[:,:2]/s[:,2,None]
        cells[c]={'n':int(n),'families':g,'family_load':int(v[0,2]),'weight':float(W[h]),'models':{name:{'correct':int(v[:,j].sum()),'accuracy':float(p[j]),'family_sandwich_variance':float(variance[j]),'weighted_variance_contribution':float(W[h]**2*variance[j])} for j,name in enumerate(models)}}
    result_models={}
    for j,(name,rows) in enumerate(models.items()):
        original=panel_statistics(tasks,rows,repetitions=20000,seed=2026100719)
        p=sum(r['is_correct'] for r in rows)/200
        final_iid_cells=sum(W[h]**2*cells[c]['models'][name]['accuracy']*(1-cells[c]['models'][name]['accuracy'])/manifest['composition'][c] for h,c in enumerate(CELLS))
        result_models[name]={'n':200,'correct':int(p*200+.01),'accuracy':p,'all_usable':True,'iid_se':math.sqrt(p*(1-p)/200),'stratified_independent_question_plugin_se':float(math.sqrt(iid_strata[j])),'unstratified_family_sandwich_se':original['all_request']['root_cluster_sandwich_standard_error'],'existing_unstratified_bootstrap_20000':original['all_request']['family_bootstrap'],'existing_class_stratified_bootstrap_20000':original['all_request']['class_stratified_family_bootstrap'],'replicated_unstratified_bootstrap_100000':summary(unrestricted[:,j]),'replicated_class_stratified_bootstrap_100000':summary(class_draws[:,j]),'fixed_three_cell_family_bootstrap':summary(fixed[:,j]),'fixed_three_cell_family_sandwich_se':float(math.sqrt(sandwich[j])),'fixed_three_cell_family_bootstrap_analytic_se':float(math.sqrt(analytic_boot[j])),'development_rates_only_iid_projection_N1800':{'iid_se':math.sqrt(p*(1-p)/1800),'stratified_independent_question_plugin_se':math.sqrt(final_iid_cells),'caveat':'Arithmetic illustration only, not a forecast or final result. No family dependence, final class/tense composition, repeated-query variance or selection uncertainty is transported.'}}
    assert np.allclose(np.mean(fixed,axis=0),[.875,.805],atol=.001)
    assert np.allclose(fixed.std(axis=0,ddof=1),np.sqrt(analytic_boot),rtol=.01)
    report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'purpose':'Map precision estimands using only the completed200 development panel; no change to live final qualification.','canonical_development_grading_retained':True,'no_source_regrading':True,'fixed_weights':dict(zip(CELLS,W.tolist())),'development_family_count':len(ks),'cells':cells,'models':result_models,'paired_astra_minus_opus':{'estimate':-.07,'fixed_cell_family_bootstrap':summary(fixed[:,1]-fixed[:,0])},'mixture_weight_variation_in_resamples':{'unstratified':{c:{'sd':float(unrestricted_weights[:,h].std(ddof=1)),'p025_p975':np.quantile(unrestricted_weights[:,h],[.025,.975]).tolist()} for h,c in enumerate(CELLS)},'class_stratified':{c:{'sd':float(class_weights[:,h].std(ddof=1)),'p025_p975':np.quantile(class_weights[:,h],[.025,.975]).tolist()} for h,c in enumerate(CELLS)},'fixed_cell':{c:{'sd':0.,'weight':float(W[h])} for h,c in enumerate(CELLS)}},'input1800_design':{k:manifest[k] for k in ['n','families','composition','family_size_histogram','precision','exposure_limit','selection']},'bootstrap_formula':'For each replicate independently sample g_h families with replacement within each of the3cells; take each sampled family with all observed questions and paired outcomes; compute sum_h w_h*(sum successes/sum questions). No FPC.','sandwich_formula':'Sum_h w_h^2 * g_h/(g_h-1) * sum_g(S_hg-p_h*n_hg)^2 / N_h^2. Square-root gives SE. Families occur in one cell only.','sampling_caveat':'This honors the3mixture weights, not every tense/class/person/number/solver constraint. It is a sensitivity based on exchangeable sampled families, not an exact randomization variance for the constrained deterministic selector.','primary_references':{'stratified_variance':'https://www150.statcan.gc.ca/n1/pub/12-001-x/2019002/article/00006/02-eng.htm','within_stratum_PSU_bootstrap':'https://r-survey.r-forge.r-project.org/survey/html/bootweights.html','clustering_target_population':'https://www.nber.org/papers/w24003','quota_and_inclusion_probability_limits':'https://www150.statcan.gc.ca/n1/pub/12-001-x/2022002/article/00002/01-eng.htm'},'finite_population_correction_applied':False,'repeated_query_variance_identified':False,'unseen_root_population_explicitly_required_by_user':False,'user_request_interpretation':'The phrase stddev<1% does not uniquely specify the random quantity or target population. The project chose a conservative both-iid-and-family-SE gate; this audit neither changes that gate nor certifies the user meant unseen-root generalization.','inputs':INPUTS,'bootstrap_repetitions':REPS,'seed':SEED,'reviewer_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'final_responses_read':False,'live_ledger_read_or_written':False,'frozen_files_modified':False,'paid_calls':0,'benchmark_ready':False}
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in INPUTS.items())
    (OUT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'cells':cells,'models':result_models,'mixture_weight_variation':report['mixture_weight_variation_in_resamples']},indent=2))
if __name__=='__main__':main()
