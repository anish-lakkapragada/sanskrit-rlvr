"""Frozen, same-question Astra comparison; only execute makes paid calls.

The existing shared ledger owns all caps and reservations. A scoped client
adapter makes the standard pricing tier explicit without editing the frozen
shared runner or changing any model input. Effective SDK bodies are retained.
"""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_goal as r, oai_batch_eval as io

OUT = ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01'
POOL = 'simple4d-astra-standard-20261007'
CAP = 150_000_000
SOURCE = 'opus-simple4d-90-01'


def validate_receipt(body):
    if body.get('service_tier') != 'default':
        raise ValueError('Expected explicit standard/default billing tier')
    if body.get('model') != 'gpt-6-astra' or not body.get('id'):
        raise ValueError('Unexpected model or missing response identity')
    if body.get('status') not in {'completed', 'incomplete', 'failed', 'cancelled'}:
        raise ValueError('Nonterminal direct response')
    usage = body.get('usage') or {}
    for name, maximum in [('input_tokens',1500),('output_tokens',65536)]:
        if type(usage.get(name)) is not int or not 0 <= usage[name] <= maximum:
            raise ValueError('Missing or out-of-policy integer token usage')
    if type(usage.get('total_tokens')) is not int or usage['total_tokens'] != usage['input_tokens']+usage['output_tokens']:
        raise ValueError('Inconsistent total token usage')
    for details,key,maximum in [('input_tokens_details','cached_tokens',usage['input_tokens']),
                                ('output_tokens_details','reasoning_tokens',usage['output_tokens'])]:
        n=(usage.get(details) or {}).get(key,0)
        if type(n) is not int or not 0 <= n <= maximum:
            raise ValueError('Inconsistent usage details')
    if (usage.get('input_tokens_details') or {}).get('cache_write_tokens',0):
        raise ValueError('Unexpected paid cache writes')
    return usage


class StandardClient:
    def __init__(self, client, jobdir, requests):
        self.client, self.jobdir = client, jobdir
        self.by_digest = {r.digest(x['body']):x for x in requests}
        if len(self.by_digest) != len(requests):
            raise ValueError('Duplicate effective prompt')
        self.responses = self
        self.with_raw_response = self

    def __getattr__(self, name):
        return getattr(self.client, name)

    def with_options(self, **options):
        return StandardClient(self.client.with_options(**options), self.jobdir, list(self.by_digest.values()))

    def create(self, **body):
        original = self.by_digest[r.digest(body)]
        cid = original['custom_id']
        actual = dict(body, service_tier='default')
        path = self.jobdir/(cid+'.effective-request.json')
        if path.exists():
            raise ValueError('Effective request already attempted; no replay')
        io.atomic_json(path, {'created_at':io.now(), 'canonical_request_digest':r.digest(original),
                             'effective_body_digest':r.digest(actual), 'body':actual})
        raw = self.client.responses.with_raw_response.create(**actual)
        receipt = io.capture_json(self.jobdir/(cid+'.effective.http.json'), raw)
        validate_receipt(receipt)
        return raw


def register():
    if (OUT/'plan.json').exists():
        return load_plan()
    s=r.load(); original=s['jobs'][SOURCE];tasks,_=r.verify_job(original)
    if len(tasks)!=200:raise ValueError('Expected complete frozen200')
    # These are the complete input-selected Opus questions, never its failed subset.
    stages=[]
    for start in range(0,200,10):
        name=f'astra-simple4d-direct-{start//10+1:02d}'
        path=OUT/'inputs'/(name+'.json');io.atomic_json(path,tasks[start:start+10])
        stages.append({'id':name,'start':start,'stop':start+10,'n':10,
                       'path':str(path.relative_to(ROOT)),'sha256':io.sha256(path),
                       'tasks_digest':r.digest(tasks[start:start+10])})
    plan={'created_at':io.now(),'source_job':SOURCE,'source_tasks_digest':r.digest(tasks),
          'purpose':'Same200 ordinary4D development questions after reviewed Opus175/200; no final qualification.',
          'authorization':'Continuing user-authorized benchmark search and direct acceleration within unchanged lifetime caps.',
          'provider':'OpenAI','model':'gpt-6-astra','effort':'xhigh','max_output_tokens':65536,
          'transport':'direct','service_tier':'default','maximum_concurrency':8,
          'stages':stages,'spending_pool':POOL,'additional_cap_micro':CAP,
          'maximum_per_stage_micro':32_918_000,'all200_worst_case_micro':658_360_000,
          'protected_allocation':r.protected_allocations(s),
          'accounting':'Reserve each full10 at standard rates beforePOST. Actuals plus unsettled maxima <=$150 and globalcap, protected reserves unchanged. Full200 is conditional on observed usage; no outcome-based stopping.',
          'pricing_checked_on':'2026-10-07','pricing_source':'https://developers.openai.com/api/docs/models/gpt-6-astra',
          'standard_rates_per_million':{'input':10,'output':50},
          'adapter':'Canonical requests retain existing renderer. Add only service_tier=default to actual SDK bodies, saved separately beforePOST; inspect complete terminal integer usage and billing tier before settlement.',
          'analysis':'Report only complete200 primary accuracy, usable accuracy, missing bounds, cells/families/tenses, paired Astra-minus-Opus with frozen200 counterpart; incomplete run reports completion without claimed full-panel score.',
          'stopping':'Only cost, protocol or unknown-request failures stop execution. No paid retries or task substitution. Source corrections are separate and symmetric.',
          'dependencies':{str(p.relative_to(ROOT)):io.sha256(p) for p in [
              Path(__file__),ROOT/'misc/vp_simple_astra_analyze.py',ROOT/'misc/vp_goal.py',
              ROOT/'misc/vp_goal_validate.py',ROOT/'misc/oai_batch_eval.py',
              ROOT/'misc/vp_cartesian_prompt_v1.py',ROOT/'misc/vp_simple_search_analyze.py',
              ROOT/'misc/vp_cartesian_final_analyze.py',
              OUT.parent/'four_d-90/direct-result-source-review.json']},
          'benchmark_ready':False}
    io.atomic_json(OUT/'plan.json',plan)
    with io.lock(r.OUT):
        s=r.load()
        if r.committed(s,'OpenAI')+CAP+r.protected_remaining(s,'OpenAI')>r.PROVIDERS['OpenAI']['cap_micro']:
            raise ValueError('Insufficient unprotected OpenAI allowance')
        s.setdefault('submission_pools',{})[POOL]={'provider':'OpenAI','cap_micro':CAP,
            'job_ids':[x['id'] for x in stages],'plan_sha256':io.sha256(OUT/'plan.json')}
        r.save(s)
        registry=io.read_json(r.OUT/'experiment-registry.json')
        for stage in stages:
            registry['authorized_task_digests'].append(stage['tasks_digest'])
            registry['experiments'].append(dict(stage,provider='OpenAI',phase='confirm_64k',transport='direct',
                registered_at=io.now(),rationale=plan['purpose'],coordinator_registration_sha256=io.sha256(OUT/'plan.json')))
        io.atomic_json(r.OUT/'experiment-registry.json',registry)
    return load_plan()


def load_plan():
    plan=io.read_json(OUT/'plan.json');s=r.load()
    for path,sha in plan['dependencies'].items():
        if io.sha256(ROOT/path)!=sha:raise ValueError('Frozen dependency changed: '+path)
    expected={'provider':'OpenAI','cap_micro':CAP,'job_ids':[x['id'] for x in plan['stages']],
              'plan_sha256':io.sha256(OUT/'plan.json')}
    if s.get('submission_pools',{}).get(POOL)!=expected:raise ValueError('Spending pool changed')
    if plan['additional_cap_micro']!=CAP or plan['protected_allocation']!=r.protected_allocations(s):
        raise ValueError('Budget allocation changed')
    source,_=r.verify_job(s['jobs'][SOURCE])
    if r.digest(source)!=plan['source_tasks_digest']:raise ValueError('Source changed')
    for stage in plan['stages']:
        path=ROOT/stage['path']
        if io.sha256(path)!=stage['sha256'] or io.read_json(path)!=source[stage['start']:stage['stop']]:
            raise ValueError('Stage membership changed')
    return plan


def prepare(plan):
    s=r.load();_,opus_requests=r.verify_job(s['jobs'][SOURCE])
    for stage in plan['stages']:
        j=r.prepare(stage['id'],ROOT/stage['path'],'OpenAI','confirm_64k',transport='direct')
        _,requests=r.verify_job(j)
        if [x['body']['input'] for x in requests]!=[x['params']['messages'] for x in opus_requests[stage['start']:stage['stop']]]:
            raise ValueError('Model-visible inputs differ from paired Opus')
        with io.lock(r.OUT):
            s=r.load();s['jobs'][j['id']]['spending_pool_id']=POOL;r.save(s)
        r.count_inputs(j['id'])


def execute():
    with (OUT/'executor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        plan=load_plan();prepare(plan)
        spec=importlib.util.spec_from_file_location('vp_astra_scoped_runner',ROOT/'misc/vp_goal.py')
        run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
        try:
            for stage in plan['stages']:
                load_plan();job=r.load()['jobs'][stage['id']]
                if job.get('settled') and job.get('collected_at'):continue
                _,requests=r.verify_job(job);jobdir=r.OUT/'jobs'/job['id']
                run.client_for=lambda provider:StandardClient(r.client_for(provider),jobdir,requests)
                io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'running','current_job':job['id'],'n':200})
                with (OUT/'runner.log').open('a') as log,contextlib.redirect_stdout(log):
                    if job.get('attempted_at'):
                        if job.get('batch_id') and job['batch_id'].startswith('direct-'):run.collect(job['id'])
                        else:raise ValueError('Prior uncertain submission; never replay')
                    else:run.submit(job['id']);run.collect(job['id'])
                job=r.load()['jobs'][job['id']]
                if not job.get('settled') or not job.get('collected_at'):raise ValueError('Incomplete usage; retain reservation')
                print(f"Settled {job['id']}:10 requests, ${job['actual_cost_upper_micro']/1e6:.4f}",flush=True)
            io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'complete','n':200})
        except Exception as exc:
            io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'stopped_for_review',
                'reason':type(exc).__name__+': '+str(exc),'no_retries':True})
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['register','execute'])
    args=parser.parse_args();register() if args.command=='register' else execute()
