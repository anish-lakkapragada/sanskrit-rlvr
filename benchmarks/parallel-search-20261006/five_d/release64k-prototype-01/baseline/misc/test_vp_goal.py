"""Financial invariants for adaptive paid experiments; entirely offline."""
import copy
import unittest
from contextlib import nullcontext
from unittest.mock import patch
from misc import vp_goal as c


def state():
    return {"status": "exploring", "historical_spend_micro": {"Anthropic": 23072126, "OpenAI": 0}, "jobs": {}}


def job(provider="Anthropic", phase="explore", n=400):
    return {"provider": provider, "phase": phase, "n": n, "attempted_at": None, "reservation_micro": 0}


class AccountingTests(unittest.TestCase):
    def test_new_confirmation_cap_preserves_shared_allowance_and_reserves(self):
        s = state()
        self.assertEqual(c.budget_gate(s, job(phase='confirm_64k', n=400)), 263344000)
        old = job(phase='confirm', n=19999)
        old.update(attempted_at='past', settled=True, actual_cost_upper_micro=1)
        s['jobs']['old_confirmation'] = old
        for phase in c.CONFIRMATION_PHASES:
            with self.assertRaisesRegex(ValueError, 'Phase allowance'):
                c.budget_gate(s, job(phase=phase, n=2))
        self.assertEqual(c.PHASES['confirm'][1], 16384)
        self.assertEqual(c.PHASES['confirm_64k'][1], 65536)
        self.assertNotIn('confirm_64k', c.FINAL_PHASES)

    def test_invalid_prefix_cannot_reach_paid_submission(self):
        bad = {"derivation": {"prefixes": ["abhi", "sam"]}}
        with patch.object(c.base, "lock", return_value=nullcontext()), \
             patch.object(c, "load", return_value={"jobs": {"bad": {}}}), \
             patch.object(c, "verify_job", return_value=([bad], [])), \
             patch.object(c, "client_for") as client, patch.object(c, "save") as save:
            with self.assertRaisesRegex(ValueError, "SLP1 upasarga"):
                c.submit("bad")
            client.assert_not_called()
            save.assert_not_called()

    def test_direct_diagnostics_reserve_standard_rates(self):
        j = job(n=32)
        j["transport"] = "direct"
        self.assertEqual(c.budget_gate(state(), j), 10677760)
        self.assertEqual(c.rates(j), {"input_rate": 4, "output_rate": 20})
        j["provider"] = "OpenAI"
        self.assertEqual(c.budget_gate(state(), j), 26694400)

    def test_prior_spend_and_final_protection(self):
        s = state()
        self.assertEqual(c.committed(s, "Anthropic"), 23072126)
        self.assertEqual(c.protected_remaining(s, "Anthropic"), 461980000)
        self.assertEqual(c.protected_remaining(s, "OpenAI"), 1154950000)
        self.assertEqual(c.budget_gate(s, job()), 66736000)

    def test_unknown_submission_retains_full_reservation(self):
        s = state()
        j = job()
        j.update(attempted_at="now", reservation_micro=66736000, actual_cost_upper_micro=1)
        s["jobs"]["unknown"] = j
        self.assertEqual(c.committed(s, "Anthropic"), 89808126)
        with self.assertRaisesRegex(ValueError, "never replay"):
            c.budget_gate(s, j)

    def test_only_settled_savings_reused(self):
        s = state()
        j = job()
        j.update(attempted_at="now", reservation_micro=66736000, actual_cost_upper_micro=2000000,
                 settled=True)
        s["jobs"]["done"] = j
        self.assertEqual(c.committed(s, "Anthropic"), 25072126)

    def test_provider_caps_and_protected_allowances(self):
        for p in c.PROVIDERS:
            s = state()
            with self.assertRaisesRegex(ValueError, "Cumulative"):
                c.budget_gate(s, job(p, n=20000))
            # A final call consumes its own reserve, rather than double counting it.
            n = job(p, "bench_final", 1000)
            reserve = c.budget_gate(s, n)
            self.assertEqual(c.protected_remaining(s, p, n) + reserve, c.protected_remaining(s, p))

    def test_two_accepted_jobs_cannot_oversubscribe(self):
        s = state()
        j = job(n=3000)
        j["reservation_micro"] = c.budget_gate(s, j)
        j["attempted_at"] = "now"
        s["jobs"]["first"] = j
        with self.assertRaises(ValueError):
            c.budget_gate(s, job(n=100))

    def test_halt_and_phase_limits(self):
        s = state()
        s["status"] = "halted_for_reconciliation"
        with self.assertRaises(ValueError):
            c.budget_gate(s, job())
        with self.assertRaises(ValueError):
            c.budget_gate(state(), job(phase="bench_final", n=1001))

    def test_extensions_wait_for_settled_core_and_preserve_other_tier(self):
        s = state()
        more = job(phase="bench_extension", n=500)
        with self.assertRaisesRegex(ValueError, "settle the core"):
            c.budget_gate(s, more)
        core = job(phase="bench_final", n=1000)
        core.update(attempted_at="now", collected_at="later", settled=True,
                    actual_cost_upper_micro=10000000, reservation_micro=166840000)
        s["jobs"]["core"] = core
        self.assertEqual(c.budget_gate(s, more), 83420000)
        self.assertEqual(c.protected_remaining(s, "Anthropic", more), 295140000)
        self.assertEqual(c.FINAL_PHASES - c.PROTECTED, {"bench_extension", "hard_extension"})
        core["settled"] = False
        with self.assertRaisesRegex(ValueError, "settle the core"):
            c.budget_gate(s, more)

    def test_extensions_still_obey_total_cap(self):
        s = state()
        core = job(phase="bench_final", n=1000)
        core.update(attempted_at="now", collected_at="later", settled=True,
                    actual_cost_upper_micro=166840000, reservation_micro=166840000)
        s["jobs"]["core"] = core
        with self.assertRaisesRegex(ValueError, "Cumulative"):
            c.budget_gate(s, job(phase="bench_extension", n=5000))

    def test_final_stage_cannot_replay_unknown_or_settled_questions(self):
        previous = job(phase='hard_final', n=1000)
        previous.update(id='old', attempted_at='now')
        s = state()
        s['jobs']['old'] = previous
        with patch.object(c.base, 'read_json', return_value=[{'id': 'same'}]):
            for settled in (False, True):
                previous['settled'] = settled
                with self.assertRaisesRegex(ValueError, 'already attempted'):
                    c.prevent_repeated_final_questions(s, job(phase='hard_extension'), [{'id': 'same'}])
            c.prevent_repeated_final_questions(s, job(phase='hard_extension'), [{'id': 'new'}])
            c.prevent_repeated_final_questions(s, job(provider='OpenAI', phase='hard_final'), [{'id': 'same'}])
            c.prevent_repeated_final_questions(s, job(phase='cap_check'), [{'id': 'same'}])

    def test_development_sensitivity_consumes_same_protected_pool(self):
        for provider in c.PROVIDERS:
            s = state()
            before = c.protected_remaining(s, provider)
            j = job(provider=provider, phase='cap_check_development', n=40)
            reserve = c.budget_gate(s, j)
            self.assertEqual(before, c.protected_remaining(s, provider, j) + reserve)
            j.update(attempted_at='now', reservation_micro=reserve)
            s['jobs']['sensitivity'] = j
            c.budget_gate(s, job(provider=provider, phase='cap_check', n=60))
            for phase in c.SENSITIVITY_PHASES:
                with self.assertRaisesRegex(ValueError, 'Phase allowance'):
                    c.budget_gate(s, job(provider=provider, phase=phase, n=61))
            self.assertNotIn('cap_check_development', c.FINAL_PHASES)

    def test_documented_reallocation_keeps_hard_caps_and_replay_guards(self):
        s = state()
        allocation = c.protected_allocations(s)
        allocation['OpenAI']['bench_final'] = 0
        allocation['OpenAI']['cap_check'] = 60
        s['protected_phase_minimum_questions'] = allocation
        with self.assertRaisesRegex(ValueError, 'documented rationale'):
            c.protected_remaining(s, 'OpenAI')
        s['reserve_revisions'] = [{'reason': 'Offline test of a documented design reallocation',
                                  'new_allocation': copy.deepcopy(allocation)}]
        self.assertEqual(c.protected_remaining(s, 'OpenAI'), 417100000 + 192450000)
        self.assertEqual(c.protected_remaining(s, 'Anthropic'), 461980000)
        with self.assertRaisesRegex(ValueError, 'Cumulative'):
            c.budget_gate(s, job('OpenAI', n=20000))
        self.assertIn('bench_final', c.FINAL_PHASES)
        self.assertEqual(c.PHASES['cap_check'][2]['OpenAI'], 100)
        allocation['OpenAI']['bench_final'] = -1
        with self.assertRaisesRegex(ValueError, 'Invalid protected'):
            c.protected_remaining(s, 'OpenAI')


if __name__ == "__main__":
    unittest.main()
