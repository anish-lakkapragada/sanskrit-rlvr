# data/ — what the model trains on, how it was made, and why

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
| `in_fragment/grpo/train.jsonl` | 2000 | GRPO training | verified reward per family (see below): live Lean checker for translate/compose/post_edit, exact match vs Lean-exported gold for qa/cloze/error_id |
| `in_fragment/grpo/valid.jsonl` | 64 | GRPO validation | same |
| `in_fragment/eval.jsonl` | 250 | checkpoint + final eval | `lean+chrf` |
| `out_of_fragment/eval.jsonl` | 150 | generalization benchmark | `exact` |

All five in-fragment files come from one generator run with a single
shared prompt-dedup set — 4,250 unique prompts, so no eval or validation
prompt ever appears in a training file.

**What changed from the previous (v1) data.** The v1 files were 2,278
tasks of three families (qa / translate / compose) over a 118-lemma
lexicon, generated purely from templates; the out-of-fragment benchmark
was 36 hand-curated English→Sanskrit maxims judged by chrF++. The current
data has six families over the 774-lemma v2 lexicon, draws sentence tasks
from real corpus sentences as well as templates, and replaces the maxim
benchmark with attested cloze (below). Concretely for **SFT**: v1
assistant turns were only inflected forms and reference translations; v2
assistant turns additionally contain corrected sentences (post_edit),
restored words (cloze), and error names or *sādhu* (error_id) — so
supervised training now demonstrates error-repair and fill-in behavior,
not just generation. Every assistant turn is still `<ans>gold</ans>` where
gold is verified against the reward function at generation time.

---

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
'correct'). About one third are correct, so a policy of always hunting for
errors fails. Exact-match.

**`post_edit` — fix a corrupted sentence** (50 / 12+12 / 400+400). A
verified-grammatical sentence is minimally corrupted — verb number/person
flip, noun case/number swap, required-object deletion — each re-inflected
through the real paradigms and each *verified to actually fail* the
checker. The model outputs the corrected sentence. Reward = the checker's
all-or-nothing verdict × lemma preservation (bare-lemma constraint bits) ×
length damping.
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

## How the reward is computed, per family

Every family — and the chrF++ control reward — shares one shell:

    reward = 0.15 × format + 0.85 × task

`format` is 1 iff the answer was inside `<ans></ans>` tags (last match
wins; otherwise the last nonempty line is graded with format = 0).
Answers are normalized (NFC, lowercased, punctuation stripped) before
grading. `task ∈ [0,1]` has three regimes:

**Exact-match** (`qa`, `cloze`, `error_id`) — no checker call:

    task = 1.0              if answer ∈ gold list
         = 0.25 × ratio     if best SequenceMatcher ratio ≥ 0.5 (near-miss, capped low, anti-gaming)
         = 0.0              otherwise

The gold list carries every accepted variant of the cell (mataye/matyai
both score 1.0); for error_id it is the misinflected word, or sādhu.

**Open production** (`translate`, `compose`) — structural, multiplicative:

    task = grammar × (0.15 + 0.85 × content) × damp
    grammar = weighted checker components (words .40, clauses .15,
              subject .20, adjective .10, object .15)
    content = fraction of constraint specs satisfied
    damp    = 1 if n_tokens ≤ cap, else max(0.05, cap / n_tokens)

`cap` is per-row (reference length + 3 for translate; 12–13 for compose).
Multiplicative on purpose: word salad zeroes grammar, prompt-ignoring
zeroes content, padding is crushed by damp.

**Post-edit** (`post_edit`) — same shape, but grammar becomes a **gate**:

    task = 1.0 if answer == the original sentence, else
         = gate × (0.15 + 0.85 × content) × damp
    gate    = 1.0 iff the checker's verdict is fully grammatical, else 0.0
    content = bare-lemma bits of the original sentence (no word swaps)
    cap     = original length + 2

The gate exists because of a measured exploit: a corrupted sentence
typically fails only one checker component, so under the weighted formula
echoing the prompt back would score task ≈ 0.8; with the gate, an echo
scores 0. A *different* valid repair (fixing agreement from the other
side) scores 1.0 — the contract is "grammatical, same words", not
"byte-identical".

The `gold`/`reference` strings inside a GRPO row's `answer` spec are
consumed only by these reward computations over sampled rollouts — GRPO
never trains on them as target text. Every row was verified at generation
time to satisfy its own contract (reference scores exactly 1.0; post-edit
echo scores < 0.2).

## In-fragment: how it was generated

1. **The vocabulary** is the v2 Lean lexicon (774 lemmas, 23,897 forms),
   itself selected by fragment-usable corpus frequency from the Digital
   Corpus of Sanskrit (DCS) — see [dcs/README.md](dcs/README.md). The
   generator reads inflected forms exclusively from the Lean `export`
   binary; Python never inflects anything.
2. **Sentence sources are twofold.**
   - *Templated*: small sentences built from the lexicon. Per-noun
     template semantics — which nouns pluralize, which sit naturally in a
     locative, which take a dative — are derived from corpus statistics
     (`dcs/corpus/noun_traits.json`), not hand lists.
   - *Real*: 436 corpus sentences that the fragment fully analyzes
     (`dcs/corpus/mined_sentences.tsv`), mined from the DCS with per-token
     (lemma, cell) provenance taken from the human-verified annotation,
     each joined from unsandhied tokens and verified Grammatical by the
     Lean checker. Real sentences carry a train/eval split assigned by
     sentence-text hash; every task derived from a sentence (its
     corruptions, its cloze blanks) inherits that split, so no real
     sentence straddles the boundary. Per train file, 450 rows derive from
     real sentences (cloze 120, post_edit 200, error_id 130); eval has 65.
3. **Corruptions are generated, then proven wrong.** The corruption
   generator (finetune/corrupt.py) re-inflects one word through the actual
   paradigm tables and keeps a candidate only if the Lean checker rejects
   the resulting sentence. This filter is load-bearing: plausible-looking
   corruptions (an oblique case swap, a mismatched adjective that can
   re-parse as a standalone nominal) often still parse, and must be
   discarded rather than mislabeled.
4. **Everything checkable is checked at generation time**: translate and
   compose references must compile and satisfy their own constraint specs;
   post-edit gold must score reward 1.0 and the corrupted echo < 0.2.
   `python -m finetune.tasks --self-test` re-reads the written files and
   re-asserts the contract.
5. **One task, three renderings.** The same task becomes an SFT chat row
   (`messages`, assistant = `<ans>gold</ans>`), a GRPO row (`prompt` +
   `answer` = the JSON spec the reward replays), and an eval row (with a
   `judge` field). Prompts are deduplicated globally across all five
   files.

## In-fragment: why these tasks

The reward is the product: every family exists because it can be graded
*mechanically and adversarially* by the Lean checker or by exact match —
no LLM judging, no reference-similarity scoring for correctness claims.

- **qa / cloze** teach and test the paradigms directly; cloze adds the
  skill of reading a case assignment out of sentence context.
- **error_id / post_edit** are the discriminative and corrective halves of
  the same skill: noticing that agreement is broken, and repairing it
  minimally. Post-editing is also the family with the densest reward
  signal for GRPO — a near-miss fix still earns partial credit through
  the lemma-preservation bits. Its reward uses the checker's
  all-or-nothing verdict as a gate specifically because a
  weighted-component score would give ~0.8 to a model that simply echoes
  the corrupted prompt back (measured during design); the gate makes
  echoing worthless.
- **translate / compose** are the open-ended production tasks, graded
  structurally (the right lemmas in the right cells) so that free word
  order is never penalized.
- **Real corpus sentences** are included in both training and evaluation
  (with a hard hash split) because templated sentences have a narrow
  stylistic distribution; real prose supplies particles, vocatives-in-
  context, and word orders no template produces. The short-sentence pool
  skews Vedic-prose (brāhmaṇas) plus the Mahābhārata — every sentence is
  checker-verified regardless of source.

There is deliberately **no held-out-lemma tier**: all 774 lemmas are
training vocabulary. Generalization is measured only across the fragment
boundary, by the out-of-fragment benchmark below.

---

## Out-of-fragment: what is in it

**Attested cloze** (150 rows, judge `exact`): real sentences from 22
classical texts — Mahābhārata, Rāmāyaṇa, Harivaṃśa; Hitopadeśa,
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
produce the attested form exactly (gold also accepts the accepted
classical variants of the same cell).

> *"tam ca ____ daśarathaḥ yaṣṭu-kāmaḥ kṛta-añjaliḥ"* — replace `____`
> with the correct form of *rājan* ('king') → `rājā`

## Out-of-fragment: how it was generated

Mined by `data/dcs/make_oof_cloze.py` from the DCS's human-verified
annotations: sentence boundaries, per-token lemmas, and morphological
cells all come from the corpus, so the sentences' validity is inherited
from real transmitted text — nothing is authored by a model or a human
for this benchmark. Selection: 4–12 display tokens, every token carrying
an unsandhied form, at least one token failing the in-fragment test (that
failure is what makes the row out-of-fragment, and guarantees disjointness
from the mined in-fragment sentences by construction), and a maskable
token whose surface occurs exactly once in the sentence. Nominals are
preferred as masks; at most 12 rows per text.

## Out-of-fragment: why this design

**Why cloze at all: there is no machine judge beyond the fragment.** The
Lean checker can only verify what it formalizes, so "translate this using
the perfect tense" cannot be graded mechanically — the retired 36-maxim
benchmark had exactly this problem and fell back to chrF++ string
similarity, which is fuzzy and gameable. Attested cloze flips the
arrangement: the *scoring* stays inside the fragment (exact match against
a human-verified attested form) while the *context* moves outside it. It
measures one thing precisely: does morphology learned inside the fragment
survive contact with real classical Sanskrit full of constructions the
model was never trained on? What it deliberately does not measure is the
ability to *produce* out-of-fragment grammar — no benchmark here claims to
score what nothing can verify.

**Why classical texts** (not Vedic, not śāstric lists): the fragment
formalizes classical grammar, so classical texts keep the benchmark on
the intended axis — same language stage, unfamiliar syntax. Vedic is a
different grammar (during lexicon validation, ~6% of attested-form
mismatches were Vedic variants like *devebhiḥ* for *devaiḥ* — a model
that correctly learned classical paradigms would be marked wrong against
them), and the technical corpora are largely enumerative lists, which
test vocabulary guessing rather than grammar-in-context. The register
split also runs opposite to training: the mined in-fragment sentences
skew Vedic-prose, so a good out-of-fragment score cannot be explained by
stylistic familiarity.

**Why pretraining memorization does not carry the benchmark.** These are
famous texts, so the obvious worry is that a pretrained model has simply
memorized them. Two design properties resist this:

1. **The representation gap.** Pretraining copies of these texts are
   sandhied, continuous, and usually Devanagari — the actual Rāmāyaṇa line
   behind the example above is *"taṃ ca rājā daśaratho yaṣṭukāmaḥ
   kṛtāñjaliḥ"*. The benchmark shows *"tam ca ____ daśarathaḥ yaṣṭu-kāmaḥ
   kṛta-añjaliḥ"* — unsandhied word forms, compounds hyphen-split, IAST,
   and DCS sentence segmentation rather than verse boundaries. String
   memory does not look up cleanly across that gap; to exploit a memorized
   line the model would have to undo sandhi and re-segment, which is
   itself the grammatical competence under test.
2. **The vocabulary is given away on purpose.** The prompt names the
   missing word's lemma and gloss, so "knowing the word" — the thing
   memorization most helps with — is free for every model. The only
   scored decision is the inflection.

Empirically this holds: an un-fine-tuned Qwen3-8B baseline scores 18.7%
exact, its errors are overwhelmingly right-lemma-wrong-case
(*bharataḥ* for *bharatasya*), and per-text scores show no fame gradient —
the most-anthologized texts (Meghadūta, Gītagovinda, Rāmāyaṇa) sit at or
below the average. A definitive per-model control exists if ever needed:
rerun the benchmark with the lemma/gloss hint stripped; a reciting model
scores the same, an inflecting model degrades sharply.

---

## Reading the metrics

In-fragment eval reports `compile_rate` (sentence tasks that parse),
`qa_exact` / `exact_rate` (exact-match families), `fix_rate` (post-edit
solved), `mean_reward`, plus chrF++/TER against the references.
Out-of-fragment reports `cloze_exact`. Because Sanskrit word order is
free, read chrF++/TER as a pair: high chrF++ with high TER (↓ lower is
better) means right words in a different order. In-fragment, correctness
claims rest on the Lean verdicts, which are order-invariant;
out-of-fragment, on exact restoration of attested text.

Eval row fields: `prompt`/`system` (what the model sees), `judge` (how it
is scored), `gold` (accepted exact answers), `specs` (Lean constraint
strings), `reference` (canonical answer, for chrF++/TER), `cap`
(length-damping threshold for sentence tasks).
