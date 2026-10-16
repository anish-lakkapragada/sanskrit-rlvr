"""Local answer extraction and scoring for the answer-only benchmark contract."""

import re

VERSION = "answer-membership-v1"
STATUSES = ("completed", "refused", "incomplete", "api_error", "transport_error", "unknown")


def score_output(output_text, accepted_answers, status="completed"):
    """Keep grammatical membership separate from response format and API status.

    Trim whitespace inside the answer block. Do not normalize Unicode, alter
    Sanskrit spelling, remove punctuation, or select among multiple answers.
    """
    if status not in STATUSES:
        raise ValueError(f"Unknown result status: {status}")
    matches = list(re.finditer(r"<answer>([^<>]*)</answer>", output_text, re.S))
    one_block = (len(matches) == 1 and output_text.count("<answer>") == 1
                 and output_text.count("</answer>") == 1)
    answer_raw = matches[0].group(1) if one_block else None
    answer = (answer_raw.strip() or None) if answer_raw is not None else None
    format_ok = bool(answer is not None and one_block and re.fullmatch(
        r"\s*<answer>[^<>]*</answer>\s*", output_text, re.S))
    correct = (answer is not None and answer in accepted_answers) if status == "completed" else None
    return {
        "answer": answer,
        "correct": correct,
        "format_ok": format_ok,
    }
