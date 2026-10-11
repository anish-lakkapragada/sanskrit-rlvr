"""Collect no data itself: wait for the fixed pilot06 receipt, then analyze once."""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io, vp_goal as runner

OUT = ROOT / 'benchmarks/parallel-search-20261006/four_d/coverage-05'


def watch():
    registration = OUT / 'coordinator-registration.json'
    reg = io.read_json(registration)
    fingerprint = io.sha256(registration)
    if (reg['job_id'], reg['provider'], reg['phase'], reg['n']) != (
            'opus-four-d-pilot-06', 'Anthropic', 'confirm_64k', 96):
        raise ValueError('Unexpected fixed pilot')
    with (OUT / 'analysis-watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (OUT / 'pilot-06.analysis.json').exists():
            raise ValueError('Analysis already exists; preserve its completion receipt')
        record = dict(pid=os.getpid(), started_at=io.now(), job_id=reg['job_id'],
                      registration_sha256=fingerprint, paid_calls=0,
                      benchmark_ready=False, final_authorization=False)
        deadline = time.monotonic() + 26 * 3600
        while True:
            if io.sha256(registration) != fingerprint:
                raise ValueError('Registration changed')
            for filename, expected in reg['dependency_sha256'].items():
                if io.sha256(ROOT / filename) != expected:
                    raise ValueError('Frozen dependency changed: ' + filename)
            state = runner.load()
            job = state['jobs'][reg['job_id']]
            if any(job[k] != reg[k] for k in ('provider', 'phase', 'n', 'tasks_digest')):
                raise ValueError('Job differs from fixed registration')
            record.update(updated_at=io.now(), status='waiting_for_complete_panel',
                          provider_status=job.get('status'))
            if job.get('settled') and job.get('collected_at'):
                with (OUT / 'analysis-watch.log').open('a') as log:
                    subprocess.run([sys.executable, '-m', 'misc.vp_4d_coverage05_analyze',
                                    'analyze'], cwd=ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, check=True)
                record.update(status='complete_pending_coordinator_review',
                              analysis_sha256=io.sha256(OUT / 'pilot-06.analysis.json'))
                io.atomic_json(OUT / 'analysis-watch.json', record)
                try:
                    sound = subprocess.run(['/usr/bin/afplay', '/System/Library/Sounds/Glass.aiff'],
                                           capture_output=True, timeout=10)
                    record['completion_sound_exit_code'] = sound.returncode
                except (OSError, subprocess.TimeoutExpired) as exc:
                    record['completion_sound_error'] = str(exc)
                io.atomic_json(OUT / 'analysis-watch.json', record)
                subprocess.run([sys.executable, 'misc/vp_campaign_watch.py', '--refresh-only'],
                               cwd=ROOT, check=True)
                return record
            if time.monotonic() >= deadline or (OUT / 'analysis-watch.STOP').exists():
                record['status'] = 'stopped_incomplete'
                io.atomic_json(OUT / 'analysis-watch.json', record)
                return record
            io.atomic_json(OUT / 'analysis-watch.json', record)
            time.sleep(15)


if __name__ == '__main__':
    try:
        print(watch())
    except Exception as exc:
        io.atomic_json(OUT / 'analysis-watch.error.json',
                       dict(at=io.now(), error=str(exc), paid_calls=0))
        raise
