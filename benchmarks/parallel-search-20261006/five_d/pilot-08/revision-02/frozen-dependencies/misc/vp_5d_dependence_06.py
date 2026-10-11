"""Development dependence including Astra completion influence; no final answers."""
import json,itertools
from collections import Counter,defaultdict
from misc.vp_5d_prepare_04 import ROOT,OUT,atomic_json,now,sha
from misc.vp_5d_metrics import completed,summarize
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_dependence_05 import correlations,category
from misc import vp_campaign_candidates as old

def analyze(rows):
 groups=defaultdict(list);families=defaultdict(list)
 for r in rows:families[r['task']['campaign']['root_family']].append(r)
 c=sum(completed(r) for r in rows)/len(rows);p=sum(completed(r) and bool(r['is_correct']) for r in rows)/sum(completed(r) for r in rows)
 values={'recorded_all_correct':{id(r):float(bool(r['is_correct'])) for r in rows},'completion':{id(r):float(completed(r)) for r in rows},'completed_ratio_influence':{id(r):float(completed(r))*(float(bool(r['is_correct']))-p)/c for r in rows}}
 pairs=defaultdict(list)
 for f,rr in families.items():
  for a,b in itertools.combinations(rr,2):pairs[category(a,b)].append((f,a,b))
 out={}
 for label,yy in values.items():
  out[label]={}
  for fine in [False,True]:
   groups=defaultdict(list)
   for r in rows:
    t=r['task'];m=t['morphology'];la=m['lakara'];k=(r['_panel'],t['derivation']['recipe_id'],la if fine else ('Lun' if la=='Lun' else 'other'),m['prayoga']);groups[k].append(r)
   residual={id(r):yy[id(r)]-sum(yy[id(x)] for x in rs)/len(rs) for rs in groups.values() for r in rs}
   out[label]['fine' if fine else 'coarse']={cat:correlations(pp,residual) for cat,pp in pairs.items()}
  out[label]['raw']={cat:correlations(pp,yy) for cat,pp in pairs.items()}
 return dict(summary=summarize(rows),family_load_histogram=dict(Counter(len(rr) for rr in families.values())),residual_diagnostics=out,completed_fraction=c)

def main():
 es={e.code:e for e in old.load_entries()};panels={};sources={}
 for model,ps in [('opus',['04','05','06']),('astra',['04'])]:
  rr=[]
  for p in ps:
   path=ROOT/f'benchmarks/iterative-goal-20261006/jobs/{model}-five-d-pilot-{p}{"-pair" if model=="astra" else ""}/results.json';raw=json.loads(path.read_text());sources[f'{model}{p}']=sha(path)
   for r in raw:
    if not current_issue(r['task'],es):r['_panel']=p;rr.append(r)
  panels[model]=analyze(rr)
 out=dict(created_at=now(),policy='oracle-policy-15',shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),sources=sources,models=panels,method='Family-equal symmetrized pair covariance with raw, panel x recipe x aorist/other x voice centered, and exact-tense centered alternatives. Completed-ratio influence includes missing rows as zero and scales by mean completion. Family bootstrap intervals condition on fitted cell means.',limitations=['Astra has no within-family repeated aorist observations. Such covariance is unidentified here.','Fine cells are small and mean fitting can depress residual correlations. Bootstrap intervals omit that fitting uncertainty and design adaptation.','Pairs per root increase across Opus panels but do not identify Astra dependence.','Empirical correlations from selected development families are not guaranteed transportable to differently allocated final families.'],no_final_membership_selected=True,no_heldout_answers_read=True,paid_calls=0)
 atomic_json(OUT/'pilot-06.cross-panel-dependence.json',out)
 print(json.dumps({model:{metric:{cat:{'pairs':z['pairs'],'rho':z['correlation'],'interval':z.get('bootstrap_percentile95')} for cat,z in values['coarse'].items()} for metric,values in v['residual_diagnostics'].items()} for model,v in panels.items()},indent=2))
if __name__=='__main__':main()
