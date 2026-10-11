"""Offline first-attempt analysis with one explicit infrastructure-missing row.

Never makes API calls or updates accounting. Never runs before all other1799
OpenAI receipts and all1800 Anthropic receipts are settled. Original output stays
untouched. A separate independent analysis review is mandatory before reading
any successful response body.
"""
from __future__ import annotations
import argparse
import copy
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reviewed_carry_driver',HERE/'continue.py')
carry=importlib.util.module_from_spec(spec);spec.loader.exec_module(carry)
original,legacy,io=carry.original,carry.legacy,carry.io
from misc import ant_batch_eval as ant
from misc import vp_continuous64k_analyze as frozen_analysis
from misc.vp_simple_search_analyze import describe,paired,SEED,B
from misc.vp_cartesian_final_analyze import panel_statistics


def ready(progress,jobs):
    """Metadata-only gate; no response body is loaded here."""
    if not carry.all_attempted(progress):return False
    for provider,job in jobs.items():
        if len(job['request_accounts']) != carry.FINAL_N:return False
        unknown={int(i) for i,r in job['request_accounts'].items() if r['state']!='settled'}
        if unknown != ({carry.KNOWN} if provider=='OpenAI' else set()):return False
        if job.get(carry.NOVEL):return False
    return True


def contrast(astra,opus,*,imputation=None):
    value=paired(astra,opus)
    value['direction']='Astra minus Opus; same complete fixed question membership'
    value['transitions_opus_to_astra']=value.pop('transitions_creation_to_modification')
    value['limitation']=('Infrastructure-missing Astra row is false only in this lower-bound counting convention, not a model error. See paired sensitivity and explicit missing index.'
                         if imputation is None else
                         'This paired statistic hypothetically imputes the missing answer as '+str(imputation)+'. No observed model answer is asserted; genuine usable pairs are unchanged.')
    value['infrastructure_imputation']=imputation
    value['infrastructure_missing_indices']=[carry.KNOWN]
    return value


def sensitivity(tasks,rows,*,repetitions=B):
    """Imputation copies only; original result rows and their missingness stay intact."""
    require=carry.require
    require(len(rows)==len(tasks) and rows[carry.KNOWN]['is_correct'] is None,'Expected unscored infrastructure hole')
    result={}
    for label,correct in [('missing_incorrect',False),('missing_correct',True)]:
        imputed=copy.deepcopy(rows)
        imputed[carry.KNOWN]['is_correct']=correct
        # Keep status/answer missing, so usable-answer counts remain genuine.
        stats=panel_statistics(tasks,imputed,repetitions=repetitions,seed=SEED)
        result[label]=dict(infrastructure_imputation=correct,statistics=stats,
                          limitation='Hypothetical fixed-N accuracy/SE calculation only; no observed answer or terminal usage is fabricated.')
    return result


def numerical(models,imputations):
    stats=[m['statistics'] for m in models.values()]
    upper_below=all(s['missing_answer_accuracy_bounds'][1]<.9 and
                    s['completed_answer']['accuracy'] is not None and s['completed_answer']['accuracy']<.9 for s in stats)
    variants=[models['Anthropic']['statistics']]+[v['statistics'] for v in imputations.values()]
    def precise(field):
        return all(v[label].get(field) is not None and v[label][field]<.01
                   for v in variants for label in ['all_request','completed_answer'])
    return dict(both_references_complete=False,all_questions_attempted=True,
        original_complete_gate_met=False,both_below_90_before_source_adjudication=False,
        both_below_90_with_all_missing_answer_upper_bounds=bool(upper_below),
        both_iid_se_below_one_pp_under_both_infrastructure_imputations=precise('iid_standard_error'),
        both_family_se_below_one_pp_under_both_infrastructure_imputations=precise('root_cluster_sandwich_standard_error'),
        both_iid_se_below_one_pp=precise('iid_standard_error'),
        both_family_se_below_one_pp=precise('root_cluster_sandwich_standard_error'),
        source_adjudication_complete=False,benchmark_ready=False,
        limitation='This prospective all-attempted protocol is distinct from the original all-responses-complete qualification gate. Family dependence and source review still apply.')


def check_review(overlay,guard):
    review=io.read_json(overlay/'analysis-review.json')
    carry.require(review.get('passed') is True and
        review.get('analyzer_sha256')==io.sha256(Path(__file__))==io.sha256(overlay/'analyze.py') and
        review.get('tests_sha256')==io.sha256(overlay/'test_analyze.py') and
        review.get('driver_sha256')==io.sha256(overlay/'continue.py') and
        review.get('execution_plan_sha256')==guard.plan_sha and
        review.get('continuation_amendment_sha256')==guard.amendment_sha,
        'Separate independent analysis review must bind exact code/protocol/amendment')


def analyze(directory,overlay):
    directory,overlay=Path(directory).resolve(),Path(overlay).resolve()
    with carry.prior.coordinator(directory):
        plan,tasks,requests=original.inspect_manifest(directory)
        guard=carry.Guard(directory,overlay,plan,requests)
        check_review(overlay,guard)
        state=legacy.load();jobs=guard.state(state,adopted=True,allow_active=True)
        progress=guard.accounting.snapshot()
        if not ready(progress,jobs):
            return dict(state='waiting_for_all_attempts_and_settled_remaining_receipts',progress=progress,
                        scores_visible=False,benchmark_ready=False)
        execution=io.read_json(directory/'execution.json')
        carry.require(execution.get('state')=='complete_attempted_pending_paired_analysis' and
                      execution.get('scheduling_amendment_sha256')==guard.amendment_sha,
                      'Final attempted-state/continuation identity not recorded')
        # First successful response-body access happens strictly below the gate.
        receipts=carry.receipt_bindings(directory,requests,jobs)
        scorer_spec=importlib.util.spec_from_file_location('frozen_carry_scorer',legacy.ROOT/plan['scorer_path'])
        scorer_module=importlib.util.module_from_spec(scorer_spec);scorer_spec.loader.exec_module(scorer_module)
        scorer=scorer_module.FiniteScorer()
        canonical_models,primary_models,rowsets,canonical_rows,changes,pending={},{},{},{},{},{}
        collected_at=io.now()
        for provider in original.HARD_CAPS:
            originals,wrapped=[],[]
            for i,(task,body) in enumerate(zip(tasks,requests[provider])):
                cid=f'task-{i:05d}'
                wire=(dict(custom_id=cid,params=body) if provider=='Anthropic' else
                      dict(custom_id=cid,method='POST',url='/v1/responses',body=body))
                row=io.base_record(task,i,wire,plan['run_id'],provider)
                row.update(transport='direct',phase=original.PHASE)
                originals.append(row)
                if provider=='OpenAI' and i==carry.KNOWN:continue
                response=io.read_json(directory/'receipts'/provider/f'{i:05d}.http.json')['body']
                wrapped.append(dict(custom_id=cid,result=dict(type='succeeded',message=response)) if provider=='Anthropic' else
                               dict(custom_id=cid,response=dict(status_code=200,body=response)))
            synthetic_batch=dict(id=plan['run_id']+'-'+provider,status='completed',processing_status='ended')
            canonical=(ant.assemble if provider=='Anthropic' else io.assemble)(originals,wrapped,synthetic_batch,collected_at)
            if provider=='OpenAI':
                missing=canonical[carry.KNOWN]
                missing.update(status='infrastructure_error',is_correct=None,output_text=None,answer=None,answer_normalized=None,
                    raw_batch_result=None,collected_at=None,original_request_unresolved=True,
                    error=dict(code='acknowledged_http_502_without_response',status_code=502,
                               usage_unknown=True,maximum_liability_micro=original.maximum('OpenAI')))
            primary,changes[provider],pending[provider]=frozen_analysis.spelling_rows(canonical,scorer)
            canonical_models[provider]=describe(tasks,canonical);primary_models[provider]=describe(tasks,primary)
            for model,rows in [(canonical_models[provider],canonical),(primary_models[provider],primary)]:
                n=len(tasks);correct=sum(x['is_correct'] is True for x in rows)
                model['statistics']['genuine_response_receipts']=n-(provider=='OpenAI')
                model['statistics']['expected_infrastructure_missing']=int(provider=='OpenAI')
                model['statistics']['infrastructure_only_accuracy_bounds']=[correct/n,(correct+int(provider=='OpenAI'))/n]
                if provider=='OpenAI':
                    model['statistics']['all_request_interpretation']='Known correct/1800, a lower bound with one unscored infrastructure attempt; not1800 observed Bernoulli answers.'
            rowsets[provider]=primary;canonical_rows[provider]=canonical
        primary_sensitivity=sensitivity(tasks,rowsets['OpenAI'])
        canonical_sensitivity=sensitivity(tasks,canonical_rows['OpenAI'])
        paired_sensitivity={}
        for label,correct in [('missing_incorrect',False),('missing_correct',True)]:
            imputed=copy.deepcopy(rowsets['OpenAI']);imputed[carry.KNOWN]['is_correct']=correct
            paired_sensitivity[label]=contrast(imputed,rowsets['Anthropic'],imputation=correct)
        missing=dict(provider='OpenAI',index=carry.KNOWN,task_id=tasks[carry.KNOWN]['id'],http_status=502,
            response_received=False,usage_settled=False,maximum_liability_micro=original.maximum('OpenAI'),
            request_digest=plan['request_digests']['OpenAI'][carry.KNOWN],
            error_sha256=receipts['OpenAI'][carry.KNOWN]['error_sha256'],
            accuracy_bound_width=1/len(tasks),accuracy_bound_width_percentage_points=100/len(tasks))
        value=dict(updated_at=io.now(),state='complete_attempted_pending_independent_source_adjudication',
            execution_plan_sha256=guard.plan_sha,scheduling_amendment_sha256=guard.amendment_sha,n=len(tasks),
            canonical=canonical_models,primary=primary_models,paired=contrast(rowsets['OpenAI'],rowsets['Anthropic']),
            spelling_changes=changes,unrecognized_usable_answers=pending,
            numerical=numerical(primary_models,primary_sensitivity),expected_transport_failures=[missing],
            infrastructure_sensitivity=dict(primary=primary_sensitivity,canonical=canonical_sensitivity,paired=paired_sensitivity),
            original_analyzer_complete_gate_passed=False,source_corrections=[],benchmark_ready=False,
            declaration='Every original question remains. Index837 is an unscored infrastructure outage, never a linguistic model error. '
                        'No retry, outcome-driven filtering, substitution or fake settlement. Both missing-answer imputations and genuine usable-answer statistics are reported. '
                        'Known+unknown actual liabilities remain charged in the existing ledger. Every unrecognized usable answer still requires independent source adjudication.')
        for provider in original.HARD_CAPS:
            io.atomic_json(overlay/'results'/provider/'canonical.json',canonical_rows[provider])
            io.atomic_json(overlay/'results'/provider/'predeclared-spelling.json',rowsets[provider])
        io.atomic_json(overlay/'analysis.json',value)
        return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,default=HERE.parent)
    parser.add_argument('--overlay',type=Path,default=HERE);args=parser.parse_args()
    print(analyze(args.directory,args.overlay)['state'])
