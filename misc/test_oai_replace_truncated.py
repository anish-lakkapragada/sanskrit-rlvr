"""Offline regression tests for targeted paid reruns and in-place replacement."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from misc import oai_replace_truncated as runner
from misc.test_oai_batch_eval import record, result

base = runner.base
SLUG = "gpt-6-astra-xhigh"


def original(index=0, truncated=True, correct=False):
    row = record(index)
    row["task_id"] = row["task"]["id"] = f"task-id-{index}"
    raw = result(index, text="<answer>बभूविव</answer>" if correct else "<thinking>unfinished",
                 status="incomplete" if truncated else "completed",
                 incomplete_details={"reason": "max_output_tokens"} if truncated else None)
    row = base.apply_result(row, raw, "original-time")
    row["batch_id"] = "batch_original"
    return row


def fixture(out, rows=None):
    rows = rows or [original(0), original(1, truncated=False), original(2, correct=True)]
    paths = base.configuration_paths(out, SLUG)
    base.atomic_json(paths["result"], rows)
    base.atomic_json(paths["meta"], {"max_output_tokens": 2048, "summary": base.summarize(rows)})
    return runner.prepare(out)


def raw_response(body=None, content=None):
    return SimpleNamespace(status_code=200, headers=SimpleNamespace(multi_items=lambda: []),
                           http_response=SimpleNamespace(json=lambda: copy.deepcopy(body), content=content))


def terminal_cfg(state):
    cfg = state["configurations"][SLUG]
    cfg.update(batch_id="batch_new", submit_attempted_at="submitted", results_ready_at="collected",
               status="completed", batch={"id": "batch_new", "status": "completed"})
    return cfg


class ReplacementTests(unittest.TestCase):
    def test_selector_uses_api_truncation_reason_and_original_cap(self):
        self.assertTrue(runner.eligible(original()))
        self.assertTrue(runner.eligible(original(correct=True)))
        for mutate in (
            lambda r: r["request"]["body"].update(max_output_tokens=6000),
            lambda r: r["raw_batch_result"]["response"].update(status_code=500),
            lambda r: runner.body_of(r).update(status="completed", usage={"output_tokens": 2048}),
            lambda r: runner.body_of(r).update(incomplete_details={"reason": "content_filter"}),
        ):
            row = original()
            mutate(row)
            self.assertFalse(runner.eligible(row))

    def test_prepare_frozen_subset_exact_backups_and_only_cap_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            cfg = state["configurations"][SLUG]
            work = out / cfg["work_dir"]
            self.assertEqual(cfg["task_count"], 2)
            self.assertEqual(set(state["configurations"]), {SLUG})
            self.assertEqual((work / "original-results.json").read_bytes(),
                             (out / cfg["result_path"]).read_bytes())
            selected = [r for r in runner.checked_original(out, cfg) if runner.eligible(r)]
            requests = [json.loads(line) for line in (work / "input.jsonl").read_text().splitlines()]
            for row, request in zip(selected, requests):
                expected = copy.deepcopy(row["request"])
                expected["body"]["max_output_tokens"] = 6000
                self.assertEqual(request, expected)
            self.assertEqual(runner.prepare(out), state)

    def test_shuffled_results_merge_preserves_unselected_rows_and_all_raw_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            cfg = terminal_cfg(state)
            originals = runner.checked_original(out, cfg)
            raw0, raw2 = result(0), result(2, text="<answer>wrong</answer>")
            new = runner.build_replacements(originals, cfg, state, [raw2, raw0])
            merged = runner.merge_rows(originals, new, cfg["selected_custom_ids"])
            self.assertEqual(merged[1], originals[1])
            self.assertEqual([r["task_index"] for r in merged], [0, 1, 2])
            self.assertEqual(merged[0]["raw_batch_result"], raw0)
            self.assertTrue(merged[0]["is_correct"])
            self.assertTrue(originals[2]["is_correct"])
            self.assertFalse(merged[2]["is_correct"])  # No best-of-two cherry picking.
            self.assertEqual(merged[0]["attempt_number"], 2)
            self.assertFalse(runner.eligible(merged[0]))
            for bad in ([raw0, raw0], [raw0, result(99)]):
                with self.assertRaises(ValueError):
                    runner.build_replacements(originals, cfg, state, bad)
            changed = copy.deepcopy(new)
            changed[0]["request"]["body"]["input"] = []
            with self.assertRaises(ValueError):
                runner.merge_rows(originals, changed, cfg["selected_custom_ids"])

    def test_failure_missing_and_new_truncation_never_reuse_old_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out, [original(0, correct=True), original(1, correct=True), original(2)])
            cfg = terminal_cfg(state)
            cfg["batch"]["status"] = "expired"
            raws = [result(0, status="incomplete", incomplete_details={"reason": "max_output_tokens"}),
                    {"custom_id": "task-00001", "response": None, "error": {"code": "batch_expired"}}]
            new = runner.build_replacements(runner.checked_original(out, cfg), cfg, state, raws)
            self.assertTrue(new[0]["truncated"])
            self.assertFalse(runner.eligible(new[0]))
            for row in new[1:]:
                self.assertIsNone(row["answer"])
                self.assertIsNone(row["answer_normalized"])
                self.assertIsNone(row["is_correct"])
            self.assertEqual(new[2]["status"], "batch_expired")

    def test_uncertain_submit_is_recorded_before_post_and_never_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            cfg = state["configurations"][SLUG]
            cfg.update(input_file_id="file_test", upload_attempted_at="past")
            client = Mock(api_key="test-secret")
            def fail(**kwargs):
                durable = base.read_json(runner.ledger(out))["configurations"][SLUG]
                self.assertIsNotNone(durable["submit_attempted_at"])
                raise TimeoutError("uncertain outcome test-secret")
            client.batches.with_raw_response.create.side_effect = fail
            runner.submit_one(client, out, state, SLUG)
            runner.submit_one(client, out, base.read_json(runner.ledger(out)), SLUG)
            client.batches.with_raw_response.create.assert_called_once()
            client.files.with_raw_response.create.assert_not_called()
            self.assertNotIn("test-secret", runner.ledger(out).read_text())

    def test_attempted_upload_is_never_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            state["configurations"][SLUG]["upload_attempted_at"] = "past"
            client = Mock(api_key="secret")
            runner.submit_one(client, out, state, SLUG)
            client.files.with_raw_response.create.assert_not_called()
            client.batches.with_raw_response.create.assert_not_called()

    def test_collection_merges_once_and_accounts_for_both_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            cfg = state["configurations"][SLUG]
            cfg.update(batch_id="batch_new", submit_attempted_at="submitted")
            client = Mock(api_key="secret")
            batch = {"id": "batch_new", "status": "completed", "output_file_id": "file_output"}
            client.batches.with_raw_response.retrieve.return_value = raw_response(batch)
            payload = "".join(json.dumps(result(i)) + "\n" for i in (2, 0)).encode()
            client.files.with_raw_response.content.return_value = raw_response(content=payload)
            runner.collect(client, out, state)
            self.assertIsNotNone(cfg["collected_at"])
            merged = base.read_json(out / cfg["result_path"])
            originals = runner.checked_original(out, cfg)
            self.assertEqual(merged[1], originals[1])
            meta = base.read_json(out / cfg["meta_path"])
            self.assertEqual(meta["usage_totals"]["output_tokens"], 3 * 900)
            self.assertEqual(meta["usage_totals_all_attempts"]["output_tokens"], 5 * 900)
            self.assertEqual(meta["retained_request_cap_counts"], {"6000": 2, "2048": 1})
            self.assertEqual(meta["summary"]["correct"], 2)
            self.assertGreater(meta["estimated_cost_usd_all_attempts"], meta["cap_extension"]["estimated_additional_cost_usd"])
            runner.collect(client, out, base.read_json(runner.ledger(out)))
            client.batches.with_raw_response.retrieve.assert_called_once()
            client.files.with_raw_response.content.assert_called_once()
            client.batches.with_raw_response.create.assert_not_called()

    def test_interrupted_commit_recovers_but_external_edits_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            cfg = terminal_cfg(state)
            new = runner.build_replacements(runner.checked_original(out, cfg), cfg, state, [result(0), result(2)])
            path = out / cfg["work_dir"] / "replacements.json"
            base.atomic_json(path, new)
            cfg["replacements_sha256"] = base.sha256(path)
            client = Mock(api_key="secret")
            with patch.object(runner, "update_meta", side_effect=OSError("simulated failed metadata write")):
                runner.collect(client, out, state)
            self.assertIsNone(cfg["collected_at"])
            self.assertIsNone(base.read_json(runner.ledger(out))["configurations"][SLUG]["collected_at"])
            runner.collect(client, out, state)
            self.assertIsNotNone(cfg["collected_at"])
            client.batches.with_raw_response.retrieve.assert_not_called()
            destination = out / cfg["result_path"]
            destination.write_text("[]\n")
            with self.assertRaisesRegex(ValueError, "changed externally"):
                runner.commit_replacements(out, state, SLUG)
            self.assertEqual(destination.read_text(), "[]\n")

    def test_user_cancellation_archives_partial_results_without_replacing_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            state = fixture(out)
            cfg = state["configurations"][SLUG]
            cfg.update(batch_id="batch_new", submit_attempted_at="submitted",
                       replacement_disabled_at="cancelled-by-user")
            before = (out / cfg["result_path"]).read_bytes()
            client = Mock(api_key="secret")
            batch = {"id": "batch_new", "status": "cancelled", "output_file_id": "file_partial"}
            client.batches.with_raw_response.retrieve.return_value = raw_response(batch)
            client.files.with_raw_response.content.return_value = raw_response(
                content=(json.dumps(result(0)) + "\n").encode())
            runner.collect(client, out, state)
            self.assertEqual((out / cfg["result_path"]).read_bytes(), before)
            self.assertIsNotNone(cfg["collected_at"])
            self.assertFalse(cfg["replacement_applied"])
            self.assertEqual(cfg["archived_result_count"], 1)
            self.assertEqual(base.read_json(out / cfg["work_dir"] / "cancelled-results.json"), [result(0)])
            self.assertFalse(base.read_json(out / cfg["meta_path"])["cap_extension"]["replacement_applied"])
            with self.assertRaisesRegex(ValueError, "disabled replacement"):
                runner.commit_replacements(out, state, SLUG)
            runner.collect(client, out, base.read_json(runner.ledger(out)))
            client.batches.with_raw_response.retrieve.assert_called_once()
            client.batches.with_raw_response.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
