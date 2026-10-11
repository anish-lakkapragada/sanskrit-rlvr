"""Offline checks for a paid, fresh evaluation with no repeat attempts."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from misc import oai_direct_eval as runner
from misc.test_oai_batch_eval import TASK, result

base = runner.base


def fixture(out, count=3):
    tasks, previous = [], []
    for i in range(count):
        task = copy.deepcopy(TASK)
        task["id"] = f"task-id-{i}"
        tasks.append(task)
        request = base.batch_request(task, i, runner.MODEL, runner.EFFORT)
        old = base.base_record(task, i, request, "previous", runner.SLUG)
        previous.append(base.apply_result(old, result(i), "before"))
    paths = base.configuration_paths(out, runner.SLUG)
    base.atomic_json(paths["result"], previous)
    base.atomic_json(paths["meta"], {"summary": base.summarize(previous)})
    dataset = out / "tasks.json"
    base.atomic_json(dataset, tasks)
    state = runner.prepare(out, dataset=dataset, expected_count=count)
    return state, previous


def raw_response():
    body = result()["response"]["body"]
    return SimpleNamespace(status_code=200,
        headers=SimpleNamespace(multi_items=lambda: [("x-request-id", "req-direct"), ("x-future", "preserved")]),
        http_response=SimpleNamespace(json=lambda: copy.deepcopy(body)))


class DirectTests(unittest.TestCase):
    def test_prepare_fresh_all_tasks_with_exact_prompt_and_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state, previous = fixture(out)
            rows = runner.load_rows(out, state)
            self.assertEqual(len(rows), 3)
            self.assertEqual(base.read_json(runner.workdir(out) / "previous-results.json"), previous)
            for old, new in zip(previous, rows):
                self.assertEqual(new["task"], old["task"])
                expected = copy.deepcopy(old["request"])
                expected["body"].update(max_output_tokens=6000, service_tier="default")
                self.assertEqual(new["request"], expected)
                self.assertIsNone(new["answer"])
                self.assertIsNone(new["is_correct"])
                self.assertIsNone(new["raw_response"])
                self.assertEqual(new["attempt_number"], 1)
            self.assertEqual(runner.prepare(out), state)

    def test_raw_response_preserved_and_attempt_durable_before_send(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state, _ = fixture(out)
            seed = runner.load_rows(out, state)[0]
            client = Mock(api_key="secret")
            def send(**kwargs):
                self.assertTrue(runner.task_paths(out, seed)["attempt"].exists())
                self.assertEqual(kwargs, seed["request"]["body"])
                return raw_response()
            client.responses.with_raw_response.create.side_effect = send
            row = runner.execute_one(client, out, seed)
            self.assertTrue(row["is_correct"])
            self.assertEqual(row["raw_response"], result()["response"]["body"])
            self.assertIsNone(row["raw_batch_result"])
            self.assertEqual(row["request_id"], "req-direct")
            self.assertIn(("x-future", "preserved"), row["response_headers"])
            with self.assertRaises(FileExistsError):
                runner.execute_one(client, out, seed)
            client.responses.with_raw_response.create.assert_called_once()

    def test_api_failure_does_not_retry_or_keep_old_correct_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state, _ = fixture(out)
            seed = runner.load_rows(out, state)[0]
            client = Mock(api_key="secret-key")
            client.responses.with_raw_response.create.side_effect = TimeoutError("failed secret-key")
            row = runner.execute_one(client, out, seed)
            self.assertEqual(row["status"], "api_error")
            self.assertIsNone(row["answer"])
            self.assertIsNone(row["is_correct"])
            self.assertNotIn("secret-key", json.dumps(row))
            self.assertEqual(runner.load_rows(out, state)[0], row)
            with self.assertRaises(FileExistsError):
                runner.execute_one(client, out, seed)
            client.responses.with_raw_response.create.assert_called_once()

    def test_restart_recovers_receipt_and_never_resends_unknown_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state, _ = fixture(out)
            seeds = runner.load_rows(out, state)
            for seed in seeds[:2]:
                runner.claim_attempt(runner.task_paths(out, seed)["attempt"], {"attempted_at": "past"})
            receipt = {"received_at": "now", "status_code": 200, "headers": [],
                       "latency_ms": 12, "body": result()["response"]["body"]}
            base.atomic_json(runner.task_paths(out, seeds[0])["response"], receipt)
            rows = runner.load_rows(out, state)
            self.assertTrue(rows[0]["is_correct"])
            self.assertEqual(rows[1]["status"], "unknown_outcome")
            self.assertIsNone(rows[1]["is_correct"])
            self.assertEqual(rows[2]["status"], "prepared")
            self.assertEqual(runner.load_rows(out, state), rows)

    def test_publish_recovers_after_interruption_and_protects_external_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state, _ = fixture(out)
            rows = runner.load_rows(out, state)
            rows[0]["status"] = "in_progress"
            actual_atomic = base.atomic_json
            def fail_meta(path, value):
                if Path(path) == out / state["meta_path"]:
                    raise OSError("interrupted metadata save")
                return actual_atomic(path, value)
            with patch.object(base, "atomic_json", side_effect=fail_meta):
                with self.assertRaises(OSError):
                    runner.publish(out, state, rows)
            restored = base.read_json(runner.workdir(out) / "state.json")
            runner.publish(out, restored, rows)
            self.assertEqual(base.read_json(out / state["result_path"]), rows)
            (out / state["result_path"]).write_text("[]\n")
            with self.assertRaisesRegex(ValueError, "changed externally"):
                runner.publish(out, restored, rows)

    def test_complete_run_skips_failed_tasks_and_finished_restart_sends_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state, _ = fixture(out, count=2)
            state.update(max_workers=2, minimum_request_interval_seconds=0, snapshot_interval_seconds=60)
            runner.save_state(out, state)
            client = Mock(api_key="secret")
            client.with_options.return_value = client
            client.responses.with_raw_response.create.side_effect = [TimeoutError("unavailable"), raw_response()]
            with patch.object(base, "api_client", return_value=client), patch.object(runner.signal, "signal"):
                runner.run(out)
                runner.run(out)
            self.assertEqual(client.responses.with_raw_response.create.call_count, 2)
            meta = base.read_json(out / state["meta_path"])
            self.assertEqual(meta["progress"], {"total": 2, "finished": 2, "in_flight": 0, "pending": 0, "attempted": 2})
            self.assertEqual(meta["summary"]["correct"], 1)
            self.assertEqual(meta["summary"]["unscored"], 1)
            self.assertEqual(meta["usage_totals"]["output_tokens"], 900)
            self.assertAlmostEqual(meta["estimated_cost_usd"], (460 * 2 + 900 * 10) / 1e6)


if __name__ == "__main__":
    unittest.main()
