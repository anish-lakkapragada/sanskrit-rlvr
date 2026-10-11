"""Wait for an entire fixed development panel, then run its frozen analysis.

No provider calls, retries, membership changes, or final authorization. The
collector and fixed confirmation executor operate as separate processes.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io, vp_goal as runner


def run(directory, hours=26):
    directory = Path(directory).resolve()
    manifest_path = directory / 'coordinator-execution.json'
    manifest_hash = io.sha256(manifest_path)
    manifest = io.read_json(manifest_path)
    chunks = manifest['chunks']
    if manifest['fixed_n'] != 2400 or len(chunks) != 2:
        raise ValueError('Only the fixed two-chunk development confirmation is supported')
    if any(c['provider'] != 'Anthropic' or c['phase'] != 'confirm' or c['n'] != 1200 for c in chunks):
        raise ValueError('Unexpected confirmation protocol')
    with (directory / 'analysis-watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = io.now()
        deadline = time.monotonic() + hours * 3600
        while True:
            if io.sha256(manifest_path) != manifest_hash:
                raise ValueError('Fixed confirmation manifest changed')
            ledger = runner.load()
            jobs = [ledger['jobs'].get(c['id'], {}) for c in chunks]
            for chunk, job in zip(chunks, jobs):
                if any(job.get(k) != chunk[k] for k in ('provider', 'phase', 'n', 'tasks_digest')):
                    raise ValueError('Registered job differs from the fixed panel')
            complete = all(j.get('settled') and j.get('collected_at') for j in jobs)
            record = {'pid': os.getpid(), 'started_at': started, 'updated_at': io.now(),
                      'manifest_sha256': manifest_hash, 'status': 'waiting_for_both_chunks',
                      'paid_calls': 0, 'final_authorization': False}
            if complete:
                result_paths = [runner.OUT / 'jobs' / c['id'] / 'results.json' for c in chunks]
                target = directory / 'aggregate-analysis.json'
                if not target.exists():
                    for path, expected in manifest['dependency_sha256'].items():
                        if io.sha256(ROOT / path) != expected:
                            raise ValueError('Frozen dependency changed before analysis: ' + path)
                    with (directory / 'aggregate-analysis.log').open('a') as log:
                        subprocess.run([sys.executable, '-m', 'misc.vp_5d_analyze_07',
                                        'analyze', str(directory), *map(str, result_paths)],
                                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                aggregate = io.read_json(target)
                if (not aggregate.get('all_chunks_present') or aggregate.get('fixed_n') != 2400
                    or [x['sha256'] for x in aggregate['result_sources']]
                       != [io.sha256(p) for p in result_paths]):
                    raise ValueError('Existing aggregate does not match both completed chunks')
                record['status'] = 'complete_pending_coordinator_review'
                record['aggregate_sha256'] = io.sha256(target)
                io.atomic_json(directory / 'analysis-watch.json', record)
                subprocess.run([sys.executable, 'misc/vp_campaign_watch.py', '--refresh-only'],
                               cwd=ROOT, check=True)
                return record
            if (directory / 'analysis-watch.STOP').exists() or time.monotonic() >= deadline:
                record['status'] = 'stopped_incomplete'
                io.atomic_json(directory / 'analysis-watch.json', record)
                return record
            io.atomic_json(directory / 'analysis-watch.json', record)
            time.sleep(15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.directory)))
    except Exception as exc:
        io.atomic_json(args.directory / 'analysis-watch.error.json',
                       {'at': io.now(), 'error': str(exc), 'paid_calls': 0})
        raise
