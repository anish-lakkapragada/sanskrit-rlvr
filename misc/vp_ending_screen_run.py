"""One frozen, budget-reserved 96-question exact4D development experiment.

This controller preserves the shared runner, canonical tasks, and raw responses.
Reviewed orthographic aliases are applied only in a separate full-panel analysis.
"""
from __future__ import annotations
import argparse
import contextlib
import fcntl
import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc import vp_goal as r,oai_batch_eval as io

OUT=ROOT/'benchmarks/parallel-search-20261007/four_d-90/ending-screen-01'
JOB='opus-ending-screen-01'
POOL='ending-screen-direct-20261007'
CAP=126_405_120


def validate_receipt(body):
    if body.get('model')!='claude-opus-5-5' or not body.get('id') or body.get('type')!='message':
        raise ValueError('Unexpected model or response identity')
    if body.get('stop_reason') not in {'end_turn','max_tokens','stop_sequence','refusal','model_context_window_exceeded'}:
        raise ValueError('Unexpected or nonterminal no-tools response')
    usage=body.get('usage') or {}
    for key,maximum in [('input_tokens',1500),('output_tokens',65536)]:
        if type(usage.get(key)) is not int or not 0<=usage[key]<=maximum:
            raise ValueError('Incomplete or out-of-policy integer usage')
    if usage.get('service_tier')!='standard' or usage.get('inference_geo')!='global':
        raise ValueError('Unexpected billing tier or geography')
    if usage.get('cache_creation_input_tokens',0) or usage.get('cache_read_input_tokens',0):
        raise ValueError('Unexpected caching')
    return usage


class StandardClient:
    def __init__(self,client,requests):
        self.client=client;self.requests={r.digest(x['params']):x for x in requests}
        if len(self.requests)!=len(requests):raise ValueError('Duplicate prompt')
        self.messages=self;self.with_raw_response=self

    def __getattr__(self,name):return getattr(self.client,name)

    def with_options(self,**options):
        return StandardClient(self.client.with_options(**options),list(self.requests.values()))

    def create(self,**params):
        load_plan()
        request=self.requests[r.digest(params)];cid=request['custom_id'];jobdir=r.OUT/'jobs'/JOB
        effective=dict(params,service_tier='standard_only',inference_geo='global')
        path=jobdir/(cid+'.effective-request.json')
        if path.exists():raise ValueError('Effective request already attempted; no replay')
        io.atomic_json(path,{'created_at':io.now(),'canonical_request_digest':r.digest(request),
                            'effective_body_digest':r.digest(effective),'params':effective})
        raw=self.client.messages.with_raw_response.create(**effective)
        body=io.capture_json(jobdir/(cid+'.effective.http.json'),raw)
        validate_receipt(body)
        return raw


def verify_inputs():
    tasks=io.read_json(OUT/'proposedtasks.json')
    if len(tasks)!=96 or len({t['id'] for t in tasks})!=96 or len({t['campaign']['root_family'] for t in tasks})!=96:
        raise ValueError('Require96 unique questions and families')
    if any(t['task_type']!='cartesian_4d' or t['prompt_version']!='cartesian-4d-v1' for t in tasks):
        raise ValueError('Exact4D protocol changed')
    aliases=io.read_json(OUT/'alias-policy.json')
    items={x['task_id']:x for x in aliases['items']}
    if len(items)!=96 or set(items)!={t['id'] for t in tasks}:raise ValueError('Alias membership differs')
    for t in tasks:
        if set(items[t['id']]['canonical_forms_devanagari'])!=set(t['gold_devanagari']):
            raise ValueError('Canonical key differs from source-reviewed alias map')
    review=io.read_json(OUT/'independent-source-review.json')
    if review.get('bounded_execution_review_passed') is not True or review.get('unresolved_blockers'):
        raise ValueError('Independent bounded execution review not passed')
    for path,sha in review['input_hashes'].items():
        if io.sha256(ROOT/path)!=sha:raise ValueError('Reviewed input changed:'+path)
    for filename,key in [('alias-policy.json','policy_sha256'),('alias_policy.py','helper_sha256')]:
        if io.sha256(OUT/filename)!=review['alias_review'][key]:
            raise ValueError('Reviewed spelling policy changed:'+filename)
    proposal=io.read_json(OUT/'plan.json')
    if (proposal['tasks_sha256']!=io.sha256(OUT/'proposedtasks.json') or
        proposal['source_review']['independent_review_sha256']!=io.sha256(OUT/'independent-source-review.json') or
        proposal['scoring']['alias_policy_sha256']!=io.sha256(OUT/'alias-policy.json')):
        raise ValueError('Proposal is not bound to the reviewed inputs')
    from misc.vp_goal_validate import validate
    validate(tasks,'development')
    return tasks


def register():
    if (OUT/'registration.json').exists():return load_plan()
    tasks=verify_inputs();s=r.load()
    preview=dict(id=JOB,provider='Anthropic',phase='confirm_64k',n=96,transport='direct',attempted_at=None)
    if r.budget_gate(s,preview)!=CAP:raise ValueError('Changed maximum reservation')
    dependencies=[Path(__file__),ROOT/'misc/vp_ending_screen_analyze.py',ROOT/'misc/vp_goal.py',
                  ROOT/'misc/vp_goal_validate.py',ROOT/'misc/ant_batch_eval.py',ROOT/'misc/oai_batch_eval.py',
                  ROOT/'misc/vp_simple_search_analyze.py',ROOT/'misc/vp_cartesian_final_analyze.py',
                  OUT/'proposedtasks.json',OUT/'alias-policy.json',OUT/'plan.json',
                  OUT/'alias_policy.py',OUT/'manifest.json',
                  OUT/'independent-source-review.json',OUT/'primary-source-controls.json',OUT/'task-path-audit.json']
    dependencies.extend(ROOT/path for path in io.read_json(OUT/'independent-source-review.json')['input_hashes'])
    plan={'created_at':io.now(),'job':JOB,'provider':'Anthropic','model':'claude-opus-5-5',
          'phase':'confirm_64k','transport':'direct','effort':'xhigh','max_output_tokens':65536,'maximum_concurrency':8,
          'n':96,'tasks_digest':r.digest(tasks),'pool_id':POOL,'additional_cap_micro':CAP,
          'effective_sdk_additions':{'service_tier':'standard_only','inference_geo':'global'},
          'rationale':'Distinct grammar-defined ending-interaction hypothesis across96 families/10classes. Prior matching19/19correct makes this low-confidence discovery, not an established hardness lead.',
          'primary_scoring':'CanonicalVPgold plus exact predeclared per-item licensed spelling aliases; preserve canonical-only secondary score and all raw outputs. Independently adjudicate every actual miss before source-supported error gate.',
          'decision':'All96 attempted; >=92usable; all-request and usable accuracy<90%; source-supported errors in >=8families, >=3classes, >=3cells. Unresolved spellings are not source-supported errors. No final qualification.',
          'stopping':'No accuracy-based stopping, paid retries, resampled tasks, or automatic second-reference calls. Unknown usage retains full reservation and stops for review.',
          'pricing_checked_on':'2026-10-07','pricing_source':'https://platform.claude.com/docs/en/models/opus-5-5/overview',
          'rates_per_million':{'input':4,'output':20},'protected_allocation':r.protected_allocations(s),
          'dependencies':{str(p.relative_to(ROOT)):io.sha256(p) for p in dependencies},'benchmark_ready':False}
    with io.lock(r.OUT):
        s=r.load();r.budget_gate(s,preview)
        io.atomic_json(OUT/'registration.json',plan)
        s.setdefault('submission_pools',{})[POOL]={'provider':'Anthropic','cap_micro':CAP,'job_ids':[JOB],
                                                  'plan_sha256':io.sha256(OUT/'registration.json')}
        r.save(s)
        registry=io.read_json(r.OUT/'experiment-registry.json')
        registry['authorized_task_digests'].append(r.digest(tasks))
        registry['experiments'].append({'id':JOB,'provider':'Anthropic','phase':'confirm_64k','transport':'direct',
            'n':96,'tasks_digest':r.digest(tasks),'registered_at':io.now(),'rationale':plan['rationale'],
            'coordinator_registration_sha256':io.sha256(OUT/'registration.json')})
        io.atomic_json(r.OUT/'experiment-registry.json',registry)
    return load_plan()


def load_plan():
    plan=io.read_json(OUT/'registration.json');s=r.load()
    for path,sha in plan['dependencies'].items():
        if io.sha256(ROOT/path)!=sha:raise ValueError('Frozen dependency changed:'+path)
    expected={'provider':'Anthropic','cap_micro':CAP,'job_ids':[JOB],'plan_sha256':io.sha256(OUT/'registration.json')}
    if s.get('submission_pools',{}).get(POOL)!=expected:raise ValueError('Spending pool changed')
    if plan['additional_cap_micro']!=CAP or plan['protected_allocation']!=r.protected_allocations(s):
        raise ValueError('Budget allocation changed')
    return plan


def execute():
    with (OUT/'executor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);load_plan()
        job=r.prepare(JOB,OUT/'proposedtasks.json','Anthropic','confirm_64k',transport='direct')
        with io.lock(r.OUT):
            s=r.load();s['jobs'][JOB]['spending_pool_id']=POOL;r.save(s)
        if job.get('settled') and job.get('collected_at'):return
        r.count_inputs(JOB);load_plan();job=r.load()['jobs'][JOB];_,requests=r.verify_job(job)
        spec=importlib.util.spec_from_file_location('vp_ending_scoped_runner',ROOT/'misc/vp_goal.py')
        run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
        run.client_for=lambda provider:StandardClient(r.client_for(provider),requests)
        io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'running','job':JOB,'n':96})
        try:
            with (OUT/'runner.log').open('a') as log,contextlib.redirect_stdout(log):
                if job.get('attempted_at'):
                    if job.get('batch_id')==('direct-'+JOB):run.collect(JOB)
                    else:raise ValueError('Prior uncertain submission; never replay')
                else:run.submit(JOB);run.collect(JOB)
            job=r.load()['jobs'][JOB]
            if not job.get('settled') or not job.get('collected_at'):raise ValueError('Incomplete billing settlement')
            io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'complete','n':96,
                                               'cost_upper_usd':job['actual_cost_upper_micro']/1e6})
        except Exception as exc:
            io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'stopped_for_review',
                                               'reason':type(exc).__name__+': '+str(exc)})
            raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['register','execute'])
    args=parser.parse_args();register() if args.command=='register' else execute()
