"""Offline checks of grading, isolated trials, and duplicate-spend protection."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from misc import abc_astra_eval as ev

DATASET = ev.ROOT / "benchmarks/a-b-c"


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = {f: ev.read_jsonl(DATASET / f"VP-Bench-{f}-400.jsonl") for f in "ABC"}

    def test_every_gold_and_all_three_scripts(self):
        for task in self.tasks["A"]:
            self.assertTrue(ev.grade(task, json.dumps(task["answer"]))["is_correct"], task["id"])
            for key in ("root_iast", "root_aliases_slp1"):
                answer = copy.deepcopy(task["answer"])
                for prediction, gold in zip(answer, task["accepted_analyses"]):
                    prediction["root"] = gold[key][0] if key == "root_aliases_slp1" else gold[key]
                self.assertTrue(ev.grade(task, json.dumps(list(reversed(answer))))["is_correct"], (task["id"], key))
            for i, gold in enumerate(task["accepted_analyses"]):
                for spelling in ev.root_spellings(gold):
                    answer = copy.deepcopy(task["answer"])
                    answer[i]["root"] = spelling
                    self.assertTrue(ev.grade(task, json.dumps(answer))["is_correct"], (task["id"], spelling))
        for family in "BC":
            for task in self.tasks[family]:
                for key in ("accepted_devanagari", "accepted_iast", "accepted_slp1"):
                    for answer in task[key]:
                        self.assertTrue(ev.grade(task, f"<answer>{answer}</answer>")["is_correct"], (task["id"], key, answer))

    def test_incomplete_extra_duplicate_and_wrong_analyses_fail(self):
        task = next(t for t in self.tasks["A"] if len(t["answer"]) > 1)
        for answer in (task["answer"][:-1], task["answer"] + task["answer"][:1]):
            self.assertFalse(ev.grade(task, json.dumps(answer))["is_correct"])
        wrong = copy.deepcopy(task["answer"])
        wrong[0]["person"] = 99
        self.assertFalse(ev.grade(task, json.dumps(wrong))["is_correct"])
        wrong[0]["person"] = True
        self.assertFalse(ev.grade(task, json.dumps(wrong))["is_correct"])
        duplicate = [task["answer"][0]] * len(task["answer"])
        self.assertFalse(ev.grade(task, json.dumps(duplicate))["is_correct"])
        self.assertFalse(ev.grade(task, '```json\n' + json.dumps(task["answer"]) + '\n```')["is_correct"])

    def test_tag_format_no_multiple_answers_and_no_harvard_conversion(self):
        task = self.tasks["B"][0]
        answer = task["accepted_slp1"][0]
        for text in (answer, f"Explanation <answer>{answer}</answer>",
                     f"<answer>{answer}</answer><answer>{answer}</answer>", "<answer></answer>",
                     "<answer>chopsyAvaH</answer>"):
            self.assertFalse(ev.grade(task, text)["is_correct"], text)
        self.assertTrue(ev.grade(task, f" \n<answer> {answer} </answer>\n")["is_correct"])

    def test_all_4800_requests_have_only_the_original_prompt_and_no_tools(self):
        ids = set()
        for tasks in self.tasks.values():
            for task in tasks:
                bodies = []
                for trial in range(1, 5):
                    req = ev.request(task, trial)
                    self.assertNotIn(req["custom_id"], ids)
                    ids.add(req["custom_id"])
                    body = req["body"]
                    self.assertEqual(body["input"], [{"role": "user", "content": task["prompt"]}])
                    self.assertEqual(body["tools"], [])
                    self.assertEqual(body["tool_choice"], "none")
                    self.assertEqual(body["model"], "gpt-6-astra")
                    self.assertEqual(body["reasoning"], {"mode": "standard", "effort": "xhigh"})
                    self.assertNotIn("previous_response_id", body)
                    self.assertNotIn("conversation", body)
                    bodies.append(body)
                self.assertTrue(all(b == bodies[0] for b in bodies))
        self.assertEqual(len(ids), 4800)

    def test_pass_at_4_counts_tasks_and_exposes_unknown_trials(self):
        tasks = self.tasks["B"][:2]
        rows = [{"task_id": t["id"], "trial": i, "is_correct": j == 0 and i == 4,
                 "status": "completed"} for j, t in enumerate(tasks) for i in range(1, 5)]
        summary = ev.metrics(tasks, rows)
        self.assertEqual(summary["pass_at_4"], 0.5)
        self.assertEqual(summary["mean_pass_at_1"], 1 / 8)
        rows[-1]["is_correct"] = None
        summary = ev.metrics(tasks, rows)
        self.assertIsNone(summary["pass_at_4"])
        self.assertEqual(summary["pass_at_4_lower_bound"], 0.5)
        self.assertEqual(summary["pass_at_4_upper_bound"], 1)

    def test_uncertain_submission_cannot_repeat_paid_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = ev.prepare(out, DATASET)
            state["families"] = {"A": state["families"]["A"]}
            state["families"]["A"]["input_file_id"] = "file_test"
            client = Mock(api_key="fake-secret")
            client.batches.with_raw_response.create.side_effect = TimeoutError("ambiguous POST")
            with self.assertRaises(RuntimeError):
                ev.submit(client, out, state)
            ev.submit(client, out, ev.io.read_json(out / "state.json"))
            self.assertEqual(client.batches.with_raw_response.create.call_count, 1)
            client.files.with_raw_response.create.assert_not_called()

    def test_response_model_and_tool_calls_checked(self):
        task = self.tasks["B"][0]
        body = {"id": "resp_test", "model": ev.MODEL, "status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": task["answer"]}]}]}
        result = {"response": {"status_code": 200, "body": body}}
        self.assertTrue(ev.grade_result(task, 1, result)["is_correct"])
        body["output"].append({"type": "web_search_call"})
        self.assertEqual(ev.grade_result(task, 1, result)["status"], "protocol_error")
        body["output"].pop()
        body["model"] = "other-model"
        self.assertEqual(ev.grade_result(task, 1, result)["status"], "protocol_error")
        self.assertIsNone(ev.grade_result(task, 1, None)["is_correct"])


if __name__ == "__main__":
    unittest.main()
