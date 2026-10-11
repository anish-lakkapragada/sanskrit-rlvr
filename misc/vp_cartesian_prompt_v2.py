"""Versioned wording probe for a Sanskrit exercise misclassified as cyber.

All grammatical fields and output requirements remain identical to v1.
"""
from misc.vp_cartesian_prompt_v1 import render as render_v1


def render(task):
    return render_v1(task).replace('Sanskrit verbal root', 'Sanskrit verb entry')
