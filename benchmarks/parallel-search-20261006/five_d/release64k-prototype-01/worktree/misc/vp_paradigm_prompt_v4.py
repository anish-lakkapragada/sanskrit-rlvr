"""Format diagnostic: identical Sanskrit questions with ordered-line answers."""
from misc.vp_paradigm_prompt_v3 import render as render_previous
from misc.vp_contrast_prompt_v4 import JSON_INSTRUCTIONS, LINE_INSTRUCTIONS


def render(task):
    previous = render_previous(task)
    if previous.count(JSON_INSTRUCTIONS) != 1:
        raise ValueError('Frozen output instructions unexpectedly changed')
    return previous.replace(JSON_INSTRUCTIONS, LINE_INSTRUCTIONS)
