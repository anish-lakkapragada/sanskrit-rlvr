# data/ — what the model trains on, and how it was made

Three groups:

- **`dcs/`** — the pipeline (corpus statistics → lexicon → mined sentences
  → benchmarks). See [dcs/README.md](dcs/README.md).
- **`in_fragment/`** — everything the Lean grammar models. Trains AND
  evaluates. Fully regenerable: `python -m finetune.tasks`.
- **`out_of_fragment/`** — real classical Sanskrit the grammar does NOT
  model. Only evaluates. Regenerable: `python data/dcs/make_oof_cloze.py`.

| File | Rows | Used by | Judge |
|---|---|---|---|
| `in_fragment/sft/train.jsonl` | 2000 | SFT training | — (assistant turn = gold) |
| `in_fragment/sft/valid.jsonl` | 64 | SFT validation loss | — |
| `in_fragment/grpo/train.jsonl` | 2000 | GRPO training | Lean reward (replays `answer` spec) |
| `in_fragment/grpo/valid.jsonl` | 64 | GRPO validation | same |
| `in_fragment/eval.jsonl` | 250 | checkpoint + final eval | `lean+chrf` |
| `out_of_fragment/eval.jsonl` | 150 | generalization benchmark | `exact` |

All five in-fragment files come from one generator run with a single
shared prompt-dedup set — 4,250 unique prompts, so no eval or validation
prompt ever appears in a training file.

## In-fragment: what is in it

Six task families. Every row was verified at generation time: the
reference answer scores reward 1.0 through the actual reward function, and
(for post-edit) the corrupted sentence scores ~0, so the grading contract
is guaranteed by construction, not by hope.

**`qa` — produce one inflected form** (eval 40 / valid 10+10 / train 300+300).
Nouns by case+number, adjectives by gender+case+number, verbs by
person+number (athematic verbs included). Gold = every accepted variant of
that cell from the Lean export. Exact-match.
> *"What is the feminine locative singular of the Sanskrit adjective
> anuttara ('chief')?"* → `anuttarāyām`

**`cloze` — restore a blanked word** (40 / 8+8 / 250+250). A sentence with
one word replaced by `____`, plus the lemma and gloss of the missing word.
Gold = all accepted forms of that cell. Exact-match.
> *"Complete the Sanskrit sentence '____ sukham aṅgāni balam varṇaḥ ca
> vardhate' … correct form of the verb labh"* → `labhante`

**`error_id` — find the wrong word** (30 / 8+8 / 250+250). A sentence that
either contains exactly one misinflected word (the model must output that
word verbatim) or is fully correct (the model must output `sādhu`
'correct'). About one third are correct, so always-hunt-for-errors fails.
Exact-match.

**`post_edit` — fix a corrupted sentence** (50 / 12+12 / 400+400). A
verified-grammatical sentence is minimally corrupted (verb number/person
flip, noun case/number swap, required-object deletion — each re-inflected
through the real paradigms, and each *verified to actually fail* the
checker). The model outputs the corrected sentence. Reward = the checker's
all-or-nothing verdict × lemma preservation (bare-lemma constraint bits) ×
length damping. Echoing the corruption back scores ~0 by construction.
> corrupted *"vistareṇa na śaknutaḥ bṛhaspatiḥ api dvijāḥ"* →
> *"vistareṇa na śaknoti …"*

**`translate` — English → Sanskrit** (50 / 16+16 / 500+500). Templated
English with no vocabulary hints; graded structurally — the Lean checker
confirms grammaticality and that the required lemmas appear in the
required cells (`specs` like `yuddha:nom:sg`, `verb:vṛt:3:sg`). Nine
template shapes: S-V, S-V-O, locative adjunct, *saha*+instrumental,
genitive possession, dative recipient, pronominal adjective (*sarva/eka*),
2–3-clause coordination (*ca/vā/tu*), and negation (*na*). Because the
English is templated from corpus glosses, some prompts read oddly ("One
fight turns.") — grading never depends on English naturalness.

**`compose` — sentence from required words** (40 / 10+10 / 300+300). Four
words (verb, two nouns, adjective) or five (two clauses + *ca*), given in
citation form with glosses; grammar judged by Lean, coverage by
constraint bits.

### How in-fragment data was generated

1. **The vocabulary** is the v2 Lean lexicon (774 lemmas, 23,897 forms),
   itself selected by corpus frequency from the Digital Corpus of Sanskrit
   (DCS). The generator reads forms exclusively from the Lean `export`
   binary — Python never inflects anything.
2. **Sentence sources are twofold.** *Templated*: small sentences built
   from the lexicon, with per-noun template semantics (which nouns
   pluralize, which sit in a locative…) derived from corpus statistics
   (`dcs/corpus/noun_traits.json`), not hand lists. *Real*: 436 corpus
   sentences that the fragment fully analyzes
   (`dcs/corpus/mined_sentences.tsv`) — mined from DCS with per-token cell
   provenance, each verified Grammatical by the Lean checker. Real
   sentences carry a train/eval split assigned by text hash; every task
   derived from a sentence (its corruptions, its blanks) inherits that
   split. Per train file, 450 rows derive from real sentences (cloze 120,
   post_edit 200, error_id 130); eval has 65.
3. **Everything checkable is checked at generation time**: translate and
   compose references must compile and satisfy their own constraints;
   corruptions must fail the checker; post-edit gold must score 1.0 and
   the echo < 0.2. `python -m finetune.tasks --self-test` re-reads the
   written files and re-asserts the contract.

## Out-of-fragment: what is in it

**Attested cloze** (150 rows, judge `exact`): real sentences from 22
classical texts — the Mahābhārata, Rāmāyaṇa, Harivaṃśa; Hitopadeśa,
Tantrākhyāyikā, Kathāsaritsāgara, Vetālapañcaviṃśatikā, Śukasaptati,
Daśakumāracarita, Bṛhatkathāślokasaṃgraha; Buddhacarita, Saundarānanda,
Kumārasaṃbhava, Kirātārjunīya, Meghadūta, Ṛtusaṃhāra, Amaruśataka,
Śatakatraya, Gītagovinda; Manusmṛti, Yājñavalkyasmṛti, Devīmāhātmya
(5–12 rows per text; no Vedic, no technical treatises).

Each sentence is genuinely beyond the fragment — it contains at least one
token the Lean grammar cannot analyze (an unknown lemma, an imperfect or
imperative verb, a compound) — but exactly one blanked token IS
in-fragment: a word from the lexicon, in a covered cell, whose attested
form matches the Lean paradigms. The model sees the sentence (unsandhied,
compounds hyphenated), the missing word's lemma and gloss, and must
produce the attested form exactly (gold also accepts the classical
variants of the same cell).

> *"tam ca ____ daśarathaḥ yaṣṭu-kāmaḥ kṛta-añjaliḥ"* — replace `____`
> with the correct form of *rājan* ('king') → `rājā`

### How out-of-fragment data was generated, and why this design

Mined by `data/dcs/make_oof_cloze.py` from the DCS's human-verified
annotations: sentence boundaries, per-token lemmas, and morphological
cells all come from the corpus, so validity is inherited from real text,
not generated. Grading is exact string match — no Lean call (the checker
can't parse these sentences, which is the point), no English references,
no LLM judging. It measures precisely one thing: **does morphology learned
inside the fragment survive contact with wild classical Sanskrit?**

This replaces the earlier hand-curated 36-maxim benchmark (English →
Sanskrit, judged by chrF++), which v2's larger fragment had partially
absorbed; recover it from git history if needed.

## Reading the metrics

In-fragment eval reports `compile_rate` (sentence tasks that parse),
`qa_exact` / `exact_rate` (exact-match families), `fix_rate` (post-edit
solved), `mean_reward`, plus chrF++/TER against the references.
Out-of-fragment reports `cloze_exact`. Because Sanskrit word order is
free, read chrF++/TER as a pair: high chrF++ with high TER (↓ lower is
better) means right words in a different order. In-fragment, correctness
claims rest on the Lean verdicts, which are order-invariant;
out-of-fragment, on exact restoration of attested text.
