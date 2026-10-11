"""Carry one frozen HTTP502 liability; continue only never-admitted suffix.

No retry, fake settlement, changed question, scoring, or new accounting job.
prepare only writes additive input/control artifacts. execute can make paid calls.
"""
from __future__ import annotations
import argparse
import copy
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'astra-concurrency-32'
spec = importlib.util.spec_from_file_location('prior_astra_schedule', PREVIOUS / 'resume.py')
prior = importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
original, legacy, io = prior.original, prior.legacy, prior.io
require = prior.require
VERSION = 'final1800-astra-infrastructure-carry-v1'
KNOWN = 837
FINAL_N = 1800
RUNTIME = {'Anthropic': 0, 'OpenAI': 31}
AGGREGATE = {'Anthropic': 0, 'OpenAI': 32}
NOVEL = 'infrastructure_carry_new_failure'


def review_bindings(overlay, plan_sha):
    names = ['continue.py', 'test_continue.py', 'README.md', 'independent-review.json']
    result = {str((overlay/n).resolve()): io.sha256(overlay/n) for n in names}
    review = io.read_json(overlay/'independent-review.json')
    require(review.get('passed') is True and review.get('execution_plan_sha256') == plan_sha
            and review.get('driver_sha256') == io.sha256(overlay/'continue.py') == io.sha256(Path(__file__))
            and review.get('tests_sha256') == io.sha256(overlay/'test_continue.py'),
            'Independent review must bind exact carry driver/tests/original plan')
    return result


def previous_bindings(directory):
    folder = directory/'astra-concurrency-32'
    return {str((folder/n).resolve()): io.sha256(folder/n) for n in
            ['resume.py','test_resume.py','README.md','independent-review.json','checkpoint.json','amendment.json']}


class CarryAccounting(original.Accounting):
    def __init__(self, plan, plan_sha, checkpoint):
        effective = copy.deepcopy(plan); effective['concurrency'] = AGGREGATE.copy()
        require(plan['pool_caps_micro'] == prior.POOLS, 'Original pool caps required')
        super().__init__(effective, plan_sha)
        self.checkpoint = checkpoint

    def acknowledged(self, state):
        j = self.job(state, 'OpenAI')
        old = self.checkpoint['jobs']['OpenAI']
        require(j.get('operational_failure') == old.get('operational_failure') and
                j['request_accounts'].get(str(KNOWN)) == old['request_accounts'][str(KNOWN)],
                'Acknowledged failure or its full reservation changed')
        require(not j.get(NOVEL), 'Novel operational failure requires new review')
        return j

    def reserve(self, provider, index, digest):
        """Original admission arithmetic; sole exception is exact archived837 error."""
        require(provider == 'OpenAI', 'Anthropic is complete; no new calls')
        with original.transaction():
            s = legacy.load(); j = self.acknowledged(s); records = j['request_accounts']
            require(index >= self.checkpoint['next_indices']['OpenAI'] and
                    index == len(records) and index < self.plan['n'] and str(index) not in records,
                    'Only never-admitted original suffix; never replay')
            require(digest == self.plan['request_digests'][provider][index], 'Exact request required')
            amount = original.maximum(provider)
            if j['reservation_micro'] + amount > self.plan['pool_caps_micro'][provider]:
                raise original.CapacityUnavailable('Execution pool ceiling; await settlement')
            if legacy.committed(s, provider) + legacy.protected_remaining(s, provider) + amount > original.HARD_CAPS[provider]:
                raise original.CapacityUnavailable('Lifetime ceiling/protected reserves; await settlement')
            # The carried unknown consumes one of the unchanged32 unresolved slots.
            if sum(x['state'] != 'settled' for x in records.values()) >= 32:
                raise original.CapacityUnavailable('Aggregate unresolved window is full')
            records[str(index)] = dict(index=index, request_digest=digest, state='reserved_unknown',
                                      admitted_at=io.now(), maximum_cost_micro=amount)
            j.update(reservation_micro=original.liability(records),
                     attempted_at=j['attempted_at'] or io.now(), status='running_with_acknowledged_infrastructure_failure')
            legacy.save(s)

    def fail(self, provider, index, error_type, body=None):
        with original.transaction():
            s = legacy.load(); j = self.job(s, provider)
            j.setdefault(NOVEL, []).append(dict(index=index, error_type=error_type, at=io.now()))
            j['status'] = 'stopped_new_failure_with_original_hold_retained'
            record = j['request_accounts'][str(index)]
            observed = original.observed_cost(provider, body)
            if record['state'] != 'settled' and observed is not None:
                record['observed_cost_micro'] = max(record.get('observed_cost_micro', 0), observed)
                j['reservation_micro'] = original.liability(j['request_accounts'])
            legacy.save(s)


def validate_state(state, accounting, *, allow_active=False):
    accounting.check_state(state)
    owned = {accounting.job_id(p) for p in original.HARD_CAPS}
    for p in original.HARD_CAPS:
        require(type(state['historical_spend_micro'][p]) is int and state['historical_spend_micro'][p] >= 0,
                'Invalid historical cost')
    for name, job in state['jobs'].items():
        require(job['provider'] in original.HARD_CAPS, 'Unknown provider')
        for key in ['reservation_micro','actual_cost_upper_micro']:
            require(type(job.get(key,0)) is int and job.get(key,0) >= 0, 'Invalid ledger cost')
        require(name in owned or not job.get('attempted_at') or job.get('settled') is True,
                'Other unresolved accounting job')
    jobs = {p: accounting.job(state,p) for p in original.HARD_CAPS}
    accounting.acknowledged(state)
    require(jobs['Anthropic']['settled'] is True and not jobs['Anthropic'].get('operational_failure'),
            'Anthropic must already be fully settled')
    for p,j in jobs.items():
        unknown = {int(i) for i,r in j['request_accounts'].items() if r['state'] != 'settled'}
        if p == 'OpenAI':
            require(KNOWN in unknown and (allow_active or unknown == {KNOWN}),
                    'Only exact acknowledged837 may remain unknown after drain')
            require(len(unknown) <= 32, 'More than32 aggregate unresolved accounts')
        else:
            require(not unknown, 'Anthropic unknown')
        require(j['reservation_micro'] <= prior.POOLS[p], 'Pool exceeded')
        require(legacy.committed(state,p)+legacy.protected_remaining(state,p) <= original.HARD_CAPS[p],
                'Lifetime cap/protected reserve exceeded')
    return jobs


def receipt_bindings(directory, requests, jobs):
    result = {}
    for p,j in jobs.items():
        rows, expected = [], set()
        for i in range(len(j['request_accounts'])):
            record = j['request_accounts'][str(i)]
            stem = directory/'receipts'/p/f'{i:05d}'
            intent_path = stem.with_suffix('.intent.json')
            intent = io.read_json(intent_path); digest = legacy.digest(requests[p][i])
            require(intent.get('body') == requests[p][i] and intent.get('request_digest') == digest == record['request_digest'],
                    'Actual request differs from exact frozen question')
            expected.add(intent_path.name)
            row = dict(index=i, request_digest=digest, account_sha256=legacy.digest(record),
                       intent_sha256=io.sha256(intent_path))
            if p == 'OpenAI' and i == KNOWN:
                error_path = stem.with_suffix('.error.json'); error = io.read_json(error_path)
                require(error.get('status_code') == 502 and not stem.with_suffix('.http.json').exists(),
                        'Only the exact HTTP502 with no successful receipt is acknowledged')
                require(record['state'] == 'reserved_unknown' and
                        record['maximum_cost_micro'] == original.maximum('OpenAI') and
                        'actual_cost_upper_micro' not in record and not record.get('response_id') and
                        not record.get('observed_cost_micro'), 'Carry must retain full unknown liability')
                row['error_sha256'] = io.sha256(error_path); expected.add(error_path.name)
            else:
                path = stem.with_suffix('.http.json'); receipt = io.read_json(path)
                require(not stem.with_suffix('.error.json').exists() and record['state'] == 'settled',
                        'Unacknowledged failure or unresolved receipt')
                require(receipt.get('status_code') == 200 and io.sha256(path) == record['receipt_sha256'],
                        'Settled receipt hash/status changed')
                body = receipt['body']
                require(original.validated_cost(p,body) == record['actual_cost_upper_micro'] and
                        body['id'] == record['response_id'], 'Settled receipt identity/cost changed')
                row['receipt_sha256'] = io.sha256(path); expected.add(path.name)
            rows.append(row)
        require({x.name for x in (directory/'receipts'/p).iterdir() if x.is_file()} == expected,
                'Unexpected receipt/intent outside admitted prefix')
        result[p] = rows
    return result


def prepare(directory, overlay):
    directory,overlay = Path(directory).resolve(),Path(overlay).resolve()
    with prior.coordinator(directory):
        plan,_,requests = original.inspect_manifest(directory); sha = io.sha256(directory/'execution-plan.json')
        require(plan['n'] == FINAL_N, 'This exception applies only to original1800')
        code = review_bindings(overlay,sha); previous = previous_bindings(directory)
        previous_guard = prior.Guard(directory,directory/'astra-concurrency-32',plan,requests)
        status = io.read_json(directory/'execution.json')
        require(status.get('state') == 'stopped_incomplete' and status.get('execution_plan_sha256') == sha,
                'Previous driver must be fully drained')
        require(status.get('scheduling_amendment_sha256') == io.sha256(directory/'astra-concurrency-32/amendment.json'),
                'Unexpected prior scheduling amendment')
        require(not (overlay/'STOP').exists(), 'New STOP already exists')
        with original.transaction():
            state = legacy.load()
            base = original.Accounting(plan,sha)
            jobs = {p:copy.deepcopy(base.job(state,p)) for p in original.HARD_CAPS}
            require(state.get(prior.AMENDMENTS,[]) == [previous_guard.record()], 'Prior durable amendment changed')
            require(KNOWN >= previous_guard.checkpoint['next_indices']['OpenAI'], 'Known failure cannot rewrite old settled prefix')
            for p,j in jobs.items():
                old = previous_guard.checkpoint['jobs'][p]['request_accounts']
                require({str(i):j['request_accounts'][str(i)] for i in range(len(old))} == old,
                        'Original pre-acceleration prefix changed')
            require(jobs['OpenAI'].get('operational_failure',{}).get('index') == KNOWN,
                    'Only original837 failure is authorized')
            cp = dict(schema=VERSION,created_at=io.now(),run_id=plan['run_id'],execution_plan_sha256=sha,
                dependencies=plan['dependencies'],previous_bindings=previous,runtime_concurrency=RUNTIME,
                original_stop_sha256=io.sha256(directory/'STOP'),drain_execution=status,
                drain_execution_sha256=io.sha256(directory/'execution.json'),
                ledger_sha256=io.sha256(legacy.OUT/'ledger.json'),ledger_state_digest=legacy.digest(state),
                static_ledger_digest=legacy.digest(prior.static_ledger(state,base)),
                original_amendments=copy.deepcopy(state.get(prior.AMENDMENTS,[])),jobs=jobs,
                next_indices={p:len(j['request_accounts']) for p,j in jobs.items()})
            a = CarryAccounting(plan,sha,cp); validate_state(state,a)
            require(status.get('providers') == a.snapshot(), 'Drained execution differs from ledger')
            require(len(cp['original_amendments']) == 1 and cp['original_amendments'][0].get('scheduling_amendment_sha256') ==
                    status['scheduling_amendment_sha256'], 'Prior amendment chain differs')
            cp['receipts'] = receipt_bindings(directory,requests,jobs)
            reviewed_failure = io.read_json(overlay/'independent-review.json').get('acknowledged_failure')
            exact_failure = {k:cp['receipts']['OpenAI'][KNOWN][k]
                             for k in ['index','request_digest','intent_sha256','error_sha256']}
            require(reviewed_failure == exact_failure, 'Exact502 evidence requires independent review')
        require(not (overlay/'checkpoint.json').exists() and not (overlay/'amendment.json').exists(), 'Never replace checkpoint')
        prior.write_new(overlay/'checkpoint.json',cp)
        amendment = dict(schema=VERSION,created_at=io.now(),run_id=plan['run_id'],execution_plan_sha256=sha,
            checkpoint_path=str(overlay/'checkpoint.json'),checkpoint_sha256=io.sha256(overlay/'checkpoint.json'),
            dependencies=code,runtime_concurrency=RUNTIME,aggregate_unresolved_limit=32,
            acknowledged_transport_failures=[dict(index=KNOWN,http_status=502,maximum_cost_micro=original.maximum('OpenAI'))],
            reason='Continue only never-admitted suffix. Keep original837 failure and full unknown liability; '
                   'no replay, no fake settlement, no model-outcome selection. All1800 original questions remain in analysis denominator.')
        prior.write_new(overlay/'amendment.json',amendment)
        return dict(state='prepared_no_ledger_or_api_mutation',next_indices=cp['next_indices'],
                    scheduling_amendment_sha256=io.sha256(overlay/'amendment.json'))


class Guard:
    def __init__(self,directory,overlay,plan,requests):
        self.directory,self.overlay = Path(directory).resolve(),Path(overlay).resolve()
        self.plan,self.requests = plan,requests
        self.plan_sha = io.sha256(self.directory/'execution-plan.json')
        self.amendment_path = self.overlay/'amendment.json'; self.amendment_sha = io.sha256(self.amendment_path)
        self.amendment = io.read_json(self.amendment_path); self.checkpoint = io.read_json(self.overlay/'checkpoint.json')
        self.accounting = CarryAccounting(plan,self.plan_sha,self.checkpoint); self.bindings()

    def bindings(self):
        a,cp = self.amendment,self.checkpoint
        require(a.get('schema') == cp.get('schema') == VERSION and a.get('run_id') == cp.get('run_id') == self.plan['run_id'],
                'Carry amendment identity changed')
        require(io.sha256(self.directory/'execution-plan.json') == self.plan_sha == a.get('execution_plan_sha256') == cp.get('execution_plan_sha256'),
                'Original plan changed')
        require(io.sha256(self.amendment_path) == self.amendment_sha and
                io.sha256(self.overlay/'checkpoint.json') == a.get('checkpoint_sha256') and
                a.get('checkpoint_path') == str(self.overlay/'checkpoint.json'), 'Checkpoint/amendment changed')
        require(a.get('runtime_concurrency') == cp.get('runtime_concurrency') == RUNTIME and
                a.get('aggregate_unresolved_limit') == 32 and
                a.get('acknowledged_transport_failures') == [dict(index=KNOWN,http_status=502,maximum_cost_micro=original.maximum('OpenAI'))],
                'Failure exception or concurrency changed')
        require(io.sha256(self.directory/'STOP') == cp['original_stop_sha256'], 'Original STOP changed')
        require(cp['dependencies'] == self.plan['dependencies'], 'Original dependency set changed')
        for path,sha in self.plan['dependencies'].items():
            require(io.sha256(legacy.ROOT/path) == sha, 'Original frozen dependency changed')
        require(cp['previous_bindings'] == previous_bindings(self.directory), 'Prior amendment/artifacts changed')
        require(a['dependencies'] == review_bindings(self.overlay,self.plan_sha), 'New code/review changed')
        error = self.directory/'receipts/OpenAI'/f'{KNOWN:05d}.error.json'
        intent = self.directory/'receipts/OpenAI'/f'{KNOWN:05d}.intent.json'
        frozen = cp['receipts']['OpenAI'][KNOWN]
        require(io.sha256(error) == frozen['error_sha256'] and io.sha256(intent) == frozen['intent_sha256'] and
                not error.with_name(f'{KNOWN:05d}.http.json').exists(), 'Original502 evidence changed')

    def record(self):
        return dict(schema=VERSION,scheduling_amendment_path=str(self.amendment_path),
            scheduling_amendment_sha256=self.amendment_sha,checkpoint_sha256=self.amendment['checkpoint_sha256'],
            execution_plan_sha256=self.plan_sha,runtime_concurrency=RUNTIME,run_id=self.plan['run_id'],
            acknowledged_transport_failures=self.amendment['acknowledged_transport_failures'])

    def state(self,state,*,adopted,allow_active=False):
        jobs = validate_state(state,self.accounting,allow_active=allow_active); cp = self.checkpoint
        require(legacy.digest(prior.static_ledger(state,self.accounting)) == cp['static_ledger_digest'], 'Unrelated ledger state changed')
        require(state.get(prior.AMENDMENTS,[]) == cp['original_amendments']+([self.record()] if adopted else []),
                'Missing/changed amendment chain')
        for p,j in jobs.items():
            old = cp['jobs'][p]; n = cp['next_indices'][p]
            changing = {'request_accounts','status','settled','collected_at','reservation_micro','actual_cost_upper_micro'}
            require({k:v for k,v in j.items() if k not in changing} == {k:v for k,v in old.items() if k not in changing},
                    'Original job identity/failure changed')
            require(n == len(old['request_accounts']) and len(j['request_accounts']) >= n and
                    {str(i):j['request_accounts'][str(i)] for i in range(n)} == old['request_accounts'], 'Old prefix changed')
            if p == 'Anthropic' or not adopted: require(j == old,'Checkpoint job changed')
        return jobs

    def adopt(self):
        self.bindings()
        with original.transaction():
            state = legacy.load(); adopted = state.get(prior.AMENDMENTS,[]) == self.checkpoint['original_amendments']+[self.record()]
            jobs = self.state(state,adopted=adopted); rows = receipt_bindings(self.directory,self.requests,jobs)
            for p,old in self.checkpoint['receipts'].items(): require(rows[p][:len(old)] == old,'Prior receipt changed')
            if not adopted:
                require(io.sha256(legacy.OUT/'ledger.json') == self.checkpoint['ledger_sha256'] and
                        legacy.digest(state) == self.checkpoint['ledger_state_digest'] and
                        io.sha256(self.directory/'execution.json') == self.checkpoint['drain_execution_sha256'], 'Drain checkpoint stale')
                state.setdefault(prior.AMENDMENTS,[]).append(self.record()); legacy.save(state)
                prior.sync_file(legacy.OUT/'ledger.json')
                require(legacy.load().get(prior.AMENDMENTS) == state[prior.AMENDMENTS], 'Amendment not durable')
        return self.accounting.snapshot()

    def before_post(self,index,body):
        self.bindings()
        require(index >= self.checkpoint['next_indices']['OpenAI'] and body == self.requests['OpenAI'][index], 'Never replay; exact suffix only')
        with original.transaction():
            jobs = self.state(legacy.load(),adopted=True,allow_active=True)
            row = jobs['OpenAI']['request_accounts'].get(str(index))
            require(row and row['state'] == 'reserved_unknown' and row['request_digest'] == legacy.digest(body), 'Durable reservation missing')


def all_attempted(progress):
    return (progress['Anthropic']['complete'] and progress['OpenAI']['admitted'] == FINAL_N and
            progress['OpenAI']['terminal_usage'] == FINAL_N-1)


def execute(directory,overlay):
    directory,overlay = Path(directory).resolve(),Path(overlay).resolve()
    with prior.coordinator(directory):
        plan,_,requests = original.inspect_manifest(directory); guard = Guard(directory,overlay,plan,requests)
        progress = guard.adopt(); accounting = guard.accounting
        active,stopped = {},(overlay/'STOP').exists(); integrity_error = None
        client = None
        if not stopped and not all_attempted(progress):
            client = legacy.client_for('OpenAI').with_options(timeout=600.0,max_retries=0)
        def call(index,body):
            stem = directory/'receipts/OpenAI'/f'{index:05d}'
            try:
                guard.before_post(index,body)
                require(not stem.with_suffix('.http.json').exists() and not stem.with_suffix('.error.json').exists(),'Prior attempt; never replay')
                prior.write_new(stem.with_suffix('.intent.json'),dict(at=io.now(),request_digest=legacy.digest(body),body=body))
                raw = client.responses.with_raw_response.create(**body)
                result = io.capture_json(stem.with_suffix('.http.json'),raw)
                require(raw.status_code == 200,'Unexpected HTTP status'); original.validated_cost('OpenAI',result)
                return result,io.sha256(stem.with_suffix('.http.json'))
            except Exception as exc:
                if not stem.with_suffix('.error.json').exists(): io.atomic_json(stem.with_suffix('.error.json'),io.error_details(exc,client))
                raise RuntimeError(type(exc).__name__+': retained without retry') from None
        with ThreadPoolExecutor(max_workers=31) as pool:
            while True:
                for future in [f for f in active if f.done()]:
                    index = active.pop(future)
                    try:
                        body,sha = future.result()
                        accounting.settle('OpenAI',index,plan['request_digests']['OpenAI'][index],body,sha)
                    except Exception as exc:
                        path = directory/'receipts/OpenAI'/f'{index:05d}.http.json'
                        saved = io.read_json(path).get('body') if path.exists() else None
                        accounting.fail('OpenAI',index,type(exc).__name__,saved); stopped = True
                progress = accounting.snapshot()
                if (overlay/'STOP').exists(): stopped = True
                if not stopped:
                    try:
                        guard.bindings()
                        with original.transaction(): guard.state(legacy.load(),adopted=True,allow_active=True)
                        index = progress['OpenAI']['admitted']
                        while len(active)<31 and index<plan['n']:
                            try: accounting.reserve('OpenAI',index,plan['request_digests']['OpenAI'][index])
                            except original.CapacityUnavailable: break
                            active[pool.submit(call,index,requests['OpenAI'][index])] = index; index += 1
                    except Exception as exc:
                        stopped = True; integrity_error = dict(error_type=type(exc).__name__,stage='pre_admission_integrity_check')
                progress = accounting.snapshot()
                state = ('complete_attempted_pending_paired_analysis' if all_attempted(progress) else
                         'stopped_incomplete' if stopped and not active else 'budget_limited_incomplete' if not active else
                         'running_with_acknowledged_infrastructure_failure')
                io.atomic_json(directory/'execution.json',dict(updated_at=io.now(),pid=os.getpid(),state=state,
                    providers=progress,execution_plan_sha256=guard.plan_sha,runtime_concurrency=RUNTIME,
                    scheduling_amendment_sha256=guard.amendment_sha,scheduling_amendment_path=str(guard.amendment_path),
                    execution_driver=str(overlay/'continue.py'),admission_integrity_error=integrity_error,
                    acknowledged_transport_failures=guard.amendment['acknowledged_transport_failures'],
                    infrastructure_hold_micro=original.maximum('OpenAI'),aggregate_unresolved_limit=32,
                    benchmark_ready=False,scores_visible=False))
                if not active: return state
                wait(active,timeout=1,return_when=FIRST_COMPLETED)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=['prepare','execute'])
    parser.add_argument('--directory',type=Path,default=HERE.parent); parser.add_argument('--overlay',type=Path,default=HERE)
    args=parser.parse_args(); print(json.dumps(globals()[args.command](args.directory,args.overlay)))
