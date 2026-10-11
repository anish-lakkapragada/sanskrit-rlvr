"""Independently rederive the correction dataset and audit its displayed contract."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[1]
sys.path.insert(0, str(ROOT))

import vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana

from finetune.prompts import slp1_to_devanagari
from misc.vp_cartesian_task import entries_by_code


def freeze(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_markers(value):
    return re.sub(r"[~\\^]+", lambda match: "".join(sorted(match.group())), value)


def render_term(value):
    rendered = unicodedata.normalize("NFC", slp1_to_devanagari(value))
    restored = transliterate(rendered, Scheme.Devanagari, Scheme.Slp1)
    if normalize_markers(restored) != normalize_markers(value):
        raise ValueError(f"Lossy Devanagari conversion: {value!r} -> {rendered!r} -> {restored!r}")
    return rendered


def project_independently(path):
    checkpoints = []
    for step in path.history:
        current = [render_term(term) for term in step.result if term != ""]
        if current and (not checkpoints or checkpoints[-1] != current):
            checkpoints.append(current)
    return {"states": checkpoints, "final_answer": render_term(path.text)}


def main():
    tasks_path = DIRECTORY / "tasks.json"
    tasks = json.loads(tasks_path.read_text())
    manifest = json.loads((DIRECTORY / "manifest.json").read_text())
    inventory = json.loads((ROOT / manifest["source_inventory"]).read_text())
    inventory_codes = {task["dhatu"]["code"] for task in inventory}
    entries = entries_by_code()
    grammar = Vyakarana(log_steps=True, is_chandasi=False, use_svaras=False, nlp_mode=False)
    findings = []
    records = []
    raw_target_paths = 0
    raw_donor_paths = 0
    multiple_gold_tasks = 0
    shorter_or_longer_repair_tasks = 0

    def check(condition, number, message):
        if not condition:
            findings.append({"number": number, "message": message})

    def rederive(code, morphology):
        return grammar.derive(Pada.Tinanta(
            dhatu=entries[code].dhatu,
            lakara=getattr(Lakara, morphology["lakara"]),
            prayoga=getattr(Prayoga, morphology["prayoga"]),
            purusha=getattr(Purusha, morphology["purusha"]),
            vacana=getattr(Vacana, morphology["vacana"]),
        ))

    check(vidyut.__version__ == "0.4.0", None, "Unexpected installed VP version")
    check(manifest["vp_settings"] == {
        "log_steps": True, "is_chandasi": False, "use_svaras": False, "nlp_mode": False,
    }, None, "Manifest settings differ from audit settings")
    check(len(tasks) == 200, None, "Task count is not 200")
    for key in ("code", "aupadeshika"):
        check(len({task["dhatu"][key] for task in tasks}) == 200,
              None, f"Dhatu {key} values are not all distinct")

    for task in tasks:
        number = task["number"]
        code = task["dhatu"]["code"]
        check(code in inventory_codes, number, "Root absent from original 4D inventory")
        expected_root = entries[code]
        check(task["dhatu"] == {
            "code": code, "aupadeshika": expected_root.dhatu.aupadeshika,
            "gana": expected_root.dhatu.gana.name, "artha": expected_root.artha,
        }, number, "Public root identity differs from dictionary input")
        target = task["morphology"]
        donor = task["generation"]["donor_morphology"]
        changed_axes = [axis for axis in target if target[axis] != donor[axis]]
        check(changed_axes == [task["generation"]["changed_coordinate"]], number,
              "Donor does not differ by exactly the declared coordinate")
        check(target["prayoga"] == donor["prayoga"] == "Kartari", number,
              "Unexpected nonactive input")
        target_raw = rederive(code, target)
        donor_raw = rederive(code, donor)
        raw_target_paths += len(target_raw)
        raw_donor_paths += len(donor_raw)
        try:
            target_paths = [project_independently(path) for path in target_raw]
            donor_paths = [project_independently(path) for path in donor_raw]
            render_term(task["dhatu"]["aupadeshika"])
            render_term(task["dhatu"]["artha"])
        except ValueError as error:
            findings.append({"number": number, "message": str(error)})
            continue

        observed = task["proposed_steps"]
        shown_path = {"states": observed, "final_answer": task["proposed_final_answer"]}
        check(shown_path in donor_paths, number, "Displayed trace is not a complete VP donor trace")
        check(task["proposed_final_answer"] not in {path["final_answer"] for path in target_paths},
              number, "Wrong final word is also accepted for target")
        valid_prefixes = {
            freeze(path["states"][:length])
            for path in target_paths
            for length in range(len(path["states"]) + 1)
        }
        missing = [length for length in range(1, len(observed) + 1)
                   if freeze(observed[:length]) not in valid_prefixes]
        check(bool(missing), number, "No invalid proposed checkpoint")
        if not missing:
            continue
        first_wrong = min(missing)
        prefix = observed[:first_wrong - 1]
        check(first_wrong >= 3, number, "Fewer than two correct preceding checkpoints")
        check(len(observed) - first_wrong + 1 >= 2, number, "No displayed downstream continuation")
        expected_answers = set()
        compatible_count = 0
        for path in target_paths:
            if path["states"][:first_wrong - 1] != prefix:
                continue
            compatible_count += 1
            remaining = path["states"][first_wrong - 1:]
            check(bool(remaining), number, "Compatible target continuation has no checkpoint suffix")
            answer = {
                "first_incorrect_step": first_wrong,
                "corrected_steps": [
                    {"step": step_number, "terms": terms}
                    for step_number, terms in enumerate(remaining, first_wrong)
                ],
                "final_answer": path["final_answer"],
            }
            expected_answers.add(freeze(answer))
        check(first_wrong == task["generation"]["first_incorrect_step"], number,
              "Stored first-error location differs from independent prefix search")
        check(expected_answers == {freeze(answer) for answer in task["accepted_answers"]}, number,
              "Gold set differs from the complete independently derived continuation set")
        check(len(task["accepted_answers"]) == len(expected_answers), number,
              "Duplicate gold repairs")
        multiple_gold_tasks += len(expected_answers) > 1
        shorter_or_longer_repair_tasks += any(
            len(answer["corrected_steps"]) != len(observed) - first_wrong + 1
            for answer in task["accepted_answers"]
        )

        prompt = task["prompt"]
        public_trace = prompt.split("Proposed trace:\n", 1)[1].split("\nProposed final word:", 1)[0]
        parsed_rows = []
        for line_number, line in enumerate(public_trace.splitlines(), 1):
            prefix_text, terms_text = line.split(". ", 1)
            check(prefix_text == str(line_number), number, "Prompt checkpoint numbering is inconsistent")
            parsed_rows.append(json.loads(terms_text))
        check(parsed_rows == observed, number, "Prompt trace differs from stored proposed trace")
        check(f"Proposed final word: {task['proposed_final_answer']}\n" in prompt,
              number, "Prompt omits or changes proposed final word")
        check("donor" not in prompt.lower() and "changed_coordinate" not in prompt,
              number, "Private donor metadata is exposed in prompt")
        check(hashlib.sha256(prompt.encode()).hexdigest() == task["prompt_sha256"],
              number, "Prompt hash mismatch")
        check("different number of steps" in prompt and "Technical suffix markers" in prompt,
              number, "Prompt omits variable-length or technical-marker contract")
        records.append({
            "number": number, "id": task["id"], "first_incorrect_step": first_wrong,
            "raw_target_paths": len(target_raw), "raw_donor_paths": len(donor_raw),
            "compatible_raw_paths": compatible_count, "distinct_gold_repairs": len(expected_answers),
        })

    result = {
        "audit": "Independent VP rederivation; no generator prefix/repair helpers used",
        "vp_version": vidyut.__version__,
        "tasks_sha256": hashlib.sha256(tasks_path.read_bytes()).hexdigest(),
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tasks_checked": len(records), "raw_target_paths": raw_target_paths,
        "raw_donor_paths": raw_donor_paths, "multiple_gold_tasks": multiple_gold_tasks,
        "tasks_with_different_length_valid_repairs": shorter_or_longer_repair_tasks,
        "first_incorrect_step": dict(sorted(Counter(record["first_incorrect_step"] for record in records).items())),
        "findings": findings,
        "passed": not findings and len(records) == 200,
        "limitations": [
            "Verification is relative to VP 0.4.0 and the declared projected trace contract.",
            "The v1 errors substitute a single inflection coordinate, not arbitrary phonological mistakes.",
            "No model difficulty evaluation or comprehensive linguistic-source certification is performed.",
        ],
        "records": records,
    }
    (DIRECTORY / "independent-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
