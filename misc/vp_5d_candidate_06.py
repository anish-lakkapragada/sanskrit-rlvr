"""Policy13 pooled-v3 hypotheses; never used for question membership."""
import json
from misc.vp_5d_prepare_04 import ROOT,OUT,atomic_json,now,sha
from misc.vp_5d_prepare_06 import quotas,UNRESOLVED
from misc.vp_5d_candidate_05 import estimate
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_calibration_analysis_02 import summarize
from misc import vp_campaign_candidates as old

def main():
    es={e.code:e for e in old.load_entries()};panels={};sources={}
    for panel in ['04','05']:
        p=ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-{panel}/results.json';raw=json.loads(p.read_text());panels[panel]=[r for r in raw if not current_issue(r['task'],es)];sources[panel]={'path':str(p),'sha256':sha(p)}
    results={}
    for label,hold in [('current_policy13',set()),('prospective_source_holds',set(UNRESOLVED))]:
        rr={p:[r for r in rs if r['task']['dhatu']['code'] not in hold] for p,rs in panels.items()};rr['pooled']=rr['04']+rr['05'];results[label]={}
        for panel,rs in rr.items():
            cases={}
            for n,frac in [(600,.4),(600,.45),(720,.45)]:
                d=quotas(n,frac);cases[f'n{n}_Lun{int(100*frac)}']={'design':d,'fine':estimate(rs,d),'coarse':estimate(rs,d,True)}
            results[label][panel]={'summary':summarize(rs),'contrasts':cases}
    out={'created_at':now(),'policy':'oracle-policy-13','shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'sources':sources,'results':results,'status':'Exploratory joint-cell predictions, not qualification or independent replication. Next questions selected by inputs only.','limitations':['Pool same-v3 development rows by recipe, exact tense and voice; family-cluster bootstrap preserves cross-panel repeated roots.','Fine cells are sparse; estimates omit adaptation and oracle uncertainty. Coarse pooling is an assumption, not another independent experiment.','A45% aorist panel with two distinct tenses per family requires90% of sampled families to be aorist-eligible. This changes family composition, so cell reweighting cannot fully predict the next panel.','Same recipe proportions, all ten tenses and classes,55% non-aorist and10% passive remain. No guarantee of79–81% from these predictions.'],'no_heldout_answers_read':True,'no_membership_selected':True,'paid_calls':0}
    atomic_json(OUT/'pilot-06.pooled-comparison-policy13.json',out)
    print(json.dumps({s:{p:{k:{metric:round(v['fine'][metric]['accuracy']*100,4) for metric in ['all_requests','completed']}|{'se_pp':100*v['fine']['completed']['cluster_se']} for k,v in z['contrasts'].items()} for p,z in d.items()} for s,d in results.items()},indent=2))
if __name__=='__main__':main()
