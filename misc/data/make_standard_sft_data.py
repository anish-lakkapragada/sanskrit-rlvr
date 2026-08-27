#!/usr/bin/env python
"""Build contamination-free translation SFT splits (sft-qwen3-4b-standard-* runs).

data/eval/{samayik,flores-200}.json stay FULL corpus copies; this script derives
from each a finetune/validation split with no leakage between the two:

  1. Pairs sharing a normalized EN or SA sentence (whitespace-collapsed,
     casefolded) are grouped together, so a validation sentence can never
     appear in training with a variant translation (the old exact-(en,sa)
     holdout let ~8% of eval sources leak that way).
  2. Whole groups are seed-42 sampled into a ~VAL_TARGET-pair validation set
     (groups with > MAX_GROUP unique pairs stay in training so one mega-group
     of duplicated boilerplate cannot swallow the validation budget).
  3. Finetune records are then filtered against the validation keys of BOTH
     datasets, so e.g. a Samayik-trained model is clean on the FLORES
     validation set too.

Outputs (data/finetune/sft-standard/):
    {name}_finetune.json    finetune.sft-schema records:
                              prompt:     [{"role": "user", render_translation(en)}]
                              completion: [{"role": "assistant", "<translation>sa</translation>"}]
    {name}_validation.json  raw [{"en", "sa"}] pairs -- same schema as data/eval/,
                            consumed directly by finetune.evals.eval_samayik

No <thinking> block in targets -- this is the plain-SFT baseline; the tags are
kept so finetune.prompts.extract_translation works unchanged at eval time.

Usage:  uv run python misc/data/make_standard_sft_data.py
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from finetune.prompts import render_translation

VAL_TARGET = 750   # validation set size in unique pairs (stops at first crossing)
MAX_GROUP = 20     # groups with more unique pairs than this never enter validation
SEED = 42
OUT_DIR = REPO_ROOT / "data" / "finetune" / "sft-standard"
DATASETS = ("samayik", "flores-200")


def norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def contamination_groups(pairs: list[dict]) -> list[list[int]]:
    """Union-find: pairs sharing a normalized EN or SA sentence share a group."""
    parent = list(range(len(pairs)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner: dict[tuple[str, str], int] = {}
    for i, p in enumerate(pairs):
        for side in ("en", "sa"):
            key = (side, norm(p[side]))
            if not key[1]:
                continue  # empty sentence must not glue unrelated pairs together
            if key in owner:
                parent[find(i)] = find(owner[key])
            else:
                owner[key] = i

    groups = defaultdict(list)
    for i in range(len(pairs)):
        groups[find(i)].append(i)
    return sorted(groups.values(), key=lambda g: g[0])  # deterministic pre-shuffle order


def pick_validation(pairs: list[dict], groups: list[list[int]]) -> list[dict]:
    """Seed-42 whole-group sample of ~VAL_TARGET unique, eval-usable pairs."""
    groups = groups.copy()
    random.Random(SEED).shuffle(groups)
    chosen, seen = [], set()
    for g in groups:
        if len(chosen) >= VAL_TARGET:
            break
        uniq = {(pairs[i]["en"], pairs[i]["sa"]) for i in g}
        if len(uniq) > MAX_GROUP:
            continue
        if any(not norm(pairs[i]["en"]) or not norm(pairs[i]["sa"]) for i in g):
            continue  # empty side -> not scoreable; leave the group in training
        for i in sorted(g):
            key = (pairs[i]["en"], pairs[i]["sa"])
            if key not in seen:
                seen.add(key)
                chosen.append({"en": pairs[i]["en"], "sa": pairs[i]["sa"]})
    return chosen


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    corpora = {n: json.loads((REPO_ROOT / "data" / "eval" / f"{n}.json").read_text())
               for n in DATASETS}

    # --- validation sets first: their keys block finetune records everywhere ---
    validations = {}
    for name, pairs in corpora.items():
        groups = contamination_groups(pairs)
        validations[name] = pick_validation(pairs, groups)
        print(f"{name}: {len(pairs)} pairs in {len(groups)} contamination groups "
              f"-> {len(validations[name])} validation pairs", file=sys.stderr)

    blocked_en = {norm(p["en"]) for v in validations.values() for p in v}
    blocked_sa = {norm(p["sa"]) for v in validations.values() for p in v}

    # --- finetune sets: everything not touching ANY validation set -------------
    for name, pairs in corpora.items():
        records, dropped = [], 0
        for i, p in enumerate(pairs):
            if norm(p["en"]) in blocked_en or norm(p["sa"]) in blocked_sa:
                dropped += 1
                continue
            records.append({
                "id": f"{name}:{i:06d}",
                "en": p["en"],
                "sa": p["sa"],
                "prompt": [{"role": "user", "content": render_translation(p["en"])}],
                "completion": [{"role": "assistant",
                                "content": f"<translation>{p['sa']}</translation>"}],
            })

        for suffix, rows in (("finetune", records), ("validation", validations[name])):
            out = OUT_DIR / f"{name}_{suffix}.json"
            with out.open("w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
                f.write("\n")

        train_en = {norm(r["en"]) for r in records}
        train_sa = {norm(r["sa"]) for r in records}
        assert not train_en & blocked_en and not train_sa & blocked_sa, \
            f"{name}: validation keys leaked into finetune"
        print(f"{name}: {len(records)} finetune records "
              f"({dropped} dropped for validation contamination) "
              f"-> {name}_{{finetune,validation}}.json", file=sys.stderr)


if __name__ == "__main__":
    main()
