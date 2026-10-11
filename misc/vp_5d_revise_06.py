"""Source-driven pre-exposure replacement; preserve frozen original600."""
import json,random,copy
from collections import Counter
from misc.vp_5d_prepare_06 import ROOT,OUT,RECIPES,PN,SOURCE_ROOTS,UNRESOLVED,VERSION,history,entries,task_for,SEED
from misc.vp_5d_prepare_04 import atomic_json,status,now,sha
from misc.vp_5d_novelty_04 import normalized
from misc.vp_cartesian_task import make_task,validate_task,oracle_issue
from misc.vp_goal_validate import validate
from misc import vp_campaign_candidates as old
from vidyut.prakriya import Vyakarana
PREFIX='pilot-06.revision-01'

def main():
    tp=OUT/(PREFIX+'.tasks.json');pp=OUT/(PREFIX+'.plan.json')
    if tp.exists() or pp.exists():raise RuntimeError('Preserve frozen revision')
    original=json.loads((OUT/'pilot-06.tasks.json').read_text());affected=[t for t in original if oracle_issue(t)]
    assert len(affected)==1 and affected[0]['id']=='cart5-2b8c7c8844df4c89a566438f'
    f=affected[0]['campaign']['root_family'];replaced=[t for t in original if t['campaign']['root_family']==f];assert len(replaced)==2
    p=json.loads((OUT/'pilot-06.plan.json').read_text());p.update(revised_at=now(),oracle_policy='oracle-policy-14',revision={'original_plan_sha256':sha(OUT/'pilot-06.plan.json'),'original_task_sha256':sha(OUT/'pilot-06.tasks.json'),'reason':'Shared policy14 holds trace7.4.96 after yaNluk before Ric; preserve300 two-tense family pairs by replacing both questions of the affected family before any provider exposure.','replacement_seed':SEED+1,'membership_rule':'Seeded first eligible unselected Bhvadi family matching both original recipe×tense×voice×person×number cells; prefer families absent named prior5D panels. All historical normalized tuples excluded.','grammar_weights_unchanged':True,'no_model_outcomes_available':True})
    atomic_json(pp,p)
    es=entries();v=Vyakarana();bases={ff:sorted({q.text for q in v.derive(e.dhatu)}) for ff,e in es.items()};used,hf,ha=history();selected={t['campaign']['root_family'] for t in original}
    prior={t['campaign']['root_family'] for panel in ['01','02','03','04','05'] for t in json.loads((OUT/f'pilot-{panel}.tasks.json').read_text())}
    pool=sorted(ff for ff,e in es.items() if ff not in selected and e.code not in SOURCE_ROOTS and e.code not in UNRESOLVED and old.name(e.dhatu.gana)=='Bhvadi');random.Random(SEED+1).shuffle(pool);pool.sort(key=lambda ff:ff in prior)
    new=None;rejections=Counter()
    for ff in pool:
        ts=[]
        for t in replaced:
            probe,issue=task_for(es[ff],t['derivation']['recipe_id'],t['morphology'],bases)
            if issue:rejections[issue]+=1;break
            if normalized(probe)[0] in used:rejections['historical_tuple']+=1;break
            z=make_task(es[ff],'development',t['morphology'],t['derivation']['recipe_id'],t['derivation']['sanadi'],prompt_version=VERSION)
            z['campaign'].update({k:q for k,q in t['campaign'].items() if k in {'panel','slot','selection_reason','sampling_cell','audit_status'}})
            z['campaign'].update(lexical_bases=bases[ff],source_driven_replacement_for=t['id'])
            ts.append(z)
        if len(ts)==2:new=ts;break
    assert new,'No same-cell new family available'
    mapping={a['id']:b for a,b in zip(replaced,new)};tasks=[mapping.get(t['id'],copy.deepcopy(t)) for t in original]
    for t in tasks:
        t['campaign'].update(plan_sha256=sha(pp),oracle_policy='oracle-policy-14')
        validate_task(t,es[t['campaign']['root_family']],'development')
    assert len(tasks)==len({normalized(t)[0] for t in tasks})==600
    assert not any(normalized(t)[0] in used for t in tasks)
    assert Counter(t['campaign']['root_family'] for t in tasks)==Counter({ff:2 for ff in {t['campaign']['root_family'] for t in tasks}})
    assert len({t['campaign']['root_family'] for t in tasks})==300
    for field in ['dhatu','morphology','derivation']:
        if field=='dhatu':assert Counter(t[field]['gana'] for t in original)==Counter(t[field]['gana'] for t in tasks)
        else:assert Counter(json.dumps(t[field],sort_keys=True) for t in original)==Counter(json.dumps(t[field],sort_keys=True) for t in tasks)
    for ff in {t['campaign']['root_family'] for t in tasks}:assert len({t['morphology']['lakara'] for t in tasks if t['campaign']['root_family']==ff})==2
    audit=validate(tasks,'development');atomic_json(tp,tasks);atomic_json(OUT/(PREFIX+'.runner-audit.json'),audit)
    repl=dict(created_at=now(),policy='oracle-policy-14',original_task_sha256=sha(OUT/'pilot-06.tasks.json'),revised_task_sha256=sha(tp),replaced=[{'old_id':a['id'],'new_id':b['id'],'old_code':a['dhatu']['code'],'new_code':b['dhatu']['code'],'morphology':a['morphology'],'recipe':a['derivation']['recipe_id']} for a,b in zip(replaced,new)],unchanged_normalized_tuples=598,seed=SEED+1,source_evidence='pilot-06.luk-broader-source-review.json',candidate_rejections=dict(rejections),all_grammar_margins_unchanged=True,no_answers_used=True)
    atomic_json(OUT/(PREFIX+'.replacement-audit.json'),repl)
    mf=json.loads((OUT/'pilot-06.manifest.json').read_text());families={t['campaign']['root_family'] for t in tasks};mf.update(created_at=now(),policy='oracle-policy-14',task_sha256=sha(tp),plan_sha256=sha(pp),revision_script_sha256=sha(ROOT/'misc/vp_5d_revise_06.py'),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),new_families_vs_named_five_d_01_to05=len(families-prior),reused_families_vs_named_five_d_01_to05=len(families&prior),revision_audit=str(OUT/(PREFIX+'.replacement-audit.json')))
    atomic_json(OUT/(PREFIX+'.manifest.json'),mf)
    ha.update(created_at=now(),task_sha256=sha(tp),n=600,overlap_count=0,all_questions_fresh=True,families_absent_from_all_historical_inputs=len(families-hf),families_previously_in_historical_inputs=len(families&hf),model_results_read_for_selection=False)
    atomic_json(OUT/(PREFIX+'.novelty-audit.json'),ha)
    spec=json.loads((OUT/'pilot-06.analysis-predeclaration.json').read_text());spec.update(created_at=now(),task_sha256=sha(tp),oracle_policy='oracle-policy-14',source_driven_revision=repl);atomic_json(OUT/(PREFIX+'.analysis-predeclaration.json'),spec)
    request=json.loads((OUT/'pilot-06.experiment-request.json').read_text());request.update(created_at=now(),task_file=str(tp),task_file_sha256=sha(tp),plan=str(pp),manifest=str(OUT/(PREFIX+'.manifest.json')),audit=str(OUT/(PREFIX+'.runner-audit.json')),source_review=str(OUT/'pilot-06.luk-broader-source-review.json'),replacement_audit=str(OUT/(PREFIX+'.replacement-audit.json')));atomic_json(OUT/(PREFIX+'.experiment-request.json'),request)
    status('Pilot06 source-driven revision validated','Policy14 revision preserves598 questions and replaces the veṣṭ family pair with a seeded same-cell family. All600 remain fresh, with unchanged grammar margins and300 distinct-tense pairs. No paid calls.')
    print(json.dumps(repl,indent=2));print(json.dumps(request,indent=2))
if __name__=='__main__':main()
