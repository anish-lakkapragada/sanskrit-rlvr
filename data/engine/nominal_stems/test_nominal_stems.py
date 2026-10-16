#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Lexical regression examples and complete export/accounting checks."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate as g
import vp_support as vp


def row(number, headword, lexnorm, compound=None):
    return {"source_line": str(number), "mw_id": str(number), "headword": headword,
            "compound_headword": compound or headword, "lexnorm": lexnorm}


class NominalStemTests(unittest.TestCase):
    def test_dictionary_examples_and_gender_preservation(self):
        entries, audits = g.normalize([row(1, "guru", "m:f#vI:n"), row(2, "guru", "m"),
                                       row(3, "deva", "m:f#I:n")])
        g.validate(entries, audits)
        self.assertEqual({(e["stem"], e["gender"]) for e in entries}, {
            ("guru", "masculine"), ("guru", "neuter"), ("gurvI", "feminine"),
            ("deva", "masculine"), ("deva", "neuter"), ("devI", "feminine"),
        })
        guru = next(e for e in entries if e["id"] == "nominal:guru:masculine")
        self.assertEqual([s["mw_id"] for s in guru["sources"]], ["1", "2"])
        feminine = next(e for e in entries if e["stem"] == "gurvI")
        self.assertEqual(feminine["stem_devanagari"], "गुर्वी")
        self.assertEqual(feminine["sources"][0]["descriptor"], "f#vI")

    def test_alternative_feminines_and_default_rules(self):
        examples = [("alpa", "f", "alpA"), ("DImat", "f#I", "DImatI"),
                    ("rAjan", "f#jYI", "rAjYI"), ("rAjan", "f#jA", "rAjA"),
                    ("pAcaka", "f#ikA", "pAcikA"), ("lakzmI", "n#i", "lakzmi"),
                    ("vadhU", "n", "vadhu")]
        for headword, descriptor, expected in examples:
            with self.subTest(headword=headword, descriptor=descriptor):
                resolved, reason = g.resolve_descriptor(headword, descriptor)
                self.assertIsNone(reason)
                self.assertEqual(resolved[0], expected)
        entries, audits = g.normalize([row(1, "Palgu", "m:f#U:f#u:f#vI:n")])
        g.validate(entries, audits)
        self.assertEqual(len(entries), 5)
        self.assertEqual({e["stem"] for e in entries if e["gender"] == "feminine"},
                         {"PalgU", "Palgu", "PalgvI"})

    def test_no_subanta_scope_filters_or_constructor_guessing(self):
        rows = [row(1, "trayImaya", "m:f#I:n", "trayI-maya"), row(2, "DI", "f"),
                row(3, "SrI", "f"), row(4, "mahat", "m"), row(5, "pacat", "m"),
                row(6, "atonya", "m", "ato-'nya")]
        entries, audits = g.normalize(rows)
        g.validate(entries, audits)
        self.assertEqual(len(entries), 8)
        self.assertTrue(all(r["status"] == "included" for r in audits))
        compound = next(e for e in entries if e["stem"] == "trayImayI")
        self.assertEqual(compound["sources"][0]["compound_headword"], "trayI-maya")
        self.assertTrue(all("is_nyap" not in e and "gold_slp1" not in e for e in entries))

    def test_unresolved_descriptors_remain_auditable(self):
        rows = [row(1, "yogin", "m:f:n"), row(2, "pacat", "m:f:n"),
                row(3, "guru", "m:f#unexpected"), row(4, "a", "LEXID=pron,STEM=idam"),
                row(5, "tatra", "ind"), row(6, "deva!", "m"), row(7, "deva", "x")]
        entries, audits = g.normalize(rows)
        g.validate(entries, audits)
        self.assertEqual([r["status"] for r in audits], ["partial"] * 3 + ["excluded"] * 4)
        self.assertFalse(any(e["gender"] == "feminine" for e in entries))
        self.assertEqual(audits[0]["excluded"][0]["reason"], "unresolved_feminine_stem")
        self.assertEqual(audits[2]["excluded"][0]["reason"], "unresolved_stem_hint")

    def test_suffix_spelling_does_not_identify_a_feminine_formation(self):
        # saMvat has distinct dictionary senses. A bare feminine descriptor
        # does not by itself establish an adjective in the suffix -vat.
        resolved, reason = g.resolve_descriptor("saMvat", "f")
        self.assertIsNone(resolved)
        self.assertEqual(reason, "unresolved_feminine_stem")

    def test_deduplication_keeps_distinct_source_interpretations(self):
        rows = [row(1, "trayImaya", "m", "trayI-maya"), row(2, "trayImaya", "m"),
                row(3, "devI", "f:f#I:f")]
        entries, audits = g.normalize(rows)
        g.validate(entries, audits)
        self.assertEqual(len(entries), 2)
        self.assertEqual(sorted(len(e["sources"]) for e in entries), [2, 2])
        self.assertEqual(len(audits[2]["stem_ids"]), 1)
        entry = next(e for e in entries if e["stem"] == "trayImaya")
        self.assertEqual({s["compound_headword"] for s in entry["sources"]}, {"trayI-maya", "trayImaya"})

    def test_accounting_catches_a_missing_descriptor(self):
        entries, audits = g.normalize([row(1, "guru", "m:f#vI:n")])
        entries = [e for e in entries if e["gender"] != "feminine"]
        with self.assertRaisesRegex(ValueError, "Missing or multiply classified"):
            g.validate(entries, audits)

    def test_vp_filter_removes_unsupported_whole_rows(self):
        rows = [row(1, "guru", "m:f#vI:n"), row(2, "trayImaya", "m", "trayI-maya"),
                row(3, "trayImaya", "m"), row(4, "DI", "f"), row(5, "mahat", "m"),
                row(6, "lakzmI", "f"), row(7, "rAjan", "m"), row(8, "nAman", "n")]
        entries, audits = g.normalize(rows)
        originals = {e["id"]: json.dumps(e, ensure_ascii=False) for e in entries}
        kept, removed, constructors = g.apply_vp_filter(entries, audits, rows)
        g.validate(kept, audits)
        self.assertEqual(len(kept), 6)
        self.assertEqual({e["stem"] for e in removed}, {"trayImaya", "DI", "mahat"})
        self.assertTrue(all(json.dumps(e, ensure_ascii=False) == originals[e["id"]] for e in kept))
        self.assertEqual(constructors["nominal:gurvI:feminine"], "nyap")
        self.assertEqual(constructors["nominal:lakzmI:feminine"], "basic")
        # A simple source does not silently override a compound interpretation.
        self.assertEqual(audits[2]["excluded"][0]["vp_reasons"], ["compound_boundary"])

    def test_vp_filter_checks_metadata_from_excluded_source_rows(self):
        rows = [row(1, "Bavat", "m"), row(2, "Bavat", "LEXID=pron,STEM=Bavat"),
                row(3, "tantrI", "f"), row(4, "tantrI", "f#Is")]
        entries, audits = g.normalize(rows)
        kept, removed, _ = g.apply_vp_filter(entries, audits, rows)
        g.validate(kept, audits)
        self.assertEqual(kept, [])
        reasons = {e["stem"]: e["reasons"] for e in removed}
        self.assertIn("special_lexical_metadata", reasons["Bavat"])
        self.assertEqual(reasons["tantrI"], ["ambiguous_feminine_class"])

    def test_vp_filter_records_constructor_failure(self):
        rows = [row(1, "guru", "m")]
        entries, audits = g.normalize(rows)
        with patch.object(vp, "construct", side_effect=ValueError("bad constructor")):
            kept, removed, _ = g.apply_vp_filter(entries, audits, rows)
        self.assertEqual(kept, [])
        self.assertEqual(removed[0]["reasons"], ["constructor_failure"])
        self.assertEqual(removed[0]["error"]["message"], "bad constructor")
        g.validate(kept, audits)

    def test_reproducible_export_and_existing_file_protection(self):
        rows = [row(1, "guru", "m:f#vI:n"), row(2, "tatra", "ind"),
                row(3, "trayImaya", "m", "trayI-maya")]
        with tempfile.TemporaryDirectory() as tmp, patch.object(g, "read_source", return_value=rows):
            out = Path(tmp)
            counts = g.generate(out)
            self.assertEqual(counts["stem_gender_pairs"], 3)
            self.assertEqual(counts["vp_filter"]["removed_pairs"], 1)
            before = {name: (out / name).read_bytes() for name in (g.LIST, g.AUDIT, g.VP_EXCLUSIONS, g.MANIFEST)}
            self.assertEqual(g.generate(out, check=True), counts)
            with self.assertRaisesRegex(ValueError, "already exists"):
                g.generate(out)
            self.assertEqual(before, {name: (out / name).read_bytes() for name in before})
            self.assertEqual(len(json.loads(before[g.LIST])), 3)
            (out / g.LIST).write_text("[]\n")
            with self.assertRaisesRegex(ValueError, "differs"):
                g.generate(out, check=True)

    def test_source_hash_pin(self):
        with patch.object(g, "sha256", return_value="unexpected"):
            with self.assertRaisesRegex(ValueError, "source hash changed"):
                g.read_source()


if __name__ == "__main__":
    unittest.main()
