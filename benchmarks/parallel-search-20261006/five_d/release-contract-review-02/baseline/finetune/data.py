"""Dataset loading: VP task JSON -> HF Dataset for TRL, plus raw task lists."""

import json
from pathlib import Path

from finetune.config import ROOT
from finetune.prompts import render_vp_task


def load_vp_tasks(path: str | Path) -> list[dict]:
    """Raw task dicts (id, dhatu, morphology, gold_slp1, gold_devanagari)."""
    return json.loads((ROOT / path).read_text())


def load_vp_dataset(path: str | Path, template: str = "v0/vp_task.txt",
                    tokenizer=None):
    """HF Dataset for GRPOTrainer.

    Without ``tokenizer``, ``prompt`` uses the conversational format (single
    user message) and TRL applies the model's chat template with ITS defaults
    -- on Qwen3 that turns the native think channel ON. With ``tokenizer``,
    prompts are pre-rendered to plain strings (TRL standard format, passed to
    rollouts verbatim) through the chat template with enable_thinking=False,
    keeping GRPO rollouts byte-identical to SFT training and prevals eval
    rendering. Every other column passes through to reward functions as
    kwargs (remove_unused_columns=False).
    """
    from datasets import Dataset

    tasks = load_vp_tasks(path)

    def prompt(t):
        p = render_vp_task(t, template=template)
        if tokenizer is None:
            return [{"role": "user", "content": p}]
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": p}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False)

    return Dataset.from_dict({
        "prompt": [prompt(t) for t in tasks],
        "id": [t["id"] for t in tasks],
        "dhatu": [t["dhatu"] for t in tasks],
        "morphology": [t["morphology"] for t in tasks],
        "gold_slp1": [t["gold_slp1"] for t in tasks],
        "gold_devanagari": [t["gold_devanagari"] for t in tasks],
    })


def load_sft_dataset(path: str | Path):
    """data/finetune/sft-r1/*.json distillation records -> HF Dataset with the
    TRL prompt/completion conversational columns. Metadata fields (gold,
    reward, dhatu, ...) are dropped here; they exist for provenance and
    re-verification, not training."""
    from datasets import Dataset

    records = json.loads((ROOT / path).read_text())
    return Dataset.from_list(
        [{"prompt": r["prompt"], "completion": r["completion"]} for r in records])


def load_samayik_pairs(path: str | Path) -> list[dict]:
    """data/eval/samayik.json: list of {"en": ..., "sa": ...} dicts."""
    pairs = json.loads((ROOT / path).read_text())
    return [p for p in pairs if p.get("en") and p.get("sa")]
