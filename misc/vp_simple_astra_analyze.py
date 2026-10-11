"""Full200 Astra versus the frozen full200 direct Opus creation panel."""
from misc import vp_goal as r, oai_batch_eval as io
from misc.vp_simple_search_analyze import describe, paired

OUT=r.ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01'


def analyze():
    from misc.vp_simple_astra_compare import load_plan, validate_receipt
    plan=load_plan();s=r.load();jobs=[s['jobs'].get(x['id'],{}) for x in plan['stages']]
    value={'updated_at':io.now(),'state':'waiting_for_complete_panel','n':200,'benchmark_ready':False,
           'plan_sha256':io.sha256(OUT/'plan.json'),
           'execution':io.read_json(OUT/'execution.json') if (OUT/'execution.json').exists() else {'state':'prepared'},
           'received':sum(len(list((r.OUT/'jobs'/x['id']).glob('task-*.result.json'))) for x in plan['stages']),
           'settled':sum(j['n'] for j in jobs if j.get('settled')),
           'cost_upper_usd':sum(j.get('actual_cost_upper_micro',0) for j in jobs if j.get('settled'))/1e6,
           'committed_usd':sum(j.get('actual_cost_upper_micro',0) if j.get('settled') else j.get('reservation_micro',0) for j in jobs)/1e6}
    if not all(j.get('settled') and j.get('collected_at') for j in jobs):
        io.atomic_json(OUT/'analysis.json',value);return value
    tasks,_=r.verify_job(s['jobs'][plan['source_job']]);astra=[];message_ids=set()
    for stage,job in zip(plan['stages'],jobs):
        chunk,requests=r.verify_job(job);jobdir=r.OUT/'jobs'/job['id']
        if job['provider']!='OpenAI' or job['phase']!='confirm_64k' or job.get('transport')!='direct':
            raise ValueError('Unexpected Astra protocol')
        rows=io.read_json(jobdir/'results.json')
        if len(rows)!=len(chunk) or [x['task'] for x in rows]!=chunk:raise ValueError('Result membership changed')
        for req,row in zip(requests,rows):
            effective=io.read_json(jobdir/(req['custom_id']+'.effective-request.json'))
            if (effective['body']!=dict(req['body'],service_tier='default') or
                effective['canonical_request_digest']!=r.digest(req) or
                effective['effective_body_digest']!=r.digest(effective['body'])):
                raise ValueError('Effective SDK input changed')
            raw=row['raw_batch_result']['response']['body'];validate_receipt(raw)
            if raw['id'] in message_ids:raise ValueError('Reused provider response')
            message_ids.add(raw['id'])
        astra.extend(rows)
    opus=[]
    for i in range(1,6):
        job=s['jobs'][f'opus-fast-simple4d-{i:02d}'];r.verify_job(job)
        if not job.get('settled'):raise ValueError('Unsettled Opus counterpart')
        opus.extend(io.read_json(r.OUT/'jobs'/job['id']/'results.json'))
    if len(astra)!=200 or [x['task'] for x in astra]!=tasks or [x['task'] for x in opus]!=tasks:
        raise ValueError('Primary full-panel mismatch')
    contrast=paired(astra,opus);contrast['direction']='Astra minus Opus, identical200 creation questions'
    contrast['limitation']='Paired development comparison; no held-out or top-model population qualification.'
    value.update(state='complete_pending_independent_review',astra=describe(tasks,astra),opus=describe(tasks,opus),paired=contrast)
    io.atomic_json(OUT/'analysis.json',value);return value


if __name__=='__main__':
    print(analyze()['state'])
