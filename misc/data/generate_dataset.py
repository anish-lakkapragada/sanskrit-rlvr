#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Generate tinanta fine-tune/eval datasets from the Dhatupatha.

For every usable dhatu in data/finetune/task-data/vidyut_dhatupatha_5.tsv, sample
PER_DHATU random coordinate tuples (lakara x prayoga x purusha x vacana),
derive the gold forms with vidyut-prakriya, transliterate to Devanagari with
vidyut-lipi, and split dhatu-wise into data/finetune/task-data/finetune.json (90%) and
data/finetune/task-data/validation.json (10%). Fully deterministic given SEED.

Usage:  uv run misc/data/generate_dataset.py
"""

import json
import os
import random
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import (
    Data, Dhatu, Gana, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana,
)

ROOT = Path(__file__).resolve().parents[2]
TSV = ROOT / "data" / "finetune" / "task-data" / "vidyut_dhatupatha_5.tsv"
OUT_TRAIN = ROOT / "data" / "finetune" / "task-data" / "finetune.json"
OUT_EVAL = ROOT / "data" / "finetune" / "task-data" / "validation.json"
OUT_META = ROOT / "data" / "finetune" / "task-data" / "metadata.json"

SEED = 42
PER_DHATU = 3
EVAL_FRAC = 0.10
MAX_ATTEMPTS = 25  # coordinate re-draws per task slot before giving up

V = Vyakarana()


def name(enum_val) -> str:
    """Python variant name, e.g. Lakara.VidhiLin -> 'VidhiLin'."""
    return repr(enum_val).split(".")[-1]


def load_entries():
    """Load via vidyut's official loader (applies antargana metadata).

    Data(path) expects a directory containing 'dhatupatha.tsv', so expose our
    TSV under that name via a symlink in a temp dir.
    """
    tmp = tempfile.mkdtemp(prefix="vidyut-dhatupatha-")
    os.symlink(TSV, Path(tmp) / "dhatupatha.tsv")
    return Data(tmp).load_dhatu_entries()


def derive_forms(dhatu, lakara, prayoga, purusha, vacana) -> list[str]:
    try:
        prakriyas = V.derive(Pada.Tinanta(
            dhatu=dhatu, prayoga=prayoga, lakara=lakara,
            purusha=purusha, vacana=vacana,
        ))
    except Exception:
        return []
    return sorted({p.text for p in prakriyas})


def sanity_checks(entries) -> None:
    by_code = {e.code: e for e in entries}
    bu = by_code["01.0001"].dhatu
    assert derive_forms(bu, Lakara.Lat, Prayoga.Kartari, Purusha.Prathama,
                        Vacana.Eka) == ["Bavati"]
    badh = by_code["01.0005"].dhatu
    assert derive_forms(badh, Lakara.Lat, Prayoga.Kartari, Purusha.Prathama,
                        Vacana.Eka) == ["bADate"], "bADf~\\ must be atmanepada-only"
    assert derive_forms(bu, Lakara.Lun, Prayoga.Karmani, Purusha.Prathama,
                        Vacana.Eka), "passive aorist of BU must derive"
    cita = by_code["10.0192"].dhatu  # Akusmiya antargana
    assert derive_forms(cita, Lakara.Lat, Prayoga.Kartari, Purusha.Prathama,
                        Vacana.Eka) == ["cetayate"], "antargana metadata missing"
    print("sanity checks passed", file=sys.stderr)


def main() -> None:
    rng = random.Random(SEED)
    entries = load_entries()
    print(f"loaded {len(entries)} dhatu entries", file=sys.stderr)
    sanity_checks(entries)

    lakaras = [l for l in Lakara.choices() if name(l) != "Let"]
    prayogas = Prayoga.choices()
    purushas = Purusha.choices()
    vacanas = Vacana.choices()

    tasks_by_code: dict[str, list[dict]] = {}
    dropped: list[str] = []
    shortfall = 0

    for i, e in enumerate(entries, 1):
        if i % 250 == 0:
            print(f"  {i}/{len(entries)} dhatus...", file=sys.stderr)
        used: set[tuple] = set()
        tasks: list[dict] = []
        for _slot in range(PER_DHATU):
            for _attempt in range(MAX_ATTEMPTS):
                la = rng.choice(lakaras)
                pr = rng.choice(prayogas)
                pu = rng.choice(purushas)
                va = rng.choice(vacanas)
                key = (name(la), name(pr), name(pu), name(va))
                if key in used:
                    continue
                forms = derive_forms(e.dhatu, la, pr, pu, va)
                if not forms:
                    continue
                used.add(key)
                tasks.append({
                    "id": f"{e.code}:{key[0]}:{key[1]}:{key[2]}:{key[3]}",
                    "dhatu": {
                        "code": e.code,
                        "aupadeshika": e.dhatu.aupadeshika,
                        "gana": name(e.dhatu.gana),
                        "artha": e.artha,
                    },
                    "morphology": {
                        "lakara": key[0],
                        "prayoga": key[1],
                        "purusha": key[2],
                        "vacana": key[3],
                    },
                    "gold_slp1": forms,
                    "gold_devanagari": [
                        transliterate(f, Scheme.Slp1, Scheme.Devanagari)
                        for f in forms
                    ],
                })
                break
        if tasks:
            tasks_by_code[e.code] = tasks
            shortfall += PER_DHATU - len(tasks)
        else:
            dropped.append(e.code)

    # Dhatu-level split: no root appears in both files.
    codes = sorted(tasks_by_code)
    random.Random(SEED + 1).shuffle(codes)
    n_eval = round(EVAL_FRAC * len(codes))
    eval_codes = set(codes[:n_eval])
    train = [t for c in sorted(tasks_by_code) if c not in eval_codes
             for t in tasks_by_code[c]]
    evaluation = [t for c in sorted(eval_codes) for t in tasks_by_code[c]]

    # Round-trip transliteration check on a random sample.
    sample = random.Random(SEED + 2).sample(train + evaluation,
                                            min(100, len(train) + len(evaluation)))
    for t in sample:
        for slp1, deva in zip(t["gold_slp1"], t["gold_devanagari"]):
            back = transliterate(deva, Scheme.Devanagari, Scheme.Slp1)
            assert back == slp1, f"round-trip failed: {slp1} -> {deva} -> {back}"
    print("round-trip transliteration check passed (100 tasks)", file=sys.stderr)

    OUT_TRAIN.write_text(json.dumps(train, ensure_ascii=False, indent=1) + "\n")
    OUT_EVAL.write_text(json.dumps(evaluation, ensure_ascii=False, indent=1) + "\n")
    meta = {
        "seed": SEED,
        "vidyut_version": vidyut.__version__,
        "source_tsv": str(TSV.relative_to(ROOT)),
        "per_dhatu": PER_DHATU,
        "eval_fraction": EVAL_FRAC,
        "coordinate_space": {
            "lakara": [name(l) for l in lakaras],
            "prayoga": [name(p) for p in prayogas],
            "purusha": [name(p) for p in purushas],
            "vacana": [name(v) for v in vacanas],
        },
        "counts": {
            "dhatus_loaded": len(entries),
            "dhatus_kept": len(tasks_by_code),
            "dhatus_dropped": len(dropped),
            "dhatus_eval": len(eval_codes),
            "tasks_train": len(train),
            "tasks_eval": len(evaluation),
            "task_shortfall": shortfall,
        },
        "dropped_codes": dropped,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    OUT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps(meta["counts"], indent=2))
    print(f"wrote {OUT_TRAIN.name}, {OUT_EVAL.name}, {OUT_META.name}")


if __name__ == "__main__":
    main()
