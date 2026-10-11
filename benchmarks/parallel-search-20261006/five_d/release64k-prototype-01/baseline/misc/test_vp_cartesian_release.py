"""Guard fixed membership against omissions, duplicates and phase drift."""
import copy
import unittest

from misc.vp_cartesian_release import audit_partition


class FixedReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [{'id': str(i), 'gold': ['unchanged']} for i in range(2400)]
        self.stages = [{'phase': 'hard_final', 'tasks': self.tasks[:1000]},
                       {'phase': 'hard_extension', 'tasks': self.tasks[1000:1500]},
                       {'phase': 'hard_extension', 'tasks': self.tasks[1500:2000]},
                       {'phase': 'hard_extension', 'tasks': self.tasks[2000:]}]

    def test_exact_partition_preserves_all_questions(self):
        result = audit_partition(self.tasks, self.stages, 'five_d')
        self.assertEqual((result['core_n'], result['extension_n']), (1000, 1400))

    def test_omissions_duplicates_and_metadata_changes_fail(self):
        for mutation in ('omit', 'duplicate', 'gold'):
            stages = copy.deepcopy(self.stages)
            if mutation == 'omit':
                stages[-1]['tasks'].pop()
            elif mutation == 'duplicate':
                stages[-1]['tasks'][-1] = stages[0]['tasks'][0]
            else:
                stages[-1]['tasks'][-1]['gold'] = ['changed']
            with self.assertRaisesRegex(ValueError, 'exactly partition'):
                audit_partition(self.tasks, stages, 'five_d')

    def test_phase_drift_and_early_extension_fail(self):
        with self.assertRaisesRegex(ValueError, 'Wrong track'):
            audit_partition(self.tasks, self.stages, 'four_d')
        self.stages[0]['phase'] = 'hard_extension'
        with self.assertRaisesRegex(ValueError, 'first 1000'):
            audit_partition(self.tasks, self.stages, 'five_d')


if __name__ == '__main__':
    unittest.main()
