"""Execute a frozen development panel in sequential budget-gated chunks.

Only the coordinator registers manifests. This executor never reads model
answers and never retries a paid submission. A separate collector settles jobs.
"""
from __future__ import annotations

import argparse
import fcntl
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_cartesian_release_run import decision


def inspect(path):
    plan = io.read_json(path)
    registry = io.read_json(runner.OUT / 'experiment-registry.json')
    if io.sha256(path) not in registry.get('fixed_confirmation_manifest_sha256', []):
        raise ValueError('Fixed confirmation manifest is not registered')
    for filename, expected in plan['dependency_sha256'].items():
        if io.sha256(ROOT / filename) != expected:
            raise ValueError('Frozen confirmation dependency changed: ' + filename)
    full = io.read_json(ROOT / plan['full_tasks_path'])
    if io.sha256(ROOT / plan['full_tasks_path']) != plan['full_tasks_sha256']:
        raise ValueError('Frozen full panel changed')
    flattened = []
    for part in plan['chunks']:
        tasks = io.read_json(ROOT / part['tasks_path'])
        if io.sha256(ROOT / part['tasks_path']) != part['tasks_sha256']:
            raise ValueError('Frozen chunk changed')
        if len(tasks) != part['n'] or runner.digest(tasks) != part['tasks_digest']:
            raise ValueError('Chunk count or digest changed')
        if part['tasks_digest'] not in registry['authorized_task_digests']:
            raise ValueError('Chunk tasks are not registered')
        if (part['phase'] not in runner.CONFIRMATION_PHASES
                or part['phase'] != plan.get('phase', 'confirm')
                or part['provider'] != plan['provider']):
            raise ValueError('Confirmation phase or provider changed')
        flattened.extend(tasks)
    if (len(full) != plan['fixed_n'] or len({t['id'] for t in full}) != len(full)
            or runner.digest(flattened) != runner.digest(full)):
        raise ValueError('Chunks must exactly partition the unique frozen panel')
    return plan


def execute(path, deadline_hours=24):
    path = Path(path)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = inspect(path)
        frozen = io.sha256(path)
        deadline = time.monotonic() + deadline_hours * 3600
        record = {'started_at': io.now(), 'manifest_sha256': frozen,
                  'fixed_n': plan['fixed_n'], 'model_answers_read': False,
                  'policy': 'Sequential financial settlement only; no interim score stopping.'}
        for index, part in enumerate(plan['chunks']):
            while True:
                if io.sha256(path) != frozen:
                    raise ValueError('Frozen confirmation manifest changed')
                state = runner.load()
                job = state['jobs'].get(part['id'])
                if job is None or any(job[k] != part[k] for k in
                                      ('provider', 'phase', 'n', 'tasks_digest')):
                    raise ValueError('Prepared job differs from registered chunk')
                if state.get('status', '').startswith('halted'):
                    raise ValueError('Shared runner halted')
                if job.get('attempted_at') and not job.get('batch_id'):
                    raise ValueError('Unknown paid submission; never retry')
                record.update(updated_at=io.now(), chunk=index + 1, job=part['id'], status='waiting')
                if job.get('settled') and job.get('collected_at'):
                    break
                if path.with_suffix('.STOP').exists() or time.monotonic() >= deadline:
                    record['status'] = 'stopped_incomplete'
                    io.atomic_json(path.with_suffix('.execution.json'), record)
                    return record
                if not job.get('attempted_at'):
                    action = decision(state, job)
                    if action == 'unfunded_fixed_membership':
                        record['status'] = 'unfunded_incomplete'
                        io.atomic_json(path.with_suffix('.execution.json'), record)
                        return record
                    if action == 'submit':
                        inspect(path)
                        runner.count_inputs(part['id'])
                        runner.submit(part['id'])
                        record['status'] = 'submitted_once'
                io.atomic_json(path.with_suffix('.execution.json'), record)
                time.sleep(15)
        record.update(updated_at=io.now(), status='complete_pending_analysis')
        io.atomic_json(path.with_suffix('.execution.json'), record)
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute:
        try:
            print(execute(args.manifest))
        except Exception as exc:
            io.atomic_json(args.manifest.with_suffix('.error.json'),
                           {'at': io.now(), 'error_type': type(exc).__name__,
                            'message': str(exc), 'no_paid_retry': True})
            raise
    else:
        plan = inspect(args.manifest)
        print({'dry_run': True, 'fixed_n': plan['fixed_n'], 'chunks': len(plan['chunks']), 'paid_calls': 0})
