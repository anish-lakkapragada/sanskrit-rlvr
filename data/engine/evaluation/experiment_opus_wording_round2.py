"""A separate 100-request experiment; update candidate templates only after verification.

40 discovery requests, 40 paired holdout requests, 20 confirmation requests.
All request data, lexical meanings, and answer requirements remain explicit.
"""

import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import random
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import experiment_opus_wording as first

opus, base = first.opus, first.base
FOLDER = ROOT / "data/benchmark/experiments/opus55-cyber-wording-round2"
CANDIDATES = first.FOLDER / "candidate-templates"
FAMILIES = ("tinanta", "krdanta", "taddhitanta", "subanta")
VARIANTS = ("current", "compact", "question", "dictionary_gloss")
COUNTS = {"discovery": 40, "holdout": 40, "confirmation": 20}
PERSISTENT = "06.0035:Lan:Kartari:Uttama:Bahu"
COMPACT = {
    "tinanta": "Give the Sanskrit conjugated form specified below. Read the dhatu as a Dhatupatha citation with anubandhas; "
               "use its gana, artha and any prefixes, then the requested lakara, prayoga, purusha and vacana.",
    "krdanta": "Give the Sanskrit form derived with the specified krt suffix, using the supplied dhatu, gana, artha "
               "and any prefixes or participle coordinates. The dhatu is a Dhatupatha citation with anubandhas. "
               "Return the uninflected nominal stem, or the complete indeclinable.",
    "taddhitanta": "Give the Sanskrit derivative formed by the specified taddhita affix. "
                  "Use the supplied nominal base and its grammatical interpretation. Any meaning licensed for the affix is allowed. "
                  "Return the uninflected stem or complete indeclinable, without case or number endings.",
    "subanta": "Give the standalone Sanskrit form of the supplied nominal stem for the specified gender, case and number. "
               "Start from the supplied spelling, including any supplied feminine stem.",
}
QUESTION = {
    "tinanta": "What is the conjugated Sanskrit word matching the grammatical specification below? "
               "The dictionary entry supplies the Dhatupatha citation, including anubandhas, together with the verb class, "
               "dictionary meaning and any prefixes. The required tense or mood, voice, person and number determine the requested form.",
    "krdanta": "What Sanskrit word is formed from the dictionary entry below with the specified primary suffix (krt)? "
               "The entry includes its Dhatupatha citation with anubandhas, verb class, dictionary meaning, and any prefixes. "
               "Use any specified participle coordinates. Give a nominal stem without case or number endings, or a complete indeclinable.",
    "taddhitanta": "What Sanskrit word results from applying the specified taddhita affix to the given nominal base? "
                  "Use the displayed spelling and stated grammatical interpretation. Any grammatical meaning licensed for that affix is allowed. "
                  "Give the derived nominal stem or complete indeclinable, without case or number endings.",
    "subanta": "What is the standalone Sanskrit noun or adjective form for the supplied stem, gender, case and number? "
               "Use the displayed stem as the starting spelling. A supplied feminine stem is already the starting stem.",
}


def transform(current, family, variant):
    if variant == "current":
        return current
    instructions, fields = current.split("=== Your task ===", 1)
    answer_rule = instructions[instructions.index("Write ONLY the final form"):].strip()
    if variant in ("compact", "question"):
        intro = COMPACT[family] if variant == "compact" else QUESTION[family]
        return intro + "\n\n" + answer_rule + "\n\n=== Your task ===" + fields
    if variant == "dictionary_gloss":
        # Explicitly label lexical data while retaining every supplied value.
        intro = "The fields below are a Sanskrit dictionary entry and a grammatical specification. "
        intro += "The meaning field, where present, is a dictionary gloss identifying the lexical entry.\n\n"
        return intro + current
    raise ValueError(variant)


def plan_for(cases, phase, winners=None):
    plan = []
    for c in cases:
        if c["phase"] != phase:
            continue
        if phase == "discovery":
            variants = [(v, v) for v in VARIANTS]
        elif phase == "holdout":
            variants = [("control", "current"), ("selected", winners[c["family"]])]
        else:
            variants = [("selected", winners[c["family"]])]
        for arm, variant in variants:
            plan.append({"request_key": f"{phase}:{c['case_id']}:{arm}", "case_id": c["case_id"],
                         "family": c["family"], "task_id": c["task"]["id"], "phase": phase,
                         "variant": arm, "transformation": variant,
                         "prompt": transform(c["current_prompt"], c["family"], variant)})
    random.Random({"discovery": 69, "holdout": 70, "confirmation": 71}[phase]).shuffle(plan)
    assert len(plan) == COUNTS[phase]
    return plan


def summarize(records):
    rows = list(records.values())
    result = {"total": first.metrics(rows), "phases": {}}
    for phase in COUNTS:
        subset = [r for r in rows if r["phase"] == phase]
        variants = sorted({r["variant"] for r in subset})
        entry = {"arms": {v: first.metrics([r for r in subset if r["variant"] == v]) for v in variants},
                 "families": {f: {v: first.metrics([r for r in subset if r["family"] == f and r["variant"] == v])
                                  for v in variants} for f in FAMILIES}}
        if phase == "holdout":
            control = {r["case_id"]: r for r in subset if r["variant"] == "control"}
            pairs = Counter()
            for r in subset:
                if r["variant"] == "selected" and r["case_id"] in control:
                    pairs[f"control_{control[r['case_id']]['status']}_selected_{r['status']}"] += 1
            entry["paired_outcomes"] = dict(pairs)
        result["phases"][phase] = entry
    return result


def select_winners(records):
    rows = [r for r in records.values() if r["phase"] == "discovery"]
    if len(rows) != 40 or any(r["status"] not in ("completed", "refused") for r in rows):
        raise RuntimeError("Need all 40 valid discovery outcomes")
    selected = {}
    for family in FAMILIES:
        choices = []
        for i, v in enumerate(VARIANTS):
            group = [r for r in rows if r["family"] == family and r["variant"] == v]
            m = first.metrics(group)
            choices.append(((m["refusals"], -m["strict_correct"], -m["statuses"].get("completed", 0), i), v))
        selected[family] = min(choices)[1]
    return selected


def prepare(folder):
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError("Existing experiment; cannot overwrite or reset budget")
    source, tasks, prompts, _ = opus.load_inputs()
    old_cases = json.loads((first.FOLDER / "cases.json").read_text())
    excluded = {(c["family"], c["task"]["id"]) for c in old_cases}
    current_templates, selection, cases = {}, {}, []
    originals = {e["family"]: e["prompt_template"]["text"] for e in source["tasks"]}
    rng = random.Random(69)
    for family in FAMILIES:
        path = CANDIDATES / f"vp_{family}.txt"
        current_templates[family] = path.read_text() if path.exists() else originals[family]
        expected = first.change_prompt(originals[family], family, "concise_instructions") if path.exists() else originals[family]
        if current_templates[family] != expected:
            raise RuntimeError(f"Unexpected current candidate template: {family}")
        rows = json.loads((opus.RUN / f"{family}.json").read_text())
        by_id = {r["task_id"]: r for r in rows}
        flagged = [r for r in rows if r["status"] == "refused" and (r.get("error") or {}).get("stop_details", {}).get("category") == "cyber"]
        pool = sorted((r for r in (rows if family == "subanta" else flagged)
                       if (family, r["task_id"]) not in excluded and r["status"] in ("refused", "completed")), key=lambda r:r["task_id"])
        n_discovery = 4 if family == "tinanta" else 2
        # Each family contributes five fresh holdout tasks and five confirmation requests.
        required = n_discovery + 10 - (2 if family == "tinanta" else 0)
        chosen = rng.sample(pool, required)
        discovery = ([by_id[PERSISTENT]] if family == "tinanta" else []) + chosen[:n_discovery - (family == "tinanta")]
        rest = chosen[n_discovery - (family == "tinanta"):]
        holdout = rest[:5]
        confirmation = ([by_id[PERSISTENT]] if family == "tinanta" else []) + rest[5:]
        assert (len(discovery), len(holdout), len(confirmation)) == (n_discovery, 5, 5)
        selection[family] = {"available_cyber_refusals": len(flagged), "eligible_fresh_cases": len(pool),
                             "baseline": "existing concise candidate" if path.exists() else "original production template (no previous subanta candidate)"}
        for phase, selected in (("discovery", discovery), ("holdout", holdout), ("confirmation", confirmation)):
            for original in selected:
                task_id = original["task_id"]
                current_prompt = first.change_prompt(prompts[family, task_id], family, "concise_instructions") if path.exists() else prompts[family, task_id]
                cases.append({"case_id": f"case_{len(cases)+1:02}", "family": family, "phase": phase,
                              "task": tasks[family][task_id], "original_prompt": prompts[family, task_id],
                              "current_prompt": current_prompt, "original_benchmark_result": original,
                              "persistent_challenge": task_id == PERSISTENT})
    assert len(cases) == 50 and len({(c['family'],c['task']['id']) for c in cases}) == 49
    plan = plan_for(cases, "discovery")
    folder.mkdir(parents=True)
    (folder / "journals").mkdir()
    (folder / "candidate-templates-before").mkdir()
    for family, template in current_templates.items():
        base.atomic_write(folder / "candidate-templates-before" / f"vp_{family}.txt", template)
    manifest = {
        "experiment": "opus55-cyber-wording-round2", "created_at": base.now(), "status": "prepared",
        "request_budget": 100, "submitted_requests": 0, "seed": 69,
        "request_defaults": deepcopy(opus.REQUEST_DEFAULTS), "pricing": source["pricing"],
        "source_tasks": source["tasks"], "selection": selection, "cases_sha256": first.sha(cases),
        "baseline_templates": current_templates, "production_templates": originals,
        "script": opus.descriptor(Path(__file__)),
        "dependencies": [opus.descriptor(Path(first.__file__)), opus.descriptor(Path(opus.__file__)),
                         opus.descriptor(Path(base.__file__)), source["scoring"]["implementation"]],
        "phases": {p: {"requests": n, "status": "prepared" if p == "discovery" else "awaiting_selection"} for p,n in COUNTS.items()},
        "selection_rule": "Choose per family: fewest discovery refusals, most strict correct, most completed; tie preference current, compact, question, dictionary_gloss. Freeze before holdout and confirmation.",
        "variants": {"current": "Existing candidate (original production template for subanta).",
                     "compact": "Shorter direct grammatical instruction; preserve all data fields and answer rule.",
                     "question": "Ask for the grammatical form as a question; preserve all data fields and answer rule.",
                     "dictionary_gloss": "Prepend an explanation of dictionary meanings as lexical data; preserve the rest exactly."},
        "scope": "Discovery contains the persistent round-one tinanta refusal. Holdout has 20 fresh tasks, five per category. Confirmation has five per category, with the persistent tinanta repeated and 19 fresh tasks. Tasks are disjoint otherwise, though roots/stems can overlap. Subanta cases are unflagged controls; other categories use previously cyber-refused tasks.",
        "preservation": "No production prompt/result edits or automatic retries. At most 100 additional requests, separate from round one. Update all four candidate templates after verification, retaining before snapshots. Zero observed refusals cannot guarantee zero future refusals.",
    }
    manifest["phases"]["discovery"]["plan_sha256"] = first.sha(plan)
    first.write_json(folder / "cases.json", cases)
    first.write_json(folder / "discovery-plan.json", plan)
    first.write_json(folder / "manifest.json", manifest)
    first.write_json(folder / "results.json", [])
    return {"requests": COUNTS, "selection": selection}


def load(folder):
    m = json.loads((folder / "manifest.json").read_text())
    cases = json.loads((folder / "cases.json").read_text())
    if first.sha(cases) != m["cases_sha256"] or m["request_defaults"] != opus.REQUEST_DEFAULTS:
        raise RuntimeError("Pinned inputs changed")
    for entry in [m["script"], *m["dependencies"]]:
        base.verify_descriptor(entry)
    journal, starts, records = first.recover(folder, m, cases)
    if set(starts) - records.keys():
        raise RuntimeError("Unresolved attempts; never automatically resend")
    return m, cases, journal, starts, records


def run_phase(folder, phase):
    with (folder / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, cases, journal, starts, records = load(folder)
        if phase != "discovery" and "selected_variants" not in m:
            m["selected_variants"] = select_winners(records)
            m["selected_at"] = base.now()
            first.write_json(folder / "manifest.json", m)
        if phase == "confirmation" and m["phases"]["holdout"]["status"] != "completed":
            raise RuntimeError("Complete holdout first")
        phase_selection = m["phases"][phase].get("selected_variants", m.get("selected_variants"))
        plan = plan_for(cases, phase, phase_selection)
        plan_path = folder / f"{phase}-plan.json"
        if plan_path.exists():
            if json.loads(plan_path.read_text()) != plan or first.sha(plan) != m["phases"][phase]["plan_sha256"]:
                raise RuntimeError("Plan changed")
        else:
            first.write_json(plan_path, plan)
            m["phases"][phase]["plan_sha256"] = first.sha(plan)
            first.write_json(folder / "manifest.json", m)
        for p in plan:
            if p["request_key"] in starts and starts[p["request_key"]]["request"] != opus.request_body(p["prompt"]):
                raise RuntimeError("Submitted request differs from plan")
        pending = [p for p in plan if p["request_key"] not in starts]
        if len(starts) + len(pending) > 100:
            raise RuntimeError("100-request budget exceeded")
        key = os.environ.get("ANTHROPIC_API_KEY") or opus.dotenv_values(ROOT / ".env").get("ANTHROPIC_API_KEY")
        if pending and not key:
            raise RuntimeError("Missing Anthropic key")
        cases_by_id = {c["case_id"]: c for c in cases}
        m["status"] = "running"
        m["phases"][phase]["status"] = "running"
        futures, cursor, stop = {}, 0, None

        def checkpoint():
            m.update(submitted_requests=len(starts), updated_at=base.now(), stopped_reason=stop)
            first.write_json(folder / "results.json", sorted(records.values(), key=lambda r:r["request_key"]))
            first.write_json(folder / "summary.json", summarize(records))
            first.write_json(folder / "manifest.json", m)

        checkpoint()
        with opus.httpx.Client(timeout=opus.httpx.Timeout(1800, connect=30), follow_redirects=False,
                               transport=opus.httpx.HTTPTransport(retries=0)) as client, ThreadPoolExecutor(max_workers=8) as pool:
            while cursor < len(pending) or futures:
                while not stop and cursor < len(pending) and len(futures) < 8:
                    if len(starts) >= 100:
                        raise RuntimeError("Request budget exhausted")
                    p = pending[cursor]
                    cursor += 1
                    body, client_id = opus.request_body(p["prompt"]), str(uuid.uuid4())
                    marker = {"event": "started", "task_id": p["request_key"], "attempt_number": 1,
                              "timestamp": base.now(), "client_request_id": client_id, "plan": p, "request": body}
                    journal.append(marker)
                    starts[p["request_key"]] = marker
                    futures[pool.submit(opus.execute, client, m, p["request_key"], body, client_id, journal, key)] = p
                if not futures:
                    break
                done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    p = futures.pop(future)
                    row = opus.result_row(future.result(), cases_by_id[p["case_id"]]["task"], m)
                    records[p["request_key"]] = {**{k:p[k] for k in ("request_key","case_id","family","phase","variant")}, **row}
                    if row["status"] not in ("completed", "refused") or row["cost_usd"] is None:
                        stop = f"Inspect {p['request_key']}: {row['status']}"
                checkpoint()
                print(base.compact({"phase":phase,"submitted":len(starts),"settled":len(records),"in_flight":len(futures),"stop":stop}),flush=True)
        complete = all(p["request_key"] in records for p in plan)
        m["phases"][phase]["status"] = "completed" if complete else "paused"
        m["status"] = "completed" if phase == "confirmation" and complete else phase + "_complete" if complete else "paused"
        checkpoint()
        if m["status"] == "completed":
            journal.archive()
        return summarize(records)


def refine_confirmation(folder):
    """Record an explicit protocol amendment after failures in the paired test."""
    with (folder / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m = json.loads((folder / "manifest.json").read_text())
        cases = json.loads((folder / "cases.json").read_text())
        if m.get("protocol_amendment"):
            raise RuntimeError("Confirmation selection already frozen")
        if m["status"] != "holdout_complete" or m["submitted_requests"] != 80:
            raise RuntimeError("Refinement requires exactly 80 settled requests")
        history = folder / "protocol-history"
        prior_script = opus.descriptor(history / "runner-before-refinement.py")
        if prior_script["sha256"] != m["script"]["sha256"] or first.sha(cases) != m["cases_sha256"]:
            raise RuntimeError("Pre-amendment snapshot mismatch")
        if json.loads((history / "manifest-before-refinement.json").read_text()) != m or json.loads((history / "cases-before-refinement.json").read_text()) != cases:
            raise RuntimeError("Pre-amendment inputs were not preserved exactly")
        for entry in m["dependencies"]:
            base.verify_descriptor(entry)
        _, starts, records = first.recover(folder,m,cases)
        if len(starts) != 80 or set(starts) != records.keys():
            raise RuntimeError("Unresolved requests")
        old_selection = deepcopy(m["selected_variants"])
        changed = deepcopy(old_selection)
        failures = [r for r in records.values() if r["phase"] == "holdout" and r["status"] == "refused"]
        for family in {r["family"] for r in failures}:
            choices = []
            for i,v in enumerate(VARIANTS):
                if v == old_selection[family]:
                    continue
                group = [r for r in records.values() if r["phase"] == "discovery" and r["family"] == family and r["variant"] == v]
                stats = first.metrics(group)
                choices.append(((stats["refusals"],-stats["strict_correct"],i),v))
            changed[family] = min(choices)[1]
        # Revisit every newly refused lexical task, retaining the earlier persistent tinanta.
        replacements = []
        for family in FAMILIES:
            targets = sorted({r["task_id"] for r in failures if r["family"] == family})
            existing = {c["task"]["id"] for c in cases if c["phase"] == "confirmation" and c["family"] == family}
            slots = [c for c in cases if c["phase"] == "confirmation" and c["family"] == family and not c["persistent_challenge"]]
            for task_id, slot in zip((t for t in targets if t not in existing),slots):
                original = next(c for c in cases if c["phase"] == "holdout" and c["family"] == family and c["task"]["id"] == task_id)
                replacements.append({"case_id":slot["case_id"],"replaced_task":slot["task"]["id"],"challenge_task":task_id})
                case_id = slot["case_id"]
                slot.clear()
                slot.update(deepcopy(original),case_id=case_id,phase="confirmation",confirmation_reason="Cyber refusal in the paired stage")
        m["phases"]["holdout"]["selected_variants"] = old_selection
        m["phases"]["confirmation"]["selected_variants"] = changed
        m["selected_variants"] = changed
        m["protocol_amendment"] = {
            "at":base.now(),"after_requests":80,
            "reason":"Paired requests exposed refusals with the same current template, including a task refused twice. Use the final 20 requests for alternative wording in affected families and explicitly revisit failed tasks.",
            "prior_selection":old_selection,"final_selection":changed,"confirmation_replacements":replacements,
            "selection_rule":"For each family with any paired-stage refusal, choose an alternative from discovery with fewest refusals, most strict correct, then compact/question/dictionary-gloss order. Keep the current wording for other families. Freeze these before confirmation.",
            "inference_limit":"The paired stage now informs tuning and is not an untouched final test. The final 20 calls contain 16 fresh tasks and four known challenge tasks; report outcomes for every call that used the final template, including controls with identical prompts.",
            "prior_script":prior_script,"prior_manifest":opus.descriptor(history / "manifest-before-refinement.json"),
            "prior_cases":opus.descriptor(history / "cases-before-refinement.json")}
        m["cases_sha256"] = first.sha(cases)
        m["script"] = opus.descriptor(Path(__file__))
        m["scope"] += " Adaptive amendment after 80 calls: alternative tinanta/taddhitanta wording; confirmation includes all three newly refused tasks plus the persistent tinanta and 16 fresh tasks. See protocol_amendment."
        first.write_json(folder / "cases.json",cases)
        first.write_json(folder / "manifest.json",m)
        return m["protocol_amendment"]


def verify_and_update(folder):
    with (folder / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, cases, journal, starts, records = load(folder)
        if m["status"] != "completed" or len(starts) != 100 or len(records) != 100:
            raise RuntimeError("Need all 100 outcomes before candidate update")
        if sorted(records.values(), key=lambda r:r["request_key"]) != json.loads((folder / "results.json").read_text()):
            raise RuntimeError("Journal replay mismatch")
        if summarize(records) != json.loads((folder / "summary.json").read_text()):
            raise RuntimeError("Summary mismatch")
        for phase in COUNTS:
            phase_selection = m["phases"][phase].get("selected_variants", m.get("selected_variants"))
            plan = plan_for(cases, phase, phase_selection)
            if first.sha(plan) != m["phases"][phase]["plan_sha256"] or plan != json.loads((folder / f"{phase}-plan.json").read_text()):
                raise RuntimeError("Plan verification failed")
            for p in plan:
                if starts[p["request_key"]]["request"] != opus.request_body(p["prompt"]):
                    raise RuntimeError("Request verification failed")
        for entry in m["source_tasks"]:
            for name in ("dataset", "prompt_template", "renderer", "sampling_manifest"):
                base.verify_descriptor(entry[name])
        schema = opus.schema()
        validator = opus.Draft202012Validator(schema)
        extras = {"request_key","case_id","family","phase","variant"}
        for r in records.values():
            validator.validate([{k:v for k,v in r.items() if k not in extras}])
        frozen = folder / "candidate-templates-after"
        frozen.mkdir(exist_ok=True)
        updated = {}
        for family in FAMILIES:
            template = transform(m["baseline_templates"][family], family, m["selected_variants"][family])
            target = CANDIDATES / f"vp_{family}.txt"
            if target.exists() and target.read_text() not in (m["baseline_templates"][family], template):
                raise RuntimeError(f"Candidate modified externally: {family}")
            base.atomic_write(frozen / target.name, template)
            base.atomic_write(target, template)
            updated[family] = opus.descriptor(target)
        confirmation = [r for r in records.values() if r["phase"] == "confirmation"]
        cases_by_id = {c["case_id"]:c for c in cases}
        final_template_rows = []
        for key,row in records.items():
            case = cases_by_id[row["case_id"]]
            final_prompt = transform(case["current_prompt"],row["family"],m["selected_variants"][row["family"]])
            if starts[key]["request"] == opus.request_body(final_prompt):
                final_template_rows.append(row)
        verification = {"verified_at":base.now(),"verified_requests":100,"updated_templates":updated,
                        "confirmation_outcomes":first.metrics(confirmation),
                        "final_template_outcomes_all_phases":first.metrics(final_template_rows),
                        "final_template_outcomes_by_family":{f:first.metrics([r for r in final_template_rows if r["family"]==f]) for f in FAMILIES},
                        "zero_observed_final_template_refusals":all(r["status"]=="completed" for r in final_template_rows),
                        "scope":"Confirmation: 16 fresh tasks and four known challenges. The all-phases count includes every request matching the final templates exactly, including duplicate controls; discovery/paired outcomes used for selection are not independent validation."}
        first.write_json(folder / "verification.json", verification)
        m["candidate_update"] = {"at":verification["verified_at"],"files":updated}
        first.write_json(folder / "manifest.json", m)
        return verification


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", *COUNTS, "refine", "finalize"))
    parser.add_argument("--folder", type=Path, default=FOLDER)
    args = parser.parse_args()
    value = prepare(args.folder) if args.action == "prepare" else refine_confirmation(args.folder) if args.action == "refine" else verify_and_update(args.folder) if args.action == "finalize" else run_phase(args.folder,args.action)
    print(json.dumps(value,ensure_ascii=False,indent=2))
