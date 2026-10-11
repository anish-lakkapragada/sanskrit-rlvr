"""Extend the established Sanskrit task template with two grammatical fields."""
from finetune.prompts import render_vp_task, slp1_to_devanagari
from misc.vp_compositional import OPERATIONS


def render(task):
    d = task["derivation"]
    prefixes = " + ".join(slp1_to_devanagari(p) for p in d["prefixes"]) or "none"
    operations = ", followed by ".join(OPERATIONS[op] for op in d["sanadi"]) or "none"
    fields = (f"upasarga (Sanskrit verbal prefix): {prefixes}\n"
              f"sanadi (Sanskrit derived-root suffixes, innermost first): {operations}\n\n")
    return render_vp_task(task, "v2/vp_task_eval.txt").replace("Required form:\n", fields + "Required form:\n")
