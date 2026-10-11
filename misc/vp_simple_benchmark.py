#!/usr/bin/env python3
"""Build a deterministic forward-morphology prototype and score saved responses.

No model calls. Test membership never depends on model outputs or scores.
Primary generalization: new tense/voice cells within the original training vocabulary.
Original validation citation+class families are excluded from all new training data.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finetune.prompts import LAKARA_EN, PRAYOGA_EN, PURUSHA_EN, VACANA_EN, GANA_EN, slp1_to_devanagari

SEED = "vp-simple-forward-v1-20261010"
LAKARAS = tuple(LAKARA_EN)
VOICES = ("Kartari",)
PERSONS = ("Prathama", "Madhyama", "Uttama")
NUMBERS = ("Eka", "Dvi", "Bahu")
CELLS = tuple(itertools.product(LAKARAS, VOICES))
QUOTAS = {"train": 2000, "dev": 40, "test": 100}  # Per tense/voice cell.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank(*items):
    data = json.dumps([SEED, *items], ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def enum_name(value):
    return repr(value).split(".")[-1]


def family_of(task):
    return task["dhatu"]["aupadeshika"] + "|" + task["dhatu"]["gana"]


def semantic_key(task):
    m = task["morphology"]
    return family_of(task), m["lakara"], m["prayoga"], m["purusha"], m["vacana"]


def render(task):
    d, m = task["dhatu"], task["morphology"]
    return (
        "Derive one classical Sanskrit conjugated verb form from the information below.\n"
        "The root is given in its dictionary citation form, including grammatical markers.\n"
        "Use its ordinary dictionary formation and required prefixes; add no extra derivation or prefix.\n"
        "Use your own knowledge without tools or internet search.\n\n"
        f"dhatu (root): {slp1_to_devanagari(d['aupadeshika'])}\n"
        f"gana (verb class): {d['gana']} ({GANA_EN[d['gana']]})\n"
        f"artha (dictionary meaning): {slp1_to_devanagari(d['artha'])}\n\n"
        "Required form:\n"
        f"- lakara (tense/mood): {m['lakara']} ({LAKARA_EN[m['lakara']]})\n"
        f"- prayoga (voice): {m['prayoga']} ({PRAYOGA_EN[m['prayoga']]})\n"
        f"- purusha (person): {m['purusha']} ({PURUSHA_EN[m['purusha']]})\n"
        f"- vacana (number): {m['vacana']} ({VACANA_EN[m['vacana']]})\n\n"
        "You may reason before your final answer. Give exactly one permitted form in Devanagari, IAST, or SLP1 "
        "inside one <answer></answer> block. Any permitted pada or optional variant is accepted."
    )


def extract(text):
    if text.count("<answer>") != 1 or text.count("</answer>") != 1:
        return None
    match = re.search(r"<answer>([^<>]+)</answer>", text, re.DOTALL)
    return unicodedata.normalize("NFC", match[1]).strip() if match else None


def correct(task, text):
    answer = extract(text)
    return answer is not None and answer in {
        unicodedata.normalize("NFC", value).strip()
        for key in ("gold_devanagari", "gold_iast", "gold_slp1") for value in task[key]}


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def build(out):
    import vidyut
    from vidyut.lipi import Scheme, transliterate
    from vidyut.prakriya import Data, Vyakarana, Pada, Lakara, Prayoga, Purusha, Vacana
    if vidyut.__version__ != "0.4.0":
        raise ValueError("This prototype pins vidyut==0.4.0")
    if (out / "manifest.json").exists():
        raise ValueError("Refusing to overwrite a frozen build; use a new output directory")
    source = ROOT / "data/finetune/task-data"
    paths = [source / f"{split}.json" for split in ("finetune", "validation")]
    original_train, original_val = [json.loads(p.read_text()) for p in paths]
    legacy = original_train + original_val
    legacy_ids = {t["id"] for t in legacy}
    grpo_path = ROOT / "data/data-mixture/grpo-prompts.json"
    sft_path = ROOT / "data/data-mixture/tb20m/samayik67.json"
    assert {t["id"] for t in json.loads(grpo_path.read_text())} <= legacy_ids
    assert {t["id"] for t in json.loads(sft_path.read_text()) if t["task"] == "morphology"} <= legacy_ids
    paths.extend([grpo_path, sft_path, source / "vidyut_dhatupatha_5.tsv", Path(__file__), ROOT / "finetune/prompts.py"])
    validation_families = {family_of(t) for t in original_val}
    allowed_families = {family_of(t) for t in original_train} - validation_families
    legacy_keys = {semantic_key(t) for t in legacy}
    legacy_cells = defaultdict(set)
    for t in legacy:
        legacy_cells[family_of(t)].add((t["morphology"]["lakara"], t["morphology"]["prayoga"]))
    with tempfile.TemporaryDirectory(prefix="vp-simple-dictionary-") as temp:
        (Path(temp) / "dhatupatha.tsv").symlink_to((source / "vidyut_dhatupatha_5.tsv").resolve())
        entries = Data(temp).load_dhatu_entries()
    representatives = {}
    for entry in sorted(entries, key=lambda e: e.code):
        family = entry.dhatu.aupadeshika + "|" + enum_name(entry.dhatu.gana)
        if family in allowed_families:
            representatives.setdefault(family, entry)
    assert set(representatives) == allowed_families
    reserved = {}
    for family in sorted(representatives):
        fresh = sorted((c for c in CELLS if c not in legacy_cells[family]), key=lambda c: rank("reserve", family, c))
        assert len(fresh) >= 2
        reserved[family] = {"test": fresh[0], "dev": fresh[1]}
    v = Vyakarana(log_steps=False)
    counts = Counter()

    def derive(family, cell, person, number, split):
        entry = representatives[family]
        la, pr = cell
        request = Pada.Tinanta(dhatu=entry.dhatu, lakara=getattr(Lakara, la), prayoga=getattr(Prayoga, pr),
                              purusha=getattr(Purusha, person), vacana=getattr(Vacana, number))
        forms = sorted({p.text for p in v.derive(request)})
        counts["derivation_requests"] += 1
        if not forms:
            counts["empty_requests_skipped"] += 1
            return None
        row = {"id": "vps1-" + rank("task", family, cell, person, number)[:20], "split": split,
               "root_family": family, "dhatu": {"code": entry.code, "aupadeshika": entry.dhatu.aupadeshika,
                    "gana": enum_name(entry.dhatu.gana), "artha": entry.artha},
               "morphology": {"lakara": la, "prayoga": pr, "purusha": person, "vacana": number},
               "gold_slp1": forms,
               "gold_devanagari": sorted({transliterate(s, Scheme.Slp1, Scheme.Devanagari) for s in forms}),
               "gold_iast": sorted({transliterate(s, Scheme.Slp1, Scheme.Iast) for s in forms})}
        row["prompt"] = render(row)
        return row

    datasets = {}
    for split in ("test", "dev", "train"):
        rows = []
        for cell in CELLS:
            if split == "train":
                candidates = [(f, pe, nu) for f in representatives
                              if cell not in reserved[f].values()
                              for pe, nu in itertools.product(PERSONS, NUMBERS)
                              if (f, *cell, pe, nu) not in legacy_keys]
                candidates.sort(key=lambda x: rank("training-order", cell, x))
            else:
                families = sorted((f for f in representatives if reserved[f][split] == cell),
                                  key=lambda f: rank("evaluation-order", split, cell, f))
                candidates = [(f, pe, nu) for f in families for pe, nu in sorted(itertools.product(PERSONS, NUMBERS),
                              key=lambda x: rank("person-number", split, f, x))]
            accepted, used_families = [], Counter()
            for family, person, number in candidates:
                if used_families[family] >= (4 if split == "train" else 1):
                    continue
                row = derive(family, cell, person, number, split)
                if row is not None:
                    accepted.append(row)
                    used_families[family] += 1
                if len(accepted) == QUOTAS[split]:
                    break
            if len(accepted) != QUOTAS[split]:
                raise ValueError(f"Insufficient candidates for {split} {cell}: {len(accepted)}")
            rows.extend(accepted)
        rows.sort(key=lambda r: rank("release-order", split, r["id"]))
        datasets[split] = rows
        print(split, len(rows), flush=True)

    all_keys = [semantic_key(t) for rows in datasets.values() for t in rows]
    assert len(all_keys) == len(set(all_keys)) and not set(all_keys) & legacy_keys
    train_cells = {(r["root_family"], r["morphology"]["lakara"], r["morphology"]["prayoga"]) for r in datasets["train"]}
    for split in ("dev", "test"):
        assert len({r["root_family"] for r in datasets[split]}) == len(datasets[split])
        assert not train_cells & {(r["root_family"], r["morphology"]["lakara"], r["morphology"]["prayoga"]) for r in datasets[split]}
    assert not {r["root_family"] for r in datasets["train"]} & validation_families
    for rows in datasets.values():
        for task in rows:
            for key in ("gold_slp1", "gold_iast", "gold_devanagari"):
                assert all(correct(task, f"Reasoning is optional.\n<answer>{a}</answer>") for a in task[key])
            assert not correct(task, "<answer>not-a-Sanskrit-form</answer>")
    out.mkdir(parents=True, exist_ok=True)
    for split, rows in datasets.items():
        write_rows(out / f"{split}.jsonl", rows)
        write_rows(out / f"{split}-prompts.jsonl", [{"id": r["id"], "prompt": r["prompt"]} for r in rows])
    write_json(out / "train-sft.json", [{"id": r["id"], "task": "morphology",
        "prompt": [{"role": "user", "content": r["prompt"]}],
        "completion": [{"role": "assistant", "content": "<answer>" + r["gold_devanagari"][int(rank("gold", r["id"]), 16) % len(r["gold_devanagari"])] + "</answer>"}]}
        for r in datasets["train"]])
    write_json(out / "reserved-cells.json", reserved)
    files = sorted([out / f"{split}{suffix}.jsonl"
                    for split in datasets for suffix in ("", "-prompts")]
                   + [out / "train-sft.json", out / "reserved-cells.json"])
    manifest = {"name": "VP-Simple v1", "status": "Generated development prototype; not yet an independently adjudicated benchmark or an evaluated leaderboard.",
        "seed": SEED, "vidyut_version": vidyut.__version__, "scope": {"lakaras": LAKARAS, "prayogas": VOICES,
        "persons": PERSONS, "numbers": NUMBERS, "formation": "ordinary dictionary formation, no added sanadi or prefix"},
        "counts": {s: len(rs) for s, rs in datasets.items()}, "quota_per_tense_voice_cell": QUOTAS,
        "split": "New tense+voice cells within the original training vocabulary; all persons/numbers of reserved cells excluded from train; no reserved cell appears in the original 6687 tasks.",
        "family_definition": "exact dictionary citation (aupadeshika) + gana; not a claim of all-senses/alias disjointness",
        "original_validation_preserved": True, "new_training_uses_original_validation_families": False,
        "root_families_available": len(representatives), "derivation_counts": dict(counts),
        "scoring": "One nonempty answer block, optional reasoning outside; exact NFC+trim membership in any of three script lists; no reasoning-format bonus; same parser for all models.",
        "limitations": ["This tests new conjugation cells for familiar vocabulary, not wholly unseen-root generalization.",
            "Voice is fixed to Kartari in this first version; passive and impersonal constructions are out of scope.",
            "Pure VP 0.4.0 reference; software reproducibility is checked, independent linguistic adjudication is still needed.",
            "Known older prompts and model outputs are excluded from selection logic; previous evaluations may still have exposed related roots and forms.",
            "No claim that Qwen3-4B beats any frontier model; no model inference or training has been run on these files."],
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in paths},
        "output_sha256": {p.name: sha(p) for p in files}}
    write_json(out / "manifest.json", manifest)


def score(task_path, response_path, out):
    tasks = {r["id"]: r for r in map(json.loads, task_path.read_text().splitlines())}
    seen, per_task = set(), defaultdict(list)
    for row in map(json.loads, response_path.read_text().splitlines()):
        tid, trial = row["task_id"], row["trial"]
        if tid not in tasks or type(trial) is not int or trial not in range(1, 5) or (tid, trial) in seen:
            raise ValueError("Unexpected or duplicate task/trial")
        if row.get("status", "completed") not in {"completed", "incomplete"}:
            raise ValueError("Unresolved infrastructure result; do not turn missing data into a grammar failure")
        if not isinstance(row["output_text"], str):
            raise ValueError("output_text must be a string")
        seen.add((tid, trial))
        per_task[tid].append({"trial": trial, "correct": correct(tasks[tid], row["output_text"]),
                              "answer": extract(row["output_text"]), "truncated": bool(row.get("truncated", False))})
    if len(seen) != 4 * len(tasks):
        raise ValueError("Scoring requires four recorded trials for every task; missing trials remain unresolved")
    n = len(tasks)
    write_json(out, {"tasks": n, "trials": 4 * n,
        "pass_at_1": sum(r["correct"] for rs in per_task.values() for r in rs) / (4 * n),
        "pass_at_4": sum(any(r["correct"] for r in rs) for rs in per_task.values()) / n,
        "truncated_trials": sum(r["truncated"] for rs in per_task.values() for r in rs),
        "tasks_sha256": sha(task_path), "responses_sha256": sha(response_path),
        "per_task": {tid: sorted(rs, key=lambda r: r["trial"]) for tid, rs in sorted(per_task.items())}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", type=Path, default=ROOT / "benchmarks/vp-simple-v1")
    s = sub.add_parser("score")
    s.add_argument("--tasks", type=Path, required=True)
    s.add_argument("--responses", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build":
        build(args.out)
    else:
        score(args.tasks, args.responses, args.out)


if __name__ == "__main__":
    main()
