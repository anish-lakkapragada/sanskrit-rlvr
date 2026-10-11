"""Three reviewer-owned synthetic carry checks. No live ledger, outputs or API."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('carry_author_tests', HERE/'test_continue.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


class IndependentTests(t.CarryTests):
    def test_exact_failure_fingerprint_required_before_checkpoint(self):
        path = self.overlay/'independent-review.json'
        review = t.io.read_json(path)
        review['acknowledged_failure']['error_sha256'] = '0'*64
        t.io.atomic_json(path, review)
        before = (self.out/'ledger.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Exact502 evidence'):
            self.prepare()
        self.assertEqual(before, (self.out/'ledger.json').read_bytes())
        self.assertFalse((self.overlay/'checkpoint.json').exists())

    def test_prior_frozen_file_cannot_become_new_baseline(self):
        prior_readme = self.directory/'astra-concurrency-32/README.md'
        prior_readme.write_text('accidental prior file edit')
        with self.assertRaisesRegex(ValueError, 'Additive code/review changed'):
            self.prepare()
        self.assertFalse((self.overlay/'checkpoint.json').exists())

    def test_pool_boundary_includes_held_unknown(self):
        self.prepare()
        g = self.guard()
        g.adopt()
        a = g.accounting
        j = a.job(t.legacy.load(), 'OpenAI')
        held = dict(j['request_accounts']['2'])
        current = j['reservation_micro']
        self.assertEqual(current, 4000 + t.c.maximum('OpenAI'))
        a.plan['pool_caps_micro'] = dict(t.r.prior.POOLS,
            OpenAI=current+t.c.maximum('OpenAI')-1)
        with self.assertRaisesRegex(t.c.CapacityUnavailable, 'pool ceiling'):
            a.reserve('OpenAI', 3, self.plan['request_digests']['OpenAI'][3])
        a.plan['pool_caps_micro']['OpenAI'] += 1
        a.reserve('OpenAI', 3, self.plan['request_digests']['OpenAI'][3])
        after = a.job(t.legacy.load(), 'OpenAI')
        self.assertEqual(after['request_accounts']['2'], held)
        self.assertEqual(after['reservation_micro'], current+t.c.maximum('OpenAI'))


if __name__ == '__main__':
    names = ['test_exact_failure_fingerprint_required_before_checkpoint',
             'test_prior_frozen_file_cannot_become_new_baseline',
             'test_pool_boundary_includes_held_unknown']
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(IndependentTests(name) for name in names))
    raise SystemExit(0 if result.wasSuccessful() else 1)
