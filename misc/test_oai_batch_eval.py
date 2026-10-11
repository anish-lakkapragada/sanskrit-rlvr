"""Offline checks for the paid batch runner's no-repeat and scoring guarantees."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from misc import oai_batch_eval as runner


TASK = {
    "id": "01.0001:Lit:Kartari:Uttama:Dvi",
    "dhatu": {"code": "01.0001", "aupadeshika": "BU", "gana": "Bhvadi", "artha": "sattAyAm"},
    "morphology": {"lakara": "Lit", "prayoga": "Kartari", "purusha": "Uttama", "vacana": "Dvi"},
    "gold_devanagari": ["बभूविव"], "gold_slp1": ["baBUviva"],
}


def record(index=0):
    return runner.base_record(copy.deepcopy(TASK), index,
                              runner.batch_request(TASK, index, "gpt-6-astra", "xhigh"), "test", "gpt-6-astra-xhigh")


def result(index=0, text="<thinking>Derivation</thinking><answer>बभूविव</answer>", **body_fields):
    body = {"id": "resp_test", "status": "completed", "unknown_future_field": {"preserve": True},
            "output": [{"type": "reasoning", "encrypted_content": "opaque"},
                       {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 460, "output_tokens": 900}, **body_fields}
    return {"id": "batch_req_test", "custom_id": f"task-{index:05d}", "error": None,
            "response": {"status_code": 200, "request_id": "req_test", "body": body}, "unknown_envelope": 42}


class BatchTests(unittest.TestCase):
    def test_no_output_limit_omits_parameter_and_preserves_other_settings(self):
        for model, effort in runner.CONFIGS:
            capped = runner.batch_request(TASK, 0, model, effort)
            expected = copy.deepcopy(capped)
            del expected["body"]["max_output_tokens"]
            actual = runner.batch_request(TASK, 0, model, effort, max_output_tokens=None)
            self.assertEqual(actual, expected)
            self.assertNotIn("max_output_tokens", json.loads(json.dumps(actual))["body"])

    def test_prepare_does_not_reuse_existing_capped_run_as_uncapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            runner.atomic_json(runner.state_path(out), {"run_id": "old", "max_output_tokens": 2048})
            with self.assertRaises(ValueError):
                runner.prepare(out, max_output_tokens=None)
            self.assertEqual(runner.read_json(runner.state_path(out))["run_id"], "old")

    def test_exact_prompt_and_no_tools_for_every_configuration(self):
        for model, effort in runner.CONFIGS:
            body = runner.request_body(TASK, model, effort)
            self.assertEqual(body["input"], [{"role": "user", "content": runner.render_vp_task(TASK, runner.TEMPLATE)}])
            self.assertNotIn(TASK["gold_devanagari"][0], body["input"][0]["content"])
            self.assertEqual(body["tools"], [])
            self.assertEqual(body["tool_choice"], "none")
            self.assertEqual(body["max_output_tokens"], 2048)
            self.assertEqual(body["reasoning"], {"mode": "standard", "effort": effort})

    def test_response_preserved_and_gold_checked(self):
        raw = result()
        row = runner.apply_result(record(), raw, "now")
        self.assertEqual(row["raw_batch_result"], raw)
        self.assertTrue(row["is_correct"])
        self.assertIn("<thinking>", row["output_text"])

    def test_nfc_normalization(self):
        row = record()
        row["task"]["gold_devanagari"] = ["क़"]
        actual = runner.apply_result(row, result(text="<answer> क़ </answer>"), "now")
        self.assertTrue(actual["is_correct"])

    def test_no_answer_and_multiple_answers_are_incorrect(self):
        for text in ("बभूविव", "<answer></answer>", "<answer>बभूविव</answer><answer>बभूविव</answer>"):
            row = runner.apply_result(record(), result(text=text), "now")
            self.assertIsNone(row["answer"])
            self.assertFalse(row["is_correct"])

    def test_truncation_does_not_discard_complete_answer(self):
        for text, correct in (("<answer>बभूविव</answer>", True), ("<thinking>unfinished", False)):
            row = runner.apply_result(record(), result(text=text, status="incomplete",
                                     incomplete_details={"reason": "max_output_tokens"}), "now")
            self.assertTrue(row["truncated"])
            self.assertIs(row["is_correct"], correct)

    def test_errors_and_expiration_are_unscored(self):
        raw = {"custom_id": "task-00000", "response": None,
               "error": {"code": "batch_expired", "message": "Expired"}}
        row = runner.apply_result(record(), raw, "now")
        self.assertIsNone(row["is_correct"])
        self.assertEqual(row["raw_batch_result"], raw)

    def test_results_map_by_id_and_keep_missing_tasks(self):
        rows = runner.assemble([record(0), record(1), record(2)], [result(1), result(0)],
                               {"id": "batch_test", "status": "expired"}, "now")
        self.assertEqual([r["task_index"] for r in rows], [0, 1, 2])
        self.assertTrue(rows[0]["is_correct"])
        self.assertIsNone(rows[2]["is_correct"])
        self.assertEqual(runner.summarize(rows)["pass_at_1_all_tasks"], 2 / 3)
        with self.assertRaises(ValueError):
            runner.assemble([record()], [result(), result()], {"id": "b", "status": "completed"}, "now")

    def test_submission_failure_and_restart_never_repeat_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            slug = "gpt-6-astra-xhigh"
            inp = out / "input.jsonl"
            inp.write_text(json.dumps(runner.batch_request(TASK, 0, "gpt-6-astra", "xhigh")) + "\n")
            cfg = {"model": "gpt-6-astra", "effort": "xhigh", "input_path": "input.jsonl",
                   "input_sha256": runner.sha256(inp), "input_file_id": "file_test", "batch_id": None,
                   "batch": None, "status": "uploaded", "task_count": 1, "upload_attempted_at": "past",
                   "submit_attempted_at": None, "submission_error": None, "collected_at": None}
            state = {"run_id": "test", "dataset_sha256": "hash", "prompt_sha256": "hash",
                     "task_count": 1, "configurations": {slug: cfg}}
            runner.atomic_json(runner.configuration_paths(out, slug)["result"], [record()])
            client = Mock(api_key="secret-test-key")
            def fail(**kwargs):
                on_disk = runner.read_json(runner.state_path(out))
                self.assertIsNotNone(on_disk["configurations"][slug]["submit_attempted_at"])
                raise TimeoutError("uncertain outcome")
            client.batches.with_raw_response.create.side_effect = fail
            runner.submit_config(client, out, state, slug)
            runner.submit_config(client, out, runner.read_json(runner.state_path(out)), slug)
            self.assertEqual(client.batches.with_raw_response.create.call_count, 1)
            self.assertEqual(client.files.with_raw_response.create.call_count, 0)

    def test_attempted_upload_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            inp = out / "input.jsonl"
            inp.write_text("{}\n")
            cfg = {"batch_id": None, "submit_attempted_at": None, "submission_error": None,
                   "input_path": "input.jsonl", "input_sha256": runner.sha256(inp),
                   "input_file_id": None, "upload_attempted_at": "past", "status": "uploading"}
            client = Mock(api_key="secret")
            runner.submit_config(client, out, {"configurations": {"test-xhigh": cfg}}, "test-xhigh")
            client.files.with_raw_response.create.assert_not_called()
            client.batches.with_raw_response.create.assert_not_called()

    def test_credentials_redacted_in_error(self):
        err = runner.error_details(ValueError("bad secret-value"), SimpleNamespace(api_key="secret-value"))
        self.assertNotIn("secret-value", json.dumps(err))


if __name__ == "__main__":
    unittest.main()
