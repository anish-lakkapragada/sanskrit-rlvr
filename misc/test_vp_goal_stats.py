import math
import unittest

from misc.vp_goal_stats import accuracy_uncertainty, wilson


def rows(families, per_family, correlated):
    return [{"task": {"id": f"{f}:{i}", "campaign": {"root_family": str(f)}},
             "is_correct": bool((f if correlated else i) % 2)}
            for f in range(families) for i in range(per_family)]


class UncertaintyTests(unittest.TestCase):
    def test_known_interval_and_sample_size(self):
        lo, hi = wilson(50, 100)
        self.assertAlmostEqual(lo, 0.40383153, places=7)
        self.assertAlmostEqual(hi, 0.59616847, places=7)
        s = accuracy_uncertainty(rows(100, 1, True))
        self.assertEqual(s["iid_n_for_strictly_below_one_percentage_point_se_at_observed_p"], 2501)

    def test_root_dependence_is_retained(self):
        s = accuracy_uncertainty(rows(100, 10, True))
        # 100 independent roots, not 1000 independent coin flips.
        self.assertAlmostEqual(s["root_cluster_bootstrap_standard_error"], 0.05, delta=0.002)
        self.assertAlmostEqual(s["estimated_design_effect"], 10, delta=0.5)
        self.assertAlmostEqual(s["root_cluster_sandwich_standard_error"], math.sqrt(0.25 / 99))
        balanced = accuracy_uncertainty(rows(100, 10, False))
        self.assertEqual(balanced["root_cluster_bootstrap_standard_error"], 0)

    def test_unequal_families_use_ratio_residuals(self):
        a = rows(2, 1, True)
        a.extend([{"task": {"id": str(i), "campaign": {"root_family": "1"}},
                   "is_correct": True} for i in range(2, 4)])
        s = accuracy_uncertainty(a)
        self.assertEqual(s['accuracy'], 0.75)
        self.assertAlmostEqual(s['root_cluster_sandwich_standard_error'], 0.375)

    def test_boundary_uncertainty_and_duplicate_rejection(self):
        self.assertGreater(wilson(0, 100)[1], 0.03)
        a = rows(2, 1, True)
        with self.assertRaisesRegex(ValueError, "unique task"):
            accuracy_uncertainty(a + a)
        a[0]["is_correct"] = None
        with self.assertRaisesRegex(ValueError, "Unscored"):
            accuracy_uncertainty(a)

    def test_shared_constituents_cannot_hide_behind_cohort_ids(self):
        a = rows(2, 1, True)
        a[0]['task']['campaign']['root_families'] = ['dhatu-a', 'dhatu-b']
        a[1]['task']['campaign']['root_families'] = ['dhatu-b', 'dhatu-c']
        with self.assertRaisesRegex(ValueError, 'Overlapping dhatu cohorts'):
            accuracy_uncertainty(a)
        a[1]['task']['campaign']['root_families'] = ['dhatu-c', 'dhatu-d']
        s = accuracy_uncertainty(a)
        self.assertEqual(s['root_families'], 4)
        self.assertEqual(s['resampling_clusters'], 2)
        self.assertEqual(s['n_unique'], 2)


if __name__ == "__main__":
    unittest.main()
