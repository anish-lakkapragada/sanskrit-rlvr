import json
from pathlib import Path
import tempfile
import unittest

from misc.vp_simple_benchmark import correct, score
from misc.abc_fairness_audit import final_array


class GradingContractTest(unittest.TestCase):
    task = {"id": "example", "gold_devanagari": ["भवति"], "gold_iast": ["bhavati"], "gold_slp1": ["Bavati"]}

    def test_reasoning_is_optional_and_scripts_share_credit(self):
        for answer in ["भवति", "bhavati", "Bavati"]:
            self.assertTrue(correct(self.task, f"<answer>{answer}</answer>"))
            self.assertTrue(correct(self.task, f"<thinking>Some reasoning.</thinking>\n<answer> {answer} </answer>"))

    def test_wrong_alternatives_do_not_gain_credit(self):
        for text in ["भवति", "<answer>wrong</answer>", "<answer>भवति or wrong</answer>",
                     "<answer>भवति</answer><answer>wrong</answer>", "<answer>भवति",
                     "<answer><answer>भवति</answer>", "<answer></answer>"]:
            self.assertFalse(correct(self.task, text), text)

    def test_diagnostic_extraction_never_repairs_schema_or_picks_by_gold(self):
        self.assertEqual(final_array('Reasoning\n```json\n[{"person": "third"}]\n```'), '[{"person": "third"}]')
        self.assertIsNone(final_array('[{"person": 3}] trailing explanation'))
        self.assertEqual(final_array('[{"person": 3}]\n[{"person": 2}]'), '[{"person": 2}]')

    def test_complete_scoring_and_missing_or_duplicate_trial_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tasks, responses, output = root / "tasks.jsonl", root / "responses.jsonl", root / "summary.json"
            tasks.write_text(json.dumps(self.task) + "\n")
            rows = [{"task_id": "example", "trial": i, "output_text": "<answer>भवति</answer>" if i == 2 else "<answer>wrong</answer>"} for i in range(1, 5)]
            def save(records):
                responses.write_text("".join(json.dumps(r) + "\n" for r in records))
            save(rows)
            score(tasks, responses, output)
            result = json.loads(output.read_text())
            self.assertEqual(result["pass_at_1"], 0.25)
            self.assertEqual(result["pass_at_4"], 1.0)
            for invalid in [rows[:-1], rows + [rows[0]], [dict(rows[0], status="api_error"), *rows[1:]]]:
                save(invalid)
                with self.assertRaises(ValueError):
                    score(tasks, responses, output)


if __name__ == "__main__":
    unittest.main()
