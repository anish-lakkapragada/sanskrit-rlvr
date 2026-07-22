"""Pipeline step 7: corpus-derived noun traits for task templating.

v1's task generator gated templates on hand lists keyed to English glosses
(_NO_PLURAL, _LOC_OK). At 500 nouns that doesn't scale; the corpus already
knows which nouns pluralize and which sit naturally in the locative. This
script reduces harvest.json's attested-cell counters to per-noun boolean
traits, keyed by the *lexicon* lemma (bhagavant -> bhagavat).

Output: corpus/noun_traits.json  {lemma: {plural_ok, dual_ok, loc_ok,
ins_ok, gen_ok, dat_ok, acc_ok, case_counts, number_counts}}
"""

import csv
import json
from collections import Counter
from pathlib import Path

here = Path(__file__).parent

MIN_PLUR_SHARE, MIN_PLUR_N = 0.05, 5
MIN_DUAL_N = 3
MIN_CASE_N = {"Loc": 5, "Ins": 5, "Gen": 5, "Acc": 5, "Dat": 3}

NOUN_TAGS = {"m", "f", "n", "mn", "mf", "fn", "mfn"}


def lexicon_lemma(dcs_lemma: str) -> str:
    return dcs_lemma[:-2] + "t" if dcs_lemma.endswith("ant") else dcs_lemma


selected = set()
with open(here / "selection" / "selection_nouns.tsv", encoding="utf-8") as fh:
    for row in list(csv.reader(fh, delimiter="\t"))[1:]:
        selected.add(lexicon_lemma(row[0]))

harvest = json.load(open(here / "corpus" / "harvest.json", encoding="utf-8"))

case_counts = {l: Counter() for l in selected}
number_counts = {l: Counter() for l in selected}
for entry in harvest.values():
    lemma = lexicon_lemma(entry["lemma"])
    if lemma not in selected or entry["grammar"] not in NOUN_TAGS:
        continue
    for cell, forms in entry["nominal"].items():
        case, num, _gender = cell.split("|")
        n = sum(forms.values())
        if case != "Cpd":
            case_counts[lemma][case] += n
            number_counts[lemma][num] += n

traits = {}
for lemma in sorted(selected):
    cc, nc = case_counts[lemma], number_counts[lemma]
    total = sum(nc.values())
    traits[lemma] = {
        "plural_ok": total > 0 and nc["Plur"] >= MIN_PLUR_N
                     and nc["Plur"] / total >= MIN_PLUR_SHARE,
        "dual_ok": nc["Dual"] >= MIN_DUAL_N,
        **{f"{case.lower()}_ok": cc[case] >= n for case, n in MIN_CASE_N.items()},
        "case_counts": dict(cc),
        "number_counts": dict(nc),
    }

out = here / "corpus" / "noun_traits.json"
json.dump(traits, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
n_pl = sum(t["plural_ok"] for t in traits.values())
n_loc = sum(t["loc_ok"] for t in traits.values())
print(f"wrote {out}: {len(traits)} nouns ({n_pl} plural_ok, {n_loc} loc_ok)")
