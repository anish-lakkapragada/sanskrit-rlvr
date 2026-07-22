# `check` — the compiled grammaticality judge

`check` is the executable bridge between the Lean formalization and
everything that needs a verdict at runtime: data generation, the GRPO
reward, and evaluation. It judges one sentence per invocation, in ~30–60 ms,
and its verdict is **definitionally the same computation** as the
`Grammatical` proposition that the test theorems prove at every build —
[Check.lean](Check.lean) calls the shared `report` function
([Sentence.lean:185](Sanskrit/Sentence.lean#L185)) and conjoins the same
five booleans that `grammaticalB` ([Sentence.lean:192](Sanskrit/Sentence.lean#L192))
defines. One definition, two evaluators: the kernel replays it as theorems
(`by native_decide` in [Tests.lean](Sanskrit/Tests.lean)); this binary
evaluates it as compiled native code per sentence.

## Build & invoke

```sh
cd lean && lake build           # also re-proves every theorem in Tests.lean
.lake/build/bin/check [--json] "<sentence in IAST>" [constraint ...]
```

- **Exit code**: `0` iff the sentence is grammatical, `1` if not, `2` on
  missing arguments. The exit code ignores constraints — those are reported
  but never affect the verdict.
- **Input**: IAST romanization (ā ī ū ṛ ṭ ḍ ṇ ñ ṅ ś ṣ ṃ ḥ), words separated
  by spaces, NFC-normalized. External sandhi may be applied or not: both
  `rāmo grāmaṃ gacchati` and the pausa spelling `rāmaḥ grāmam gacchati`
  are accepted (each token is restored against the first sound of the next
  token before lookup).

## Output formats

Plain (one line, `1`/`0` per component):

```
$ check "rājā karma karoti"
words=1 clauses=1 subject=1 adjective=1 object=1 reqs= lemmas=rājan,karman,kṛ
```

`--json` (full diagnostics):

```json
{
  "grammatical": true,
  "components": {"words": true, "clauses": true, "subject": true,
                  "adjective": true, "object": true},
  "constraints": [true, false],
  "lemmas": ["rājan", "karman", "kṛ"],
  "tokens": [
    {"surface": "rājā",
     "analyses": [{"lemma": "rājan", "pos": "noun", "gender": "m",
                    "case": "nom", "number": "sg", "person": "3"}]},
    ...
  ]
}
```

- `grammatical` — the verdict (= exit code = the `Grammatical` Prop).
- `components` — the five checks, below.
- `constraints` — one boolean per constraint argument, in order.
- `lemmas` — deduplicated dictionary words recognized anywhere in the
  sentence (IAST). Downstream, this drives lemma-preservation scoring.
- `tokens[*].analyses` — **every** reading of each surface token:
  `lemma`, `pos` (`noun|adj|pron|verb|ind`), and whichever of
  `gender`/`case`/`number`/`person` the reading carries. Ambiguity is the
  norm — a single form like `sarve` legitimately has nine readings.

## The five components

A sentence is grammatical iff all five hold. Every check is **existentially
quantified over readings**: the checker never picks an analysis; it asks
whether *some* reading makes the requirement true. Word order is never
consulted — Sanskrit's is free.

1. **`words`** — every token has at least one lexicon reading after sandhi
   restoration. The vocabulary-and-morphology gate: misspellings, unknown
   words, and nonexistent inflections die here. A *real but wrongly chosen*
   form passes `words` and must be caught by the agreement checks.
2. **`clauses`** — *k* finite verbs require *k−1* coordinating particles
   (*ca*, *vā*, *tu*): one verb per clause, any number of coordinated
   clauses, and no verbless sentences.
3. **`subject`** — every verb finds a nominative reading elsewhere in the
   sentence agreeing in person and number. First/second-person verbs may
   drop their subject (*gacchāmi* "I go" stands alone), unless a clashing
   personal pronoun is present.
4. **`adjective`** — every unambiguous adjective agrees with some
   noun/pronoun reading in gender, case, and number simultaneously.
   Gender-less pronoun readings (*aham*, *tvam*) wildcard the gender slot.
5. **`object`** — if the verb is transitive (an empirically derived flag in
   the lexicon), an accusative reading must exist somewhere. An existence
   check, not a dependency parse — the fragment's decidable approximation
   of argument structure.

## Constraints (content specs)

Extra arguments let a caller demand not just *a* grammatical sentence but
*the requested one*. Three forms, parsed by `satisfies`
([Check.lean:31](Check.lean#L31)); each yields one bit in `constraints`:

| form | example | satisfied when |
|---|---|---|
| `lemma:case:number` | `rāma:nom:sg` | some reading of some token has that lemma, case, and number (any POS, gender-blind) |
| `verb:lemma:person:number` | `verb:gam:3:pl` | some verbal reading matches lemma, person, number |
| `lemma` | `saha` | any reading of any token has that lemma |

Cases: `nom acc ins dat abl gen loc voc`; numbers: `sg du pl`; persons:
`3 2 1`. Lemmas are written in IAST and converted internally. A malformed
spec is simply `false`. Constraints never change the exit code — they are
inputs to *reward shaping*, not to grammaticality.

## How the training stack consumes it

`finetune/lean.py:check()` shells out to this binary with `--json`
(lru-cached on `(sentence, constraints)`); `finetune/reward.py` turns the
result into the verified reward: the weighted component sum
(words .40, clauses .15, subject .20, adjective .10, object .15) × the mean
of the constraint bits × length damping for translate/compose, and the
all-or-nothing `grammatical` gate × lemma-preservation bits for post-edit.
During GRPO, every sampled rollout of the sentence-task families passes
through here; during evaluation, `compile_rate` is this binary's verdict
over eval generations.

## Scope and guarantees

The judgment is exactly as strong as the fragment: 774 lemmas
(23,897 generated forms), present indicative only, no compounds, no
subordination — see [README.md](README.md) for the full contract table.
Within that fragment the verdict is mechanical and reproducible: the same
paradigm functions that generate every form also analyze every token, gold
cells re-prove as theorems at each `lake build`, and the generated forms
match 94.2% of frequently-attested cells in the Digital Corpus of Sanskrit
(the residue being Vedic variants and corpus-representation artifacts).
One caveat for maintainers: `main` re-forms the five-way conjunction
inline ([Check.lean:83-85](Check.lean#L83-L85)) rather than calling
`grammaticalB`; if a sixth component is ever added, update both sites (or
refactor `grammaticalB` to take a `Report`).
