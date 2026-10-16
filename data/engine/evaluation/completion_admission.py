"""Completion-driven concurrency growth with the existing capacity backoff."""

import math
import time

from data.engine.evaluation.admission import Admission


class CompletionAdmission(Admission):
    INTERVAL = 200
    MULTIPLIER = 1.25

    def __init__(self, maximum=512, initial=4, completed=0, saved=None, backoff_seconds=15):
        super().__init__(maximum, recovery_step=0, backoff_seconds=backoff_seconds)
        saved = saved or {}
        if saved and (saved.get("kind") != "completion_growth" or saved.get("interval") != self.INTERVAL
                      or saved.get("multiplier") != self.MULTIPLIER):
            raise ValueError("Unexpected completion-scaling policy")
        if completed < saved.get("completed", 0):
            raise ValueError("Completed response count went backwards")
        self.completed = completed
        self.baseline = saved.get("baseline", completed)
        self.next_boost_at = saved.get("next_boost_at", completed + self.INTERVAL)
        self.ceiling = max(1, min(maximum, saved.get("concurrency", initial)))
        self.pressure_count = saved.get("pressure_count", 0)
        remaining = max(0, saved.get("cooldown_until_unix", 0) - time.time())
        self.until = time.monotonic() + remaining if remaining else 0.0
        self.events = []

    def success(self):
        # The caller counts only status=completed, regardless of correctness.
        self.completed += 1

    def target(self, requested, now=None):
        now = time.monotonic() if now is None else now
        if now >= self.until:
            while self.completed >= self.next_boost_at:
                previous = min(requested, self.ceiling)
                self.ceiling = min(self.maximum, requested, math.ceil(previous * self.MULTIPLIER))
                self.events.append({"reason": "200_completions", "completed": self.next_boost_at,
                                    "previous_concurrency": previous, "concurrency": self.ceiling})
                self.next_boost_at += self.INTERVAL
                self.pressure_count = max(0, self.pressure_count - 1)
        return min(requested, self.ceiling)

    def pressure(self, target, retry_after=None, now=None):
        previous = min(target, self.ceiling)
        until = super().pressure(target, retry_after, now)
        if self.ceiling != previous:
            self.events.append({"reason": "capacity_pressure", "completed": self.completed,
                                "previous_concurrency": previous, "concurrency": self.ceiling})
        return until

    def snapshot(self):
        remaining = max(0, self.until - time.monotonic())
        return {"kind": "completion_growth", "interval": self.INTERVAL, "multiplier": self.MULTIPLIER,
                "counted_status": "completed", "baseline": self.baseline, "completed": self.completed,
                "next_boost_at": self.next_boost_at, "concurrency": self.ceiling,
                "maximum": self.maximum, "pressure_count": self.pressure_count,
                "cooldown_until_unix": time.time() + remaining if remaining else 0}


def completed_responses(records):
    return sum(row["status"] == "completed" for rows in records.values() for row in rows.values())
