"""Dataset loading: VP task JSON -> HF Dataset for TRL, plus raw task lists."""

import json
from pathlib import Path

from finetune.config import ROOT
from finetune.prompts import render_vp_task


def load_vp_tasks(path: str | Path) -> list[dict]:
    """Raw task dicts (id, dhatu, morphology, gold_slp1, gold_devanagari)."""
    return json.loads((ROOT / path).read_text())


def load_vp_dataset(path: str | Path):
    """HF Dataset for GRPOTrainer.

    ``prompt`` uses the conversational format (single user message) so TRL
    applies the model's chat template. Every other column passes through to
    reward functions as kwargs (remove_unused_columns=False).
    """
    from datasets import Dataset

    tasks = load_vp_tasks(path)
    return Dataset.from_dict({
        "prompt": [[{"role": "user", "content": render_vp_task(t)}] for t in tasks],
        "id": [t["id"] for t in tasks],
        "dhatu": [t["dhatu"] for t in tasks],
        "morphology": [t["morphology"] for t in tasks],
        "gold_slp1": [t["gold_slp1"] for t in tasks],
        "gold_devanagari": [t["gold_devanagari"] for t in tasks],
    })


def load_samayik_pairs(path: str | Path) -> list[dict]:
    """data/eval/samayik.json: list of {"en": ..., "sa": ...} dicts."""
    pairs = json.loads((ROOT / path).read_text())
    return [p for p in pairs if p.get("en") and p.get("sa")]
