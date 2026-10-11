"""Predeclared development-only pair covariance diagnostics across v3 panels."""
from __future__ import annotations
import json,itertools,math
from collections import defaultdict,Counter
import numpy as np
from misc.vp_5d_prepare_04 import ROOT,OUT,atomic_json,now,sha
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_novelty_04 import normalized
from misc import vp_campaign_candidates as old

def category(a,b):
    la=a['task']['morphology']['lakara'];lb=b['task']['morphology']['lakara']
    return 'both_Lun' if la==lb=='Lun' else 'one_Lun' if 'Lun' in [la,lb] else 'same_non_Lun' if la==lb else 'different_non_Lun'

def y(r):return int(r['status']=='completed' and bool(r['is_correct']))

def stratum(r,fine):
    t=r['task'];m=t['morphology'];la=m['lakara']
    return r['_panel']+'|'+t['derivation']['recipe_id']+'|'+(la if fine else 'Lun' if la=='Lun' else 'other')+'|'+m['prayoga']

def correlations(pairs,residual):
    clusters=defaultdict(list)
    for f,a,b in pairs:
        x=residual[id(a)];z=residual[id(b)];clusters[f].append(np.array([(x+z)/2,(x*x+z*z)/2,x*z]))
    if not clusters:return {'correlation':None,'reason':'No pairs'}
    a=np.array([np.mean(v,axis=0) for v in clusters.values()]);g=len(a);mean=a.mean(axis=0);var=mean[1]-mean[0]**2;cov=mean[2]-mean[0]**2
    result={'correlation':float(cov/var) if var>0 else None,'symmetric_pair_covariance':float(cov),'symmetric_pair_variance':float(var),'families':g,'pairs':len(pairs)}
    if g>1 and var>0:
        boot=np.random.default_rng(202610070705).multinomial(g,[1/g]*g,10000)@a/g
        vv=boot[:,1]-boot[:,0]**2;good=vv>1e-15;rr=(boot[good,2]-boot[good,0]**2)/vv[good]
        result.update(bootstrap_percentile95=np.quantile(rr,[.025,.975]).tolist(),bootstrap_valid_replicates=len(rr))
    return result

def analyze(rows,completed):
    use=[r for r in rows if not completed or r['status']=='completed'];byfamily=defaultdict(list)
    for r in use:byfamily[r['task']['campaign']['root_family']].append(r)
    raw={id(r):y(r) for r in use};res=[];cellinfo=[]
    for fine in [False,True]:
        groups=defaultdict(list)
        for r in use:groups[stratum(r,fine)].append(r)
        means={c:sum(y(r) for r in rr)/len(rr) for c,rr in groups.items()}
        res.append({id(r):y(r)-means[stratum(r,fine)] for r in use})
        cellinfo.append({'centering':'panel×recipe×'+('lakara' if fine else 'aorist/non-aorist')+'×voice','cells':len(groups),'smallest_cell':min(map(len,groups.values()))})
    pairs=defaultdict(list)
    for f,rr in byfamily.items():
        for a,b in itertools.combinations(rr,2):
            c=category(a,b);pairs[c].append((f,a,b))
            if c=='both_Lun':pairs[c+('::same_recipe' if a['task']['derivation']['recipe_id']==b['task']['derivation']['recipe_id'] else '::different_recipe')].append((f,a,b))
    report={}
    for c,pp in pairs.items():
        # Order-free table; each family has unit total weight within a category.
        report[c]={'pair_correctness_table':dict(Counter('/'.join(map(str,sorted([y(a),y(b)]))) for f,a,b in pp)),
          'raw_symmetric_correlation':correlations(pp,raw),'coarse_residual_correlation':correlations(pp,res[0]),'fine_residual_correlation':correlations(pp,res[1])}
    return {'questions':len(use),'families':len(byfamily),'family_load_histogram':dict(Counter(len(rr) for rr in byfamily.values())),'centering_strata':cellinfo,'categories':report}

def main():
    es={e.code:e for e in old.load_entries()};rows=[];files=[];excluded=[]
    for panel in ['04','05']:
        path=ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-{panel}/results.json';rr=json.loads(path.read_text());files.append({'path':str(path),'sha256':sha(path)})
        for r in rr:
            t=r['task'];assert t['campaign']['split']=='development' and t['prompt_version']=='cartesian-5d-v3-sanskrit';r['_panel']=panel
            issue=current_issue(t,es)
            if issue:excluded.append({'panel':panel,'id':t['id'],'reason':issue})
            else:rows.append(r)
    assert len(rows)==len({normalized(r['task'])[0] for r in rows})
    pending=json.loads((OUT/'pilot-05.luk-marker-source-audit.json').read_text())['affected_saved_development_rows'];pendingids={r['id'] for p in ['04','05'] for r in pending[p]}
    sensitiv=[r for r in rows if r['task']['id'] not in pendingids and r['task']['dhatu']['code'] not in {'04.0137','10.0023'}]
    out={'created_at':now(),'predeclaration_sha256':sha(OUT/'pilot-05.cross-panel-dependence-predeclaration.json'),'sources':files,'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'excluded':excluded,
      'current_scope':{'all_requests':analyze(rows,False),'completed_only':analyze(rows,True)},
      'source_hold_sensitivity':{'reason':'Policy13 already excludes narrow luk-marker/mit rows. Additionally exclude unresolved stim/urja uniformly across outcomes; raw scores remain unchanged.','all_requests':analyze(sensitiv,False),'completed_only':analyze(sensitiv,True)},
      'method':'Unordered pairs are symmetrized before Pearson correlation. Each exact-root family receives equal total weight within each pair category. Coarse/fine residuals subtract observed stratum means; whole-family bootstrap intervals condition on those fitted cell means.',
      'limitations':['These are exploratory development covariance diagnostics, not a transportable final design effect. Panel weights and root eligibility differ.','Bootstrap intervals condition on estimated cell means; they omit adaptation, oracle uncertainty and sparse-cell mean fitting uncertainty.','Raw pair correlations confound differing cell difficulty; use residual results as a sensitivity, not a causal explanation.','Astra04 alone has no repeated aorist pair within family; no Astra repeated-aorist correlation is inferred from these Opus estimates.'],
      'heldout_answers_read':False,'paid_calls':0,'benchmark_ready':False}
    atomic_json(OUT/'pilot-05.cross-panel-dependence.json',out)
    print(json.dumps({scope:{stat:{c:{'pairs':x['coarse_residual_correlation']['pairs'],'families':x['coarse_residual_correlation']['families'],'correlation':x['coarse_residual_correlation']['correlation'],'interval':x['coarse_residual_correlation'].get('bootstrap_percentile95')} for c,x in d['categories'].items()} for stat,d in out[scope].items() if stat in ['all_requests','completed_only']} for scope in ['current_scope','source_hold_sensitivity']},indent=2))

if __name__=='__main__':main()
