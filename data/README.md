# data/ — what trains what, and what only evaluates

Everything except `eval/beyond_fragment.jsonl` is regenerated from the Lean
lexicon by `python -m finetune.tasks` (one deduplicated stream → disjoint
splits; nothing in any eval file ever appears in a training file).

| File | Rows | Vocabulary | Used by | Format |
|---|---|---|---|---|
| `sft/train.jsonl` | 1000 | core tier only | **SFT** training (`mode: sft` configs) | chat `messages`, assistant = `<ans>gold</ans>` |
| `sft/valid.jsonl` | 64 | core tier only | SFT validation loss | same |
| `grpo/train.jsonl` | 1000 | core tier only | **GRPO** training (`mode: grpo` configs) | `prompt` + `answer` (= task spec the reward replays) |
| `grpo/valid.jsonl` | 64 | core tier only | GRPO validation | same |
| `eval/in_fragment.jsonl` | 150 | core tier (prompts disjoint from training) | checkpoint + final evaluation | eval rows, `judge: lean+chrf` |
| `eval/held_out_vocab.jsonl` | 100 | **held-out tier**: lemmas that exist in the Lean model but are banned from all training data | generalization benchmark (unseen words, still Lean-verifiable) | eval rows, `judge: lean+chrf` |
| `eval/beyond_fragment.jsonl` | 36 | **beyond the fragment**: canonical maxims + textbook sentences using tenses/stems the Lean model doesn't cover | generalization benchmark; hand-curated, never regenerated | eval rows, `judge: chrf` (Lean cannot judge vocabulary it doesn't model) |

Task families in the generated files: `qa` (produce one inflected form;
exact-match), `translate` (templated English sentence, **no vocabulary
hints**; verified structurally by the Lean checker — right lemmas in the
right cases), `compose` (one sentence using four required words including an
adjective; grammar by Lean, coverage by constraint bits).

Eval row fields: `prompt`/`system` (what the model sees), `judge` (how it is
scored), `gold` (accepted exact answers, qa only), `specs` (Lean constraint
strings, e.g. `vīra:nom:sg` or `verb:rakṣ:3:sg`), `reference` (for chrF++).
