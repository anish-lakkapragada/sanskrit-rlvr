"""Build a lemma frequency table for the whole DCS corpus.

Counts LemmaId occurrences over every token line of the CoNLL-U dump in
OliverHellwig/sanskrit (dcs/data/conllu/files), then joins the counts with
dictionary.csv (lookup/dictionary.csv) to attach lemma, grammar tag, and gloss.

Inputs (override via argv):
  1. corpus dir   (default /tmp/dcs-sparse/dcs/data/conllu/files)
  2. dictionary   (default /tmp/dcs_dictionary.csv)
  3. output tsv   (default data/dcs/lemma_frequencies.tsv next to this script)

Output columns: rank, lemma_id, lemma, dcs_grammar, upos, count, gloss.
UPOS is the majority universal POS tag among the lemma's corpus tokens —
a cross-check against the DCS grammar tag, and a fallback where the
dictionary row is missing. Lemmas never attested in the corpus are omitted.
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

corpus_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dcs-sparse/dcs/data/conllu/files")
dict_path = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/dcs_dictionary.csv")
out_path = Path(sys.argv[3] if len(sys.argv) > 3 else Path(__file__).parent / "corpus" / "lemma_frequencies.tsv")

counts = Counter()
corpus_lemma = {}
upos_counts = defaultdict(Counter)
files = sorted(corpus_dir.rglob("*.conllu"))
token_lines = 0

for i, f in enumerate(files):
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            if not line or line[0] == "#":
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 10:
                continue
            misc = cols[9]
            pos = misc.find("LemmaId=")
            if pos == -1:
                continue
            end = misc.find("|", pos)
            lid = misc[pos + 8 : end if end != -1 else len(misc)]
            counts[lid] += 1
            token_lines += 1
            if lid not in corpus_lemma:
                corpus_lemma[lid] = cols[2]
            upos_counts[lid][cols[3]] += 1
    if (i + 1) % 2000 == 0:
        print(f"  {i + 1}/{len(files)} files, {token_lines:,} tokens", file=sys.stderr)

dictionary = {}
with open(dict_path, encoding="utf-8") as fh:
    for row in csv.reader(fh, delimiter="\t"):
        if row and row[0].isdigit():
            row += [""] * (5 - len(row))
            dictionary[row[0]] = (row[1], row[2], "; ".join(p for p in row[4:] if p))

with open(out_path, "w", encoding="utf-8") as out:
    out.write("rank\tlemma_id\tlemma\tdcs_grammar\tupos\tcount\tgloss\n")
    for rank, (lid, n) in enumerate(counts.most_common(), 1):
        lemma, grammar, gloss = dictionary.get(lid, (corpus_lemma[lid], "", ""))
        upos = upos_counts[lid].most_common(1)[0][0]
        out.write(f"{rank}\t{lid}\t{lemma}\t{grammar}\t{upos}\t{n}\t{gloss}\n")

in_dict = sum(1 for lid in counts if lid in dictionary)
print(f"files: {len(files)}")
print(f"token lines counted: {token_lines:,}")
print(f"distinct lemma ids: {len(counts):,} ({in_dict:,} found in dictionary.csv)")
print(f"wrote {out_path}")
