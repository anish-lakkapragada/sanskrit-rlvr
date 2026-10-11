"""Frozen prompt for a specified subset of a derived verb's paradigm."""
from finetune.prompts import (slp1_to_devanagari as deva, GANA_EN, LAKARA_EN,
                             PURUSHA_EN, VACANA_EN)
from misc.vp_compositional import OPERATIONS


def render(task):
    d, root = task["derivation"], task["dhatu"]
    lines = [
        "You are an expert in Sanskrit grammar (vyakarana).",
        "Derive every requested conjugated form of the same Sanskrit derived root.",
        "The root is given in its Dhatupatha citation form, with anubandha markers included.",
        "Apply the sanadi operations in the listed order, then inflect separately for each row.",
        "Include the listed upasarga prefixes, in order, with regular sandhi in every form.",
        "Return ONLY a JSON object inside one <answer></answer> block. Use the row numbers",
        "as string keys and one valid Devanagari form as each value. Include every row exactly once.",
        "Example format for two rows: <answer>{\"1\":\"FORM\",\"2\":\"FORM\"}</answer>.",
        "Do not include explanation. If alternatives are valid, give exactly one per row.",
        "", "=== Your task ===", "",
        f"dhatu (Sanskrit verbal root): {deva(root['aupadeshika'])}",
        f"gana (verb class): {root['gana']} ({GANA_EN[root['gana']]})",
        f"artha (traditional meaning): {deva(root['artha'])}",
        "upasarga (prefixes, in order): " + (" + ".join(deva(p) for p in d["prefixes"]) or "none"),
        "sanadi (derived-root suffixes, innermost first): " + ", followed by ".join(OPERATIONS[x] for x in d["sanadi"]),
        "prayoga (voice): Kartari (active)",
        "dhatu_pada (ending set): Parasmaipada (active endings)",
        "", "Required forms:",
    ]
    for i, form in enumerate(task["forms"], 1):
        m = form["morphology"]
        lines.append(f"{i}. lakara: {m['lakara']} ({LAKARA_EN[m['lakara']]}); "
                     f"purusha: {m['purusha']} ({PURUSHA_EN[m['purusha']]}); "
                     f"vacana: {m['vacana']} ({VACANA_EN[m['vacana']]})")
    return "\n".join(lines) + "\n"
