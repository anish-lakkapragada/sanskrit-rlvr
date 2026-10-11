"""Final numerical analysis must preserve membership and family dependence."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_cartesian_final_analyze import panel_statistics, numerical_gates, analyze, ROOT


def fixture(n=2400, cluster_size=1, numerator=8, denominator=10):
    tasks = [{'id': str(i), 'dhatu': {'gana': 'Bhvadi'},
              'campaign': {'root_family': str(i // cluster_size)}} for i in range(n)]
    rows = [{'task': t, 'is_correct': (i // cluster_size) % denominator < numerator,
             'status': 'completed', 'answer': 'form', 'truncated': False}
            for i, t in enumerate(tasks)]
    return tasks, rows


class FinalAnalysisTests(unittest.TestCase):
    def test_strongest_model_target_and_both_model_precision(self):
        t, r = fixture()
        a = panel_statistics(t, r, repetitions=1000)
        _, other = fixture(numerator=13, denominator=20)
        b = panel_statistics(t, other, repetitions=1000)
        gates = numerical_gates({'Anthropic': a, 'OpenAI': b})
        self.assertTrue(gates['all_numerical_requirements_met'])
        self.assertEqual(gates['strongest_reference_missing_answer_bounds'], [.8, .8])

    def test_large_question_count_does_not_hide_few_correlated_families(self):
        t, r = fixture(cluster_size=120)
        a = panel_statistics(t, r, repetitions=1000)
        self.assertLess(a['all_request']['iid_standard_error'], .01)
        self.assertGreater(a['all_request']['root_cluster_sandwich_standard_error'], .08)
        self.assertFalse(numerical_gates({'Anthropic': a, 'OpenAI': a})['both_references_precision_met'])

    def test_partial_membership_keeps_missing_denominator_and_cannot_qualify(self):
        t, r = fixture()
        a = panel_statistics(t, r[:1000], repetitions=1000)
        self.assertEqual(a['all_request']['n'], 2400)
        self.assertEqual(a['statuses']['missing_result'], 1400)
        self.assertFalse(numerical_gates({'Anthropic': a, 'OpenAI': a})['paired_references_complete'])

    def test_changed_or_duplicate_rows_fail(self):
        t, r = fixture(n=10)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            panel_statistics(t, r + r[:1], repetitions=1000)
        altered = copy.deepcopy(r)
        altered[0]['task']['dhatu']['gana'] = 'Curadi'
        with self.assertRaisesRegex(ValueError, 'changed'):
            panel_statistics(t, altered, repetitions=1000)

    def test_completion_ratio_retains_families_without_answers(self):
        t, r = fixture(n=3)
        r[0]['is_correct'] = True
        r[1]['is_correct'] = False
        r[2].update(status='refused', answer=None, is_correct=False)
        a = panel_statistics(t, r, repetitions=1000)
        self.assertEqual(a['completed_answer']['accuracy'], .5)
        self.assertAlmostEqual(a['completed_answer']['root_cluster_sandwich_standard_error'], (0.75 ** .5) / 2)
        self.assertEqual(a['root_families'], 3)

    def test_parsed_truncated_answer_keeps_its_recorded_score_but_is_not_usable(self):
        t, r = fixture(n=3)
        r[0]['is_correct'] = True
        r[1]['is_correct'] = False
        r[2].update(status='incomplete', truncated=True, is_correct=True)
        a = panel_statistics(t, r, repetitions=1000)
        self.assertEqual(a['all_request']['correct'], 2)
        self.assertEqual(a['completed_answer']['correct'], 1)
        self.assertEqual(a['completed_answer']['n'], 2)
        self.assertEqual(a['missing_answer_accuracy_bounds'], [1 / 3, 2 / 3])

    def test_stage_reconciliation_and_frozen_plan_integrity(self):
        tasks, rows = fixture(n=10)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'release'
            directory.mkdir()
            out = Path(tmp) / 'runner'
            io.atomic_json(directory / 'tasks.json', tasks)
            io.atomic_json(directory / 'stage-01.tasks.json', tasks)
            io.atomic_json(directory / 'sampling-plan.json', {'fixed_n': 10})
            policy = 'benchmarks/parallel-search-20261006/oracle-policy-13.json'
            manifest = {'fixed_n': 10, 'track': 'five_d',
                        'frozen_tasks_sha256': io.sha256(directory / 'tasks.json'),
                        'frozen_sampling_plan_sha256': io.sha256(directory / 'sampling-plan.json'),
                        'oracle_policy_path': policy, 'oracle_policy_sha256': io.sha256(ROOT / policy),
                        'dependency_sha256': {}, 'stages': [{'phase': 'hard_final',
                        'path': 'stage-01.tasks.json', 'tasks_digest': runner.digest(tasks),
                        'sha256': io.sha256(directory / 'stage-01.tasks.json')}]}
            io.atomic_json(directory / 'manifest.json', manifest)
            jobdir = out / 'jobs' / 'opus-final-test'
            jobdir.mkdir(parents=True)
            io.atomic_json(jobdir / 'results.json', rows)
            job = {'id': 'opus-final-test', 'provider': 'Anthropic', 'phase': 'hard_final',
                   'tasks_digest': runner.digest(tasks), 'attempted_at': 'frozen',
                   'settled': True, 'collected_at': 'later'}
            with patch.object(runner, 'OUT', out), patch.object(runner, 'load', return_value={'jobs': {job['id']: job}}):
                result = analyze(directory)
                self.assertEqual(result['status'], 'incomplete_evaluation')
                self.assertEqual(result['models']['Anthropic']['result_rows'], 10)
                self.assertEqual(result['models']['OpenAI']['result_rows'], 0)
                self.assertFalse(result['benchmark_ready'])
                io.atomic_json(directory / 'sampling-plan.json', {'fixed_n': 9})
                with self.assertRaisesRegex(ValueError, 'sampling plan changed'):
                    analyze(directory)


if __name__ == '__main__':
    unittest.main()
