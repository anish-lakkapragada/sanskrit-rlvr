"""Offline tests for the paid runner; HTTP is replaced with local fixtures."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import httpx

from data.engine.evaluation import run_astra as runner


MANIFEST = json.loads((runner.RUN / "manifest.json").read_bytes())


def response(text="<answer>भवति</answer>"):
    return {"id": "resp_fixture", "status": "completed", "model": "gpt-6-astra",
            "service_tier": "default", "output": [{"type": "message", "content": [
                {"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 200, "output_tokens": 1000,
                      "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                      "output_tokens_details": {"reasoning_tokens": 900}, "total_tokens": 1200}}


def terminal_event(payload):
    return {"event": "response", "task_id": "fixture", "attempt_number": 1,
            "request_id": "req_fixture", "elapsed_ms": 10, "response": payload}


def sse(payload):
    return ("event: response.completed\ndata: " + json.dumps(
        {"type": "response.completed", "response": payload}) + "\n\n").encode()


class CostAndScoringTests(unittest.TestCase):
    def test_reasoning_is_not_billed_twice(self):
        cost, error = runner.estimate_cost(response(), MANIFEST["pricing"])
        self.assertAlmostEqual(cost, 0.052)
        self.assertIsNone(error)

    def test_cache_reads_and_writes_are_priced_separately(self):
        payload = response()
        payload["usage"]["input_tokens_details"] = {"cached_tokens": 50, "cache_write_tokens": 100}
        cost, error = runner.estimate_cost(payload, MANIFEST["pricing"])
        self.assertAlmostEqual(cost, (50 * 10 + 50 + 100 * 12.5 + 1000 * 50) / 1e6)
        self.assertIsNone(error)

    def test_missing_usage_unknown_tier_and_bad_counters_are_unknown_cost(self):
        variants = []
        payload = response()
        payload["usage"] = None
        variants.append(payload)
        payload = response()
        payload["service_tier"] = "priority"
        variants.append(payload)
        payload = response()
        payload["usage"]["input_tokens_details"]["cached_tokens"] = 300
        variants.append(payload)
        for payload in variants:
            with self.subTest(payload=payload):
                cost, error = runner.estimate_cost(payload, MANIFEST["pricing"])
                self.assertIsNone(cost)
                self.assertTrue(error)

    def test_long_context_rate_is_selected(self):
        payload = response()
        payload["usage"]["input_tokens"] = 300000
        self.assertAlmostEqual(runner.estimate_cost(payload, MANIFEST["pricing"])[0], 6.075)

    def test_refusal_preserves_details_and_is_unscored(self):
        payload = response()
        payload["output"][0]["content"] = [{"type": "refusal", "refusal": "Fixture refusal", "category": "cyber"}]
        row = runner.result_row(terminal_event(payload), {"id": "fixture", "gold_devanagari": ["भवति"]}, MANIFEST)
        self.assertEqual(row["status"], "refused")
        self.assertIsNone(row["correct"])
        self.assertEqual(row["error"]["refusals"][0]["category"], "cyber")
        self.assertAlmostEqual(row["cost_usd"], 0.052)

    def test_incomplete_answer_is_unscored_and_exact_membership_is_unchanged(self):
        task = {"id": "fixture", "gold_devanagari": ["भवति"]}
        payload = response()
        payload.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        row = runner.result_row(terminal_event(payload), task, MANIFEST)
        self.assertIsNone(row["correct"])
        self.assertEqual(row["answer"], "भवति")
        row = runner.result_row(terminal_event(response("Here: <answer>भवति</answer>")), task, MANIFEST)
        self.assertTrue(row["correct"])
        self.assertFalse(row["format_ok"])


class StreamAndJournalTests(unittest.TestCase):
    def test_terminal_response_is_durable_before_return(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = runner.Journal(Path(temp) / "journal.jsonl")
            transport = httpx.MockTransport(lambda req: httpx.Response(200, content=sse(response()), headers={"x-request-id": "req_fixture"}))
            with httpx.Client(transport=transport) as client:
                event = runner.execute(client, MANIFEST, "fixture", {"model": "gpt-6-astra"}, "client_fixture", journal, "fake-key")
            self.assertEqual(event["event"], "response")
            self.assertEqual(list(journal.read()), [event])
            journal.archive()
            self.assertFalse(journal.path.exists())
            self.assertEqual(list(journal.read()), [event])

    def test_stream_without_terminal_preserves_partial_text(self):
        content = ('data: {"type":"response.created","response":{"id":"resp_fixture"}}\n\n'
                   'data: {"type":"response.output_text.delta","delta":"<answer>"}\n\n')
        with tempfile.TemporaryDirectory() as temp:
            journal = runner.Journal(Path(temp) / "journal.jsonl")
            with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, text=content))) as client:
                event = runner.execute(client, MANIFEST, "fixture", {}, "client_fixture", journal, "fake-key")
            self.assertEqual(event["event"], "error")
            self.assertEqual(event["status"], "transport_error")
            self.assertEqual(event["partial_output"], "<answer>")
            self.assertEqual(event["response_id"], "resp_fixture")

    def test_http_error_is_saved_without_retry(self):
        calls = []
        def failed(request):
            calls.append(request)
            return httpx.Response(429, json={"error": {"code": "rate_limit_exceeded"}})
        with tempfile.TemporaryDirectory() as temp:
            journal = runner.Journal(Path(temp) / "journal.jsonl")
            with httpx.Client(transport=httpx.MockTransport(failed)) as client:
                event = runner.execute(client, MANIFEST, "fixture", {}, "client_fixture", journal, "fake-key")
            self.assertEqual(len(calls), 1)
            self.assertEqual(event["status"], "api_error")
            self.assertEqual(list(journal.read()), [event])

    def test_truncated_or_duplicate_started_records_block_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "journal.jsonl"
            path.write_text('{"event":')
            with self.assertRaisesRegex(RuntimeError, "Truncated"):
                list(runner.Journal(path).read())
            path.unlink()
            journal = runner.Journal(path)
            marker = {"event": "started", "task_id": "fixture", "attempt_number": 1,
                      "request": {**MANIFEST["request_defaults"], "input": "Fixture prompt"}}
            journal.append(marker)
            args = ({"tinanta": journal}, {"tinanta": {"fixture": {}}}, MANIFEST, {("tinanta", "fixture"): "Fixture prompt"})
            _, _, unresolved = runner.recover(*args)
            self.assertEqual(unresolved, [("tinanta", "fixture")])
            journal.append(marker)
            with self.assertRaisesRegex(RuntimeError, "Duplicate"):
                runner.recover(*args)


class RunnerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        for name in ("manifest.json", "result.schema.json"):
            shutil.copy2(runner.RUN / name, self.folder / name)
        # Fixtures always start as a fresh scaffold, including after the real run starts.
        manifest = deepcopy(MANIFEST)
        manifest.update(status="scaffolded", started_at=None, finished_at=None, submitted_requests=0)
        manifest["execution"].update(runner=None, state="not_started")
        manifest["execution"].pop("retry_batches", None)
        (self.folder / "manifest.json").write_text(json.dumps(manifest))
        self.calls = []
        client_type = httpx.Client
        def local(request):
            body = json.loads(request.content)
            self.calls.append(body)
            self.assertNotIn("max_output_tokens", body)
            self.assertEqual(body["reasoning"], {"effort": "xhigh"})
            return httpx.Response(200, content=sse(response()), headers={"x-request-id": f"req_{len(self.calls)}"})
        def client(**kwargs):
            return client_type(transport=httpx.MockTransport(local))
        self.patch_client = patch.object(runner.httpx, "Client", side_effect=client)
        self.patch_env = patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"})
        self.patch_client.start()
        self.patch_env.start()

    def tearDown(self):
        self.patch_client.stop()
        self.patch_env.stop()
        self.temp.cleanup()

    def test_resume_adds_new_tasks_and_never_resends_previous_requests(self):
        first = runner.run(self.folder, 2, 3000, max_new=4)
        second = runner.run(self.folder, 2, 3000, max_new=4)
        self.assertEqual((first["settled"], second["settled"], len(self.calls)), (4, 8, 8))
        for family in runner.FAMILIES:
            rows = json.loads((self.folder / f"{family}.json").read_bytes())
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({r["task_id"] for r in rows}), 2)
        self.assertEqual(runner.inspect(self.folder, verify=True)["settled"], 8)

    def test_budget_reserves_full_provider_output_limit_before_sending(self):
        result = runner.run(self.folder, 2, 0.01, max_new=4)
        self.assertEqual(len(self.calls), 0)
        self.assertEqual(result["settled"], 0)
        manifest = json.loads((self.folder / "manifest.json").read_bytes())
        self.assertIn("Budget guard", manifest["execution"]["stopped_reason"])

    def test_live_control_changes_admission_without_resending(self):
        control = self.folder / "run-control.json"
        control.write_text('{"concurrency": 1}')
        original_execute = runner.execute
        updated = False
        def execute_and_raise_limit(*args):
            nonlocal updated
            event = original_execute(*args)
            if not updated:
                updated = True
                runner.atomic_write(control, '{"concurrency": 4}\n')
            return event
        with patch.object(runner, "execute", side_effect=execute_and_raise_limit):
            result = runner.run(self.folder, 2, 3000, max_new=8)
        self.assertEqual(result["settled"], 8)
        self.assertEqual(len(self.calls), 8)
        manifest = json.loads((self.folder / "manifest.json").read_bytes())
        self.assertEqual(manifest["execution"]["concurrency"], 4)
        self.assertEqual(runner.inspect(self.folder, verify=True)["settled"], 8)

    def test_invalid_control_blocks_requests(self):
        for value in (0, -1, 513, True, "256"):
            with self.subTest(value=value):
                (self.folder / "run-control.json").write_text(json.dumps({"concurrency": value}))
                with self.assertRaises(ValueError):
                    runner.run(self.folder, 2, 3000, max_new=4)
        self.assertEqual(self.calls, [])

    def test_overload_is_retained_and_unknown_cost_stays_reserved_on_resume(self):
        original_execute = runner.execute
        first = True
        def overload_once(client, manifest, task_id, body, client_id, journal, key):
            nonlocal first
            if not first:
                return original_execute(client, manifest, task_id, body, client_id, journal, key)
            first = False
            self.calls.append(body)
            payload = response()
            payload.update(status="failed", usage=None, output=[],
                           error={"code": "server_is_overloaded", "message": "Fixture overload"})
            event = terminal_event(payload)
            event["task_id"] = task_id
            journal.append(event)
            return event
        with patch.object(runner, "execute", side_effect=overload_once), patch.object(runner, "TRANSIENT_BACKOFF_SECONDS", 0):
            first_run = runner.run(self.folder, 1, 3000, max_new=4)
            second_run = runner.run(self.folder, 1, 3000, max_new=4)
        self.assertEqual((first_run["settled"], second_run["settled"], len(self.calls)), (4, 8, 8))
        self.assertEqual(second_run["unknown_cost_attempts"], 1)
        manifest = json.loads((self.folder / "manifest.json").read_bytes())
        reserve = manifest["execution"]["reservation_usd_per_inflight_request"]
        self.assertAlmostEqual(second_run["unknown_cost_reserve_usd"], reserve)
        failure = json.loads((self.folder / "tinanta.json").read_bytes())[0]
        self.assertEqual(failure["status"], "api_error")
        self.assertIsNone(failure["correct"])
        self.assertIsNone(failure["cost_usd"])
        self.assertEqual(runner.inspect(self.folder, verify=True)["settled"], 8)
        calls_before = len(self.calls)
        blocked = runner.run(self.folder, 1, reserve + 0.5, max_new=4)
        self.assertEqual(blocked["settled"], 8)
        self.assertEqual(len(self.calls), calls_before)

    def test_interrupted_stream_is_preserved_and_never_resent_on_resume(self):
        original_execute = runner.execute
        interrupted = []
        def interrupt_twice(client, manifest, task_id, body, client_id, journal, key):
            if len(interrupted) == 2:
                return original_execute(client, manifest, task_id, body, client_id, journal, key)
            self.calls.append(body)
            error = ({"type": "RemoteProtocolError", "message": "incomplete chunked read"}
                     if interrupted else {"message": "Stream ended without a terminal response; cost unknown"})
            event = {"event": "error", "task_id": task_id, "attempt_number": 1,
                     "status": "transport_error", "response_id": "resp_interrupted",
                     "partial_output": "<answer>", "error": error}
            interrupted.append(task_id)
            journal.append(event)
            return event
        with patch.object(runner, "execute", side_effect=interrupt_twice), patch.object(runner, "TRANSIENT_BACKOFF_SECONDS", 0):
            first_run = runner.run(self.folder, 1, 3000, max_new=4)
            second_run = runner.run(self.folder, 1, 3000, max_new=4)
        self.assertEqual((first_run["settled"], second_run["settled"], len(self.calls)), (4, 8, 8))
        manifest = json.loads((self.folder / "manifest.json").read_bytes())
        reserve = manifest["execution"]["reservation_usd_per_inflight_request"]
        self.assertEqual(second_run["unknown_cost_attempts"], 2)
        self.assertAlmostEqual(second_run["unknown_cost_reserve_usd"], 2 * reserve)
        rows = [row for f in runner.FAMILIES for row in json.loads((self.folder / f"{f}.json").read_bytes())]
        failures = [row for row in rows if row["task_id"] in interrupted]
        self.assertEqual(len(failures), 2)
        for row in failures:
            self.assertEqual(row["status"], "transport_error")
            self.assertEqual(row["output_text"], "<answer>")
            self.assertIsNone(row["correct"])
            self.assertIsNone(row["cost_usd"])
        self.assertEqual(runner.inspect(self.folder, verify=True)["settled"], 8)
        self.assertEqual(runner.run(self.folder, 1, 2 * reserve + 0.5, max_new=4)["settled"], 8)
        self.assertEqual(len(self.calls), 8)

    def test_unrecognized_failures_are_not_treated_as_transient(self):
        for status, error in [
            ("completed", {"unknown_cost_reason": "Provider usage unavailable"}),
            ("transport_error", {"type": "ValueError", "message": "broken parser"}),
            ("transport_error", {"stream_error": {"code": "unexpected"}}),
            ("api_error", {"provider_error": {"code": "invalid_api_key"}}),
        ]:
            with self.subTest(status=status, error=error):
                self.assertFalse(runner.transient_request_failure({
                    "status": status, "response_id": "resp_fixture", "error": error}))

    def test_repeated_interruptions_stop_admission_and_report_draining(self):
        checkpoints = []
        original_write = runner.atomic_write
        def capture_write(path, text):
            original_write(path, text)
            if path.name == "manifest.json":
                checkpoints.append(json.loads(text))
        def interrupted(client, manifest, task_id, body, client_id, journal, key):
            self.calls.append(body)
            event = {"event": "error", "task_id": task_id, "attempt_number": 1,
                     "status": "transport_error", "response_id": "resp_interrupted",
                     "error": {"type": "RemoteProtocolError", "message": "incomplete chunked read"}}
            journal.append(event)
            return event
        with patch.object(runner, "execute", side_effect=interrupted), patch.object(runner, "TRANSIENT_BACKOFF_SECONDS", 0), patch.object(runner, "atomic_write", side_effect=capture_write):
            result = runner.run(self.folder, 1, 3000, max_new=8)
        self.assertEqual((result["settled"], len(self.calls)), (5, 5))
        self.assertEqual(result["unknown_cost_attempts"], 5)
        self.assertTrue(any(m["status"] == "running"
                            and m["execution"].get("submission_state") == "draining"
                            and "Five transient" in (m["execution"].get("stopped_reason") or "")
                            for m in checkpoints))
        self.assertEqual(checkpoints[-1]["status"], "paused")
        self.assertEqual(runner.inspect(self.folder, verify=True)["settled"], 5)


if __name__ == "__main__":
    unittest.main()
