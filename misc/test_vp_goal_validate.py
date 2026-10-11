"""Negative checks for errors that could invalidate a released benchmark."""
import copy
import unittest
from misc import vp_goal as c, oai_batch_eval as io
from misc.vp_goal_validate import validate
from misc.vp_goal_grammar import validate_prefixes


class TaskAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = io.read_json(c.OUT / "pada-prefix-candidate-01.json")[0]

    def test_real_task_regenerates(self):
        result = validate([self.task], "development")
        self.assertTrue(result["passed_mechanical_checks"])

    def test_gold_corruption_is_rejected(self):
        t = copy.deepcopy(self.task)
        t["gold_devanagari"] = ["पठति"]
        with self.assertRaisesRegex(ValueError, "gold_devanagari"):
            validate([t], "development")

    def test_unspecified_prompt_cannot_hide_pada(self):
        t = copy.deepcopy(self.task)
        t["prompt_version"] = "composition-v3-fields"
        with self.assertRaisesRegex(ValueError, "absent from the prompt"):
            validate([t], "development")

    def test_split_leakage_and_prior_exposure_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "split violation"):
            validate([self.task], "test")
        with self.assertRaisesRegex(ValueError, "previously exposed"):
            validate([self.task], "development", forbidden_ids=[self.task["id"]])

    def test_cell_exclusions_are_enforced(self):
        t = copy.deepcopy(self.task)
        t["campaign"]["sampling_cell"]["exclude_rules"] = t["campaign"]["trace_rule_ids"][:1]
        with self.assertRaisesRegex(ValueError, "validity exclusions"):
            validate([t], "development")

    def test_slp1_prefix_encoding_is_required_even_if_engine_derives(self):
        validate_prefixes(["aBi", "sam"])
        with self.assertRaisesRegex(ValueError, "SLP1 upasarga"):
            validate_prefixes(["abhi", "sam"])
        t = copy.deepcopy(self.task)
        t["derivation"]["prefixes"] = ["abhi", "sam"]
        with self.assertRaisesRegex(ValueError, "SLP1 upasarga"):
            validate([t], "development")


if __name__ == "__main__":
    unittest.main()
