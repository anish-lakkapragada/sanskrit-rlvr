# data/ — two groups: in_fragment and out_of_fragment

**`in_fragment/`** is everything the Lean grammar models. It trains AND
evaluates. Regenerated from the Lean lexicon by `python -m finetune.tasks`
(one deduplicated stream → disjoint splits; no eval prompt ever appears in a
training file).

**`out_of_fragment/`** is real classical Sanskrit the grammar does not model
(other tenses, consonant stems, compounds). It only evaluates — this is the
project's generalization axis. Hand-curated, never regenerated.

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
