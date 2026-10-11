"""Versioned prompt for an explicitly specified grammatical ending set."""
from misc.vp_compositional_prompt_v3 import render as render_fields


def render(task):
    pada = task["morphology"]["dhatu_pada"]
    labels = {"Parasmaipada": "Parasmaipada (active endings)",
              "Atmanepada": "Atmanepada (middle endings)"}
    return render_fields(task) + f"- dhatu_pada (ending set): {labels[pada]}\n"
