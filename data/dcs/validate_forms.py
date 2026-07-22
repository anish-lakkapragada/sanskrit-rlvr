"""Validate generated Lean forms against corpus-attested cells.

For every selected lemma, compare each DCS-attested (case, number) cell in
harvest.json with the forms the Lean `export` binary generates. A cell
matches if the attested unsandhied form equals a generated form, up to
final-consonant normalization (DCS stores underlying finals: manas, vāc;
the Lean citation forms are pausa: manaḥ, vāk).

Usage: python3 validate_forms.py [min_count]
  min_count - ignore attested cells seen fewer than this many times
              (default 3; hapax cells are mostly annotation noise)
"""

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

here = Path(__file__).parent
min_count = int(sys.argv[1]) if len(sys.argv) > 1 else 3

CASES = {"Nom": "nom", "Acc": "acc", "Ins": "ins", "Dat": "dat",
         "Abl": "abl", "Gen": "gen", "Loc": "loc", "Voc": "voc"}
NUMS = {"Sing": "sg", "Dual": "du", "Plur": "pl"}

# final-consonant neutralization: pausa (generated) vs underlying (DCS)
def norm(w: str) -> str:
    if w.endswith("ant"):  # DCS stores bhagavant for bhagavān/jagat
        return w[:-3] + "ān"
    for pausa, under in (("ḥ", "s"), ("ḥ", "r"), ("k", "c"), ("k", "ś"),
                         ("ṭ", "ś"), ("ṭ", "j"), ("t", "d"), ("t", "dh"), ("k", "j")):
        if w.endswith(under):
            w = w[: -len(under)] + pausa
            break
    return w

def fold(w: str) -> str:
    """Retroflex-folded comparison tier (DCS unsandhied often derétroflexes)."""
    return norm(w).replace("ṇ", "n").replace("ant", "at").replace("ān", "at")

export = subprocess.run([str(here.parent.parent / "lean" / ".lake" / "build" / "bin" / "export")],
                        capture_output=True, text=True, check=True).stdout
generated = defaultdict(set)   # (kind, lemma, case, num) -> {forms}
entry_gender = {}
lemmas_in_lexicon = set()
for line in export.splitlines():
    kind, lemma, extra, _gloss, c, n, form = line.split("\t")
    if kind in ("noun", "adj"):
        generated[(kind, lemma, c, n)].add(form)
        lemmas_in_lexicon.add(lemma)
        if kind == "noun":
            entry_gender[lemma] = extra

harvest = json.load(open(here / "corpus" / "harvest.json", encoding="utf-8"))
sel_nouns = {r.split("\t")[0] for r in open(here / "selection" / "selection_nouns.tsv", encoding="utf-8").read().splitlines()[1:]}
sel_adjs = {r.split("\t")[0] for r in open(here / "selection" / "selection_adjs.tsv", encoding="utf-8").read().splitlines()[1:]}

total = matched = 0
mismatches = []
for lid, h in harvest.items():
    lemma = h["lemma"]
    kind = "noun" if lemma in sel_nouns else "adj" if lemma in sel_adjs else None
    if kind is None:
        continue
    # export prints the lexicon stem in IAST (bhagavant -> bhagavat)
    key_lemma = lemma[:-2] + "t" if lemma.endswith("ant") else lemma
    if key_lemma not in lemmas_in_lexicon:
        continue
    GEN = {"Masc": "m", "Fem": "f", "Neut": "n"}
    for cell, forms in h["nominal"].items():
        case_, num, gen_ = cell.split("|")
        if case_ == "Cpd" or case_ not in CASES or case_ == "Voc":
            continue  # vocative unsandhied cells in DCS are unreliable
        if kind == "noun" and gen_ in GEN and GEN[gen_] != entry_gender.get(key_lemma):
            continue  # same lemma, other gender (bala m as a name) — not in lexicon
        gen_forms = generated.get((kind, key_lemma, CASES[case_], NUMS[num]), set())
        gen_normed = {norm(f) for f in gen_forms} | gen_forms
        gen_folded = {fold(f) for f in gen_forms}
        for form, count in forms.items():
            if count < min_count:
                continue
            total += 1
            if (form in gen_forms or norm(form) in gen_normed or form in gen_normed
                    or fold(form) in gen_folded):
                matched += 1
            else:
                mismatches.append((count, lemma, cell, form, sorted(gen_forms)[:4]))

print(f"attested cells checked (count >= {min_count}): {total}")
print(f"matched: {matched} ({100 * matched / total:.1f}%)")
mismatches.sort(reverse=True)
print("\ntop mismatches (count, lemma, cell, attested, generated):")
for m in mismatches[:40]:
    print(" ", m)
