# data/

Every file here is data (no scripts/configs); everything is regenerable by a
script under `misc/data/`, deterministic at seed 42.

## eval/ — full reference corpora (never train on these directly)

| file | contents | built by |
|---|---|---|
| `samayik.json` | 48,326 EN→SA pairs, full Samayik corpus | `misc/data/fetch_samayik_eval.py` |
| `flores-200.json` | 2,009 EN→SA pairs, FLORES-200 dev+devtest | `misc/data/fetch_flores_eval.py` |

Flat `[{"en", "sa"}]` arrays. Training/eval splits are *derived* from these by
`make_standard_sft_data.py`; scoring runs use the `*_validation.json` splits
below, not these files.

## finetune/task-data/ — vidyut-prakriya morphology task

Built by `misc/data/generate_dataset.py` from `vidyut_dhatupatha_5.tsv`
(the source lexicon, checked in here). Split dhatu-wise, so validation
dhatus are never seen in training.

- `finetune.json` — 6,018 tasks / 2,006 dhatus (GRPO + distillation prompts)
- `validation.json` — 669 tasks / 223 dhatus, disjoint by dhatu (pass@k evals)
- `metadata.json` — generation provenance (seed, coordinate space, counts)
- `sdpo-finetune.json` — SDPO variant, built by `misc/data/make_sdpo_data.py`

## finetune/sft-r1/ — Opus 5 distillation corpus (morphology traces)

Built by `misc/data/generate_sft_data.py misc/data/claude-opus-5-sft.yml`:
Claude Opus 5 rejection-sampled over the training tasks, keeping only
vp_exact-perfect completions.

- `claude-opus-5.json` — kept traces, TRL prompt/completion schema
- `claude-opus-5.smoke.json` — tiny smoke-run counterpart
- `raw/` — Batches-API result cache + resume state (keep: re-runs are free)

## finetune/sft-standard/ — translation SFT splits (contamination-free)

Built by `misc/data/make_standard_sft_data.py` from `data/eval/`. Pairs
sharing a normalized (whitespace/case) EN **or** SA sentence always land on
the same side of the split, and finetune sets are filtered against BOTH
validation sets, so no validation sentence appears in any finetune corpus
with a variant translation.

- `samayik_finetune.json` — 47,576 SFT records · `samayik_validation.json` — 750 pairs
- `flores-200_finetune.json` — 1,259 SFT records · `flores-200_validation.json` — 750 pairs

`*_finetune.json` use the TRL prompt/completion schema; `*_validation.json`
use the same `[{"en", "sa"}]` shape as `data/eval/` and are what
`misc/final_translation_eval.py` scores.

## finetune/sft-upsample-mix/ — mixture corpora (translation + morphology)

Built by `misc/data/make_mixed_sft_data.py`: samayik_finetune.json plus the
sft-r1 traces upsampled ×k, one corpus per ratio.

- `mix-upsample-{0.5,1,2,4,6,8,10}.json` — the seven sweep arms
- `val-{translation,morphology}.json` — fixed eval-loss split, identical across arms

⚠ Current files predate the 2026-08-24 contamination-free rework (they were
built from the old `sft-standard/samayik.json`). They document what the
existing mix-upsample checkpoints trained on; re-run the script before
training anything new on them.
