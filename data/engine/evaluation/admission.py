"""Admission backoff for new benchmark tasks; this never resends a request."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import random
import time


class Admission:
    def __init__(self, maximum=512, recovery_step=8, backoff_seconds=15):
        self.maximum = maximum
        self.ceiling = maximum
        self.recovery_step = recovery_step
        self.backoff_seconds = backoff_seconds
        self.until = 0.0
        self.recover_at = 0.0
        self.pressure_count = 0
        self.healthy = False

    def target(self, requested, now=None):
        now = time.monotonic() if now is None else now
        if self.healthy and now >= self.recover_at and now >= self.until:
            self.ceiling = min(self.maximum, self.ceiling + self.recovery_step)
            self.recover_at = now + 60
            self.pressure_count = max(0, self.pressure_count - 1)
            self.healthy = False
        return min(requested, self.ceiling)

    def success(self):
        self.healthy = True

    def pressure(self, target, retry_after=None, now=None):
        now = time.monotonic() if now is None else now
        # One burst of failures should cause one reduction, not repeated halving.
        if now >= self.until:
            self.ceiling = max(1, min(self.ceiling, target // 2))
            self.pressure_count += 1
        delay = min(120, self.backoff_seconds * 2 ** min(3, self.pressure_count - 1))
        try:
            hint = float(retry_after)
        except (TypeError, ValueError):
            try:
                hint = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                hint = 0
        if math.isfinite(hint):
            delay = max(delay, hint)
        self.until = max(self.until, now + delay + random.uniform(0, 2))
        self.recover_at = self.until + 60
        self.healthy = False
        return self.until


def capacity_error(row, event):
    error = row.get("error") or {}
    provider = error.get("provider_error") or {}
    if isinstance(provider, dict) and isinstance(provider.get("error"), dict):
        provider = provider["error"]
    return (event.get("http_status") in (429, 500, 502, 503, 504)
            or error.get("http_status") in (429, 500, 502, 503, 504)
            or isinstance(provider, dict) and provider.get("code") in
            ("server_is_overloaded", "server_error", "rate_limit_exceeded", "slow_down"))
