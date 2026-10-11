"""Plain grammatical specification for the same one-form creation problem."""
from finetune.prompts import (slp1_to_devanagari as deva, GANA_EN, LAKARA_EN,
                             PRAYOGA_EN, PURUSHA_EN, VACANA_EN)

DESCRIPTIONS = {
    ("Ric",): "causative (णिजन्त)",
    ("san",): "desiderative (सन्नन्त)",
    ("yaN",): "intensive (यङन्त)",
    ("yaNluk",): "intensive with यङ् deletion (यङ्लुगन्त)",
    ("Ric", "san"): "desiderative of the causative (णिजन्तस्य सन्नन्तम्)",
    ("san", "Ric"): "causative of the desiderative (सन्नन्तस्य णिजन्तम्)",
    ("yaN", "Ric"): "causative of the intensive (यङन्तस्य णिजन्तम्)",
    ("yaN", "Ric", "san"): "desiderative of the causative of the intensive (यङन्तस्य णिजन्तस्य सन्नन्तम्)",
}


def render(task):
    d, m, form = task["dhatu"], task["morphology"], task["derivation"]
    prefix = " + ".join(map(deva, form["prefixes"])) or "none"
    return f"""Sanskrit grammar exercise: supply one correctly inflected finite verb in Devanagari.

Dhātupāṭha citation (including grammatical markers): {deva(d['aupadeshika'])}
Verb class: {d['gana']} ({GANA_EN[d['gana']]})
Traditional meaning: {deva(d['artha'])}
Derived verb: {DESCRIPTIONS[tuple(form['sanadi'])]}
Upasarga: {prefix}
Tense or mood: {m['lakara']} ({LAKARA_EN[m['lakara']]})
Voice: {m['prayoga']} ({PRAYOGA_EN[m['prayoga']]})
Person: {m['purusha']} ({PURUSHA_EN[m['purusha']]})
Number: {m['vacana']} ({VACANA_EN[m['vacana']]})

Use the traditional rules of Sanskrit grammar, including regular sandhi with the upasarga.
Any grammatically permitted pada and any valid variant are acceptable.
Return exactly one form in <answer>...</answer>, with no other text."""
