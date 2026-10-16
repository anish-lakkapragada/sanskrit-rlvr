"""Offline scoring and schema checks; fixtures are synthetic, not API responses.

uv run --python 3.11 --with jsonschema==4.23.0 python -m unittest \
    data.engine.evaluation.test_scaffold
"""

import json
import unittest

from jsonschema import Draft202012Validator, ValidationError

from data.engine.evaluation.scaffold_astra import ROOT, RUN, REQUEST_DEFAULTS, schema
from data.engine.evaluation.scoring import score_output


def example_record():
    task = json.loads((ROOT / "data/benchmark/tinanta/tinanta.json").read_bytes())[0]
    output = f"<answer>{task['gold_devanagari'][0]}</answer>"
    return {
        "task_id": task["id"], "attempt_number": 1,
        "status": "completed", "output_text": output,
        **score_output(output, task["gold_devanagari"]),
        "usage": {"input_tokens": 200, "output_tokens": 1000, "total_tokens": 1200,
                  "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 900}},
        "cost_usd": 0.052, "request_id": "req_synthetic_fixture",
        "response_id": "resp_synthetic_fixture", "elapsed_ms": 1000, "error": None,
    }


class ScoringTests(unittest.TestCase):
    def test_any_accepted_alternative_and_outer_whitespace(self):
        result = score_output(" \n<answer>  भवति\n</answer> \n", ["भवती", "भवति"])
        self.assertEqual(result, {"answer": "भवति", "correct": True, "format_ok": True})

    def test_correctness_and_format_are_separate(self):
        result = score_output("Here: <answer>भवति</answer>", ["भवति"])
        self.assertTrue(result["correct"])
        self.assertFalse(result["format_ok"])

    def test_wrong_answer_can_have_valid_format(self):
        result = score_output("<answer>गच्छति</answer>", ["भवति"])
        self.assertFalse(result["correct"])
        self.assertTrue(result["format_ok"])

    def test_invalid_blocks_are_not_salvaged(self):
        for text in ("भवति", "<answer> </answer>", "<answer>भवति</answer><answer>भवति</answer>",
                     "<answer><b>भवति</b></answer>", "<answer>भवति", "<ANSWER>भवति</ANSWER>"):
            with self.subTest(text=text):
                result = score_output(text, ["भवति"])
                self.assertIsNone(result["answer"])
                self.assertFalse(result["correct"] or result["format_ok"])

    def test_no_punctuation_or_unicode_repairs(self):
        self.assertFalse(score_output("<answer>भवति।</answer>", ["भवति"])["correct"])
        self.assertFalse(score_output("<answer>\u0958</answer>", ["\u0915\u093c"])["correct"])

    def test_refusals_errors_and_partial_answers_are_unscored(self):
        for status in ("refused", "incomplete", "api_error", "transport_error", "unknown"):
            with self.subTest(status=status):
                result = score_output("<answer>भवति</answer>", ["भवति"], status)
                self.assertEqual(result["answer"], "भवति")
                self.assertIsNone(result["correct"])


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = schema()
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def test_saved_schema_matches_generator(self):
        self.assertEqual(json.loads((RUN / "result.schema.json").read_bytes()), self.schema)

    def test_complete_record_and_future_raw_usage_fields(self):
        row = example_record()
        row["usage"]["future_provider_detail"] = {"preserve": True}
        self.validator.validate([row])

    def test_duplicate_task_request_and_derived_fields_are_rejected(self):
        for key, value in (("task", {}), ("request", {}), ("accepted_answers", []),
                           ("artifacts", {}), ("output_tokens", 1000), ("strict_correct", True)):
            with self.subTest(key=key):
                row = example_record()
                row[key] = value
                with self.assertRaises(ValidationError):
                    self.validator.validate([row])
        self.assertEqual(len(self.schema["$defs"]["result"]["required"]), 13)

    def test_request_settings_live_once_in_manifest_without_output_cap(self):
        manifest = json.loads((RUN / "manifest.json").read_bytes())
        self.assertEqual(manifest["request_defaults"], REQUEST_DEFAULTS)
        self.assertEqual(REQUEST_DEFAULTS["model"], "gpt-6-astra")
        self.assertEqual(REQUEST_DEFAULTS["reasoning"], {"effort": "xhigh"})
        self.assertNotIn("max_output_tokens", REQUEST_DEFAULTS)

    def test_unresolved_request_has_unknown_cost(self):
        row = example_record()
        row.update(status="transport_error", output_text="", usage=None, cost_usd=None,
                   response_id=None, error={"message": "Connection lost before terminal usage"},
                   **score_output("", [], "transport_error"))
        self.validator.validate([row])
        row["cost_usd"] = 0
        with self.assertRaises(ValidationError):
            self.validator.validate([row])

    def test_api_error_cannot_be_marked_graded(self):
        row = example_record()
        row["status"] = "api_error"
        with self.assertRaises(ValidationError):
            self.validator.validate([row])

    def test_correct_answer_can_have_invalid_format(self):
        row = example_record()
        row["output_text"] = "Here: " + row["output_text"]
        row["format_ok"] = False
        self.validator.validate([row])


if __name__ == "__main__":
    unittest.main()
