import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from data.engine.evaluation import experiment_opus_wording as exp


class WordingExperimentTests(unittest.TestCase):
    def test_fields_and_answer_contract_preserved(self):
        for family in exp.INTRO:
            prompt = (exp.ROOT / f"data/engine/prompts/v2/vp_{family}.txt").read_text()
            fields = prompt.split("=== Your task ===", 1)[1]
            answer_rule = prompt.split("Write ONLY the final form", 1)[1].split("=== Your task ===", 1)[0]
            for variant in exp.VARIANTS:
                changed = exp.change_prompt(prompt, family, variant)
                self.assertIn("Write ONLY the final form" + answer_rule.strip(), changed)
                if variant != "dictionary_labels":
                    self.assertTrue(changed.endswith(fields))
                else:
                    for token in fields.split():
                        if token.startswith("{"):
                            self.assertIn(token, changed)

    def test_held_out_cases_disjoint_and_exact_budget(self):
        cases = [{"case_id": str(i), "phase": "discovery" if i < 10 else "holdout",
                  "family": "krdanta", "task": {"id": str(i)},
                  "original_prompt": "Write ONLY the final form\n=== Your task ===\nword: नमः"} for i in range(40)]
        discovery = exp.make_plan(cases, "discovery", exp.VARIANTS)
        holdout = exp.make_plan(cases, "holdout", ("original", "linguistics_context"))
        self.assertEqual((len(discovery), len(holdout)), (40, 60))
        self.assertEqual(len(discovery) + len(holdout), exp.LIMIT)
        self.assertFalse({p["case_id"] for p in discovery} & {p["case_id"] for p in holdout})

    def test_budget_violation_detected_from_durable_markers(self):
        events = [{"event": "started", "task_id": str(i)} for i in range(101)]
        with tempfile.TemporaryDirectory() as directory, patch.object(exp.base.Journal, "read", return_value=iter(events)):
            with self.assertRaisesRegex(RuntimeError, "budget exceeded"):
                exp.recover(Path(directory), {"submitted_requests": 101}, [])

    def test_missing_start_markers_prevent_resetting_budget(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(exp.base.Journal, "read", return_value=iter([])):
            with self.assertRaisesRegex(RuntimeError, "markers missing"):
                exp.recover(Path(directory), {"submitted_requests": 20}, [])

    def test_recovered_refusal_is_not_counted_as_correct_or_api_error(self):
        cases = [{"case_id": "one", "task": {"id": "real_task", "gold_devanagari": ["रामः"]}}]
        plan = {"request_key": "r1", "case_id": "one", "family": "subanta", "phase": "discovery", "variant": "original"}
        events = [{"event": "started", "task_id": "r1", "plan": plan},
                  {"event": "response", "task_id": "r1", "attempt_number": 1, "usage_final": True,
                   "response": {"model": "claude-opus-5-5", "content": [], "stop_reason": "refusal",
                                "stop_details": {"type": "refusal", "category": "cyber"},
                                "usage": {"input_tokens": 100, "output_tokens": 0}}}]
        with tempfile.TemporaryDirectory() as directory, patch.object(exp.base.Journal, "read", return_value=iter(events)):
            _, starts, records = exp.recover(Path(directory), {"submitted_requests": 1, "pricing": {}}, cases)
        self.assertEqual(set(starts), set(records))
        self.assertEqual(records["r1"]["task_id"], "real_task")
        self.assertEqual(records["r1"]["status"], "refused")
        self.assertIsNone(records["r1"]["correct"])
        self.assertEqual(records["r1"]["cost_usd"], 0)


if __name__ == "__main__":
    unittest.main()
