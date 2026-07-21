"""GRPO reward registration: mlx-lm-lora loads this file by path; the task
spec rides in each dataset row's `answer` field and the Lean checker judges
the completion."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mlx_lm_lora.trainer.grpo_reward_functions import register_reward_function

from finetune.reward import chrf_reward_from_answer_field, reward_from_answer_field


@register_reward_function()
def lean_sanskrit_reward(prompts, completions, answer, types=None, **kwargs):
    return [reward_from_answer_field(spec, completion)
            for completion, spec in zip(completions, answer)]


@register_reward_function()
def chrf_format_reward(prompts, completions, answer, types=None, **kwargs):
    """The non-verified control: same shape, chrF++ instead of the compiler."""
    return [chrf_reward_from_answer_field(spec, completion)
            for completion, spec in zip(completions, answer)]
