"""Read-only complete96 integrity review and timing-only Astra scheduling audit."""
from pathlib import Path
import collections,copy,datetime,hashlib,heapq,importlib.util,json,statistics,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from misc import vp_goal as r
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_cartesian_analyze import completed
from misc.vp_ending_screen_run import validate_receipt
from finetune.prompts import extract_answer
from misc.oai_batch_eval import normalize

OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(s):return datetime.datetime.fromisoformat(s).timestamp()

def main():
    state=r.load();job=state['jobs']['opus-ending-screen-01'];jobdir=r.OUT/'jobs'/job['id']
    assert job['settled'] and job['collected_at'] and json.loads((OUT/'execution.json').read_text())['state']=='complete'
    reg=json.loads((OUT/'registration.json').read_text())
    for f,h in reg['dependencies'].items():assert sha(ROOT/f)==h,f
    tasks,requests=r.verify_job(job);raw=json.loads((jobdir/'results.json').read_text())
    assert tasks==json.loads((OUT/'proposedtasks.json').read_text())==[x['task'] for x in raw]
    assert len(tasks)==len(raw)==len(requests)==96 and len({t['campaign']['root_family'] for t in tasks})==96
    assert r.digest(tasks)==reg['tasks_digest']
    assert job['provider']=='Anthropic' and job['phase']=='confirm_64k' and job['transport']=='direct'
    spec=importlib.util.spec_from_file_location('frozen_ending_aliases',OUT/'alias_policy.py');am=importlib.util.module_from_spec(spec);spec.loader.exec_module(am)
    policy=json.loads((OUT/'alias-policy.json').read_text());am.validate_policy(policy,tasks)
    mid=set();checks=collections.Counter();cells=collections.Counter();classes=collections.Counter();usage=collections.Counter();misses=[];alias_changes=[];proof=[]
    fingerprints={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'proposedtasks.json',OUT/'alias-policy.json',OUT/'registration.json',OUT/'analysis.json',jobdir/'tasks.json',jobdir/'requests.json',jobdir/'results.json']}
    for t,q,row in zip(tasks,requests,raw):
        cid=q['custom_id'];params=q['params'];prompt=render(t)
        assert params==dict(model='claude-opus-5-5',max_tokens=65536,messages=[{'role':'user','content':prompt}],
             thinking={'type':'adaptive','display':'summarized'},output_config={'effort':'xhigh'},tools=[],tool_choice={'type':'none'},stream=False)
        assert hashlib.sha256(prompt.encode()).hexdigest()==t['campaign']['prompt_sha256']
        altered=copy.deepcopy(t);altered['gold_slp1']=['PRIVATE_SENTINEL'];altered['gold_devanagari']=['PRIVATE_SENTINEL'];altered['campaign']={};altered['dhatu']['code']='PRIVATE_SENTINEL'
        assert render(altered)==prompt
        assert row['request']==q and row['task_id']==t['id'] and row['custom_id']==cid and row['attempt_number']==1
        intent=json.loads((jobdir/(cid+'.intent.json')).read_text());eff=json.loads((jobdir/(cid+'.effective-request.json')).read_text())
        http=json.loads((jobdir/(cid+'.effective.http.json')).read_text());http2=json.loads((jobdir/(cid+'.http.json')).read_text())
        single=json.loads((jobdir/(cid+'.result.json')).read_text())
        expected=dict(params,service_tier='standard_only',inference_geo='global')
        assert intent['request_digest']==eff['canonical_request_digest']==r.digest(q)
        assert eff['params']==expected and eff['effective_body_digest']==r.digest(expected)
        assert dt(intent['attempted_at'])<=dt(eff['created_at'])<=dt(http['received_at'])
        body=row['raw_batch_result']['result']['message'];validate_receipt(body)
        assert http['status_code']==http2['status_code']==200 and http['body']==http2['body']==body
        assert single==row['raw_batch_result'] and body['id'] not in mid;mid.add(body['id'])
        assert body['role']=='assistant' and body['stop_reason']=='end_turn'
        texts=[x['text'] for x in body['content'] if x['type']=='text'];text=''.join(texts)
        assert not any(x['type'] in {'tool_use','server_tool_use','refusal'} for x in body['content'])
        assert text==row['output_text'] and completed(row) and not row['truncated'] and not row['refusals']
        answer=extract_answer(text);canonical=normalize(answer) in {normalize(g) for g in t['gold_devanagari']}
        alias=am.grade_policy(text,t['id'],policy)
        assert answer==row['answer'] and normalize(answer)==row['answer_normalized'] and canonical==row['is_correct']
        assert alias['canonical_correct']==canonical
        if not alias['alias_aware_correct']:misses.append(t['id'])
        if canonical!=alias['alias_aware_correct']:alias_changes.append(t['id'])
        checks['protocol_public_input_exact']=checks['protocol_public_input_exact']+1
        checks['raw_receipt_and_record_exact']=checks['raw_receipt_and_record_exact']+1
        checks['usable']=checks['usable']+1;checks['canonical_correct']+=int(canonical);checks['alias_aware_correct']+=int(alias['alias_aware_correct'])
        cells[t['campaign']['sampling_cell']['label']]+=int(canonical);classes[t['dhatu']['gana']]+=1
        usage.update({k:body['usage'][k] for k in ['input_tokens','output_tokens']})
        proof.append({'task_id':t['id'],'provider_message_id':body['id'],'answer':answer,'canonical_correct':canonical,'alias_aware_correct':alias['alias_aware_correct']})
        for suffix in ['intent.json','effective-request.json','effective.http.json','http.json','result.json']:
            p=jobdir/(cid+'.'+suffix);fingerprints[str(p.relative_to(ROOT))]=sha(p)
    assert not list(jobdir.glob('task-*.error.json'))
    assert len(list(jobdir.glob('task-*.intent.json')))==len(list(jobdir.glob('task-*.result.json')))==96
    cost=usage['input_tokens']*4+usage['output_tokens']*20
    assert cost==job['actual_cost_upper_micro']==722716
    assert checks['canonical_correct']==checks['alias_aware_correct']==96 and not misses and not alias_changes
    assert all(sha(ROOT/p)==h for p,h in fingerprints.items())
    report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'complete96 integrity validated; close ending-interaction hardness hypothesis for this bounded screen',
        'checks':dict(checks),'correct_by_frozen_cell':dict(cells),'class_task_counts':dict(classes),'families':96,
        'canonical_accuracy':1.0,'alias_aware_accuracy':1.0,'refusals':0,'truncations':0,'unparsed':0,
        'source_miss_audit':{'misses':misses,'unrecognized_usable':[],'alias_score_changes':alias_changes,'disposition':'Empty because every actual returned answer matches canonical gold; earlier bounded source review remains the validity basis.'},
        'hardness_gate_passed':False,'benchmark_ready':False,'automatic_further_reference_evaluation_recommended':False,
        'usage':dict(usage),'actual_cost_usd':cost/1e6,'row_checks':proof,'fingerprints':fingerprints,
        'limitations':['Development results only, not a final benchmark.','Canonical matching does not independently certify every Sanskrit paradigm.','Does not establish every possible ending interaction is easy; rejects this prospective four-cell hardness screen.'],
        'paid_calls':0,'raw_or_frozen_mutations':False,'heldout_candidate_model_answers_read':False}
    (OUT/'independent-result-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    # Read timestamps and job accounting only for the separate Astra concurrency assessment.
    intervals=[];stages=[];durations=[];astra_cost=0
    for n in range(1,21):
        name=f'astra-simple4d-direct-{n:02d}';j=state['jobs'][name];p=r.OUT/'jobs'/name
        assert j['settled'] and j['collected_at']
        for i in range(10):
            cid=f'task-{i:05d}';a=json.loads((p/(cid+'.intent.json')).read_text())['attempted_at'];b=json.loads((p/(cid+'.effective.http.json')).read_text())['received_at']
            intervals.append((dt(a),dt(b)));durations.append(dt(b)-dt(a))
        stages.append((dt(j['attempted_at']),dt(j['collected_at'])));astra_cost+=j['actual_cost_upper_micro']
    wall=max(b for a,b in intervals)-min(a for a,b in intervals);running=maximum=0
    for _,delta in sorted([(a,1) for a,b in intervals]+[(b,-1) for a,b in intervals]):running+=delta;maximum=max(maximum,running)
    simulations={}
    for workers in [8,16,24,32]:
        q=[0.]*workers
        for sec in durations:heapq.heappush(q,heapq.heappop(q)+sec)
        simulations[str(workers)]={'seconds':max(q),'conditional_on_observed_service_durations':True}
    budget={p:{'cap_usd':r.PROVIDERS[p]['cap_micro']/1e6,'committed_usd':r.committed(state,p)/1e6,
               'protected_remaining_usd':r.protected_remaining(state,p)/1e6,
               'unprotected_remaining_usd':(r.PROVIDERS[p]['cap_micro']-r.committed(state,p)-r.protected_remaining(state,p))/1e6}
            for p in ['Anthropic','OpenAI']}
    concurrency={'created_at':report['created_at'],'reads':'Astra timing and accounting only; no response text or accuracy used',
        'wall_seconds':wall,'total_request_seconds':sum(durations),'average_concurrency':sum(durations)/wall,'maximum_observed_concurrency':maximum,
        'eight_slot_utilization':sum(durations)/(8*wall),'request_seconds':{'min':min(durations),'median':statistics.median(durations),'mean':statistics.mean(durations),'max':max(durations)},
        'between_stage_overhead_seconds':sum(max(0,stages[i+1][0]-stages[i][1]) for i in range(19)),
        'continuous_fixed_order_simulations':simulations,'actual_astra200_cost_usd':astra_cost/1e6,'budget_snapshot':budget,
        'reservation_per_astra_request_usd':3.2918,'reservation_16_requests_usd':52.6688,'reservation_32_requests_usd':105.3376,
        'recommendation':'Future-only versioned single coordinator: release the ledger lock during network waits; maintain a bounded persistent request pool, atomically reserve every admitted unit and settle only validated complete usage. All unsettled and uncertain requests retain their full maxima. No score-driven stopping, task substitution or replay.',
        'minimal_speed_option':'Continuous eight slots first; 16 or 32 slots only within separately frozen concurrency/budget policy and observed provider capacity.',
        'warning':'Do not launch multiple unchanged submit() executors: the shared lock encloses network waits. Simulations exclude rate limits, changed latency and provider queuing; they are not completion-time guarantees.',
        'read_code_hashes':{p:sha(ROOT/p) for p in ['misc/vp_goal.py','misc/vp_simple_astra_compare.py']},'paid_calls':0,'ledger_or_runner_edits':False}
    (OUT/'independent-concurrency-review.json').write_text(json.dumps(concurrency,indent=2)+'\n')
    print(json.dumps({'ending96':dict(checks),'cost_usd':cost/1e6,'astra_wall_minutes':wall/60,'astra_average_concurrency':sum(durations)/wall,'budget':budget},indent=2))

if __name__=='__main__':main()
