"""Strict structured gold-set grading; standard library only."""

from __future__ import annotations

import json
import unicodedata


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def canonical_answer(answer):
    if isinstance(answer, str):
        answer = json.loads(answer, object_pairs_hook=unique_object)
    if not isinstance(answer, dict) or set(answer) != {"first_incorrect_step", "corrected_steps", "final_answer"}:
        raise ValueError("Unexpected answer fields")
    first = answer["first_incorrect_step"]
    if type(first) is not int or first < 1:
        raise ValueError("Error position must be a positive integer")
    rows = answer["corrected_steps"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("A complete nonempty continuation is required")
    result = []
    for index, row in enumerate(rows, first):
        if not isinstance(row, dict) or set(row) != {"step", "terms"}:
            raise ValueError("Unexpected checkpoint fields")
        if type(row["step"]) is not int or row["step"] != index:
            raise ValueError("Checkpoint numbers must be consecutive")
        terms = row["terms"]
        if not isinstance(terms, list) or not terms or any(type(term) is not str or not term for term in terms):
            raise ValueError("Checkpoint terms must be nonempty strings")
        result.append((index, tuple(unicodedata.normalize("NFC", term) for term in terms)))
    final = answer["final_answer"]
    if type(final) is not str or not final:
        raise ValueError("A final word is required")
    return first, tuple(result), unicodedata.normalize("NFC", final)


def grade(answer, accepted_answers):
    try:
        key = canonical_answer(answer)
    except (ValueError, TypeError, RecursionError):
        return False
    return key in {canonical_answer(gold) for gold in accepted_answers}
