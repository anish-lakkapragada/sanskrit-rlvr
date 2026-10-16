"""Offline checks for safety metadata and streamed billing; no API calls."""

import unittest

from data.engine.reports.flagging_pilot import Stream, classify, cost, request_body, visible_text


class FlaggingTests(unittest.TestCase):
    def test_anthropic_free_pre_output_refusal_but_generated_reasoning_is_billed(self):
        response = {"stop_reason": "refusal", "stop_details": {"category": "cyber"}}
        self.assertEqual(cost("opus", {"input_tokens": 435, "output_tokens": 0}, response), 0)
        self.assertAlmostEqual(cost("opus", {"input_tokens": 415, "output_tokens": 81}, response), .00328)
        response["stop_details"]["category"] = "reasoning_extraction"
        self.assertAlmostEqual(cost("opus", {"input_tokens": 435, "output_tokens": 0}, response), .00174)

    def test_answer_only_format_keeps_scoring_and_rejects_extra_explanation(self):
        result = {"status": "completed", "response_format": "answer_only"}
        good = classify("astra", {}, result, "<answer>रामः</answer>\n", ["रामः"])
        self.assertTrue(good["format_ok"] and good["answer_correct"])
        extra = classify("astra", {}, result, "An explanation. <answer>रामः</answer>", ["रामः"])
        self.assertFalse(extra["format_ok"])
        self.assertTrue(extra["answer_correct"])

    def test_anthropic_stop_details_survive_stream_and_end_turn(self):
        stream = Stream("opus")
        events = [
            {"type": "message_start", "message": {"content": [], "usage": {"input_tokens": 42}}},
            {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_details": {
                "type": "refusal", "category": "cyber"}}, "usage": {"output_tokens": 0}},
            {"type": "message_stop"},
        ]
        for event in events:
            stream.feed(event)
        result = classify("opus", stream.response, {"status": "completed"}, "", ["रामः"])
        self.assertTrue(stream.terminal)
        self.assertTrue(result["structured_safety_flag"])
        self.assertTrue(result["structured_cyber_flag"])
        self.assertEqual(stream.response["usage"], {"input_tokens": 42, "output_tokens": 0})

    def test_reasoning_extraction_is_not_cyber(self):
        response = {"stop_reason": "refusal", "stop_details": {
            "type": "refusal", "category": "reasoning_extraction"}}
        result = classify("opus", response, {"status": "completed"}, "", ["रामः"])
        self.assertTrue(result["structured_safety_flag"])
        self.assertFalse(result["structured_cyber_flag"])
        self.assertIsNone(result["answer"])

    def test_openai_refusal_or_content_filter(self):
        for response in [
            {"output": [{"content": [{"type": "refusal", "refusal": "Declined"}]}]},
            {"incomplete_details": {"reason": "content_filter"}},
        ]:
            result = classify("astra", response, {"status": "completed"}, "", ["रामः"])
            self.assertTrue(result["structured_safety_flag"])

    def test_wrong_answer_and_grammatical_uncertainty_are_not_safety(self):
        output = "<thinking>I cannot derive this with confidence.</thinking><answer>फलम्</answer>"
        result = classify("astra", {}, {"status": "completed"}, output, ["रामः"])
        self.assertFalse(result["structured_safety_flag"])
        self.assertFalse(result["answer_correct"])
        self.assertFalse(result["text_review_candidates"])
        self.assertTrue(result["format_ok"])

    def test_streamed_usage_is_cumulative_and_native_thinking_not_visible_answer(self):
        stream = Stream("opus")
        for event in [
            {"type": "message_start", "message": {"content": [], "usage": {"input_tokens": 42, "output_tokens": 1}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "example"}},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "<answer>रामः</answer>"}},
            {"type": "message_delta", "usage": {"output_tokens": 10}},
            {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 15}},
            {"type": "message_stop"},
        ]:
            stream.feed(event)
        self.assertEqual(stream.response["usage"]["output_tokens"], 15)
        self.assertEqual(visible_text("opus", stream.response), "<answer>रामः</answer>")

    def test_no_extra_output_cap_and_cost_includes_reasoning_once(self):
        self.assertNotIn("max_output_tokens", request_body("astra", "prompt"))
        self.assertEqual(request_body("opus", "prompt")["max_tokens"], 128000)
        self.assertAlmostEqual(cost("astra", {"input_tokens": 1000, "output_tokens": 1000,
            "output_tokens_details": {"reasoning_tokens": 900}}), .06)
        self.assertAlmostEqual(cost("opus", {"input_tokens": 1000, "output_tokens": 1000}), .024)


if __name__ == "__main__":
    unittest.main()
