"""Offline checks for the user-requested 200-response / 1.25x policy."""

import unittest
from unittest.mock import patch

from data.engine.evaluation.completion_admission import CompletionAdmission, completed_responses


class CompletionAdmissionTests(unittest.TestCase):
    def test_growth_occurs_only_every_two_hundred_completions(self):
        a = CompletionAdmission(initial=44, completed=13000)
        for _ in range(199):
            a.success()
        self.assertEqual(a.target(512, now=100000), 44)
        a.success()
        self.assertEqual(a.target(512, now=100001), 55)
        self.assertEqual(a.target(512, now=200000), 55)
        for _ in range(200):
            a.success()
        self.assertEqual(a.target(512, now=200001), 69)

    def test_capacity_burst_halves_once_and_honors_cooldown(self):
        a = CompletionAdmission(initial=55)
        with patch('data.engine.evaluation.admission.random.uniform', return_value=0):
            self.assertEqual(a.pressure(55, retry_after='30', now=0), 30)
            self.assertEqual(a.target(512, now=1), 27)
            a.pressure(55, retry_after='30', now=1)
            self.assertEqual(a.target(512, now=2), 27)
            for _ in range(200):
                a.success()
            self.assertEqual(a.target(512, now=30), 27)
            self.assertEqual(a.target(512, now=32), 34)
            a.pressure(34, now=33)
            self.assertEqual(a.target(512, now=34), 17)

    def test_restart_preserves_progress_and_does_not_duplicate_a_boost(self):
        a = CompletionAdmission(initial=40, completed=1000)
        for _ in range(200):
            a.success()
        self.assertEqual(a.target(512), 50)
        resumed = CompletionAdmission(initial=4, completed=1200, saved=a.snapshot())
        self.assertEqual(resumed.target(512), 50)
        self.assertEqual(resumed.next_boost_at, 1400)
        # Journal replay can contain completions newer than the last checkpoint.
        resumed = CompletionAdmission(initial=4, completed=1400, saved=a.snapshot())
        self.assertEqual(resumed.target(512), 63)
        self.assertEqual(resumed.next_boost_at, 1600)

    def test_maximum_minimum_and_requested_limit(self):
        a = CompletionAdmission(initial=500)
        for _ in range(200):
            a.success()
        self.assertEqual(a.target(512), 512)
        self.assertEqual(a.target(256), 256)
        b = CompletionAdmission(initial=1)
        b.pressure(1)
        self.assertEqual(b.target(512), 1)

    def test_errors_refusals_and_incomplete_responses_do_not_trigger_growth(self):
        records = {'family': {str(i): {'status': status, 'correct': False} for i, status in enumerate(
            ['completed', 'completed', 'api_error', 'transport_error', 'refused', 'incomplete'])}}
        self.assertEqual(completed_responses(records), 2)


if __name__ == '__main__':
    unittest.main()
