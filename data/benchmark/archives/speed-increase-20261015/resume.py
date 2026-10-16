"""Apply the authorized speed increase only after each old worker has drained."""
from copy import deepcopy
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_openai, run_gemini

ARCHIVE = Path(__file__).resolve().parent
TARGETS = {'sol-xhigh': (run_openai, 256), 'luna-xhigh': (run_openai, 256),
           'astra-xhigh': (run_openai, 128), 'gemini4-argon-high': (run_gemini, 64)}


def emit(event, **fields):
    print(json.dumps({'at': run_openai.base.now(), 'event': event, **fields}), flush=True)


def resume(name, runner, ceiling):
    folder = ROOT/'data/benchmark/results'/name
    with (folder/'run.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        m = json.loads((folder/'manifest.json').read_bytes())
        if m['status'] != 'paused' or m['execution']['progress']['unsettled']:
            raise RuntimeError(f'{name}: expected fully drained paused run')
        old_runner = ARCHIVE/Path(runner.__file__).name
        assert m['execution']['runner']['sha256'] == hashlib.sha256(old_runner.read_bytes()).hexdigest()
        previous = deepcopy(m)
        (ARCHIVE/f'{name}.drained-manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2)+'\n')
        m['execution']['runner'] = runner.descriptor(Path(runner.__file__))
        m['implementation_dependencies'].append(runner.descriptor(ROOT/'data/engine/evaluation/admission.py'))
        if runner is run_openai:
            m['budget_accounting'].update(overall_openai_target_usd=8000, additional_authorized_usd=5000,
                combined_new_run_ceiling_usd=6750,
                allocations_usd={k:v['budget_usd'] for k,v in run_openai.MODELS.items()},
                authorization='User authorized an additional $5000 for OpenAI on 2026-10-14 PDT, prioritizing speed.')
            m['execution']['budget_usd'] = runner.MODELS[name]['budget_usd']
        policy = 'Paced admission; halve concurrency on capacity errors, honor Retry-After and exponential backoff, then recover gradually after healthy traffic. Isolated connection failures remain recorded for later explicit retries and do not suspend unrelated requests. Stop after five consecutive transient failures.'
        m['execution']['failure_handling'] = policy
        m['execution']['concurrency_ceiling'] = ceiling
        m['execution'].setdefault('implementation_revisions', []).append({
            'at': runner.base.now(), 'reason': 'User-authorized speed increase; updated budgets and adaptive admission only.',
            'previous_runner': previous['execution']['runner'],
            'previous_budget_usd': previous['execution']['budget_usd'],
            'new_budget_usd': m['execution']['budget_usd'], 'concurrency_ceiling': ceiling,
            'request_settings_changed': False, 'archive': str(ARCHIVE.relative_to(ROOT)),
            'validation': '14 offline tests passed; all saved requests and results reverified against pinned prompts and journals before resume.'})
        runner.base.atomic_write(folder/'manifest.json', json.dumps(m, ensure_ascii=False, indent=2)+'\n')
        try:
            verified = runner.inspect(folder, verify=True)
            assert verified['unresolved'] == 0
        except BaseException:
            runner.base.atomic_write(folder/'manifest.json', json.dumps(previous, ensure_ascii=False, indent=2)+'\n')
            raise
        assert m['request_defaults'] == previous['request_defaults']
        assert m['tasks'] == previous['tasks']
        emit('verified', model=name, settled=verified['settled'], budget_usd=m['execution']['budget_usd'])
    provider = 'openai' if runner is run_openai else 'gemini'
    runtime = ROOT/f'data/benchmark/archives/{provider}-v3-runtime'
    with (runtime/f'{name}.supervisor.log').open('ab', buffering=0) as log:
        child = subprocess.Popen([sys.executable, '-u', str(ROOT/f'data/engine/evaluation/supervise_{provider}.py'),
            '--model', name, '--concurrency-ceiling', str(ceiling)], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    caffeinate = subprocess.Popen(['/usr/bin/caffeinate', '-dimsu', '-w', str(child.pid)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    emit('resumed', model=name, supervisor_pid=child.pid, caffeinate_pid=caffeinate.pid, concurrency_ceiling=ceiling)
    return True


if __name__ == '__main__':
    remaining = dict(TARGETS)
    while remaining:
        for name, (runner, ceiling) in list(remaining.items()):
            if resume(name, runner, ceiling):
                del remaining[name]
        if remaining:
            emit('waiting_for_existing_requests', models=list(remaining))
            time.sleep(15)
    emit('all_resumed')
