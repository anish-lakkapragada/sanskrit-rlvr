"""Explain the frozen 50-task pilot failures without changing its strict scores.

Mechanical comparisons diagnose representation/granularity differences. They are
not a replacement grader or a certificate that a reordered derivation is valid.
This script makes no model/API calls.
"""

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmarks.correction import core
from vidyut.lipi import Scheme, transliterate

DIRECTORY = core.DIRECTORY / "opus-50-20261009"


def sequence(answer, joined=False, markers=False):
    result = []
    for checkpoint in answer["corrected_steps"]:
        terms = [transliterate(term, Scheme.Devanagari, Scheme.Slp1) for term in checkpoint["terms"]]
        if markers:
            # Diagnostic only: intentionally ignores meaningful technical notation.
            terms = ["<LAKARA>" if term in {"la", "l"} else term.replace("~", "") for term in terms]
        result.append("".join(terms) if joined else tuple(terms))
    return result


def subsequence(actual, gold):
    if not actual or actual[0] != gold[0] or actual[-1] != gold[-1]:
        return False
    remaining = iter(gold)
    return all(any(candidate == checkpoint for candidate in remaining) for checkpoint in actual)


MANUAL = {
    12: ("operation_order", "Auxiliary reduplication is performed before the main stem's i→e→ay changes; both paths rejoin."),
    37: ("operation_order", "Opus has go→gu→ju; VP has go→jo→ju. The differing checkpoint reflects the order of vowel and consonant changes."),
    61: ("operation_order", "The ending vas→va occurs before adding/processing the aat augment; the paths rejoin."),
    92: ("operation_order", "Reduplicant changes hu→jhu→ju precede stem hu→ho→hav in the response; VP interleaves them differently."),
    151: ("operation_order", "Nasal assimilation and s→sh occur before final s→ru→r→visarga; VP records these operations in another order."),
    156: ("operation_order", "Vowel lengthening precedes final-ending processing, and one intermediate r checkpoint is omitted."),
    18: ("mixed_requires_review", "Missing marker in cli; augment insertion, causative removal, and reduplication occur in another order, with a different initial reduplicant boundary."),
    85: ("mixed_requires_review", "The sut augment is represented as a separate term rather than fused with the ending; some marker-removal and sibilant steps are compressed."),
    126: ("mixed_requires_review", "The response substitutes vocalic ऌ for the sequence लृ: ऌँट् (SLP1 x~w) instead of लृँट् (lf~w). It also reorders sibilant/ending operations and omits an r state."),
    161: ("mixed_requires_review", "Omits mip→mi, changes reduplication/deaspiration order, and represents the tuk augment separately. Needs grammatical review beyond string matching."),
    199: ("mixed_requires_review", "Reduplicant krsh→karsh→ka→ca differs from VP krsh→kr→cr→ca. Alternate rule order/analysis needs independent grammatical adjudication."),
}


def audit():
    analysis = json.loads((DIRECTORY / "analysis.json").read_text())
    tasks = {task["id"]: task for task in json.loads((DIRECTORY / "tasks.json").read_text())}
    rows = []
    for result in analysis["results"]:
        if result["strict_pass"]:
            continue
        task = tasks[result["id"]]
        paths = core.derive_for(task["dhatu"]["code"], task["morphology"])
        regenerated = core.accepted_repairs(task["proposed_steps"], task["generation"]["first_incorrect_step"] - 1, paths)
        assert regenerated == task["accepted_answers"], "Frozen gold does not regenerate"
        actual = result["parsed_output"]
        matches = {}
        for name, joined, markers, partial in [
            ("term_boundaries_only", True, False, False),
            ("omitted_checkpoints_only", False, False, True),
            ("technical_notation_only", False, True, False),
            ("notation_and_boundaries", True, True, False),
            ("notation_and_omissions", False, True, True),
        ]:
            observed = sequence(actual, joined, markers)
            for index, gold in enumerate(task["accepted_answers"]):
                expected = sequence(gold, joined, markers)
                matched = subsequence(observed, expected) if partial else observed == expected
                if matched:
                    matches[name] = index
                    break
        if matches:
            category = next(iter(matches))
            note = "Mechanically established structural difference; not an assertion that the original format requirements were satisfied."
        else:
            category, note = MANUAL[task["number"]]
        rows.append({
            "task_number": task["number"], "task_id": task["id"],
            "category": category, "note": note, "mechanical_matches": matches,
            "gold_regenerated": True, "first_error_correct": result["first_error_correct"],
            "final_word_correct": result["final_word_correct"],
            "strict_pass_unchanged": False, "original_differences": result["differences"],
        })
    counts = dict(Counter(row["category"] for row in rows))
    assert len(rows) == 26
    assert sum(bool(row["mechanical_matches"]) for row in rows) == 15
    audit = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_sha256": core.file_sha(DIRECTORY / "analysis.json"),
        "tasks_sha256": core.file_sha(DIRECTORY / "tasks.json"),
        "failed_tasks_reviewed": len(rows), "all_failed_task_gold_sets_regenerated": True,
        "original_strict_score": {"correct": 24, "total": 50, "accuracy": 0.48},
        "category_counts": counts,
        "representation_notation_or_omissions_only": 15,
        "ordering_dominated": 6, "mixed_requires_further_grammatical_review": 5,
        "interpretation": "Most failures reflect exact VP trace reproduction. This does not establish that 52% of conjugations or first-error diagnoses were wrong; all 50 were correct on those two diagnostics.",
        "limits": "Structural review, not expert certification of alternative Sanskrit derivations. Omitted mandatory steps, technical markers, and rule order can matter. No adjusted accuracy or replacement gold set is asserted.",
        "branch_scope": "VP enumerates its implemented optional-rule branches; this is not enumeration of every linguistically defensible derivation order or notation.",
        "sources": [
            "https://vidyut.readthedocs.io/en/latest/prakriya.html",
            "https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/core/prakriya_stack.rs",
            "https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/args/tin.rs",
        ],
        "results": rows,
    }
    (DIRECTORY / "failure-audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    return {key: value for key, value in audit.items() if key != "results"}


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
