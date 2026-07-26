"""Prompt rendering + tag extraction — the single source of truth.

Templates live in prompts/*.txt at the repo root. Rewards and evals must use
the extraction helpers here so answer parsing never diverges.
"""

import re
from functools import lru_cache
from pathlib import Path

PROMPT_VERSION = 1
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=None)
def _template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


def render_vp_task(task: dict) -> str:
    """Render a VP dataset task (see data/finetune.json schema) into the
    dhatu+morphology -> verb prompt."""
    return _template("vp_task.txt").format(
        aupadeshika=task["dhatu"]["aupadeshika"],
        gana=task["dhatu"]["gana"],
        artha=task["dhatu"]["artha"],
        **task["morphology"],
    )


def render_translation(english: str) -> str:
    return _template("translation.txt").format(english=english)


def _extract(text: str, tag: str) -> str | None:
    """Content of <tag>...</tag>. None unless exactly one well-formed match."""
    if not isinstance(text, str):
        return None
    matches = re.findall(rf"<{tag}>(.*?)</{tag}>", text, flags=re.DOTALL)
    if len(matches) != 1:
        return None
    inner = matches[0].strip()
    return inner or None


def extract_answer(text: str) -> str | None:
    """Final verb form from a VP-task completion (<answer> tags)."""
    return _extract(text, "answer")


def extract_translation(text: str) -> str | None:
    """Final translation from a translation completion (<translation> tags)."""
    return _extract(text, "translation")
