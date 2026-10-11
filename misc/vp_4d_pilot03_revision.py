#!/usr/bin/env python3
"""Preserve preliminary180panel and freeze178after source-only lexical exclusion."""
from collections import Counter
import json,hashlib,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,HISTORY,write,sha,now,load_entries,name,family,source_rows,row_identity,matches,CELLS
from misc.vp_4d_pilot03 import CELLS03,marker_groups,eligible,stats
from misc.vp_4d_pilot02 import metadata_issue,exposure
from misc.vp_4d_pilot02_audit import contrast_families
from misc.vp_4d_search03 import RUN_ID,status
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_goal_validate import validate
from finetune.prompts import slp1_to_devanagari
EXCLUDE={'01.1088'}
SOURCE='https://sa.wikisource.org/wiki/पृष्ठम्:सिद्धान्तकौमुदी_(बालमनोरमा_उत्तर-१).djvu/१६१'
def main():
 path=OUT/'pilot-03-r1.questions.json'
 if path.exists():raise RuntimeError('Revisedpilotisfrozen')
 original=OUT/'pilot-03.questions.json';ts=json.load(open(original));removed=[t for t in ts if t['dhatu']['code'] in EXCLUDE];ts=[t for t in ts if t['dhatu']['code'] not in EXCLUDE]
 assert len(ts)==178 and len(removed)==2
 write(path,ts);audit=validate(ts,'development');audit.update(questions_sha256=sha(path),source_controls_passed=35,unique_visible_tuples=178,prior_exposure_overlap=0)
 # Prompt check uses full retained citation, not a normalized pool key.
 assert all(slp1_to_devanagari(t['dhatu']['aupadeshika']) in render(t) for t in ts)
 audit['full_citation_retained_in_every_prompt']=True
 es={e.code:e for e in load_entries()};groups=marker_groups(es);cross=contrast_families(list(es.values()));seen=set();safe=[]
 for r in source_rows(es):
  if r['code'] in EXCLUDE or metadata_issue(r,es):continue
  key=row_identity(r,es)
  if key in seen:continue
  seen.add(key);safe.append(r)
 old=lambda r:any(matches(r,c,es) for c in CELLS) or (r['family'] in cross and name(es[r['code']].dhatu.gana)!='Curadi' and r['prayoga']=='Kartari' and r['lakara'] in {'Lat','Lan','Lot','VidhiLin'})
 new=lambda r:any(eligible(r,c,es,groups) for c in CELLS03)
 tests=[r for r in safe if r['split']=='test']
 pool=dict(prior_pilot01_plus02_union=stats([r for r in tests if old(r)],es),new_predicates=stats([r for r in tests if new(r)],es),new_tuples_outside_prior_union=stats([r for r in tests if new(r) and not old(r)],es),all_predicates_union=stats([r for r in tests if old(r) or new(r)],es))
 fm=Counter(t['campaign']['root_family'] for t in ts);collapsed=Counter((groups.get(t['campaign']['root_family'],{}).get('base',t['dhatu']['aupadeshika']),t['dhatu']['gana']) for t in ts)
 cell=lambda t:t['campaign']['sampling_cell']['label']
 cells={label:dict(n=len(xs),families=len({t['campaign']['root_family'] for t in xs}),subtypes=dict(Counter(t['campaign']['selection']['mechanism_subtype'] for t in xs))) for label in [c['label'] for c in CELLS03] if (xs:=[t for t in ts if cell(t)==label])}
 dist={k:dict(Counter(t['morphology'][k] for t in ts)) for k in ['lakara','prayoga','purusha','vacana']};dist['gana']=dict(Counter(t['dhatu']['gana'] for t in ts))
 evidence=dict(created_at=now(),dictionary_code='01.1088',aupadeshika='Gf\\',gana='Bhvadi',artha='secane',source=SOURCE,source_locator='Printed page150, Bhvadi gṛ/ghṛ entries',short_quote='घृत, घर्म, घृणा, इत्यत्रैव प्रयोगः, नान्यत्र',finding='Balamanorama explicitly restricts this Bhvadi root to these nominal formations and cites Mahabhasya on7.1.95. Ordinary finite conjugation is not established. Exclude the entry from finite benchmarks pending contrary primary evidence.',excluded_from_preliminary_panel=[t['id'] for t in removed],stage='After preliminary generation but before any model evaluation; no model answers viewed for this decision.',policy='All coordinates and outcome categories are treated alike. Preliminary questions, gold, manifests and all prior evaluation records remain untouched.',independence='This does not exclude Bhvadi gṛ or Juhotyadi ṛ, which the inspected commentaries license separately.')
 write(OUT/'pilot-03.lexical-addendum.json',evidence)
 manifest=dict(created_at=now(),run_id=RUN_ID,seed=2026100703,questions_sha256=sha(path),n=len(ts),unique_families=len(fm),maximum_tasks_per_family=max(fm.values()),family_size_histogram=dict(Counter(fm.values())),partially_collapsed_marker_family_count=len(collapsed),distribution=dist,cells=cells,preliminary_manifest_path=str(OUT/'pilot-03.manifest.json'),preliminary_questions_sha256=sha(original),revision=dict(reason='Uniform finite-scope quarantine of dictionary01.1088 following a primary lexical restriction',removed_task_ids=[t['id'] for t in removed],replacement_tasks=0,score_exposure_before_revision=False),generation_design='Prespecified source-audited180task recipe, then deterministic deletion of the two unsupported lexical entry tuples. All other members retained; no outcome-based replacement.',source_audit_path=str(OUT/'pilot-03.source-audit.json'),source_audit_sha256=sha(OUT/'pilot-03.source-audit.json'),lexical_addendum_path=str(OUT/'pilot-03.lexical-addendum.json'),generator_sha256=sha(ROOT/'misc/vp_4d_pilot03.py'),revision_generator_sha256=sha(__file__),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),family_split_sha256=sha(HISTORY/'family-split.json'),supply=pool,no_test_model_answers_read=True,final_membership_selected=False,benchmark_ready=False)
 write(OUT/'pilot-03-r1.manifest.json',manifest);write(OUT/'pilot-03-r1.audit.json',audit)
 request=json.load(open(OUT/'experiment-request-03.json'));request.update(created_at=now(),request_id='four-d-pilot-03-r1-opus',questions_path=str(path),questions_sha256=sha(path),n=len(ts),unique_root_families=len(fm),suggested_sampling='Evaluate all178frozenquestions:60marker,60weakperfect,58specialit. Report all-request/completed metrics,mechanism/subtype/family diagnostics and every oracle disagreement.',audit_paths=[str(OUT/x) for x in ['pilot-03-r1.audit.json','pilot-03.source-audit.json','pilot-03.lexical-addendum.json','pilot-03-r1.manifest.json','pilot-02.disagreement-review.json']],supersedes='experiment-request-03.json',submission_status='Ready for coordinator review; no worker paid calls.',scope_exclusion={'code':'01.1088','evidence_path':str(OUT/'pilot-03.lexical-addendum.json')})
 request['estimate']['maximum_reservation_usd']=round(len(ts)*(1500*2/1e6+16384*10/1e6),6)
 request['predeclared_analysis']=dict(primary='Exact match against the full audited accepted form set, completed-answer accuracy and all-request accuracy reported separately.',subgroups='Report three main cells and fixed15accent/45othermarker,30positive/30prohibition perfect subsets. Display all results, including easy groups.',promising_signal='A main cell with at least8source-supported grammatical errors spanning at least6families warrants a fresh confirmatory panel. The smaller30question perfect subgroup needs at least5errors across4families to motivate, not certify, follow-up. These are pragmatic discovery triggers, not significance tests or release acceptance.',negative_result='If no cell shows this signal, do not assume80percent is impossible: report the tested mechanisms as disconfirmed at useful scale and list any independently justified untested hypotheses. Do not repeat model-missed items or use refusals to create hardness.',release='No final task membership or weights fixed by this pilot. Final sets require independent families, predeclared diversity and family-aware uncertainty, plus bothreference scores if funded.')
 write(OUT/'experiment-request-03-r1.json',request)
 # Mark original request as superseded in a separate sidecar, preserving frozen files.
 write(OUT/'experiment-request-03.superseded.json',dict(created_at=now(),superseded='experiment-request-03.json',replacement='experiment-request-03-r1.json',reason='Two source-unlicensed ordinary finite questions removed before evaluation; do not submit the preliminary180panel.'))
 print(json.dumps({k:manifest[k] for k in ['questions_sha256','n','unique_families','distribution','cells','supply']},indent=2))
if __name__=='__main__':main()
