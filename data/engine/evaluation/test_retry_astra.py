"""Offline retry tests, including archived journals and idempotent batch resume."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from jsonschema import Draft202012Validator

from data.engine.evaluation import retry_astra as retry
from data.engine.evaluation import run_astra as runner
from data.engine.evaluation.scaffold_astra import schema
from data.engine.evaluation.test_run_astra import response, sse


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        (self.folder / "journals").mkdir()
        self.manifest = json.loads((runner.RUN / "manifest.json").read_bytes())
        self.manifest.update(status="completed", finished_at=runner.now())
        self.manifest["execution"].pop("retry_batches", None)
        self.manifest["execution"].pop("retry_runner", None)
        self.tasks = {f: {f"{f}:{i}": {"id": f"{f}:{i}", "gold_devanagari": ["भवति"]}
                          for i in range(2)} for f in runner.FAMILIES}
        self.prompts = {(f, task_id): f"Fixture {task_id}" for f in self.tasks for task_id in self.tasks[f]}
        self.journals = {f: runner.Journal(self.folder / "journals" / f"{f}.jsonl") for f in self.tasks}
        self.failed_keys = []
        for index, (family, task_id) in enumerate(self.prompts):
            journal = self.journals[family]
            journal.append({"event": "started", "task_id": task_id, "attempt_number": 1,
                            "request": {**self.manifest["request_defaults"], "input": self.prompts[family, task_id]}})
            if index < 7:
                self.failed_keys.append((family, task_id))
                event = {"event": "error", "task_id": task_id, "attempt_number": 1,
                         "status": "transport_error", "response_id": f"resp_old_{index}",
                         "error": {"message": "Stream ended without a terminal response; cost unknown"}}
                if index == 0:
                    payload = response()
                    payload.update(status="failed", usage=None, output=[], error={"code": "server_is_overloaded"})
                    event = {"event": "response", "task_id": task_id, "attempt_number": 1, "response": payload}
                elif index > 4:
                    event["error"] = {"type": "RemoteProtocolError", "message": "incomplete chunked read"}
            else:
                event = {"event": "response", "task_id": task_id, "attempt_number": 1,
                         "response": response("<answer>गच्छति</answer>")}
            journal.append(event)
        _, records, _ = runner.recover(self.journals, self.tasks, self.manifest, self.prompts)
        self.original_records = deepcopy(records)
        for family in self.tasks:
            runner.write_results(self.folder, family, records[family], self.tasks[family])
            self.journals[family].archive()
        (self.folder / "manifest.json").write_text(json.dumps(self.manifest))
        self.calls = []
        self.interrupt_one = False
        client_type = httpx.Client

        def local(request):
            body = json.loads(request.content)
            self.calls.append(body)
            self.assertEqual(set(body), set(self.manifest["request_defaults"]) | {"input"})
            self.assertEqual({k: v for k, v in body.items() if k != "input"}, self.manifest["request_defaults"])
            if self.interrupt_one and len(self.calls) == 1:
                return httpx.Response(200, text='data: {"type":"response.created","response":{"id":"resp_interrupted_retry"}}\n\n')
            text = "<answer>गच्छति</answer>" if body["input"] == self.prompts[self.failed_keys[0]] else "<answer>भवति</answer>"
            return httpx.Response(200, content=sse(response(text)))

        self.patches = [
            patch.object(runner, "load_inputs", side_effect=lambda folder: (
                json.loads((folder / "manifest.json").read_bytes()), self.tasks, self.prompts, Draft202012Validator(schema()))),
            patch.object(retry.httpx, "Client", side_effect=lambda **kwargs: client_type(transport=httpx.MockTransport(local))),
            patch.dict(os.environ, {"OPENAI_API_KEY": "fixture-key"}),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_retry_replaces_only_failed_rows_and_preserves_history_and_billing(self):
        report = retry.retry_failed(self.folder, "fixture", 7, concurrency=2)
        self.assertEqual((report["settled"], report["attempts_settled"], report["retry_attempts"]), (8, 15, 7))
        self.assertEqual(report["unknown_cost_attempts"], 7)
        self.assertAlmostEqual(report["known_cost_usd"], 8 * .052)
        self.assertEqual(len(self.calls), 7)
        self.assertEqual({r["input"] for r in self.calls}, {self.prompts[k] for k in self.failed_keys})
        for family in self.tasks:
            rows = json.loads((self.folder / f"{family}.json").read_bytes())
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({r["task_id"] for r in rows}), 2)
            for row in rows:
                if (family, row["task_id"]) in self.failed_keys:
                    self.assertEqual(row["attempt_number"], 2)
                else:
                    self.assertEqual(row, self.original_records[family][row["task_id"]])
            self.assertFalse(self.journals[family].path.exists())
        manifest = json.loads((self.folder / "manifest.json").read_bytes())
        _, attempts, unresolved = runner.recover_attempts(self.journals, self.tasks, manifest, self.prompts)
        self.assertFalse(unresolved)
        for family, task_id in self.failed_keys:
            self.assertEqual(attempts[family][task_id, 1], self.original_records[family][task_id])
        self.assertEqual(sum(f["strict_correct"] for f in report["families"].values()), 6)
        (self.folder / "tinanta.json").unlink()
        resumed = retry.retry_failed(self.folder, "fixture", 7, concurrency=2)
        self.assertEqual(len(self.calls), 7)
        self.assertEqual(resumed["attempts_settled"], 15)
        self.assertEqual(runner.inspect(self.folder, verify=True)["unresolved"], 0)

    def test_interrupted_retry_is_saved_without_automatic_third_attempt(self):
        self.interrupt_one = True
        report = retry.retry_failed(self.folder, "fixture", 7, concurrency=1)
        self.assertEqual(report["unknown_cost_attempts"], 8)
        self.assertEqual(report["attempts_settled"], 15)
        retry.retry_failed(self.folder, "fixture", 7, concurrency=1)
        self.assertEqual(len(self.calls), 7)
        rows = [r for f in self.tasks for r in json.loads((self.folder / f"{f}.json").read_bytes())]
        failed = [r for r in rows if r["status"] != "completed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["attempt_number"], 2)
        self.assertIsNone(failed[0]["cost_usd"])

    def test_unresolved_retry_is_never_resent(self):
        family, task_id = self.failed_keys[0]
        self.manifest["execution"]["retry_batches"] = [{"id": "fixture", "targets": [
            {"family": family, "task_id": task_id, "attempt_number": 2}]}]
        (self.folder / "manifest.json").write_text(json.dumps(self.manifest))
        self.journals[family].append({"event": "started", "task_id": task_id, "attempt_number": 2,
                                    "request": {**self.manifest["request_defaults"], "input": self.prompts[family, task_id]}})
        with self.assertRaisesRegex(RuntimeError, "Unresolved started attempts"):
            retry.retry_failed(self.folder, "fixture", 1)
        self.assertFalse(self.calls)

    def test_unapproved_retry_is_rejected_during_replay(self):
        family, task_id = self.failed_keys[0]
        self.journals[family].append({"event": "started", "task_id": task_id, "attempt_number": 2,
                                    "request": {**self.manifest["request_defaults"], "input": self.prompts[family, task_id]}})
        with self.assertRaisesRegex(RuntimeError, "Unauthorized retry"):
            runner.recover_attempts(self.journals, self.tasks, self.manifest, self.prompts)

    def test_count_and_budget_guards_send_nothing(self):
        with self.assertRaisesRegex(RuntimeError, "Expected 8"):
            retry.retry_failed(self.folder, "fixture", 8)
        reserve = runner.reserve_per_request(self.manifest, self.prompts)
        with self.assertRaisesRegex(RuntimeError, "Budget cannot reserve"):
            retry.retry_failed(self.folder, "fixture", 7, budget=13 * reserve + .052)
        self.assertFalse(self.calls)


if __name__ == "__main__":
    unittest.main()
