import unittest
from misc.vp_cartesian_cap_check import paired_analysis


def row(i, correct, truncated=False):
    return {'task': {'id': str(i), 'campaign': {'root_family': str(i)}},
            'is_correct': correct, 'status': 'completed', 'answer': 'form',
            'truncated': truncated}


class CapCheckTests(unittest.TestCase):
    def test_truncated_correct_and_directional_regressions(self):
        before = [row(0, True, True), row(1, False), row(2, True)]
        after = [row(0, True), row(1, True), row(2, False)]
        result = paired_analysis(before, after)
        self.assertEqual(result['baseline']['correct'], 2)
        self.assertEqual(result['baseline']['completed_correct'], 1)
        self.assertEqual(result['newly_completed'], 1)
        self.assertEqual(result['recorded_accuracy_difference'], 0)
        self.assertEqual(result['wrong_or_missing_to_correct'], 1)
        self.assertEqual(result['correct_to_wrong_or_missing'], 1)

    def test_changed_or_missing_pair_rejected(self):
        with self.assertRaises(ValueError):
            paired_analysis([row(0, True)], [row(1, True)])
        with self.assertRaises(ValueError):
            paired_analysis([row(0, True)], [])


if __name__ == '__main__':
    unittest.main()
