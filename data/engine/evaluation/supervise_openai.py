"""Run one authorized OpenAI benchmark through verification and compact export.

Gradually raises admission concurrency. It never changes prompts, effort, model,
output limits or budget allocations. Only recorded infrastructure failures are
eligible for up to two explicit recovery batches after primary completion.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_openai as runner
from data.engine.evaluation.publish_openai import publish
from data.engine.evaluation.watch_astra import notify

RUNTIME = ROOT/'data/benchmark/archives/openai-v3-runtime'


def emit(event, **fields):
    print(json.dumps({'at': runner.base.now(), 'event': event, **fields}), flush=True)


def supervise(model, concurrency_ceiling=None, retry_concurrency=4):
    ceiling = concurrency_ceiling if concurrency_ceiling is not None else (128 if model == 'astra-xhigh' else 256)
    if not 1 <= ceiling <= runner.base.MAX_CONCURRENCY:
        raise ValueError('Concurrency ceiling must be between 1 and 512')
    if not 1 <= retry_concurrency <= runner.base.MAX_CONCURRENCY:
        raise ValueError('Retry concurrency must be between 1 and 512')
    RUNTIME.mkdir(parents=True, exist_ok=True)
    folder = ROOT/'data/benchmark/results'/model
    with (RUNTIME/f'{model}.supervisor.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = json.loads((folder/'manifest.json').read_bytes())
        if manifest.get('artifact_layout') == 'six-file-v1':
            emit('already_published', model=model)
            return
        # Let the existing four-task preflight settle; never compete for its lock.
        if manifest['status'] == 'running':
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
        notified_refusal = False
        for invocation in range(3):
            manifest = json.loads((folder/'manifest.json').read_bytes())
            if manifest['status'] == 'completed':
                break
            initial = min(32 if model == 'astra-xhigh' else 128, ceiling)
            runner.base.atomic_write(folder/'run-control.json', json.dumps({'concurrency': initial})+'\n')
            command = [sys.executable, '-u', str(ROOT/'data/engine/evaluation/run_openai.py'), 'run', '--folder', str(folder), '--concurrency', str(initial)]
            with (RUNTIME/f'{model}.worker.log').open('a') as log:
                child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                start, last_report, concurrency = time.monotonic(), 0, initial
                emit('worker_started', model=model, pid=child.pid, invocation=invocation+1, concurrency_ceiling=ceiling)
                while child.poll() is None:
                    elapsed = time.monotonic()-start
                    step = 16 if model == 'astra-xhigh' else 64
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
            if reason.startswith('Five consecutive transient failures') and invocation < 2:
                runner.inspect(folder, verify=True)
                emit('cooldown_before_primary_resume', model=model, reason=reason)
                time.sleep(60)
                continue
            raise RuntimeError(f'Run paused: {reason}')
        # Explicit recovery batches preserve primary failures and their unknown
        # charges. No retries of wrong answers, refusals or format failures.
        for batch_number in (1, 2):
            rows = [r for f in runner.FAMILIES for r in json.loads((folder/f'{f}.json').read_bytes())]
            failed = [r for r in rows if runner.transient_failure(r)]
            if not failed:
                break
            retry_target = min(retry_concurrency, len(failed))
            emit('infrastructure_recovery', model=model, count=len(failed), batch=batch_number, concurrency=retry_target)
            command = [sys.executable, '-u', str(ROOT/'data/engine/evaluation/retry_openai.py'), '--folder', str(folder),
                       '--batch-id', f'v3-infrastructure-recovery-{batch_number}', '--expected-count', str(len(failed)), '--concurrency', str(retry_target)]
            with (RUNTIME/f'{model}.worker.log').open('a') as log:
                outcome = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            if outcome.returncode != 0:
                raise RuntimeError('Infrastructure recovery paused/failed; inspect logs and budget reserve')
        result = publish(folder)
        emit('published', **result)
        notify(f'{model}: benchmark finished', f"20,000 verified tasks. {result['correct']/200:.2f}% exact accuracy; ${result['cost_usd']:.2f} recorded cost; {result['refusals']} refusals. Six-file results and full raw archive saved.")
        subprocess.run(['/usr/bin/osascript', '-e', 'beep 1'], capture_output=True, timeout=30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=tuple(runner.MODELS), required=True)
    parser.add_argument('--concurrency-ceiling', type=int,
                        help='Maximum admission target, including after automatic primary resumes')
    parser.add_argument('--retry-concurrency', type=int, default=4,
                        help='Concurrency for explicit infrastructure recovery batches')
    args = parser.parse_args()
    if args.concurrency_ceiling is not None and not 1 <= args.concurrency_ceiling <= runner.base.MAX_CONCURRENCY:
        parser.error('Concurrency ceiling must be between 1 and 512')
    if not 1 <= args.retry_concurrency <= runner.base.MAX_CONCURRENCY:
        parser.error('Retry concurrency must be between 1 and 512')
    model = args.model
    try:
        supervise(model, args.concurrency_ceiling, args.retry_concurrency)
    except Exception as error:
        emit('needs_review', model=model, error=str(error))
        notify(f'{model}: benchmark needs review', str(error))
        raise
