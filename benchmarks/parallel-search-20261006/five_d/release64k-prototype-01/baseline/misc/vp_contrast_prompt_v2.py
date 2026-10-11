"""Versioned Sanskrit-only terminology for the unchanged contrast task format."""
from finetune.prompts import (slp1_to_devanagari as deva, GANA_EN, LAKARA_EN,
                             PURUSHA_EN, VACANA_EN)
from misc.vp_compositional import OPERATIONS


def render(task):
    dhatu, prefixes = task['dhatu'], task['derivation']['prefixes']
    lines = [
        "You are an expert in Sanskrit grammar (vyakarana).",
        "",
        "Derive the requested conjugated verb forms from the Sanskrit verbal root",
        "(dhatu, given in Devanagari in its Dhatupatha citation form, anubandha markers",
        "included), its verb class (gana), its traditional meaning (artha), and each",
        "row's required Sanskrit grammatical suffixes (sanadi), tense/mood (lakara),",
        "voice (prayoga), person (purusha), and number (vacana).",
        "Each Sanskrit grammatical term is glossed in parentheses in English.",
        "",
        "Each row is a separate Sanskrit derivation from the original dhatu: apply",
        "that row's sanadi suffixes in order, then its specified tense, person and number.",
        "Do not carry a derived Sanskrit stem from one row into another.",
        "Include the listed upasarga (Sanskrit verbal prefixes), in order, with regular sandhi in every answer.",
        "Return ONLY a JSON object inside one <answer></answer> block. Use the row numbers",
        "as string keys and one valid Devanagari form as each value. Include every row exactly once.",
        "Example format for two rows: <answer>{\"1\":\"FORM\",\"2\":\"FORM\"}</answer>.",
        "Do not include explanation. If alternatives are valid, give exactly one per row.",
        "", "=== Your task ===", "",
        f"dhatu (Sanskrit verbal root): {deva(dhatu['aupadeshika'])} (Dhatupatha citation; anubandha markers included)",
        f"gana (verb class): {dhatu['gana']} ({GANA_EN[dhatu['gana']]})",
        f"artha (traditional meaning): {deva(dhatu['artha'])}",
        "upasarga (Sanskrit verbal prefixes, in order): " + (" + ".join(deva(x) for x in prefixes) or "none"),
        "prayoga (voice): Kartari (active)",
        "dhatu_pada (Sanskrit verb ending set): Parasmaipada (active endings)",
        "", "Required forms (each starts from the original dhatu):",
    ]
    for i, form in enumerate(task['forms'], 1):
        m = form['morphology']
        lines.extend([f"{i}. sanadi (Sanskrit grammatical suffixes, innermost first): " +
                      ', followed by '.join(OPERATIONS[x] for x in form['derivation']['sanadi']),
                      f"   lakara (tense/mood): {m['lakara']} ({LAKARA_EN[m['lakara']]}); "
                      f"purusha (person): {m['purusha']} ({PURUSHA_EN[m['purusha']]}); "
                      f"vacana (number): {m['vacana']} ({VACANA_EN[m['vacana']]})"])
    return '\n'.join(lines) + '\n'
