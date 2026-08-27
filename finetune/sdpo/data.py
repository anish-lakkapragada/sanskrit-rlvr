"""SDPO data: task records with privileged blocks, and prompt-pair rendering.

CPU-only (no torch); the tokenizer is passed in by the caller.
"""

import json
from pathlib import Path

from finetune.config import ROOT
from finetune.prompts import render_vp_task

ANSWER_OPEN = "<answer>"
THINKING_OPEN = "<thinking>"
# Appended after the privileged block in the TEACHER prompt so the teacher's
# conditional format-prior matches the student's (without it, a teacher that
# already sees the answer puts ~zero mass on opening a <thinking> block, and
# the KL on that one structural token steadily teaches the student to skip
# thinking — observed as full format collapse by step 100).
TEACHER_GUIDANCE = ("\nUse this reference to guide a step-by-step derivation in "
                    "<thinking></thinking> tags as usual, then give the final "
                    "form in <answer></answer> tags.")


def load_sdpo_tasks(path: str | Path) -> list[dict]:
    tasks = json.loads((ROOT / path).read_text())
    missing = [t.get("id", "?") for t in tasks if "privileged_block" not in t]
    if missing:
        raise ValueError(
            f"{path}: {len(missing)} records lack 'privileged_block' "
            f"(first: {missing[:3]}) — build with misc/data/make_sdpo_data.py")
    return tasks


def chat_wrap(tokenizer, user_content: str) -> str:
    """Chat-template a single user turn, generation prompt appended —
    byte-identical to the GRPO/SFT rendering (enable_thinking=False)."""
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": user_content}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)


def render_pair(task: dict, template: str, tokenizer) -> dict:
    """Student prompt x and teacher prompt x+ for one task.

    The privileged block is appended to the USER message of the teacher
    prompt only; the student prompt is exactly the training/eval prompt."""
    user = render_vp_task(task, template=template)
    return {
        "student_text": chat_wrap(tokenizer, user),
        "teacher_text": chat_wrap(
            tokenizer, user + "\n\n" + task["privileged_block"] + TEACHER_GUIDANCE),
        "user_text": user,
    }


def completion_token_weights(tokenizer, completion: str,
                             thinking_w: float, answer_w: float):
    """(ids, weights) for a completion string.

    Re-tokenizes the completion text (a valid teacher-forcing sequence even if
    vLLM's sampled ids segmented differently) and assigns per-token weights by
    character span: tokens starting at or after the first ``<answer>`` get
    ``answer_w``, everything before gets ``thinking_w``."""
    enc = tokenizer(completion, add_special_tokens=False,
                    return_offsets_mapping=True)
    ids = enc["input_ids"]
    cut = completion.find(ANSWER_OPEN)
    if cut < 0:
        cut = len(completion)  # no answer tag: all thinking-weighted
    # Zero-weight the opening format region (through the <thinking> tag): the
    # teacher's format-prior must never gradient the student's response shape.
    topen = completion.find(THINKING_OPEN)
    zero_until = (topen + len(THINKING_OPEN)) if topen >= 0 else 0
    weights = [0.0 if start < zero_until
               else (answer_w if start >= cut else thinking_w)
               for start, _ in enc["offset_mapping"]]
    return ids, weights
