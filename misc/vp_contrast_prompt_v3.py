"""Paired terminology probe: replace only 'Sanskrit verbal root' with 'Sanskrit verbal base'."""
from misc.vp_contrast_prompt_v2 import render as render_previous


def render(task):
    return render_previous(task).replace('Sanskrit verbal root', 'Sanskrit verbal base')
