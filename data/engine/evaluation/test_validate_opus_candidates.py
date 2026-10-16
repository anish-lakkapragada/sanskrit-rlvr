"""Offline tests for fresh sampling and concurrent dollar reservations."""
from collections import Counter
from copy import deepcopy
import unittest
from data.engine.evaluation import validate_opus_candidates as v


class ValidationTests(unittest.TestCase):
    def test_output_setting_does_not_change_effort_or_enable_tools(self):
        m = {'request_defaults': deepcopy(v.opus.REQUEST_DEFAULTS)}
        m['request_defaults']['max_tokens'] = 16000
        b = v.body('Sanskrit test', m)
        self.assertEqual(b['model'], 'claude-opus-5-5')
        self.assertEqual(b['output_config'], {'effort': 'xhigh'})
        self.assertEqual(b['max_tokens'], 16000)
        self.assertEqual(b['messages'], [{'role': 'user', 'content': 'Sanskrit test'}])
        self.assertTrue(set(b).isdisjoint({'tools', 'tool_choice', 'fallbacks', 'system'}))
        self.assertEqual(v.opus.REQUEST_DEFAULTS['max_tokens'], 128000)

    def test_concurrent_reservations_fit_actual_ceiling(self):
        rates = {'uncached_input': 4, 'cache_write_input': 8, 'output': 20}
        m = {'request_defaults': {'max_tokens': 16000}, 'pricing': {'rates_usd_per_million_tokens': rates}}
        reserve = v.reservation('राम', m)
        self.assertGreater(reserve, .32)
        self.assertTrue(v.admission(0, 3*reserve, reserve, 2))
        self.assertFalse(v.admission(1.5, reserve, reserve, 2))
        self.assertFalse(v.admission(1.8, 0, reserve, 2))
        self.assertFalse(v.admission(2, 0, reserve, 5))
        m['request_defaults']['max_tokens'] = 128000
        self.assertFalse(v.admission(0, 0, v.reservation('राम', m), 2))

    def test_fresh_balanced_seeded_sample_ignores_gold_and_outcomes(self):
        tasks = {f: {str(i): {'gold_devanagari': ['unused']} for i in range(100)} for f in v.FAMILIES}
        excluded = {(f, str(i)) for f in v.FAMILIES for i in range(10)}
        plan = v.sample(tasks, excluded, 20)
        self.assertEqual(plan, v.sample(tasks, excluded, 20))
        self.assertEqual(len(plan), len(set(plan)))
        self.assertFalse(set(plan) & excluded)
        for end in range(1, len(plan)+1):
            counts = Counter(f for f, _ in plan[:end])
            self.assertLessEqual(max(counts.get(f, 0) for f in v.FAMILIES)-min(counts.get(f, 0) for f in v.FAMILIES), 1)
        changed = {f: {k: {'gold_devanagari': ['different'], 'status': 'refused'} for k in rows} for f, rows in tasks.items()}
        self.assertEqual(plan, v.sample(changed, excluded, 20))

    def test_zero_refusals_have_nonzero_uncertainty(self):
        low, high = v.wilson(0, 200)
        self.assertAlmostEqual(low, 0)
        self.assertGreater(high, .01)
        self.assertLess(high, .02)

    def test_remaining_budget_preserves_largest_affordable_allowance(self):
        m = {'request_defaults': deepcopy(v.opus.REQUEST_DEFAULTS), 'output_budget_policy': 'remaining_dollars',
             'pricing': {'rates_usd_per_million_tokens': {'uncached_input': 4, 'cache_write_input': 8, 'output': 20}}}
        request, reserve = v.affordable_request('राम', m, 3)
        self.assertEqual(request['max_tokens'], 128000)
        self.assertLess(reserve, 3)
        request, reserve = v.affordable_request('राम', m, 1)
        self.assertGreater(request['max_tokens'], 49000)
        self.assertLess(request['max_tokens'], 50000)
        self.assertLessEqual(reserve, 1)
        self.assertGreater(v.reservation('राम', m, request['max_tokens']+1), 1)
        self.assertEqual(request['output_config']['effort'], 'xhigh')
        self.assertEqual(v.affordable_request('राम', m, .001), (None, 0))


if __name__ == '__main__':
    unittest.main()
