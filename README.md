# Sanskrit compiles — a Lean 4 grammar as a fine-tuning reward

```lean
-- the kernel accepts this proof ✓
example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide
-- plural subject, singular verb — this file DOES NOT BUILD ✗
example : Grammatical "bālāḥ grāmaṃ gacchati" := by native_decide
```

A fragment of Pāṇini's Sanskrit grammar formalized in **Lean 4**, so that a
sentence is grammatical iff its check compiles — and a small experiment
framework that fine-tunes an open LLM (Qwen3-4B, Apple MLX) against that
checker, comparing **pure SFT** with the canonical **SFT → GRPO** pipeline.
No human labels anywhere: the grammar generates its own training answers and
judges every model output.

**Read the report → [`report.html`](report.html)** — results, figures, and
the full story, no Sanskrit or Lean background assumed.

## Repository map

| Path | What it is |
|---|---|
| `lean/` | The formalization. `Sanskrit/` modules: phonology, transliteration, declension (7 vowel-stem classes, retroflexion derived by rule), conjugation, sandhi undoing, sentence-level agreement; `Grammatical : String → Prop` is decidable. `Tests.lean` re-proves gold paradigms + positive/negative sentences at every `lake build`. Executables: `check` (`--json` diagnostics; exit 0 iff grammatical) and `export` (every inflected form as TSV, tagged `core` or `heldout`). |
| `data/` | All training/eval sets, with a README mapping each file to the experiment that uses it. Training draws only from core vocabulary; two generalization benchmarks (held-out lemmas; beyond-fragment classical lines) never appear in training. Regenerate with `python -m finetune.tasks`. |
| `finetune/` | The framework (below) plus per-module code: `lean.py` (checker bridge), `reward.py` (score in [0,1]), `tasks.py` (data generation), `common.py` (generation + checkpoint eval), `rewards_shim.py` (GRPO hook), `dashboard.py` (live view). |
| `finetune/configs/` | One YAML per experiment. `example.yaml` documents every field. |
| `runs/` | One directory per experiment run (gitignored): frozen config, train.log, checkpoints, metrics.jsonl, generation snapshots. |
| `results/` | Committed benchmark outputs the report's figures are built from. |
| `report.html` | The technical report. |

## Running an experiment

```sh
# one-time setup
cd lean && lake build && cd ..                 # build the verifier (+ theorems)
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python mlx-lm-lora sacrebleu pyyaml

# launch (config = the entire experiment definition)
bash finetune/run.sh finetune/configs/sft-baseline.yaml
bash finetune/run.sh finetune/configs/sft-then-grpo.yaml   # after the SFT run
```

Each run: evaluates its starting point, trains, saves a checkpoint every 25%
of iterations, and at every checkpoint generates answers for the eval
prompts, judges them with the Lean checker, and computes chrF++ — appending
one line per checkpoint to `runs/<name>/metrics.jsonl` and the raw
generations to `runs/<name>/snapshots/`. Watch it live at
`http://localhost:8777` (`dashboard.enabled` in the config).

### Changing a configuration

Copy any config, edit, launch. The fields that matter most:

- `run_name` — names `runs/<run_name>/`; a run refuses to overwrite an
  existing directory (pass `--force` to replace it).
- `mode: sft | grpo` — supervised imitation of grammar-generated answers vs
  RLVR against the checker (GRPO). Point `data.dir` at the matching format
  (`data/sft` or `data/grpo`).
- `model.init_from_run` — chain runs: fuses the named run's final adapter
  into its base, re-quantizes to 4-bit, and starts from that (the SFT→GRPO
  handoff; the quantization cost is measured into `metrics.jsonl`).
- `hyperparameters` — mirrored onto mlx-lm-lora flags; `iters: null` +
  `epochs: N` derives the count for SFT.
- `eval` — which prompts, how many per checkpoint, decoding temperature,
  number of checkpoints.
- `backend: mlx` — the only supported backend (validated at startup).

### Benchmarking any model

```sh
.venv/bin/python -m finetune.evaluate --run sft-then-grpo \
    --benchmark data/eval/held_out_vocab.jsonl
.venv/bin/python -m finetune.evaluate --model mlx-community/Qwen3-4B-Instruct-2507-4bit \
    --tag base --benchmark data/eval/beyond_fragment.jsonl
```

Each row is judged per its `judge` field: `lean+chrf` (compile-rate, QA
exact-match, reward, chrF++) or `chrf` (reference similarity only — used
beyond the fragment, where Lean has no model to judge with). Outputs land in
`results/<tag>__<benchmark>.json`.

## The two claims, honestly scoped

1. A natural language's grammar — a genuine Pāṇinian fragment: 7 vowel-stem
   classes × 8 cases × 3 numbers, present tense both voices, ~125 lemmas,
   sandhi undone at word boundaries, ca-coordinated clauses of any length —
   can live in a general-purpose prover with grammaticality as a
   kernel-checkable proposition.
2. The standard RLVR pipeline runs end-to-end against it, and the framework
   here measures what each training signal contributes (see the report for
   findings, including where RL does and does not help).

Not modeled: other tenses, consonant stems, compounds, meaning. Paradigm
tables were cross-verified against vidyut-prakriya (an independent Pāṇinian
engine) in an earlier iteration; gold tables are kernel-checked theorems in
`lean/Sanskrit/Tests.lean`.
