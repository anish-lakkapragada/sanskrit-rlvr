"""Versioned continuous final/test execution; legacy runners remain unchanged.

This module does not select tasks or grant a release freeze. Execution requires
a separate reviewed manifest, exact input counts and prospective scoring policy.
All credits remain in the existing lifetime ledger. No response is graded here.
"""
from __future__ import annotations

import contextlib
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import fcntl
import json
import os
from pathlib import Path
import re
import time

from misc import oai_batch_eval as io, vp_goal as legacy
from misc.vp_simple_astra_compare import validate_receipt as validate_astra
from misc.vp_ending_screen_run import validate_receipt as validate_opus

VERSION = 'continuous-final-64k-v1'
PHASE = 'continuous_final_64k_v1'
OUTPUT_CAP = 65536
INPUT_CAP = 1500
RATES = {'Anthropic': (4, 20), 'OpenAI': (10, 50)}
HARD_CAPS = {'Anthropic': 1_000_000_000, 'OpenAI': 2_000_000_000}


class CapacityUnavailable(ValueError):
    """Wait for usage settlement; never change tasks or the output ceiling."""


@contextlib.contextmanager
def transaction(timeout=15):
    """Same lock file as legacy, held only during a local read/modify/write."""
    path = legacy.OUT / '_batch/lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Shared ledger busy; no request submitted') from None
                time.sleep(.025)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def request_for(task, provider, index):
    # Reuse only the already compared wire format. No development job is made:
    # this driver's distinct phase and mandatory test-split gate own execution.
    old = legacy.request(task, provider, 'confirm_64k', index)
    if provider == 'Anthropic':
        return dict(old['params'], service_tier='standard_only', inference_geo='global')
    return dict(old['body'], service_tier='default')


def maximum(provider):
    inp, out = RATES[provider]
    return INPUT_CAP * inp + OUTPUT_CAP * out


def validated_cost(provider, body):
    usage = (validate_opus if provider == 'Anthropic' else validate_astra)(body)
    inp, out = RATES[provider]
    return usage['input_tokens'] * inp + usage['output_tokens'] * out


def liability(records):
    return sum(x['actual_cost_upper_micro'] if x['state'] == 'settled'
               else max(x['maximum_cost_micro'], x.get('observed_cost_micro', 0))
               for x in records.values())


def observed_cost(provider, body):
    """A rejected receipt may still demonstrate liability above our reservation."""
    usage = (body or {}).get('usage') or {}
    keys = ['input_tokens', 'output_tokens']
    if any(type(usage.get(k)) is not int or usage[k] < 0 for k in keys):
        return None
    inp, out = RATES[provider]
    cost = usage['input_tokens'] * inp + usage['output_tokens'] * out
    if provider == 'Anthropic':
        # Caching is forbidden by this protocol. If unexpectedly reported, use
        # full input price for reads and the higher2x long-TTL write price until
        # billing is reconciled, never release credit on that receipt.
        for key, multiplier in [('cache_read_input_tokens', 1), ('cache_creation_input_tokens', 2)]:
            value = usage.get(key, 0)
            if type(value) is not int or value < 0:
                return None
            cost += value * inp * multiplier
    return cost


def inspect_manifest(directory, *, require_review=True):
    """Input-only checks. The complete panel is immutable before the first POST."""
    directory = Path(directory).resolve()
    p = io.read_json(directory / 'execution-plan.json')
    if (p.get('schema') != VERSION or p.get('phase') != PHASE or
            p.get('split') != 'test' or not re.fullmatch(r'[a-z0-9-]+', p.get('run_id', ''))):
        raise ValueError('Require an explicit versioned test-split final plan')
    if p.get('provider_caps_micro') != HARD_CAPS or p.get('rates_micro_per_token') != {
            k: list(v) for k, v in RATES.items()}:
        raise ValueError('Lifetime caps or standard pricing changed')
    if p.get('effort') != 'xhigh' or p.get('max_output_tokens') != OUTPUT_CAP:
        raise ValueError('Reference reasoning/token protocol changed')
    if p.get('paired_analyzer_path') != 'misc/vp_continuous64k_analyze.py':
        raise ValueError('Require the versioned full-paired-cohort analyzer')
    if set(p.get('pool_caps_micro', {})) != set(HARD_CAPS):
        raise ValueError('Both reference provider pools are required')
    for provider in HARD_CAPS:
        if (type(p['pool_caps_micro'][provider]) is not int or
                not 0 < p['pool_caps_micro'][provider] <= HARD_CAPS[provider] or
                type(p['concurrency'][provider]) is not int or
                not 1 <= p['concurrency'][provider] <= 32):
            raise ValueError('Invalid provider pool/concurrency')
    if sum(p['concurrency'].values()) > 32:
        raise ValueError('At most32 outstanding workers across both providers')
    required = {p['tasks_path'], p['public_prompts_path'], p['candidate_manifest_path'], p['input_review_path'],
                p['paired_analyzer_path'], p['source_policy_path'], p['scoring_adoption_path'],
                p['scorer_path'], p['scoring_review_path'], p['alias_policy_path'], p['spelling_rules_path'],
                'finetune/prompts.py', 'prompts/v2/vp_task_eval.txt',
                p['requests_path'], p['input_counts_path'],
                str(Path(__file__).resolve().relative_to(legacy.ROOT)),
                'misc/vp_goal.py', 'misc/vp_goal_validate.py',
                'misc/vp_cartesian_task.py', 'misc/vp_cartesian_prompt_v1.py',
                'misc/oai_batch_eval.py', 'misc/ant_batch_eval.py',
                'misc/vp_simple_astra_compare.py', 'misc/vp_ending_screen_run.py',
                'misc/vp_simple_search_analyze.py', 'misc/vp_cartesian_final_analyze.py',
                'misc/vp_cartesian_analyze.py', 'misc/vp_goal_stats.py',
                'misc/vp_cartesian_visibility.py',
                'benchmarks/creation-campaign-20261006/family-split.json'}
    if not required <= set(p.get('dependencies', {})):
        raise ValueError('Incomplete frozen dependency set')
    for name, sha in p['dependencies'].items():
        if io.sha256(legacy.ROOT / name) != sha:
            raise ValueError('Frozen final dependency changed: ' + name)
    candidate = io.read_json(legacy.ROOT/p['candidate_manifest_path'])
    for name, sha in candidate['dependencies'].items():
        if p['dependencies'].get(name) != sha:
            raise ValueError('Candidate source/generator dependency missing from execution plan: '+name)
    tasks = io.read_json(legacy.ROOT / p['tasks_path'])
    requests = io.read_json(legacy.ROOT / p['requests_path'])
    counts = io.read_json(legacy.ROOT / p['input_counts_path'])
    if len(tasks) != p['n'] or len({t['id'] for t in tasks}) != p['n'] or p['n'] < 500:
        raise ValueError('Final cohort must contain at least500 distinct questions')
    if p['fixed_task_ids'] != [t['id'] for t in tasks] or p['tasks_digest'] != legacy.digest(tasks):
        raise ValueError('Manifest task identities/digest changed')
    task_sha = io.sha256(legacy.ROOT/p['tasks_path'])
    public_sha = io.sha256(legacy.ROOT/p['public_prompts_path'])
    source_sha = io.sha256(legacy.ROOT/p['source_policy_path'])
    if (candidate['n'] != p['n'] or candidate['tasks_sha256'] != task_sha or
            candidate['public_prompts_sha256'] != public_sha or candidate['source_policy_sha256'] != source_sha):
        raise ValueError('Candidate manifest binds a different task/prompt/source artifact')
    review = io.read_json(legacy.ROOT/p['input_review_path'])
    if (review.get('passed') is not True or review.get('tasks_sha256') != task_sha or
            review.get('manifest_sha256') != io.sha256(legacy.ROOT/p['candidate_manifest_path']) or
            review.get('public_prompts_sha256') != public_sha or review.get('source_policy_sha256') != source_sha):
        raise ValueError('Independent input review does not approve these exact candidate inputs')
    if any(t.get('task_type') != 'cartesian_4d' or t.get('prompt_version') != 'cartesian-4d-v1'
           or t['campaign'].get('split') != 'test' for t in tasks):
        raise ValueError('Require original4D test questions')
    for provider in HARD_CAPS:
        expected = [request_for(t, provider, i) for i, t in enumerate(tasks)]
        if requests[provider] != expected:
            raise ValueError('Frozen requests differ from the compared public protocol')
        if p['request_digests'][provider] != [legacy.digest(x) for x in expected]:
            raise ValueError('Request identity allowlist changed')
        c = counts[provider]
        if c['requests_digest'] != legacy.digest(expected) or set(c['counts']) != {str(i) for i in range(p['n'])}:
            raise ValueError('Exact provider input counts missing')
        if any(type(n) is not int or not 0 < n <= 1300 for n in c['counts'].values()):
            raise ValueError('Provider input estimate exceeds reserved allowance')
    public = io.read_json(legacy.ROOT/p['public_prompts_path'])
    expected_public = [{'id':t['id'], 'prompt':b['messages'][0]['content']}
                       for t, b in zip(tasks, requests['Anthropic'])]
    if public != expected_public:
        raise ValueError('Published questions differ from actual model-visible inputs')
    aliases = io.read_json(legacy.ROOT/p['alias_policy_path'])
    if (aliases['task_count'] != p['n'] or aliases['canonical_tasks_sha256'] != task_sha or
            len(aliases['items']) != p['n']):
        raise ValueError('Spelling policy belongs to a different cohort')
    for task, item in zip(tasks, aliases['items']):
        if (item['task_id'] != task['id'] or item['canonical_forms_slp1'] != task['gold_slp1'] or
                item['canonical_forms_devanagari'] != task['gold_devanagari']):
            raise ValueError('Spelling policy changes canonical membership/answers')
    adoption = io.read_json(legacy.ROOT / p['scoring_adoption_path'])
    if adoption['candidate_tasks_sha256'] != io.sha256(legacy.ROOT / p['tasks_path']):
        raise ValueError('Scoring declaration belongs to another candidate')
    if (adoption['scorer_sha256'] != io.sha256(legacy.ROOT / p['scorer_path']) or
            adoption['alias_policy_sha256'] != io.sha256(legacy.ROOT / p['alias_policy_path'])):
        raise ValueError('Prospectively adopted scorer/aliases changed')
    scoring_review = io.read_json(legacy.ROOT/p['scoring_review_path'])
    if (adoption['independent_review_sha256'] != io.sha256(legacy.ROOT/p['scoring_review_path']) or
            scoring_review.get('passed') is not True or scoring_review.get('tasks_sha256') != task_sha or
            scoring_review.get('policy_sha256') != adoption['alias_policy_sha256'] or
            scoring_review.get('scorer_sha256') != adoption['scorer_sha256']):
        raise ValueError('Independent scoring review is not bound to the adopted policy')
    if require_review:
        gate = io.read_json(directory / 'execution-review.json')
        if (gate.get('passed') is not True or gate.get('execution_plan_sha256') != io.sha256(directory / 'execution-plan.json')
                or gate.get('test_split_verified') is not True or gate.get('source_scoring_review_passed') is not True
                or gate.get('independent_input_review_sha256') != io.sha256(legacy.ROOT/p['input_review_path'])
                or not gate.get('precision_limitations_declared')):
            raise ValueError('This exact final protocol/membership requires completed independent review')
    return p, tasks, requests


class Accounting:
    """Aggregate jobs expose all paid liabilities to unchanged legacy cap checks."""
    def __init__(self, plan, plan_sha):
        self.plan, self.plan_sha = plan, plan_sha
        self.marker = 'halted_owned_' + plan['run_id'] + '_' + VERSION

    def job_id(self, provider):
        return self.plan['run_id'] + '-' + provider.lower()

    def check_state(self, s):
        if {k: v['cap_micro'] for k, v in s['authorization'].items()} != HARD_CAPS:
            raise ValueError('Shared lifetime authorization changed')
        if s.get('status') != self.marker:
            raise ValueError('Continuous coordinator does not own the spending fence')
        if legacy.protected_allocations(s) != self.plan['protected_allocation']:
            raise ValueError('Protected reserve allocation changed')

    def job(self, s, provider):
        self.check_state(s)
        j = s['jobs'][self.job_id(provider)]
        if (j.get('accounting_driver') != VERSION or j.get('phase') != PHASE or
                j.get('execution_plan_sha256') != self.plan_sha or j.get('batch_id') is not None or
                j.get('provider') != provider or j.get('n') != self.plan['n']):
            raise ValueError('Versioned aggregate accounting record changed')
        if (j.get('fixed_task_ids') != self.plan['fixed_task_ids'] or
                j.get('tasks_digest') != self.plan['tasks_digest']):
            raise ValueError('Fixed membership in accounting record changed')
        records = j['request_accounts']
        if len(records) > self.plan['n'] or set(records) != {str(i) for i in range(len(records))}:
            raise ValueError('Admitted indices are not the exact fixed input prefix')
        response_ids = set()
        for key, record in records.items():
            if (record.get('index') != int(key) or
                    record.get('request_digest') != self.plan['request_digests'][provider][int(key)] or
                    record.get('maximum_cost_micro') != maximum(provider) or
                    record.get('state') not in {'reserved_unknown', 'settled'}):
                raise ValueError('Request identity/reservation changed')
            if record['state'] == 'settled':
                cost = record.get('actual_cost_upper_micro')
                if (type(cost) is not int or not 0 <= cost <= record['maximum_cost_micro'] or
                        not record.get('receipt_sha256') or not record.get('response_id') or
                        record['response_id'] in response_ids):
                    raise ValueError('Invalid settled request cost/receipt identity')
                response_ids.add(record['response_id'])
            elif 'actual_cost_upper_micro' in record:
                raise ValueError('Unsettled request cannot release its maximum reservation')
            if ('observed_cost_micro' in record and
                    (type(record['observed_cost_micro']) is not int or record['observed_cost_micro'] < 0)):
                raise ValueError('Invalid observed liability on rejected receipt')
        complete = len(records) == self.plan['n'] and all(x['state'] == 'settled' for x in records.values())
        actual = sum(x.get('actual_cost_upper_micro', 0) for x in records.values())
        if (j.get('settled') is not complete or bool(j.get('collected_at')) != complete or
                j.get('actual_cost_upper_micro') != actual):
            raise ValueError('Aggregate settlement/actual cost disagrees with exact request accounts')
        if j['reservation_micro'] != liability(records):
            raise ValueError('Aggregate liability does not match request accounts')
        return j

    def register(self, tasks):
        from misc.vp_goal_validate import validate
        if [t['id'] for t in tasks] != self.plan['fixed_task_ids'] or legacy.digest(tasks) != self.plan['tasks_digest']:
            raise ValueError('Registration membership differs from frozen plan')
        validate(tasks, 'test')
        with transaction():
            s = legacy.load()
            if all(self.job_id(p) in s['jobs'] for p in HARD_CAPS):
                for provider in HARD_CAPS:
                    self.job(s, provider)
                return
            if any(self.job_id(p) in s['jobs'] for p in HARD_CAPS):
                raise ValueError('Incomplete aggregate registration')
            if s.get('status', '').startswith('halted'):
                raise ValueError('Reconcile the existing spending fence first')
            if any(j.get('attempted_at') and not j.get('settled') for j in s['jobs'].values()):
                raise ValueError('Reconcile earlier outstanding liabilities first')
            if legacy.protected_allocations(s) != self.plan['protected_allocation']:
                raise ValueError('Protected allocation changed before registration')
            ids = {t['id'] for t in tasks}
            for old in s['jobs'].values():
                if old.get('accounting_driver') == VERSION:
                    if ids & set(old['fixed_task_ids']):
                        raise ValueError('Final question already belongs to a continuous run')
                elif old.get('attempted_at') and old['phase'] in legacy.FINAL_PHASES:
                    prior = io.read_json(legacy.OUT / 'jobs' / old['id'] / 'tasks.json')
                    if ids & {t['id'] for t in prior}:
                        raise ValueError('Final question was already attempted by a legacy run')
            previous = s.get('status')
            for provider in HARD_CAPS:
                name = self.job_id(provider)
                s['jobs'][name] = dict(id=name, provider=provider, phase=PHASE,
                    accounting_driver=VERSION, execution_plan_sha256=self.plan_sha,
                    transport='direct', n=len(tasks), fixed_task_ids=[t['id'] for t in tasks],
                    tasks_digest=legacy.digest(tasks), status='registered_unattempted',
                    batch_id=None, attempted_at=None, settled=False, collected_at=None,
                    reservation_micro=0, actual_cost_upper_micro=0, request_accounts={})
            s['status'] = self.marker
            s.setdefault('continuous_execution_fences', []).append(dict(at=io.now(),
                previous_status=previous, status=self.marker, execution_plan_sha256=self.plan_sha,
                note='Legacy paid submissions blocked; final requests owned by separate reviewed64k driver.'))
            legacy.save(s)

    def reserve(self, provider, index, request_digest):
        with transaction():
            s = legacy.load()
            j = self.job(s, provider)
            records = j['request_accounts']
            if not 0 <= index < self.plan['n'] or str(index) in records or index != len(records):
                raise ValueError('Question already admitted or fixed input order changed; never replay')
            if request_digest != self.plan['request_digests'][provider][index]:
                raise ValueError('Request is not the frozen question at this index')
            if j.get('operational_failure'):
                raise ValueError('Prior operational failure requires review')
            reserve = maximum(provider)
            if j['reservation_micro'] + reserve > self.plan['pool_caps_micro'][provider]:
                raise CapacityUnavailable('Execution pool ceiling; await settlement')
            if legacy.committed(s, provider) + legacy.protected_remaining(s, provider) + reserve > HARD_CAPS[provider]:
                raise CapacityUnavailable('Lifetime ceiling/protected reserves; await settlement')
            pending = sum(x['state'] != 'settled' for x in records.values())
            if pending >= self.plan['concurrency'][provider]:
                raise CapacityUnavailable('Provider concurrency is full')
            records[str(index)] = dict(index=index, request_digest=request_digest,
                state='reserved_unknown', admitted_at=io.now(), maximum_cost_micro=reserve)
            j.update(reservation_micro=liability(records), attempted_at=j['attempted_at'] or io.now(),
                     status='running_without_interim_scores')
            legacy.save(s)

    def settle(self, provider, index, request_digest, body, receipt_sha):
        cost = validated_cost(provider, body)
        with transaction():
            s = legacy.load()
            j = self.job(s, provider)
            record = j['request_accounts'][str(index)]
            if record['state'] != 'reserved_unknown' or record['request_digest'] != request_digest:
                raise ValueError('Settlement does not match a single outstanding request')
            if cost > record['maximum_cost_micro']:
                raise ValueError('Receipt exceeds the durable reservation')
            if body['id'] in {x.get('response_id') for x in j['request_accounts'].values()}:
                raise ValueError('Provider response reused across questions')
            record.update(state='settled', actual_cost_upper_micro=cost,
                          response_id=body['id'], receipt_sha256=receipt_sha, settled_at=io.now())
            j['reservation_micro'] = liability(j['request_accounts'])
            j['actual_cost_upper_micro'] = sum(x.get('actual_cost_upper_micro', 0) for x in j['request_accounts'].values())
            if len(j['request_accounts']) == self.plan['n'] and all(x['state'] == 'settled' for x in j['request_accounts'].values()):
                j.update(settled=True, collected_at=io.now(), status='complete_usage_only_pending_paired_analysis')
            legacy.save(s)

    def fail(self, provider, index, error_type, body=None):
        with transaction():
            s = legacy.load()
            j = self.job(s, provider)
            # Even a crash before POST may have raced a billable request. Keep
            # the full reservation and require reconciliation without replay.
            j['operational_failure'] = dict(index=index, error_type=error_type, at=io.now())
            j['status'] = 'stopped_unknown_reservation_retained'
            record = j['request_accounts'][str(index)]
            observed = observed_cost(provider, body)
            if record['state'] != 'settled' and observed is not None:
                record['observed_cost_micro'] = max(record.get('observed_cost_micro', 0), observed)
                j['reservation_micro'] = liability(j['request_accounts'])
            legacy.save(s)

    def snapshot(self):
        s = legacy.load()
        result = {}
        for provider in HARD_CAPS:
            j = self.job(s, provider)
            rows = j['request_accounts'].values()
            result[provider] = dict(fixed_n=j['n'], admitted=len(j['request_accounts']),
                terminal_usage=sum(x['state'] == 'settled' for x in rows),
                settled_cost_usd=j['actual_cost_upper_micro']/1e6,
                committed_usd=j['reservation_micro']/1e6, complete=j['settled'],
                operational_failure=j.get('operational_failure'))
        return result


def execute(directory):
    """One continuously refilled pool. This is the only paid entry point."""
    directory = Path(directory).resolve()
    with (directory/'coordinator.lock').open('a') as process_lock:
        fcntl.flock(process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan, tasks, requests = inspect_manifest(directory)
        fingerprint = io.sha256(directory/'execution-plan.json')
        accounting = Accounting(plan, fingerprint)
        accounting.register(tasks)
        start = accounting.snapshot()
        if any(s['admitted'] != s['terminal_usage'] or s['operational_failure'] for s in start.values()):
            raise ValueError('Uncertain previous request; reconcile saved receipts, never replay')
        clients = {p: legacy.client_for(p).with_options(timeout=600.0, max_retries=0) for p in HARD_CAPS}
        active, stopped = {}, False
        slots = sum(plan['concurrency'].values())

        def call(provider, index, body):
            # The parent already persisted a full reservation and exact digest.
            if io.sha256(directory/'execution-plan.json') != fingerprint:
                raise ValueError('Execution plan changed before POST')
            for path, sha in plan['dependencies'].items():
                if io.sha256(legacy.ROOT/path) != sha:
                    raise ValueError('Dependency changed before POST: '+path)
            path = directory/'receipts'/provider/f'{index:05d}'
            intent = path.with_suffix('.intent.json')
            if intent.exists():
                raise ValueError('Request intent already exists; never replay')
            io.atomic_json(intent, dict(at=io.now(), request_digest=legacy.digest(body), body=body))
            client = clients[provider]
            endpoint = client.messages if provider == 'Anthropic' else client.responses
            try:
                raw = endpoint.with_raw_response.create(**body)
                receipt = path.with_suffix('.http.json')
                result = io.capture_json(receipt, raw)
                validated_cost(provider, result)
                return result, io.sha256(receipt)
            except Exception as exc:
                io.atomic_json(path.with_suffix('.error.json'), io.error_details(exc, client))
                raise RuntimeError('Request outcome requires review; no paid retry') from None

        with ThreadPoolExecutor(max_workers=slots) as pool:
            while True:
                # Settle everything already finished before admitting more work.
                done = [f for f in active if f.done()]
                for future in done:
                    provider, index, digest = active.pop(future)
                    try:
                        body, sha = future.result()
                        accounting.settle(provider, index, digest, body, sha)
                    except Exception as exc:
                        receipt = directory/'receipts'/provider/f'{index:05d}.http.json'
                        body = io.read_json(receipt)['body'] if receipt.exists() else None
                        accounting.fail(provider, index, type(exc).__name__, body)
                        stopped = True
                snapshot = accounting.snapshot()
                if (directory/'STOP').exists():
                    stopped = True
                if not stopped:
                    for provider in HARD_CAPS:
                        n_active = sum(p == provider for p, _, _ in active.values())
                        for _ in range(plan['concurrency'][provider] - n_active):
                            index = snapshot[provider]['admitted']
                            if index == plan['n']:
                                break
                            body = requests[provider][index]
                            digest = legacy.digest(body)
                            try:
                                accounting.reserve(provider, index, digest)
                            except CapacityUnavailable:
                                break
                            # If submit itself crashes after reservation, the
                            # durable unknown is preserved on restart.
                            active[pool.submit(call, provider, index, body)] = (provider, index, digest)
                            snapshot[provider]['admitted'] += 1
                snapshot = accounting.snapshot()
                complete = all(x['complete'] for x in snapshot.values())
                state = ('complete_pending_paired_analysis' if complete else
                         'stopped_incomplete' if stopped and not active else
                         'budget_limited_incomplete' if not active else 'running')
                io.atomic_json(directory/'execution.json', dict(updated_at=io.now(), pid=os.getpid(),
                    state=state, providers=snapshot, execution_plan_sha256=fingerprint,
                    benchmark_ready=False, scores_visible=False))
                if not active:
                    return state
                wait(active, timeout=1, return_when=FIRST_COMPLETED)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute:
        print(execute(args.directory))
    else:
        p, _, _ = inspect_manifest(args.directory, require_review=False)
        print(dict(dry_run=True, n=p['n'], concurrency=p['concurrency'], paid_calls=0))
