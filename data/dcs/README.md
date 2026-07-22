# DCS lexicon pipeline

Builds the generated [../../lean/Sanskrit/Lexicon.lean](../../lean/Sanskrit/Lexicon.lean)
from the **Digital Corpus of Sanskrit** (DCS, Oliver Hellwig): 5.7M
annotator-verified tokens across 270 texts in CoNLL-U format, joined with
its 180k-entry dictionary.

## Layout

```
dcs/
  *.py          the pipeline, in run order (below)
  corpus/       corpus-derived intermediates — regenerable from the checkout
    lemma_frequencies.tsv     raw ranking of all 98,606 attested lemmas
    usable_frequencies.tsv    fragment-usable counts + transitivity signal
    harvest.json              attested paradigm cells for candidate lemmas
    noun_traits.json          per-noun template semantics (pluralizes? locative?)
    mined_sentences.tsv       436 real sentences fully inside the fragment,
                              checker-verified, with per-token cell provenance
                              and a stable train/eval split
  selection/    the v2 lexicon decision — small, reviewed
    selection_nouns.tsv       500 nouns with stem class
    selection_adjs.tsv        150 adjectives with class + feminine stem
    selection_verbs.tsv       100 verb entries (thematic stems / athematic tables)
    exclusions.tsv            what was skipped, and why (irregulars, numerals …)
```

## Corpus checkout (not in this repo, ~1.1 GB)

```sh
git clone --depth 1 --filter=blob:none --sparse https://github.com/OliverHellwig/sanskrit.git /tmp/dcs-sparse
git -C /tmp/dcs-sparse sparse-checkout set dcs/data/conllu/files
curl -o /tmp/dcs_dictionary.csv https://raw.githubusercontent.com/OliverHellwig/sanskrit/master/dcs/data/conllu/lookup/dictionary.csv
```

## The pipeline, in order

1. **build_frequency_table.py** — count every LemmaId over the corpus →
   `corpus/lemma_frequencies.tsv`.
2. **build_usable_frequencies.py** — fragment-usable counts: declined
   non-compound tokens for nominals, finite present-indicative non-passive
   tokens for verbs, plus per-verb accusative co-occurrence (empirical
   transitivity) → `corpus/usable_frequencies.tsv`.
3. **harvest_paradigms.py** — attested unsandhied forms per grammatical
   cell for the top candidate lemmas → `corpus/harvest.json`. Grounds every
   classification decision (an-stem syncope, ṛ-stem guṇa/vṛddhi grade,
   adjective feminines, athematic verb cells) in corpus evidence.
4. **select_lexicon.py** — classify the top 500 nouns / 150 adjectives /
   100 verbs into Lean stem classes; exclude irregulars with documented
   reasons → `selection/`.
5. **generate_lexicon.py** — render the selections as `Lexicon.lean`.
6. **validate_forms.py** — after `lake build`, compare every generated
   form against corpus-attested cells (94% exact on frequent cells; the
   residue is Vedic variants and DCS representation artifacts).
7. **build_noun_traits.py** — reduce harvest.json to per-noun template
   semantics (`plural_ok`, `loc_ok`, …) → `corpus/noun_traits.json`.
   Replaces the gloss-keyed hand lists v1's task generator used.
8. **mine_sentences.py** — find corpus sentences the fragment fully
   analyzes (every token in a covered cell, finite present verbs only),
   verify each through the Lean checker, split by text hash →
   `corpus/mined_sentences.tsv`. These feed the post-edit / cloze /
   error-id task families in finetune/tasks.py. The short-sentence pool
   skews Vedic-prose (brāhmaṇas) plus the Mahābhārata; every sentence is
   checker-verified regardless of source.
9. **make_oof_cloze.py** — the out-of-fragment benchmark: attested cloze
   over 22 classical texts (epics, fable prose, kāvya, dharmaśāstra; no
   Vedic) → `data/out_of_fragment/eval.jsonl` (150 rows, judge `exact`).
   Each row blanks the one in-fragment token of an otherwise
   out-of-fragment sentence; gold = the attested form + accepted
   same-cell variants.

The ratio 500:100:150 comes from equal-coverage analysis (500 nouns cover
51.5% of declined-noun tokens; the same coverage needs ~65 verbs and ~288
adjectives) adjusted for checker design: verbs are boosted (each one is
structurally load-bearing), adjectives trimmed (flat frequency curve,
three paradigms each).
