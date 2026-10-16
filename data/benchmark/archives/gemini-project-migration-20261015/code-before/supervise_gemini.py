"""Run one authorized Gemini benchmark through verification and compact export.

Gradually raises admission concurrency. It never changes prompts, effort, model,
output limits or budget allocations. Only recorded infrastructure failures are
eligible for explicit recovery batches after primary completion. Unattended
mode continues through temporary capacity failures with increasing cooldowns.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_gemini as runner
from data.engine.evaluation.publish_gemini import publish
from data.engine.evaluation.watch_astra import notify

RUNTIME = ROOT/'data/benchmark/archives/gemini-v3-runtime'


def emit(event, **fields):
    print(json.dumps({'at': runner.base.now(), 'event': event, **fields}), flush=True)


def monitor_state(model, state, **fields):
    record = {'at': runner.base.now(), 'model': model, 'state': state,
              'supervisor_pid': os.getpid(), **fields}
    runner.base.atomic_write(RUNTIME/f'{model}.supervision.json', json.dumps(record, indent=2)+'\n')


def cooldown(model, seconds, reason):
    resume_at = (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()
    monitor_state(model, 'cooling_down', reason=reason, seconds=seconds, resume_at=resume_at)
    emit('cooldown_before_resume', model=model, reason=reason, seconds=seconds, resume_at=resume_at)
    time.sleep(seconds)


def supervise(model, concurrency_ceiling=None, unattended=False, initial_cooldown=0):
    ceiling = concurrency_ceiling if concurrency_ceiling is not None else 64
    if not 1 <= ceiling <= runner.base.MAX_CONCURRENCY:
        raise ValueError('Concurrency ceiling must be between 1 and 512')
    RUNTIME.mkdir(parents=True, exist_ok=True)
    folder = ROOT/'data/benchmark/results'/model
    with (RUNTIME/f'{model}.supervisor.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = json.loads((folder/'manifest.json').read_bytes())
        if manifest.get('artifact_layout') == 'six-file-v1':
            monitor_state(model, 'completed')
            emit('already_published', model=model)
            return
        # Let the existing four-task preflight settle; never compete for its lock.
        if manifest['status'] == 'running':
            monitor_state(model, 'waiting_for_worker', worker_pid=manifest['execution'].get('pid'))
            emit('waiting_for_preflight', model=model, pid=manifest['execution'].get('pid'))
        while manifest['status'] == 'running':
            pid = manifest['execution'].get('pid')
            if not pid:
                raise RuntimeError('Running manifest has no worker PID')
            os.kill(pid, 0)
            time.sleep(5)
            manifest = json.loads((folder/'manifest.json').read_bytes())
        # Never repair a crashed process without journal inspection.
        with (folder/'run.lock').open('a+') as run_lock:
            fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            runner.inspect(folder, verify=True)
        if initial_cooldown and manifest['status'] != 'completed':
            cooldown(model, initial_cooldown, 'Operator-requested cooldown after repeated Google capacity errors')
        notified_refusal = False
        invocation, pressure_restarts = 0, 0
        while True:
            manifest = json.loads((folder/'manifest.json').read_bytes())
            if manifest['status'] == 'completed' or manifest['execution'].get('retry_batches'):
                break
            priority = manifest['api']['headers_without_credentials'].get('X-Vertex-AI-LLM-Shared-Request-Type') == 'priority'
            initial = min(4 if unattended else 32 if priority else 16, ceiling)
            before = manifest['execution'].get('progress', {}).get('settled', 0)
            invocation += 1
            runner.base.atomic_write(folder/'run-control.json', json.dumps({'concurrency': initial})+'\n')
            command = [sys.executable, '-u', str(ROOT/'data/engine/evaluation/run_gemini.py'), 'run', '--folder', str(folder), '--concurrency', str(initial)]
            with (RUNTIME/f'{model}.worker.log').open('a') as log:
                child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                start, last_report, concurrency = time.monotonic(), 0, initial
                monitor_state(model, 'running', worker_pid=child.pid, unattended=unattended, concurrency_ceiling=ceiling)
                emit('worker_started', model=model, pid=child.pid, invocation=invocation, concurrency_ceiling=ceiling)
                while child.poll() is None:
                    elapsed = time.monotonic()-start
                    step = 4 if unattended else 32 if priority else 4
                    target = min(ceiling, initial+step*int(elapsed//60))
                    if target != concurrency:
                        runner.base.atomic_write(folder/'run-control.json', json.dumps({'concurrency': target})+'\n')
                        concurrency = target
                        emit('concurrency_target', model=model, target=target)
                    current = json.loads((folder/'manifest.json').read_bytes())
                    progress = current['execution'].get('progress', {})
                    if elapsed-last_report >= 60:
                        emit('progress', model=model, status=current['status'], progress=progress)
                        last_report = elapsed
                    refusals = sum(f['statuses'].get('refused', 0) for f in progress.get('families', {}).values())
                    if refusals and not notified_refusal:
                        notify(f'{model}: refusal detected', f'{refusals} provider-reported refusal(s). Saved in the result JSON; the run continues without retrying refusals.')
                        notified_refusal = True
                    time.sleep(5)
                emit('worker_exited', model=model, exit_code=child.returncode)
            current = json.loads((folder/'manifest.json').read_bytes())
            reason = current['execution'].get('stopped_reason') or ''
            if child.returncode != 0:
                raise RuntimeError('Worker exited with an error; inspect the saved log and journals')
            if current['status'] == 'completed':
                break
            if reason.startswith('Five consecutive transient failures') and (unattended or invocation < 3):
                runner.inspect(folder, verify=True)
                progressed = current['execution']['progress']['settled']-before
                pressure_restarts = 1 if progressed >= 100 else pressure_restarts+1
                delay = min(1800, 300*2**min(3, pressure_restarts-1)) if unattended else 60
                cooldown(model, delay, reason)
                continue
            raise RuntimeError(f'Run paused: {reason}')
        # Explicit recovery batches preserve primary failures and their unknown
        # charges. No retries of wrong answers, refusals or format failures.
        recovery_rounds = 0
        while True:
            current = json.loads((folder/'manifest.json').read_bytes())
            batches = current['execution'].get('retry_batches', [])
            unfinished = [b for b in batches if b['state'] != 'completed']
            if len(unfinished) > 1:
                raise RuntimeError('Multiple unfinished recovery batches require inspection')
            rows = [r for f in runner.FAMILIES for r in json.loads((folder/f'{f}.json').read_bytes())]
            failed = [r for r in rows if runner.transient_failure(r)]
            if any(r['status'] in ('api_error', 'transport_error', 'unknown') and not runner.transient_failure(r) for r in rows):
                raise RuntimeError('A non-transient infrastructure error requires inspection')
            if not failed and not unfinished:
                break
            if not unattended and recovery_rounds >= 2:
                break
            if recovery_rounds:
                cooldown(model, min(1800, 300*2**min(3, recovery_rounds-1)), 'Infrastructure failures remain after retry batch')
            batch_id = unfinished[0]['id'] if unfinished else f'v3-infrastructure-recovery-{len(batches)+1}'
            expected = len(unfinished[0]['targets']) if unfinished else len(failed)
            recovery_rounds += 1
            monitor_state(model, 'retrying', batch_id=batch_id, count=expected)
            emit('infrastructure_recovery', model=model, count=expected, batch=batch_id)
            command = [sys.executable, '-u', str(ROOT/'data/engine/evaluation/retry_gemini.py'), '--folder', str(folder),
                       '--batch-id', batch_id, '--expected-count', str(expected), '--concurrency', str(min(4, expected))]
            with (RUNTIME/f'{model}.worker.log').open('a') as log:
                outcome = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            if outcome.returncode != 0:
                raise RuntimeError('Infrastructure recovery paused/failed; inspect logs and budget reserve')
        monitor_state(model, 'verifying')
        result = publish(folder)
        monitor_state(model, 'completed', result=result)
        emit('published', **result)
        notify(f'{model}: benchmark finished', f"20,000 verified tasks. {result['correct']/200:.2f}% exact accuracy; ${result['cost_usd']:.2f} gross recorded cost; {result['refusals']} refusals. Six-file results and full raw archive saved.")
        subprocess.run(['/usr/bin/osascript', '-e', 'beep 1'], capture_output=True, timeout=30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=tuple(runner.MODELS), required=True)
    parser.add_argument('--concurrency-ceiling', type=int,
                        help='Maximum admission target, including after automatic primary resumes')
    parser.add_argument('--unattended', action='store_true',
                        help='Resume temporary failures with 5–30 minute cooldowns; start at four and ramp gradually')
    parser.add_argument('--initial-cooldown', type=int, default=0,
                        help='Wait this many seconds after draining and verification before resuming')
    args = parser.parse_args()
    if args.concurrency_ceiling is not None and not 1 <= args.concurrency_ceiling <= runner.base.MAX_CONCURRENCY:
        parser.error('Concurrency ceiling must be between 1 and 512')
    if not 0 <= args.initial_cooldown <= 3600:
        parser.error('Initial cooldown must be between 0 and 3600 seconds')
    model = args.model
    try:
        supervise(model, args.concurrency_ceiling, args.unattended, args.initial_cooldown)
    except Exception as error:
        emit('needs_review', model=model, error=str(error))
        # A duplicate supervisor must not overwrite the active owner's state.
        if not isinstance(error, BlockingIOError):
            monitor_state(model, 'needs_review', error=str(error))
        notify(f'{model}: benchmark needs review', str(error))
        raise
