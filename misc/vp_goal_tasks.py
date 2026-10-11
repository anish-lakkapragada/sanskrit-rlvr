"""Draw fresh creation panels from explicit, score-independent cell definitions."""
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
from misc import vp_goal as c, vp_compositional as g, oai_batch_eval as io
from misc.vp_compositional_prompt_v3 import render
from misc.vp_compositional_prompt_v4 import render as render_pada
from misc.vp_finite_pada import task_for as task_with_pada
from misc.vp_goal_grammar import validate_prefixes
from misc.vp_goal_phonology import matches as matches_phonology
from misc import vp_compositional_deep as deep
from vidyut.prakriya import Lakara, Purusha, Vacana


def generate(label, cells, split="development", seed=20261008, max_per_family=4):
    for cell in cells:
        for prefixes in cell.get("prefixes", [[]]):
            validate_prefixes(prefixes)
    path = c.OUT / (label + ".json")
    if path.exists():
        raise ValueError("Panel exists; do not change frozen membership")
    assignments = io.read_json(c.HISTORY / "family-split.json")["families"]
    allowed = {f for f, a in assignments.items() if a["split"] == split}
    if split == "test":
        allowed &= set(io.read_json(c.OUT / "test-family-reserve.json")["initial_release_families"])
    entries = {}
    for entry in g.old.load_entries():
        if g.old.family(entry) in allowed:
            entries.setdefault(g.old.family(entry), entry)
    used = set()
    for job in c.load()["jobs"].values():
        for t in io.read_json(c.OUT / "jobs" / job["id"] / "tasks.json"):
            used.update(f['id'] for f in t.get('forms', [t]))
    # Also avoid unsubmitted panels that were already frozen by this sampler.
    for manifest in c.OUT.glob("*.sampling.json"):
        for t in io.read_json(c.OUT / io.read_json(manifest)["filename"]):
            used.update(f['id'] for f in t.get('forms', [t]))
    rng = random.Random(seed)
    tasks, per_family, counts, attempts = [], Counter(), Counter(), Counter()
    for cell in cells:
        construction = cell["construction"]
        assert construction in g.CONSTRUCTIONS or construction in deep.CONSTRUCTIONS
        lakaras = [getattr(Lakara, n) for n in cell.get("lakaras", [g.old.name(x) for x in Lakara.choices() if g.old.name(x) != "Let"])]
        prefixes = cell.get("prefixes", [[], [], [], ["pra"], ["sam"], ["ni"], ["vi"], ["upa"]])
        n = 0
        # Every pass visits each eligible root once, giving breadth priority.
        for cycle in range(12):
            ordered = list(entries.items())
            rng.shuffle(ordered)
            for family, entry in ordered:
                if per_family[family] >= max_per_family:
                    continue
                if g.old.name(entry.dhatu.gana) in cell.get("exclude_ganas", []):
                    continue
                if not matches_phonology(entry, cell.get('phonology')):
                    continue
                coordinates = (rng.choice(lakaras), rng.choice(Purusha.choices()), rng.choice(Vacana.choices()))
                attempts[construction] += 1
                if construction in deep.CONSTRUCTIONS:
                    task = deep.task_for(entry, split, construction, rng.choice(prefixes), coordinates,
                        rng.choice(cell["dhatu_padas"]) if cell.get("dhatu_padas") else None)
                elif cell.get("dhatu_padas"):
                    task = task_with_pada(entry, split, construction, rng.choice(prefixes), coordinates,
                                          rng.choice(cell["dhatu_padas"]))
                else:
                    task = g.task_for(entry, split, construction, rng.choice(prefixes), coordinates)
                if not task or task["id"] in used:
                    continue
                if set(task["campaign"]["trace_rule_ids"]) & set(cell.get("exclude_rules", [])):
                    continue
                task.setdefault("prompt_version", "composition-v3-fields")
                renderer = render_pada if task["prompt_version"] == "composition-v4-pada" else render
                task["campaign"].update(panel=label, sampling_cell=cell,
                    prompt_sha256=hashlib.sha256(renderer(task).encode()).hexdigest())
                used.add(task["id"])
                tasks.append(task)
                per_family[family] += 1
                counts[construction] += 1
                n += 1
                if n == cell["n"]:
                    break
            if n == cell["n"]:
                break
        if n != cell["n"]:
            raise ValueError(f"Supply exhausted for {construction}: {n}/{cell['n']}")
    assert len({t["campaign"]["prompt_sha256"] for t in tasks}) == len(tasks)
    assert len({t["id"] for t in tasks}) == len(tasks)
    io.atomic_json(path, tasks)
    io.atomic_json(c.OUT / (label + ".sampling.json"), {
        "created_at": io.now(), "filename": path.name, "n": len(tasks), "seed": seed,
        "cells": cells, "counts": dict(counts), "attempts": dict(attempts), "split": split,
        "root_families": len(per_family), "max_per_family": max(per_family.values()),
        "task_digest": c.digest(tasks), "file_sha256": io.sha256(path),
        "generator_sha256": io.sha256(Path(__file__)),
        "selection": "Uniform shuffled root visits within predeclared cells; grammatical validity and uniqueness only. No model-score filtering.",
        "audit_status": "VP generation and transliteration checks; construction review remains required"})
    print(json.dumps({"panel": label, "n": len(tasks), "families": len(per_family), "cells": dict(counts)}))
    return tasks


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("label")
    p.add_argument("--cells", type=Path, required=True)
    p.add_argument("--split", choices=["development", "test", "rl_train"], default="development")
    p.add_argument("--seed", type=int, default=20261008)
    a = p.parse_args()
    generate(a.label, io.read_json(a.cells), a.split, a.seed)
