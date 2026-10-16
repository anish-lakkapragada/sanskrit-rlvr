#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Regression checks for task scope, gold alternatives, and prompt fairness."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from vidyut.prakriya import Vyakarana

from common import (ENGINE_OPTIONS, load_entries, make_record, prompt_conflicts,
                    render_task, request)
from generate import generate


class KrdantaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = {e.code: e for e in load_entries()}
        cls.engine = Vyakarana(**ENGINE_OPTIONS)

    def row(self, code="08.0010", krt="kta"):
        return make_record(self.engine, self.entries[code], krt)

    def test_stems_and_indeclinables(self):
        # Stem-level examples, not masculine nominative singulars.
        for krt, expected in {"kta": ["कृत"], "ktavatu": ["कृतवत्"],
                              "tfc": ["कर्तृ"], "tumun": ["कर्तुम्"], "ktvA": ["कृत्वा"]}.items():
            with self.subTest(krt=krt):
                self.assertEqual(self.row(krt=krt)["gold_devanagari"], expected)

    def test_lexical_prefix_changes_gold_and_is_visible(self):
        row = self.row("02.0041")
        self.assertEqual(row["gold_devanagari"], ["अधीत"])
        self.assertIn("upasarga (verbal prefixes to include, in order): अधि", render_task(row))
        self.assertNotIn("upasarga", render_task(self.row()))

    def test_preserve_all_alternatives(self):
        self.assertEqual(self.row("10.0368")["gold_devanagari"], ["आसादित", "आसन्न"])

    def test_participle_pada_and_defaults(self):
        # bhu is parasmaipada; badh is atmanepada. A nonempty result is required.
        self.assertEqual(self.row("01.0001", "SAnac")["gold_slp1"], [])
        self.assertEqual(self.row("01.0005", "Satf")["gold_slp1"], [])
        row = self.row("01.0005", "SAnac")
        self.assertEqual(row["gold_devanagari"], ["बाधमान"])
        self.assertEqual(row["morphology"], {"krt": "SAnac", "lakara": "Lat", "prayoga": "Kartari"})
        self.assertIn("Lat (present)", render_task(row))
        self.assertIn("Kartari (active)", render_task(row))
        self.assertNotIn("lakara", render_task(self.row()))

    def test_reject_ignored_or_unsupported_conditions(self):
        for m in [{"krt": "kta", "krt_artha": "Karta"},
                  {"krt": "SAnac", "lakara": "Lrt", "prayoga": "Kartari"},
                  {"krt": "SAnac", "lakara": "Lat", "prayoga": "Karmani"},
                  {"krt": "SAnac"}, {"krt": "kAnac"}]:
            with self.subTest(morphology=m), self.assertRaises(ValueError):
                request(self.entries["08.0010"], m)

    def test_no_gold_or_id_leakage(self):
        row = self.row()
        expected = render_task(row)
        row["id"] = "SECRET_ID"
        row["gold_slp1"] = ["SECRET_GOLD"]
        row["gold_devanagari"] = ["SECRET_GOLD"]
        self.assertEqual(render_task(row), expected)
        self.assertNotIn("sanadi", expected)
        self.assertNotIn("conditions", expected)
        row["dhatu"]["sanadi"] = ["san"]
        with self.assertRaises(ValueError):
            render_task(row)

    def test_conflicting_dictionary_entries_are_identified(self):
        a, b = self.row("10.0257", "tfc"), self.row("10.0367", "tfc")
        self.assertEqual(render_task(a), render_task(b))
        self.assertNotEqual(a["gold_slp1"], b["gold_slp1"])
        self.assertEqual(prompt_conflicts([a, b])[0], sorted([a["id"], b["id"]]))
        same = deepcopy(a)
        same["id"] = "same-answer-another-id"
        self.assertEqual(prompt_conflicts([a, same])[0], [])

    def test_citation_hiatus_is_preserved(self):
        entry = next(e for e in self.entries.values() if e.dhatu.aupadeshika == "wuo~Svi")
        self.assertIn("टुओँश्वि", render_task(self.row(entry.code)))

    def test_existing_export_is_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "full.json"
            path.write_text("existing data")
            with self.assertRaises(ValueError):
                generate(Path(tmp))
            self.assertEqual(path.read_text(), "existing data")


if __name__ == "__main__":
    unittest.main()
