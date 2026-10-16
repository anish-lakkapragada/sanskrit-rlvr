#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Resolve MWlexnorm and retain supported VP stem representations; no tasks."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from functools import lru_cache
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata

from vidyut.lipi import Scheme, transliterate

if __package__:
    from . import vp_support
else:
    import vp_support

ROOT = Path(__file__).resolve().parents[3]
FILES = ROOT / "data/engine/files"
SOURCE = FILES / "mw-lexnorm/nominal-entries.csv"
SOURCE_SHA256 = "84797688cfbc3e82260567cf7cca86353acc14b6898f45f279e5a92b4c2b07cc"
REVISION = "34e51125583b1f5026d44e6ef1e44d2a88b73670"
VERSION = "0.4.0"
LIST = "shared-nominal-stems.json"
AUDIT = "shared-nominal-stems.audit.json"
MANIFEST = "shared-nominal-stems.manifest.json"
VP_EXCLUSIONS = "shared-nominal-stems.vp-exclusions.json"
GENDERS = {"m": "masculine", "f": "feminine", "n": "neuter"}
SLP1 = re.compile(r"[aAiIuUfFxXeEoOkKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzshMH]+\Z")
VOWELS = set("aAiIuUfFxXeEoO")
REASONS = {
    "special_lexical_metadata": "LEXID/INFLECTID notation needs a separate interpretation of stems and genders.",
    "indeclinable": "The source lists an indeclinable, not a masculine/feminine/neuter entry.",
    "unsupported_descriptor": "The descriptor is outside the supported gender/hint notation.",
    "invalid_headword_encoding": "The headword is not losslessly renderable SLP1.",
    "unresolved_stem_hint": "The explicit stem hint has no supported replacement rule for this headword.",
    "unresolved_feminine_stem": "This ending needs additional feminine-stem formation rules; do not copy the headword as the feminine stem.",
    "invalid_stem_encoding": "The resolved stem is not losslessly renderable SLP1.",
    "vp_unsupported_input": "The resolved row failed the supported VP representation checks; see vp_reasons and the VP exclusion file.",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=250_000)
def devanagari(stem):
    return unicodedata.normalize("NFC", transliterate(stem, Scheme.Slp1, Scheme.Devanagari))


def valid_stem(stem):
    if not SLP1.fullmatch(stem):
        return False
    text = devanagari(stem)
    return bool(text and all("\u0900" <= c <= "\u097f" for c in text)
                and transliterate(text, Scheme.Devanagari, Scheme.Slp1) == stem)


def read_source():
    require(importlib.metadata.version("vidyut") == VERSION, "Wrong transliteration package version")
    require(sha256(SOURCE) == SOURCE_SHA256, "MWlexnorm source hash changed")
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == 197652, "MWlexnorm row count changed")
    require(len({r["mw_id"] for r in rows}) == len(rows), "Repeated MW ID")
    require([int(r["source_line"]) for r in rows] == list(range(1, len(rows) + 1)),
            "Unexpected source line numbers")
    return rows


def resolve_hint(stem, hint, gender):
    """Explicit replacement rules, following pinned MWlexnorm step1b/stemmodel.py.

    Hints are not arbitrary suffixes to append. Unknown hints remain unresolved.
    Keep this lexical operation independent of either VP task adapter.
    """
    if hint in {"a", "A", "i", "I", "u", "U"}:
        if stem[-1] in VOWELS:
            return stem[:-1] + hint
        if gender == "f" and hint in {"A", "I"}:
            return stem + hint
    if gender != "f":
        return None
    if hint in {"ikA", "akA"} and stem.endswith("aka"):
        return stem[:-3] + "ikA"
    if hint in {"ikA", "ikI"} and stem.endswith("ika"):
        return stem[:-3] + hint
    if hint == "akI" and stem.endswith("aka"):
        return stem[:-3] + hint
    if hint in {"ikA", "akA"} and stem.endswith("a"):
        return stem[:-1] + hint
    replacements = {
        "vI": (("u", "vI"), ("U", "vI")),
        "inI": (("in", "inI"),), "iRI": (("in", "iRI"),),
        "jYI": (("jan", "jYI"),), "jA": (("jan", "jA"),),
        "arI": (("van", "varI"),), "varI": (("van", "varI"),),
        "mnI": (("man", "mnI"),), "GnI": (("han", "GnI"),),
        "trI": (("tf", "trI"),), "rI": (("f", "rI"),),
        "antI": (("at", "antI"),), "ntI": (("at", "antI"),),
        "atI": (("at", "atI"),), "padI": (("pad", "padI"),),
    }
    for ending, replacement in replacements.get(hint, ()):
        if stem.endswith(ending):
            return stem[:-len(ending)] + replacement
    return None


def resolve_descriptor(headword, descriptor):
    """Return (stem, gender, resolution) or an explicit exclusion reason."""
    match = re.fullmatch(r"([mfn])(?:#([^:]+))?", descriptor)
    if not match:
        reason = "indeclinable" if descriptor.split("#")[0] == "ind" else "unsupported_descriptor"
        return None, reason
    if not valid_stem(headword):
        return None, "invalid_headword_encoding"
    gender, hint = match.groups()
    stem, resolution = headword, "headword"
    if hint:
        stem = resolve_hint(stem, hint, gender)
        if stem is None:
            return None, "unresolved_stem_hint"
        resolution = "explicit_hint"
    elif gender == "f":
        if stem.endswith("a"):
            stem, resolution = stem[:-1] + "A", "feminine_a_to_A"
        elif stem.endswith(("n", "at", "vas", "yas", "aYc")):
            # These can require replacement, nasal retroflexion, or derivational
            # metadata. Their masculine/neuter descriptors remain usable here.
            return None, "unresolved_feminine_stem"
    if gender == "n" and stem[-1] in "AIU":
        stem = stem[:-1] + stem[-1].lower()
        resolution += "+neuter_long_vowel_shortening"
    if not valid_stem(stem):
        return None, "invalid_stem_encoding"
    return (stem, GENDERS[gender], resolution), None


def normalize(rows):
    entries, audits = {}, []
    for row in rows:
        source = {**row, "source_line": int(row["source_line"])}
        audit = {**source, "stem_ids": [], "excluded": []}
        if "=" in row["lexnorm"]:
            audit["excluded"].append({"descriptor": row["lexnorm"], "reason": "special_lexical_metadata"})
        else:
            for descriptor in dict.fromkeys(row["lexnorm"].split(":")):
                resolved, reason = resolve_descriptor(row["headword"], descriptor)
                if reason:
                    audit["excluded"].append({"descriptor": descriptor, "reason": reason})
                    continue
                stem, gender, resolution = resolved
                identifier = f"nominal:{stem}:{gender}"
                entry = entries.setdefault(identifier, {
                    "id": identifier, "stem": stem, "stem_devanagari": devanagari(stem),
                    "gender": gender, "sources": [],
                })
                # Each source analysis survives deduplication, including compound
                # notation and alternative feminine hints for the same spelling.
                entry["sources"].append({**source, "descriptor": descriptor, "resolution": resolution})
                if identifier not in audit["stem_ids"]:
                    audit["stem_ids"].append(identifier)
        audit["status"] = ("excluded" if not audit["stem_ids"] else
                           "partial" if audit["excluded"] else "included")
        audits.append(audit)
    entries = [entries[key] for key in sorted(entries)]
    return entries, audits


def validate(entries, audits):
    """Check every source descriptor is accounted for, in both directions."""
    linked, accepted = {}, Counter()
    for entry in entries:
        require(entry["id"] == f"nominal:{entry['stem']}:{entry['gender']}", "Invalid stem ID")
        require(valid_stem(entry["stem"]) and entry["stem_devanagari"] == devanagari(entry["stem"]),
                "Invalid stem transliteration")
        require(entry["sources"], "Stem without provenance")
        for source in entry["sources"]:
            key = (source["mw_id"], source["descriptor"])
            require(key not in linked, "Source descriptor exported twice")
            linked[key] = entry["id"]
            accepted[source["mw_id"]] += 1
    for row in audits:
        descriptors = {row["lexnorm"]} if "=" in row["lexnorm"] else set(row["lexnorm"].split(":"))
        excluded = {item["descriptor"] for item in row["excluded"]}
        require(all(item["reason"] in REASONS for item in row["excluded"]), "Unknown exclusion")
        resolved = {d: linked[(row["mw_id"], d)] for d in descriptors if (row["mw_id"], d) in linked}
        require(not (set(resolved) & excluded) and set(resolved) | excluded == descriptors,
                "Missing or multiply classified source descriptor")
        require(set(resolved.values()) == set(row["stem_ids"]), "Audit has incorrect stem references")
        require(len(resolved) == accepted[row["mw_id"]], "Orphaned source reference")
    require(len({entry["id"] for entry in entries}) == len(entries), "Duplicate stem entry")


def apply_vp_filter(entries, audits, rows):
    kept, removed, constructors = vp_support.filter_entries(entries, rows)
    by_id = {row["mw_id"]: row for row in audits}
    for entry in removed:
        for source in entry["sources"]:
            audit = by_id[source["mw_id"]]
            if entry["id"] in audit["stem_ids"]:
                audit["stem_ids"].remove(entry["id"])
            audit["excluded"].append({
                "descriptor": source["descriptor"], "reason": "vp_unsupported_input",
                "stem_id": entry["id"], "vp_reasons": entry["reasons"],
            })
    for row in audits:
        row["status"] = ("excluded" if not row["stem_ids"] else
                         "partial" if row["excluded"] else "included")
    require(len(kept) + len(removed) == len(entries), "Incomplete VP filter partition")
    return kept, removed, constructors


def write_array(path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("[\n")
        for i, row in enumerate(rows):
            if i:
                stream.write(",\n")
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
        stream.write("\n]\n")


def generate(output_dir=FILES, *, check=False, overwrite=False):
    output_dir = Path(output_dir)
    names = (LIST, AUDIT, VP_EXCLUSIONS, MANIFEST)
    require(check or overwrite or not any((output_dir / name).exists() for name in names),
            "Shared inventory already exists; use --check or --overwrite")
    rows = read_source()
    entries, audits = normalize(rows)
    validate(entries, audits)
    lexical_count = len(entries)
    entries, removed, constructors = apply_vp_filter(entries, audits, rows)
    validate(entries, audits)
    counts = {
        "source_rows": len(rows), "source_row_status": dict(sorted(Counter(r["status"] for r in audits).items())),
        "stem_gender_pairs": len(entries), "distinct_stem_spellings": len({e["stem"] for e in entries}),
        "pairs_by_gender": dict(sorted(Counter(e["gender"] for e in entries).items())),
        "resolved_source_descriptors": sum(len(e["sources"]) for e in entries),
        "source_rows_with_compound_boundaries": sum("-" in r["compound_headword"] for r in rows),
        "compound_rows_with_stems": sum("-" in r["compound_headword"] and bool(r["stem_ids"]) for r in audits),
        "excluded_descriptors_by_reason": dict(sorted(Counter(x["reason"] for r in audits for x in r["excluded"]).items())),
        "vp_filter": {
            "lexical_candidate_pairs": lexical_count, "retained_pairs": len(entries), "removed_pairs": len(removed),
            "retained_by_constructor": dict(sorted(Counter(constructors.values()).items())),
            "removal_reason_events": dict(sorted(Counter(reason for entry in removed for reason in entry["reasons"]).items())),
            "constructor_checks": len(entries) + sum("constructor_failure" in e["reasons"] for e in removed),
        },
    }
    with tempfile.TemporaryDirectory(prefix="shared-nominal-stems-") as tmp:
        build = Path(tmp)
        write_array(build / LIST, entries)
        write_array(build / AUDIT, audits)
        write_array(build / VP_EXCLUSIONS, removed)
        manifest = {
            "schema_version": 2, "inventory": "mwlexnorm-shared-nominal-stems", "generation_complete": True,
            "source": {"path": SOURCE.relative_to(ROOT).as_posix(), "sha256": SOURCE_SHA256,
                       "repository": "https://github.com/funderburkjim/MWlexnorm", "revision": REVISION},
            "generator": {"path": Path(__file__).resolve().relative_to(ROOT).as_posix(), "sha256": sha256(__file__)},
            "vp_filter_code": {"path": Path(vp_support.__file__).resolve().relative_to(ROOT).as_posix(),
                               "sha256": sha256(vp_support.__file__)},
            "transliteration": {"package": "vidyut", "version": VERSION, "input": "SLP1", "output": "NFC Devanagari"},
            "policy": {
                "unit": "One resolved stem spelling and source-listed gender; retain every contributing source analysis.",
                "compound_handling": "Remove any row with a source-marked compound/derivational boundary; the current basic/nyap adapter does not represent it.",
                "feminine_stems": "Resolve supported explicit hints and implicit a-to-A formation; audit unresolved formations.",
                "engine_constructors": "Reviewed basic/nyap classes; every retained row is instantiated in VP 0.4.0 and checked for spelling, flags, and gender-enum mapping.",
                "task_generation": "None. No case-number or 175-affix enumeration, derivations, answers, or prompts.",
                "deduplication": "Stem and gender; a row is removed if any contributing source interpretation is unsupported. Retained rows are unchanged.",
                "validation_limit": "Supported representation in the current adapter, not independent linguistic certification or a guarantee for every taddhita affix. Taddhitanta gender/meaning and known suffix-specific constructor behavior still need task-level validation.",
            },
            "counts": counts, "exclusion_reasons": REASONS,
            "vp_exclusion_reasons": vp_support.REASONS,
            "files": {name: {"sha256": sha256(build / name), "bytes": (build / name).stat().st_size}
                      for name in (LIST, AUDIT, VP_EXCLUSIONS)},
        }
        (build / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if check:
            for name in names:
                require((output_dir / name).is_file() and sha256(output_dir / name) == sha256(build / name),
                        f"Shared inventory differs: {name}")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            # Same-directory staging permits atomic replacement of each artifact;
            # publish the manifest last so hashes detect an interrupted export.
            with tempfile.TemporaryDirectory(prefix=".shared-stems-", dir=output_dir) as stage:
                for name in names:
                    staged = Path(stage) / name
                    shutil.copyfile(build / name, staged)
                    staged.replace(output_dir / name)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=FILES)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Rebuild and compare every artifact without writing")
    mode.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(json.dumps(generate(args.output_dir, check=args.check, overwrite=args.overwrite), indent=2))
