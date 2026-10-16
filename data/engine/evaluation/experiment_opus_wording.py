"""Controlled wording experiment on benign Sanskrit tasks previously refused as cyber.

prepare is offline; discovery sends at most 40 requests; holdout sends at most 60.
Existing benchmark prompts and results are never modified.
"""

import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_opus as opus

base = opus.base
FOLDER = ROOT / "data/benchmark/experiments/opus55-cyber-wording"
LIMIT = 100
VARIANTS = ("original", "linguistics_context", "concise_instructions", "dictionary_labels")
CONTEXT = (
    "This is a Sanskrit morphology exercise: forming words according to Sanskrit grammar. "
    "The entries below are dictionary forms and grammatical labels. "
    "The requested result is one Sanskrit word form.\n\n"
)
INTRO = {
    "tinanta": "Conjugate the supplied Sanskrit verb for the specified tense or mood, voice, person, and number. "
               "The verb is supplied in its traditional Dhatupatha citation spelling, including grammatical anubandha notation. "
               "Use the supplied verb class, dictionary meaning, and any verbal prefixes.",
    "krdanta": "Form the Sanskrit derivative specified by the primary suffix (krt). "
               "The verb is supplied in its traditional Dhatupatha citation spelling, including grammatical anubandha notation. "
               "Use the supplied verb class, dictionary meaning, any verbal prefixes, and any participle coordinates. "
               "For a noun or adjective, give the uninflected nominal stem without case or number endings. "
               "For an indeclinable, give its complete form.",
    "taddhitanta": "Apply the specified taddhita affix to the supplied Sanskrit nominal base, respecting its stated grammatical interpretation. "
                  "Give the derived nominal stem or complete indeclinable without case or number endings. "
                  "No particular meaning is required; use a meaning under which the affix applies.",
    "subanta": "Inflect the supplied Sanskrit nominal stem for the specified gender, case, and number. "
               "Give the complete standalone noun or adjective form. "
               "Use the displayed stem, including any supplied feminine stem, as the starting form.",
}
LABELS = {
    "dhatu (Sanskrit verbal root):": "dhatu (Sanskrit verb dictionary entry):",
    "anubandha markers included": "grammatical anubandha notation included",
    "artha (traditional meaning):": "artha (dictionary meaning of the Sanskrit verb):",
    "Required form:": "Grammatical target:",
    "artha (meaning): unrestricted": "artha (meaning): any meaning licensed by Sanskrit grammar",
}


def write_json(path, value):
    base.atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(value):
    return hashlib.sha256(base.compact(value).encode()).hexdigest()


def change_prompt(prompt, family, variant):
    if variant == "original":
        return prompt
    if variant == "linguistics_context":
        return CONTEXT + prompt
    instructions, fields = prompt.split("=== Your task ===", 1)
    if variant == "concise_instructions":
        output_rule = instructions[instructions.index("Write ONLY the final form"):].strip()
        return INTRO[family] + "\n\n" + output_rule + "\n\n=== Your task ===" + fields
    if variant == "dictionary_labels":
        for old, new in LABELS.items():
            fields = fields.replace(old, new)
        return instructions + "=== Sanskrit dictionary data and grammatical target ===" + fields
    raise ValueError(variant)


def make_plan(cases, phase, variants):
    plan = [{"request_key": f"{phase}:{c['case_id']}:{v}", "case_id": c["case_id"],
             "family": c["family"], "task_id": c["task"]["id"], "phase": phase, "variant": v,
             "prompt": change_prompt(c["original_prompt"], c["family"], v)}
            for c in cases if c["phase"] == phase for v in variants]
    random.Random(69 if phase == "discovery" else 70).shuffle(plan)
    return plan


def prepare(folder):
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError("Experiment already exists; do not overwrite it")
    source, tasks, prompts, _ = opus.load_inputs()
    cases, selection = [], {}
    rng = random.Random(69)
    # All eight tinanta/taddhitanta cases and 32 krdanta cases are unique across phases.
    allocation = {"tinanta": (2, 2), "taddhitanta": (2, 2), "krdanta": (6, 26)}
    for family, (discovery, holdout) in allocation.items():
        raw = (opus.RUN / f"{family}.json").read_bytes()
        rows = json.loads(raw)
        candidates = sorted((r for r in rows if r["status"] == "refused" and
                             (r.get("error") or {}).get("stop_details", {}).get("category") == "cyber"),
                            key=lambda r: r["task_id"])
        selection[family] = {"available_refusals": len(candidates), "source_results_sha256": hashlib.sha256(raw).hexdigest()}
        chosen = rng.sample(candidates, discovery + holdout)
        for i, original in enumerate(chosen):
            task_id = original["task_id"]
            cases.append({"case_id": f"case_{len(cases)+1:02}", "family": family,
                          "phase": "discovery" if i < discovery else "holdout",
                          "task": tasks[family][task_id], "original_prompt": prompts[family, task_id],
                          "original_benchmark_result": original})
    plan = make_plan(cases, "discovery", VARIANTS)
    assert len(cases) == 40 and len(plan) == 40
    folder.mkdir(parents=True)
    (folder / "journals").mkdir()
    manifest = {
        "experiment": "opus55-cyber-wording", "created_at": base.now(), "status": "prepared",
        "seed": 69, "request_budget": LIMIT, "submitted_requests": 0,
        "request_defaults": deepcopy(opus.REQUEST_DEFAULTS), "pricing": source["pricing"],
        "source_run": str(opus.RUN.relative_to(ROOT)), "selection": selection,
        "source_tasks": source["tasks"], "cases_sha256": sha(cases),
        "script": opus.descriptor(Path(__file__)),
        "dependencies": [opus.descriptor(Path(opus.__file__)), opus.descriptor(Path(base.__file__)), source["scoring"]["implementation"]],
        "phases": {"discovery": {"requests": 40, "plan_sha256": sha(plan), "status": "prepared"},
                   "holdout": {"requests": 60, "status": "awaiting_discovery"}},
        "variants": {"original": "Exact original prompt, retried as the contemporaneous control.",
                     "linguistics_context": "Prepend a short explanation that the task is Sanskrit word formation.",
                     "concise_instructions": "Shorten introductory prose; retain all task fields, grammatical constraints, and exact answer-format rule.",
                     "dictionary_labels": "Clarify dictionary-field labels; retain original instructions and all grammatical inputs."},
        "selection_rule": "Among changed variants: fewest refusals, then most completed responses, then most strict correct answers; tie order is context, concise, labels. Freeze winner before holdout.",
        "scope": "Selected previously refused tasks, not an unbiased estimate of the full benchmark. Holdout tasks are disjoint from discovery tasks, but roots/stems may overlap.",
        "preservation": "No benchmark result replacements, template changes, automatic retries, model fallbacks, tools, or Internet access in evaluated requests. One durable start marker per request; at most 100 across both phases.",
    }
    write_json(folder / "cases.json", cases)
    write_json(folder / "discovery-plan.json", plan)
    write_json(folder / "manifest.json", manifest)
    write_json(folder / "results.json", [])
    return {"cases": len(cases), "discovery_requests": len(plan), "selection": selection}


def recover(folder, manifest, cases):
    journal = base.Journal(folder / "journals/requests.jsonl")
    starts, records = {}, {}
    case_map = {c["case_id"]: c for c in cases}
    for event in journal.read():
        key = event["task_id"]
        if event["event"] == "started":
            if key in starts:
                raise RuntimeError("Duplicate request start")
            starts[key] = event
        elif event["event"] in ("response", "error"):
            if key not in starts or key in records:
                raise RuntimeError("Unmatched/duplicate terminal event")
            p = starts[key]["plan"]
            row = opus.result_row(event, case_map[p["case_id"]]["task"], manifest)
            records[key] = {**{k: p[k] for k in ("request_key", "case_id", "family", "phase", "variant")}, **row}
        else:
            raise RuntimeError("Unknown journal event")
    if len(starts) > LIMIT or manifest["submitted_requests"] > len(starts):
        raise RuntimeError("Request budget exceeded or start markers missing")
    return journal, starts, records


def metrics(rows):
    n = len(rows)
    refusals = sum(r["status"] == "refused" for r in rows)
    return {"requests": n, "statuses": dict(Counter(r["status"] for r in rows)),
            "refusals": refusals, "refusal_rate": refusals / n if n else None,
            "refusal_categories": dict(Counter((r.get("error") or {}).get("stop_details", {}).get("category") for r in rows if r["status"] == "refused")),
            "correct": sum(r["correct"] is True for r in rows),
            "strict_correct": sum(r["correct"] is True and r["format_ok"] for r in rows),
            "format_ok": sum(r["format_ok"] for r in rows),
            "known_cost_usd": round(sum(r["cost_usd"] or 0 for r in rows), 10),
            "unknown_cost_requests": sum(r["cost_usd"] is None for r in rows),
            "output_tokens": sum((r["usage"] or {}).get("output_tokens", 0) for r in rows)}


def summarize(records):
    rows = list(records.values())
    result = {"total": metrics(rows), "phases": {}}
    for phase in ("discovery", "holdout"):
        subset = [r for r in rows if r["phase"] == phase]
        variants = {v: metrics([r for r in subset if r["variant"] == v]) for v in VARIANTS if any(r["variant"] == v for r in subset)}
        pairs = {}
        original = {r["case_id"]: r for r in subset if r["variant"] == "original"}
        for v in variants.keys() - {"original"}:
            counts = Counter()
            for r in subset:
                if r["variant"] != v or r["case_id"] not in original:
                    continue
                control = original[r["case_id"]]
                if control["status"] not in ("completed", "refused") or r["status"] not in ("completed", "refused"):
                    counts["incomplete_or_error"] += 1
                elif control["status"] == "refused" and r["status"] == "completed":
                    counts["control_refused_variant_completed"] += 1
                elif control["status"] == "completed" and r["status"] == "refused":
                    counts["control_completed_variant_refused"] += 1
                else:
                    counts["both_" + r["status"]] += 1
            pairs[v] = dict(counts)
        result["phases"][phase] = {"variants": variants, "paired_outcomes": pairs,
                                    "families": {f: {v: metrics([r for r in subset if r["family"] == f and r["variant"] == v])
                                                      for v in variants} for f in sorted({r["family"] for r in subset})}}
    return result


def winner(records):
    rows = [r for r in records.values() if r["phase"] == "discovery"]
    if len(rows) != 40 or any(r["status"] not in ("completed", "refused") for r in rows):
        raise RuntimeError("Need 40 completed/refused discovery outcomes before selection")
    candidates = []
    for i, v in enumerate(VARIANTS[1:]):
        m = metrics([r for r in rows if r["variant"] == v])
        candidates.append(((m["refusals"], -m["statuses"].get("completed", 0), -m["strict_correct"], i), v))
    return min(candidates)[1]


def run_phase(folder, phase):
    with (folder / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest = json.loads((folder / "manifest.json").read_text())
        cases = json.loads((folder / "cases.json").read_text())
        if sha(cases) != manifest["cases_sha256"] or manifest["request_defaults"] != opus.REQUEST_DEFAULTS:
            raise RuntimeError("Pinned inputs/settings changed")
        for entry in [manifest["script"], *manifest["dependencies"]]:
            base.verify_descriptor(entry)
        journal, starts, records = recover(folder, manifest, cases)
        if set(starts) - records.keys():
            raise RuntimeError("Unresolved request; inspect before continuing, never resend automatically")
        if phase == "holdout" and manifest["phases"][phase]["status"] == "awaiting_discovery":
            selected = winner(records)
            plan = make_plan(cases, phase, ("original", selected))
            write_json(folder / "holdout-plan.json", plan)
            manifest["selected_variant"] = selected
            manifest["phases"][phase].update(status="prepared", plan_sha256=sha(plan), selected_at=base.now())
            write_json(folder / "manifest.json", manifest)
        plan = json.loads((folder / f"{phase}-plan.json").read_text())
        if sha(plan) != manifest["phases"][phase]["plan_sha256"]:
            raise RuntimeError("Request plan changed")
        for p in plan:
            if p["request_key"] in starts and starts[p["request_key"]]["request"] != opus.request_body(p["prompt"]):
                raise RuntimeError("Previously submitted prompt differs from plan")
        pending = [p for p in plan if p["request_key"] not in starts]
        if len(starts) + len(pending) > LIMIT:
            raise RuntimeError("100-request budget would be exceeded")
        case_map = {c["case_id"]: c for c in cases}
        key = os.environ.get("ANTHROPIC_API_KEY") or opus.dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
        if pending and not key:
            raise RuntimeError("Missing Anthropic key")
        manifest["status"] = "running"
        manifest["phases"][phase]["status"] = "running"
        futures, cursor, stop = {}, 0, None

        def checkpoint():
            manifest["submitted_requests"] = len(starts)
            manifest["updated_at"] = base.now()
            manifest["stopped_reason"] = stop
            write_json(folder / "results.json", sorted(records.values(), key=lambda r: r["request_key"]))
            write_json(folder / "summary.json", summarize(records))
            write_json(folder / "manifest.json", manifest)

        checkpoint()
        with opus.httpx.Client(timeout=opus.httpx.Timeout(1800, connect=30), follow_redirects=False,
                               transport=opus.httpx.HTTPTransport(retries=0)) as client, ThreadPoolExecutor(max_workers=8) as pool:
            while cursor < len(pending) or futures:
                while not stop and cursor < len(pending) and len(futures) < 8:
                    p = pending[cursor]
                    cursor += 1
                    if len(starts) >= LIMIT:
                        raise RuntimeError("Request budget exhausted")
                    body = opus.request_body(p["prompt"])
                    client_id = str(uuid.uuid4())
                    marker = {"event": "started", "task_id": p["request_key"], "attempt_number": 1,
                              "timestamp": base.now(), "client_request_id": client_id, "plan": p, "request": body}
                    journal.append(marker)
                    starts[p["request_key"]] = marker
                    futures[pool.submit(opus.execute, client, manifest, p["request_key"], body, client_id, journal, key)] = p
                if not futures:
                    break
                done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    p = futures.pop(future)
                    event = future.result()
                    row = opus.result_row(event, case_map[p["case_id"]]["task"], manifest)
                    records[p["request_key"]] = {**{k: p[k] for k in ("request_key", "case_id", "family", "phase", "variant")}, **row}
                    if row["status"] not in ("completed", "refused") or row["cost_usd"] is None:
                        stop = f"Inspect {p['request_key']}: {row['status']}"
                checkpoint()
                print(base.compact({"phase": phase, "submitted": len(starts), "settled": len(records), "in_flight": len(futures), "stop": stop}), flush=True)
        complete = all(p["request_key"] in records for p in plan)
        manifest["phases"][phase]["status"] = "completed" if complete else "paused"
        manifest["status"] = "completed" if phase == "holdout" and complete else "discovery_complete" if complete else "paused"
        checkpoint()
        if phase == "holdout" and complete:
            journal.archive()
        return summarize(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "discovery", "holdout"))
    parser.add_argument("--folder", type=Path, default=FOLDER)
    args = parser.parse_args()
    print(json.dumps(prepare(args.folder) if args.action == "prepare" else run_phase(args.folder, args.action), ensure_ascii=False, indent=2))
