#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Regression checks for gender-aware inputs and complete suffix coverage."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from common import (SUFFIXES, adapter, base_id, derive_base, inventory, load_bases,
                    make_record, nominal, render_task)
from generate import generate
from verify import verify


def entry(stem, linga="Pum", nyap=False):
    gender = {"Pum": "masculine", "Stri": "feminine", "Napumsaka": "neuter"}[linga]
    return dict(id=base_id(stem, nyap, linga), stem=stem, is_nyap=nyap, linga=linga,
                gender=gender, nominal_id=f"nominal:{stem}:{gender}", mw_ids=["1"])


class FullTests(unittest.TestCase):
    def test_shared_inputs_preserve_gender_without_raw_headword_fallback(self):
        inputs = [entry("guru"), entry("guru", "Napumsaka"), entry("gurvI", "Stri", True)]
        for e in inputs:
            e.pop("id")
        audits = [dict(mw_id="1", stem_ids=[e["nominal_id"] for e in inputs], excluded=[])]
        with patch.object(inventory, "load", return_value=(inputs, audits)), \
             patch.object(nominal, "read_source", side_effect=AssertionError("raw CSV fallback")), \
             patch.object(nominal, "normalize_source", side_effect=AssertionError("old normalizer")):
            entries, saved, counts = load_bases()
        self.assertEqual(len(entries), 3)
        self.assertEqual(len({e["id"] for e in entries}), 3)
        self.assertEqual(counts["bases"], 3)
        self.assertEqual(set(saved[0]["base_ids"]), {e["id"] for e in entries})

    def test_feminine_references_and_all_175_suffixes(self):
        for stem, suffix, expected in [("cUqA", "matup", ["cUqAvat"]),
                                       ("mAyA", "vini", ["mAyAvin"]), ("samA", "Ka", ["samIna"]),
                                       ("suparRA", "Qak", ["sOparReya"]), ("dattA", "Qak", ["dAtteya"]),
                                       ("gopI", "Qak", ["gOpeya"])]:
            with self.subTest(stem=stem):
                _, result = derive_base(entry(stem, "Stri", True))
                self.assertEqual([r[0] for r in result], list(SUFFIXES))
                self.assertTrue(all(r[2] is None for r in result))
                self.assertEqual(next(r[1] for r in result if r[0] == suffix), expected)

    def test_source_gender_affects_rules_without_forcing_output_gender(self):
        binary, _ = adapter.prepare()
        requests = [dict(id=g, stem="lakzmI", is_nyap=False, gender=g, suffix="Qak", artha="TasyaApatyam")
                    for g in ("Stri", "Pum", "Napumsaka")]
        result = adapter.derive(binary, requests)
        self.assertEqual([r["forms"] for r in result], [["lAkzmeya"], [], []])
        _, forms = derive_base(entry("guru"))
        self.assertEqual(next(r[1] for r in forms if r[0] == "tal"), ["gurutA"])
        self.assertEqual(result, adapter.derive(binary, requests, log_steps=True))

    def test_invalid_gender_is_not_silently_dropped(self):
        binary, _ = adapter.prepare()
        request = dict(id="bad", stem="cUqA", is_nyap=True, gender="Pum", suffix="matup", artha=None)
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError):
            adapter.derive(binary, [request])
        request.pop("gender")
        with self.assertRaises(subprocess.CalledProcessError):
            adapter.derive(binary, [request])

    def test_meaning_and_input_gender_visible_gold_hidden(self):
        e = entry("guru")
        e["mw_ids"] = ["123"]
        task = make_record(e, "aR", ["gOrava"])
        prompt = render_task(task)
        for visible in ("गुरु", "unrestricted", "aR", "masculine"):
            self.assertIn(visible, prompt)
        for hidden in ("गौरव", "gOrava", "123", task["id"], e["nominal_id"]):
            self.assertNotIn(hidden, prompt)
        task["morphology"]["artha"] = "TasyaBhava"
        with self.assertRaises(ValueError):
            render_task(task)

    def test_small_export_and_full_reverification(self):
        e = entry("guru")
        audit = dict(mw_id="1", base_ids=[e["id"]], input_exclusions=[])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            with patch("generate.load_bases", return_value=([e], [dict(audit)], {})), \
                 patch("verify.load_bases", return_value=([e], [dict(audit)], {})):
                manifest = generate(out, workers=1)
                counts = verify(out, rederive=True, workers=1)
            self.assertEqual(counts["candidates"], 175)
            self.assertEqual(counts["full"], manifest["counts"]["full"])
            attempt = json.loads((out / "attempts.json").read_text())[0]
            self.assertEqual(set(attempt["exported"]) | set(attempt["no_forms"]), set(SUFFIXES))
            with self.assertRaisesRegex(ValueError, "already exists"):
                generate(out)

    def test_engine_error_does_not_replace_existing_export(self):
        e = entry("guru")
        derived = [(s, ["gOrava"], None) if s == "aR" else
                   (s, [], {"type": "EnginePanic", "message": "test failure"}) for s in SUFFIXES]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "full.json").write_text("existing")
            with patch("generate.load_bases", return_value=([e], [], {})), \
                 patch("generate.iter_derivations", return_value=iter([(e["id"], derived)])):
                with self.assertRaisesRegex(ValueError, "Engine errors"):
                    generate(out, overwrite=True, workers=1)
            self.assertEqual((out / "full.json").read_text(), "existing")
            self.assertFalse((out / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
