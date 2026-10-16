"""Track the four existing runs and cautiously raise Astra's live admission target.

Does not submit or retry model requests. Existing supervisors own execution,
recovery, verification and publication. Logs live outside result directories.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
RUNS = ('astra-xhigh', 'sol-xhigh', 'luna-xhigh', 'gemini4-argon-high')
RUNTIME = ROOT/'data/benchmark/archives/live-progress'


def now():
    return datetime.now(timezone.utc).isoformat()


def snapshot(name):
    folder = ROOT/'data/benchmark/results'/name
    manifest = json.loads((folder/'manifest.json').read_bytes())
    execution = manifest['execution']
    progress = execution.get('progress', {})
    statuses = {}
    for family in progress.get('families', {}).values():
        for status, count in family['statuses'].items():
            statuses[status] = statuses.get(status, 0) + count
    pid = execution.get('pid')
    try:
        if not pid:
            raise ProcessLookupError()
        os.kill(pid, 0)
        alive = True
    except ProcessLookupError:
        alive = False
    batches = execution.get('retry_batches', [])
    active = next((b for b in batches if b.get('state') == 'running'), None)
    control = folder/'run-control.json'
    target = json.loads(control.read_bytes())['concurrency'] if control.exists() else None
    return {'run': name, 'status': manifest['status'], 'published': manifest.get('artifact_layout') == 'six-file-v1',
            'pid': pid, 'worker_alive': alive, 'submission_state': execution.get('submission_state'),
            'processed': progress.get('settled'), 'planned': progress.get('planned', 20000),
            'statuses': statuses, 'cost_usd': progress.get('known_cost_usd'),
            'unknown_cost_attempts': progress.get('unknown_cost_attempts'),
            'updated_at': progress.get('updated_at'), 'concurrency': execution.get('concurrency'),
            'control_target': target, 'stopped_reason': execution.get('stopped_reason'),
            'in_flight': progress.get('unsettled_attempts', progress.get('unsettled')),
            'retry_batch': {k: active.get(k) for k in ('id', 'submitted', 'settled')} if active else None}


def next_target(current, actual, maximum, *, healthy, progressed, interval_elapsed, retrying):
    if healthy and progressed and interval_elapsed and not retrying and actual >= current:
        return min(maximum, current + 32)
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--astra-ceiling', type=int, default=256)
    args = parser.parse_args()
    if not 128 <= args.astra_ceiling <= 512:
        parser.error('Expected Astra ceiling in 128..512')
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME/'tracker.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = snapshot('astra-xhigh')
        last_increase = time.monotonic()
        while True:
            rows = [snapshot(name) for name in RUNS]
            astra = rows[0]
            pressure = astra['statuses'].get('api_error', 0) > previous['statuses'].get('api_error', 0)
            if pressure:
                last_increase = time.monotonic()
            current = astra['control_target']
            if current is not None and current < args.astra_ceiling:
                target = next_target(current, astra['concurrency'], args.astra_ceiling,
                    healthy=astra['worker_alive'] and astra['submission_state'] == 'submitting' and not pressure,
                    progressed=astra['processed'] > previous['processed'],
                    interval_elapsed=time.monotonic()-last_increase >= 60,
                    retrying=astra['retry_batch'] is not None)
                if target != current:
                    control = ROOT/'data/benchmark/results/astra-xhigh/run-control.json'
                    temp = control.with_name('run-control.tracker.tmp')
                    temp.write_text(json.dumps({'concurrency': target})+'\n')
                    temp.replace(control)
                    event = {'at': now(), 'event': 'concurrency_target', 'model': 'astra-xhigh', 'previous': current, 'target': target}
                    print(json.dumps(event), flush=True)
                    with (RUNTIME/'history.jsonl').open('a') as file:
                        file.write(json.dumps(event)+'\n')
                    last_increase = time.monotonic()
            record = {'at': now(), 'astra_target_ceiling': args.astra_ceiling, 'runs': rows}
            temp = RUNTIME/'progress.tmp'
            temp.write_text(json.dumps(record, indent=2)+'\n')
            temp.replace(RUNTIME/'progress.json')
            with (RUNTIME/'history.jsonl').open('a') as file:
                file.write(json.dumps(record)+'\n')
            print(json.dumps({'at': record['at'], 'progress': [{k:r[k] for k in ('run','status','processed','in_flight','concurrency')} for r in rows]}), flush=True)
            if all(r['published'] for r in rows):
                break
            previous = astra
            time.sleep(60)


if __name__ == '__main__':
    main()
