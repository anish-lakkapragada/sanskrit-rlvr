"""Reconcile terminal original batches using complete provider result receipts.

Anthropic documents errored/canceled/expired batch requests as unbilled.
This helper never submits, cancels, retries, or changes a model answer.
"""
from collections import Counter
from misc import vp_goal as r, oai_batch_eval as io
from misc.vp_simple_search_fast import ORIGINAL, OUT

SOURCE = 'https://platform.claude.com/docs/en/build-with-claude/batch-processing#retrieving-batch-results'
UNBILLED = {'errored','canceled','expired'}


def audited_cost(job, requests, rows):
    if (job['provider']!='Anthropic' or job.get('transport','batch')!='batch' or
        job['status']!='ended' or not job.get('collected_at')):
        raise ValueError('Complete terminal Anthropic batch required')
    if (job.get('batch',{}).get('processing_status')!='ended' or
        job.get('batch',{}).get('id')!=job.get('batch_id') or not job.get('batch_id')):
        raise ValueError('Terminal batch identity or state mismatch')
    expected={x['custom_id'] for x in requests}
    if len(expected)!=job['n'] or len(rows)!=job['n']:
        raise ValueError('Full unique membership required')
    seen=set();counts=Counter();cost=0
    for row in rows:
        raw=row.get('raw_batch_result') or {};cid=raw.get('custom_id')
        if cid not in expected or cid in seen:raise ValueError('Missing or duplicate billing receipt')
        seen.add(cid);outcome=raw.get('result',{});kind=outcome.get('type');counts[kind]+=1
        if kind in UNBILLED:
            if outcome.get('message'):raise ValueError('Conflicting nonbillable result')
            continue
        if kind!='succeeded':raise ValueError('Unknown result type')
        usage=outcome.get('message',{}).get('usage',{})
        for key in ['input_tokens','output_tokens']:
            if type(usage.get(key)) is not int or usage[key]<0:raise ValueError('Incomplete token billing receipt')
        if (usage['input_tokens']>r.INPUT_ALLOWANCE or usage['output_tokens']>r.PHASES[job['phase']][1]
            or usage.get('cache_creation_input_tokens',0) or usage.get('cache_read_input_tokens',0)):
            raise ValueError('Unexpected token or caching policy')
        rates=r.rates(job);cost+=usage['input_tokens']*rates['input_rate']+usage['output_tokens']*rates['output_rate']
    summary=job.get('batch',{}).get('request_counts',{})
    if summary.get('processing')!=0 or any(summary.get(k)!=counts[k] for k in ['succeeded',*sorted(UNBILLED)]):
        raise ValueError('Terminal counts disagree with complete result receipts')
    if cost>job['reservation_micro'] or cost!=job.get('actual_cost_upper_micro') or job.get('token_policy_violations'):
        raise ValueError('Cost reconciliation disagrees with collected usage or reservation')
    return cost,dict(counts)


def reconcile():
    receipts=[]
    for name in ORIGINAL.values():
        with io.lock(r.OUT):
            state=r.load();job=state['jobs'][name]
            if job.get('settled') or job['status']!='ended' or not job.get('collected_at'):continue
            _,requests=r.verify_job(job);path=r.OUT/'jobs'/name/'results.json';rows=io.read_json(path)
            cost,counts=audited_cost(job,requests,rows)
            receipt={'job':name,'reconciled_at':io.now(),'actual_cost_upper_micro':cost,
                     'counts':counts,'source':SOURCE,'source_checked_on':'2026-10-07',
                     'results_sha256':io.sha256(path),'rule':'Complete terminal per-request receipts; successful token usage plus documented zero-billed non-success types.'}
            io.atomic_json(OUT/(name+'.billing-reconciliation.json'),receipt)
            job['settled']=True;job['billing_reconciliation']=receipt;r.save(state)
            io.atomic_json(r.OUT/'jobs'/name/'summary.json',job);receipts.append(receipt)
    return receipts


if __name__=='__main__':
    print(reconcile())
