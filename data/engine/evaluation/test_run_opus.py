"""Offline tests for Opus streaming, billing, exact scoring and resumable work."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import httpx
from jsonschema import Draft202012Validator

from data.engine.evaluation import run_opus as runner
from data.engine.evaluation import merge_manifests
from data.engine.evaluation.scaffold_astra import schema


def events(text="<answer>भवति</answer>", reason="end_turn", category=None, output_tokens=1000):
    message = {"id": "msg_fixture", "model": "claude-opus-5-5", "type": "message", "role": "assistant",
               "content": [], "stop_reason": None,
               "usage": {"input_tokens": 200, "output_tokens": 1, "service_tier": "standard",
                         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}
    result = [{"type": "message_start", "message": message}, {"type": "ping"}]
    if text:
        result += [{"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
                   {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "opaque-fixture"}},
                   {"type": "content_block_stop", "index": 0},
                   {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
                   {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": text}},
                   {"type": "content_block_stop", "index": 1}]
    result += [{"type": "message_delta", "delta": {}, "usage": {"output_tokens": output_tokens // 2}},
               {"type": "message_delta", "delta": {"stop_reason": reason, "stop_details": {"type": "refusal", "category": category} if reason == "refusal" else None},
                "usage": {"output_tokens": output_tokens, "output_tokens_details": {"thinking_tokens": max(0, output_tokens - 10)}}},
               {"type": "message_stop"}]
    return result


def wire(parts):
    return "".join("data: " + json.dumps(part, ensure_ascii=False) + "\n\n" for part in parts).encode()


class OpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = tempfile.TemporaryDirectory()
        cls.source = Path(cls.seed.name)
        cls.manifest = runner.prepare(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.seed.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "run"
        shutil.copytree(self.source, self.folder)
        self.task = {"id": "fixture", "gold_devanagari": ["भवति"]}

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, parts=None, http_status=200):
        path = self.folder / "journals" / "fixture.jsonl"
        journal = runner.base.Journal(path)
        calls = []
        def serve(request):
            calls.append(request)
            if http_status != 200:
                return httpx.Response(http_status, json={"error": {"type": "rate_limit_error"}}, headers={"retry-after": "1"})
            return httpx.Response(200, content=wire(parts if parts is not None else events()), headers={"request-id": "req_fixture"})
        with httpx.Client(transport=httpx.MockTransport(serve)) as client:
            event = runner.execute(client, self.manifest, "fixture", runner.request_body("Fixture"), "client_fixture", journal, "fixture-key")
        self.assertEqual(list(journal.read())[-1], event)
        self.assertEqual(len(calls), 1)
        return event, runner.result_row(event, self.task, self.manifest)

    def test_stream_assembles_text_signature_and_cumulative_usage(self):
        event, row = self.execute()
        self.assertEqual(row["output_text"], "<answer>भवति</answer>")
        self.assertTrue(row["correct"] and row["format_ok"])
        self.assertEqual(row["usage"]["output_tokens"], 1000)
        self.assertAlmostEqual(row["cost_usd"], .0208)
        self.assertEqual(event["response"]["content"][0]["signature"], "opaque-fixture")
        Draft202012Validator(schema()).validate([row])

    def test_refusal_categories_preserved_and_charged_correctly(self):
        _, row = self.execute(events(text="", reason="refusal", category="cyber", output_tokens=0))
        self.assertEqual(row["status"], "refused")
        self.assertEqual(row["error"]["stop_details"]["category"], "cyber")
        self.assertIsNone(row["correct"])
        self.assertEqual(row["cost_usd"], 0)
        _, bio = self.execute(events(text="", reason="refusal", category="bio", output_tokens=0))
        self.assertAlmostEqual(bio["cost_usd"], .0008)
        _, streamed = self.execute(events(text="Declined", reason="refusal", category="cyber", output_tokens=100))
        self.assertAlmostEqual(streamed["cost_usd"], .0028)

    def test_partial_usage_is_not_misreported_as_final_billing(self):
        event, row = self.execute(events()[:-1])
        self.assertEqual(row["status"], "transport_error")
        self.assertEqual(row["output_text"], "<answer>भवति</answer>")
        self.assertIsNone(row["correct"])
        self.assertIsNone(row["usage"])
        self.assertIsNone(row["cost_usd"])
        self.assertTrue(event["partial_response"]["usage"])
        self.assertTrue(runner.transient_failure(row))

    def test_missing_final_usage_blocks_billing_and_model_mismatch_blocks_scoring(self):
        parts = [p for p in events() if p["type"] != "message_delta"]
        _, row = self.execute(parts)
        self.assertIsNone(row["cost_usd"])
        self.assertFalse(runner.transient_failure(row))
        parts = events()
        parts[0]["message"]["model"] = "claude-sonnet-5-5"
        _, row = self.execute(parts)
        self.assertEqual(row["status"], "api_error")
        self.assertIsNone(row["correct"])
        self.assertIsNone(row["cost_usd"])

    def test_http_and_stream_errors_never_retry(self):
        _, row = self.execute(http_status=429)
        self.assertEqual(row["status"], "api_error")
        self.assertTrue(runner.transient_failure(row))
        event, row = self.execute(events()[:1] + [{"type": "error", "error": {"type": "overloaded_error", "message": "Fixture overload"}}])
        self.assertEqual(row["error"]["provider_error"]["type"], "overloaded_error")
        self.assertTrue(runner.transient_failure(row))
        self.assertIsNone(row["cost_usd"])

    def test_incomplete_and_exact_membership(self):
        _, row = self.execute(events(reason="max_tokens"))
        self.assertEqual(row["status"], "incomplete")
        self.assertIsNone(row["correct"])
        _, row = self.execute(events("<answer>भवति।</answer>"))
        self.assertFalse(row["correct"])
        self.assertTrue(row["format_ok"])

    def test_anthropic_cache_counts_are_additional_and_thinking_not_added_twice(self):
        usage = {"input_tokens": 200, "output_tokens": 1000, "cache_read_input_tokens": 500,
                 "cache_creation_input_tokens": 200, "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 100},
                 "output_tokens_details": {"thinking_tokens": 990}, "service_tier": "standard"}
        payload = {"usage": usage, "stop_reason": "end_turn"}
        cost, error = runner.estimate_cost(payload, self.manifest["pricing"])
        self.assertIsNone(error)
        self.assertAlmostEqual(cost, (200*4 + 500*.2 + 100*5 + 100*8 + 1000*20)/1e6)
        usage["cache_creation_input_tokens"] = 100
        self.assertIsNone(runner.estimate_cost(payload, self.manifest["pricing"])[0])

    def test_real_scaffold_pins_same_tasks_and_prompt_templates(self):
        astra = json.loads((runner.base.RUN / "manifest.json").read_bytes())
        self.assertEqual(self.manifest["tasks"], astra["tasks"])
        self.assertEqual(self.manifest["request_defaults"]["output_config"]["effort"], "xhigh")
        self.assertEqual(self.manifest["request_defaults"]["max_tokens"], 128000)
        self.assertNotIn("tools", runner.request_body("Fixture"))
        self.assertNotIn("system", runner.request_body("Fixture"))

    def test_v3_manifest_controls_rendering_without_changing_v2_defaults(self):
        modules = {f: runner.importlib.import_module(f"data.engine.{f}.common") for f in runner.FAMILIES}
        defaults = {f: module.template_text for f, module in modules.items()}
        # Populate the v2 caches before loading v3, to catch stale-template use.
        original_text = {f: getter() for f, getter in defaults.items()}
        folder = Path(self.temp.name) / "v3"
        manifest = runner.prepare(folder, prompt_version="v3")
        _, tasks, prompts, _ = runner.load_inputs(folder)
        self.assertEqual(len(prompts), 20000)
        self.assertEqual(manifest["prompt_version"], "v3")
        for entry in manifest["tasks"]:
            f = entry["family"]
            self.assertEqual(entry["prompt_template"]["path"], f"data/engine/prompts/v3/vp_{f}.txt")
            self.assertIs(modules[f].template_text, defaults[f])
            self.assertEqual(modules[f].template_text(), original_text[f])
            for task_id in tasks[f]:
                self.assertTrue(prompts[f, task_id].startswith(entry["prompt_template"]["text"].splitlines()[0]))
                self.assertIn("| Grammatical input | Value |", prompts[f, task_id])
                self.assertNotIn("You are an expert", prompts[f, task_id])
        entry = manifest["tasks"][0]
        entry["prompt_template"]["text"] = "Different from the pinned file"
        (folder / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, "Pinned template text differs"):
            runner.load_inputs(folder)

    def test_run_resume_and_full_reservations(self):
        tasks = {f: {f"{f}:{i}": {"id": f"{f}:{i}", "gold_devanagari": ["भवति"]} for i in range(2)} for f in runner.FAMILIES}
        prompts = {(f, task_id): task_id for f in tasks for task_id in tasks[f]}
        calls = []
        client_type = httpx.Client
        def serve(request):
            body = json.loads(request.content)
            self.assertEqual(body, runner.request_body(body["messages"][0]["content"]))
            calls.append(body)
            return httpx.Response(200, content=wire(events()))
        def load(folder):
            return json.loads((folder / "manifest.json").read_bytes()), tasks, prompts, Draft202012Validator(schema())
        with patch.object(runner, "load_inputs", side_effect=load), patch.object(runner.httpx, "Client", side_effect=lambda **kwargs: client_type(transport=httpx.MockTransport(serve))), patch.dict(os.environ, {"ANTHROPIC_API_KEY": "fixture-key"}):
            blocked = runner.run(self.folder, 2, .01, max_new=4)
            self.assertEqual(blocked["settled"], 0)
            self.assertFalse(calls)
            first = runner.run(self.folder, 2, 1500, max_new=4)
            second = runner.run(self.folder, 2, 1500, max_new=4)
            self.assertEqual((first["settled"], second["settled"], len(calls)), (4, 8, 8))
            self.assertEqual(len({r["messages"][0]["content"] for r in calls}), 8)
            self.assertEqual(runner.inspect(self.folder, verify=True)["unresolved"], 0)
            self.assertEqual(runner.run(self.folder, 2, 1500)["settled"], 8)
            self.assertEqual(len(calls), 8)

    def test_unresolved_request_blocks_resend(self):
        manifest, tasks, prompts, _ = runner.load_inputs(self.folder)
        family, task_id = next(iter(prompts))
        journal = runner.base.Journal(self.folder / "journals" / f"{family}.jsonl")
        journal.append({"event": "started", "task_id": task_id, "attempt_number": 1, "request": runner.request_body(prompts[family, task_id])})
        with self.assertRaisesRegex(RuntimeError, "Unresolved started"):
            runner.run(self.folder, 1, 1500)


class ManifestMergeTests(unittest.TestCase):
    def test_lossless_idempotent_merge_keeps_current_results_and_old_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            old = {"run_id": "fixture", "status": "completed", "execution": {"pid": None}, "submitted_requests": 20000}
            current = deepcopy(old)
            current["submitted_requests"] = 20007
            (path / "manifest.json").write_text(json.dumps(current))
            (path / "manifest-before-retries.json").write_text(json.dumps(old))
            merged = merge_manifests.merge(path)
            self.assertEqual(merged["submitted_requests"], 20007)
            self.assertEqual(merged["manifest_history"][0]["manifest"], old)
            self.assertFalse((path / "manifest-before-retries.json").exists())
            self.assertEqual(merge_manifests.merge(path), merged)


if __name__ == "__main__":
    unittest.main()
