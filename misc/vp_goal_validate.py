"""Mechanically audit generated creation tasks without any model calls.

This checks engine reproducibility, prompt coverage and split membership. It
does not replace independent review of the grammatical construction.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_goal as c, vp_compositional as g, oai_batch_eval as io
from misc.vp_compositional_prompt_v2 import render as render_v2
from misc.vp_compositional_prompt_v3 import render as render_v3
from misc.vp_compositional_prompt_v4 import render as render_v4
from misc.vp_paradigm_prompt_v1 import render as render_paradigm
from misc.vp_contrast_prompt_v1 import render as render_contrast
from misc.vp_krdanta_prompt_v1 import render as render_krdanta
from misc.vp_paradigm_prompt_v2 import render as render_paradigm_v2
from misc.vp_contrast_prompt_v2 import render as render_contrast_v2
from misc.vp_paradigm_prompt_v3 import render as render_paradigm_v3
from misc.vp_contrast_prompt_v3 import render as render_contrast_v3
from misc.vp_paradigm_prompt_v4 import render as render_paradigm_v4
from misc.vp_contrast_prompt_v4 import render as render_contrast_v4
from misc.vp_multiform_prompt_v5 import render as render_multiform_v5
from misc.vp_samasa_prompt_v1 import render as render_samasa
from misc.vp_samasa_prompt_v2 import render as render_samasa_v2
from misc.vp_samasa_prompt_v3 import render as render_samasa_v3
from misc.vp_bundle_prompt_v1 import render as render_bundle
from misc.vp_unadi_prompt_v1 import render as render_unadi
from misc.vp_sanskrit_prompt_v1 import render as render_sanskrit
from misc.vp_cartesian_prompt_v1 import render as render_cartesian
from misc.vp_cartesian_prompt_v2 import render as render_cartesian_v2
from misc.vp_cartesian_prompt_v3 import render as render_cartesian_v3
from misc.vp_finite_pada import task_for as task_with_pada
from misc.vp_goal_grammar import validate_prefixes
from misc.vp_goal_phonology import matches as matches_phonology
from misc import vp_compositional_deep as deep
from vidyut.prakriya import Lakara, Purusha, Vacana

RENDERERS = {"composition-v1": g.render, "composition-v2-plain": render_v2,
             "composition-v3-fields": render_v3, "composition-v4-pada": render_v4,
             "paradigm-v1": render_paradigm, "contrast-v1": render_contrast,
             "krdanta-v1": render_krdanta,
             "paradigm-v2-sanskrit": render_paradigm_v2, "contrast-v2-sanskrit": render_contrast_v2,
             "paradigm-v3-dhatu": render_paradigm_v3, "contrast-v3-dhatu": render_contrast_v3,
             "paradigm-v4-lines": render_paradigm_v4, "contrast-v4-lines": render_contrast_v4,
             "paradigm-v5-fields": render_multiform_v5, "contrast-v5-fields": render_multiform_v5,
             "samasa-v1": render_samasa, "samasa-v2-fields": render_samasa_v2,
             "samasa-v3-fields": render_samasa_v3, "bundle-v1": render_bundle,
             "unadi-v1": render_unadi, "unadi-v2-sanskrit": render_sanskrit,
             "bundle-v2-sanskrit": render_sanskrit,
             "cartesian-4d-v1": render_cartesian, "cartesian-5d-v1": render_cartesian,
             "cartesian-4d-v2-verb": render_cartesian_v2, "cartesian-5d-v2-verb": render_cartesian_v2,
             "cartesian-4d-v3-sanskrit": render_cartesian_v3, "cartesian-5d-v3-sanskrit": render_cartesian_v3}


def validate(tasks, split, *, allowed_families=None, forbidden_ids=()):
    if not tasks:
        raise ValueError("Empty panel")
    assignments = io.read_json(c.HISTORY / "family-split.json")["families"]
    entries = {e.code: e for e in g.old.load_entries()}
    ids, prompts, roots, cells = set(), set(), Counter(), Counter()
    component_ids = set()
    forbidden_ids = set(forbidden_ids)
    for t in tasks:
        if t["id"] in ids or t["id"] in forbidden_ids:
            raise ValueError("Duplicate or previously exposed task")
        ids.add(t["id"])
        if t.get('task_type')=='samasa_creation':
            from misc.vp_goal_samasa import validate_task
            validate_task(t,split,allowed_families=allowed_families)
            prompt_digest=hashlib.sha256(RENDERERS[t['prompt_version']](t).encode()).hexdigest()
            if prompt_digest in prompts:
                raise ValueError('Duplicate compound prompt')
            prompts.add(prompt_digest)
            for family in t['campaign']['root_families']:
                roots[family]+=1
            cells[t['campaign']['construction']]+=1
            continue
        if t.get('task_type') in {'finite_paradigm','finite_contrast','finite_bundle'}:
            if t['task_type'] == 'finite_bundle':
                from misc.vp_goal_bundle import validate_task
            else:
                from misc.vp_goal_paradigm import validate_task
            validate_task(t, split, allowed_families=allowed_families, forbidden_ids=forbidden_ids)
            part_ids = {f['id'] for f in t['forms']}
            if component_ids & part_ids:
                raise ValueError('A component form is reused across paradigm tasks')
            component_ids.update(part_ids)
            prompt_digest = hashlib.sha256(RENDERERS[t['prompt_version']](t).encode()).hexdigest()
            if prompt_digest in prompts:
                raise ValueError('Duplicate paradigm prompt')
            prompts.add(prompt_digest)
            for family in t['campaign'].get('root_families', [t['campaign']['root_family']]):
                roots[family] += 1
            cells[t['campaign'].get('sampling_cell', {}).get('label', t['campaign']['construction'])] += 1
            continue
        e = entries[t["dhatu"]["code"]]
        family = g.old.family(e)
        if t["campaign"]["root_family"] != family or t["campaign"]["split"] != split or assignments[family]["split"] != split:
            raise ValueError("Root-family split violation")
        if allowed_families is not None and family not in allowed_families:
            raise ValueError("Root not in the frozen family allocation")
        if t.get('task_type') == 'modification':
            from misc.vp_modification_task_v1 import validate_task
            from misc.vp_modification_prompt_v1 import render as render_modification
            validate_task(t, split, allowed_families=allowed_families)
            prompt_digest = hashlib.sha256(render_modification(t).encode()).hexdigest()
            if prompt_digest != t['campaign']['prompt_sha256'] or prompt_digest in prompts:
                raise ValueError('Modification prompt changed or duplicated')
            prompts.add(prompt_digest)
            roots[family] += 1
            cells[t['campaign'].get('sampling_cell', {}).get('label', t['campaign']['construction'])] += 1
            continue
        if t.get('task_type') in {'cartesian_4d', 'cartesian_5d'}:
            from misc.vp_cartesian_task import validate_task
            validate_task(t, e, split)
            prompt_digest = hashlib.sha256(RENDERERS[t['prompt_version']](t).encode()).hexdigest()
            if prompt_digest in prompts:
                raise ValueError('Duplicate Cartesian prompt')
            prompts.add(prompt_digest)
            roots[family] += 1
            cells[t['campaign'].get('sampling_cell', {}).get('label', t['campaign']['construction'])] += 1
            continue
        if t.get('task_type') == 'passive_creation':
            from misc.vp_goal_passive import validate_task
            validate_task(t,e,split)
            prompt_digest=hashlib.sha256(RENDERERS[t['prompt_version']](t).encode()).hexdigest()
            if prompt_digest in prompts:
                raise ValueError('Duplicate passive prompt')
            prompts.add(prompt_digest);roots[family]+=1
            cells[t['campaign'].get('sampling_cell',{}).get('label',t['campaign']['construction'])]+=1
            continue
        if t.get('task_type') == 'unadi_creation':
            from misc.vp_goal_unadi import validate_task
            validate_task(t,split)
            prompt_digest = hashlib.sha256(RENDERERS[t['prompt_version']](t).encode()).hexdigest()
            if prompt_digest in prompts:
                raise ValueError('Duplicate unadi prompt')
            prompts.add(prompt_digest)
            roots[family] += 1
            cells[t['campaign']['construction']] += 1
            continue
        if t.get('task_type') == 'krdanta_creation':
            from misc.vp_goal_krdanta import validate_task
            validate_task(t,e,split)
            prompt_digest = hashlib.sha256(render_krdanta(t).encode()).hexdigest()
            if prompt_digest in prompts:
                raise ValueError('Duplicate krdanta prompt')
            prompts.add(prompt_digest)
            roots[family] += 1
            cells[t['campaign'].get('sampling_cell',{}).get('label',t['campaign']['construction'])] += 1
            continue
        m, d = t["morphology"], t["derivation"]
        validate_prefixes(d["prefixes"])
        if m["prayoga"] != "Kartari" or m["lakara"] == "Let" or d["order"] != "innermost_to_outermost":
            raise ValueError("Task outside declared grammatical scope")
        coords = (getattr(Lakara, m["lakara"]), getattr(Purusha, m["purusha"]), getattr(Vacana, m["vacana"]))
        construction = t["campaign"]["construction"]
        if d["sanadi"] != {**g.CONSTRUCTIONS, **deep.CONSTRUCTIONS}[construction]:
            raise ValueError("Construction does not describe the requested operations")
        version = t.get("prompt_version", "composition-v1")
        if "dhatu_pada" in m and version != "composition-v4-pada":
            raise ValueError("Specified pada is absent from the prompt")
        if construction in deep.CONSTRUCTIONS:
            expected = deep.task_for(e, split, construction, d["prefixes"], coords, m.get("dhatu_pada"))
        elif "dhatu_pada" in m:
            if version != "composition-v4-pada":
                raise ValueError("Specified pada is absent from the prompt")
            expected = task_with_pada(e, split, construction, d["prefixes"], coords, m["dhatu_pada"])
        else:
            expected = g.task_for(e, split, construction, d["prefixes"], coords)
        if expected is None:
            raise ValueError("The specified form has no engine derivation")
        for key in ("id", "dhatu", "morphology", "derivation", "gold_slp1", "gold_devanagari"):
            if t[key] != expected[key]:
                raise ValueError(f"Regenerated task disagrees: {t['id']} / {key}")
        for key in ("trace_rule_ids", "minimum_trace_steps", "gold_variants", "vp_version"):
            if t["campaign"][key] != expected["campaign"][key]:
                raise ValueError(f"Derivation metadata disagrees: {key}")
        cell = t["campaign"].get("sampling_cell", {})
        if cell.get('construction', construction) != construction:
            raise ValueError('Task construction differs from the declared sampling cell')
        if not matches_phonology(e, cell.get('phonology')):
            raise ValueError('Task violates the declared phonological sampling predicate')
        if t["dhatu"]["gana"] in cell.get("exclude_ganas", []) or set(t["campaign"]["trace_rule_ids"]) & set(cell.get("exclude_rules", [])):
            raise ValueError("Task violates declared validity exclusions")
        for key, value in (("lakaras", m["lakara"]), ("prefixes", d["prefixes"]), ("dhatu_padas", m.get("dhatu_pada"))):
            if key in cell and value not in cell[key]:
                raise ValueError(f"Task violates sampling cell: {key}")
        prompt_digest = hashlib.sha256(RENDERERS[version](t).encode()).hexdigest()
        if prompt_digest != t["campaign"]["prompt_sha256"] or prompt_digest in prompts:
            raise ValueError("Prompt changed or is duplicated")
        prompts.add(prompt_digest)
        roots[family] += 1
        cells[cell.get("label", construction)] += 1
    return {"created_at": io.now(), "passed_mechanical_checks": True,
            "n": len(tasks), "split": split, "task_digest": c.digest(tasks),
            "root_families": len(roots), "maximum_tasks_per_root": max(roots.values()),
            "cells": dict(cells), "validator_sha256": io.sha256(Path(__file__)),
            "family_definition": "Exact Dhatupatha citation including markers, plus gana; not an etymological lemma split.",
            "scope": "Full regeneration, semantic fields, all accepted gold variants, prompt identity, split membership and declared sampling exclusions.",
            "limits": "Does not independently certify Sanskrit correctness, empirical difficulty, contamination absence or benchmark sampling precision."}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tasks", type=Path)
    p.add_argument("--split", required=True, choices=["development", "test", "rl_train"])
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    result = validate(io.read_json(a.tasks), a.split)
    io.atomic_json(a.output, result)
    print(f"Verified {result['n']} tasks / {result['root_families']} root families")
