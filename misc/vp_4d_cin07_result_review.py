"""Bounded additive review of settled 4D ciN pilot07; no API or other outcomes."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from misc.vp_4d_gap06_analyze import verify_settled,verify_panel,verify_results,summarize
from misc.vp_4d_gap06_source_audit import derive,paths
from misc.vp_cartesian_task import entries_by_code,validate_task
from misc.vp_cartesian_prompt_v1 import render
from misc.ant_batch_eval import apply_result
from vidyut.prakriya import DhatuPada
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'benchmarks/parallel-search-20261006/four_d/coverage-gap-06'
JOB=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-four-d-pilot-07'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

def main():
 decl=read(OUT/'cin-analysis-predeclaration.json')
 job=verify_settled(read(ROOT/'benchmarks/iterative-goal-20261006/ledger.json'),decl)
 reg=read(OUT/'coordinator-registration.json')
 for f,h in reg['dependency_sha256'].items():assert sha(ROOT/f)==h,f
 ts=read(OUT/'cin-candidate-inputs.json');bs=read(OUT/'cin-branches.json')
 verify_panel(ts,bs);assert read(JOB/'tasks.json')==ts
 an=read(OUT/'cin-analysis.json');rp=JOB/'results.json'
 assert sha(rp)==an['result_sha256'];assert sha(OUT/'cin-analysis-predeclaration.json')==an['analysis_predeclaration_sha256']
 rs=read(rp);verify_results(ts,rs)
 reproduced=summarize(rs,bs)
 for k,v in reproduced.items():assert an[k]==v,k
 assert an['all46_settled_and_collected']
 es=entries_by_code();checks=[];representatives=[]
 bmap={b['id']:b for b in bs};chosen_branches=set()
 cached={c['id']:c for c in read(OUT/'cin-source-controls.json')if c['kind']=='panel_positive'}
 for r in rs:
  t=r['task'];tid=t['id'];e=es[t['dhatu']['code']]
  rescored=apply_result(r,r['raw_batch_result'],r['collected_at'])
  for k in ['output_text','answer','answer_normalized','is_correct','status','truncated','refusals','stop_reason']:
   assert rescored[k]==r[k],(tid,k)
  assert r['is_correct'] and r['status']=='completed' and not r['truncated']
  assert r['request']['params']['messages']==[dict(role='user',content=render(t))]
  assert hashlib.sha256(render(t).encode()).hexdigest()==t['campaign']['prompt_sha256']
  assert r['request']['params']['model']==decl['model'] and r['request']['params']['max_tokens']==65536
  assert r['request']['params']['output_config']['effort']==decl['effort']
  validate_task(t,e,'development');ps=derive(e,t['morphology']);gold={p.text for p in ps}
  explicit={p.text for pada in DhatuPada.choices()for p in derive(e,t['morphology'],pada)}
  assert gold==explicit==set(t['gold_slp1'])
  assert all({'3.1.66','6.4.104'}<={h.code for h in p.history}for p in ps)
  assert paths(ps)==cached[tid]['derivations']
  branch=bmap[tid]['branch']
  row=dict(id=tid,code=e.code,family=t['campaign']['root_family'],gana=t['dhatu']['gana'],branch=branch,
   answer=r['answer'],gold_slp1=t['gold_slp1'],gold_devanagari=t['gold_devanagari'],path_count=len(ps),
   scoring_parity=True,full_pada_union_equal=True,source_paths_unchanged=True)
  checks.append(row)
  if len(ps)>1 or branch not in chosen_branches or e.code in ['01.1079','04.0013','09.0044','10.0221']:
   representatives.append(row);chosen_branches.add(branch)
 now=datetime.now(timezone.utc).isoformat()
 independent=ROOT/'benchmarks/parallel-search-20261006/four_d/pilot-07-independent-review/mechanical-audit.json'
 optional=read(independent)['optional_control']
 review=dict(created_at=now,run_id='cin-pilot07-result-review',job_id=decl['job_id'],
  result_sha256=sha(rp),analysis_sha256=sha(OUT/'cin-analysis.json'),
  tasks_sha256=sha(OUT/'cin-candidate-inputs.json'),declaration_sha256=sha(OUT/'cin-analysis-predeclaration.json'),
  registered_dependency_count=len(reg['dependency_sha256']),all_registered_dependencies_unchanged=True,
  whole_panel_analysis_reproduced=True,all46_exact_scorer_parity=True,all46_prompts_match=True,
  all46_regenerate_with_full_union=True,source_paths=sum(r['path_count']for r in checks),
  all_source_paths_match_presubmission_controls=True,metrics=an['metrics'],trigger=an['trigger'],
  gana_counts={k:v['n']for k,v in an['groups']['gana'].items()},branch_counts={k:v['n']for k,v in an['groups']['branch'].items()},
  paid_questions_with_multiple_surface_forms=0,multiple_path_single_surface_questions=[r for r in checks if r['path_count']>1],
  representative_successes=representatives,all_checks=checks,
  optionality=dict(paid_optional_surface_successes=0,explanation='All46 full accepted unions are singletons. Four questions have two derivation paths converging on the same surface. No engine option was removed.',
   separate_offline_control=optional,control_sha256=sha(independent),control_is_model_success=False,
   note='The saved sam+Ric optional-length control is outside ordinary4D and outside the paid panel. It is preserved as an engine/source control, not newly generated or evidence of paid-panel success.'),
  source_qualification='Primary7.3.33 prints adayi for the dadati/dadhati discussion; the panel Bhvadi da01.1079 uses the general A-final rule by inference, not a separately printed exact-class paradigm. This pre-existing qualification remains; no new blocker was found.',
  disagreements=[],new_source_issues=[],source_policy_change_proposed=False,
  no_frozen_files_modified=True,no_paid_calls=True,no_5d08_results_read=True,benchmark_ready=False)
 save('result-review.json',review)
 save('result-verdict.json',dict(created_at=now,run_id=review['run_id'],mechanism='Ordinary passive third-singular aorist cin',
  status='closed_as_unsupported_hardness_lead',score='46/46 correct;46/46 usable',trigger_pass=False,
  correct=46,n=46,families=46,source_branch_count=4,class_count=8,
  nominal_wilson95=an['metrics']['all_request_wilson95'],
  zero_se_caution='The plug-in SE is zero because every response succeeds. It is not a precision guarantee or zero uncertainty. Nominal Wilson95 is92.29–100%; iid coverage is an approximation for this fixed selected panel.',
  decision='Do not spend further on this cin hypothesis. No observed hard component is supplied for a final mixture.',
  scale_limit='The declared source-clean test predicate has only80 tuples/families, allLun/Karmani/Prathama/Eka. Neither final diversity nor sub1pp precision is established.',
  broader_4d_status='Unresolved globally. The independent96-question ordinary-tail screen remains pending; no outcome from that screen or5D08 is used.',
  review_sha256=sha(OUT/'result-review.json'),raw_result_sha256=sha(rp),analysis_sha256=sha(OUT/'cin-analysis.json'),
  no_impossibility_claim=True,benchmark_ready=False))
 print(json.dumps({k:review[k]for k in ['result_sha256','analysis_sha256','registered_dependency_count','source_paths','all46_exact_scorer_parity']},indent=2))

if __name__=='__main__':main()
