# data/ — three groups: dcs, in_fragment, out_of_fragment

**`dcs/`** is the lexicon pipeline: corpus statistics from the Digital
Corpus of Sanskrit and the selection lists that generate
[../lean/Sanskrit/Lexicon.lean](../lean/Sanskrit/Lexicon.lean) (500 nouns,
150 adjectives, 100 verbs, by corpus frequency). See
[dcs/README.md](dcs/README.md).

**`in_fragment/`** is everything the Lean grammar models. It trains AND
evaluates. Regenerated from the Lean lexicon by `python -m finetune.tasks`
(one deduplicated stream → disjoint splits; no eval prompt ever appears in a
training file). **Stale:** the current files were generated from the v1
lexicon (118 lemmas); regenerate against the v2 lexicon (774 lemmas,
23,897 forms) before the next training run.

**`out_of_fragment/`** is real classical Sanskrit the grammar does not model
(other tenses, irregular nouns, compounds). It only evaluates — this is the
project's generalization axis. Hand-curated, never regenerated. Note that
v2 moved several v1 exclusions (consonant stems, ṛ-stems, athematic
presents) *into* the fragment; rows exercising those should migrate to
in-fragment evaluation at the next data refresh.

| File | Rows | Used by | Format / judge |
|---|---|---|---|
| `in_fragment/sft/train.jsonl` | 1000 | **SFT** training (`mode: sft`) | chat `messages`, assistant = `<ans>gold</ans>` |
| `in_fragment/sft/valid.jsonl` | 64 | SFT validation loss | same |
| `in_fragment/grpo/train.jsonl` | 1000 | **GRPO** training (`mode: grpo`) | `prompt` + `answer` (= task spec the reward replays) |
| `in_fragment/grpo/valid.jsonl` | 64 | GRPO validation | same |
| `in_fragment/eval.jsonl` | 150 | checkpoint + final evaluation | eval rows, `judge: lean+chrf` — compile-rate, QA exact, chrF++, TER |
| `out_of_fragment/eval.jsonl` | 36 | generalization benchmark | eval rows, `judge: chrf` — chrF++ and TER only (Lean cannot judge what it doesn't model) |

Task families in the generated files: `qa` (produce one inflected form;
exact-match), `translate` (templated English sentence, **no vocabulary
hints**; verified structurally by the Lean checker — right lemmas in the
right cases), `compose` (one sentence using four required words including an
adjective; grammar by Lean, coverage by constraint bits).

Eval row fields: `prompt`/`system` (what the model sees), `judge` (how it is
scored), `gold` (accepted exact answers, qa only), `specs` (Lean constraint
strings, e.g. `vīra:nom:sg` or `verb:rakṣ:3:sg`), `reference` (for
chrF++/TER). Because Sanskrit word order is free, read the string metrics as
a pair: high chrF++ with high TER (↓ lower is better) means right words in a
different order; low chrF++ with high TER means wrong words. In-fragment,
correctness claims rest on the Lean verdicts, which are order-invariant.

> **Note:** all pre-restructure runs and results (trained on the old
> core/held-out vocabulary tiers) have been deleted; report.html still
> shows numbers from that era. Retraining on this layout starts fresh.
