#!/usr/bin/env python3
"""Generate and fingerprint new VP creation tasks without model calls."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import re
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign as campaign, oai_batch_eval as base
from finetune.prompts import slp1_to_devanagari
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Data, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana
import vidyut

OUT = campaign.OUT
SEED = 20261006
TSV = ROOT / "data/finetune/task-data/vidyut_dhatupatha_5.tsv"


def name(value):
    return repr(value).split(".")[-1]


def family(entry):
    return entry.dhatu.aupadeshika + "|" + name(entry.dhatu.gana)


def load_entries():
    with tempfile.TemporaryDirectory(prefix="vp-campaign-") as directory:
        Path(directory, "dhatupatha.tsv").symlink_to(TSV)
        return Data(directory).load_dhatu_entries()


def split_families():
    if (OUT / "family-split.json").exists():
        return base.read_json(OUT / "family-split.json")
    entries = load_entries()
    groups = defaultdict(list)
    for entry in entries:
        groups[family(entry)].append(entry.code)
    # Counts are allocated from a score-independent seeded permutation.
    ordered = sorted(groups, key=lambda f: hashlib.sha256(f"{SEED}:{f}".encode()).hexdigest())
    assignments = {f: {"split": "test" if i < 1000 else "development" if i < 1700 else "rl_train",
                        "codes": groups[f]} for i, f in enumerate(ordered)}
    data = {"seed": SEED, "created_at": base.now(), "source_sha256": base.sha256(TSV),
            "grouping": "Exact Dhatupatha citation + gana; duplicate code entries stay together",
            "families": assignments, "counts": dict(Counter(v["split"] for v in assignments.values())),
            "training_status": "Requires a new learner trained only on rl_train families. Existing checkpoints are not certified clean.",
            "prior_exposure": "Legacy analysis inspected all families; new discovery fitting excludes all reserved test-family legacy records."}
    base.atomic_json(OUT / "family-split.json", data)
    with base.lock(OUT):
        state = campaign.load()
        state["family_split_sha256"] = base.sha256(OUT / "family-split.json")
        campaign.save(state)
    print(json.dumps(data["counts"]), flush=True)
    return data


def connect():
    db = sqlite3.connect(OUT / "candidates.sqlite")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS candidates (id TEXT PRIMARY KEY, family TEXT, split TEXT, code TEXT, lakara TEXT, prayoga TEXT, purusha TEXT, vacana TEXT, gold TEXT, rules TEXT, min_steps INTEGER, variants INTEGER)")
    db.execute("CREATE INDEX IF NOT EXISTS candidate_split ON candidates(split)")
    db.execute("CREATE TABLE IF NOT EXISTS generated (code TEXT PRIMARY KEY, tasks INTEGER)")
    return db


def generate():
    splits = split_families()
    entries = load_entries()
    db = connect()
    completed = {row[0] for row in db.execute("SELECT code FROM generated")}
    grammar = Vyakarana()
    lakaras = [v for v in Lakara.choices() if name(v) != "Let"]
    # Exclude all impersonal tasks during discovery to avoid both known audit clusters.
    # Passive constructions are candidates only: semantic validity still needs review.
    coordinates = list(itertools.product(lakaras, [Prayoga.Kartari, Prayoga.Karmani], Purusha.choices(), Vacana.choices()))
    for i, entry in enumerate(entries, 1):
        f = family(entry)
        split = splits["families"][f]["split"]
        if split == "rl_train" or entry.code in completed:
            continue
        records = []
        for la, pr, pu, va in coordinates:
            derivations = grammar.derive(Pada.Tinanta(dhatu=entry.dhatu, lakara=la, prayoga=pr, purusha=pu, vacana=va))
            if not derivations:
                continue
            gold = sorted({p.text for p in derivations})
            for form in gold:
                assert transliterate(slp1_to_devanagari(form), Scheme.Devanagari, Scheme.Slp1) == form
            codes = sorted({h.code for p in derivations for h in p.history if name(h.source) == "Ashtadhyayi"})
            coord = tuple(name(v) for v in (la, pr, pu, va))
            tid = entry.code + ":" + ":".join(coord)
            records.append((tid, f, split, entry.code, *coord, json.dumps(gold), json.dumps(codes),
                            min(len(p.history) for p in derivations), len(gold)))
        db.executemany("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", records)
        db.execute("INSERT INTO generated VALUES (?,?)", (entry.code, len(records)))
        db.commit()
        if i % 100 == 0:
            print(f"Generated through root entry {i}/{len(entries)}", flush=True)
    totals = dict(db.execute("SELECT split,COUNT(*) FROM candidates GROUP BY split"))
    meta = {"created_at": base.now(), "vidyut_version": vidyut.__version__, "source_sha256": base.sha256(TSV),
            "split_sha256": base.sha256(OUT / "family-split.json"), "candidate_counts": totals,
            "coordinate_scope": "10 classical lakaras; active/passive, all person-number combinations; no prefixes or sanadi",
            "excluded": ["Let (Vedic)", "all Bhave (both historical audit clusters)", "empty derivation sets", "RL-training families"],
            "audit_status": "Engine generation + complete VP variant sets + transliteration round-trip. Not yet independent linguistic certification; passive semantics and discovered error constructions require review before calibration/final release."}
    base.atomic_json(OUT / "candidate-generation.json", meta)
    print(json.dumps(meta, indent=2), flush=True)


def row_task(row, entries, reason=None):
    tid, f, split, code, la, pr, pu, va, gold, rules, steps, variants = row
    entry = entries[code]
    return {"id": tid, "dhatu": {"code": code, "aupadeshika": entry.dhatu.aupadeshika,
            "gana": name(entry.dhatu.gana), "artha": entry.artha},
            "morphology": {"lakara": la, "prayoga": pr, "purusha": pu, "vacana": va},
            "gold_slp1": json.loads(gold), "gold_devanagari": [slp1_to_devanagari(v) for v in json.loads(gold)],
            "campaign": {"root_family": f, "split": split, "trace_rule_ids": json.loads(rules),
                         "minimum_trace_steps": steps, "gold_variants": variants,
                         "selection_reason": reason, "audit_status": "VP_consistency_passed; independent_construction_review_pending"}}


def sample_discovery():
    if (OUT / "discovery-manifest.json").exists():
        print("Discovery already frozen; preserving task lists", flush=True)
        return
    db = connect()
    entries = {e.code: e for e in load_entries()}
    splits = base.read_json(OUT / "family-split.json")
    study = base.read_json(ROOT / "benchmarks/analysis/performance-study/study.json")
    op = next(i for i, m in enumerate(study["models"]) if m["id"] == "claude-opus-5-5-xhigh")
    oh = next(i for i, m in enumerate(study["models"]) if m["id"] == "claude-opus-5-5-high")
    ah = next(i for i, m in enumerate(study["models"]) if m["id"] == "gpt-6-astra-high")
    legacy_ids = {t["id"] for t in study["tasks"]}
    legacy_dev = [t for t in study["tasks"] if splits["families"][t["slp1"] + "|" + t["gana"]]["split"] == "development" and t["prayoga"] != "Bhave"]
    rule_total, rule_misses = Counter(), Counter()
    coord_total, coord_misses = Counter(), Counter()
    used_legacy, excluded_signals = [], []
    def orthographic_key(text):
        text = text or ""
        for nasal, following in (("ङ", "कखगघ"), ("ञ", "चछजझ"), ("ण", "टठडढ"), ("न", "तथदध"), ("म", "पफबभ")):
            text = re.sub(nasal + "्(?=[" + following + "])", "ं", text)
        return text
    for t in legacy_dev:
        row = db.execute("SELECT rules FROM candidates WHERE id=?", (t["id"],)).fetchone()
        if row is None:
            continue
        # Fixed historical signal: Opus xHigh failure or both High models fail.
        gold_keys = {orthographic_key(v) for v in t["gold"]}
        def substantive_miss(index):
            answer = t["answers"][index]
            return t["scores"][index] == 0 and answer is not None and orthographic_key(answer) not in gold_keys
        miss = substantive_miss(op) or (substantive_miss(oh) and substantive_miss(ah))
        if t["scores"][op] == 0 and not substantive_miss(op):
            excluded_signals.append({"task_id": t["id"], "reason": "missing answer or nasal spelling alone; not a difficulty lead"})
        rules = json.loads(row[0])
        rule_total.update(rules)
        if miss:
            rule_misses.update(rules)
        coord = (t["lakara"], t["prayoga"], t["purusha"], t["vacana"])
        coord_total[coord] += 1
        coord_misses[coord] += int(miss)
        used_legacy.append(t["id"])
    enriched = {r: (rule_misses[r] + 1) / (n + 20) for r, n in rule_total.items()
                if n >= 8 and rule_misses[r] >= 2 and r.split(".")[0] in {"3", "6", "7", "8"}}
    rows = list(db.execute("SELECT * FROM candidates WHERE split='development'"))
    rows = [r for r in rows if r[0] not in legacy_ids]
    # Deduplicate exact model-visible prompts, independent of expected answer or scores.
    seen, unique = set(), []
    for r in rows:
        e = entries[r[3]]
        key = (e.dhatu.aupadeshika, name(e.dhatu.gana), e.artha, *r[4:8])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    rows = unique
    frequency = Counter(rule for r in rows for rule in json.loads(r[9]))
    tie = lambda r: hashlib.sha256(f"{SEED}:discovery:{r[0]}".encode()).hexdigest()
    def analogy(r):
        rules = json.loads(r[9])
        strongest = max((enriched.get(rule, 0) for rule in rules), default=0)
        coord = tuple(r[4:8])
        return strongest + .2 * (coord_misses[coord] + 1) / (coord_total[coord] + 20)
    def unusual(r):
        values = sorted((1 / frequency[rule] for rule in json.loads(r[9])
                         if rule.split(".")[0] in {"3", "6", "7", "8"}), reverse=True)
        return sum(values[:4]) + .0002 * r[10] + .002 * min(r[11], 6)
    rankings = {"failure_analogues": sorted(rows, key=lambda r: (-analogy(r), tie(r))),
                "unusual_rule_combinations": sorted(rows, key=lambda r: (-unusual(r), tie(r))),
                "coverage_controls": sorted(rows, key=tie)}
    selected, family_counts, cell_counts = set(), Counter(), Counter()
    batches = []
    for batch in range(1, 4):
        tasks = []
        for category, n in (("failure_analogues", 1000), ("unusual_rule_combinations", 500), ("coverage_controls", 500)):
            chosen = 0
            for row in rankings[category]:
                if row[0] in selected or family_counts[row[1]] >= 18 or cell_counts[(row[1], row[4], row[5])] >= 3:
                    continue
                selected.add(row[0]); family_counts[row[1]] += 1; cell_counts[(row[1], row[4], row[5])] += 1
                tasks.append(row_task(row, entries, {"category": category, "batch": batch,
                                  "analogy_score": analogy(row), "unusual_score": unusual(row)}))
                chosen += 1
                if chosen == n:
                    break
            if chosen != n:
                raise ValueError(f"Insufficient candidates for {category}: {chosen}/{n}")
        random.Random(SEED + batch).shuffle(tasks)
        path = OUT / f"discovery-{batch:02d}.json"
        base.atomic_json(path, tasks)
        batches.append({"path": path.name, "n": len(tasks), "digest": campaign.digest(tasks),
                        "families": len({t["campaign"]["root_family"] for t in tasks}),
                        "lakaras": dict(Counter(t["morphology"]["lakara"] for t in tasks)),
                        "voices": dict(Counter(t["morphology"]["prayoga"] for t in tasks))})
    manifest = {"created_at": base.now(), "seed": SEED, "phase": "discovery",
                "split_sha256": base.sha256(OUT / "family-split.json"), "batches": batches,
                "unique_tasks": len(selected), "root_families": len(family_counts),
                "legacy_fit_task_ids": used_legacy, "rule_enrichment": enriched, "excluded_historical_error_signals": excluded_signals,
                "sampling": "Fixed score-independent family split, development-only legacy enrichment, full local generation; no legacy task IDs or exact prompt duplicates. Max 18 per family, 3 per family/lakara/voice; candidates include successes.",
                "review_gate": "Each batch must be reviewed before the next submission. Discovery candidates are not final benchmark members or independently certified keys."}
    base.atomic_json(OUT / "discovery-manifest.json", manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ("legacy_fit_task_ids", "rule_enrichment")}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["generate", "sample"])
    args = parser.parse_args()
    generate() if args.command == "generate" else sample_discovery()


if __name__ == "__main__":
    main()
