from pathlib import Path
import sys,hashlib,json,copy
ROOT=Path('/Users/anish/Documents/git-repos/sanskrit');sys.path.insert(0,str(ROOT))
from misc import vp_goal as r,oai_batch_eval as io
from misc.vp_goal_validate import validate
from misc.vp_modification_prompt_v1 import render
from misc.vp_simple_search_analyze import paired
OUT=ROOT/'benchmarks/parallel-search-20261007'
panels=[('opus-simple4d-90-01','four_d-90/tasks.json'),('opus-modification-01','modification-01/tasks.json'),('opus-modification-control-01','modification-01/controls.json')]
# Independently verify frozen dependencies and regenerate every panel before any spending.
m=io.read_json(OUT/'four_d-90/manifest.json')
for row in m['dependencies']+m['historical_inputs']+io.read_json(OUT/'four_d-90/dependency-supplement.json')['files']:
 assert io.sha256(ROOT/row['path'])==row['sha256'],row['path']
h=io.read_json(OUT/'modification-01/preflight-handoff.json')
for p,sha in h['files_sha256'].items():assert io.sha256(OUT/'modification-01'/p)==sha,p
for p,sha in h['helper_sha256'].items():assert io.sha256(ROOT/p)==sha,p
for p,sha in io.read_json(OUT/'modification-01/manifest.json')['dependencies'].items():assert io.sha256(ROOT/p)==sha,p
assert io.read_json(OUT/'analysis-predeclaration.json')['analyzer_sha256']==io.sha256(ROOT/'misc/vp_simple_search_analyze.py')
loaded={}
for name,path in panels:
 tasks=io.read_json(OUT/path);assert len(tasks)==200
 audit=validate(tasks,'development');loaded[name]=tasks
 print(name,'validated',flush=True)
mods=loaded[panels[1][0]];ctrl=loaded[panels[2][0]]
for a,b in zip(mods,ctrl):
 for f in ['dhatu','morphology','gold_slp1','gold_devanagari']:assert a[f]==b[f]
 assert render(a)==render({k:a[k] for k in ['source_form_devanagari','source_morphology','target_morphology']})
# Validate contrast sign and fail closed on an incorrect target pairing.
def row(t,correct):return dict(task=t,is_correct=correct,status='completed',answer='synthetic',truncated=False)
a=[row(t,False) for t in mods[:2]];b=[row(t,True) for t in ctrl[:2]]
assert paired(a,b)['all_request_accuracy_difference']==-1
bad=copy.deepcopy(b);bad[0]['task']['gold_slp1']=['bad']
try:paired(a,bad)
except ValueError:pass
else:raise AssertionError('Pair mismatch accepted')
reg={'created_at':io.now(),'panels':[{'id':name,'path':str(OUT/path),'sha256':io.sha256(OUT/path),'tasks_digest':r.digest(loaded[name]),'n':200,'phase':'confirm_64k','provider':'Anthropic'} for name,path in panels], 'analysis_predeclaration_sha256':io.sha256(OUT/'analysis-predeclaration.json'),'runner_sha256':io.sha256(ROOT/'misc/vp_goal.py'),'validator_sha256':io.sha256(ROOT/'misc/vp_goal_validate.py'),'four_d_manifest_sha256':io.sha256(OUT/'four_d-90/manifest.json'),'modification_handoff_sha256':io.sha256(OUT/'modification-01/preflight-handoff.json'),'phase_clarification':'Worker 4D request says explore but explicitly specifies65536. Coordinator authorizes confirm_64k, the only matching64k phase; this remains development research.','maximum_total_reservation_usd':395.016,'independent_full_regeneration_passed':True,'public_only_and_paired_target_checks_passed':True,'benchmark_ready':False}
p=OUT/'coordinator-registration.json';assert not p.exists();io.atomic_json(p,reg)
with io.lock(r.OUT):
 s=r.load();s.setdefault('additional_renderers',{})['vp_modification_prompt_v1.py']=io.sha256(ROOT/'misc/vp_modification_prompt_v1.py');r.save(s)
 registry=io.read_json(r.OUT/'experiment-registry.json')
 for x in reg['panels']:
  registry['authorized_task_digests'].append(x['tasks_digest'])
  registry['experiments'].append(dict(x,registered_at=reg['created_at'],rationale='Frozen single-VP-Bench development: diverse grammar-defined4D challenge or no-dhatu modification and exact paired ordinary4D control. No final qualification; both modification arms must finish before contrast analysis.',coordinator_registration_sha256=io.sha256(p)))
 io.atomic_json(r.OUT/'experiment-registry.json',registry)
for name,path in panels:r.prepare(name,OUT/path,'Anthropic','confirm_64k')
# Locked runner independently revalidates all inputs and cumulative caps before each POST.
for name,path in panels:
 r.count_inputs(name)
 r.submit(name)
print('ALL_THREE_SUBMITTED',flush=True)
