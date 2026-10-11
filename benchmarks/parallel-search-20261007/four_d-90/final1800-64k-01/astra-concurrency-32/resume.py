"""Scheduling-only continuation of the original final1800 accounts.

prepare is ledger/API read-only. Only execute can append the reviewed amendment,
reserve original suffix indices, or call the OpenAI API. No response is graded.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'misc/vp_continuous64k.py').is_file())
sys.path.insert(0, str(ROOT))
from misc import vp_continuous64k as original
from misc import vp_goal as legacy, oai_batch_eval as io

VERSION = 'final1800-astra-concurrency-32-v1'
RUNTIME = {'Anthropic': 0, 'OpenAI': 32}
POOLS = {'Anthropic': 100_000_000, 'OpenAI': 225_000_000}
AMENDMENTS = 'continuous_scheduling_amendments'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sync_file(path):
    with Path(path).open('rb') as f:
        os.fsync(f.fileno())
    fd = os.open(str(Path(path).parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, value):
    """Never replace a historical checkpoint, amendment, or intent."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    sync_file(path)


@contextlib.contextmanager
def coordinator(directory):
    with (directory / 'coordinator.lock').open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def effective_accounting(plan, fingerprint):
    require(plan['pool_caps_micro'] == POOLS, 'Original 100/225 run pools required')
    effective = copy.deepcopy(plan)
    effective['concurrency'] = dict(RUNTIME)
    require({k: v for k, v in effective.items() if k != 'concurrency'} ==
            {k: v for k, v in plan.items() if k != 'concurrency'}, 'Scheduling-only overlay')
    # Unchanged class, original execution-plan identity; no new accounting job.
    return original.Accounting(effective, fingerprint)


def static_ledger(state, accounting):
    """Everything except these two evolving accounts/timestamp/amendment list."""
    value = copy.deepcopy(state)
    value.pop('updated_at', None)
    value.pop(AMENDMENTS, None)
    for provider in original.HARD_CAPS:
        value['jobs'].pop(accounting.job_id(provider))
    return value


def validate_ledger(state, accounting, *, allow_pending=False):
    """Inspect the entire liability ledger, including unrelated old accounts."""
    accounting.check_state(state)
    owned = {accounting.job_id(p) for p in original.HARD_CAPS}
    for provider in original.HARD_CAPS:
        historical = state['historical_spend_micro'][provider]
        require(type(historical) is int and historical >= 0, 'Invalid historical liability')
    for job_id, job in state['jobs'].items():
        require(job['provider'] in original.HARD_CAPS, 'Unknown provider in ledger')
        for name in ['reservation_micro', 'actual_cost_upper_micro']:
            value = job.get(name, 0)
            require(type(value) is int and value >= 0, 'Invalid ledger cost')
        if job_id not in owned:
            require(not job.get('attempted_at') or job.get('settled') is True,
                    'Unresolved liability in another job')
    jobs = {p: accounting.job(state, p) for p in original.HARD_CAPS}
    for provider, job in jobs.items():
        require(not job.get('operational_failure'), 'Existing operational_failure')
        if not allow_pending or provider == 'Anthropic':
            require(all(r['state'] == 'settled' for r in job['request_accounts'].values()),
                    'Unknown admitted request; never replay')
        else:
            require(sum(r['state'] != 'settled' for r in job['request_accounts'].values()) <= 32,
                    'More than 32 outstanding reservations')
        require(job['reservation_micro'] <= POOLS[provider], 'Run pool exceeded')
        require(legacy.committed(state, provider) + legacy.protected_remaining(state, provider)
                <= original.HARD_CAPS[provider], 'Lifetime cap or protected reserve exceeded')
    require(jobs['Anthropic']['settled'] is True, 'Anthropic must already be complete')
    return jobs


def validate_receipts(directory, requests, jobs):
    """Usage/identity audit only: never extract, grade, or print answer text."""
    result = {}
    for provider, job in jobs.items():
        rows = []
        expected = set()
        for i in range(len(job['request_accounts'])):
            record = job['request_accounts'][str(i)]
            stem = directory / 'receipts' / provider / f'{i:05d}'
            intent_path, receipt_path = stem.with_suffix('.intent.json'), stem.with_suffix('.http.json')
            expected.update([intent_path.name, receipt_path.name])
            require(not stem.with_suffix('.error.json').exists(), 'Error sidecar requires review')
            intent, receipt = io.read_json(intent_path), io.read_json(receipt_path)
            digest = legacy.digest(requests[provider][i])
            require(intent.get('body') == requests[provider][i] and
                    intent.get('request_digest') == digest == record['request_digest'],
                    'Intent differs from exact frozen request')
            sha = io.sha256(receipt_path)
            require(receipt.get('status_code') == 200 and sha == record['receipt_sha256'],
                    'Receipt status/hash changed')
            body = receipt['body']
            require(original.validated_cost(provider, body) == record['actual_cost_upper_micro']
                    and body['id'] == record['response_id'], 'Receipt identity/cost mismatch')
            rows.append(dict(index=i, request_digest=digest, intent_sha256=io.sha256(intent_path),
                             receipt_sha256=sha, account_sha256=legacy.digest(record)))
        receipt_dir = directory / 'receipts' / provider
        require({p.name for p in receipt_dir.iterdir() if p.is_file()} == expected,
                'Unexpected receipt/intent outside exact settled prefix')
        result[provider] = rows
    return result


def code_bindings(overlay):
    return {str((overlay / name).resolve()): io.sha256(overlay / name)
            for name in ['resume.py', 'test_resume.py', 'README.md', 'independent-review.json']}


def check_review(overlay, plan_sha):
    review = io.read_json(overlay / 'independent-review.json')
    require(review.get('passed') is True and review.get('execution_plan_sha256') == plan_sha
            and review.get('driver_sha256') == io.sha256(overlay / 'resume.py')
            and io.sha256(Path(__file__)) == review.get('driver_sha256')
            and review.get('tests_sha256') == io.sha256(overlay / 'test_resume.py'),
            'Independent review must bind this exact driver, tests and original plan')


def prepare(directory, overlay):
    """Save a new immutable drain checkpoint/amendment; no ledger/API writes."""
    directory, overlay = Path(directory).resolve(), Path(overlay).resolve()
    with coordinator(directory):
        plan, _, requests = original.inspect_manifest(directory)
        plan_sha = io.sha256(directory / 'execution-plan.json')
        check_review(overlay, plan_sha)
        accounting = effective_accounting(plan, plan_sha)
        require((directory / 'STOP').is_file(), 'Original STOP record required')
        status = io.read_json(directory / 'execution.json')
        require(status.get('state') in {'stopped_incomplete', 'complete_pending_paired_analysis'}
                and status.get('execution_plan_sha256') == plan_sha,
                'Original coordinator has not gracefully drained')
        require(not status.get('scheduling_amendment_sha256'), 'Use existing checkpoint for restart')
        require(not (overlay / 'STOP').exists(), 'New scheduler STOP already exists')
        with original.transaction():
            state = legacy.load()
            jobs = validate_ledger(state, accounting)
            require(status.get('providers') == accounting.snapshot(), 'Drain metadata differs from ledger')
            require(not state.get(AMENDMENTS), 'Existing scheduling amendment requires review')
            receipts = validate_receipts(directory, requests, jobs)
            checkpoint = dict(schema=VERSION, created_at=io.now(), run_id=plan['run_id'],
                execution_plan_sha256=plan_sha, dependencies=plan['dependencies'],
                runtime_concurrency=RUNTIME, original_stop_sha256=io.sha256(directory / 'STOP'),
                drain_execution=status, drain_execution_sha256=io.sha256(directory / 'execution.json'),
                ledger_sha256=io.sha256(legacy.OUT / 'ledger.json'),
                ledger_state_digest=legacy.digest(state),
                static_ledger_digest=legacy.digest(static_ledger(state, accounting)),
                original_amendments=state.get(AMENDMENTS, []),
                jobs=copy.deepcopy(jobs), receipts=receipts,
                next_indices={p: len(j['request_accounts']) for p, j in jobs.items()})
        require(not (overlay / 'checkpoint.json').exists() and not (overlay / 'amendment.json').exists(),
                'Never replace an existing checkpoint/amendment')
        write_new(overlay / 'checkpoint.json', checkpoint)
        amendment = dict(schema=VERSION, created_at=io.now(), run_id=plan['run_id'],
            execution_plan_sha256=plan_sha, checkpoint_path=str(overlay / 'checkpoint.json'),
            checkpoint_sha256=io.sha256(overlay / 'checkpoint.json'),
            runtime_concurrency=RUNTIME, dependencies=code_bindings(overlay),
            reason='User-authorized scheduling acceleration after graceful original drain; '
                   'same accounts, suffix, model inputs, xhigh/65536, caps and source policy.')
        write_new(overlay / 'amendment.json', amendment)
        return dict(state='prepared_no_ledger_or_api_mutation', next_indices=checkpoint['next_indices'],
                    scheduling_amendment_sha256=io.sha256(overlay / 'amendment.json'))


class Guard:
    def __init__(self, directory, overlay, plan, requests):
        directory, overlay = Path(directory).resolve(), Path(overlay).resolve()
        self.directory, self.overlay, self.plan, self.requests = directory, overlay, plan, requests
        self.plan_sha = io.sha256(directory / 'execution-plan.json')
        self.amendment_path = overlay / 'amendment.json'
        self.amendment_sha = io.sha256(self.amendment_path)
        self.amendment = io.read_json(self.amendment_path)
        self.checkpoint = io.read_json(overlay / 'checkpoint.json')
        self.accounting = effective_accounting(plan, self.plan_sha)
        self.bindings()

    def bindings(self):
        a, cp = self.amendment, self.checkpoint
        require(io.sha256(self.directory / 'execution-plan.json') == self.plan_sha ==
                a.get('execution_plan_sha256') == cp.get('execution_plan_sha256'), 'Original plan changed')
        require(a.get('schema') == cp.get('schema') == VERSION and
                a.get('run_id') == cp.get('run_id') == self.plan['run_id'] and
                a.get('runtime_concurrency') == cp.get('runtime_concurrency') == RUNTIME,
                'Amendment identity/overlay changed')
        require(a.get('checkpoint_path') == str(self.overlay / 'checkpoint.json') and
                io.sha256(self.overlay / 'checkpoint.json') == a.get('checkpoint_sha256') and
                io.sha256(self.amendment_path) == self.amendment_sha, 'Checkpoint/amendment changed')
        require(io.sha256(self.directory / 'STOP') == cp['original_stop_sha256'], 'Original STOP changed')
        require(cp['dependencies'] == self.plan['dependencies'], 'Checkpoint dependencies changed')
        for path, sha in self.plan['dependencies'].items():
            require(io.sha256(legacy.ROOT / path) == sha, 'Original frozen dependency changed: ' + path)
        require(a['dependencies'] == code_bindings(self.overlay), 'Additive code/review changed')
        check_review(self.overlay, self.plan_sha)

    def record(self):
        return dict(schema=VERSION, scheduling_amendment_path=str(self.amendment_path),
                    scheduling_amendment_sha256=self.amendment_sha,
                    checkpoint_sha256=self.amendment['checkpoint_sha256'],
                    execution_plan_sha256=self.plan_sha, runtime_concurrency=RUNTIME,
                    run_id=self.plan['run_id'])

    def state(self, state, *, adopted, allow_pending=False):
        jobs = validate_ledger(state, self.accounting, allow_pending=allow_pending)
        cp = self.checkpoint
        require(legacy.digest(static_ledger(state, self.accounting)) == cp['static_ledger_digest'],
                'Unrelated ledger state changed since checkpoint')
        expected = cp['original_amendments'] + ([self.record()] if adopted else [])
        require(state.get(AMENDMENTS, []) == expected, 'Missing, duplicate or changed ledger amendment')
        for provider, job in jobs.items():
            old = cp['jobs'][provider]
            evolving = {'request_accounts', 'status', 'settled', 'collected_at',
                        'reservation_micro', 'actual_cost_upper_micro'}
            require({k: v for k, v in job.items() if k not in evolving} ==
                    {k: v for k, v in old.items() if k not in evolving},
                    'Original aggregate identity/metadata changed')
            n = cp['next_indices'][provider]
            require(n == len(old['request_accounts']) and len(job['request_accounts']) >= n,
                    'Checkpoint prefix length changed')
            require({str(i): job['request_accounts'][str(i)] for i in range(n)} == old['request_accounts'],
                    'Previously settled prefix changed')
            if provider == 'Anthropic' or not adopted:
                require(job == old, 'Original checkpoint job changed')
        return jobs

    def adopt(self):
        """Only mutation beyond ordinary Accounting: append one exact amendment."""
        self.bindings()
        with original.transaction():
            state = legacy.load()
            adopted = state.get(AMENDMENTS, []) == self.checkpoint['original_amendments'] + [self.record()]
            jobs = self.state(state, adopted=adopted)
            receipts = validate_receipts(self.directory, self.requests, jobs)
            for p, old in self.checkpoint['receipts'].items():
                require(receipts[p][:len(old)] == old, 'Saved prefix receipt/intent changed')
            if not adopted:
                require(io.sha256(legacy.OUT / 'ledger.json') == self.checkpoint['ledger_sha256']
                        and legacy.digest(state) == self.checkpoint['ledger_state_digest'],
                        'Ledger changed after checkpoint; do not adopt')
                require(io.sha256(self.directory / 'execution.json') ==
                        self.checkpoint['drain_execution_sha256'], 'Drain record changed before adoption')
                state.setdefault(AMENDMENTS, []).append(self.record())
                legacy.save(state)
                sync_file(legacy.OUT / 'ledger.json')
                require(legacy.load().get(AMENDMENTS) == state[AMENDMENTS], 'Amendment not durable')
        return self.accounting.snapshot()

    def before_post(self, index, body):
        self.bindings()
        require(body == self.requests['OpenAI'][index], 'Only exact frozen suffix requests allowed')
        require(index >= self.checkpoint['next_indices']['OpenAI'], 'Never replay old prefix')
        with original.transaction():
            state = legacy.load()
            jobs = self.state(state, adopted=True, allow_pending=True)
            account = jobs['OpenAI']['request_accounts'].get(str(index))
            require(account and account['state'] == 'reserved_unknown' and
                    account['request_digest'] == legacy.digest(body), 'Durable exact reservation missing')


def execute(directory, overlay):
    directory, overlay = Path(directory).resolve(), Path(overlay).resolve()
    with coordinator(directory):
        plan, _, requests = original.inspect_manifest(directory)
        guard = Guard(directory, overlay, plan, requests)
        progress = guard.adopt()  # Refuses unknowns; no registration or replay.
        accounting = guard.accounting
        active, stopped = {}, (overlay / 'STOP').exists()
        admission_integrity_error = None
        client = None
        if not stopped and not progress['OpenAI']['complete']:
            client = legacy.client_for('OpenAI').with_options(timeout=600.0, max_retries=0)

        def call(index, body):
            stem = directory / 'receipts' / 'OpenAI' / f'{index:05d}'
            try:
                guard.before_post(index, body)
                require(not stem.with_suffix('.http.json').exists() and
                        not stem.with_suffix('.error.json').exists(), 'Prior attempt artifacts; never replay')
                write_new(stem.with_suffix('.intent.json'),
                          dict(at=io.now(), request_digest=legacy.digest(body), body=body))
                raw = client.responses.with_raw_response.create(**body)
                body_out = io.capture_json(stem.with_suffix('.http.json'), raw)
                require(raw.status_code == 200, 'Unexpected HTTP status')
                original.validated_cost('OpenAI', body_out)
                return body_out, io.sha256(stem.with_suffix('.http.json'))
            except Exception as exc:
                path = stem.with_suffix('.error.json')
                if not path.exists():
                    io.atomic_json(path, io.error_details(exc, client))
                raise RuntimeError(type(exc).__name__ + ': request retained, no paid retry') from None

        with ThreadPoolExecutor(max_workers=32) as pool:
            while True:
                for future in [f for f in active if f.done()]:
                    index = active.pop(future)
                    try:
                        body, sha = future.result()
                        accounting.settle('OpenAI', index, plan['request_digests']['OpenAI'][index], body, sha)
                    except Exception as exc:
                        path = directory / 'receipts' / 'OpenAI' / f'{index:05d}.http.json'
                        saved = io.read_json(path).get('body') if path.exists() else None
                        accounting.fail('OpenAI', index, type(exc).__name__, saved)
                        stopped = True
                progress = accounting.snapshot()
                if (overlay / 'STOP').exists():
                    stopped = True
                if not stopped:
                    try:
                        guard.bindings()
                        with original.transaction():
                            guard.state(legacy.load(), adopted=True, allow_pending=True)
                        index = progress['OpenAI']['admitted']
                        while len(active) < 32 and index < plan['n']:
                            try:
                                accounting.reserve('OpenAI', index, plan['request_digests']['OpenAI'][index])
                            except original.CapacityUnavailable:
                                break  # Keep settling active requests; retry admission after usage arrives.
                            future = pool.submit(call, index, requests['OpenAI'][index])
                            active[future] = index
                            index += 1
                    except Exception as exc:
                        stopped = True
                        admission_integrity_error = dict(error_type=type(exc).__name__,
                                                         stage='pre_admission_integrity_check')
                        # An integrity failure stops admission; already admitted futures drain.
                progress = accounting.snapshot()
                complete = all(p['complete'] for p in progress.values())
                state = ('complete_pending_paired_analysis' if complete else
                         'stopped_incomplete' if stopped and not active else
                         'budget_limited_incomplete' if not active else 'running')
                io.atomic_json(directory / 'execution.json', dict(updated_at=io.now(), pid=os.getpid(),
                    state=state, providers=progress, execution_plan_sha256=guard.plan_sha,
                    runtime_concurrency=RUNTIME, scheduling_amendment_sha256=guard.amendment_sha,
                    scheduling_amendment_path=str(guard.amendment_path), execution_driver=str(overlay / 'resume.py'),
                    admission_integrity_error=admission_integrity_error,
                    benchmark_ready=False, scores_visible=False))
                if not active:
                    return state
                wait(active, timeout=1, return_when=FIRST_COMPLETED)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'execute'])
    parser.add_argument('--directory', type=Path, default=HERE.parent)
    parser.add_argument('--overlay', type=Path, default=HERE)
    args = parser.parse_args()
    print(json.dumps(globals()[args.command](args.directory, args.overlay), ensure_ascii=False))
