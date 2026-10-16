"""Offline checks for the descriptive statistics used in results.html."""

import unittest

from benchmark_results import comparison_stats, quantiles, summarize


class ReportStatisticsTests(unittest.TestCase):
    def test_interpolated_quantiles(self):
        expected = {
            "min": 0, "p10": 3, "q1": 7.5, "median": 15,
            "q3": 22.5, "p90": 27, "p99": 29.7, "max": 30,
        }
        actual = quantiles([30, 0, 20, 10])
        self.assertEqual(actual.keys(), expected.keys())
        for key, value in expected.items():
            self.assertAlmostEqual(actual[key], value)
        self.assertTrue(all(v == 7 for v in quantiles([7]).values()))
        with self.assertRaises(ValueError):
            quantiles([])

    def test_aligned_outcomes(self):
        result = comparison_stats({
            "A": [1, 1, 0, 0, 0, 1],
            "B": [1, 0, 1, 0, 0, 1],
            "C": [0, 0, 1, 1, 0, 1],
        })
        self.assertEqual(result["n"], 6)
        self.assertEqual(result["correct"], [3, 3, 3])
        self.assertEqual(result["consensus"], [1, 2, 2, 1])
        self.assertEqual(result["wins"], [[0, 1, 2], [1, 0, 1], [2, 1, 0]])
        for i in range(3):
            for j in range(3):
                a_only = result["wins"][i][j]
                b_only = result["wins"][j][i]
                both = result["correct"][i] - a_only
                neither = result["n"] - both - a_only - b_only
                self.assertGreaterEqual(neither, 0)
                self.assertEqual(both + b_only, result["correct"][j])

    def test_comparison_rejects_missing_or_invalid_outcomes(self):
        for vectors in [{}, {"A": []}, {"A": [1], "B": [0, 1]}, {"A": [2]}, {"A": [None]}]:
            with self.subTest(vectors=vectors), self.assertRaises(ValueError):
                comparison_stats(vectors)

    def test_all_selected_attempts_contribute(self):
        rows = [{"correct": correct, "format_ok": fmt, "status": status,
                 "elapsed_ms": 1000 * (i + 1), "cost_usd": .01 * (i + 1),
                 "usage": {"output_tokens": 100 * (i + 1)}}
                for i, (correct, fmt, status) in enumerate([
                    (True, True, "completed"), (True, False, "completed"),
                    (None, False, "refused"), (None, False, "incomplete"),
                ])]
        result = summarize(rows)
        self.assertEqual(result["answer"], 50)
        self.assertEqual(result["strict"], 25)
        self.assertEqual(result["metricCounts"], {"tokens": 4, "duration": 4, "cost": 4})
        self.assertEqual(result["distribution"]["tokens"]["median"], 250)
        self.assertEqual(result["distribution"]["duration"]["p90"], 3.7)
        rows[0]["usage"]["output_tokens"] = None
        with self.assertRaisesRegex(ValueError, "Missing tokens"):
            summarize(rows)


if __name__ == "__main__":
    unittest.main()
