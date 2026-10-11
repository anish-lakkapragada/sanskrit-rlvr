"""Complete-panel canonical and predeclared spelling-aware development scores."""
import copy
from misc import vp_goal as r,oai_batch_eval as io
from misc.vp_simple_search_analyze import describe
from misc.vp_cartesian_analyze import completed


def analyze():
    from misc.vp_ending_screen_run import load_plan,OUT,JOB,validate_receipt
    load_plan();s=r.load();job=s['jobs'].get(JOB,{});jobdir=r.OUT/'jobs'/JOB
    value={'updated_at':io.now(),'state':'waiting_for_complete_panel','n':96,'benchmark_ready':False,
           'received':len(list(jobdir.glob('task-*.result.json'))),'settled':96 if job.get('settled') else 0,
           'cost_upper_usd':job.get('actual_cost_upper_micro',0)/1e6 if job.get('settled') else 0,
           'committed_usd':(job.get('actual_cost_upper_micro',0) if job.get('settled') else job.get('reservation_micro',0))/1e6,
           'execution':io.read_json(OUT/'execution.json') if (OUT/'execution.json').exists() else {'state':'prepared'}}
    if not job.get('settled') or not job.get('collected_at'):
        io.atomic_json(OUT/'analysis.json',value);return value
    tasks,requests=r.verify_job(job);raw=io.read_json(jobdir/'results.json')
    if (job['provider']!='Anthropic' or job['phase']!='confirm_64k' or job.get('transport')!='direct' or
        len(raw)!=96 or [x['task'] for x in raw]!=tasks):raise ValueError('Frozen result protocol/membership differs')
    aliases={x['task_id']:x for x in io.read_json(OUT/'alias-policy.json')['items']}
    expanded=copy.deepcopy(raw);changes=[];message_ids=set()
    for req,row,out in zip(requests,raw,expanded):
        effective=io.read_json(jobdir/(req['custom_id']+'.effective-request.json'))
        expected=dict(req['params'],service_tier='standard_only',inference_geo='global')
        if effective['params']!=expected or effective['canonical_request_digest']!=r.digest(req) or effective['effective_body_digest']!=r.digest(expected):
            raise ValueError('Unexpected effective SDK parameters')
        body=row['raw_batch_result']['result']['message'];validate_receipt(body)
        if body['id'] in message_ids:raise ValueError('Reused provider message')
        message_ids.add(body['id'])
        item=aliases[row['task']['id']]
        if set(item['canonical_forms_devanagari'])!=set(row['task']['gold_devanagari']):raise ValueError('Changed canonical key')
        if row['is_correct'] is not None:
            acceptable={io.normalize(x) for x in item['canonical_forms_devanagari']+item['aliases_devanagari']}
            out['is_correct']=row.get('answer_normalized') in acceptable
            if out['is_correct']!=row['is_correct']:changes.append({'task_id':row['task']['id'],'canonical_correct':row['is_correct'],'alias_aware_correct':out['is_correct'],'answer':row.get('answer')})
    primary=describe(tasks,expanded);canonical=describe(tasks,raw)
    wrong=[x for x in expanded if completed(x) and x['is_correct'] is False]
    errors={'families':len({x['task']['campaign']['root_family'] for x in wrong}),
            'classes':len({x['task']['dhatu']['gana'] for x in wrong}),
            'cells':len({x['task']['campaign']['sampling_cell']['label'] for x in wrong})}
    st=primary['statistics'];usable=st['completed_answer']['n']
    numerical=bool(usable>=92 and st['all_request']['accuracy']<.9 and st['completed_answer']['accuracy']<.9
                   and errors['families']>=8 and errors['classes']>=3 and errors['cells']>=3)
    value.update(state='complete_pending_independent_review',primary=primary,canonical=canonical,
                 spelling_alias_changes=changes,raw_error_coverage=errors,numerical_gate_before_source_adjudication=numerical,
                 source_supported_gate_passed=False,independent_miss_review_required=True)
    io.atomic_json(OUT/'analysis.json',value);return value


if __name__=='__main__':print(analyze()['state'])
