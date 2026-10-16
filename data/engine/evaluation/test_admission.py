"""Offline capacity-backoff and recovery checks."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import unittest
from unittest.mock import patch

from data.engine.evaluation.admission import Admission, capacity_error


class AdmissionTests(unittest.TestCase):
    @patch('data.engine.evaluation.admission.random.uniform', return_value=0)
    def test_burst_halves_once_then_recovers_after_success(self, _):
        a = Admission(recovery_step=4)
        self.assertEqual(a.target(48, now=100), 48)
        self.assertEqual(a.pressure(48, now=100), 115)
        self.assertEqual(a.target(48, now=101), 24)
        a.pressure(48, now=102)
        self.assertEqual(a.ceiling, 24)
        self.assertEqual(a.target(48, now=500), 24)  # No healthy result yet.
        a.success()
        self.assertEqual(a.target(48, now=500), 28)
        a.success()
        self.assertEqual(a.target(48, now=559), 28)
        self.assertEqual(a.target(48, now=560), 32)
        self.assertEqual(a.target(12, now=561), 12)  # Manual target remains binding.

    @patch('data.engine.evaluation.admission.random.uniform', return_value=0)
    def test_retry_after_is_not_capped_and_failures_back_off(self, _):
        a = Admission()
        self.assertEqual(a.pressure(128, retry_after='600', now=100), 700)
        self.assertEqual(a.target(128, now=699), 64)
        self.assertEqual(a.pressure(64, now=701), 731)
        self.assertEqual(a.ceiling, 32)
        later = format_datetime(datetime.now(timezone.utc)+timedelta(seconds=300))
        self.assertGreater(a.pressure(32, retry_after=later, now=800), 1098)

    def test_capacity_errors_and_isolated_transport_errors_differ(self):
        self.assertTrue(capacity_error({'error': {'http_status': 429}}, {}))
        self.assertTrue(capacity_error({'error': {'provider_error': {'code': 'server_is_overloaded'}}}, {}))
        self.assertTrue(capacity_error({}, {'http_status': 503}))
        self.assertFalse(capacity_error({'status': 'transport_error', 'error': {'type': 'ReadError'}}, {}))


if __name__ == '__main__':
    unittest.main()
