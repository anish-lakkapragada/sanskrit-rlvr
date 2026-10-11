"""Execute an explicitly authorized fixed release without reading model answers.

Dry-run by default. Payment decisions depend only on frozen membership, settled
usage, outstanding maximum reservations and the unchanged provider caps. An
independent collector must reconcile submitted jobs. Never retries a paid POST.
"""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_cartesian_release import audit_partition


def inspect(directory, prefix, *, require_authorized=False):
    directory = Path(directory)
    manifest = io.read_json(directory/'manifest.json')
    tasks = io.read_json(directory/'tasks.json')
    assert io.sha256(directory/'tasks.json') == manifest['frozen_tasks_sha256']
    assert io.sha256(directory/'sampling-plan.json') == manifest['frozen_sampling_plan_sha256']
    assert len(tasks) == manifest['fixed_n']
    if manifest['reference_models'] != {p: v['model'] for p, v in runner.PROVIDERS.items()}:
        raise ValueError('Frozen reference models changed')
    for phase, protocol in manifest['reference_protocol_by_phase'].items():
        if protocol != {'effort': runner.PHASES[phase][0],
                        'max_output_tokens': runner.PHASES[phase][1]}:
            raise ValueError('Frozen reference protocol changed')
    for path, fingerprint in manifest['dependency_sha256'].items():
        if io.sha256(ROOT/path) != fingerprint:
            raise ValueError('Frozen release dependency changed: '+path)
    queue, partition = [], []
    for stage in manifest['stages']:
        path = directory/stage['path']; rows = io.read_json(path)
        assert io.sha256(path) == stage['sha256'] and runner.digest(rows) == stage['tasks_digest']
        assert len(rows) == stage['n']
        partition.append({'phase':stage['phase'],'tasks':rows})
        for provider, tag in [('Anthropic','opus'),('OpenAI','astra')]:
            queue.append({'id':f'{prefix}-{tag}-{stage["stage"]:02d}',
                          'provider':provider,'phase':stage['phase'],'n':stage['n'],
                          'tasks_digest':stage['tasks_digest'],'path':str(path),
                          'release_manifest_path':str((directory/'manifest.json').resolve()),
                          'release_manifest_sha256':io.sha256(directory/'manifest.json')})
    audit_partition(tasks,partition,manifest['track'],manifest.get('protocol_version','legacy16k-v1'))
    if require_authorized:
        gate = io.read_json(runner.OUT/'release-freeze.json')
        if (not gate.get('passed') or io.sha256(directory/'manifest.json') not in
                gate.get('authorized_release_manifest_sha256', [])):
            raise ValueError('This exact release manifest is not authorized')
        for item in queue:
            if item['tasks_digest'] not in gate.get('authorized_by_phase',{}).get(item['phase'],[]):
                raise ValueError('Frozen stage is not authorized')
    return manifest,queue


def decision(state, job):
    """Return a budget/core wait reason; unexpected invariant failures propagate."""
    try:
        runner.budget_gate(state,job)
    except ValueError as exc:
        reason = str(exc)
        if reason.startswith('Collect and settle the core'):
            return 'waiting_for_core_settlement'
        if reason.startswith('Cumulative provider cap'):
            outstanding = any(j['provider'] == job['provider'] and j.get('attempted_at')
                              and not j.get('settled') for j in state['jobs'].values())
            return 'waiting_for_settlement' if outstanding else 'unfunded_fixed_membership'
        raise
    return 'submit'


def verify_existing_stage(existing, item, manifest):
    """Legacy unbound jobs retain resume support; new protocols require binding."""
    if any(existing.get(k) != item[k] for k in ('provider','phase','n','tasks_digest')):
        raise ValueError('Existing job does not match the fixed stage')
    bound = existing.get('release_manifest_path') or existing.get('release_manifest_sha256')
    if bound or manifest.get('protocol_version', 'legacy16k-v1') != 'legacy16k-v1':
        if any(existing.get(k) != item[k] for k in ('release_manifest_path','release_manifest_sha256')):
            raise ValueError('Existing job does not match the fixed release binding')


def execute(directory, prefix, deadline_hours=12):
    directory = Path(directory)
    with (directory/'execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        manifest,queue = inspect(directory,prefix,require_authorized=True)
        manifest_sha = io.sha256(directory/'manifest.json')
        deadline = time.monotonic()+deadline_hours*3600
        started = io.now()
        while True:
            if io.sha256(directory/'manifest.json') != manifest_sha:
                raise ValueError('Authorized manifest changed during execution')
            state = runner.load()
            if state.get('status','').startswith('halted'):
                raise ValueError('Shared ledger halted; stop execution')
            finished = 0
            for item in queue:
                existing = state['jobs'].get(item['id'])
                if not existing:
                    continue
                verify_existing_stage(existing, item, manifest)
                if existing.get('attempted_at') and not existing.get('batch_id'):
                    raise ValueError('Unknown paid submission; never retry')
                finished += bool(existing.get('settled') and existing.get('collected_at'))
            record = {'updated_at':io.now(),'started_at':started,'pid':os.getpid(),
                      'fixed_n':manifest['fixed_n'],'manifest_sha256':manifest_sha,
                      'settled_stages':finished,'total_provider_stages':len(queue),
                      'status':'running','benchmark_ready':False,
                      'policy':'Fixed membership; no model answers read; no score-driven stopping; maximum-cost accounting.'}
            if finished == len(queue):
                record['status']='complete_pending_analysis';io.atomic_json(directory/'execution.json',record);return record
            if (directory/'STOP').exists() or time.monotonic() >= deadline:
                record['status']='stopped_incomplete';io.atomic_json(directory/'execution.json',record);return record
            reasons, ready = {}, []
            for provider in runner.PROVIDERS:
                item = next((x for x in queue if x['provider'] == provider
                             and not state['jobs'].get(x['id'],{}).get('attempted_at')),None)
                if item is None:
                    continue
                job = state['jobs'].get(item['id'])
                if job is None:
                    job = runner.prepare(item['id'],Path(item['path']),provider,item['phase'],
                                         release_manifest_path=directory/'manifest.json')
                action = decision(runner.load(),job);reasons[provider]=action
                if action == 'submit':
                    ready.append(item)
            record['provider_actions']=reasons
            if 'unfunded_fixed_membership' in reasons.values():
                record['status']='unfunded_incomplete';io.atomic_json(directory/'execution.json',record);return record
            for item in ready:
                # Count exact inputs before the single budget-locked paid POST.
                inspect(directory,prefix,require_authorized=True)
                runner.count_inputs(item['id'])
                inspect(directory,prefix,require_authorized=True)
                runner.submit(item['id'])
            io.atomic_json(directory/'execution.json',record)
            time.sleep(10)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path);parser.add_argument('--prefix',required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--deadline-hours',type=float,default=12)
    args=parser.parse_args()
    if args.execute:
        if not 0 < args.deadline_hours <= 24:
            raise ValueError('Execution deadline must be within 24 hours')
        try:
            print(execute(args.directory,args.prefix,args.deadline_hours))
        except Exception as exc:
            io.atomic_json(args.directory/'execution-error.json',{'at':io.now(),'error_type':type(exc).__name__,
                'message':str(exc),'no_paid_retry':True,'benchmark_ready':False})
            raise
    else:
        manifest,queue=inspect(args.directory,args.prefix)
        print({'dry_run':True,'fixed_n':manifest['fixed_n'],'provider_stages':len(queue),'paid_calls':0})
