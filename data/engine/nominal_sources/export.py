#!/usr/bin/env python3
"""Export review CSVs from the pinned nominal sources; no VP derivations.

Run with --check to verify the existing exports and their manifest entries.
Source downloads and revisions are recorded in ../files/sources.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


FILES = Path(__file__).resolve().parents[1] / "files"
MW_SOURCE = "mw-lexnorm/lexnorm-all2.txt"
HERITAGE_SOURCE = "sanskrit-heritage/SL_nouns.xml"
GENDERS = {"mas": "m", "fem": "f", "neu": "n", "dei": "dei"}
CASES = {"nom": "1", "acc": "2", "ins": "3", "dat": "4",
         "abl": "5", "gen": "6", "loc": "7", "voc": "8"}
NUMBERS = {"sg": "s", "du": "d", "pl": "p"}


def csv_bytes(columns, rows):
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def export_mw():
    columns = ["source_line", "mw_id", "headword", "compound_headword", "lexnorm"]
    rows = []
    ids = set()
    with (FILES / MW_SOURCE).open(encoding="utf-8", newline="") as f:
        for line, row in enumerate(csv.reader(f, delimiter="\t"), 1):
            if len(row) != 4 or not all(row):
                raise ValueError(f"Unexpected MW row at line {line}: {row!r}")
            if row[0] in ids:
                raise ValueError(f"Repeated MW ID at line {line}: {row[0]}")
            ids.add(row[0])
            rows.append([line, *row])
    stats = {
        "columns": columns,
        "rows": len(rows),
        "distinct_headwords": len({r[2] for r in rows}),
        "rows_with_explicit_feminine_hint": sum("f#" in r[4] for r in rows),
    }
    return csv_bytes(columns, rows), stats


def one_feature(tags, mapping):
    matches = [mapping[tag] for tag in tags if tag in mapping]
    if len(matches) != 1:
        raise ValueError(f"Expected one of {list(mapping)} in {tags}")
    return matches[0]


def export_heritage():
    # Keep homonyms separate and use only genders actually present in <na>.
    # The XML's lexical stem may differ from its feminine inflectional base.
    entries = {}
    num_records = num_analyses = 0
    events = ET.iterparse(FILES / HERITAGE_SOURCE, events=["start", "end"])
    _, root = next(events)
    for event, element in events:
        if event != "end" or element.tag != "f":
            continue
        num_records += 1
        children = list(element)
        if (len(children) < 2 or children[-1].tag != "s"
                or any(c.tag != "na" for c in children[:-1])):
            raise ValueError(f"Unexpected Heritage record {num_records}")
        source_stem = children[-1].attrib["stem"]
        form = element.attrib["form"]
        if not source_stem or not form:
            raise ValueError(f"Empty Heritage record {num_records}")
        for analysis in children[:-1]:
            num_analyses += 1
            tags = [c.tag for c in analysis]
            if len(tags) != 3:
                raise ValueError(f"Unexpected features in record {num_records}: {tags}")
            gender = one_feature(tags, GENDERS)
            case = one_feature(tags, CASES)
            number = one_feature(tags, NUMBERS)
            entry = entries.setdefault((source_stem, gender), {
                "forms": set(), "slots": set(), "nom_sg": set(),
                "acc_sg": set(), "first_record": num_records,
            })
            entry["forms"].add(form)
            entry["slots"].add(case + number)
            if number == "s" and case in {"1", "2"}:
                entry["nom_sg" if case == "1" else "acc_sg"].add(form)
        element.clear()
        root.clear()

    columns = ["source_stem", "headword", "homonym", "gender",
               "nominative_singular", "accusative_singular",
               "observed_case_number_slots", "distinct_forms", "source_first_record"]
    rows = []
    for (source_stem, gender), entry in sorted(entries.items()):
        match = re.fullmatch(r"(.+?)(?:#(\d+))?", source_stem)
        if match is None:
            raise ValueError(f"Unexpected stem: {source_stem}")
        headword, homonym = match.groups()
        rows.append([
            source_stem, headword, homonym or "", gender,
            json.dumps(sorted(entry["nom_sg"]), ensure_ascii=False),
            json.dumps(sorted(entry["acc_sg"]), ensure_ascii=False),
            json.dumps(sorted(entry["slots"])), len(entry["forms"]),
            entry["first_record"],
        ])
    stats = {
        "columns": columns, "rows": len(rows),
        "distinct_source_stems": len({r[0] for r in rows}),
        "distinct_headwords": len({r[1] for r in rows}),
        "source_form_records": num_records, "source_analyses": num_analyses,
        "rows_by_gender": {g: sum(r[3] == g for r in rows)
                           for g in sorted(GENDERS.values())},
        "rows_with_nominative_singular": sum(r[4] != "[]" for r in rows),
    }
    return csv_bytes(columns, rows), stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest_path = FILES / "sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    exports = [
        ("mw-lexnorm/nominal-entries.csv", MW_SOURCE, export_mw,
         "Lossless tab-to-CSV conversion with source line numbers; lexnorm remains unparsed."),
        ("sanskrit-heritage/nominal-entries.csv", HERITAGE_SOURCE, export_heritage,
         "One row per original lexical stem (including homonym) and observed gender. "
         "Includes nominative/accusative singular witnesses, not inferred feminine stems. "
         "Full inflectional evidence remains in the source XML."),
    ]
    outputs = []
    for dest, source, export, note in exports:
        raw = (FILES / source).read_bytes()
        source_meta = manifest["files"][source]
        if hashlib.sha256(raw).hexdigest() != source_meta["sha256"]:
            raise ValueError(f"Source checksum mismatch: {source}")
        content, stats = export()
        meta = {
            "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
            "snapshot_kind": "local_review_export", "derived_from": source,
            "source_sha256": source_meta["sha256"],
            "source_repository": source_meta["source_repository"],
            "source_commit": source_meta["source_commit"],
            "generator": "data/engine/nominal_sources/export.py",
            "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "prepared_on": "2026-10-10", "transformation": note,
            "encoding": "SLP1; source notation and homonym identifiers preserved",
            **stats,
        }
        for key in ("license", "license_file", "license_note"):
            if key in source_meta:
                meta[key] = source_meta[key]
        if args.check:
            if (FILES / dest).read_bytes() != content:
                raise ValueError(f"Export differs: {dest}")
            if manifest["files"][dest] != meta:
                raise ValueError(f"Manifest differs: {dest}")
        outputs.append((dest, content, meta))
        print(json.dumps({"file": dest, **stats}, ensure_ascii=False))
    if not args.check:
        for dest, content, meta in outputs:
            (FILES / dest).write_bytes(content)
            manifest["files"][dest] = meta
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")


if __name__ == "__main__":
    main()
