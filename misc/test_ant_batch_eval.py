"""Offline checks for Anthropic scoring, raw capture, and paid-request safety."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import anthropic
import httpx

from misc import ant_batch_eval as runner
from misc.test_oai_batch_eval import TASK

base = runner.base
SLUG = "claude-opus-5-5-xhigh"


def record(index=0):
    task = copy.deepcopy(TASK)
    task["id"] = f"task-{index}"
    request = runner.batch_request(task, index, "claude-opus-5-5", "xhigh")
    return runner.new_record(task, index, request, "test-run", SLUG)


def result(index=0, text="<thinking>Visible derivation</thinking><answer>बभूविव</answer>", **fields):
    return {"custom_id": f"task-{index:05d}", "future_envelope": 42, "result": {
        "type": "succeeded", "message": {"id": "msg_test", "type": "message", "role": "assistant",
            "model": "claude-opus-5-5", "future_message": {"preserve": True},
            "content": [{"type": "thinking", "thinking": "<answer>WRONG</answer>", "signature": "opaque"},
                        {"type": "redacted_thinking", "data": "encrypted"}, {"type": "text", "text": text}],
            "stop_reason": "end_turn", "usage": {"input_tokens": 100, "output_tokens": 50}, **fields}}}


def fixture(out):
    dataset = out / "tasks.json"
    base.atomic_json(dataset, [record(i)["task"] for i in range(2)])
    return runner.prepare(out, [("claude-opus-5-5", "xhigh")], dataset, expected_count=2)


class AnthropicBatchTests(unittest.TestCase):
    def test_prompt_and_thinking_configuration_for_every_supported_effort(self):
        for model in runner.MODELS:
            for effort in runner.EFFORTS:
                p = runner.request_params(TASK, model, effort)
                self.assertEqual(p["messages"], [{"role": "user", "content": base.render_vp_task(TASK, "v2/vp_task_eval.txt")}])
                self.assertNotIn("<thinking>", p["messages"][0]["content"])
                self.assertNotIn(TASK["gold_devanagari"][0], p["messages"][0]["content"])
                self.assertEqual(p["tools"], [])
                self.assertEqual(p["tool_choice"], {"type": "none"})
                self.assertEqual(p["max_tokens"], 128000)
                self.assertEqual(p["thinking"], {"type": "adaptive", "display": "summarized"})
                self.assertEqual(p["output_config"], {"effort": effort})
                self.assertNotIn("temperature", p)
                self.assertNotIn("system", p)

    def test_raw_fields_preserved_and_thinking_excluded_from_scoring(self):
        raw = result()
        row = runner.apply_result(record(), raw, "now")
        self.assertEqual(row["raw_batch_result"], raw)
        self.assertTrue(row["is_correct"])
        self.assertEqual(row["thinking_text"], "<answer>WRONG</answer>")
        row = runner.apply_result(record(), result(text="No final answer"), "now")
        self.assertIsNone(row["answer"])
        self.assertFalse(row["is_correct"])

    def test_same_answer_normalization_and_strict_single_answer(self):
        row = record()
        row["task"]["gold_devanagari"] = ["क़"]
        self.assertTrue(runner.apply_result(row, result(text="<answer> क़ </answer>"), "now")["is_correct"])
        for text in ("बभूविव", "<answer></answer>", "<answer>बभूविव</answer><answer>बभूविव</answer>"):
            self.assertFalse(runner.apply_result(record(), result(text=text), "now")["is_correct"])

    def test_truncations_keep_complete_answers_and_refusals_are_recorded(self):
        for reason in ("max_tokens", "model_context_window_exceeded"):
            row = runner.apply_result(record(), result(stop_reason=reason), "now")
            self.assertTrue(row["is_correct"])
            self.assertTrue(row["truncated"])
            self.assertEqual(row["status"], "incomplete")
        row = runner.apply_result(record(), result(text="Cannot comply", stop_reason="refusal"), "now")
        self.assertEqual(row["status"], "refused")
        self.assertEqual(row["refusals"], ["Cannot comply"])

    def test_failures_and_missing_results_do_not_retain_old_answers(self):
        old = runner.apply_result(record(), result(), "earlier")
        for kind in ("errored", "expired", "canceled"):
            raw = {"custom_id": "task-00000", "result": {"type": kind}}
            row = runner.apply_result(old, raw, "now")
            self.assertIsNone(row["answer"])
            self.assertIsNone(row["is_correct"])
            self.assertEqual(row["raw_batch_result"], raw)
        row = runner.assemble([old], [], {"id": "batch", "processing_status": "ended"}, "now")[0]
        self.assertIsNone(row["answer"])
        self.assertIsNone(row["is_correct"])

    def test_shuffled_results_mapping_and_duplicate_rejection(self):
        batch = {"id": "batch", "processing_status": "ended"}
        rows = runner.assemble([record(0), record(1)], [result(1), result(0)], batch, "now")
        self.assertEqual([r["task_index"] for r in rows], [0, 1])
        self.assertTrue(all(r["is_correct"] for r in rows))
        for raws in ([result(0), result(0)], [result(2)]):
            with self.assertRaises(ValueError):
                runner.assemble([record(0), record(1)], raws, batch, "now")

    def test_uncertain_submission_is_durable_and_never_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            attempts = []
            def handler(request):
                attempts.append(request)
                self.assertIsNotNone(base.read_json(base.state_path(out))["configurations"][SLUG]["submit_attempted_at"])
                raise httpx.ConnectTimeout("uncertain outcome", request=request)
            client = anthropic.Anthropic(api_key="test-key", max_retries=0,
                                         http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            runner.submit_config(client, out, state, SLUG)
            runner.submit_config(client, out, base.read_json(base.state_path(out)), SLUG)
            self.assertEqual(len(attempts), 1)
            self.assertIsNone(base.read_json(out / state["configurations"][SLUG]["result_path"])[0]["answer"])
            client.close()

    def test_http_round_trip_collection_and_recovery_never_resubmits(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            calls = []
            batch = {"id": "msgbatch_test", "processing_status": "ended", "future_field": "preserved",
                     "results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_test/results",
                     "request_counts": {"processing": 0, "succeeded": 2, "errored": 0, "expired": 0, "canceled": 0}}
            raws = [result(1), result(0)]
            def handler(request):
                calls.append((request.method, request.url.path))
                if request.method == "POST":
                    payload = json.loads(request.content)
                    self.assertEqual(len(payload["requests"]), 2)
                    self.assertEqual(payload["requests"][0], record()["request"])
                    return httpx.Response(200, json=batch)
                if request.url.path.endswith("/results"):
                    return httpx.Response(200, content="\n".join(json.dumps(r) for r in raws).encode(),
                                          headers={"x-request-id": "download-test"})
                return httpx.Response(200, json=batch)
            client = anthropic.Anthropic(api_key="test-key", max_retries=0,
                                         http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            runner.submit_config(client, out, state, SLUG)
            runner.submit_config(client, out, state, SLUG)
            # Simulate a crash after the response receipt, before the creation state was committed.
            state["configurations"][SLUG]["batch_id"] = None
            with patch.object(runner, "write_meta", side_effect=[None, OSError("metadata interrupted")]):
                runner.collect(client, out, state)
            self.assertIsNone(state["configurations"][SLUG]["collected_at"])
            runner.collect(client, out, state)
            runner.collect(client, out, state)
            rows = base.read_json(out / state["configurations"][SLUG]["result_path"])
            self.assertEqual([r["raw_batch_result"] for r in rows], list(reversed(raws)))
            meta = base.read_json(out / state["configurations"][SLUG]["meta_path"])
            self.assertEqual(meta["summary"]["correct"], 2)
            self.assertTrue(meta["summary"]["final"])
            self.assertAlmostEqual(meta["estimated_cost_usd"], .0014)
            self.assertEqual(sum(method == "POST" for method, path in calls), 1)
            self.assertEqual(sum(path.endswith("/results") for method, path in calls), 1)
            self.assertTrue((out / state["configurations"][SLUG]["work_dir"] / "results.http.json").exists())
            client.close()

    def test_changed_input_and_conflicting_configurations_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            with self.assertRaises(ValueError):
                runner.prepare(out, [("claude-opus-5-5", "high")])
            with patch.object(runner, "TEMPLATE", "v1/vp_task_eval.txt"):
                with self.assertRaises(ValueError):
                    runner.prepare(out, [("claude-opus-5-5", "xhigh")])
            path = out / state["configurations"][SLUG]["input_path"]
            path.write_text(path.read_text() + " ")
            with self.assertRaises(ValueError):
                runner.submit_config(None, out, state, SLUG)
            self.assertIsNone(state["configurations"][SLUG]["submit_attempted_at"])


if __name__ == "__main__":
    unittest.main()
