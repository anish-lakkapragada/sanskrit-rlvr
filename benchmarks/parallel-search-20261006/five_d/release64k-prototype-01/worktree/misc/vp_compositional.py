"""Reproducible one-form creation tasks with explicit derived-root operations."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finetune.prompts import render_vp_task, slp1_to_devanagari
from misc import oai_batch_eval as io, vp_campaign_candidates as old
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Vacana, Sanadi, Vyakarana
import vidyut

OUT = ROOT / "benchmarks/iterative-goal-20261006"
OPERATIONS = {
    "Ric": "णिच् (causative)", "san": "सन् (desiderative)",
    "yaN": "यङ् (intensive)", "yaNluk": "यङ्-लुक् (intensive with deletion of यङ्)",
}
CONSTRUCTIONS = {
    "causative": ["Ric"], "desiderative": ["san"],
    "intensive": ["yaN"], "intensive_luk": ["yaNluk"],
    "desiderative_of_causative": ["Ric", "san"],
    "causative_of_desiderative": ["san", "Ric"],
    "causative_of_intensive": ["yaN", "Ric"],
    "desiderative_of_causative_of_intensive": ["yaN", "Ric", "san"],
}


def render(task):
    prompt = render_vp_task(task, "v2/vp_task_eval.txt")
    operations = task["derivation"]["sanadi"]
    prefixes = task["derivation"]["prefixes"]
    extra = "\nDerived-root formation (apply before the requested finite inflection):\n"
    extra += "\n".join(f"{i + 1}. Apply {OPERATIONS[op]} to the result of the preceding step."
                       if i else f"1. Apply {OPERATIONS[op]} to the supplied root."
                       for i, op in enumerate(operations))
    extra += "\nUpasarga (prefix): " + (" + ".join(slp1_to_devanagari(p) for p in prefixes) if prefixes else "none")
    extra += (". Include this prefix and its regular sandhi in the final form.\n" if prefixes else ".\n")
    extra += "The operation order is innermost to outermost. Any grammatically permitted pada is accepted.\n"
    return prompt + extra


def derive(entry, operations, prefixes, coordinates):
    dhatu = entry.dhatu.with_sanadi([getattr(Sanadi, op) for op in operations]).with_prefixes(prefixes)
    la, pu, va = coordinates
    return Vyakarana().derive(Pada.Tinanta(dhatu=dhatu, lakara=la, prayoga=Prayoga.Kartari,
                                          purusha=pu, vacana=va))


def task_for(entry, split, construction, prefixes, coordinates):
    ops = CONSTRUCTIONS[construction]
    ps = derive(entry, ops, prefixes, coordinates)
    if not ps:
        return None
    gold = sorted({p.text for p in ps})
    if len(gold) > 64:
        return None
    for form in gold:
        assert transliterate(slp1_to_devanagari(form), Scheme.Devanagari, Scheme.Slp1) == form
    la, pu, va = map(old.name, coordinates)
    identity = [old.family(entry), ops, prefixes, la, pu, va]
    tid = "comp-" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    rules = sorted({h.code for p in ps for h in p.history if old.name(h.source) == "Ashtadhyayi"})
    return {"id": tid, "dhatu": {"code": entry.code, "aupadeshika": entry.dhatu.aupadeshika,
             "gana": old.name(entry.dhatu.gana), "artha": entry.artha},
            "morphology": {"lakara": la, "prayoga": "Kartari", "purusha": pu, "vacana": va},
            "derivation": {"sanadi": ops, "prefixes": prefixes, "order": "innermost_to_outermost"},
            "gold_slp1": gold, "gold_devanagari": list(map(slp1_to_devanagari, gold)),
            "campaign": {"root_family": old.family(entry), "split": split, "construction": construction,
                "trace_rule_ids": rules, "minimum_trace_steps": min(len(p.history) for p in ps),
                "gold_variants": len(gold), "vp_version": vidyut.__version__,
                "selection_reason": "score-independent random sample of an explicit grammatical construction",
                "audit_status": "engine_and_roundtrip_verified; construction_review_pending"}}


def generate_panel(label, split="development", per_cell=50, seed=20261007, constructions=None):
    path = OUT / (label + ".json")
    if path.exists():
        raise ValueError("Panel already frozen; choose a new label")
    splits = io.read_json(old.OUT / "family-split.json")
    unique = {}
    for e in old.load_entries():
        if splits["families"][old.family(e)]["split"] == split:
            unique.setdefault(old.family(e), e)
    rng = random.Random(seed)
    tasks, attempts, empty, seen = [], Counter(), Counter(), set()
    for cell in constructions or CONSTRUCTIONS:
        entries = list(unique.values())
        rng.shuffle(entries)
        n = 0
        for entry in entries:
            la = rng.choice([x for x in Lakara.choices() if old.name(x) != "Let"])
            pu, va = rng.choice(Purusha.choices()), rng.choice(Vacana.choices())
            prefixes = rng.choice([[], [], [], ["pra"], ["sam"], ["ni"], ["vi"], ["upa"]])
            attempts[cell] += 1
            task = task_for(entry, split, cell, prefixes, (la, pu, va))
            if task is None:
                empty[cell] += 1
                continue
            prompt_hash = hashlib.sha256(render(task).encode()).hexdigest()
            assert prompt_hash not in seen
            seen.add(prompt_hash)
            task["campaign"]["prompt_sha256"] = prompt_hash
            tasks.append(task)
            n += 1
            if n == per_cell:
                break
        if n != per_cell:
            raise ValueError(f"Insufficient supply in {cell}: {n}/{per_cell}")
    io.atomic_json(path, tasks)
    io.atomic_json(OUT / (label + ".manifest.json"), {
        "created_at": io.now(), "seed": seed, "split": split, "n": len(tasks),
        "sha256": io.sha256(path), "generator_sha256": io.sha256(Path(__file__)),
        "root_families": len({t["campaign"]["root_family"] for t in tasks}),
        "cells": dict(Counter(t["campaign"]["construction"] for t in tasks)),
        "attempts": dict(attempts), "empty_or_excess_variants": dict(empty),
        "grammar_scope": "Classical active finite verbs; explicit sanadi order; zero or one prefix; all engine variants accepted",
        "purpose": "exploratory pilot, not final benchmark; grammatical review required before release"})
    print(json.dumps({"path": str(path), "n": len(tasks), "attempts": dict(attempts), "skipped": dict(empty)}))
    return tasks


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("label")
    p.add_argument("--per-cell", type=int, default=50)
    p.add_argument("--seed", type=int, default=20261007)
    a = p.parse_args()
    generate_panel(a.label, per_cell=a.per_cell, seed=a.seed)
