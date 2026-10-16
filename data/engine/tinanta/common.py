"""Tiṅanta eligibility and complete JSON-to-prompt hydration."""

from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import unicodedata

from vidyut.lipi import Scheme, transliterate

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "data/engine/prompts/v2/vp_tinanta.txt"
GANA = {name: f"class {i}" for i, name in enumerate(
    ("Bhvadi", "Adadi", "Juhotyadi", "Divadi", "Svadi", "Tudadi", "Rudhadi", "Tanadi", "Kryadi", "Curadi"), 1)}
LAKARA = {"Lat": "present", "Lit": "perfect", "Lut": "periphrastic future",
          "Lrt": "simple future", "Lot": "imperative", "Lan": "imperfect",
          "VidhiLin": "optative", "AshirLin": "benedictive", "Lun": "aorist", "Lrn": "conditional"}
PRAYOGA = {"Kartari": "active", "Karmani": "passive", "Bhave": "impersonal"}
PURUSHA = {"Prathama": "third person", "Madhyama": "second person", "Uttama": "first person"}
VACANA = {"Eka": "singular", "Dvi": "dual", "Bahu": "plural"}
CITATIONS = {"YiinDI~\\": "ञिइन्धीँ॒", "wuo~Svi": "टुओँश्वि", "wuo~sPUrjA~": "टुओँस्फूर्जाँ"}
EXCLUSIONS = {
    "bhave_requires_third_person_singular": "Bhāve requires third-person singular; exclude incompatible person/number before calling VP.",
    "no_forms": "VP returned no forms.",
    "invalid_gold_encoding": "A gold form does not round-trip losslessly through Devanagari.",
    "ambiguous_prompt": "Identical visible prompts have different gold sets because of hidden lexical metadata; exclude every conflicting record.",
}


def coordinate_exclusion(coordinate):
    _, voice, person, number = coordinate
    if voice == "Bhave" and (person, number) != ("Prathama", "Eka"):
        return "bhave_requires_third_person_singular"
    return None


@lru_cache(maxsize=16384)
def deva(text):
    return unicodedata.normalize("NFC", transliterate(text, Scheme.Slp1, Scheme.Devanagari))


def valid_gold(forms):
    return bool(forms) and forms == sorted(set(forms)) and all(
        form and deva(form) and all("\u0900" <= c <= "\u097f" for c in deva(form))
        and transliterate(deva(form), Scheme.Devanagari, Scheme.Slp1) == form for form in forms)


@lru_cache(maxsize=1)
def template_text():
    return TEMPLATE.read_text()


def render_task(row):
    d, m = row["dhatu"], row["morphology"]
    if coordinate_exclusion(tuple(m[k] for k in ("lakara", "prayoga", "purusha", "vacana"))):
        raise ValueError("Cannot render an ineligible bhave coordinate")
    if d.get("sanadi"):
        raise ValueError("Additional sanadi is outside the tinanta task scope")
    prefixes = ("upasarga (verbal prefixes to include, in order): "
                + " + ".join(deva(p) for p in d["prefixes"]) + "\n") if d.get("prefixes") else ""
    return template_text().format(
        aupadeshika_deva=CITATIONS.get(d["aupadeshika"], deva(d["aupadeshika"])),
        gana=d["gana"], gana_en=GANA[d["gana"]], artha_deva=deva(d["artha"]),
        prefixes_block=prefixes, **m, lakara_en=LAKARA[m["lakara"]],
        prayoga_en=PRAYOGA[m["prayoga"]], purusha_en=PURUSHA[m["purusha"]], vacana_en=VACANA[m["vacana"]],
    ).rstrip() + "\n"


def prompt_conflicts(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[render_task(row)].append(row)
    return sorted(row["id"] for group in groups.values()
                  if len({tuple(row["gold_devanagari"]) for row in group}) > 1 for row in group)
