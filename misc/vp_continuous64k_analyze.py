"""Analyze a complete paired final cohort; no interim score or paid API calls."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

from misc import ant_batch_eval as ant, oai_batch_eval as io, vp_goal as legacy
from misc import vp_continuous64k as execution
from misc.vp_cartesian_analyze import completed
from misc.vp_simple_search_analyze import describe, paired


def spelling_rows(canonical, scorer):
    rows, changes, pending = copy.deepcopy(canonical), [], []
    for original, row in zip(canonical, rows):
        task_id = row['task']['id']
        grade = scorer.grade(row.get('output_text') or '', task_id)
        row['finite_spelling_grade'] = grade
        # Preserve transport failures/unparsed outcomes and the old canonical
        # result independently of any whitelist or later linguistic correction.
        if original['is_correct'] is not None:
            row['is_correct'] = grade['alias_aware_correct']
            if row['is_correct'] != original['is_correct']:
                changes.append(dict(task_id=task_id, canonical_correct=original['is_correct'],
                                    alias_aware_correct=row['is_correct'], answer=grade['answer']))
        if completed(row) and grade['requires_source_adjudication']:
            pending.append(dict(task_id=task_id, answer=grade['answer'], task=row['task']))
    return rows, changes, pending


def numerical_assessment(models):
    """Distinct item/family precision claims; never certify source validity here."""
    complete = set(models) == set(execution.HARD_CAPS) and all(
        x['statistics']['all_results_present'] for x in models.values())
    stats = [x['statistics'] for x in models.values()]
    difficulty = bool(complete and all(
        s['all_request']['accuracy'] < .9 and s['completed_answer']['accuracy'] is not None
        and s['completed_answer']['accuracy'] < .9 and s['missing_answer_accuracy_bounds'][1] < .9
        for s in stats))
    def precise(field):
        return bool(complete and all(s[label].get(field) is not None and s[label][field] < .01
                    for s in stats for label in ['all_request','completed_answer']))
    return dict(both_references_complete=complete, both_below_90_before_source_adjudication=difficulty,
                both_iid_se_below_one_pp=precise('iid_standard_error'),
                both_family_se_below_one_pp=precise('root_cluster_sandwich_standard_error'),
                source_adjudication_complete=False, benchmark_ready=False)


def analyze(directory):
    directory = Path(directory).resolve()
    plan, tasks, requests = execution.inspect_manifest(directory)
    plan_sha = io.sha256(directory/'execution-plan.json')
    accounting = execution.Accounting(plan, plan_sha)
    progress = accounting.snapshot()
    if not all(p['complete'] for p in progress.values()):
        # Do not load body text, grading code or any partial answers.
        return dict(state='waiting_for_complete_paired_cohort', progress=progress,
                    scores_visible=False, benchmark_ready=False)
    spec = importlib.util.spec_from_file_location('vp_frozen_final_scorer',legacy.ROOT/plan['scorer_path'])
    scorer_module = importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer_module)
    scorer = scorer_module.FiniteScorer()
    state = legacy.load()
    canonical_models, primary_models, rowsets, changes, pending = {}, {}, {}, {}, {}
    for provider in execution.HARD_CAPS:
        job = accounting.job(state, provider)
        originals, wrapped = [], []
        for i, (task, body) in enumerate(zip(tasks, requests[provider])):
            path = directory/'receipts'/provider/f'{i:05d}.http.json'
            account = job['request_accounts'][str(i)]
            if io.sha256(path) != account['receipt_sha256']:
                raise ValueError('Settled raw receipt changed')
            intent = io.read_json(directory/'receipts'/provider/f'{i:05d}.intent.json')
            if intent['body'] != body or intent['request_digest'] != execution.legacy.digest(body):
                raise ValueError('Actual paid request differs from frozen question')
            receipt = io.read_json(path)
            if receipt['status_code'] != 200:
                raise ValueError('Unexpected settled HTTP status')
            response = receipt['body']
            if (execution.validated_cost(provider,response) != account['actual_cost_upper_micro'] or
                    response['id'] != account['response_id']):
                raise ValueError('Raw receipt differs from settled usage or response identity')
            cid = f'task-{i:05d}'
            if provider == 'Anthropic':
                wire = dict(custom_id=cid,params=body)
                wrapped.append(dict(custom_id=cid,result=dict(type='succeeded',message=response)))
            else:
                wire = dict(custom_id=cid,method='POST',url='/v1/responses',body=body)
                wrapped.append(dict(custom_id=cid,response=dict(status_code=200,body=response)))
            row = io.base_record(task,i,wire,plan['run_id'],provider)
            row.update(transport='direct',phase=execution.PHASE)
            originals.append(row)
        batch = dict(id=plan['run_id']+'-'+provider,status='completed',processing_status='ended')
        canonical = (ant.assemble if provider == 'Anthropic' else io.assemble)(originals,wrapped,batch,job['collected_at'])
        primary, changes[provider], pending[provider] = spelling_rows(canonical,scorer)
        canonical_models[provider] = describe(tasks,canonical)
        primary_models[provider] = describe(tasks,primary)
        rowsets[provider] = primary
        io.atomic_json(directory/'results'/provider/'canonical.json',canonical)
        io.atomic_json(directory/'results'/provider/'predeclared-spelling.json',primary)
    contrast = paired(rowsets['OpenAI'],rowsets['Anthropic'])
    contrast['direction'] = 'Astra minus Opus; identical fixed final questions'
    contrast['transitions_opus_to_astra'] = contrast.pop('transitions_creation_to_modification')
    contrast['limitation'] = 'Fixed paired test cohort; task-mixture selection used development evidence. Report both iid and family-dependent uncertainty.'
    value = dict(updated_at=io.now(),state='complete_pending_independent_source_adjudication',
        execution_plan_sha256=plan_sha,n=plan['n'],canonical=canonical_models,primary=primary_models,
        paired=contrast,spelling_changes=changes,unrecognized_usable_answers=pending,
        numerical=numerical_assessment(primary_models),source_corrections=[],benchmark_ready=False,
        declaration='No questions are removed or selected after results. Every unrecognized usable answer needs independent source adjudication; any supported correction is symmetric across affected questions and models.')
    io.atomic_json(directory/'analysis.json',value)
    return value


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    print(analyze(parser.parse_args().directory)['state'])
