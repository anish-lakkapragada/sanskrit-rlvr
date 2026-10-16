#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Check task deduplication, pilot bounds, and known preview exclusions."""

import unittest
from unittest.mock import patch

from pilot import normalized_bases, preview_exclusion, preview_record, render_task, sample_bases


class PilotTests(unittest.TestCase):
    def test_genders_do_not_duplicate_taddhita_tasks(self):
        entries = [
            dict(stem="guru", is_nyap=False, linga="Pum", mw_ids=["1", "2"]),
            dict(stem="guru", is_nyap=False, linga="Napumsaka", mw_ids=["1", "3"]),
            dict(stem="gurvI", is_nyap=True, linga="Stri", mw_ids=["1"]),
        ]
        with patch("pilot.nominal.normalize_source", return_value=(entries, [{}, {}, {}])):
            bases, count = normalized_bases()
        self.assertEqual(count, 3)
        self.assertEqual(len(bases), 2)
        guru = next(b for b in bases if b["stem"] == "guru")
        self.assertEqual(guru["mw_ids"], ["1", "2", "3"])
        self.assertEqual(guru["source_genders"], ["Napumsaka", "Pum"])

    def test_failing_constructor_family_cannot_enter_preview(self):
        feminine = dict(stem="cUqA", is_nyap=True, mw_ids=["1"])
        self.assertEqual(preview_exclusion(feminine, "matup", "TadAsyaAstiAsmin"),
                         "feminine_taddhita_constructor_unreviewed")
        with self.assertRaises(ValueError):
            preview_record(feminine, "matup", "TadAsyaAstiAsmin", ["cUqAmat"])
        self.assertIsNone(preview_exclusion(feminine, "tva", "TasyaBhava"))

    def test_meaning_and_constructor_are_visible_but_gold_is_hidden(self):
        base = dict(stem="devI", is_nyap=True, mw_ids=["123"])
        row = preview_record(base, "tva", "TasyaBhava", ["devItva"])
        prompt = render_task(row)
        for required in ("देवी", "त्व", "state or quality", "feminine", "without adding case"):
            self.assertIn(required, prompt)
        for hidden in ("देवीत्व", "devItva", "123", row["id"], "gold_slp1"):
            self.assertNotIn(hidden, prompt)
        row["morphology"]["artha"] = "TadAsyaAstiAsmin"
        with self.assertRaises(ValueError):
            render_task(row)

    def test_sampling_is_bounded_and_input_order_independent(self):
        pool = [dict(id=f"base:fixture{i}:basic", stem=f"fixture{i}a", is_nyap=False) for i in range(200)]
        with patch("pilot.ANCHORS", ()):
            selected, _ = sample_bases(pool, 64)
            backwards, _ = sample_bases(list(reversed(pool)), 64)
        self.assertEqual(selected, backwards)
        self.assertEqual(len(selected), 64)
        for size in (0, 10, 257, 100000):
            with self.assertRaises(ValueError):
                sample_bases(pool, size)


if __name__ == "__main__":
    unittest.main()
