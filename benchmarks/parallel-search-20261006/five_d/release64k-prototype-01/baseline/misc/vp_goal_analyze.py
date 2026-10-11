"""Compare development compositions across both reference models; no paid calls."""
from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_goal as c, oai_batch_eval as io
from misc.vp_campaign_analyze import summarize as summarize_forms, spelling_key
from misc.vp_goal_grammar import input_issue


def summarize(rows):
    result = summarize_forms(rows)
    if any(r['task'].get('task_type') in {'samasa_creation','finite_bundle'} for r in rows):
        result['root_families']=len({f for r in rows for f in r['task']['campaign'].get('root_families',[r['task']['campaign']['root_family']])})
        result['compound_note']='Each creation set or compound is one scored task. Distinct dhatu families are counted across every constituent. A root-set identifier alone does not justify a cluster-uncertainty estimate when sets overlap.'
    grids = [r for r in rows if r['task'].get('task_type') in {'finite_paradigm','finite_contrast','finite_bundle'}]
    if grids:
        n_forms = sum(len(r['task']['forms']) for r in grids)
        correct = sum(r.get('paradigm_score', {}).get('correct_forms', 0) for r in grids)
        valid = [r for r in grids if r['status'] == 'completed' and not r['truncated']
                 and r.get('paradigm_score', {}).get('format_valid')]
        valid_forms = sum(len(r['task']['forms']) for r in valid)
        def tolerant_forms(row):
            answers = row.get('paradigm_score', {}).get('answers')
            return ([spelling_key(answers[str(i+1)]) in {spelling_key(x) for x in f['gold_devanagari']}
                     for i, f in enumerate(row['task']['forms'])] if answers else [False]*len(row['task']['forms']))
        additional_tolerant = sum(not r['is_correct'] and all(tolerant_forms(r)) for r in valid)
        result['completed_spelling_tolerant_correct'] += additional_tolerant
        result['completed_spelling_tolerant_accuracy'] = (result['completed_spelling_tolerant_correct']/result['completed']
                                                        if result['completed'] else None)
        result['nasal_spelling_only_errors'] += additional_tolerant
        result['paradigm_diagnostics'] = {
            'n_paradigms':len(grids), 'n_forms':n_forms, 'correct_forms':correct,
            'per_form_accuracy':correct/n_forms,
            'format_valid':sum(r.get('paradigm_score', {}).get('format_valid', False) for r in grids),
            'n_completed_valid_format':len(valid),
            'task_accuracy_given_completed_valid_format':sum(r['is_correct'] for r in valid)/len(valid) if valid else None,
            'per_form_accuracy_given_completed_valid_format':sum(r['paradigm_score']['correct_forms'] for r in valid)/valid_forms if valid else None,
            'per_form_spelling_tolerant_accuracy':sum(sum(tolerant_forms(r)) for r in grids)/n_forms,
            'task_spelling_tolerant_accuracy_given_completed_valid_format':sum(all(tolerant_forms(r)) for r in valid)/len(valid) if valid else None,
            'metric':'Headline: all specified forms correct in the versioned answer format. Secondary: individual forms correct; missing/invalid output counts wrong.'}
    return result


def analyze():
    state = c.load()
    all_rows, cells, errors, diagnostics, experiments = defaultdict(list), defaultdict(lambda: defaultdict(list)), [], {}, {}
    for job in state["jobs"].values():
        if not job.get("collected_at") or job["phase"] not in {"explore", "confirm"}:
            continue
        provider = job["provider"]
        raw_rows = io.read_json(c.OUT / "jobs" / job["id"] / "results.json")
        invalid = [{"id": r["task_id"], "reason": input_issue(r["task"])} for r in raw_rows if input_issue(r["task"])]
        job_rows = [r for r in raw_rows if not input_issue(r["task"])]
        if not job_rows:
            experiments[job["id"]] = {"provider": provider, "raw_overall": summarize(raw_rows), "invalid_inputs": invalid,
                                      "n_invalid_inputs": len(invalid), "prompt_version": raw_rows[0]["task"].get("prompt_version", "composition-v1"),
                                      "overall": None, "cells": {}, "sampling_cells": {}}
            continue
        experiments[job["id"]] = {"provider": provider, "prompt_version": job_rows[0]["task"].get("prompt_version", "composition-v1"),
                                  "overall": summarize(job_rows), "cells": {}, "raw_overall": summarize(raw_rows),
                                  "n_invalid_inputs": len(invalid), "invalid_inputs": invalid}
        is_prompt_diagnostic = any("probe_original_status" in r["task"]["campaign"] for r in job_rows)
        if is_prompt_diagnostic:
            diagnostics[job["id"]] = {"provider": provider, **summarize(job_rows),
                                      "note": "Paired prompt diagnostic; excluded from construction difficulty estimates"}
            experiments[job['id']]['prompt_diagnostic'] = True
        for cell in {r["task"]["campaign"]["construction"] for r in job_rows}:
            experiments[job["id"]]["cells"][cell] = summarize([r for r in job_rows if r["task"]["campaign"]["construction"] == cell])
        def sampling_label(r):
            campaign = r["task"]["campaign"]
            return campaign.get("sampling_cell", {}).get("label", campaign["construction"])
        experiments[job["id"]]["sampling_cells"] = {
            label: summarize([r for r in job_rows if sampling_label(r) == label])
            for label in sorted({sampling_label(r) for r in job_rows})}
        if is_prompt_diagnostic:
            continue
        for row in job_rows:
            task = row["task"]
            all_rows[provider].append(row)
            cell = task["campaign"]["construction"]
            cells[cell][provider].append(row)
            if row["is_correct"] is not True:
                errors.append({"job": job["id"], "provider": provider, "id": task["id"],
                    "construction": cell, "dhatu": task["dhatu"], "morphology": task["morphology"],
                    "derivation": task.get("derivation"), "gold": task["gold_devanagari"],
                    "gold_slp1": task["gold_slp1"], "answer": row["answer"], "status": row["status"],
                    "forms": task.get('forms'), "paradigm_score": row.get('paradigm_score'),
                    "truncated": row["truncated"], "spelling_only": bool(row["answer"]) and
                    spelling_key(row["answer"]) in {spelling_key(x) for x in task["gold_devanagari"]}})
    result = {"updated_at": io.now(), "overall": {p: summarize(rows) for p, rows in all_rows.items()},
              "cells": {cell: {p: summarize(rows) for p, rows in ps.items()} for cell, ps in cells.items()},
              "diagnostics": diagnostics,
              "experiments": experiments,
              "note": "Pooled totals describe development requests only. Use per-experiment, per-prompt cells for conclusions; do not mix conditions for calibration. Frozen final evaluation remains independent."}
    io.atomic_json(c.OUT / "development-analysis.json", result)
    io.atomic_json(c.OUT / "development-errors.json", errors)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return result


if __name__ == "__main__":
    analyze()
