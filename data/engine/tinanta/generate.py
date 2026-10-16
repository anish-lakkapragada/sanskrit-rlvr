#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Export eligible requests from the pinned classical tiṅanta grid.

Run: uv run --python 3.11 data/engine/tinanta/generate.py
No model calls, random sampling, or train/test split.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.metadata
from itertools import product
import json
from pathlib import Path
import shutil
import tempfile
import time
import unicodedata
import sys

from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Data, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.tinanta.common import (EXCLUSIONS, TEMPLATE, coordinate_exclusion,
                                        prompt_conflicts, render_task, valid_gold)
SOURCE = ROOT / "data/engine/files/vidyut_dhatupatha_5.tsv"
OUTPUT = ROOT / "data/datasets/tinanta"
VIDYUT_VERSION = "0.4.0"
SOURCE_SHA256 = "c6c494a6c534130b2d8e8f344d2f5e3ffbc64ed45b390e2a4e35e526f1cecd09"
EXPECTED_ROOTS = 2229
AXES = {
    "lakara": ["Lat", "Lit", "Lut", "Lrt", "Lot", "Lan", "VidhiLin", "AshirLin", "Lun", "Lrn"],
    "prayoga": ["Kartari", "Karmani", "Bhave"],
    "purusha": ["Prathama", "Madhyama", "Uttama"],
    "vacana": ["Eka", "Dvi", "Bahu"],
}
COORDINATES = tuple(product(*AXES.values()))
ELIGIBLE_COORDINATES = tuple(c for c in COORDINATES if coordinate_exclusion(c) is None)
EXPECTED_CANDIDATES = EXPECTED_ROOTS * len(COORDINATES)
EXPECTED_ELIGIBLE = EXPECTED_ROOTS * len(ELIGIBLE_COORDINATES)
ENGINE_OPTIONS = {
    "log_steps": False,
    "is_chandasi": False,
    "use_svaras": False,
    "nlp_mode": False,
}
FILES = ("full.json", "excluded_tasks.json", "manifest.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def enum_name(value) -> str | None:
    return None if value is None else repr(value).rsplit(".", 1)[-1]


def load_entries():
    """Use the official loader, including entry-number-dependent antargaṇa."""
    version = importlib.metadata.version("vidyut")
    if version != VIDYUT_VERSION:
        raise ValueError(f"Expected vidyut=={VIDYUT_VERSION}, found {version}")
    if sha256(SOURCE) != SOURCE_SHA256:
        raise ValueError("Dhātupāṭha checksum differs from the pinned source")
    with SOURCE.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    usable = {r["code"]: r for r in rows if r["dhatu"] != "-"}
    if len(rows) != 2259 or len(usable) != EXPECTED_ROOTS:
        raise ValueError("Unexpected source inventory size")
    with tempfile.TemporaryDirectory(prefix="vp-tinanta-source-") as directory:
        shutil.copyfile(SOURCE, Path(directory) / "dhatupatha.tsv")
        entries = sorted(Data(directory).load_dhatu_entries(), key=lambda e: e.code)
    if len(entries) != EXPECTED_ROOTS or {e.code for e in entries} != set(usable):
        raise ValueError("Official loader did not preserve the source entry inventory")
    for entry in entries:
        row = usable[entry.code]
        if entry.dhatu.aupadeshika != row["dhatu"] or entry.artha != row["artha"]:
            raise ValueError(f"Loader/source mismatch for {entry.code}")
    for key, cls in [("lakara", Lakara), ("prayoga", Prayoga),
                     ("purusha", Purusha), ("vacana", Vacana)]:
        actual = {enum_name(x) for x in cls.choices()}
        expected = set(AXES[key]) | ({"Let"} if key == "lakara" else set())
        if actual != expected:
            raise ValueError(f"Unexpected VP options for {key}: {actual}")
    return entries


def request(entry, coordinate):
    lakara, prayoga, purusha, vacana = coordinate
    return Pada.Tinanta(
        dhatu=entry.dhatu,
        lakara=getattr(Lakara, lakara),
        prayoga=getattr(Prayoga, prayoga),
        purusha=getattr(Purusha, purusha),
        vacana=getattr(Vacana, vacana),
        dhatu_pada=None,
        skip_at_agama=False,
    )


def derive_forms(engine, entry, coordinate):
    return sorted({p.text for p in engine.derive(request(entry, coordinate))})


def to_devanagari(text: str) -> str:
    return unicodedata.normalize("NFC", transliterate(text, Scheme.Slp1, Scheme.Devanagari))


def make_record(engine, entry, coordinate):
    if coordinate_exclusion(coordinate):
        raise ValueError("Invalid bhave coordinate must not reach the engine")
    dhatu = entry.dhatu
    record = {
        "id": ":".join((entry.code, *coordinate)),
        "dhatu": {
            "code": entry.code,
            "aupadeshika": dhatu.aupadeshika,
            "gana": enum_name(dhatu.gana),
            "artha": entry.artha,
            "antargana": enum_name(dhatu.antargana),
            "prefixes": list(dhatu.prefixes),
            "sanadi": [enum_name(s) for s in dhatu.sanadi],
        },
        "morphology": dict(zip(AXES, coordinate)),
        "gold_slp1": [],
        "gold_devanagari": [],
        "status": "no_forms",
        "warnings": [],
    }
    try:
        forms = derive_forms(engine, entry, coordinate)
        if any(not form for form in forms):
            raise ValueError("VP returned an empty surface form")
    except BaseException as exc:
        # PyO3 Rust panics use a BaseException subclass. Preserve them as errors,
        # but never swallow Ctrl-C, SystemExit, or unrelated BaseExceptions.
        if not isinstance(exc, Exception) and type(exc).__name__ != "PanicException":
            raise
        record["status"] = "error"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        return record
    record["gold_slp1"] = forms
    record["gold_devanagari"] = [to_devanagari(f) for f in forms]
    record["status"] = "ok" if forms else "no_forms"
    return record


class JsonArrayWriter:
    """A normal JSON array, streamed as one compact record per line."""

    def __init__(self, path):
        self.file = path.open("w", encoding="utf-8", newline="\n")
        self.file.write("[")
        self.count = 0

    def write(self, record):
        self.file.write(",\n" if self.count else "\n")
        self.file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        self.count += 1

    def close(self):
        self.file.write("\n]\n" if self.count else "]\n")
        self.file.close()


def sanity_checks(engine, entries):
    by_code = {e.code: e for e in entries}
    coordinate = ("Lat", "Kartari", "Prathama", "Eka")
    for code, expected in [("01.0001", ["Bavati"]), ("01.0005", ["bADate"]),
                           ("10.0192", ["cetayate"])]:
        actual = derive_forms(engine, by_code[code], coordinate)
        if actual != expected:
            raise ValueError(f"Sanity check failed for {code}: {actual} != {expected}")


def generate(output: Path, overwrite: bool = False):
    output = output.resolve()
    existing = [name for name in FILES if (output / name).exists()]
    if existing and not overwrite:
        raise FileExistsError(f"Already exported: {existing}; use --output or --overwrite")
    entries = load_entries()
    engine = Vyakarana(**ENGINE_OPTIONS)
    sanity_checks(engine, entries)
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    statuses = Counter({"ok": 0, "no_forms": 0, "error": 0})
    excluded = Counter({reason: 0 for reason in EXCLUSIONS})
    multiplicities = Counter()
    per_lakara = {name: Counter({"ok": 0, "no_forms": 0, "error": 0}) for name in AXES["lakara"]}
    per_prayoga = {name: Counter({"ok": 0, "no_forms": 0, "error": 0}) for name in AXES["prayoga"]}
    with tempfile.TemporaryDirectory(prefix=".tinanta-build-", dir=output.parent) as temp:
        build = Path(temp)
        candidates = JsonArrayWriter(build / "eligible.json")
        exclusions = JsonArrayWriter(build / "excluded_tasks.json")
        # Only roots whose visible input is identical can produce conflicting
        # prompts. Retain those few records for comparison, not the full grid.
        root_groups = defaultdict(list)
        for entry in entries:
            d = entry.dhatu
            dummy = {"dhatu": {"aupadeshika": d.aupadeshika, "gana": enum_name(d.gana),
                               "artha": entry.artha, "prefixes": list(d.prefixes), "sanadi": []},
                     "morphology": dict(zip(AXES, ELIGIBLE_COORDINATES[0]))}
            root_groups[render_task(dummy)].append(entry.code)
        duplicate_codes = {code for group in root_groups.values() if len(group) > 1 for code in group}
        duplicate_rows = []
        attempted = 0
        try:
            for index, entry in enumerate(entries, 1):
                for coordinate in COORDINATES:
                    reason = coordinate_exclusion(coordinate)
                    task_id = ":".join((entry.code, *coordinate))
                    if reason:
                        exclusions.write({"id": task_id, "reason": reason})
                        excluded[reason] += 1
                        continue
                    attempted += 1
                    record = make_record(engine, entry, coordinate)
                    if record["status"] == "error":
                        raise RuntimeError(f"Engine failure at {task_id}: {record['error']}")
                    reason = ("no_forms" if not record["gold_slp1"] else
                              "invalid_gold_encoding" if not valid_gold(record["gold_slp1"]) else None)
                    if reason:
                        exclusions.write({"id": task_id, "reason": reason})
                        excluded[reason] += 1
                        continue
                    candidates.write(record)
                    if entry.code in duplicate_codes:
                        duplicate_rows.append(record)
                if index % 100 == 0 or index == len(entries):
                    print(f"{index}/{len(entries)} roots; {attempted:,}/{EXPECTED_ELIGIBLE:,} VP requests; "
                          f"{time.monotonic() - started:.1f}s", flush=True)
        except BaseException:
            exclusions.close()
            raise
        finally:
            candidates.close()
        conflicts = set(prompt_conflicts(duplicate_rows))
        all_rows = JsonArrayWriter(build / "full.json")
        prompt_digest = hashlib.sha256()
        try:
            with (build / "eligible.json").open() as records:
                next(records)
                for line in records:
                    if line.strip() == "]":
                        break
                    record = json.loads(line.rstrip().removesuffix(","))
                    if record["id"] in conflicts:
                        exclusions.write({"id": record["id"], "reason": "ambiguous_prompt"})
                        excluded["ambiguous_prompt"] += 1
                        continue
                    all_rows.write(record)
                    statuses["ok"] += 1
                    multiplicities[len(record["gold_slp1"])] += 1
                    per_lakara[record["morphology"]["lakara"]]["ok"] += 1
                    per_prayoga[record["morphology"]["prayoga"]]["ok"] += 1
                    prompt_digest.update((json.dumps([record["id"], render_task(record)],
                                          ensure_ascii=False, separators=(",", ":")) + "\n").encode())
        finally:
            all_rows.close()
            exclusions.close()
        if attempted != EXPECTED_ELIGIBLE or all_rows.count + sum(excluded.values()) != EXPECTED_CANDIDATES:
            raise ValueError("Incomplete candidate accounting")
        manifest = {
            "schema_version": 2,
            "dataset": "vp-tinanta-reviewed-v2",
            "generation_complete": True,
            "has_engine_errors": bool(statuses["error"]),
            "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": SOURCE_SHA256,
                       "rows": 2259, "placeholders_excluded": 30, "roots": len(entries),
                       "loader_supplied_prefixes": {e.code: list(e.dhatu.prefixes)
                                                   for e in entries if e.dhatu.prefixes}},
            "generator": {"path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
                          "sha256": sha256(Path(__file__))},
            "eligibility_and_rendering": {"path": "data/engine/tinanta/common.py",
                                          "sha256": sha256(Path(__file__).with_name("common.py"))},
            "prompt": {"path": TEMPLATE.relative_to(ROOT).as_posix(), "sha256": sha256(TEMPLATE),
                       "rendered_sequence_sha256": prompt_digest.hexdigest(),
                       "sequence_format": "compact UTF-8 JSON [id,prompt] plus newline per record"},
            "engine": {"package": "vidyut", "version": VIDYUT_VERSION,
                       "options": ENGINE_OPTIONS,
                       "dhatu_loader": "Data.load_dhatu_entries",
                       "fixed_request_options": {"additional_prefixes": [], "additional_sanadi": [],
                                                 "dhatu_pada": None, "skip_at_agama": False}},
            "coordinate_space": AXES,
            "enumeration_order": "dictionary code ascending; lakara, prayoga, purusha, vacana in listed order",
            "gold_order": "unique SLP1 forms sorted lexicographically; paired NFC Devanagari forms",
            "sampling": None,
            "splits": None,
            "counts": {"roots": len(entries), "candidate_coordinates_per_root": len(COORDINATES),
                       "coordinates_per_root": len(ELIGIBLE_COORDINATES),
                       "candidates": EXPECTED_CANDIDATES, "attempted": attempted,
                       "all": all_rows.count, "full": all_rows.count, "answerable": statuses["ok"],
                       "excluded_tasks": exclusions.count, "excluded_by_reason": dict(excluded),
                       "status": dict(statuses), "warnings": {},
                       "gold_forms_per_task": {str(k): v for k, v in sorted(multiplicities.items())}},
            "by_lakara": per_lakara,
            "by_prayoga": per_prayoga,
            "status_definitions": {
                "ok": "VP returned at least one surface form; not independent linguistic validation",
                "no_forms": "VP completed normally and returned no forms",
                "error": "VP request or derivation raised an exception; abort publication"},
            "exclusion_definitions": EXCLUSIONS,
            "answerable_filter": "Eligible bhave coordinates; nonempty, lossless gold; no conflicting identical prompts. Exclusions are audited separately.",
            "scope_limits": "These checks remove known representation and coordinate problems; VP output is not independent grammatical certification.",
            "files": {name: {"records": writer.count, "bytes": (build / name).stat().st_size,
                             "sha256": sha256(build / name)}
                      for name, writer in [("full.json", all_rows), ("excluded_tasks.json", exclusions)]},
        }
        (build / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Publish the manifest last. No half-written array is exposed as an export.
        for name in FILES:
            (build / name).replace(output / name)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    generate(args.output, args.overwrite)


if __name__ == "__main__":
    main()
