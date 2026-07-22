"""Second pass over the DCS CoNLL-U dump: fragment-usable frequencies.

Raw lemma counts overstate what a present-tense, compound-free fragment can
use. This pass counts, per LemmaId:
  declined  - nominal tokens carrying a real Case feature (Case=Cpd excluded),
              i.e. usable as a standalone inflected word
  presind   - finite present indicative verb tokens (Tense=Pres|Mood=Ind
              with a Person feature), excluding passives (Voice=Pass) —
              the fragment conjugates active and middle only
  acc_rate  - of sentences containing this lemma as a finite present verb,
              the fraction that also contain an accusative token: a crude
              empirical transitivity signal

Inputs/output mirror build_frequency_table.py; writes usable_frequencies.tsv.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

corpus_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dcs-sparse/dcs/data/conllu/files")
dict_path = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/dcs_dictionary.csv")
out_path = Path(sys.argv[3] if len(sys.argv) > 3 else Path(__file__).parent / "corpus" / "usable_frequencies.tsv")

raw = Counter()
declined = Counter()
presind = Counter()
verb_sents = Counter()
verb_sents_acc = Counter()

def flush_sentence(verbs, has_acc):
    for lid in set(verbs):
        verb_sents[lid] += 1
        if has_acc:
            verb_sents_acc[lid] += 1

files = sorted(corpus_dir.rglob("*.conllu"))
for i, f in enumerate(files):
    sent_verbs, sent_acc = [], False
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line[0] == "#":
                if not line:
                    flush_sentence(sent_verbs, sent_acc)
                    sent_verbs, sent_acc = [], False
                continue
            cols = line.split("\t")
            if len(cols) < 10 or "LemmaId=" not in cols[9]:
                continue
            misc = cols[9]
            pos = misc.find("LemmaId=") + 8
            end = misc.find("|", pos)
            lid = misc[pos : end if end != -1 else len(misc)]
            feats = cols[5]
            raw[lid] += 1
            if "Case=" in feats and "Case=Cpd" not in feats:
                declined[lid] += 1
                if "Case=Acc" in feats:
                    sent_acc = True
            if (cols[3] == "VERB" and "Tense=Pres" in feats and "Mood=Ind" in feats
                    and "Person=" in feats and "Voice=Pass" not in feats):
                presind[lid] += 1
                sent_verbs.append(lid)
    flush_sentence(sent_verbs, sent_acc)
    if (i + 1) % 4000 == 0:
        print(f"  {i + 1}/{len(files)} files", file=sys.stderr)

dictionary = {}
with open(dict_path, encoding="utf-8") as fh:
    for row in csv.reader(fh, delimiter="\t"):
        if row and row[0].isdigit():
            row += [""] * (5 - len(row))
            dictionary[row[0]] = (row[1], row[2], "; ".join(p for p in row[4:] if p))

with open(out_path, "w", encoding="utf-8") as out:
    out.write("lemma_id\tlemma\tdcs_grammar\traw\tdeclined\tpresind\tacc_rate\tgloss\n")
    for lid, n in raw.most_common():
        lemma, grammar, gloss = dictionary.get(lid, ("?", "", ""))
        rate = f"{verb_sents_acc[lid] / verb_sents[lid]:.2f}" if verb_sents[lid] >= 20 else ""
        out.write(f"{lid}\t{lemma}\t{grammar}\t{n}\t{declined[lid]}\t{presind[lid]}\t{rate}\t{gloss}\n")

print(f"tokens: {sum(raw.values()):,}  declined: {sum(declined.values()):,}  presind: {sum(presind.values()):,}")
print(f"wrote {out_path}")
