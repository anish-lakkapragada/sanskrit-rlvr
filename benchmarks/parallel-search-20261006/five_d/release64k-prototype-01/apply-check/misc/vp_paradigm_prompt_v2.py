"""Versioned Sanskrit-only terminology for the unchanged small-paradigm format."""
from finetune.prompts import (slp1_to_devanagari as deva, GANA_EN, LAKARA_EN,
                             PURUSHA_EN, VACANA_EN)
from misc.vp_compositional import OPERATIONS


def render(task):
    d, dhatu = task['derivation'], task['dhatu']
    lines = [
        "You are an expert in Sanskrit grammar (vyakarana).",
        "",
        "Derive the requested conjugated verb forms from the Sanskrit verbal root",
        "(dhatu, given in Devanagari in its Dhatupatha citation form, anubandha markers",
        "included), its verb class (gana), its traditional meaning (artha), and the",
        "required Sanskrit grammatical suffixes (sanadi), tense/mood (lakara),",
        "voice (prayoga), person (purusha), and number (vacana).",
        "Each Sanskrit grammatical term is glossed in parentheses in English.",
        "",
        "All rows use the same derived Sanskrit verbal stem. Apply the sanadi suffixes",
        "in the listed order to the dhatu, then inflect separately for each row.",
        "Include the listed upasarga (Sanskrit verbal prefixes), in order, with regular sandhi in every form.",
        "Return ONLY a JSON object inside one <answer></answer> block. Use the row numbers",
        "as string keys and one valid Devanagari form as each value. Include every row exactly once.",
        "Example format for two rows: <answer>{\"1\":\"FORM\",\"2\":\"FORM\"}</answer>.",
        "Do not include explanation. If alternatives are valid, give exactly one per row.",
        "", "=== Your task ===", "",
        f"dhatu (Sanskrit verbal root): {deva(dhatu['aupadeshika'])}",
        f"gana (verb class): {dhatu['gana']} ({GANA_EN[dhatu['gana']]})",
        f"artha (traditional meaning): {deva(dhatu['artha'])}",
        "upasarga (Sanskrit verbal prefixes, in order): " + (" + ".join(deva(p) for p in d['prefixes']) or "none"),
        "sanadi (Sanskrit grammatical suffixes, innermost first): " + ', followed by '.join(OPERATIONS[x] for x in d['sanadi']),
        "prayoga (voice): Kartari (active)",
        "dhatu_pada (Sanskrit verb ending set): Parasmaipada (active endings)",
        "", "Required forms:",
    ]
    for i, form in enumerate(task['forms'], 1):
        m = form['morphology']
        lines.append(f"{i}. lakara (tense/mood): {m['lakara']} ({LAKARA_EN[m['lakara']]}); "
                     f"purusha (person): {m['purusha']} ({PURUSHA_EN[m['purusha']]}); "
                     f"vacana (number): {m['vacana']} ({VACANA_EN[m['vacana']]})")
    return '\n'.join(lines) + '\n'
