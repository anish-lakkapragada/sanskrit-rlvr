#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Regression checks for source interpretation, inflection, and prompt fairness."""

from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from common import (coordinates, derive_paradigm, finish_audits, iter_array,
                    make_record, normalize_source, paradigm_id, render_task,
                    resolve_descriptor, write_array)
from generate import generate
from verify import verify


def source_row(mw_id, stem, lex, key2=None):
    return dict(source_line=str(mw_id), mw_id=str(mw_id), headword=stem,
                compound_headword=stem if key2 is None else key2, lexnorm=lex)


def entry(stem, descriptor):
    key, reason = resolve_descriptor(stem, descriptor)
    if reason:
        raise AssertionError(reason)
    return dict(id=paradigm_id(key), stem=key[0], is_nyap=key[1], linga=key[2], mw_ids=["123"])


def forms(stem, descriptor, case, number="Eka"):
    return next(forms for c, n, forms, reason in derive_paradigm(entry(stem, descriptor))
                if c == case and n == number and reason is None)


class SubantaTests(unittest.TestCase):
    def test_explicit_feminine_stems(self):
        for stem, desc, expected in [("deva", "f#I", "devI"), ("guru", "f#vI", "gurvI"),
                                     ("alpa", "f", "alpA"), ("rAjan", "f#jYI", "rAjYI"),
                                     ("rAjan", "f#jA", "rAjA")]:
            with self.subTest(stem=stem, descriptor=desc):
                self.assertEqual(resolve_descriptor(stem, desc), ((expected, True, "Stri"), None))
        self.assertEqual(resolve_descriptor("lakzmI", "n#i"), (("lakzmi", False, "Napumsaka"), None))

    def test_uncertain_inputs_are_excluded(self):
        for stem, desc in [("mahat", "m"), ("DImat", "m"), ("pacat", "m"), ("DI", "f"),
                           ("SrI", "f"), ("nAman", "f"), ("yogin", "f"), ("deva", "f#unexpected")]:
            with self.subTest(stem=stem, descriptor=desc):
                self.assertIsNone(resolve_descriptor(stem, desc)[0])

    def test_source_scope_alternatives_and_deduplication(self):
        rows = [source_row(1, "deva", "m:f#I:n"), source_row(2, "deva", "m"),
                source_row(3, "rAjan", "m:f#jYI:f#jA"),
                source_row(4, "trayImaya", "m:f#I:n", "trayI-maya"),
                source_row(5, "Bavat", "m"), source_row(6, "Bavat", "LEXID=pron,STEM=Bavat"),
                source_row(7, "tantrI", "f#I:f#Is"), source_row(8, "tantrI", "f")]
        with patch("common.read_source", return_value=rows):
            entries, audits = normalize_source()
        self.assertEqual(len(entries), 6)
        deva = next(e for e in entries if e["id"] == "subanta:deva:basic:Pum")
        self.assertEqual(deva["mw_ids"], ["1", "2"])
        finish_audits(entries, audits, Counter({e["id"]: 24 for e in entries}))
        self.assertEqual([a["exported_tasks"] for a in audits], [72, 24, 72, 0, 0, 0, 0, 0])
        self.assertEqual([a["new_unique_tasks"] for a in audits], [72, 0, 72, 0, 0, 0, 0, 0])
        self.assertEqual(audits[3]["excluded"][0]["reason"], "compound_boundary")
        self.assertEqual(audits[4]["excluded"][0]["reason"], "special_lexical_metadata")
        self.assertEqual(audits[7]["excluded"][0]["reason"], "ambiguous_constructor")

    def test_deva_complete_paradigm(self):
        expected = [
            ["devaH"], ["devO"], ["devAH"], ["devam"], ["devO"], ["devAn"],
            ["devena"], ["devAByAm"], ["devEH"], ["devAya"], ["devAByAm"], ["deveByaH"],
            ["devAd", "devAt"], ["devAByAm"], ["deveByaH"], ["devasya"], ["devayoH"], ["devAnAm"],
            ["deve"], ["devayoH"], ["devezu"], ["deva"], ["devO"], ["devAH"],
        ]
        derived = derive_paradigm(entry("deva", "m"))
        self.assertEqual([(c, n) for c, n, _, _ in derived], coordinates())
        self.assertEqual([f for _, _, f, _ in derived], expected)
        self.assertTrue(all(reason is None for _, _, _, reason in derived))

    def test_nyap_irregular_and_alternative_forms(self):
        self.assertEqual(forms("deva", "f#I", "Prathama"), ["devI"])
        self.assertEqual(forms("guru", "f#vI", "Trtiya"), ["gurvyA"])
        self.assertEqual(forms("lakzmI", "f", "Prathama"), ["lakzmIH"])
        self.assertEqual(forms("strI", "f", "Dvitiya"), ["strIm", "striyam"])
        self.assertEqual(forms("rAjan", "m", "Saptami"), ["rAjYi", "rAjani"])
        self.assertEqual(forms("nAman", "n", "Prathama", "Dvi"), ["nAmanI", "nAmnI"])
        self.assertEqual(forms("mAtf", "f", "Prathama"), ["mAtA"])

    def test_prompt_uses_resolved_stem_without_gold_or_ids(self):
        row = make_record(entry("guru", "f#vI"), "Trtiya", "Eka", ["gurvyA"])
        prompt = render_task(row)
        self.assertIn("गुर्वी", prompt)
        self.assertIn("feminine", prompt)
        self.assertIn("instrumental", prompt)
        self.assertIn("singular", prompt)
        for hidden in ("गुर्व्या", "gurvyA", "123", "mw_ids", "nyap", row["id"]):
            self.assertNotIn(hidden, prompt)
        row["gold_slp1"], row["gold_devanagari"] = [], []
        row["pratipadika"]["mw_ids"] = ["different"]
        self.assertEqual(render_task(row), prompt)

    def test_json_streams_and_interrupted_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            for rows in ([], [{"unicode": "देव"}], [{"x": 1}, {"x": 2}]):
                write_array(path, iter(rows))
                self.assertEqual(json.loads(path.read_text()), rows)
                self.assertEqual(list(iter_array(path)), rows)
            path.write_text('[\n{"x":1},\n')
            with self.assertRaises(ValueError):
                list(iter_array(path))

    def test_shared_input_export_and_full_reverification(self):
        from copy import deepcopy
        from data.engine.nominal_stems import inventory
        inputs = [dict(nominal_id="nominal:deva:masculine", stem="deva", gender="masculine",
                       linga="Pum", is_nyap=False, mw_ids=["1"]),
                  dict(nominal_id="nominal:devI:feminine", stem="devI", gender="feminine",
                       linga="Stri", is_nyap=True, mw_ids=["1"]),
                  dict(nominal_id="nominal:deva:neuter", stem="deva", gender="neuter",
                       linga="Napumsaka", is_nyap=False, mw_ids=["1"])]
        audits = [dict(mw_id="1", stem_ids=[e["nominal_id"] for e in inputs], excluded=[])]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(inventory, "load", side_effect=lambda: deepcopy((inputs, audits))):
                manifest = generate(Path(tmp))
                counts = verify(Path(tmp), rederive=True)
            self.assertEqual(manifest["counts"]["full"], 72)
            self.assertEqual(counts["full"], 72)
            self.assertEqual(counts["source_rows"]["new_unique_tasks"], 72)

    def test_engine_failure_does_not_publish_partial_dataset(self):
        entries = [entry("deva", "m")]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "export"
            with patch("generate.load_stems", return_value=(entries, [])), \
                 patch("generate.derive_paradigm", side_effect=RuntimeError("engine failed")):
                with self.assertRaisesRegex(RuntimeError, "engine failed"):
                    generate(out)
            self.assertFalse((out / "full.json").exists())
            self.assertFalse((out / "manifest.json").exists())
            (out / "full.json").write_text("existing")
            with self.assertRaisesRegex(ValueError, "already exists"):
                generate(out)
            self.assertEqual((out / "full.json").read_text(), "existing")


if __name__ == "__main__":
    unittest.main()
