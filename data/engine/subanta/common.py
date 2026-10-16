"""MWlexnorm-only normalization, pinned VP requests, and prompt hydration."""

from __future__ import annotations

from collections import defaultdict
import csv
from collections import Counter
from functools import lru_cache
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sys
import unicodedata

from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Linga, Pada, Pratipadika, Vacana, Vibhakti, Vyakarana

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "data/engine/files/mw-lexnorm/nominal-entries.csv"
SOURCE_SHA256 = "84797688cfbc3e82260567cf7cca86353acc14b6898f45f279e5a92b4c2b07cc"
SOURCE_REVISION = "34e51125583b1f5026d44e6ef1e44d2a88b73670"
TEMPLATE = ROOT / "data/engine/prompts/v2/vp_subanta.txt"
OUTPUT = ROOT / "data/datasets/subanta"
VIDYUT_VERSION = "0.4.0"
ENGINE_OPTIONS = dict(log_steps=False, is_chandasi=False, use_svaras=False, nlp_mode=False)
GENDERS = {"m": "Pum", "f": "Stri", "n": "Napumsaka"}
GENDER_LABELS = {"Pum": "masculine", "Stri": "feminine", "Napumsaka": "neuter"}
CASES = {
    "Prathama": "nominative (first case)", "Dvitiya": "accusative (second case)",
    "Trtiya": "instrumental (third case)", "Caturthi": "dative (fourth case)",
    "Panchami": "ablative (fifth case)", "Sasthi": "genitive (sixth case)",
    "Saptami": "locative (seventh case)", "Sambodhana": "vocative (address)",
}
NUMBERS = {"Eka": "singular", "Dvi": "dual", "Bahu": "plural"}
SLP1 = re.compile(r"[aAiIuUfFxXeEoOkKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzshMH]+\Z")
VOWELS = set("aAiIuUfFxXeEoO")
REASON_LABELS = {
    "compound_boundary": "Compound/derivational boundaries are not represented by this basic-stem adapter.",
    "source_notation": "Headword/key2 spelling needs source-specific interpretation.",
    "special_lexical_metadata": "LEXID/INFLECTID, or a homographic entry with that metadata, needs additional grammatical information.",
    "indeclinable": "Indeclinables have no requested case/number paradigm in this task.",
    "unsupported_descriptor": "Lexnorm descriptor outside the reviewed grammar.",
    "unresolved_stem_hint": "The source's stem hint has no reviewed conversion rule.",
    "unresolved_feminine_class": "Feminine constructor or stem formation cannot be resolved in the reviewed scope.",
    "unsupported_stem_class": "Stem class needs derivational metadata or has not been reviewed for the basic constructor.",
    "ambiguous_constructor": "The same displayed stem and gender have incompatible basic/nyap interpretations.",
    "invalid_stem_encoding": "The resolved stem does not round-trip through Devanagari.",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=250_000)
def deva(text):
    return unicodedata.normalize("NFC", transliterate(text, Scheme.Slp1, Scheme.Devanagari))


def valid_text(text):
    rendered = deva(text)
    return bool(text and rendered and all("\u0900" <= c <= "\u097f" for c in rendered)
                and transliterate(rendered, Scheme.Devanagari, Scheme.Slp1) == text)


def valid_gold(forms):
    return bool(forms and forms == sorted(set(forms)) and all(valid_text(s) for s in forms))


def read_source():
    require(importlib.metadata.version("vidyut") == VIDYUT_VERSION, "Wrong Vidyut version")
    require(sha256(SOURCE) == SOURCE_SHA256, "MWlexnorm source hash changed")
    with SOURCE.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    require(len(rows) == 197652 and len({r["mw_id"] for r in rows}) == len(rows), "Source inventory changed")
    return rows


def resolve_hint(stem, hint):
    """Reviewed cases from MWlexnorm's README and step1b/stemmodel.py.

    Preserve each explicit alternative. Never append an arbitrary hint or try
    to infer its replacement span by string similarity.
    """
    if hint in {"a", "A", "i", "I", "u", "U"}:
        if stem[-1] in VOWELS:
            return stem[:-1] + hint
        if hint in {"A", "I"}:
            return stem + hint
    if hint in {"ikA", "akA", "ikI", "akI"}:
        if stem.endswith(("aka", "ika")):
            return stem[:-3] + hint
        if stem.endswith("a") and hint in {"ikA", "akA"}:
            return stem[:-1] + hint
    replacements = {
        "vI": [("u", "vI"), ("U", "vI")],
        "inI": [("in", "inI")], "iRI": [("in", "iRI")],
        "jYI": [("jan", "jYI")], "jA": [("jan", "jA")],
        "arI": [("van", "varI")], "varI": [("van", "varI")],
        "mnI": [("man", "mnI")], "GnI": [("han", "GnI")],
        "trI": [("tf", "trI")], "rI": [("f", "rI")],
        "antI": [("at", "antI")], "ntI": [("at", "antI")],
        "atI": [("at", "atI")], "padI": [("pad", "padI")],
    }
    for ending, replacement in replacements.get(hint, []):
        if stem.endswith(ending):
            return stem[:-len(ending)] + replacement
    return None


def resolve_descriptor(headword, descriptor):
    match = re.fullmatch(r"([mfn])(?:#([^:]+))?", descriptor)
    if not match:
        return None, "indeclinable" if descriptor == "ind" else "unsupported_descriptor"
    gender, hint = match.groups()
    stem = headword
    if hint:
        # Complex masculine/neuter stem hints have different conventions.
        if gender != "f" and hint not in {"a", "i", "u", "A", "I", "U"}:
            return None, "unresolved_stem_hint"
        stem = resolve_hint(stem, hint)
        if stem is None:
            return None, "unresolved_stem_hint"
    elif gender == "f" and stem.endswith("a"):
        stem = stem[:-1] + "A"
    if gender == "n" and stem[-1] in "AIU":
        stem = stem[:-1] + stem[-1].lower()  # 1.2.47; no hidden long-vowel shortening.

    is_nyap = False
    if gender == "f":
        # Ordinary A/I feminine stems need nyap. Root nouns such as DI/SrI need
        # a derivational constructor, not merely basic versus nyap.
        syllables = sum(c in VOWELS for c in stem)
        if stem.endswith(("A", "I")):
            if syllables < 2 and stem != "strI":
                return None, "unresolved_feminine_class"
            # Verified against VP 0.4.0's kaumudi_09.rs, sk_300.
            is_nyap = stem != "lakzmI"
        elif stem.endswith("U"):
            if syllables < 2:
                return None, "unresolved_feminine_class"
        elif stem.endswith("f"):
            if stem not in {"mAtf", "duhitf", "svasf", "nanAndf", "yAtf"}:
                return None, "unresolved_feminine_class"
        elif stem.endswith(("an", "in")):
            # No default feminine -n rule: source hints and retroflexion matter.
            return None, "unresolved_feminine_class"

    # Reviewed basic-stem classes. -at/-mat/-vat participles/adjectives, -vas,
    # root nouns and other consonant classes require richer VP arguments.
    ordinary = stem.endswith(("a", "i", "u", "f"))
    long_feminine = gender == "f" and stem.endswith(("A", "I", "U"))
    masculine_a = gender == "m" and stem.endswith("A") and sum(c in VOWELS for c in stem) >= 2
    nasal = gender in {"m", "n"} and stem.endswith(("an", "in"))
    s_stem = stem.endswith(("as", "is", "us")) and not stem.endswith(("vas", "Iyas"))
    special_vowel = stem in {"go", "nO"}
    if not (ordinary or long_feminine or masculine_a or nasal or s_stem or special_vowel):
        return None, "unsupported_stem_class"
    if not SLP1.fullmatch(stem) or not valid_text(stem):
        return None, "invalid_stem_encoding"
    return (stem, is_nyap, GENDERS[gender]), None


def paradigm_id(key):
    stem, nyap, gender = key
    return f"subanta:{stem}:{'nyap' if nyap else 'basic'}:{gender}"


def normalize_source():
    rows = read_source()
    special = set()
    uncertain_feminine = set()
    for row in rows:
        lex = row["lexnorm"]
        if "LEXID=" in lex or "INFLECTID=" in lex:
            special.add(row["headword"])
            special.update(re.findall(r"(?:^|,)STEM=([^,]+)", lex))
        if any(t in lex.split(":") for t in ("f#Is", "f#IH", "f#Us", "f#UH")):
            uncertain_feminine.add(row["headword"])
    entries = {}
    audits = []
    for row in rows:
        headword, lex = row["headword"], row["lexnorm"]
        descriptors = list(dict.fromkeys(lex.split(":")))
        a = {**row, "source_line": int(row["source_line"]), "paradigm_ids": [], "excluded": []}
        # Potential count before any scope filters. Null for special grammars.
        a["unfiltered_potential_tasks"] = (None if "=" in lex else
            24 * sum(bool(re.fullmatch(r"[mfn](?:#[^:]+)?", t)) for t in descriptors))
        reason = None
        if "-" in row["compound_headword"]:
            reason = "compound_boundary"
        elif row["compound_headword"] != headword or not SLP1.fullmatch(headword):
            reason = "source_notation"
        elif headword in special or "=" in lex:
            reason = "special_lexical_metadata"
        if reason:
            a["excluded"].append({"descriptor": lex, "reason": reason})
        else:
            for descriptor in descriptors:
                if descriptor.startswith("f") and headword in uncertain_feminine:
                    key, reason = None, "ambiguous_constructor"
                else:
                    key, reason = resolve_descriptor(headword, descriptor)
                if reason:
                    a["excluded"].append({"descriptor": descriptor, "reason": reason})
                    continue
                pid = paradigm_id(key)
                e = entries.setdefault(pid, {
                    "id": pid, "stem": key[0], "is_nyap": key[1], "linga": key[2],
                    "mw_ids": [],
                })
                if row["mw_id"] not in e["mw_ids"]:
                    e["mw_ids"].append(row["mw_id"])
                if pid not in a["paradigm_ids"]:
                    a["paradigm_ids"].append(pid)
        audits.append(a)

    # No hidden constructor can change the gold for an otherwise identical
    # rendered stem+gender question. Remove all sides of any conflict.
    interpretations = defaultdict(list)
    for pid, e in entries.items():
        interpretations[(deva(e["stem"]), e["linga"])].append(pid)
    conflicts = {p for ps in interpretations.values() if len(ps) > 1 for p in ps}
    for a in audits:
        for pid in a["paradigm_ids"][:]:
            if pid in conflicts:
                a["paradigm_ids"].remove(pid)
                a["excluded"].append({"paradigm_id": pid, "reason": "ambiguous_constructor"})
    return [entries[p] for p in sorted(entries) if p not in conflicts], audits


def load_stems():
    from data.engine.nominal_stems import inventory
    return inventory.for_task("subanta")


def code_files():
    from data.engine.nominal_stems import inventory
    return [Path(__file__), Path(__file__).with_name("generate.py"), *inventory.CODE]


def shared_source_metadata():
    from data.engine.nominal_stems import inventory
    return inventory.source_metadata()


def coordinates():
    return [(case, number) for case in CASES for number in NUMBERS]


def request(entry, case, number):
    stem = (Pratipadika.nyap if entry["is_nyap"] else Pratipadika.basic)(entry["stem"])
    return Pada.Subanta(stem, getattr(Linga, entry["linga"]),
                        getattr(Vibhakti, case), getattr(Vacana, number))


def derive_paradigm(entry, log_steps=False):
    engine = get_engine(log_steps)
    result = []
    for case, number in coordinates():
        try:
            forms = sorted({p.text for p in engine.derive(request(entry, case, number))})
        except BaseException as exc:
            if isinstance(exc, Exception) or type(exc).__name__ == "PanicException":
                raise RuntimeError(f"Engine failure: {entry['id']}:{case}:{number}") from exc
            raise
        reason = "no_forms" if not forms else None
        if forms and not valid_gold(forms):
            reason = "invalid_gold_encoding"
        result.append((case, number, forms, reason))
    return result


@lru_cache(maxsize=2)
def get_engine(log_steps=False):
    return Vyakarana(**{**ENGINE_OPTIONS, "log_steps": log_steps})


def make_record(entry, case, number, forms):
    return {
        "id": f"{entry['id']}:{case}:{number}",
        "pratipadika": {k: entry[k] for k in ("stem", "is_nyap", "mw_ids")},
        "morphology": {"linga": entry["linga"], "vibhakti": case, "vacana": number},
        "gold_slp1": forms, "gold_devanagari": [deva(s) for s in forms],
    }


@lru_cache(maxsize=1)
def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def render_task(task):
    p, m = task["pratipadika"], task["morphology"]
    return template_text().format(
        stem_deva=deva(p["stem"]), linga=GENDER_LABELS[m["linga"]],
        vibhakti=CASES[m["vibhakti"]], vacana=NUMBERS[m["vacana"]],
    ).rstrip() + "\n"


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def finish_audits(entries, audits, exported):
    """Count shared tasks separately from first-source-row ownership."""
    owners = {entry["id"]: entry["mw_ids"][0] for entry in entries}
    for row in audits:
        pids = row["paradigm_ids"]
        row["candidate_tasks"] = 24 * len(pids)
        row["exported_tasks"] = sum(exported[pid] for pid in pids)
        row["new_unique_tasks"] = sum(exported[pid] for pid in pids
                                      if owners[pid] == row["mw_id"])
        row["status"] = ("excluded" if not row["exported_tasks"] else
                         "partial" if row["excluded"] or row["exported_tasks"] < row["candidate_tasks"]
                         else "included")
    return audits


def source_counts(audits):
    return {
        "rows": len(audits),
        "rows_with_tasks": sum(bool(r["exported_tasks"]) for r in audits),
        "row_status": dict(sorted(Counter(r["status"] for r in audits).items())),
        "exclusion_events": dict(sorted(Counter(e["reason"] for r in audits for e in r["excluded"]).items())),
        "candidate_tasks_per_row": dict(sorted(Counter(str(r["candidate_tasks"]) for r in audits).items(), key=lambda p: int(p[0]))),
        "exported_tasks_per_row": dict(sorted(Counter(str(r["exported_tasks"]) for r in audits).items(), key=lambda p: int(p[0]))),
        "new_unique_tasks": sum(r["new_unique_tasks"] for r in audits),
    }


def write_array(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="\n") as f:
        f.write("[\n")
        first = True
        for row in rows:
            if not first:
                f.write(",\n")
            f.write(compact(row))
            first = False
        f.write("]\n" if first else "\n]\n")


def iter_array(path):
    """Stream the one-record-per-line JSON array emitted by this generator."""
    with Path(path).open(encoding="utf-8") as f:
        require(f.readline() == "[\n", f"Unexpected array format: {path}")
        line = f.readline()
        if line == "]\n":
            require(not f.read(), "Trailing content")
            return
        while line:
            next_line = f.readline()
            if next_line == "]\n":
                require(not line.rstrip().endswith(","), "Trailing comma")
                yield json.loads(line)
                require(not f.read(), "Trailing content")
                return
            require(line.endswith(",\n"), "Missing JSON array separator")
            yield json.loads(line[:-2])
            line = next_line
        raise ValueError(f"Unterminated JSON array: {path}")
