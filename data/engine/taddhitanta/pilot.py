#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Bounded MWlexnorm taddhitanta diagnostics. Never creates a full.json export."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.subanta import common as nominal
from vidyut.prakriya import Pratipadika, Taddhita, Vyakarana

from rust_probe import derive, prepare

HERE = Path(__file__).resolve().parent
OUTPUT = ROOT / "data/datasets/taddhitanta/pilot"
TEMPLATE = ROOT / "data/engine/prompts/v2/vp_taddhitanta_pilot.txt"
MEANINGS = {
    "TasyaBhava": "the state or quality of being the base (tasya bhavah)",
    "TadAsyaAstiAsmin": "having the base, or having the base present in it (tad asya asti asmin)",
    "TasyaApatyam": "a descendant of the base",
    "TenaRaktam": "dyed with the base",
    "TatraBhava": "existing or occurring in the base",
    "TasyaSamuha": "a collection of the base",
}
MEANING_SUFFIXES = ("tva", "tal", "matup", "aR", "imanic", "yat", "Wak", "WaY", "Iyasun", "izWan")
PREVIEW_SCOPE = {"tva": "TasyaBhava", "tal": "TasyaBhava", "matup": "TadAsyaAstiAsmin"}
ANCHORS = ("guru", "gurvI", "deva", "devI", "Dana", "aSva", "go", "nO", "pfTu", "mfdu",
           "Sukla", "rAjan", "rAjYI", "Atman", "nAman", "yogin", "manas", "payas", "yaSas",
           "maDu", "strI", "lakzmI", "kumArI", "cUqA", "yava", "vfkza", "Pena", "uras",
           "loman", "mAsa", "samA", "mitrayu", "udara", "kfzI", "alpa", "vfdDa", "praSasya",
           "antika", "bAQa", "kanaka", "vatsa", "mAyA", "meDA")

# Expected forms come from the pinned engine's upstream integration tests.
# Explicit meanings on formerly unscoped tests are deliberate capability probes.
# A failure is a finding; it must not be silently converted to a passing check.
REFERENCES = [
    ("aSva", False, "tva", "TasyaBhava", ["aSvatva"], "kashika_5_1.rs::sutra_5_1_119"),
    ("aSva", False, "tal", "TasyaBhava", ["aSvatA"], "kashika_5_1.rs::sutra_5_1_119"),
    ("go", False, "tva", "TasyaBhava", ["gotva"], "kashika_5_1.rs::sutra_5_1_119"),
    ("go", False, "tal", "TasyaBhava", ["gotA"], "kashika_5_1.rs::sutra_5_1_119"),
    ("pfTu", False, "imanic", "TasyaBhava", ["praTiman"], "kashika_5_1.rs::sutra_5_1_122"),
    ("mfdu", False, "imanic", "TasyaBhava", ["mradiman"], "kashika_5_1.rs::sutra_5_1_122"),
    ("pfTu", False, "aR", "TasyaBhava", ["pArTava"], "kashika_5_1.rs::sutra_5_1_122"),
    ("mfdu", False, "aR", "TasyaBhava", ["mArdava"], "kashika_5_1.rs::sutra_5_1_122"),
    ("go", False, "matup", "TadAsyaAstiAsmin", ["gomat"], "kashika_5_2.rs::sutra_5_2_94"),
    ("vfkza", False, "matup", "TadAsyaAstiAsmin", ["vfkzavat"], "kashika_5_2.rs::sutra_5_2_94"),
    ("yava", False, "matup", "TadAsyaAstiAsmin", ["yavamat"], "kashika_5_2.rs::sutra_5_2_94"),
    ("cUqA", True, "matup", "TadAsyaAstiAsmin", ["cUqAvat"], "kashika_5_2.rs::sutra_5_2_96"),
    ("Pena", False, "matup", "TadAsyaAstiAsmin", ["Penavat"], "kashika_5_2.rs::sutra_5_2_99"),
    ("loman", False, "matup", "TadAsyaAstiAsmin", ["lomavat"], "kashika_5_2.rs::sutra_5_2_100"),
    ("uras", False, "matup", "TadAsyaAstiAsmin", ["urasvat"], "kashika_5_2.rs::sutra_5_2_100"),
    ("yaSas", False, "vini", "TadAsyaAstiAsmin", ["yaSasvin"], "kashika_5_2.rs::sutra_5_2_121"),
    ("mAyA", True, "vini", "TadAsyaAstiAsmin", ["mAyAvin"], "kashika_5_2.rs::sutra_5_2_121"),
    ("mAsa", False, "yat", "Vayasi", ["mAsya"], "kashika_5_1.rs::sutra_5_1_81"),
    ("mAsa", False, "WaY", "TenaNirvrttam", ["mAsika"], "kashika_5_1.rs::sutra_5_1_81"),
    ("samA", True, "WaY", "TamAdhisteBhrtoBhutoBhavi", [], "kashika_5_1.rs::sutra_5_1_85"),
    ("samA", True, "Ka", "TamAdhisteBhrtoBhutoBhavi", ["samIna"], "kashika_5_1.rs::sutra_5_1_85"),
    ("udara", False, "kan", "TatraAdyuna", [], "kashika_5_2.rs::sutra_5_2_67"),
    ("aSva", False, "tva", "TadAsyaAstiAsmin", [], "negative control: abstract suffix in possession context"),
    ("go", False, "matup", "TasyaBhava", [], "negative control: possession suffix in abstract context"),
]


def normalized_bases():
    entries, audits = nominal.normalize_source()
    bases = {}
    for entry in entries:
        key = entry["stem"], entry["is_nyap"]
        base = bases.setdefault(key, {
            "id": f"base:{key[0]}:{'nyap' if key[1] else 'basic'}", "stem": key[0], "is_nyap": key[1],
            "mw_ids": [], "source_genders": [],
        })
        for mw_id in entry["mw_ids"]:
            if mw_id not in base["mw_ids"]:
                base["mw_ids"].append(mw_id)
        if entry["linga"] not in base["source_genders"]:
            base["source_genders"].append(entry["linga"])
    for base in bases.values():
        base["mw_ids"].sort(key=lambda s: float(s))
        base["source_genders"].sort()
    return sorted(bases.values(), key=lambda b: b["id"]), len(audits)


def stratum(base):
    stem = base["stem"]
    if base["is_nyap"]:
        return "nyap_" + stem[-1]
    if stem.endswith(("an", "in")):
        return "nasal"
    if stem.endswith(("as", "is", "us")):
        return "s_stem"
    if stem[-1] in "aiuf":
        return "vowel_" + stem[-1]
    return "other"


def sample_bases(pool, size):
    nominal.require(64 <= size <= 256, "Pilot size must be 64–256 bases; full export is not implemented")
    rank = lambda base: hashlib.sha256(("taddhitanta-pilot-v1:" + base["id"]).encode()).hexdigest()
    chosen = {b["id"]: b for b in pool if b["stem"] in ANCHORS}
    missing = sorted(set(ANCHORS) - {b["stem"] for b in chosen.values()})
    strata = defaultdict(list)
    for base in pool:
        strata[stratum(base)].append(base)
    for values in strata.values():
        for base in sorted(values, key=rank)[:2]:
            chosen[base["id"]] = base
    nominal.require(len(chosen) <= size, "Pilot size too small for anchors and stem-type coverage")
    for base in sorted(pool, key=rank):
        if len(chosen) == size:
            break
        chosen[base["id"]] = base
    return sorted(chosen.values(), key=lambda b: b["id"]), missing


def request(base, suffix, artha, prefix="grid"):
    return {"id": f"{prefix}:{base['id']}:{suffix}:{artha or 'unspecified'}",
            "stem": base["stem"], "is_nyap": base["is_nyap"], "suffix": suffix, "artha": artha}


def python_forms(base, suffix, engine):
    stem = (Pratipadika.nyap if base["is_nyap"] else Pratipadika.basic)(base["stem"])
    return sorted({p.text for p in engine.derive(Pratipadika.taddhitanta(stem, getattr(Taddhita, suffix)))})


def preview_record(base, suffix, artha, forms):
    nominal.require(preview_exclusion(base, suffix, artha) is None, "Outside provisional preview scope")
    return {
        "id": f"taddhitanta:{base['stem']}:{'nyap' if base['is_nyap'] else 'basic'}:{suffix}:{artha}",
        "pratipadika": {k: base[k] for k in ("stem", "is_nyap", "mw_ids")},
        "morphology": {"taddhita": suffix, "artha": artha},
        "gold_slp1": forms, "gold_devanagari": [nominal.deva(s) for s in forms],
    }


def preview_exclusion(base, suffix, artha):
    if PREVIEW_SCOPE.get(suffix) != artha:
        return "unreviewed_suffix_or_meaning"
    if suffix == "matup" and base["is_nyap"]:
        return "feminine_taddhita_constructor_unreviewed"
    return None


def render_task(row):
    base, morph = row["pratipadika"], row["morphology"]
    nominal.require(preview_exclusion(base, morph["taddhita"], morph["artha"]) is None,
                    "Outside pilot prompt scope")
    return TEMPLATE.read_text().format(
        stem_deva=nominal.deva(base["stem"]), suffix_deva=nominal.deva(morph["taddhita"]),
        suffix_id=morph["taddhita"], artha_description=MEANINGS[morph["artha"]],
        base_interpretation=("a feminine stem ending in a nyap suffix (already formed)" if base["is_nyap"]
                             else "a basic nominal stem, without a nyap feminine suffix"),
    )


def run(output=OUTPUT, size=96, check=False):
    started = time.monotonic()
    output = Path(output)
    pool, source_rows = normalized_bases()
    sample, missing_anchors = sample_bases(pool, size)
    by_key = {(b["stem"], b["is_nyap"]): b for b in pool}
    binary, source, build_metadata = prepare()
    suffixes = sorted(t.name for t in Taddhita.choices())
    nominal.require(len(suffixes) == 175, "Pinned suffix inventory changed")
    requests = [request(b, s, None) for b in sample for s in suffixes]
    requests += [request(b, s, a) for b in sample for s in MEANING_SUFFIXES for a in MEANINGS]
    for i, (stem, nyap, suffix, artha, _, _) in enumerate(REFERENCES):
        nominal.require((stem, nyap) in by_key, f"Reference stem not resolved from MWlexnorm: {stem}/{nyap}")
        requests.append(request(by_key[stem, nyap], suffix, artha, f"reference-{i}"))
        if nyap:
            requests.append(request({**by_key[stem, nyap], "is_nyap": False}, suffix, artha,
                                    f"reference-basic-{i}"))
    # Deliberately change the constructor on sampled feminine stems. These
    # are diagnostics, not additional licensed MWlexnorm task inputs.
    for base in sample:
        if base["is_nyap"]:
            for suffix in MEANING_SUFFIXES:
                requests.append(request({**base, "is_nyap": False}, suffix, None, "constructor-control"))
    nominal.require(len({r["id"] for r in requests}) == len(requests), "Duplicate diagnostic request IDs")
    print(f"Pilot: {size} bases × {len(suffixes)} suffixes, plus meaning and reference controls; "
          f"{len(requests):,} Rust requests", flush=True)
    responses = derive(binary, requests)
    replay = derive(binary, requests, log_steps=True)
    nominal.require(responses == replay, "Rust results changed when enabling derivation history")
    lookup = {r["id"]: r for r in responses}
    engine = Vyakarana(**nominal.ENGINE_OPTIONS)
    observations, differences, invalid = [], [], []
    counts = Counter()
    by_suffix = {suffix: Counter() for suffix in suffixes}
    for req, response in zip(requests, responses):
        forms = response["forms"]
        if forms and not nominal.valid_gold(forms):
            invalid.append(req["id"])
        row = {**req, "forms_slp1": forms, "forms_devanagari": [nominal.deva(f) for f in forms],
               "resulting_meanings": response["resulting_meanings"]}
        if req["id"].startswith("grid:"):
            kind = "unscoped" if req["artha"] is None else "meaning_scoped"
            counts[kind + "_requests"] += 1
            counts[kind + ("_nonempty" if forms else "_empty")] += 1
            if req["artha"] is None:
                row["python_forms_slp1"] = python_forms(req, req["suffix"], engine)
                if row["python_forms_slp1"] != forms:
                    differences.append(row["id"])
                by_suffix[req["suffix"]]["nonempty" if forms else "empty"] += 1
        observations.append(row)
    reference_results = []
    for i, (stem, nyap, suffix, artha, expected, evidence) in enumerate(REFERENCES):
        base = by_key[stem, nyap]
        req = request(base, suffix, artha, f"reference-{i}")
        actual = lookup[req["id"]]["forms"]
        reference_results.append({**req, "mw_ids": base["mw_ids"], "expected": sorted(expected),
                                  "actual": actual, "passed": actual == sorted(expected), "evidence": evidence,
                                  "test_kind": "adapter check against upstream example, with explicit meaning",
                                  "basic_constructor_forms": (lookup[request({**base, "is_nyap": False}, suffix,
                                      artha, f"reference-basic-{i}")["id"]]["forms"] if nyap else None),
                                  "unscoped_python": python_forms(base, suffix, engine)})

    semantic_changes, constructor_changes = [], []
    for base in sample:
        for suffix in MEANING_SUFFIXES:
            unscoped = lookup[request(base, suffix, None)["id"]]["forms"]
            for artha in MEANINGS:
                scoped = lookup[request(base, suffix, artha)["id"]]["forms"]
                if unscoped != scoped:
                    semantic_changes.append({"base_id": base["id"], "suffix": suffix, "artha": artha,
                                             "unscoped": unscoped, "scoped": scoped})
            if base["is_nyap"]:
                wrong = request({**base, "is_nyap": False}, suffix, None, "constructor-control")
                other = lookup[wrong["id"]]["forms"]
                if unscoped != other:
                    constructor_changes.append({"base_id": base["id"], "suffix": suffix,
                                                "nyap": unscoped, "basic": other})

    preview, prompts, preview_exclusions = [], {}, []
    for base in sample:
        for suffix, artha in PREVIEW_SCOPE.items():
            reason = preview_exclusion(base, suffix, artha)
            if reason:
                preview_exclusions.append({"base_id": base["id"], "suffix": suffix, "artha": artha, "reason": reason})
                continue
            forms = lookup[request(base, suffix, artha)["id"]]["forms"]
            if not forms or not nominal.valid_gold(forms):
                continue
            row = preview_record(base, suffix, artha, forms)
            prompt = render_task(row)
            nominal.require(prompt not in prompts or prompts[prompt] == forms, "Conflicting pilot prompts")
            prompts[prompt] = forms
            preview.append(row)
    # API capability check: do not silently display an artha that Python drops.
    try:
        Pratipadika.taddhitanta(Pratipadika.basic("guru"), Taddhita.tva, artha="TasyaBhava")
    except TypeError:
        rejects_artha = True
    else:
        rejects_artha = False
    nominal.require(rejects_artha, "Re-review Python API: artha signature changed")

    scoped_counts = {}
    for suffix, artha in PREVIEW_SCOPE.items():
        accepted = sum(bool(lookup[request(b, suffix, artha)["id"]]["forms"]) for b in sample)
        scoped_counts[suffix] = {"artha": artha, "requests": size, "nonempty": accepted,
                                 "empty": size - accepted,
                                 "preview_retained": sum(r["morphology"]["taddhita"] == suffix for r in preview)}
    source_paths = ["bindings-python/src/prakriya/args.rs", "vidyut-prakriya/src/taddhita/utils.rs",
                    "vidyut-prakriya/src/taddhita/nan_snan_adhikara_prakarana.rs",
                    "vidyut-prakriya/src/taddhita/pragiviya.rs",
                   "vidyut-prakriya/tests/integration/kashika_5_1.rs",
                    "vidyut-prakriya/tests/integration/kashika_5_2.rs",
                    "vidyut-prakriya/test_utils/src/lib.rs"]
    report = {
        "schema_version": 1, "kind": "preliminary_engine_diagnostics", "full_export_created": False,
        "lexical_source": {"name": "MWlexnorm", "revision": nominal.SOURCE_REVISION,
                           "path": nominal.SOURCE.relative_to(ROOT).as_posix(),
                           "sha256": nominal.SOURCE_SHA256, "rows": source_rows},
        "engine": {"python_version": nominal.VIDYUT_VERSION, "options": nominal.ENGINE_OPTIONS,
                   "rust_build": build_metadata, "upstream_evidence": {p: nominal.sha256(source / p) for p in source_paths}},
        "sampling": {"pool": "MWlexnorm stems supported by the existing subanta normalizer, deduplicated across genders",
                     "eligible_bases": len(pool), "selected_bases": size,
                     "method": "named regression anchors + two hash-ranked bases per stem type + deterministic hash fill",
                     "seed": "taddhitanta-pilot-v1", "strata": dict(sorted(Counter(stratum(b) for b in sample).items())),
                     "missing_anchors": missing_anchors, "representative_of_all_mwlexnorm": False},
        "counts": {**dict(counts), "rust_requests": len(requests), "rust_rederived": len(replay),
                   "python_rust_mismatches": len(differences), "invalid_gold_encoding": len(invalid),
                   "meaning_changes": len(semantic_changes), "constructor_changes": len(constructor_changes),
                   "reference_checks": len(reference_results),
                   "reference_passed": sum(r["passed"] for r in reference_results),
                   "reference_failed": sum(not r["passed"] for r in reference_results),
                   "preview_tasks": len(preview), "preview_scope_exclusions": len(preview_exclusions),
                   "engine_errors": 0},
        "python_accepts_artha": not rejects_artha,
        "readiness": {"full_export": "hold_for_adapter_and_suffix_review",
                      "recommended_first_scope": ["tva + TasyaBhava", "tal + TasyaBhava"],
                      "conditional_extension": "matup + TadAsyaAstiAsmin on non-nyap bases only",
                      "defer": ["feminine nyap + matup", "aR abstraction with TasyaBhava",
                                "comparatives without lexical category review", "unrestricted 175-suffix export"]},
        "reference_results": reference_results, "candidate_scope": scoped_counts,
        "unscoped_suffix_coverage": {k: dict(v) for k, v in sorted(by_suffix.items())},
        "mismatched_ids": differences, "invalid_encoding_ids": invalid,
        "limitations": [
            "Nonempty engine output is not a linguistic validity judgment or an LLM accuracy score.",
            "MWlexnorm does not provide the semantic categories needed for unrestricted suffix application.",
            "Sampled stems inherit the conservative subanta adapter; this is not an exhaustive taddhita eligibility audit.",
            "Explicit meaning mismatches and failed reference checks remain visible; they are not silently treated as invalid Sanskrit.",
            "Preview tasks are provisional: tva/tal abstraction, and matup possession only on bases without nyap.",
            "All feminine nyap + matup requests are withheld after the cUqA reference failure; no universal basic-constructor workaround is assumed.",
        ],
    }
    artifacts = {
        "bases.json": sample, "observations.json": observations, "reference_checks.json": reference_results,
        "meaning_changes.json": semantic_changes, "constructor_changes.json": constructor_changes,
        "pilot_tasks.json": preview, "preview_exclusions.json": preview_exclusions, "report.json": report,
    }
    code_paths = [HERE / name for name in ("pilot.py", "rust_probe.py", "probe.rs", "probe.Cargo.lock")]
    code_paths.append(Path(nominal.__file__))
    with tempfile.TemporaryDirectory(prefix="taddhitanta-pilot-output-") as tmp:
        build = Path(tmp)
        for name, data in artifacts.items():
            if isinstance(data, list):
                nominal.write_array(build / name, data)
            else:
                (build / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        examples = [row for row in preview if row["pratipadika"]["stem"] in {"guru", "Dana", "devI"}]
        (build / "prompt_examples.txt").write_text("\n\n".join(f"Task ID: {r['id']}\n{render_task(r)}" for r in examples))
        manifest = {
            "kind": "pilot_only", "generator": {p.relative_to(ROOT).as_posix(): nominal.sha256(p) for p in code_paths},
            "template": {"path": TEMPLATE.relative_to(ROOT).as_posix(), "sha256": nominal.sha256(TEMPLATE)},
            "files": {p.name: {"sha256": nominal.sha256(p), "bytes": p.stat().st_size} for p in sorted(build.iterdir())},
        }
        (build / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        if check:
            for path in build.iterdir():
                nominal.require((output / path.name).exists() and path.read_bytes() == (output / path.name).read_bytes(),
                                f"Pilot artifact changed: {path.name}")
        else:
            output.mkdir(parents=True, exist_ok=True)
            for path in sorted(build.iterdir(), key=lambda p: p.name == "manifest.json"):
                # Copy rather than rename: temporary storage can be on another volume.
                pending = output / ("." + path.name + ".tmp")
                pending.write_bytes(path.read_bytes())
                pending.replace(output / path.name)
    print(json.dumps(report["counts"], indent=2), flush=True)
    print(f"{'Verified byte-identical pilot' if check else 'Wrote pilot diagnostics'} in {time.monotonic() - started:.1f}s", flush=True)
    nominal.require(not differences and not invalid, "Pilot found transport/encoding failures; inspect report")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--sample-size", type=int, default=96)
    parser.add_argument("--check", action="store_true", help="Rerun and require byte-identical artifacts")
    args = parser.parse_args()
    run(args.output, args.sample_size, args.check)
