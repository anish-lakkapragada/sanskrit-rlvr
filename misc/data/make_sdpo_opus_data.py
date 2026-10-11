#!/usr/bin/env python
"""Build the SDPO-on-Opus-traces corpus: task records + rendered privileged blocks.

Counterpart to make_sdpo_data.py with the privileged block sourced from the
rejection-sampled Opus 5 SFT corpus (data/finetune/sft-r1/claude-opus-5.json,
all records reward == 1.0) instead of the vidyut-prakriya derivation. For every
task in the source file that has at least one passing trace, render the block as

    === Reference (for grading) ===
    Correct form: <gold devanagari>
    Reasoning (teacher trace):
    <the trace's <thinking> text, tags stripped>

choosing the trace whose rendered block is SHORTEST in student-tokenizer tokens
(~72% of covered tasks have two samples). The <answer> block is stripped: the
gold form is already stated on the "Correct form:" line and the teacher prompt
must not end mid-answer-format.

USER POLICY (2026-08-24, carried over): tasks whose rendered block exceeds
--budget tokens are EXCLUDED from the corpus entirely (no truncation), and the
exclusion percentage is reported. Tasks with no passing Opus trace are likewise
excluded (75.8% coverage) and reported.

    uv run --with transformers --with tokenizers python misc/data/make_sdpo_opus_data.py

Output records are the original task fields plus:
    privileged_block: str   # the exact text appended to the teacher prompt
    block_tokens: int       # length under the student tokenizer
    trace_sample: int       # which sample slot (0/1) supplied the trace
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

HEADER = "=== Reference (for grading) ==="
THINKING_OPEN, THINKING_CLOSE = "<thinking>", "</thinking>"
ANSWER_OPEN = "<answer>"


def extract_thinking(completion: str) -> str | None:
    """The <thinking> body of a trace; None if the trace has no thinking text."""
    start = completion.find(THINKING_OPEN)
    if start < 0:
        return None
    start += len(THINKING_OPEN)
    end = completion.find(THINKING_CLOSE, start)
    if end < 0:                      # unclosed: cut at the answer block instead
        end = completion.find(ANSWER_OPEN, start)
        if end < 0:
            end = len(completion)
    body = completion[start:end].strip()
    return body or None


def render_block(task: dict, thinking: str) -> str:
    return (f"{HEADER}\n"
            f"Correct form: {task['gold_devanagari'][0]}\n"
            "Reasoning (teacher trace):\n" + thinking)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks", default="data/finetune/task-data/finetune.json")
    ap.add_argument("--traces", default="data/finetune/sft-r1/claude-opus-5.json")
    ap.add_argument("--out", default="data/finetune/task-data/sdpo-opus-finetune.json")
    ap.add_argument("--budget", type=int, default=2048,
                    help="max privileged-block tokens; over-budget tasks are EXCLUDED")
    ap.add_argument("--tokenizer", default="Qwen/Qwen3-4B")
    args = ap.parse_args()

    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    tasks = json.loads((ROOT / args.tasks).read_text())
    traces = json.loads((ROOT / args.traces).read_text())

    by_task: dict = defaultdict(list)
    for r in traces:
        assert r["reward"] == 1.0, f"non-passing trace in corpus: {r['id']}"
        by_task[r["id"]].append(r)

    kept, no_trace, no_thinking, over_budget = [], 0, 0, 0
    token_counts = []
    for t in tasks:
        candidates = by_task.get(t["id"], [])
        if not candidates:
            no_trace += 1
            continue
        blocks = []
        for r in candidates:
            thinking = extract_thinking(r["completion"][0]["content"])
            if thinking is None:
                continue
            block = render_block(t, thinking)
            n = len(tok(block, add_special_tokens=False)["input_ids"])
            blocks.append((n, r["sample"], block))
        if not blocks:
            no_thinking += 1
            continue
        n, sample, block = min(blocks)          # shortest rendered block wins
        if n > args.budget:
            over_budget += 1
            continue
        token_counts.append(n)
        kept.append({**t, "privileged_block": block, "block_tokens": n,
                     "trace_sample": sample})

    (ROOT / args.out).write_text(
        json.dumps(kept, ensure_ascii=False, indent=1))

    token_counts.sort()
    total = len(tasks)
    pct = lambda k: f"{k}/{total} = {100 * k / total:.2f}%"
    print(f"tasks:          {total} ({args.tasks})")
    print(f"traces:         {len(traces)} over {len(by_task)} tasks ({args.traces})")
    print(f"no trace:       {pct(no_trace)} (rejection-sampling coverage gap)")
    print(f"no thinking:    {pct(no_thinking)}")
    print(f"over budget:    {pct(over_budget)} (budget {args.budget} tokens)")
    print(f"KEPT:           {pct(len(kept))} -> {args.out}")
    if token_counts:
        q = lambda p: token_counts[min(int(p * len(token_counts)), len(token_counts) - 1)]
        print(f"block tokens:   mean {sum(token_counts) // len(token_counts)}"
              f"  p50 {q(0.5)}  p90 {q(0.9)}  p99 {q(0.99)}  max {token_counts[-1]}")
    steps = (len(kept) + 7) // 8
    print(f"one epoch at 8 prompts/step: {steps} optimizer steps")


if __name__ == "__main__":
    main()
