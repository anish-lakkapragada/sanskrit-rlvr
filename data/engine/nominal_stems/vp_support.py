"""Reviewed representation checks for the pinned VP 0.4.0 basic/nyap adapter.

VP accepts arbitrary stem strings, so constructor success alone cannot establish
that a dictionary entry is represented correctly. Check source interpretation
and supported stem classes first. No forms or task grids are derived here.
"""

import re

from vidyut.prakriya import Linga, Pratipadika

GENDERS = {"masculine": "Pum", "feminine": "Stri", "neuter": "Napumsaka"}
VOWELS = set("aAiIuUfFxXeEoO")
REASONS = {
    "compound_boundary": "The current basic/nyap adapter does not represent the source's compound/derivational boundaries.",
    "source_notation": "The extended source spelling needs interpretation beyond a bare headword.",
    "special_lexical_metadata": "This headword also has LEXID/INFLECTID metadata requiring a richer grammatical representation.",
    "ambiguous_feminine_class": "The source gives competing feminine inflection-class hints for this headword.",
    "unresolved_feminine_class": "The feminine stem needs a richer constructor or an unreviewed interpretation.",
    "unsupported_stem_class": "The stem falls outside the reviewed basic/nyap representation classes.",
    "constructor_failure": "VP could not construct the selected representation while preserving its spelling and flags.",
}


def source_context(rows):
    special, uncertain_feminine = set(), set()
    for row in rows:
        lex = row["lexnorm"]
        if "=" in lex:
            special.add(row["headword"])
            special.update(re.findall(r"(?:^|,)STEM=([^,]+)", lex))
        if any(token in lex.split(":") for token in ("f#Is", "f#IH", "f#Us", "f#UH")):
            uncertain_feminine.add(row["headword"])
    return special, uncertain_feminine


def select_constructor(entry, context):
    """Return a constructor and reasons; every contributing analysis must pass.

    Representation classes follow the already reviewed subanta adapter. This
    module owns the shared filter without importing a task generator. It uses
    the already resolved spelling, rather than resolving lexical hints again.
    """
    special, uncertain_feminine = context
    stem, gender = entry["stem"], entry["gender"]
    reasons = set()
    for source in entry["sources"]:
        if "-" in source["compound_headword"]:
            reasons.add("compound_boundary")
        elif source["headword"] != source["compound_headword"]:
            reasons.add("source_notation")
        if source["headword"] in special or stem in special:
            reasons.add("special_lexical_metadata")
        if gender == "feminine" and source["headword"] in uncertain_feminine:
            reasons.add("ambiguous_feminine_class")

    syllables = sum(c in VOWELS for c in stem)
    constructor = "basic"
    if gender == "feminine":
        if stem.endswith(("A", "I")):
            if syllables < 2 and stem != "strI":
                reasons.add("unresolved_feminine_class")
            # The established lakzmI exception retains basic interpretation.
            if stem != "lakzmI":
                constructor = "nyap"
        elif stem.endswith("U") and syllables < 2:
            reasons.add("unresolved_feminine_class")
        elif stem.endswith("f") and stem not in {"mAtf", "duhitf", "svasf", "nanAndf", "yAtf"}:
            reasons.add("unresolved_feminine_class")
        elif stem.endswith(("an", "in")):
            reasons.add("unresolved_feminine_class")

    ordinary = stem.endswith(("a", "i", "u", "f"))
    long_feminine = gender == "feminine" and stem.endswith(("A", "I", "U"))
    masculine_a = gender == "masculine" and stem.endswith("A") and syllables >= 2
    nasal = gender in {"masculine", "neuter"} and stem.endswith(("an", "in"))
    s_stem = stem.endswith(("as", "is", "us")) and not stem.endswith(("vas", "Iyas"))
    if not (ordinary or long_feminine or masculine_a or nasal or s_stem or stem in {"go", "nO"}):
        reasons.add("unsupported_stem_class")
    return constructor, sorted(reasons)


def construct(entry, constructor):
    """Construct the VP stem and gender, without requesting any inflection."""
    stem = getattr(Pratipadika, constructor)(entry["stem"])
    gender = getattr(Linga, GENDERS[entry["gender"]])
    if stem.text != entry["stem"] or stem.is_nyap != (constructor == "nyap") or stem.is_avyaya:
        raise ValueError("VP constructor did not preserve the requested stem interpretation")
    return stem, gender


def filter_entries(entries, rows):
    context = source_context(rows)
    kept, removed, constructors = [], [], {}
    for entry in entries:
        constructor, reasons = select_constructor(entry, context)
        error = None
        if not reasons:
            try:
                construct(entry, constructor)
            except Exception as exc:
                reasons = ["constructor_failure"]
                error = {"type": type(exc).__name__, "message": str(exc)}
        if reasons:
            exclusion = {**entry, "reasons": reasons}
            if error:
                exclusion["error"] = error
            removed.append(exclusion)
        else:
            # Keep the original JSON record exactly as it was; filter rows only.
            kept.append(entry)
            constructors[entry["id"]] = constructor
    return kept, removed, constructors
