"""Pinned request scope, source loading, and JSON-to-prompt rendering."""

from __future__ import annotations

import csv
from functools import lru_cache
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import tempfile
import unicodedata

from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Data, Krt, Pratipadika

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/engine/files/vidyut_dhatupatha_5.tsv"
TEMPLATE = ROOT / "data/engine/prompts/v2/vp_krdanta.txt"
OUTPUT = ROOT / "data/datasets/krdanta"
VIDYUT_VERSION = "0.4.0"
SOURCE_SHA256 = "c6c494a6c534130b2d8e8f344d2f5e3ffbc64ed45b390e2a4e35e526f1cecd09"
ENGINE_OPTIONS = dict(log_steps=False, is_chandasi=False, use_svaras=False, nlp_mode=False)
EXPECTED_PREFIXES = {
    "02.0012": ["AN"], "02.0041": ["aDi"], "02.0042": ["aDi"], "10.0368": ["AN"],
}

# Ordered, deliberately reviewed scope: productive classical formations with
# no unsupplied upapada or separately selected semantic sense. These rules were
# checked in the source distribution of the exact installed Python release.
SUFFIXES = {
    "kta": ("past participle", "3.2.102"),
    "ktavatu": ("past active participle", "3.2.102"),
    "tfc": ("agent noun", "3.1.133"),
    "Rvul": ("agent noun", "3.1.133"),
    "tumun": ("infinitive", "3.3.10"),
    "ktvA": ("absolutive; having performed the action", "3.4.21"),
    "tavya": ("gerundive; necessity or possibility", "3.1.96"),
    "tavyat": ("gerundive; necessity or possibility", "3.1.96"),
    "anIyar": ("gerundive; necessity or possibility", "3.1.96"),
    "yat": ("gerundive; necessity or possibility", "3.1.97-3.1.132"),
    "Ryat": ("gerundive; necessity or possibility", "3.1.97-3.1.132"),
    "lyuw": ("nominal derivative", "3.3.115"),
    "Satf": ("present active participle with parasmaipada formation", "3.2.124"),
    "SAnac": ("present active participle with atmanepada formation", "3.2.124"),
}
PARTICIPLES = {"Satf", "SAnac"}
GANA_EN = {
    "Bhvadi": "class 1", "Adadi": "class 2", "Juhotyadi": "class 3",
    "Divadi": "class 4", "Svadi": "class 5", "Tudadi": "class 6",
    "Rudhadi": "class 7", "Tanadi": "class 8", "Kryadi": "class 9",
    "Curadi": "class 10",
}
# Citation hiatus that plain vidyut-lipi transliteration collapses. These are
# the same display fixes used by the archived finetune/prompts.py.
CITATION_OVERRIDES = {
    "YiinDI~\\": "ञिइन्धीँ॒",
    "wuo~Svi": "टुओँश्वि",
    "wuo~sPUrjA~": "टुओँस्फूर्जाँ",
}
SDIST_URL = "https://files.pythonhosted.org/packages/69/b5/6876b3f807ac38812c6e29eb43738d28a6a21c2aed456486e654997efcdd/vidyut-0.4.0.tar.gz"
SDIST_SHA256 = "fb776ec751e66c8d44bd94ef71008f9ea05284f51055aa009cfaef33ccf5f454"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def enum_name(value):
    return None if value is None else repr(value).rsplit(".", 1)[-1]


def deva(text):
    return unicodedata.normalize("NFC", transliterate(text, Scheme.Slp1, Scheme.Devanagari))


def root_record(entry):
    d = entry.dhatu
    return dict(code=entry.code, aupadeshika=d.aupadeshika, gana=enum_name(d.gana),
                artha=entry.artha, antargana=enum_name(d.antargana),
                prefixes=list(d.prefixes), sanadi=[enum_name(s) for s in d.sanadi])


def load_entries():
    require(importlib.metadata.version("vidyut") == VIDYUT_VERSION, "Wrong Vidyut version")
    require(sha256(SOURCE) == SOURCE_SHA256, "Root inventory checksum mismatch")
    with SOURCE.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    usable = {r["code"]: r for r in rows if r["dhatu"] != "-"}
    require(len(rows) == 2259 and len(usable) == 2229, "Unexpected source inventory")
    with tempfile.TemporaryDirectory(prefix="vp-krdanta-source-") as temp:
        shutil.copyfile(SOURCE, Path(temp) / "dhatupatha.tsv")
        entries = sorted(Data(temp).load_dhatu_entries(), key=lambda e: e.code)
    require(len(entries) == len(usable) and {e.code for e in entries} == set(usable),
            "Loader/source inventory mismatch")
    for e in entries:
        require(e.dhatu.aupadeshika == usable[e.code]["dhatu"] and e.artha == usable[e.code]["artha"],
                f"Loader/source mismatch: {e.code}")
        require(not e.dhatu.sanadi, f"Unexpected derived-root operation: {e.code}")
        require(list(e.dhatu.prefixes) == EXPECTED_PREFIXES.get(e.code, []),
                f"Unexpected lexical prefix: {e.code}")
    require(len(Krt.choices()) == 122, "Unexpected engine suffix inventory")
    require(set(SUFFIXES) <= {enum_name(k) for k in Krt.choices()}, "Missing reviewed suffix")
    return entries


def morphology(krt):
    require(krt in SUFFIXES, f"Suffix outside reviewed scope: {krt}")
    result = {"krt": krt}
    if krt in PARTICIPLES:
        # Krdanta::lakara() and prepare_krdanta() supply these defaults in 0.4.0.
        result.update(lakara="Lat", prayoga="Kartari")
    return result


def request(entry, m):
    require(m == morphology(m["krt"]), "Unsupported or missing grammatical conditions")
    return Pratipadika.krdanta(entry.dhatu, getattr(Krt, m["krt"]))


def derive_forms(engine, entry, m):
    return sorted({p.text for p in engine.derive(request(entry, m))})


def valid_gold(forms):
    if not forms or forms != sorted(set(forms)):
        return False
    for form in forms:
        rendered = deva(form)
        if (not form or not rendered or any(not "\u0900" <= c <= "\u097f" for c in rendered)
                or transliterate(rendered, Scheme.Devanagari, Scheme.Slp1) != form):
            return False
    return True


@lru_cache(maxsize=1)
def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def render_task(task):
    """Hydrate a JSON request; gold fields and task ID never enter the prompt."""
    d, m = task["dhatu"], task["morphology"]
    require(m == morphology(m["krt"]), "Unsupported or missing grammatical conditions")
    require(not d["sanadi"], "Sanadi operations are outside this dataset's scope")
    require(d["prefixes"] == EXPECTED_PREFIXES.get(d["code"], []), "Unexpected lexical prefix")
    prefixes = ""
    if d["prefixes"]:
        prefixes = ("upasarga (verbal prefixes to include, in order): "
                    + " + ".join(deva(p) for p in d["prefixes"]) + "\n")
    participle = ""
    if m["krt"] in PARTICIPLES:
        participle = "- lakara (tense): Lat (present)\n- prayoga (voice): Kartari (active)\n"
    return template_text().format(
        aupadeshika_deva=CITATION_OVERRIDES.get(d["aupadeshika"], deva(d["aupadeshika"])),
        gana=d["gana"], gana_en=GANA_EN[d["gana"]], artha_deva=deva(d["artha"]),
        prefixes_block=prefixes, krt_deva=deva(str(getattr(Krt, m["krt"]))),
        krt_en=SUFFIXES[m["krt"]][0], participle_block=participle,
    ).rstrip() + "\n"


def make_record(engine, entry, krt):
    m = morphology(krt)
    forms = derive_forms(engine, entry, m)
    return dict(id=f"krdanta:{entry.code}:{krt}", dhatu=root_record(entry), morphology=m,
                gold_slp1=forms, gold_devanagari=[deva(s) for s in forms])


def prompt_conflicts(records):
    """Exclude every member of identical-prompt groups with different gold sets.

    Dictionary codes/subclasses are provenance, not hidden model inputs. Two
    indistinguishable questions must not have different accepted answers.
    """
    groups = {}
    for row in records:
        prompt_hash = hashlib.sha256(render_task(row).encode("utf-8")).hexdigest()
        groups.setdefault(prompt_hash, []).append(row)
    conflicts = []
    for rows in groups.values():
        if len({tuple(row["gold_devanagari"]) for row in rows}) > 1:
            conflicts.extend(row["id"] for row in rows)
    return sorted(conflicts), len(groups)


def write_array(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="\n") as f:
        f.write("[\n")
        for i, row in enumerate(rows):
            if i:
                f.write(",\n")
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
        f.write("\n]\n")
