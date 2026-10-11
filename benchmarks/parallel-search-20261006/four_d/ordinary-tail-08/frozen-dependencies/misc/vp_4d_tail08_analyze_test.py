"""Synthetic checks only; no model-output files are opened."""
import copy
import math
import unittest
from unittest.mock import patch
from misc import vp_4d_tail08_analyze as a


class TailAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tasks = a.read(a.OUT / 'panel.questions.json')
        self.design = a.read(a.OUT / 'panel-design.json')
        self.rows = [dict(task=copy.deepcopy(t), task_id=t['id'], is_correct=True,
                          status='completed', answer=t['gold_devanagari'][0], truncated=False)
                     for t in self.tasks]

    def test_perfect_is_not_trigger_or_certainty(self):
        a.verify_panel(self.tasks, self.design)
        a.verify_results(self.tasks, self.rows)
        s = a.summarize(self.rows)
        self.assertFalse(s['trigger']['all_mechanical_conditions_met'])
        self.assertEqual(s['metrics']['one_per_family_sandwich_se'], 0)
        self.assertLess(s['metrics']['all_request_wilson95'][0], 1)

    def test_missingness_retains_all_fixed_family_units(self):
        for r in self.rows[45:90]:
            r['is_correct'] = False
        for r in self.rows[90:]:
            r.update(status='refused', answer=None, is_correct=False)
        s = a.summarize(self.rows)['metrics']
        c = [int(a.completed(r)) for r in self.rows]
        y = [int(r['is_correct']) * z for r, z in zip(self.rows, c)]
        p = sum(y) / sum(c)
        expected = math.sqrt(96 / 95 * sum((v - p * z)**2 for v, z in zip(y, c))) / sum(c)
        self.assertAlmostEqual(s['usable_family_se'], expected, places=14)
        self.assertNotAlmostEqual(s['usable_family_se'], math.sqrt(.25 / 89), places=12)
        self.assertEqual(s['family_units_in_variance'], 96)
        self.assertEqual(s['completion_bounds'], [45 / 96, 51 / 96])

    def test_nonusable_does_not_count_as_wrong_completed(self):
        self.rows[0]['truncated'] = True
        self.rows[1].update(status='refused', answer=None, is_correct=False)
        self.rows[2].update(answer=None, is_correct=False)
        s = a.summarize(self.rows)
        self.assertEqual(s['metrics']['usable'], 93)
        self.assertEqual(s['metrics']['correct'], 94)
        self.assertEqual(s['metrics']['completion_bounds'], [93 / 96, 1])
        self.assertEqual(s['trigger']['wrong_completed_families'], 0)

    def test_zero_usable(self):
        for r in self.rows:
            r.update(status='refused', answer=None, is_correct=False)
        s = a.summarize(self.rows)
        self.assertIsNone(s['metrics']['usable_accuracy'])
        self.assertIsNone(s['metrics']['usable_family_se'])
        self.assertEqual(s['metrics']['completion_bounds'], [0, 1])

    def test_distributed_trigger_and_family_threshold(self):
        chosen = set()
        for field, values in [('gana', {t['dhatu']['gana'] for t in self.tasks}),
                              ('lakara', {t['morphology']['lakara'] for t in self.tasks})]:
            for v in sorted(values):
                i = next(i for i, r in enumerate(self.rows)
                         if (r['task']['dhatu']['gana'] if field == 'gana'
                             else r['task']['morphology']['lakara']) == v)
                chosen.add(i)
        for i in range(96):
            if len(chosen) >= 16:
                break
            chosen.add(i)
        self.assertEqual(len(chosen), 16)
        for i in chosen:
            self.rows[i]['is_correct'] = False
        self.assertTrue(a.summarize(self.rows)['trigger']['all_mechanical_conditions_met'])
        self.rows[next(iter(chosen))]['is_correct'] = True
        self.assertFalse(a.summarize(self.rows)['trigger']['all_mechanical_conditions_met'])

    def test_concentrated_errors_fail(self):
        chosen = [i for i, r in enumerate(self.rows) if r['task']['dhatu']['gana'] == 'Bhvadi'][:16]
        for i in chosen:
            self.rows[i]['is_correct'] = False
        s = a.summarize(self.rows)
        self.assertEqual(s['trigger']['wrong_completed_families'], 16)
        self.assertFalse(s['trigger']['checks']['at_least3_error_ganas'])
        self.assertFalse(s['trigger']['all_mechanical_conditions_met'])

    def test_membership_metadata_and_quotas_fail_closed(self):
        with self.assertRaises(ValueError):
            a.verify_results(self.tasks, self.rows[:-1])
        with self.assertRaises(ValueError):
            a.verify_results(self.tasks, self.rows[:-1] + [self.rows[0]])
        self.rows[0]['task']['gold_devanagari'] = ['changed']
        with self.assertRaises(ValueError):
            a.verify_results(self.tasks, self.rows)
        self.tasks[0]['morphology']['lakara'] = 'Lit'
        with self.assertRaises(ValueError):
            a.verify_panel(self.tasks, self.design)

    def test_gate_runs_before_result_access(self):
        d = dict(job_id='unit', provider='Anthropic', phase='confirm_64k', n=96, tasks_digest='fixed')
        j = dict(d, settled=False, collected_at='timestamp')
        seen = []
        def reader(path):
            seen.append(str(path))
            if str(path).endswith('analysis-predeclaration.json'):
                return d
            if str(path).endswith('ledger.json'):
                return {'jobs': {'unit': j}}
            raise AssertionError('Read passed the settlement gate: ' + str(path))
        with patch.object(a, 'read', reader), self.assertRaises(ValueError):
            a.analyze()
        self.assertEqual(len(seen), 2)
        j['settled'] = True
        self.assertIs(a.verify_settled({'jobs': {'unit': j}}, d), j)
        j['n'] = 95
        with self.assertRaises(ValueError):
            a.verify_settled({'jobs': {'unit': j}}, d)


if __name__ == '__main__':
    unittest.main()
