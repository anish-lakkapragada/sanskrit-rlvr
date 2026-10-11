"""VP-backed derivations and coordinate-substitution correction tasks."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana

from finetune.prompts import (
    GANA_EN, LAKARA_EN, PRAYOGA_EN, PURUSHA_EN, VACANA_EN,
    slp1_to_devanagari,
)
from misc.vp_cartesian_task import entries_by_code, entry_scope_issue, oracle_issue

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).resolve().parent
INVENTORY = ROOT / "benchmarks/parallel-search-20261007/four_d-90/candidate-1800-v1/tasks.json"
DICTIONARY = ROOT / "data/finetune/task-data/vidyut_dhatupatha_5.tsv"
VERSION = "vp-correction-coordinate-v1"
SEED = "vp-correction-200-20261009"
VP_VERSION = "0.4.0"
SETTINGS = {"log_steps": True, "is_chandasi": False, "use_svaras": False, "nlp_mode": False}
GRAMMAR = Vyakarana(**SETTINGS)
LAKARAS = tuple(LAKARA_EN)
PERSONS = tuple(PURUSHA_EN)
NUMBERS = tuple(VACANA_EN)
AXES = ("purusha", "vacana", "lakara")
CHOICES = {"lakara": LAKARAS, "purusha": PERSONS, "vacana": NUMBERS}
AXIS_LABELS = {"lakara": "tense/mood", "purusha": "person", "vacana": "number"}
HOLDS = {
    "01.0150": "Previously identified accent/input repair: jabh",
    "01.0248": "Previously identified accent/input repair: reb",
    "01.0946": "Previously identified accent/input repair: khund",
    "01.0253": "Previously unresolved lexical identity: salr",
    "01.0923": "Previously unresolved lexical identity: jna",
    "01.0922": "Previously unresolved shra lexical identity",
    "02.0048": "Conservative hold on the other shra entry",
    "10.0481": "Previously documented Cada source-reading discrepancy",
}


class Excluded(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marker_order(text):
    return re.sub(r"[~\\^]+", lambda match: "".join(sorted(match.group())), text)


@lru_cache(maxsize=16384)
def devanagari(text):
    rendered = unicodedata.normalize("NFC", slp1_to_devanagari(text))
    restored = transliterate(rendered, Scheme.Devanagari, Scheme.Slp1)
    if marker_order(restored) != marker_order(text):
        raise Excluded(f"Intermediate transliteration loses information: {text!r}")
    return rendered


def inventory_entries():
    source = json.loads(INVENTORY.read_text())
    entries = entries_by_code()
    included = []
    excluded = []
    for code in sorted({task["dhatu"]["code"] for task in source}):
        entry = entries[code]
        reason = HOLDS.get(code) or entry_scope_issue(entry)
        if reason:
            excluded.append({"code": code, "reason": reason})
        else:
            included.append(entry)
    return included, excluded


def coordinates(lakara, purusha, vacana):
    return {"lakara": lakara, "prayoga": "Kartari", "purusha": purusha, "vacana": vacana}


def project(derivation):
    states = []
    raw = []
    checkpoints = []
    for raw_index, step in enumerate(derivation.history):
        terms_slp1 = list(step.result)
        terms = [devanagari(term) for term in terms_slp1 if term]
        raw.append({"rule": step.code, "source": step.source.name, "terms_slp1": terms_slp1})
        if terms and (not states or terms != states[-1]):
            states.append(terms)
            checkpoints.append({"raw_index": raw_index, "rule": step.code, "source": step.source.name})
    return {
        "states": states, "final_answer": devanagari(derivation.text),
        "final_slp1": derivation.text, "checkpoints": checkpoints, "raw_history": raw,
    }


@lru_cache(maxsize=8192)
def derive(code, lakara, prayoga, purusha, vacana):
    if vidyut.__version__ != VP_VERSION:
        raise RuntimeError(f"This generator is pinned to vidyut {VP_VERSION}")
    entry = entries_by_code()[code]
    morphology = dict(lakara=lakara, prayoga=prayoga, purusha=purusha, vacana=vacana)
    paths = GRAMMAR.derive(Pada.Tinanta(
        dhatu=entry.dhatu, lakara=getattr(Lakara, lakara), prayoga=getattr(Prayoga, prayoga),
        purusha=getattr(Purusha, purusha), vacana=getattr(Vacana, vacana),
    ))
    if not paths:
        raise Excluded("VP returned no derivation")
    issue = oracle_issue({
        "dhatu": {"code": code}, "morphology": morphology,
        "gold_slp1": sorted({path.text for path in paths}),
        "campaign": {"trace_rule_ids": sorted({step.code for path in paths for step in path.history})},
    })
    if issue:
        raise Excluded(issue)
    projected = [project(path) for path in paths]
    projected.sort(key=lambda path: canonical_json(path))
    return projected


def derive_for(code, morphology):
    return derive(code, **morphology)


def distinct_paths(paths):
    unique = {}
    for path in paths:
        key = canonical_json([path["states"], path["final_answer"]])
        unique.setdefault(key, path)
    return [unique[key] for key in sorted(unique)]


def first_invalid_index(observed, valid_paths):
    compatible = list(valid_paths)
    for index, state in enumerate(observed):
        compatible = [path for path in compatible
                      if index < len(path["states"]) and path["states"][index] == state]
        if not compatible:
            return index
    return None


def accepted_repairs(observed, error_index, valid_paths):
    prefix = observed[:error_index]
    answers = {}
    for path in valid_paths:
        if path["states"][:error_index] != prefix or len(path["states"]) <= error_index:
            continue
        answer = {
            "first_incorrect_step": error_index + 1,
            "corrected_steps": [
                {"step": index + 1, "terms": terms}
                for index, terms in enumerate(path["states"]) if index >= error_index
            ],
            "final_answer": path["final_answer"],
        }
        answers[canonical_json(answer)] = answer
    return [answers[key] for key in sorted(answers)]


def candidates_for(entry, target, axis, seed=SEED):
    target_paths = derive_for(entry.code, target)
    targets = distinct_paths(target_paths)
    final_forms = {path["final_answer"] for path in targets}
    candidates = []
    for alternative in CHOICES[axis]:
        if alternative == target[axis]:
            continue
        donor = {**target, axis: alternative}
        try:
            donor_paths = derive_for(entry.code, donor)
        except Excluded:
            continue
        for donor_path in distinct_paths(donor_paths):
            if donor_path["final_answer"] in final_forms:
                continue
            error_index = first_invalid_index(donor_path["states"], targets)
            if error_index is None or error_index < 2 or len(donor_path["states"]) - error_index < 2:
                continue
            answers = accepted_repairs(donor_path["states"], error_index, targets)
            if not answers:
                continue
            identity = [VERSION, seed, entry.code, target, donor, donor_path["states"], donor_path["final_answer"]]
            candidates.append({
                "id": "correction-" + digest(identity)[:24],
                "target_paths": target_paths, "target": target, "donor": donor,
                "donor_path": donor_path, "axis": axis, "error_index": error_index,
                "accepted_answers": answers,
            })
    return sorted(candidates, key=lambda candidate: candidate["id"])


def render_prompt(task):
    morphology = task["morphology"]
    root = task["dhatu"]
    trace = "\n".join(f"{index + 1}. {json.dumps(terms, ensure_ascii=False)}"
                      for index, terms in enumerate(task["proposed_steps"]))
    return (DIRECTORY / "prompt.txt").read_text().format(
        root=devanagari(root["aupadeshika"]), code=root["code"],
        gana=GANA_EN[root["gana"]], meaning=devanagari(root["artha"]),
        lakara=f"{LAKARA_EN[morphology['lakara']]} ({morphology['lakara']})",
        prayoga=f"{PRAYOGA_EN[morphology['prayoga']]} ({morphology['prayoga']})",
        purusha=f"{PURUSHA_EN[morphology['purusha']]} ({morphology['purusha']})",
        vacana=f"{VACANA_EN[morphology['vacana']]} ({morphology['vacana']})",
        trace=trace, final=task["proposed_final_answer"],
    ).strip()


def materialize(entry, candidate, number):
    target = candidate["target"]
    donor = candidate["donor"]
    donor_path = candidate["donor_path"]
    error_index = candidate["error_index"]
    root = {"code": entry.code, "aupadeshika": entry.dhatu.aupadeshika,
            "gana": entry.dhatu.gana.name, "artha": entry.artha}
    task = {
        "number": number, "id": candidate["id"], "task_type": VERSION,
        "dhatu": root, "morphology": target,
        "proposed_steps": donor_path["states"], "proposed_final_answer": donor_path["final_answer"],
        "accepted_answers": candidate["accepted_answers"],
        "generation": {
            "template": "single_coordinate_substitution", "changed_coordinate": candidate["axis"],
            "donor_morphology": donor, "first_incorrect_step": error_index + 1,
            "target_raw_paths": len(candidate["target_paths"]),
            "target_distinct_paths": len(distinct_paths(candidate["target_paths"])),
            "compatible_answer_count": len(candidate["accepted_answers"]),
            "first_wrong_rule": donor_path["checkpoints"][error_index],
            "verification": "Complete target prefix comparison; VP-generated donor; complete compatible suffix set",
        },
    }
    task["prompt"] = render_prompt(task)
    task["prompt_sha256"] = hashlib.sha256(task["prompt"].encode()).hexdigest()
    evidence = {
        "id": task["id"], "target_paths": candidate["target_paths"],
        "donor_path": donor_path, "donor_morphology": donor,
    }
    return task, evidence
