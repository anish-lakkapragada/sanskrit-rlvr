"""Prompt rendering + tag extraction — the single source of truth.

Templates live in prompts/*.txt at the repo root. Rewards and evals must use
the extraction helpers here so answer parsing never diverges.
"""

import re
from functools import lru_cache
from pathlib import Path

PROMPT_VERSION = 1
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=None)
def _template(name: str) -> str:
    return (PROMPTS_DIR / name).read_text()


# English glosses for every morphological value in the dataset (v1 prompts).
# Keyed by the vidyut-prakriya enum spellings used in data/finetune/*.json;
# a KeyError here means the dataset grew a value this table does not know.
GANA_EN = {
    "Bhvadi": "class 1", "Adadi": "class 2", "Juhotyadi": "class 3",
    "Divadi": "class 4", "Svadi": "class 5", "Tudadi": "class 6",
    "Rudhadi": "class 7", "Tanadi": "class 8", "Kryadi": "class 9",
    "Curadi": "class 10",
}
LAKARA_EN = {
    "Lat": "present", "Lit": "perfect", "Lut": "periphrastic future",
    "Lrt": "simple future", "Lot": "imperative", "Lan": "imperfect",
    "VidhiLin": "optative", "AshirLin": "benedictive", "Lun": "aorist",
    "Lrn": "conditional",
}
PRAYOGA_EN = {"Kartari": "active", "Karmani": "passive", "Bhave": "impersonal"}
PURUSHA_EN = {"Prathama": "third person", "Madhyama": "second person",
              "Uttama": "first person"}
VACANA_EN = {"Eka": "singular", "Dvi": "dual", "Bahu": "plural"}

# Three Dhatupatha citations have an it-prefix vowel abutting the root vowel
# (Yi+i, wu+o); flat Devanagari needs an independent vowel there and
# vidyut-lipi merges instead, so these are hand-rendered.
_DEVA_OVERRIDES = {
    "YiinDI~\\": "ञिइन्धीँ॒",
    "wuo~Svi": "टुओँश्वि",
    "wuo~sPUrjA~": "टुओँस्फूर्जाँ",
}


@lru_cache(maxsize=None)
def slp1_to_devanagari(text: str) -> str:
    """SLP1 -> Devanagari via vidyut-lipi (imported lazily: only v1 templates
    need it). Verified lossless over every dataset aupadeshika/artha except
    the three _DEVA_OVERRIDES hiatus roots."""
    if text in _DEVA_OVERRIDES:
        return _DEVA_OVERRIDES[text]
    from vidyut.lipi import Scheme, transliterate

    return transliterate(text, Scheme.Slp1, Scheme.Devanagari)


def render_vp_task(task: dict, template: str = "v0/vp_task.txt") -> str:
    """Render a VP dataset task (see data/finetune.json schema) into the
    dhatu+morphology -> verb prompt. ``template`` selects the prompts/*.txt
    file (e.g. the v1 zero-shot glossed variant v1/vp_task_eval.txt).

    v0 templates use the raw SLP1/enum fields; v1 templates additionally use
    *_deva (Devanagari) and *_en (English gloss) placeholders, computed only
    when the template mentions them so v0 renders never import vidyut."""
    tpl = _template(template)
    m = task["morphology"]
    fields = {
        "aupadeshika": task["dhatu"]["aupadeshika"],
        "gana": task["dhatu"]["gana"],
        "artha": task["dhatu"]["artha"],
        **m,
        "gana_en": GANA_EN[task["dhatu"]["gana"]],
        "lakara_en": LAKARA_EN[m["lakara"]],
        "prayoga_en": PRAYOGA_EN[m["prayoga"]],
        "purusha_en": PURUSHA_EN[m["purusha"]],
        "vacana_en": VACANA_EN[m["vacana"]],
    }
    if "{aupadeshika_deva}" in tpl:
        fields["aupadeshika_deva"] = slp1_to_devanagari(task["dhatu"]["aupadeshika"])
    if "{artha_deva}" in tpl:
        fields["artha_deva"] = slp1_to_devanagari(task["dhatu"]["artha"])
    return tpl.format(**fields)


def render_translation(english: str) -> str:
    return _template("v0/translation.txt").format(english=english)


def _extract(text: str, tag: str) -> str | None:
    """Content of <tag>...</tag>. None unless exactly one well-formed match."""
    if not isinstance(text, str):
        return None
    matches = re.findall(rf"<{tag}>(.*?)</{tag}>", text, flags=re.DOTALL)
    if len(matches) != 1:
        return None
    inner = matches[0].strip()
    return inner or None


def extract_answer(text: str) -> str | None:
    """Final verb form from a VP-task completion (<answer> tags)."""
    return _extract(text, "answer")


def extract_translation(text: str) -> str | None:
    """Final translation from a translation completion (<translation> tags)."""
    return _extract(text, "translation")
