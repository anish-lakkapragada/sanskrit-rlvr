"""Current recipe controls and Sanskrit prompt shape, offline only."""
import json
from misc.vp_5d_prepare_04 import OUT,ROOT,sha,now,atomic_json,status
from misc.vp_cartesian_prompt_v3 import render
from misc.vp_sanskrit_prompt_v1 import root_fields
from misc.vp_cartesian_task import make_task
from misc import vp_campaign_candidates as old
PREFIX='pilot-06.revision-01'
def main():
 es={e.code:e for e in old.load_entries()};tasks=json.loads((OUT/(PREFIX+'.tasks.json')).read_text());p=json.loads((OUT/(PREFIX+'.plan.json')).read_text());oldcontrol=json.loads((OUT/'pilot-03.source-audit.json').read_text());checks=[]
 for c in oldcontrol['direct_checks']:
  t=make_task(es[c['code']],'source_control',c['morphology'],'source_control',c['sanadi'],prompt_version=p['prompt_version']);assert c['expected'] in t['gold_slp1'];checks.append({**c,'actual_current_gold':t['gold_slp1'],'current_passed':True,'excluded_from_candidate':all(x['dhatu']['code']!=c['code'] for x in tasks)})
 controls=dict(created_at=now(),policy='oracle-policy-14',shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),prior_source_audit_sha256=sha(OUT/'pilot-03.source-audit.json'),direct_checks=checks,all_passed=True,limits='Independent printed examples verify one licensed output per recipe. They do not certify every alternative or every rare derived full form. Current scope gates and item disagreement audits remain necessary.',no_paid_calls=True)
 atomic_json(OUT/(PREFIX+'.source-control-audit.json'),controls)
 texts=[render(t) for t in tasks];(OUT/(PREFIX+'.prompts.txt')).write_text('\n\n'.join(t['id']+'\n'+text for t,text in zip(tasks,texts)))
 for t,txt in zip(tasks,texts):
  assert root_fields(t['dhatu']) in txt
  assert all(txt.count(label)==1 for label in ['लकारः —','प्रयोगः —','पुरुषः —','वचनम् —','सनादिप्रत्ययाः (क्रमेण) —'])
  assert 'सिद्धेषु रूपेष्वेकमेव' in txt and '<answer></answer>' in txt
  assert len(t['derivation']['sanadi']) in {1,2} and len(t['morphology'])==4
  assert t['derivation']['prefixes']==[] and t['derivation']['order']=='innermost_to_outermost'
 audit=dict(created_at=now(),n=len(tasks),prompt_version=p['prompt_version'],task_sha256=sha(OUT/(PREFIX+'.tasks.json')),rendered_prompts_sha256=sha(OUT/(PREFIX+'.prompts.txt')),prompt_helper_sha256=sha(ROOT/'misc/vp_cartesian_prompt_v3.py'),sanskrit_helper_sha256=sha(ROOT/'misc/vp_sanskrit_prompt_v1.py'),all_prompts_include_citation_class_meaning=True,exactly_four_morphology_fields=True,one_ordered_recipe_from_finite_menu=True,exactly_one_accepted_form_requested=True,no_added_prefix_or_pada_choice=True,semantic_review='Sanskrit v3 instructs deriving the specified finite form, retains the dictionary citation including markers, class and meaning, explicitly applies listed Sanadi operations in order, supplies all four coordinates, and accepts one Devanagari form. It introduces no further choices.',min_chars=min(map(len,texts)),max_chars=max(map(len,texts)))
 atomic_json(OUT/(PREFIX+'.prompt-audit.json'),audit)
 for recipe in p['recipe_counts']:
  t=next(t for t in tasks if t['derivation']['recipe_id']==recipe);print(render(t)+'\n')
 status('Pilot06 revision ready for coordinator', 'The revised600 questions passed full policy14 regeneration, shared validation, exact distribution and historical-tuple novelty checks, Sanskrit prompt review and three independent recipe controls. Original frozen files are preserved. No paid calls.')
if __name__=='__main__':main()
