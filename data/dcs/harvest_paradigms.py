"""Third pass over the DCS dump: harvest attested paradigm cells.

For the top candidate lemmas (by fragment-usable frequency), collect the
unsandhied surface forms the corpus actually attests, keyed by grammatical
cell. This grounds every classification decision (stem class, ṛ-stem
guṇa/vṛddhi, an-stem weak forms, adjective feminines, athematic verb
paradigms) in corpus evidence rather than memory, and later serves as a
gold source for Lean test theorems.

Output harvest.json:
  { lemma_id: { "lemma": ..., "grammar": ...,
                "nominal": { "Case|Number|Gender": {form: count} },
                "verb":    { "Person|Number": {form: count} },
                "genders": { gender: count } } }
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

corpus_dir = Path("/tmp/dcs-sparse/dcs/data/conllu/files")
here = Path(__file__).parent
freq_path = here / "corpus" / "usable_frequencies.tsv"
out_path = here / "corpus" / "harvest.json"

N_NOUNS, N_VERBS, N_ADJS = 900, 250, 350

def is_verb_tag(g):
    return bool(g) and ((g[0].isdigit() and ("P" in g or "Ā" in g)) or g.startswith("Denom"))

nouns, verbs, adjs = [], [], []
with open(freq_path, encoding="utf-8") as fh:
    for r in csv.reader(fh, delimiter="\t"):
        if r[0] == "lemma_id":
            continue
        lid, lemma, grammar, declined, presind = r[0], r[1], r[2], int(r[4]), int(r[5])
        if grammar in ("m", "f", "n", "mn", "mf", "fn", "mfn"):
            nouns.append((declined, lid))
        elif grammar == "adj":
            adjs.append((declined, lid))
        elif is_verb_tag(grammar):
            verbs.append((presind, lid))
targets = set()
for lst, n in ((nouns, N_NOUNS), (verbs, N_VERBS), (adjs, N_ADJS)):
    lst.sort(reverse=True)
    targets.update(lid for _, lid in lst[:n])

def feat(feats, key):
    pos = feats.find(key + "=")
    if pos == -1:
        return None
    end = feats.find("|", pos)
    return feats[pos + len(key) + 1 : end if end != -1 else len(feats)]

nominal = defaultdict(lambda: defaultdict(Counter))
verbal = defaultdict(lambda: defaultdict(Counter))
genders = defaultdict(Counter)

files = sorted(corpus_dir.rglob("*.conllu"))
for i, f in enumerate(files):
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 10:
                continue
            misc = cols[9]
            p = misc.find("LemmaId=")
            if p == -1:
                continue
            e = misc.find("|", p + 8)
            lid = misc[p + 8 : e if e != -1 else len(misc)]
            if lid not in targets:
                continue
            u = misc.find("Unsandhied=")
            if u == -1:
                continue
            e = misc.find("|", u + 11)
            form = misc[u + 11 : e if e != -1 else len(misc)]
            feats = cols[5]
            case, num, gen = feat(feats, "Case"), feat(feats, "Number"), feat(feats, "Gender")
            if case and case != "Cpd" and num:
                nominal[lid][f"{case}|{num}|{gen or '-'}"][form] += 1
                if gen:
                    genders[lid][gen] += 1
            elif (cols[3] == "VERB" and feat(feats, "Tense") == "Pres"
                  and feat(feats, "Mood") == "Ind" and "Voice=Pass" not in feats):
                person = feat(feats, "Person")
                if person and num:
                    verbal[lid][f"{person}|{num}"][form] += 1
    if (i + 1) % 4000 == 0:
        print(f"  {i + 1}/{len(files)} files", file=sys.stderr)

dictionary = {}
with open("/tmp/dcs_dictionary.csv", encoding="utf-8") as fh:
    for row in csv.reader(fh, delimiter="\t"):
        if row and row[0].isdigit():
            row += [""] * (5 - len(row))
            dictionary[row[0]] = (row[1], row[2])

result = {}
for lid in targets:
    lemma, grammar = dictionary.get(lid, ("?", ""))
    result[lid] = {
        "lemma": lemma,
        "grammar": grammar,
        "nominal": {k: dict(v.most_common()) for k, v in nominal[lid].items()},
        "verb": {k: dict(v.most_common()) for k, v in verbal[lid].items()},
        "genders": dict(genders[lid].most_common()),
    }

with open(out_path, "w", encoding="utf-8") as out:
    json.dump(result, out, ensure_ascii=False, indent=1)
print(f"harvested {len(result)} lemmas -> {out_path}")
