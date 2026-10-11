"""Independent all-attempted audit:3599 genuine receipts plus exact837 infrastructure hole."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,copy,datetime,hashlib,importlib.util,json,math,re,sys,unicodedata
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=Path(__file__).resolve().parent;OVERLAY=OUT.parent;RUN=OVERLAY.parent
spec=importlib.util.spec_from_file_location("independent_carry_driver",OVERLAY/"continue.py")
carry=importlib.util.module_from_spec(spec);spec.loader.exec_module(carry)
from misc import vp_continuous64k as execution, vp_goal as legacy
from misc.vp_cartesian_prompt_v1 import render

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def normalize(s):return unicodedata.normalize('NFC',s.strip())
def extract(s):
    if not isinstance(s,str):return None
    matches=re.findall(r'<answer>(.*?)</answer>',s,re.DOTALL)
    return (matches[0].strip() or None) if len(matches)==1 else None

def analysis_header(path):
    """Read only the first five exact metadata values; never read following answer data."""
    with path.open() as f:
        consumed=0
        def char():
            nonlocal consumed
            c=f.read(1);consumed+=1
            if not c or consumed>2048:raise ValueError('Missing or oversized primary-analysis header')
            return c
        def nonspace():
            c=char()
            while c.isspace():c=char()
            return c
        def string(first=None):
            c=first if first is not None else nonspace()
            if c!='"':raise ValueError('Require exact string metadata')
            raw=c;escaped=False
            while True:
                c=char();raw+=c
                if c=='"' and not escaped:return json.loads(raw)
                if c=='\\' and not escaped:escaped=True
                else:escaped=False
        if nonspace()!='{':raise ValueError('Primary analysis must be an object')
        result={}
        for key in ['updated_at','state','execution_plan_sha256','scheduling_amendment_sha256','n']:
            if string()!=key:raise ValueError('Unexpected primary-analysis header order/key')
            if nonspace()!=':':raise ValueError('Malformed primary-analysis header')
            first=nonspace()
            if key=='n':
                token=first
                while True:
                    c=char()
                    if c==',':break
                    token+=c
                if not token.strip().isdigit():raise ValueError('Invalid primary-analysis size')
                value=int(token)
            else:
                value=string(first)
                if key=='state' and value!='complete_attempted_pending_independent_source_adjudication':
                    raise ValueError('Primary analysis is not complete; no answer access')
                if nonspace()!=',':raise ValueError('Malformed primary-analysis metadata separator')
            result[key]=value
        return result

def require_read_permission(directory,plan,plan_sha,progress,jobs,amendment_sha):
    """Only accounting/header metadata; refuse before any answer-bearing file read."""
    if set(progress)!=set(execution.HARD_CAPS) or set(jobs)!=set(execution.HARD_CAPS):
        raise ValueError('Both fixed provider accounts required; no answer access')
    for provider in execution.HARD_CAPS:
        p=progress[provider];job=jobs[provider]
        expected=plan['n']-(provider=='OpenAI')
        if (p.get('fixed_n')!=plan['n'] or p.get('admitted')!=plan['n'] or
                p.get('terminal_usage')!=expected or len(job['request_accounts'])!=plan['n'] or
                job.get(carry.NOVEL)):
            raise ValueError('All nonheld fixed receipts must settle; no answer access')
        unknown={int(i) for i,r in job['request_accounts'].items() if r['state']!='settled'}
        if unknown!=({carry.KNOWN} if provider=='OpenAI' else set()):
            raise ValueError('Only exact837 infrastructure exception; no answer access')
        if provider=='Anthropic' and (not p.get('complete') or p.get('operational_failure')):
            raise ValueError('Anthropic incomplete; no answer access')
        if provider=='OpenAI' and (p.get('complete') or (p.get('operational_failure') or {}).get('index')!=carry.KNOWN):
            raise ValueError('Original held failure/completion changed; no answer access')
    header=analysis_header(directory/'analysis.json')
    if (header['n']!=plan['n'] or header['execution_plan_sha256']!=plan_sha or
            header['scheduling_amendment_sha256']!=amendment_sha):
        raise ValueError('Completed additive analysis belongs to another cohort/amendment')
    return header

def missing_grade():
    return dict(output_text=None,status='infrastructure_error',truncated=False,refusals=[],
        answer=None,answer_normalized=None,canonical_correct=None,finite_correct=None,usable=False,
        finite_spelling_grade=dict(answer=None,canonical_correct=False,alias_aware_correct=False,
            requires_source_adjudication=False,status='unparsed'))

def grade_response(provider,body,item):
    """Independent implementation of the frozen extraction/status/finite matching contract."""
    if provider=='Anthropic':
        text=''.join(x.get('text','') for x in body.get('content',[]) if x.get('type')=='text')
        stop=body.get('stop_reason');truncated=stop in {'max_tokens','model_context_window_exceeded'}
        refusals=[text] if stop=='refusal' else []
        status='incomplete' if truncated or stop in {'pause_turn','tool_use'} else ('refused' if refusals else 'completed')
        api_error=False
    else:
        texts=[];refusals=[]
        for message in body.get('output') or []:
            if message.get('type')!='message':continue
            for x in message.get('content') or []:
                if x.get('type')=='output_text':texts.append(x.get('text',''))
                elif x.get('type')=='refusal':refusals.append(x.get('refusal',''))
        text=''.join(texts);truncated=(body.get('incomplete_details') or {}).get('reason')=='max_output_tokens'
        api_error=body.get('status') in {'failed','cancelled'} or bool(body.get('error'))
        status='api_error' if api_error else ('incomplete' if body.get('status')=='incomplete' else ('refused' if refusals else 'completed'))
    extracted=extract(text);normal=normalize(extracted) if extracted is not None else None
    canonical=normal in {normalize(x) for x in item['canonical_forms_devanagari']}
    recognized=normal in {normalize(x) for x in item['canonical_forms_devanagari']+item['aliases_devanagari']}
    answer=None if api_error else extracted
    usable=status=='completed' and answer is not None and not truncated
    return dict(output_text=text,status=status,truncated=truncated,refusals=refusals,answer=answer,
        answer_normalized=None if api_error else normal,canonical_correct=None if api_error else canonical,
        finite_correct=None if api_error else recognized,usable=usable,
        finite_spelling_grade=dict(answer=extracted,canonical_correct=canonical,alias_aware_correct=recognized,
            requires_source_adjudication=extracted is not None and not recognized,
            status='recognized' if recognized else ('unparsed' if extracted is None else 'unrecognized_pending_source_review')))

def statistics(rows,field):
    groups=defaultdict(lambda:[0,0,0,0]);statuses=Counter()
    for r in rows:
        correct=r[field] is True;usable=r['usable'];v=groups[r['family']]
        v[0]+=correct;v[1]+=1;v[2]+=correct and usable;v[3]+=usable;statuses[r['status']]+=1
    def ratio(a,b):
        denominator=sum(v[b] for v in groups.values());num=sum(v[a] for v in groups.values())
        if not denominator:return dict(n=0,accuracy=None,root_cluster_sandwich_standard_error=None)
        p=num/denominator;g=len(groups);residual=sum((v[a]-p*v[b])**2 for v in groups.values())
        return dict(n=denominator,correct=num,accuracy=p,iid_standard_error=math.sqrt(p*(1-p)/denominator),
            root_cluster_sandwich_standard_error=math.sqrt(g/(g-1)*residual)/denominator if g>1 else None)
    allstat=ratio(0,1);usable=ratio(2,3);n=len(rows)
    return dict(fixed_n=n,result_rows=n,all_results_present=True,root_families=len(groups),statuses=dict(statuses),
        truncated=sum(r['truncated'] for r in rows),unscored_results=sum(r[field] is None for r in rows),
        all_request=allstat,completed_answer=usable,
        missing_answer_accuracy_bounds=[usable.get('correct',0)/n,(usable.get('correct',0)+n-usable['n'])/n])

def different(a,b):
    if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
        return not math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-12)
    return a!=b

def review():
    pin=read(OUT/'review-manifest.json')
    for name,h in pin['review_files'].items():
        if sha(OUT/name)!=h:raise ValueError('Independent reviewer changed: '+name)
    if sha(RUN/'execution-plan.json')!=pin['execution_plan_sha256']:raise ValueError('Exact execution plan changed')
    plan,tasks,requests=execution.inspect_manifest(RUN)
    if plan['n']!=1800 or plan['run_id']!=pin['run_id']:raise ValueError('Only the pinned1800 run is supported')
    guard=carry.Guard(RUN,OVERLAY,plan,requests)
    if guard.amendment_sha!=pin['continuation_amendment_sha256']:raise ValueError('Continuation amendment changed')
    accounting=guard.accounting
    state=legacy.load();jobs=guard.state(state,adopted=True,allow_active=True)
    progress=accounting.snapshot()
    require_read_permission(OVERLAY,plan,pin['execution_plan_sha256'],progress,jobs,guard.amendment_sha)
    output=OUT/'completed-review'
    if output.exists():raise ValueError('Preserve prior completed review; investigate additively')
    # The exact all-attempted/3599-receipt gate and completed additive analysis now permit response access.
    analysis_path=OVERLAY/'analysis.json';primary_hash=sha(analysis_path);analysis=read(analysis_path)
    if set(analysis['primary'])!=set(execution.HARD_CAPS) or set(analysis['canonical'])!=set(execution.HARD_CAPS):raise ValueError('Primary analysis missing a reference')
    for group in ['primary','canonical']:
        for provider in execution.HARD_CAPS:
            s=analysis[group][provider]['statistics']
            if not s['all_results_present'] or s['fixed_n']!=1800 or s['result_rows']!=1800:raise ValueError('Primary analysis is not full1800')
    if Counter(t['campaign']['sampling_cell']['label'] for t in tasks)!= {'short_adanta_non_aorist':936,'other_adanta_aorist':144,'broad_non_curadi':720}:raise ValueError('Fixed composition differs from the reviewed1800 design')
    if len({t['id'] for t in tasks})!=1800:raise ValueError('Duplicate fixed question')
    aliases=read(ROOT/plan['alias_policy_path']);public=read(ROOT/plan['public_prompts_path'])
    itemmap={i['task_id']:i for i in aliases['items']};source_hashes={str(analysis_path.relative_to(RUN)):primary_hash};disagreements=[];models={};queues={};audited={};sensitivity_models={}
    for t,p in zip(tasks,public):
        if render(t)!=p['prompt'] or t['id']!=p['id']:raise ValueError('Public input changed')
        altered=copy.deepcopy(t);altered.update(gold_slp1=['PRIVATE'],gold_devanagari=['PRIVATE'],campaign={'private':'PRIVATE'},aliases_devanagari=['PRIVATE']);altered['dhatu']['code']='PRIVATE'
        if render(altered)!=p['prompt']:raise ValueError('Private key contaminates the prompt')
    state=legacy.load()
    for provider in execution.HARD_CAPS:
        job=accounting.job(state,provider)
        canonical_path=OVERLAY/'results'/provider/'canonical.json';finite_path=OVERLAY/'results'/provider/'predeclared-spelling.json'
        for path in [canonical_path,finite_path]:source_hashes[str(path.relative_to(RUN))]=sha(path)
        canonical=read(canonical_path);finite=read(finite_path)
        if len(canonical)!=1800 or len(finite)!=1800 or [r['task'] for r in canonical]!=tasks or [r['task'] for r in finite]!=tasks:raise ValueError('Primary result membership changed')
        rows=[];pending=[];ids=set();changed=[]
        for i,(t,body,item) in enumerate(zip(tasks,requests[provider],aliases['items'])):
            path=RUN/'receipts'/provider/f'{i:05d}.http.json';intent_path=path.with_name(f'{i:05d}.intent.json');account=job['request_accounts'][str(i)]
            if item['task_id']!=t['id']:raise ValueError('Alias order changed')
            intent=read(intent_path)
            if intent['body']!=body or intent['request_digest']!=legacy.digest(body) or account['request_digest']!=legacy.digest(body):raise ValueError('Request identity mismatch')
            source_hashes[str(intent_path.relative_to(RUN))]=sha(intent_path)
            if provider=='OpenAI' and i==carry.KNOWN:
                error_path=path.with_name(f'{i:05d}.error.json')
                if (path.exists() or sha(error_path)!=pin['acknowledged_failure']['error_sha256'] or
                    sha(intent_path)!=pin['acknowledged_failure']['intent_sha256'] or
                    account['state']!='reserved_unknown' or account['maximum_cost_micro']!=3291800 or
                    'actual_cost_upper_micro' in account or account.get('response_id')):
                    raise ValueError('Exact held infrastructure evidence changed')
                source_hashes[str(error_path.relative_to(RUN))]=sha(error_path)
                row=missing_grade();row.update(receipt_sha256=None,response_id=None,error_sha256=sha(error_path))
            else:
                if account['state']!='settled' or sha(path)!=account['receipt_sha256']:raise ValueError('Raw receipt digest/state differs from ledger')
                receipt=read(path)
                if receipt['status_code']!=200:raise ValueError('Unexpected HTTP status')
                response=receipt['body'];cost=execution.validated_cost(provider,response)
                if cost!=account['actual_cost_upper_micro'] or response['id']!=account['response_id'] or response['id'] in ids:raise ValueError('Settled usage/response identity mismatch')
                ids.add(response['id']);source_hashes[str(path.relative_to(RUN))]=sha(path)
                row=grade_response(provider,response,item);row.update(receipt_sha256=account['receipt_sha256'],response_id=response['id'])
            row.update(task_id=t['id'],index=i,family=t['campaign']['root_family'],cell=t['campaign']['sampling_cell']['label'],gana=t['dhatu']['gana'])
            expected_wire={'custom_id':f'task-{i:05d}','params':body} if provider=='Anthropic' else {'custom_id':f'task-{i:05d}','method':'POST','url':'/v1/responses','body':body}
            for label,saved,correctfield in [('canonical',canonical[i],'canonical_correct'),('finite',finite[i],'finite_correct')]:
                if saved.get('task_index')!=i or saved.get('request')!=expected_wire or saved.get('phase')!=execution.PHASE or saved.get('transport')!='direct':raise ValueError('Primary row request/index/protocol changed')
                for field in ['output_text','status','truncated','refusals','answer','answer_normalized']:
                    if different(saved.get(field),row[field]):disagreements.append(dict(provider=provider,index=i,task_id=t['id'],layer=label,field=field,saved=saved.get(field),independent=row[field]))
                if saved['is_correct'] is not row[correctfield]:disagreements.append(dict(provider=provider,index=i,task_id=t['id'],layer=label,field='is_correct',saved=saved['is_correct'],independent=row[correctfield]))
            if provider=='OpenAI' and i==carry.KNOWN:
                for label,saved in [('canonical',canonical[i]),('finite',finite[i])]:
                    if (saved.get('original_request_unresolved') is not True or saved.get('raw_batch_result') is not None or
                            saved.get('collected_at') is not None or (saved.get('error') or {}).get('code')!='acknowledged_http_502_without_response'):
                        disagreements.append(dict(provider=provider,index=i,layer=label,field='explicit_infrastructure_provenance'))
            if finite[i].get('finite_spelling_grade')!=row['finite_spelling_grade']:disagreements.append(dict(provider=provider,index=i,task_id=t['id'],field='finite_spelling_grade',saved=finite[i].get('finite_spelling_grade'),independent=row['finite_spelling_grade']))
            if row['canonical_correct'] is not row['finite_correct']:changed.append(dict(task_id=t['id'],canonical_correct=row['canonical_correct'],alias_aware_correct=row['finite_correct'],answer=row['finite_spelling_grade']['answer']))
            if row['usable'] and row['finite_spelling_grade']['requires_source_adjudication']:
                pending.append(dict(task_id=t['id'],index=i,answer=row['answer'],output_text=row['output_text'],task=t,canonical_forms_devanagari=item['canonical_forms_devanagari'],predeclared_aliases_devanagari=item['aliases_devanagari'],receipt_sha256=row['receipt_sha256'],disposition='pending_primary_source_adjudication_not_certified_error'))
            rows.append(row)
        for group,field in [('canonical','canonical_correct'),('primary','finite_correct')]:
            computed=statistics(rows,field);models.setdefault(provider,{})[group]=computed;saved=analysis[group][provider]['statistics']
            for k,v in computed.items():
                if isinstance(v,dict) and k in ['all_request','completed_answer']:
                    for kk,vv in v.items():
                        if different(saved[k].get(kk),vv):disagreements.append(dict(provider=provider,layer=group,field=k+'.'+kk,saved=saved[k].get(kk),independent=vv))
                elif different(saved.get(k),v):disagreements.append(dict(provider=provider,layer=group,field=k,saved=saved.get(k),independent=v))
        if provider=='OpenAI':
            for group,field in [('canonical','canonical_correct'),('primary','finite_correct')]:
                for label,truth in [('missing_incorrect',False),('missing_correct',True)]:
                    imputed=copy.deepcopy(rows);imputed[carry.KNOWN][field]=truth
                    computed=statistics(imputed,field)
                    sensitivity_models.setdefault(group,{})[label]=computed
                    saved=analysis['infrastructure_sensitivity'][group][label]['statistics']
                    for k in ['all_request','completed_answer']:
                        for kk,vv in computed[k].items():
                            if different(saved[k].get(kk),vv):disagreements.append(dict(provider=provider,layer=group,imputation=label,field=k+'.'+kk,saved=saved[k].get(kk),independent=vv))
        if changed!=analysis['spelling_changes'][provider]:disagreements.append(dict(provider=provider,field='spelling_changes',saved=analysis['spelling_changes'][provider],independent=changed))
        expected_pending=[{'task_id':r['task_id'],'answer':r['answer'],'task':r['task']} for r in pending]
        if expected_pending!=analysis['unrecognized_usable_answers'][provider]:disagreements.append(dict(provider=provider,field='unrecognized_usable_answers',saved=analysis['unrecognized_usable_answers'][provider],independent=expected_pending))
        queues[provider]=pending;audited[provider]=rows
    transitions=Counter(f'{int(o["finite_correct"] is True)}->{int(a["finite_correct"] is True)}' for o,a in zip(audited['Anthropic'],audited['OpenAI']))
    delta=(sum(r['finite_correct'] is True for r in audited['OpenAI'])-sum(r['finite_correct'] is True for r in audited['Anthropic']))/1800
    if dict(transitions)!=analysis['paired']['transitions_opus_to_astra'] or not math.isclose(delta,analysis['paired']['all_request_accuracy_difference'],abs_tol=1e-12):disagreements.append(dict(field='paired_transition_or_difference',independent_transitions=dict(transitions),independent_delta=delta))
    paired_imputations={}
    for label,truth in [('missing_incorrect',False),('missing_correct',True)]:
        astra=copy.deepcopy(audited['OpenAI']);astra[carry.KNOWN]['finite_correct']=truth
        transitions_i=Counter(f'{int(o["finite_correct"] is True)}->{int(a["finite_correct"] is True)}' for o,a in zip(audited['Anthropic'],astra))
        delta_i=(sum(r['finite_correct'] is True for r in astra)-sum(r['finite_correct'] is True for r in audited['Anthropic']))/1800
        paired_imputations[label]=dict(transitions=dict(transitions_i),accuracy_difference=delta_i)
        saved=analysis['infrastructure_sensitivity']['paired'][label]
        if dict(transitions_i)!=saved['transitions_opus_to_astra'] or not math.isclose(delta_i,saved['all_request_accuracy_difference'],abs_tol=1e-12):
            disagreements.append(dict(field='paired_imputation',imputation=label,independent=paired_imputations[label]))
    if analysis.get('original_analyzer_complete_gate_passed') is not False or analysis.get('benchmark_ready') is not False:
        disagreements.append(dict(field='original_gate_or_readiness_must_remain_false'))
    reported=analysis.get('expected_transport_failures') or []
    if (len(reported)!=1 or reported[0].get('provider')!='OpenAI' or reported[0].get('index')!=carry.KNOWN or
            reported[0].get('task_id')!=tasks[carry.KNOWN]['id'] or reported[0].get('response_received') is not False or
            reported[0].get('usage_settled') is not False or reported[0].get('maximum_liability_micro')!=3291800 or
            reported[0].get('request_digest')!=pin['acknowledged_failure']['request_digest'] or
            reported[0].get('error_sha256')!=pin['acknowledged_failure']['error_sha256'] or
            different(reported[0].get('accuracy_bound_width'),1/1800)):
        disagreements.append(dict(field='exact_infrastructure_missing_provenance_or_bounds'))
    if any(sha(RUN/p)!=h for p,h in source_hashes.items()):raise ValueError('A primary result changed during independent review')
    if any(sha(ROOT/p)!=h for p,h in plan['dependencies'].items()):raise ValueError('Frozen dependency changed during review')
    result=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=not disagreements,mechanical_review_only=True,n_per_provider=1800,provider_responses=3599,explicit_infrastructure_missing=1,missing_index=carry.KNOWN,paired_imputations=paired_imputations,infrastructure_sensitivity=sensitivity_models,original_complete_gate_met=False,execution_plan_sha256=pin['execution_plan_sha256'],review_manifest_sha256=sha(OUT/'review-manifest.json'),primary_analysis_sha256=primary_hash,models=models,composition=dict(Counter(t['campaign']['sampling_cell']['label'] for t in tasks)),all_public_prompts_private_key_isolation_passed=True,unrecognized_usable_queue_sizes={p:len(q) for p,q in queues.items()},score_disagreement_count=len(disagreements),source_adjudication_complete=False,qualification_changed=False,benchmark_ready=False,paid_calls=0,ledger_writes=0,all_attempted_guard_passed=True,result_fingerprints=source_hashes,limitations=['Independent extraction/status/finite matching and analyticSE reproduction; canonical oracle validity remains a source-review question.','Primary family/class bootstraps are not independently regenerated here; iid and unstratified family sandwichSE are.','All3599 genuine receipts plus the exact837 hold and completed additive analysis were required before any provider response read. Original full-completion reviewer remains unchanged. No outcomes selected or dropped.','Unknown usable answers remain pending source review; matching canonical/finite forms does not itself certify all lexical paradigms.'])
    output.mkdir()
    for provider in execution.HARD_CAPS:
        (output/(provider+'-regraded.json')).write_text(json.dumps(audited[provider],ensure_ascii=False,indent=2)+'\n')
        (output/(provider+'-source-adjudication-queue.json')).write_text(json.dumps(queues[provider],ensure_ascii=False,indent=2)+'\n')
    (output/'score-disagreements.json').write_text(json.dumps(disagreements,ensure_ascii=False,indent=2)+'\n')
    (output/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','n_per_provider','score_disagreement_count','unrecognized_usable_queue_sizes','benchmark_ready']}))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--review',action='store_true');args=parser.parse_args()
    if not args.review:parser.error('Pass --review only after3599 genuine receipts, exact837 hold and additive primary analysis complete; use test_review.py for offline smoke tests')
    review()
