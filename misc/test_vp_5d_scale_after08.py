"""Synthetic checks for prospective scale calculations; no model outputs."""
import math
import unittest
from unittest.mock import patch

from misc import vp_5d_scale_after08 as subject


def row(correct, usable):
    return {'task': {'morphology': {'lakara': 'Lun', 'prayoga': 'Kartari'},
                     'derivation': {'recipe_id': 'test'}},
            'is_correct': correct, 'status': 'completed' if usable else 'refused',
            'answer': 'a' if usable else None, 'truncated': False}


def witness():
    return {'n': 4, 'distinct_families': 2, 'family_cap': 2, 'aorist_per_family_cap': 2,
            'cell_counts': {'test|Lun|Kartari': 4},
            'unordered_within_family_cell_pair_counts': [
                {'cell_a': 'test|Lun|Kartari', 'cell_b': 'test|Lun|Kartari', 'pairs': 2}]}


class ScaleScenarios(unittest.TestCase):
    def test_missing_cell_stays_unidentified_even_with_prior(self):
        other = row(True, True)
        other['task']['morphology']['lakara'] = 'Lat'
        result = subject.moments([other], witness(), fine=True, prior=.5)
        self.assertFalse(result['identified'])
        self.assertEqual(result['unsupported_mass'], 1.)

    def test_nonusable_correct_state_is_separate_from_usable_ratio(self):
        rows = [row(True, True), row(False, True), row(True, False), row(True, True)]
        result = subject.moments(rows, witness(), fine=True, prior=0.)
        self.assertAlmostEqual(result['projected_all_accuracy'], .75)
        self.assertAlmostEqual(result['projected_completion'], .75)
        self.assertAlmostEqual(result['projected_usable_accuracy'], 2 / 3)
        self.assertAlmostEqual(result['estimates']['completed_ratio_influence']['independent_variance_sum'], 32 / 27)

    def test_pair_covariance_matches_hand_calculation(self):
        rows = [row(True, True), row(False, True), row(True, False), row(True, True)]
        moment = subject.moments(rows, witness(), fine=False, prior=0.)['estimates']['recorded_all_correct']
        self.assertAlmostEqual(moment['independent_variance_sum'], .75)
        self.assertAlmostEqual(moment['pair_covariance_coefficients']['both_Lun'], .75)
        result = subject.scenario(moment, witness(), dict.fromkeys(subject.CATEGORIES, .2))
        self.assertAlmostEqual(result['expected_sandwich_se_pp'], 100 * math.sqrt(.9 * 2) / 4)

    def test_family_mean_term_preserves_unequal_cell_composition(self):
        first, second = row(True, True), row(False, True)
        second['task']['morphology']['lakara'] = 'Lat'
        w = witness()
        w['cell_counts'] = {'test|Lun|Kartari': 2, 'test|Lat|Kartari': 2}
        w['unordered_within_family_cell_pair_counts'] = [
            {'cell_a': cell, 'cell_b': cell, 'pairs': 1} for cell in w['cell_counts']]
        m = subject.moments([first, second], w, fine=True, prior=0.)['estimates']['recorded_all_correct']
        self.assertEqual(m['independent_variance_sum'], 0)
        self.assertEqual(m['allocation_mean_squared_sum'], 2)

    def test_missing_correlation_not_silently_zero(self):
        result = subject.scenario({}, witness(), {'both_Lun': None})
        self.assertFalse(result['identified'])

    def test_impossible_block_correlation_is_flagged(self):
        w = witness()
        w.update(family_cap=4)
        m = {'independent_variance_sum': 1., 'allocation_mean_squared_sum': 0.,
             'pair_covariance_coefficients': dict.fromkeys(subject.CATEGORIES, .5)}
        r = subject.scenario(m, w, {'both_Lun': 0., 'one_Lun': .99, 'different_non_Lun': 0.})
        self.assertFalse(r['valid_for_every_possible_family_block'])

    def test_incomplete_cohort_never_reads_results_or_aggregate(self):
        declaration = {'expected_jobs': [{'id': 'pending', 'n': 400, 'provider': 'Anthropic', 'tasks_digest': 'x'}]}
        paths = []

        def read(path):
            paths.append(str(path))
            if str(path).endswith('analysis-predeclaration.json'):
                return declaration
            if str(path).endswith('ledger.json'):
                return {'jobs': {'pending': {'settled': False}}}
            self.fail('Read before full cohort settled: ' + str(path))

        with patch.object(subject.io, 'read_json', side_effect=read):
            with self.assertRaisesRegex(ValueError, 'All8jobs must settle'):
                subject.analyze()
        self.assertEqual(len(paths), 2)


if __name__ == '__main__':
    unittest.main()
