# A fragment of Sanskrit grammar, as a Lean 4 library

This folder formalizes a small but genuine fragment of Sanskrit so that
**grammaticality is a theorem**. The library defines

```lean
Grammatical : String → Prop
```

and makes it decidable, so Lean can prove or refute it mechanically:

```lean
example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide   -- ✓ compiles
example : Grammatical "bālāḥ grāmaṃ gacchati" := by native_decide  -- ✗ build error
```

The second sentence fails because its subject is plural ("the boys") while
its verb is singular ("goes") — the same reason an English teacher would
reject *"the boys goes"*. No parser, no ML, no dictionary lookup service:
everything the checker knows is defined in the ~2,000 lines of Lean in this
folder, and the same definitions are replayed as theorems at every build.

## A 60-second Sanskrit primer

You need almost no Sanskrit to read this codebase, just three facts:

1. **Endings do the work.** Sanskrit words inflect heavily. A noun takes one
   of 8 cases (subject, object, "with", "for", "from", "of", "in", address)
   × 3 numbers (singular, **dual**, plural) — 24 slots. The ending tells you
   the word's role, so word order is grammatically free.
2. **Verbs agree.** A finite verb encodes person (I/you/she) and number, and
   must match its subject: *gacchati* "goes" needs a singular subject,
   *gacchanti* "go" a plural one.
3. **Words fuse at the seams (sandhi).** Written Sanskrit merges word
   boundaries by fixed sound laws: *devaḥ* + *gacchati* is written
   *devo gacchati*. To recognize words you must first undo this.

Worked example — `rāmo grāmaṃ gacchati` ("Rāma goes to the village"):

| surface | undo sandhi | analysis |
|---|---|---|
| rāmo | rāmaḥ | noun *rāma*, nominative singular → the subject |
| grāmaṃ | grāmam | noun *grāma* "village", accusative singular → the object |
| gacchati | — | verb *gam* "go", 3rd person singular |

Subject and verb agree (3rd sg), the transitive reading is satisfied by an
accusative — grammatical, and `by native_decide` proves it.

## The fragment, precisely

Sanskrit's full grammar (Pāṇini's *Aṣṭādhyāyī*, ~4,000 rules) is far beyond
this fragment. This table is the exact contract: a string can be judged
`Grammatical` iff it stays inside the "in the fragment" column. Anything in
the right column is rejected (or unrepresentable) even when it is perfectly
good Sanskrit.

| dimension | in the fragment | not in the fragment |
|---|---|---|
| **script** | IAST romanization in and out (*rāmo grāmaṃ gacchati*); SLP1 internally | Devanagari; Vedic accent marks |
| **phonology** | full classical sound inventory; retroflexion *n* → *ṇ* (ṇatva) derived and applied to every generated form | all other internal sound rules (memorized in the paradigm tables instead) |
| **sandhi between words** | undone, for alternations that keep tokens separate: visarga (*devo/devā/devas/devāś* ← *devaḥ*), final *m* → *ṃ*, final *t* → *d*, *nn*-doubling, *saḥ* → *sa*, avagraha (*'pi* ← *api*) | vowel fusion that merges two words into one written token (*ca + iva* → *ceva*) — write the unfused form instead |
| **nouns & adjectives** | all vowel-stem classes (a/ā/i/ī/u/ū, all genders), *ṛ*-stems in both guṇa (*pitaram*) and vṛddhi (*kartāram*) grades, and the major consonant families: *an*-stems with and without weak-stem syncope (*rājñā*/*ātmanā*), *in*-stems (*yogī*), neuter *s*-stems (*manaḥ/manāṃsi*), *mat/vat*-stems (*bhagavān*, vṛddhi *mahān*), and root stems (*vāk/vācam/vāgbhiḥ*); adjectives decline in three genders incl. pronominal endings (*sarve, anyat*, optional *pūrve/pūrvāḥ*): 8 cases × 3 numbers, with accepted classical variant cells | irregular and suppletive nouns (*strī, go, pati, pathin*, monosyllabic *śrī/bhū*), heteroclites, degrees of comparison |
| **verbs** | present indicative only, both voices (*parasmaipada*/*ātmanepada*), 3 persons × 3 numbers: thematic conjugation derived from the present stem, plus 22 athematic verbs (*as, kṛ, dā, dhā, hu, śru, jñā, grah, han, i, brū* …) as explicit tables validated against corpus attestations | every other tense and mood, participles, infinitives, causatives, verbal prefixes |
| **pronouns** | *saḥ/sā/tat* "he/she/it", *aham* "I", *tvam* "you" (forms enumerated, as suppletive forms must be) | all other pronouns |
| **vocabulary** | closed: 774 lemmas — 500 nouns, 150 adjectives, 100 verbs, 24 indeclinables — 23,897 inflected forms total, selected by corpus frequency from the Digital Corpus of Sanskrit (5.7M analyzed tokens; see [../data/dcs/](../data/dcs/)) | any word not in [Lexicon.lean](Sanskrit/Lexicon.lean) |
| **syntax** | five decidable checks: every token has a lexicon reading; *k* finite verbs need *k−1* coordinators (*ca*, *vā*, *tu*); each verb finds an agreeing nominative subject (1st/2nd person may drop it); adjectives agree in gender, case, number; transitive verbs find an accusative | word-order constraints (genuinely free in Sanskrit), compounds (*samāsa*), relative clauses, subordination, any semantics |

Each exclusion is an extension point, not a workaround — the judgment
stays decidable as the fragment grows.

## Module by module

Where each row of the table lives in the source:

- **[Phonology.lean](Sanskrit/Phonology.lean)** — the sound inventory
  (in SLP1, an ASCII encoding with one character per phoneme), vowel and
  voicing classes, and one real phonological rule derived rather than
  memorized: **retroflexion (ṇatva)**. After an *r/ṛ/ṝ/ṣ* earlier in the
  word, *n* becomes the retroflex *ṇ* unless a blocking consonant
  intervenes — so *rāma* + *inā* yields *rāmeṇa*, but *vana* + *āni* stays
  *vanāni*. Every generated noun and verb form passes through this rule.
- **[Translit.lean](Sanskrit/Translit.lean)** — conversion between IAST
  (the romanization humans and the fine-tuned model read/write: *ṛ, ś, ṃ*)
  and SLP1 (what the grammar computes over), both directions.
- **[Nouns.lean](Sanskrit/Nouns.lean)** — declension for **33 stem
  classes**: every vowel class (a/ā/i/ī/u/ū across genders), ṛ-stems
  (guṇa and vṛddhi), an-stems (with the syncope rule *rājñā* vs
  *ātmanā*), in-stems, neuter s-stems, mat/vat-stems, root stems (the
  entry carries the word-final base *vāk*, the engine derives *vāg-*),
  and pronominal endings: 8 cases × 3 numbers per paradigm, including
  cells with accepted classical variants (*mataye*/*matyai*).
- **[Verbs.lean](Sanskrit/Verbs.lean)** — conjugation in the **present
  tense only**, both voices (active *parasmaipada*, middle *ātmanepada*),
  3 persons × 3 numbers: thematic verbs derived from the present stem;
  athematic verbs (root, reduplicating, nasal, nu/nā classes) carry
  their nine forms as lexicon tables, enumerated like all suppletive
  morphology.
- **[Lexicon.lean](Sanskrit/Lexicon.lean)** — **generated, do not edit**:
  500 nouns, 150 adjectives, 100 verbs, 24 indeclinable particles with
  English glosses (23,897 inflected forms), selected by corpus frequency
  from the Digital Corpus of Sanskrit and rendered by
  [../data/dcs/generate_lexicon.py](../data/dcs/generate_lexicon.py).
  Generated forms are cross-checked against corpus-attested paradigm
  cells (94% of 9,873 frequent cells match exactly; the rest are Vedic
  variants and DCS representation artifacts — see
  [../data/dcs/validate_forms.py](../data/dcs/validate_forms.py)).
- **[Sandhi.lean](Sanskrit/Sandhi.lean)** — **undoing** external sandhi:
  given a surface word and the first sound of the next word, enumerate the
  citation forms it could have come from. Covers the families that keep
  tokens separate — visarga alternations (*devo/devā/devas/devāś* ← *devaḥ*
  etc.), final *m* → *ṃ*, final *t* → *d*, doubled *nn*, the *saḥ* → *sa*
  special case, and avagraha (*'pi* ← *api*).
- **[Sentence.lean](Sanskrit/Sentence.lean)** — the sentence judgment.
  A sentence (IAST, space-separated, sandhi applied or not) is
  `Grammatical` iff five checks pass:
  1. **words** — every token has at least one reading in the lexicon;
  2. **clauses** — *k* finite verbs are licensed by *k−1* coordinating
     *ca* "and" particles (so one verb per clause, any number of clauses);
  3. **subject** — every verb finds a nominative subject agreeing in person
     and number (subjects of "I"/"you" verbs may be dropped, as in real
     Sanskrit: *gacchāmi* alone means "I go");
  4. **adjective** — every adjective agrees with some noun or pronoun in
     gender, case, and number;
  5. **object** — a transitive verb has an accusative somewhere.

  Pronouns (*saḥ/sā/tat* "he/she/it", *aham* "I", *tvam* "you") are
  suppletive in every language, so their forms are enumerated, not derived.
- **[Tests.lean](Sanskrit/Tests.lean)** — gold paradigm cells from
  standard grammars (Whitney) for every stem class and athematic verb,
  plus positive and negative sentences, stated as
  `example : … := by native_decide`. **They re-prove at every
  `lake build`** — a change that breaks a paradigm breaks the build.
  Independently, the full generated lexicon is validated against
  corpus-attested cells (DCS harvest) by the data pipeline.

## The two executables

Built by `lake build` into `.lake/build/bin/`, these are the bridge to the
fine-tuning framework in [`../finetune/`](../finetune/):

**`check`** — judge a sentence (exit code 0 iff grammatical):

```
$ check "rāmo grāmaṃ gacchati"
words=1 clauses=1 subject=1 adjective=1 object=1 reqs= lemmas=rāma,grāma,gam

$ check "bālāḥ grāmaṃ gacchati"        # plural subject, singular verb
words=1 clauses=1 subject=0 adjective=1 object=1 reqs= lemmas=bāla,grāma,gam
```

`--json` emits full diagnostics (per-token analyses, component verdicts).
Extra arguments are content constraints — `rāma:nom:sg` (that word, that
case/number), `verb:gam:3:sg`, or a bare lemma — so the reward can require
not just *a* grammatical sentence but *the* requested one.

**`export`** — dump every inflected form of the whole lexicon as TSV
(23,897 lines); the single source of truth the
data generator (`python -m finetune.tasks`) reads.

## Building

```sh
cd lean && lake build     # also re-proves every theorem in Tests.lean
```

Toolchain is pinned in [lean-toolchain](lean-toolchain) (Lean 4.28.0);
there are **zero external dependencies** — no mathlib, just core Lean.
