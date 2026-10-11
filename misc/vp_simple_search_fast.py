"""User-authorized direct transport for the same frozen 600 pilot questions.

Only `execute` spends. Every 40-request stage has a locked maximum reservation;
settled usage plus outstanding maxima must stay below the extra $100 ceiling.
Never selects tasks, changes prompts, retries an attempted request, or stops on accuracy.
"""
from __future__ import annotations
import argparse
import contextlib
import copy
import fcntl
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_goal as r, oai_batch_eval as io

OUT = ROOT / 'benchmarks/parallel-search-20261007/acceleration'
POOL = 'simple-search-direct-20261007'
CAP = 100_000_000
ORIGINAL = {'four_d': 'opus-simple4d-90-01', 'modification': 'opus-modification-01',
            'control': 'opus-modification-control-01'}


def register():
    if (OUT / 'plan.json').exists():
        return load_plan()
    OUT.mkdir(parents=True, exist_ok=True)
    s = r.load()
    used = sum(j['n'] for j in s['jobs'].values() if j['provider']=='Anthropic'
               and j['phase'] in r.CONFIRMATION_PHASES and j.get('attempted_at'))
    if used + 600 > r.PHASES['confirm_64k'][2]['Anthropic']:
        raise ValueError('Insufficient remaining development phase allowance for full600')
    sources, tasks_by_arm = {}, {}
    for arm, name in ORIGINAL.items():
        j = s['jobs'][name]
        tasks, requests = r.verify_job(j)
        if j.get('collected_at') or j.get('batch', {}).get('request_counts', {}).get('succeeded', 0):
            raise ValueError('Original outcomes are available; review transport plan before proceeding')
        assert len(tasks) == 200 and j['phase'] == 'confirm_64k'
        tasks_by_arm[arm] = tasks
        sources[arm] = {'job': name, 'tasks_digest': j['tasks_digest'],
                        'requests_digest': j['requests_digest'], 'status': j['status']}
    stages = []
    for start in range(0, 200, 40):
        for arm, tasks in tasks_by_arm.items():
            label = 'simple4d' if arm == 'four_d' else arm
            name = f'opus-fast-{label}-{start//40+1:02d}'
            path = OUT / 'inputs' / (name + '.json')
            io.atomic_json(path, tasks[start:start+40])
            stages.append({'id': name, 'arm': arm, 'start': start, 'stop': start+40,
                           'path': str(path.relative_to(ROOT)), 'sha256': io.sha256(path),
                           'tasks_digest': r.digest(tasks[start:start+40]), 'n': 40})
    old_allocation = r.protected_allocations(s)
    new_allocation = copy.deepcopy(old_allocation)
    new_allocation['Anthropic']['cap_check'] = 0
    plan = {'created_at': io.now(), 'authorization': 'User requested faster execution within existing provider caps.',
            'provider': 'Anthropic', 'phase': 'confirm_64k', 'transport': 'direct',
            'model': 'claude-opus-5-5', 'effort': 'xhigh', 'max_output_tokens': 65536,
            'maximum_concurrency': 8, 'extra_cost_ceiling_micro': CAP, 'pool_id': POOL,
            'sources': sources, 'stages': stages,
            'primary_transport': 'direct for all 600 frozen questions; original batches are archived separately',
            'analysis': 'Same frozen analysis functions. Full200 creation panel and full200+200paired panels only; no interim accuracy stopping.',
            'cancellation': 'After all direct questions are settled, request cancellation of any unfinished original batches. Retain their reservations until authoritative reconciliation.',
            'stopping': 'Stop on unknown submission, incomplete usage, changed dependencies, additional$100 ceiling or global cap. Never retry or claim partial completion as full.',
            'old_reserve_allocation': old_allocation, 'new_reserve_allocation': new_allocation,
            'dependencies': {str(p.relative_to(ROOT)): io.sha256(p) for p in
                [Path(__file__), ROOT/'misc/vp_goal.py', ROOT/'misc/vp_goal_validate.py',
                 ROOT/'misc/vp_simple_search_analyze.py', ROOT/'misc/vp_simple_search_fast_analyze.py',
                 OUT/'vp_goal.before.py', ROOT/'benchmarks/parallel-search-20261007/coordinator-registration.json',
                 ROOT/'benchmarks/parallel-search-20261007/source-sensitivity-predeclaration.json']},
            'benchmark_ready': False}
    # Record the exact reserve revision before changing the ledger, without changing either hard cap.
    io.atomic_json(OUT / 'plan.json', plan)
    with io.lock(r.OUT):
        s = r.load()
        if r.protected_allocations(s) != old_allocation:
            raise ValueError('Planning reserves changed concurrently')
        s['protected_phase_minimum_questions'] = new_allocation
        s.setdefault('reserve_revisions', []).append({
            'recorded_at': io.now(), 'reason': 'User authorized faster execution. Reassign unused Anthropic sensitivity reserve to bounded direct transport; preserve final evaluation reserve and unchanged lifetime caps.',
            'old_allocation': old_allocation, 'new_allocation': new_allocation,
            'plan_sha256': io.sha256(OUT/'plan.json')})
        s.setdefault('submission_pools', {})[POOL] = {'provider': 'Anthropic', 'cap_micro': CAP,
            'job_ids': [x['id'] for x in stages], 'plan_sha256': io.sha256(OUT/'plan.json')}
        r.save(s)
        registry = io.read_json(r.OUT/'experiment-registry.json')
        for stage in stages:
            registry['authorized_task_digests'].append(stage['tasks_digest'])
            registry['experiments'].append(dict(stage, provider='Anthropic', phase='confirm_64k',
                transport='direct', registered_at=io.now(),
                rationale='User-authorized latency acceleration of identical frozen inputs; uniform direct primary transport, no accuracy selection.',
                coordinator_registration_sha256=io.sha256(OUT/'plan.json')))
        io.atomic_json(r.OUT/'experiment-registry.json', registry)
    return plan


def load_plan():
    plan = io.read_json(OUT/'plan.json')
    for path, sha in plan['dependencies'].items():
        if io.sha256(ROOT/path) != sha:
            raise ValueError('Frozen acceleration dependency changed: '+path)
    s = r.load()
    expected = {'provider': 'Anthropic', 'cap_micro': CAP,
                'job_ids': [x['id'] for x in plan['stages']], 'plan_sha256': io.sha256(OUT/'plan.json')}
    if s.get('submission_pools', {}).get(POOL) != expected:
        raise ValueError('Required exact $100 spending pool missing or changed')
    if plan['extra_cost_ceiling_micro'] != CAP or plan['new_reserve_allocation'] != r.protected_allocations(s):
        raise ValueError('Acceleration allowance changed')
    return plan


def prepare_stages(plan):
    for stage in plan['stages']:
        path = ROOT/stage['path']
        if io.sha256(path) != stage['sha256']:
            raise ValueError('Frozen stage membership changed')
        job = r.prepare(stage['id'], path, 'Anthropic', 'confirm_64k', transport='direct')
        original = r.load()['jobs'][plan['sources'][stage['arm']]['job']]
        _, old_requests = r.verify_job(original)
        _, new_requests = r.verify_job(job)
        old_counts = io.read_json(r.OUT/'jobs'/original['id']/'input-counts.json')
        if old_counts['requests_digest'] != original['requests_digest']:
            raise ValueError('Original token counts changed')
        selected = old_requests[stage['start']:stage['stop']]
        if [x['params'] for x in new_requests] != [x['params'] for x in selected]:
            raise ValueError('Direct requests differ from original frozen model inputs')
        counts = {a['custom_id']: old_counts['counts'][b['custom_id']] for a,b in zip(new_requests,selected)}
        io.atomic_json(r.OUT/'jobs'/job['id']/'input-counts.json', {
            'requests_digest': job['requests_digest'], 'counts': counts, 'counted_at': old_counts['counted_at'],
            'maximum': max(counts.values()), 'source_job': original['id'],
            'note': 'Reused provider token counts only after byte-equivalent request params verification; custom IDs alone are relabeled.'})
        with io.lock(r.OUT):
            s = r.load(); s['jobs'][job['id']]['spending_pool_id'] = POOL; r.save(s)


def cancel_originals(plan):
    for source in plan['sources'].values():
        with io.lock(r.OUT):
            s = r.load(); job = s['jobs'][source['job']]
            intent = OUT/(job['id']+'.cancel-intent.json')
            if job.get('collected_at') or job['status'] in {'ended','canceling'} or intent.exists():
                continue
            io.atomic_json(intent, {'created_at': io.now(), 'batch_id': job['batch_id'],
                                     'reason': 'Complete direct replacement exists; no remaining need for queued duplicate requests.'})
            raw = r.client_for('Anthropic').messages.batches.with_raw_response.cancel(job['batch_id'])
            body = io.capture_json(OUT/(job['id']+'.cancel.http.json'), raw)
            job.update(batch=body, status=body['processing_status']); r.save(s)


def execute():
    with (OUT/'executor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        plan = load_plan()
        prepare_stages(plan)
        try:
            for stage in plan['stages']:
                load_plan()
                job = r.load()['jobs'][stage['id']]
                if job.get('settled') and job.get('collected_at'):
                    continue
                io.atomic_json(OUT/'execution.json', {'updated_at': io.now(), 'state':'running',
                    'current_job': job['id'], 'scope':'Complete600questions; no interim score stopping'})
                # Keep per-stage scores out of the researcher's view until the whole panel is complete.
                with (OUT/'runner.log').open('a') as log, contextlib.redirect_stdout(log):
                    if job.get('attempted_at'):
                        if job.get('batch_id') and job['batch_id'].startswith('direct-'):
                            r.collect(job['id'])
                        else:
                            raise ValueError('Submission already attempted with uncertain status; never retry')
                    else:
                        r.submit(job['id']); r.collect(job['id'])
                job = r.load()['jobs'][job['id']]
                if not job.get('settled') or not job.get('collected_at'):
                    raise ValueError('Complete terminal usage needed before continuing')
                print(f"Settled {job['id']}: {job['n']} requests, ${job['actual_cost_upper_micro']/1e6:.4f}", flush=True)
            io.atomic_json(OUT/'execution.json', {'updated_at':io.now(),'state':'complete','n':600})
            cancel_originals(plan)
        except Exception as exc:
            io.atomic_json(OUT/'execution.json', {'updated_at':io.now(),'state':'stopped_for_review',
                           'reason':type(exc).__name__+': '+str(exc),'no_retries':True})
            raise


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['register','execute']);a=p.parse_args()
    register() if a.command=='register' else execute()
