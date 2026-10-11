"""Supplementary reviewer-owned tests; synthetic state only, never live accounts."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('resume_author_tests', HERE / 'test_resume.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


class IndependentTests(t.ResumeTests):
    def test_report_timestamp_vs_unrelated_liability(self):
        self.prepare()
        g = self.guard()
        g.adopt()
        self.mutate(lambda s: s.update(updated_at='synthetic-report-refresh'))
        g.state(t.legacy.load(), adopted=True)
        self.mutate(lambda s: s['historical_spend_micro'].update(
            OpenAI=s['historical_spend_micro']['OpenAI'] + 1))
        with self.assertRaisesRegex(ValueError, 'Unrelated ledger state'):
            g.state(t.legacy.load(), adopted=True)

    def test_protected_reserve_one_micro_blocks_exact_boundary(self):
        self.prepare()
        g = self.guard()
        g.adopt()
        a = g.accounting
        actual = a.job(t.legacy.load(), 'OpenAI')['reservation_micro']
        self.mutate(lambda s: s['historical_spend_micro'].update(
            OpenAI=t.c.HARD_CAPS['OpenAI'] - actual - t.c.maximum('OpenAI')))
        with patch.object(t.legacy, 'protected_remaining', return_value=1):
            with self.assertRaisesRegex(t.c.CapacityUnavailable, 'Lifetime ceiling/protected'):
                a.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])
        self.assertEqual(a.snapshot()['OpenAI']['admitted'], 2)
        with patch.object(t.legacy, 'protected_remaining', return_value=0):
            a.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])

    def test_dependency_tamper_after_reservation_prevents_post(self):
        self.prepare()
        g = self.guard()
        g.adopt()
        g.accounting.reserve('OpenAI', 2, self.plan['request_digests']['OpenAI'][2])
        self.dep.write_text('changed-after-reservation')
        with self.assertRaisesRegex(ValueError, 'Original frozen dependency changed'):
            g.before_post(2, self.requests['OpenAI'][2])
        self.assertEqual(t.legacy.load()['jobs'][self.a.job_id('OpenAI')]
                         ['request_accounts']['2']['state'], 'reserved_unknown')


if __name__ == '__main__':
    names = [
        'test_report_timestamp_vs_unrelated_liability',
        'test_protected_reserve_one_micro_blocks_exact_boundary',
        'test_dependency_tamper_after_reservation_prevents_post',
    ]
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(IndependentTests(name) for name in names))
    raise SystemExit(0 if result.wasSuccessful() else 1)
