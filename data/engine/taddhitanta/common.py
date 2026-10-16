"""Complete VP suffix inventory, MWlexnorm inputs, and unrestricted prompts."""

from __future__ import annotations

from collections import Counter, deque
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.subanta import common as nominal
from vidyut.prakriya import Taddhita
from data.engine.nominal_stems import inventory
from data.engine.taddhitanta import adapter

OUTPUT = ROOT / "data/datasets/taddhitanta"
TEMPLATE = ROOT / "data/engine/prompts/v2/vp_taddhitanta.txt"
SUFFIXES = tuple(sorted(t.name for t in Taddhita.choices()))
nominal.require(len(SUFFIXES) == 175, "VP suffix inventory changed")


def base_id(stem, nyap, linga):
    return f"taddhitanta:{stem}:{'nyap' if nyap else 'basic'}:{linga}"


def load_bases():
    entries, audits = inventory.for_task("taddhitanta")
    counts = {"bases": len(entries), "nyap_bases": sum(e["is_nyap"] for e in entries),
              "source_rows": len(audits), "gender_policy": "preserve each source-listed gender"}
    return entries, audits, counts


def engine_metadata():
    _, build = adapter.prepare()
    return {"package": "vidyut", "version": nominal.VIDYUT_VERSION, "options": nominal.ENGINE_OPTIONS,
            "request": "Taddhitanta(base, suffix).with_stem_linga(source_gender)", "artha": None,
            "compatibility_build": deepcopy(build)}


def code_files():
    return [Path(__file__), Path(__file__).with_name("generate.py"), Path(nominal.__file__),
            *inventory.CODE, *adapter.CODE]


@lru_cache(maxsize=1)
def suffix_objects():
    return [getattr(Taddhita, name) for name in SUFFIXES]


def derive_base(entry, log_steps=False):
    return derive_chunk(([entry], log_steps, adapter.prepare()[0]))[0]


def derive_chunk(payload):
    entries, log_steps, binary = payload
    requests = [{"id": f"{e['id']}:{suffix}", "stem": e["stem"], "is_nyap": e["is_nyap"],
                 "gender": e["linga"], "suffix": suffix, "artha": None}
                for e in entries for suffix in SUFFIXES]
    responses = adapter.derive(binary, requests, log_steps)
    return [(e["id"], [(suffix, r["forms"], r["error"])
                      for suffix, r in zip(SUFFIXES, responses[i * len(SUFFIXES):(i + 1) * len(SUFFIXES)])])
            for i, e in enumerate(entries)]


def iter_derivations(entries, workers=4, log_steps=False):
    """Build once, batch 64 stems per process, and preserve deterministic order."""
    nominal.require(1 <= workers <= 16, "Use 1–16 workers")
    binary, _ = adapter.prepare()
    chunks = (entries[i:i + 64] for i in range(0, len(entries), 64))
    if workers == 1:
        for chunk in chunks:
            yield from derive_chunk((chunk, log_steps, binary))
        return
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending = deque()
        for _ in range(2 * workers):
            chunk = next(chunks, None)
            if chunk is not None:
                pending.append(pool.submit(derive_chunk, (chunk, log_steps, binary)))
        while pending:
            yield from pending.popleft().result()
            chunk = next(chunks, None)
            if chunk is not None:
                pending.append(pool.submit(derive_chunk, (chunk, log_steps, binary)))


def classify(forms, error):
    if error is not None:
        return "engine_error"
    if not forms:
        return "no_forms"
    if not nominal.valid_gold(forms):
        return "invalid_gold_encoding"
    return "exported"


def make_record(entry, suffix, forms):
    return {
        "id": f"{entry['id']}:{suffix}",
        "pratipadika": {k: entry[k] for k in ("stem", "is_nyap", "linga", "nominal_id", "mw_ids")},
        "morphology": {"taddhita": suffix, "artha": None},
        "gold_slp1": forms, "gold_devanagari": [nominal.deva(s) for s in forms],
    }


@lru_cache(maxsize=1)
def template_text():
    return TEMPLATE.read_text(encoding="utf-8")


def render_task(row):
    base, morph = row["pratipadika"], row["morphology"]
    nominal.require(morph["artha"] is None, "This template is for unrestricted meaning only")
    nominal.require(morph["taddhita"] in SUFFIXES, "Unknown suffix")
    return template_text().format(
        stem_deva=nominal.deva(base["stem"]), suffix_deva=nominal.deva(morph["taddhita"]),
        suffix_id=morph["taddhita"],
        base_interpretation=((f"source gender: {nominal.GENDER_LABELS[base['linga']]}; " if "linga" in base else "") +
                             ("a stem already ending in a nyap feminine suffix" if base["is_nyap"] else
                             "the supplied spelling treated as a basic nominal stem, without a nyap suffix")),
    ).rstrip() + "\n"


def suffix_inventory():
    return [{"id": t.name, "aupadeshika_slp1": str(t), "drshya_slp1": t.drshya(),
             "technical_name_devanagari": nominal.deva(t.name)} for t in suffix_objects()]


def finish_source_audits(entries, audits, exported):
    owners = {e["id"]: e["mw_ids"][0] for e in entries}
    for row in audits:
        row["candidate_tasks"] = len(row["base_ids"]) * len(SUFFIXES)
        row["exported_tasks"] = sum(exported[pid] for pid in row["base_ids"])
        row["new_unique_tasks"] = sum(exported[pid] for pid in row["base_ids"] if owners[pid] == row["mw_id"])
    return {
        "rows": len(audits), "rows_attempted": sum(bool(r["base_ids"]) for r in audits),
        "rows_with_tasks": sum(bool(r["exported_tasks"]) for r in audits),
        "new_unique_tasks": sum(r["new_unique_tasks"] for r in audits),
        "input_exclusion_events": dict(Counter(e for r in audits for e in r["input_exclusions"])),
    }


class JsonArrayWriter:
    def __init__(self, path):
        self.file = Path(path).open("w", encoding="utf-8", newline="\n")
        self.file.write("[\n")
        self.first = True

    def add(self, row):
        if not self.first:
            self.file.write(",\n")
        self.file.write(nominal.compact(row))
        self.first = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.file.write("]\n" if self.first else "\n]\n")
        self.file.close()
