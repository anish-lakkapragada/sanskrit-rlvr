"""Read-only actual-manifest review. Writes only its additive review artifacts."""
from pathlib import Path
import datetime,json,hashlib,sys
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=Path(__file__).resolve().parent
from misc import vp_continuous64k as run, vp_goal as legacy, oai_batch_eval as io
from misc.vp_goal_validate import validate

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ledger=legacy.OUT/'ledger.json';ledger_before=sha(ledger)
    input_names=['execution-plan.json','requests.json','input-counts.json'];before={n:sha(OUT/n) for n in input_names}
    with patch.object(legacy,'client_for',side_effect=AssertionError('No provider call in independent review')):
        plan,tasks,requests=run.inspect_manifest(OUT,require_review=False)
        regeneration=validate(tasks,'test')
    assert plan['n']==1800 and plan['concurrency']=={'Anthropic':16,'OpenAI':16}
    assert plan['pool_caps_micro']=={'Anthropic':100000000,'OpenAI':225000000}
    state=legacy.load();assert not state.get('status','').startswith('halted')
    assert legacy.protected_allocations(state)==plan['protected_allocation']
    assert not any(j.get('attempted_at') and not j.get('settled') for j in state['jobs'].values())
    ids=set(plan['fixed_task_ids']);replay_compared=0
    for j in state['jobs'].values():
        assert j['id'] not in {plan['run_id']+'-'+p.lower() for p in run.HARD_CAPS}
        if j.get('accounting_driver')==run.VERSION:
            assert not ids&set(j['fixed_task_ids']);replay_compared+=1
        elif j.get('attempted_at') and j['phase'] in legacy.FINAL_PHASES:
            old=io.read_json(legacy.OUT/'jobs'/j['id']/'tasks.json');assert not ids&{t['id'] for t in old};replay_compared+=1
    code_review=io.read_json(ROOT/'benchmarks/parallel-search-20261007/acceleration/continuous64k-code-review-01.json')
    assert code_review['passed'] and code_review['executor_sha256']==sha(ROOT/'misc/vp_continuous64k.py') and code_review['analyzer_sha256']==sha(ROOT/'misc/vp_continuous64k_analyze.py')
    counts=io.read_json(OUT/'input-counts.json');public=io.read_json(ROOT/plan['public_prompts_path']);adoption=io.read_json(ROOT/plan['scoring_adoption_path'])
    for key,field in [('tasks_path','candidate_tasks_sha256'),('public_prompts_path','public_prompts_sha256'),('candidate_manifest_path','candidate_manifest_sha256'),('source_policy_path','source_policy_sha256'),('input_review_path','independent_input_review_sha256')]:assert adoption[field]==sha(ROOT/plan[key])
    budget={};countproof={}
    for provider in run.HARD_CAPS:
        rows=requests[provider];c=counts[provider]
        assert c['maximum']==max(c['counts'].values())<=1300 and c.get('counted_at')
        assert len(c['counts'])==1800 and c['requests_digest']==legacy.digest(rows)
        countproof[provider]={'n':1800,'minimum':min(c['counts'].values()),'maximum':max(c['counts'].values()),'requests_digest':c['requests_digest'],'counted_at':c['counted_at']}
        for i,(t,body) in enumerate(zip(tasks,rows)):
            assert run.request_for(t,provider,i)==body and legacy.digest(body)==plan['request_digests'][provider][i]
            assert body['tools']==[] and body['tool_choice']==('none' if provider=='OpenAI' else {'type':'none'})
            if provider=='Anthropic':
                assert body['model']=='claude-opus-5-5' and body['max_tokens']==65536 and body['service_tier']=='standard_only' and body['inference_geo']=='global'
                prompt=body['messages'][0]['content']
            else:
                assert body['model']=='gpt-6-astra' and body['max_output_tokens']==65536 and body['service_tier']=='default'
                prompt=body['input'][0]['content']
            assert prompt==public[i]['prompt']
        spent=legacy.committed(state,provider);protected=legacy.protected_remaining(state,provider);cap=run.HARD_CAPS[provider];pool=plan['pool_caps_micro'][provider];maximum=run.maximum(provider);window=maximum*16
        assert spent+protected+pool<=cap and window<=pool
        budget[provider]={'cap_micro':cap,'current_committed_micro':spent,'protected_remaining_micro':protected,'available_after_protection_micro':cap-spent-protected,'pool_cap_micro':pool,'margin_after_full_pool_and_protection_micro':cap-spent-protected-pool,'maximum_single_request_micro':maximum,'maximum_16_request_window_micro':window,'whole1800_worst_case_micro':1800*maximum,'maximum_pre_last_admission_settled_pool_usage_micro':pool-maximum}
    assert before=={n:sha(OUT/n) for n in input_names};assert ledger_before==sha(ledger)
    result={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'execution_plan_sha256':sha(OUT/'execution-plan.json'),'test_split_verified':True,'source_scoring_review_passed':True,'independent_input_review_sha256':sha(ROOT/plan['input_review_path']),'precision_limitations_declared':'N1800 measures iid and family sandwich/bootstrap uncertainty separately. Fourteen families supply52% of questions; neither sub1pp family SE nor benchmark readiness is promised. Family-SE failure cannot be waived by iid precision.','blockers':[],'run_id':plan['run_id'],'phase':plan['phase'],'fixed_n_per_provider':1800,'same_ordered_questions_for_both_models':True,'counts':countproof,'budget_snapshot':budget,'protected_allocation':plan['protected_allocation'],'current_ledger_status':state['status'],'ledger_before_sha256':ledger_before,'ledger_after_sha256':sha(ledger),'ledger_unchanged':True,'reviewed_dependency_count':len(plan['dependencies']),'dependencies':plan['dependencies'],'immutable_input_hashes':before,'reviewed_executor_sha256':code_review['executor_sha256'],'reviewed_analyzer_sha256':code_review['analyzer_sha256'],'code_review_receipt_sha256':sha(ROOT/'benchmarks/parallel-search-20261007/acceleration/continuous64k-code-review-01.json'),'independent_spelling_review_sha256':sha(ROOT/plan['scoring_review_path']),'scoring_adoption_sha256':sha(ROOT/plan['scoring_adoption_path']),'full_shared_regeneration':regeneration,'prior_final_jobs_checked_for_replay':replay_compared,'registration_or_paid_action_performed':False,'reviewer_script_sha256':sha(Path(__file__)),'model_outputs_read':False,'paid_calls':0,'benchmark_ready':False,'protocol_disposition':'The explicitly versioned full1800 fixed test cohort replaces legacy1000-core/extension mechanics for this run. Legacy protocols and records remain unchanged; these questions are not development tasks.','operational_conditions':['Use the exact reviewed executor and manifest; do not change membership, request limits, grading policy or order after exposure.','No answer grading until both complete1800 cohorts have terminal validated usage. No score-based stopping, retries or selective completion.','Pools bound spending and preserve all existing reserves; realized usage can exhaust a pool before1800. Such a run stays incomplete, with full reservations retained for unknown outcomes.','Every usable unrecognized answer requires source adjudication; canonical, finite-whitelist and later symmetric corrections retain separate full-panel results.','The ownership fence must block legacy paid submissions; legacy collector must continue ignoring aggregate batch_id=None records.']}
    review_path=OUT/'execution-review.json'
    if review_path.exists():raise RuntimeError('Preserve existing actual-plan review')
    review_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with patch.object(legacy,'client_for',side_effect=AssertionError('No provider call in independent review')):run.inspect_manifest(OUT,require_review=True)
    assert ledger_before==sha(ledger)
    print(json.dumps({'passed':True,'execution_plan_sha256':result['execution_plan_sha256'],'review_sha256':sha(review_path),'budget':budget,'counts':countproof},indent=2))
if __name__=='__main__':main()
