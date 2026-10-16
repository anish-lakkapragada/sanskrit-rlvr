"""Regression checks for invalid coordinates and hidden prompt information."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from data.engine.tinanta import generate
from data.engine.tinanta.common import coordinate_exclusion, prompt_conflicts, render_task


class TinantaEligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = {e.code: e for e in generate.load_entries()}
        cls.engine = generate.Vyakarana(**generate.ENGINE_OPTIONS)

    def test_impersonal_construction_has_only_third_person_singular(self):
        self.assertEqual(len(generate.ELIGIBLE_COORDINATES), 190)
        impersonal = [c for c in generate.ELIGIBLE_COORDINATES if c[1] == "Bhave"]
        self.assertEqual(len(impersonal), 10)
        self.assertEqual({c[2:] for c in impersonal}, {("Prathama", "Eka")})
        # The exact failed calibration request must never reach VP again.
        with self.assertRaisesRegex(ValueError, "Invalid bhave"):
            generate.make_record(self.engine, self.entries["10.0333"], ("Lun", "Bhave", "Madhyama", "Eka"))

    def test_valid_bhave_still_has_gold(self):
        row = generate.make_record(self.engine, self.entries["01.0001"], ("Lat", "Bhave", "Prathama", "Eka"))
        self.assertIn("BUyate", row["gold_slp1"])
        self.assertIsNone(coordinate_exclusion(("Lat", "Bhave", "Prathama", "Eka")))

    def test_lexical_prefix_is_visible(self):
        row = generate.make_record(self.engine, self.entries["02.0012"], ("Lat", "Kartari", "Prathama", "Eka"))
        self.assertIn("upasarga (verbal prefixes to include, in order): आङ्", render_task(row))
        self.assertNotIn(row["id"], render_task(row))

    def test_actual_homograph_conflict_is_removed_symmetrically(self):
        coordinate = ("Lat", "Kartari", "Prathama", "Eka")
        rows = [generate.make_record(self.engine, self.entries[code], coordinate)
                for code in ("10.0257", "10.0367")]
        self.assertEqual(render_task(rows[0]), render_task(rows[1]))
        self.assertNotEqual(rows[0]["gold_slp1"], rows[1]["gold_slp1"])
        self.assertEqual(prompt_conflicts(rows), sorted(r["id"] for r in rows))
        same = copy.deepcopy(rows[0]); same["id"] = "another-source"
        self.assertEqual(prompt_conflicts([rows[0], same]), [])

    def test_engine_error_cannot_replace_existing_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            for name in generate.FILES:
                (output / name).write_text("previous export")
            error = {"status": "error", "error": {"type": "RuntimeError", "message": "injected failure"}}
            with patch.object(generate, "make_record", return_value=error):
                with self.assertRaisesRegex(RuntimeError, "Engine failure"):
                    generate.generate(output, overwrite=True)
            for name in generate.FILES:
                self.assertEqual((output / name).read_text(), "previous export")


if __name__ == "__main__":
    unittest.main()
