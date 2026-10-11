"""Create a small contrast set with a different derivation in each row."""
from finetune.prompts import (slp1_to_devanagari as deva, GANA_EN, LAKARA_EN,
                             PURUSHA_EN, VACANA_EN)
from misc.vp_compositional import OPERATIONS


def render(task):
    root, prefixes = task['dhatu'], task['derivation']['prefixes']
    lines = [
        "You are an expert in Sanskrit grammar (vyakarana).",
        "Derive the requested conjugated Sanskrit verb forms from the root below.",
        "Each row is a separate derivation from the original root: apply that row's",
        "sanadi operations in order, then its specified tense, person and number.",
        "Do not carry a derived stem from one row into another.",
        "Include the listed upasarga prefixes, in order, with regular sandhi in every answer.",
        "Return ONLY a JSON object inside one <answer></answer> block. Use the row numbers",
        "as string keys and one valid Devanagari form as each value. Include every row exactly once.",
        "Example format for two rows: <answer>{\"1\":\"FORM\",\"2\":\"FORM\"}</answer>.",
        "Do not include explanation. If alternatives are valid, give exactly one per row.",
        "", "=== Your task ===", "",
        f"dhatu (Sanskrit verbal root): {deva(root['aupadeshika'])} (Dhatupatha citation; anubandha markers included)",
        f"gana (verb class): {root['gana']} ({GANA_EN[root['gana']]})",
        f"artha (traditional meaning): {deva(root['artha'])}",
        "upasarga (prefixes, in order): " + (" + ".join(deva(x) for x in prefixes) or "none"),
        "prayoga (voice): Kartari (active)",
        "dhatu_pada (ending set): Parasmaipada (active endings)",
        "", "Required forms (each starts from the original root):",
    ]
    for i, form in enumerate(task['forms'], 1):
        m = form['morphology']
        lines.extend([f"{i}. sanadi (derived-root suffixes, innermost first): " +
                      ', followed by '.join(OPERATIONS[x] for x in form['derivation']['sanadi']),
                      f"   lakara: {m['lakara']} ({LAKARA_EN[m['lakara']]}); "
                      f"purusha: {m['purusha']} ({PURUSHA_EN[m['purusha']]}); "
                      f"vacana: {m['vacana']} ({VACANA_EN[m['vacana']]})"])
    return '\n'.join(lines) + '\n'
