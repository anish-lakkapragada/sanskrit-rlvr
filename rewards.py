"""GRPO reward shim: mlx-lm-lora calls this; Lean does the judging."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mlx_lm_lora.trainer.grpo_reward_functions import register_reward_function

from rlvr import reward


@register_reward_function()
def lean_sanskrit_reward(prompts, completions, answer, types=None, **kwargs):
    out = []
    for completion, spec in zip(completions, answer):
        try:
            out.append(float(reward(json.loads(spec), completion)["reward"]))
        except Exception:
            out.append(0.0)
    return out
