"""Read the shared, filtered inventory without reinterpreting dictionary rows."""

import importlib.metadata
import json
from pathlib import Path

from data.engine.nominal_stems import vp_support
from data.engine.subanta import common as nominal

FILES = Path(__file__).resolve().parents[1] / "files"
STEMS = FILES / "shared-nominal-stems.json"
AUDIT = FILES / "shared-nominal-stems.audit.json"
MANIFEST = FILES / "shared-nominal-stems.manifest.json"
CODE = (Path(__file__), Path(vp_support.__file__))


def source_metadata():
    nominal.require(importlib.metadata.version("vidyut") == nominal.VIDYUT_VERSION,
                    "Use the pinned vidyut version for shared nominal tasks")
    manifest = json.loads(MANIFEST.read_text())
    nominal.require(manifest["generation_complete"] and manifest["schema_version"] == 2,
                    "Rebuild the filtered shared nominal inventory first")
    nominal.require(manifest["source"]["sha256"] == nominal.SOURCE_SHA256, "Unexpected lexical source")
    for path in (STEMS, AUDIT):
        nominal.require(nominal.sha256(path) == manifest["files"][path.name]["sha256"],
                        f"Shared inventory changed: {path.name}")
    nominal.require(nominal.sha256(vp_support.__file__) == manifest["vp_filter_code"]["sha256"],
                    "Shared input adapter changed; rebuild the inventory first")
    return {"path": STEMS.relative_to(nominal.ROOT).as_posix(), "sha256": nominal.sha256(STEMS),
            "manifest_sha256": nominal.sha256(MANIFEST), "audit_sha256": nominal.sha256(AUDIT),
            "lexical_sources": ["MWlexnorm"], "upstream": manifest["source"],
            "rows": manifest["counts"]["source_rows"],
            "stem_gender_pairs": manifest["counts"]["stem_gender_pairs"], "encoding": "SLP1"}


def load():
    metadata = source_metadata()
    entries = list(nominal.iter_array(STEMS))
    audits = list(nominal.iter_array(AUDIT))
    nominal.require(len(entries) == metadata["stem_gender_pairs"] and len(audits) == metadata["rows"],
                    "Shared inventory count mismatch")
    nominal.require(len({e["id"] for e in entries}) == len(entries), "Duplicate shared stem ID")
    context = vp_support.source_context(audits)
    inputs = []
    for entry in entries:
        constructor, reasons = vp_support.select_constructor(entry, context)
        nominal.require(not reasons, f"Unsupported shared input {entry['id']}: {reasons}")
        vp_support.construct(entry, constructor)
        inputs.append({"nominal_id": entry["id"], "stem": entry["stem"], "gender": entry["gender"],
                       "linga": vp_support.GENDERS[entry["gender"]], "is_nyap": constructor == "nyap",
                       "mw_ids": list(dict.fromkeys(s["mw_id"] for s in
                                       sorted(entry["sources"], key=lambda s: s["source_line"])))})
    return inputs, audits


def for_task(family):
    nominal.require(family in {"subanta", "taddhitanta"}, "Unknown nominal task family")
    entries, audits = load()
    ids = {}
    for entry in entries:
        entry["id"] = f"{family}:{entry['stem']}:{'nyap' if entry['is_nyap'] else 'basic'}:{entry['linga']}"
        ids[entry["nominal_id"]] = entry["id"]
    for audit in audits:
        task_ids = sorted(ids[s] for s in audit.pop("stem_ids"))
        if family == "subanta":
            audit["paradigm_ids"] = task_ids
        else:
            audit["base_ids"] = task_ids
            if "status" in audit:
                audit["input_status"] = audit.pop("status")
            audit["input_exclusions"] = sorted({e["reason"] for e in audit["excluded"]})
    return sorted(entries, key=lambda e: e["id"]), audits
