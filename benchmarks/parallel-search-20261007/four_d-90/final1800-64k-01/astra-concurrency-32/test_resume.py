"""Isolated fake-ledger/fake-SDK tests; never load live receipts or call APIs."""
import copy
import fcntl
import importlib.util
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('astra_resume', HERE / 'resume.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
c, io, legacy = r.original, r.io, r.legacy


def response(provider, index):
    usage = dict(input_tokens=100, output_tokens=20)
    if provider == 'Anthropic':
        return dict(id=f'msg-{index}', type='message', model='claude-opus-5-5', stop_reason='end_turn',
                    usage=dict(usage, service_tier='standard', inference_geo='global'))
    return dict(id=f'resp-{index}', model='gpt-6-astra', status='completed', service_tier='default',
                usage=dict(usage, total_tokens=120))


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.directory = self.base / 'run'; self.directory.mkdir()
        self.overlay = self.directory / 'astra-concurrency-32'; self.overlay.mkdir()
        self.out = self.base / 'ledger'; self.out.mkdir()
        self.n = 40
        self.tasks = [dict(id=f'task-{i}') for i in range(self.n)]
        self.requests = {p: [dict(index=i) for i in range(self.n)] for p in c.HARD_CAPS}
        allocation = {p: {phase: 0 for phase in legacy.PROTECTED} for p in c.HARD_CAPS}
        state = dict(jobs={}, authorization=legacy.PROVIDERS, status='ready',
                     historical_spend_micro={'Anthropic': 311_430_394, 'OpenAI': 801_130_500},
                     protected_phase_minimum_questions=allocation,
                     reserve_revisions=[dict(new_allocation=allocation, reason='Isolated fixture')])
        io.atomic_json(self.out / 'ledger.json', state)
        for obj, name, value in [(legacy, 'OUT', self.out),
            (legacy, 'load', lambda: io.read_json(self.out / 'ledger.json')),
            (legacy, 'save', lambda s: io.atomic_json(self.out / 'ledger.json', s))]:
            p = patch.object(obj, name, value); p.start(); self.addCleanup(p.stop)
        self.dep = self.base / 'dep.txt'; self.dep.write_text('frozen')
        self.plan = dict(run_id='fixture-final', n=self.n, concurrency={'Anthropic': 16, 'OpenAI': 16},
            pool_caps_micro=r.POOLS, protected_allocation=allocation,
            fixed_task_ids=[t['id'] for t in self.tasks], tasks_digest=legacy.digest(self.tasks),
            request_digests={p: [legacy.digest(x) for x in rows] for p, rows in self.requests.items()},
            dependencies={str(self.dep): io.sha256(self.dep)})
        io.atomic_json(self.directory / 'execution-plan.json', self.plan)
        self.plan_sha = io.sha256(self.directory / 'execution-plan.json')
        self.a = c.Accounting(self.plan, self.plan_sha)
        with patch('misc.vp_goal_validate.validate'):
            self.a.register(self.tasks)
        for p in c.HARD_CAPS:
            for i in range(self.n if p == 'Anthropic' else 2):
                self.save_settled(p, i)
        (self.directory / 'STOP').write_text('Parent-requested graceful drain\n')
        io.atomic_json(self.directory / 'execution.json', dict(state='stopped_incomplete',
            providers=self.a.snapshot(), execution_plan_sha256=self.plan_sha, pid=123))
        for name in ['resume.py', 'test_resume.py', 'README.md']:
            (self.overlay / name).write_bytes((HERE / name).read_bytes())
        io.atomic_json(self.overlay / 'independent-review.json', dict(passed=True,
            execution_plan_sha256=self.plan_sha, driver_sha256=io.sha256(self.overlay / 'resume.py'),
            tests_sha256=io.sha256(self.overlay / 'test_resume.py')))
        p = patch.object(c, 'inspect_manifest', return_value=(self.plan, self.tasks, self.requests))
        p.start(); self.addCleanup(p.stop)

    def save_settled(self, provider, index):
        digest = self.plan['request_digests'][provider][index]
        self.a.reserve(provider, index, digest)
        stem = self.directory / 'receipts' / provider / f'{index:05d}'
        io.atomic_json(stem.with_suffix('.intent.json'), dict(at='fixture', request_digest=digest,
                                                           body=self.requests[provider][index]))
        body = response(provider, index)
        io.atomic_json(stem.with_suffix('.http.json'), dict(status_code=200, body=body))
        self.a.settle(provider, index, digest, body, io.sha256(stem.with_suffix('.http.json')))

    def mutate(self, fn):
        state = legacy.load(); fn(state); legacy.save(state)

    def prepare(self):
        return r.prepare(self.directory, self.overlay)

    def guard(self):
        return r.Guard(self.directory, self.overlay, self.plan, self.requests)

    def test_prepare_is_ledger_read_only_and_effective_overlay_is_only_change(self):
        before = (self.out / 'ledger.json').read_bytes()
        value = self.prepare()
        self.assertEqual(before, (self.out / 'ledger.json').read_bytes())
        self.assertEqual(value['next_indices'], {'Anthropic': 40, 'OpenAI': 2})
        g = self.guard()
        self.assertEqual(g.accounting.plan['concurrency'], {'Anthropic': 0, 'OpenAI': 32})
        expected = copy.deepcopy(self.plan); expected['concurrency'] = r.RUNTIME
        self.assertEqual(g.accounting.plan, expected)
        self.assertEqual(io.sha256(self.directory / 'execution-plan.json'), self.plan_sha)

    def test_missing_stop_or_lock_ownership_refuses(self):
        stop = self.directory / 'STOP'; saved = stop.read_bytes(); stop.unlink()
        with self.assertRaisesRegex(ValueError, 'STOP'): self.prepare()
        stop.write_bytes(saved)
        with (self.directory / 'coordinator.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.prepare()

    def test_unknown_and_operational_failure_refuse(self):
        self.a.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])
        with self.assertRaisesRegex(ValueError, 'Unknown'): self.prepare()
        self.a.fail('OpenAI', 2, 'TimeoutError')
        with self.assertRaisesRegex(ValueError, 'operational_failure'): self.prepare()

    def test_anthropic_incomplete_refuses(self):
        def change(state):
            j = state['jobs'][self.a.job_id('Anthropic')]
            j['request_accounts'].pop('39'); j['actual_cost_upper_micro'] -= 800
            j['reservation_micro'] -= 800; j['settled'] = False; j['collected_at'] = None
        self.mutate(change)
        with self.assertRaisesRegex(ValueError, 'Anthropic'): self.prepare()

    def test_receipt_cost_identity_and_extra_intent_refuse(self):
        path = self.directory / 'receipts/OpenAI/00000.http.json'
        before = path.read_bytes(); value = io.read_json(path); value['body']['id'] = 'wrong'
        io.atomic_json(path, value)
        with self.assertRaisesRegex(ValueError, 'Receipt'): self.prepare()
        path.write_bytes(before)
        io.atomic_json(self.directory / 'receipts/OpenAI/00002.intent.json', dict(unaccounted=True))
        with self.assertRaisesRegex(ValueError, 'Unexpected'): self.prepare()

    def test_changed_checkpoint_prefix_or_new_record_refuses(self):
        self.prepare(); before = (self.out / 'ledger.json').read_bytes()
        self.save_settled('OpenAI', 2)
        with self.assertRaisesRegex(ValueError, 'checkpoint job'): self.guard().adopt()
        (self.out / 'ledger.json').write_bytes(before)
        self.mutate(lambda s: s['jobs'][self.a.job_id('OpenAI')]['request_accounts']['0'].update(settled_at='changed'))
        with self.assertRaisesRegex(ValueError, 'prefix changed'): self.guard().adopt()

    def test_changed_checkpoint_or_dependencies_refuse(self):
        self.prepare()
        path = self.overlay / 'checkpoint.json'; value = io.read_json(path); value['next_indices']['OpenAI'] = 3
        before = path.read_bytes(); io.atomic_json(path, value)
        with self.assertRaisesRegex(ValueError, 'Checkpoint/amendment'): self.guard()
        path.write_bytes(before); self.dep.write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'dependency'): self.guard()

    def test_conflicting_amendment_and_unknown_restart_refuse(self):
        self.prepare(); g = self.guard(); g.adopt()
        state = legacy.load(); self.assertEqual(state[r.AMENDMENTS], [g.record()])
        g.adopt(); self.assertEqual(legacy.load()[r.AMENDMENTS], [g.record()])
        g.accounting.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])
        with self.assertRaisesRegex(ValueError, 'Unknown'): self.guard().adopt()
        self.mutate(lambda s: s[r.AMENDMENTS].append(dict(conflict=True)))
        with self.assertRaises(ValueError): self.guard().adopt()

    def test_conflicting_amendment_without_unknowns_refuses(self):
        self.prepare(); g = self.guard(); g.adopt()
        self.mutate(lambda s: s[r.AMENDMENTS][0].update(scheduling_amendment_sha256='wrong'))
        with self.assertRaisesRegex(ValueError, 'amendment'): self.guard().adopt()

    def test_one_micro_budget_boundary_and_pool_settlement_reclaim(self):
        self.prepare(); g = self.guard(); g.adopt(); a = g.accounting
        actual = a.job(legacy.load(), 'OpenAI')['reservation_micro']
        # Exactly one new maximum reaches the cap; one micro less headroom refuses.
        before = (self.out / 'ledger.json').read_bytes()
        for shortage in [1, 0]:
            (self.out / 'ledger.json').write_bytes(before)
            self.mutate(lambda s: s['historical_spend_micro'].update(
                OpenAI=c.HARD_CAPS['OpenAI'] - actual - c.maximum('OpenAI') + shortage))
            if shortage:
                with self.assertRaisesRegex(c.CapacityUnavailable, 'Lifetime'):
                    a.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])
            else:
                a.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])
                self.assertEqual(legacy.committed(legacy.load(), 'OpenAI'), c.HARD_CAPS['OpenAI'])
        # The unchanged pool gate distinguishes pool capacity from concurrency.
        (self.out / 'ledger.json').write_bytes(before)
        a.plan['pool_caps_micro'] = dict(r.POOLS, OpenAI=actual+c.maximum('OpenAI'))
        a.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])
        with self.assertRaisesRegex(c.CapacityUnavailable, 'pool ceiling'):
            a.reserve('OpenAI', 3, self.plan['request_digests']['OpenAI'][3])
        a.settle('OpenAI', 2, self.plan['request_digests']['OpenAI'][2], response('OpenAI', 2), 'fake-receipt')
        # Give the exact known 2,000micro usage room before admitting the next max.
        a.plan['pool_caps_micro']['OpenAI'] += 2000
        a.reserve('OpenAI', 3, self.plan['request_digests']['OpenAI'][3])

    def test_32_reservations_and_exact_lifetime_cap(self):
        self.prepare(); g = self.guard(); g.adopt(); a = g.accounting
        for i in range(2, 34): a.reserve('OpenAI', i, self.plan['request_digests']['OpenAI'][i])
        state = legacy.load(); j = a.job(state, 'OpenAI')
        self.assertEqual(j['reservation_micro'], 4000 + 32 * 3_291_800)
        with self.assertRaises(c.CapacityUnavailable): a.reserve('OpenAI', 34, self.plan['request_digests']['OpenAI'][34])
        with self.assertRaises((ValueError, c.CapacityUnavailable)):
            a.reserve('Anthropic', self.n, 'never')
        # Exact cap tested through unchanged accounting, without live ledger mutation.
        self.mutate(lambda s: s['historical_spend_micro'].update(OpenAI=c.HARD_CAPS['OpenAI']-j['reservation_micro']))
        self.assertEqual(legacy.committed(legacy.load(), 'OpenAI'), c.HARD_CAPS['OpenAI'])
        with self.assertRaises(c.CapacityUnavailable): a.reserve('OpenAI', 34, self.plan['request_digests']['OpenAI'][34])

    def fake_execute(self, callback):
        outer = self
        class Client:
            api_key = 'fake'
            def __init__(self, provider):
                assert provider == 'OpenAI'
                self.responses = self.with_raw_response = self
            def with_options(self, **kw):
                assert kw == dict(timeout=600.0, max_retries=0)
                return self
            def create(self, **body):
                index = body['index']
                # Network occurs after durable amendment, reservation, intent and outside ledger lock.
                with c.transaction(timeout=.5):
                    state = legacy.load()
                    assert state[r.AMENDMENTS] == [outer.guard().record()]
                    assert state['jobs'][outer.a.job_id('OpenAI')]['request_accounts'][str(index)]['state'] == 'reserved_unknown'
                assert io.read_json(outer.directory / 'receipts/OpenAI' / f'{index:05d}.intent.json')['body'] == body
                value = callback(index)
                headers = SimpleNamespace(multi_items=lambda: [])
                return SimpleNamespace(status_code=200, headers=headers,
                    http_response=SimpleNamespace(json=lambda: value))
        with patch.object(legacy, 'client_for', side_effect=Client):
            return r.execute(self.directory, self.overlay)

    def test_32_workers_safe_restart_no_replay_and_original_accounting_compatible(self):
        self.prepare(); calls = []; lock = threading.Lock(); event = threading.Event()
        def callback(index):
            with lock:
                calls.append(index)
                if len(calls) == 32: event.set()
            if index < 34 and not event.wait(15): raise AssertionError('32 workers not admitted')
            return response('OpenAI', index)
        self.assertEqual(self.fake_execute(callback), 'complete_pending_paired_analysis')
        self.assertEqual(sorted(calls), list(range(2, 40)))
        self.assertEqual(self.fake_execute(callback), 'complete_pending_paired_analysis')
        self.assertEqual(len(calls), 38)
        # Original analyzer uses this unmodified Accounting(plan, originalSHA) gate.
        self.assertTrue(all(x['complete'] for x in self.a.snapshot().values()))
        status = io.read_json(self.directory / 'execution.json')
        self.assertEqual(status['runtime_concurrency'], r.RUNTIME)
        self.assertFalse(status['scores_visible'])
        self.assertEqual(io.sha256(self.directory / 'execution-plan.json'), self.plan_sha)

    def test_budget_tapers_waits_for_settlement_and_graceful_own_stop(self):
        # Admit only one worst-case request initially, reclaim actual usage continuously.
        state = legacy.load(); base_cost = self.a.job(state, 'OpenAI')['reservation_micro']
        self.mutate(lambda s: s['historical_spend_micro'].update(
            OpenAI=c.HARD_CAPS['OpenAI'] - base_cost - c.maximum('OpenAI') - 10000))
        self.prepare(); calls = []
        def callback(index):
            calls.append(index)
            if index == 4: (self.overlay / 'STOP').write_text('Graceful local pause')
            return response('OpenAI', index)
        self.assertEqual(self.fake_execute(callback), 'stopped_incomplete')
        self.assertEqual(calls, [2, 3, 4])
        self.assertEqual(self.a.snapshot()['OpenAI']['admitted'], 5)
        self.assertEqual(self.a.snapshot()['OpenAI']['terminal_usage'], 5)
        self.assertTrue((self.directory / 'STOP').exists())

    def test_error_has_no_retry_and_keeps_unknown_reservation(self):
        self.prepare(); calls = []
        def callback(index):
            calls.append(index)
            if index == 2: raise TimeoutError('fake uncertainty')
            return response('OpenAI', index)
        self.assertEqual(self.fake_execute(callback), 'stopped_incomplete')
        self.assertEqual(len(calls), len(set(calls)))
        self.assertEqual(legacy.load()['jobs'][self.a.job_id('OpenAI')]['request_accounts']['2']['state'], 'reserved_unknown')
        with self.assertRaisesRegex(ValueError, 'operational_failure'): self.fake_execute(callback)


if __name__ == '__main__':
    unittest.main()
