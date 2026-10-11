"""Independent input-only audit of the frozen pilot08 Astra subset. No outputs/API."""
import json, hashlib, itertools, math
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue,validate_task
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'benchmarks/parallel-search-20261006';P=B/'five_d/pilot-08';S=P/'astra-subset';OUT=B/'four_d/subset08-review'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def family(t):return t['campaign']['root_family']
def cell(t):return '|'.join([t['derivation']['recipe_id'],t['morphology']['lakara'],t['morphology']['prayoga']])
def cross(t):return '|'.join([t['dhatu']['gana'],t['derivation']['recipe_id'],'Lun' if t['morphology']['lakara']=='Lun' else 'other'])
def norm(t):
 d=t.get('derivation')or{};m=t.get('morphology')or{};h=t.get('dhatu')or{}
 if d.get('prefixes')or h.get('prefixes')or t.get('prefixes'):return None
 if any(o.get(k)not in(None,'',[])for o in[d,m,h,t]for k in['dhatu_pada','pada']):return None
 fields=['lakara','prayoga','purusha','vacana']
 if not all(m.get(k)for k in fields)or not h.get('aupadeshika')or not h.get('gana'):return None
 return(h['aupadeshika'],h['gana'],tuple(d.get('sanadi')or[]),*(m[k]for k in fields))
def walk(t):
 if not isinstance(t,dict):return
 yield t
 for c in t.get('forms')or[]:yield from walk(c)
def pairstats(ts):
 groups=defaultdict(list)
 for t in ts:groups[family(t)].append(t)
 counts=Counter();fams=defaultdict(set);recipes=Counter();classes=Counter();samecode=Counter();ids=[]
 for f,tt in groups.items():
  for a,b in itertools.combinations(tt,2):
   la,lb=a['morphology']['lakara'],b['morphology']['lakara'];key='LL'if la==lb=='Lun'else'LN'if'Lun'in[la,lb]else'NN'
   counts[key]+=1;fams[key].add(f)
   if key=='LL':
    recipe='|'.join(sorted([a['derivation']['recipe_id'],b['derivation']['recipe_id']]))
    recipes[recipe]+=1;classes[a['dhatu']['gana']]+=1;samecode[str(a['dhatu']['code']==b['dhatu']['code'])]+=1;ids.append(dict(family=f,recipe=recipe,ids=[a['id'],b['id']]))
 return dict(counts=dict(counts),families={k:len(v)for k,v in fams.items()},LL_recipes=dict(recipes),LL_classes=dict(classes),LL_same_code=dict(samecode),LL_pairs=ids,family_count=len(groups),load_histogram=dict(Counter(len(v)for v in groups.values())))
def main():
 ts=read(P/'tasks.json');ss=read(S/'tasks.json');pm={t['id']:t for t in ts};plan=read(S/'plan.json');master=read(ROOT/'benchmarks/creation-campaign-20261006/family-split.json')
 initial_hashes={str(p.relative_to(ROOT)):sha(p)for p in[P/'tasks.json',S/'tasks.json',S/'plan.json',S/'manifest.json',ROOT/'misc/vp_cartesian_task.py']}
 assert len(ts)==len(pm)==2400 and len(ss)==len({t['id']for t in ss})==240
 assert all(t==pm[t['id']]for t in ss)
 assert sha(P/'tasks.json')==plan['source_tasks_sha256']
 assert sha(ROOT/'misc/vp_cartesian_task.py')==plan['adapter_sha256']
 for name,v in read(S/'manifest.json')['files'].items():assert sha(S/name)==v['sha256']
 for t in ts:
  e=entries_by_code()[t['dhatu']['code']];assert entry_scope_issue(e)is None and oracle_issue(t)is None
  assert master['families'][family(t)]['split']=='development' and t['dhatu']['code']in master['families'][family(t)]['codes']
 for t in ss:validate_task(t,entries_by_code()[t['dhatu']['code']],'development')
 assert dict(Counter(cell(t)for t in ss))==plan['cell_counts']
 assert dict(Counter(t['dhatu']['gana']for t in ss))==plan['gana_counts']
 assert len({cell(t)for t in ss})==42 and len({t['dhatu']['gana']for t in ss})==10 and len({t['morphology']['lakara']for t in ss})==10
 assert Counter(t['morphology']['prayoga']for t in ss)=={'Kartari':216,'Karmani':24}
 assert sum(t['morphology']['lakara']=='Lun'for t in ss)==108
 chunks=[read(S/f'chunk-{i:02}.tasks.json')for i in[1,2]];assert[len(c)for c in chunks]==[120,120] and sum(chunks,[])==ss
 assert not({family(t)for t in chunks[0]}&{family(t)for t in chunks[1]})
 hist=read(P/'historical-inputs.json');seen=set();historical_families=set()
 for rec in hist['task_files']:
  p=Path(rec['path']);assert sha(p)==rec['sha256']
  for top in read(p):
   for t in walk(top):
    n=norm(t)
    if n:seen.add(n)
    if t.get('campaign',{}).get('root_family'):historical_families.add(family(t))
 assert not{norm(t)for t in ts}&seen
 pp=pairstats(ts);sp=pairstats(ss);assert sp['counts']=={'LL':43,'LN':79,'NN':56}and sp['families']=={'LL':43,'LN':40,'NN':38}
 assert sp['family_count']==110 and max(Counter(family(t)for t in ss).values())==3
 parentcross=Counter(cross(t)for t in ts);subcross=Counter(cross(t)for t in ss)
 missing={k:v for k,v in parentcross.items()if k not in subcross}
 pc=Counter(cell(t)for t in ts);sc=Counter(cell(t)for t in ss);w={c:pc[c]/2400/(sc[c]/240)for c in sc};weights=[w[cell(t)]for t in ss]
 fweights=defaultdict(float)
 for t,wi in zip(ss,weights):fweights[family(t)]+=wi
 out=dict(created_at=datetime.now(timezone.utc).isoformat(),all_hard_checks_passed=True,no_model_answers_read=True,no_paid_calls=True,source_hashes=initial_hashes,
  checks=['240 unique exact parent dictionaries','all240 regenerated including full accepted gold union and prompt hash','all2400 parent entries pass policy19 and master development split','all42 joint cells /10classes /10tenses','Lun108/passive24','exact declared recipe/class/cell quotas','two120 chunks concatenate exactly; families disjoint across chunks','zero input-normalized overlap with saved two-campaign history','all manifest hashes verified'],
  subset=sp,parent=pp,Curadi=dict(parent=dict(Counter('Lun'if t['morphology']['lakara']=='Lun'else'other'for t in ts if t['dhatu']['gana']=='Curadi')),subset=dict(Counter('Lun'if t['morphology']['lakara']=='Lun'else'other'for t in ss if t['dhatu']['gana']=='Curadi'))),
  missing_class_recipe_Lun_cells=missing,missing_cell_parent_questions=sum(missing.values()),missing_cell_parent_weight=sum(missing.values())/2400,
  calibration=dict(method='42 joint-cell weights: parent share /subset share; no class correction',min_weight=min(weights),max_weight=max(weights),task_kish_effective_n=sum(weights)**2/sum(v*v for v in weights),family_total_kish_effective_n=sum(fweights.values())**2/sum(v*v for v in fweights.values()),weights=w,limits='Descriptive support diagnostics, not a design effect or effective independent sample size; family selection is not probability sampling.'),
  historical_scope=dict(input_files=len(hist['task_files']),normalized_history=len(seen),all_parent_families_previously_exposed=len({family(t)for t in ts}&historical_families),subset_families_previously_exposed=len({family(t)for t in ss}&historical_families),prior_exposure=master['prior_exposure']),
  limitations=['Only43 independent-family LL observations; san-containing LL pairs absent from parent and subset.','NN56 pairs arise from38families;LN79 from40, not79independent units.','Prespecified seeded quota selection has unknown inclusion probabilities; no design-unbiased claim.','No independent replay of the min-cost selection was performed; code read plus frozen hashes, actual membership and declared constraints were checked.','Source-rule audit is recorded separately; mechanical correctness is not full grammatical certification.'])
 for path,expected in initial_hashes.items():assert sha(ROOT/path)==expected
 (OUT/'membership-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items()if k in['all_hard_checks_passed','Curadi','missing_class_recipe_Lun_cells','missing_cell_parent_weight','historical_scope']},ensure_ascii=False,indent=2));print('Kish:',out['calibration']['task_kish_effective_n'],out['calibration']['family_total_kish_effective_n'])
if __name__=='__main__':main()
