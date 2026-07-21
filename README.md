# Sanskrit compiles — a Lean 4 grammar as a fine-tuning reward

```lean
-- the kernel accepts this proof ✓
example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide
-- plural subject, singular verb — this file DOES NOT BUILD ✗
example : Grammatical "bālāḥ grāmaṃ gacchati" := by native_decide
```

A fragment of Pāṇini's Sanskrit grammar formalized in **Lean 4**, so that a
sentence is grammatical iff its check compiles — and a small experiment
framework that fine-tunes an open LLM (Qwen3-4B) against that checker,
comparing **pure SFT** with the canonical **SFT → GRPO** pipeline. Two
interchangeable training backends: **mlx** (Apple Silicon, LoRA on a 4-bit
base) and **cuda** (Lambda-class GPUs via TRL — full-parameter SFT, LoRA
GRPO with vLLM rollouts, bf16 throughout, no quantization). No human labels
anywhere: the grammar generates its own training answers and judges every
model output.

**Read the report → [`report/report.html`](report/report.html)** — results, figures, and
the full story, no Sanskrit or Lean background assumed.

## Repository map

| Path | What it is |
|---|---|
| [`lean/`](lean/) | **The verifier.** The Sanskrit fragment as a Lean 4 library — `Grammatical : String → Prop`, decidable, re-proved at every `lake build`. Its two executables, `check` (exit 0 iff grammatical, `--json` diagnostics) and `export` (every inflected form as TSV), are the *only* interface the rest of the repo uses. Full spec of what's covered: [lean/README.md](lean/README.md). |
| [`finetune/`](finetune/) | **The experiment framework** — ~800 lines of Python: data generation, SFT/GRPO orchestration, the Lean-backed reward, checkpoint evaluation, benchmarking, live dashboard. File-by-file tour below. |
| [`finetune/configs/`](finetune/configs/) | One YAML per experiment — a config is the *entire* experiment definition. [`example.yaml`](finetune/configs/example.yaml) documents every field. |
| [`data/`](data/) | Two groups: `in_fragment/` (trains SFT + GRPO, and evaluates) and `out_of_fragment/` (evaluates only — the generalization axis); per-file table in [data/README.md](data/README.md). |
| `runs/` | One directory per training run (gitignored): frozen config, train.log, adapter checkpoints, metrics, generation snapshots. Anatomy below. |
| `results/` | Benchmark outputs (created by `finetune.evaluate`). Empty since the in/out-fragment restructure — populated by the next training + benchmarking pass. |
| [`scripts/`](scripts/) | [`lambda_setup.sh`](scripts/lambda_setup.sh) — one-shot bring-up of a fresh CUDA box (uv, elan, `lake build`, `uv sync --extra cuda`). |
| [`pyproject.toml`](pyproject.toml) | The uv project: shared deps plus one platform-marked extra per backend (`mlx` / `cuda`), locked together in `uv.lock`. |
| [`report/`](report/) | The technical report (markdown draft + rendered HTML; its numbers predate the restructure and the clearing of runs/results). |

## How an experiment flows

Two pipelines, both rooted in the Lean verifier. The Python layer never
makes a linguistic decision of its own — every judgment is delegated to the
compiled `check` binary, every word form comes from `export`.

**Data generation** — run once, or whenever the Lean lexicon changes:

```
lean export ─────▶ python -m finetune.tasks ─────▶ data/in_fragment/{sft,grpo,eval}
(all 2,882         one seeded, deduplicated        (disjoint slices: no eval prompt
 inflected forms)  stream of tasks                  ever appears in training)

data/out_of_fragment/eval.jsonl — hand-curated classical Sanskrit, never generated
```

**Training + evaluation** — one YAML config = one experiment:

```
finetune/configs/<exp>.yaml
    │    bash finetune/run.sh finetune/configs/<exp>.yaml
    ▼
finetune/train.py — the orchestrator
    │  1. resolve the base model: a plain HF model, or (model.init_from_run)
    │     the SFT→GRPO handoff — cuda: the source run's full checkpoint
    │     becomes the base directly; mlx: fuse the source adapter into its
    │     base and re-quantize to 4-bit
    │  2. judge the starting point            → metrics.jsonl (checkpoint 0)
    │  3. hand off to the backend trainer     → train.log, checkpoints/
    │     (mlx: mlx_lm_lora.train · cuda: finetune.cuda_train, i.e. TRL)
    │        SFT:  imitate <ans>gold</ans> completions from data/in_fragment/sft
    │        GRPO: sample group_size completions per prompt, score each via
    │              the reward shim → reward.py → lean.py → the check binary
    │  4. judge every checkpoint: generate on the eval prompts, run the
    │     Lean checker, compute chrF++ + TER  → metrics.jsonl, snapshots/
    ▼
runs/<run_name>/ — a self-describing artifact
    │    python -m finetune.evaluate --run <name> \
    │        --benchmark data/{in_fragment,out_of_fragment}/eval.jsonl
    ▼
results/<tag>__<group>_eval.json ─────▶ report figures
```

## The fine-tuning code, file by file

| File | Role |
|---|---|
| [`run.sh`](finetune/run.sh) | Entry point. Reads the config's `backend:` line, syncs the matching uv extra, and `exec`s `uv run python -m finetune.train` from the repo root. The mlx path additionally forces offline mode (`HF_HUB_OFFLINE=1` — models must already be in the HF cache). |
| [`train.py`](finetune/train.py) | The orchestrator (the flow above). Validates the config, refuses to clobber an existing run, derives the iteration count (`epochs` × dataset rows ÷ `batch_size` when `iters: null`), spaces checkpoints at `iters ÷ eval.checkpoints`, assembles the backend trainer command (mlx: `mlx_lm_lora.train` flags · cuda: `finetune.cuda_train`), and evaluates checkpoint 0, every intermediate checkpoint, and the final one. |
| [`cuda_train.py`](finetune/cuda_train.py) | The CUDA trainer (TRL). `mode: sft` = full-parameter bf16 fine-tune; `mode: grpo` = fresh LoRA on the last `num_layers` blocks with vLLM colocated on the training GPU for rollouts. Disabling the adapter recovers the base exactly, which is what TRL uses as GRPO's KL reference — the fuse/requantize step of the mlx handoff disappears. Defines the TRL-side `lean_sanskrit_reward`. |
| [`cuda_eval.py`](finetune/cuda_eval.py) | CUDA-side checkpoint evaluation: loads a full checkpoint or base+adapter (merged), generates in batches, then judges through the same shared machinery as mlx. |
| [`tasks.py`](finetune/tasks.py) | Data generator. Pulls the lexicon through `lean.py`, emits the three task families from one seeded, deduplicated stream, and slices that stream into disjoint train/valid/eval splits. Also owns the English half of the templates (pluralization, glosses). |
| [`lean.py`](finetune/lean.py) | The only bridge to the verifier. `check(sentence, constraints)` shells out to `lean/.lake/build/bin/check --json` (memoized, 200k entries — GRPO re-scores duplicates constantly); `lexicon()` parses `export`'s TSV into `{noun, adj, verb, ind}`. |
| [`reward.py`](finetune/reward.py) | Completion → score in [0, 1] (next section). Also defines the shared system prompt and the `<ans>…</ans>` extraction + Unicode normalization used everywhere. |
| [`rewards_shim.py`](finetune/rewards_shim.py) | The 18 lines mlx-lm-lora actually loads: registers `lean_sanskrit_reward`, which replays each dataset row's `answer` spec against the sampled completion. (The cuda backend registers its equivalent inside `cuda_train.py`.) |
| [`common.py`](finetune/common.py) | Shared evaluation machinery: model + adapter loading, generation, per-row judging (respecting each row's `judge` field), and the summary metrics — `compile_rate`, `qa_exact`, `mean_reward`, `chrf_pp`, `ter`. Used identically by `train.py` checkpoints and `evaluate.py` benchmarks, so numbers are comparable across both. |
| [`evaluate.py`](finetune/evaluate.py) | Standalone benchmark CLI: any run checkpoint (`--run`, optionally `--checkpoint N`) or any raw model (`--model`) × any eval file → `results/<tag>__<benchmark>.json` with the summary plus every individual generation and judgment. |
| [`dashboard.py`](finetune/dashboard.py) | Zero-dependency stdlib HTTP server that watches **all** of `runs/`: live loss/reward curve parsed from `train.log` as it grows, checkpoint metrics, and the latest sample generations with their Lean verdicts. Polls every 5 s. |
| [`configs/`](finetune/configs/) | The experiments, one pair per backend: mlx — [`sft-baseline.yaml`](finetune/configs/sft-baseline.yaml), [`sft-then-grpo.yaml`](finetune/configs/sft-then-grpo.yaml); cuda — [`cuda-sft-baseline.yaml`](finetune/configs/cuda-sft-baseline.yaml), [`cuda-sft-then-grpo.yaml`](finetune/configs/cuda-sft-then-grpo.yaml), [`cuda-smoke.yaml`](finetune/configs/cuda-smoke.yaml) (fast end-to-end check); plus the fully documented [`example.yaml`](finetune/configs/example.yaml). |

### The reward, precisely

GRPO optimizes [`reward.py`](finetune/reward.py):

```
reward = 0.15 · format + 0.85 · task          ∈ [0, 1]
```

- **format** — the answer arrived inside `<ans></ans>` tags (fallback:
  last non-empty line, format = 0).
- **task, `qa`** — exact match against the Lean-exported gold forms after
  normalization. A near-miss earns at most `0.25 × similarity`, and only
  above 50% similarity — partial credit exists but can't be farmed.
- **task, `translate` / `compose`** — three *multiplied* factors:

  ```
  task = grammar × (0.15 + 0.85 · content) × length-damping
  ```

  *grammar* = the five component verdicts from `check --json`, weighted
  (words 0.40, subject 0.20, clauses 0.15, object 0.15, adjective 0.10);
  *content* = the fraction of the prompt's constraint bits satisfied
  (`rāma:nom:sg`, `verb:gam:3:sg`, bare lemmas);
  *length-damping* = 1.0 up to 9 tokens (translate) / 12 (compose), then
  decaying toward a 0.05 floor.

The multiplication is the anti-gaming design: a fluent sentence that ignores
the prompt and a constraint-hitting word salad both score near the floor.
This shape survived an adversarial red-team in an earlier iteration of the
project (see the report).

### data/ — two groups, three task families

Everything under `data/in_fragment/` is regenerated by
`python -m finetune.tasks`; `data/out_of_fragment/eval.jsonl` is hand-curated
and never regenerated. The per-file table lives in
[data/README.md](data/README.md).

The task families (all machine-checkable — no human labels):

- **qa** — produce one inflected form (*"What is the instrumental singular
  of the Sanskrit noun rāma?"*); judged by exact match.
- **translate** — a templated English sentence with **no vocabulary hints**
  (*"Translate into Sanskrit: 'The heroes protect the village.'"*); judged
  structurally — the output must compile *and* satisfy specs like
  `vīra:nom:pl`, `verb:rakṣ:3:pl`, `grāma:acc:sg`.
- **compose** — one grammatical sentence using four required words (a verb,
  two nouns, an adjective), inflected however the model likes.

The two on-disk formats: `sft/` rows are chat transcripts whose assistant
turn is `<ans>gold</ans>`; `grpo/` rows carry the task spec in an `answer`
field that the reward replays at sampling time.

The two groups:

| Group | Files | Role |
|---|---|---|
| **in-fragment** | `in_fragment/sft/` + `in_fragment/grpo/` train/valid (1000 + 64 rows each), `in_fragment/eval.jsonl` (150) | trains both arms; evaluates in-distribution skill (eval prompts disjoint from training; judged by Lean + chrF++/TER) |
| **out-of-fragment** | `out_of_fragment/eval.jsonl` (36, hand-curated) | the generalization axis: real classical Sanskrit outside the formalization — judged by chrF++/TER only, since Lean has no model of it |

### runs/ — what a training run leaves behind (gitignored)

```
runs/<run_name>/
├── config.yaml      frozen, normalized copy of the launch config
├── train.log        raw trainer output (what the dashboard tails)
├── tb/              TensorBoard event files (cuda): per-step loss/reward/KL
│                    + the eval/* scores at every eval point, live
├── checkpoints/     every `eval.every` iterations —
│                    mlx:  0000100_adapters.safetensors … + adapters.safetensors
│                    cuda: checkpoint-100/ … + final/ (SFT: a full model;
│                          GRPO: a PEFT adapter dir; final path is the
│                          config's model.final_checkpoint)
├── fused_4bit/      mlx only, and only when a later run chains from this one
│                    (init_from_run fuses + re-quantizes into the source run;
│                    the cuda handoff needs no such artifact)
├── metrics.jsonl    one line per eval point with one summary object per
│                    benchmark group: in_fragment {compile_rate, qa_exact,
│                    mean_reward, chrf_pp, ter}, out_of_fragment {chrf_pp,
│                    ter} (line 0 = the untrained start)
└── snapshots/       checkpoint_<it>/{in_fragment,out_of_fragment}.jsonl —
                     every eval generation with its extracted answer,
                     reward breakdown, and Lean verdict
```

### Watching a cuda run live

Per-step training metrics and the per-`eval.every` benchmark scores stream
to TensorBoard as they happen (evals run *inside* the trainer, on the live
model — you see compile-rate climb mid-run, not after):

```sh
# on the box
uv run tensorboard --logdir runs --port 6006
# from your laptop
ssh -L 6006:localhost:6006 ubuntu@<lambda-ip>   # → http://localhost:6006
```

(mlx runs evaluate after training instead — the zero-dependency dashboard
at :8777 is the live view there.)

### results/ — the committed outputs

- `results/<tag>__<benchmark>.json` — one file per `evaluate.py` invocation
  (e.g. `sft-then-grpo__in_fragment_eval.json`): the summary metrics plus
  every record, so any number in the report can be traced to the exact
  generation behind it.
- `results/runs/` — frozen copies of each headline run's `config.yaml`,
  `metrics.jsonl`, and `snapshots/`, so the report's training curves are
  reproducible without re-running training.

## Running an experiment

Dependencies are managed by [uv](https://docs.astral.sh/uv/) — one lockfile,
two install profiles (`--extra mlx` / `--extra cuda`); `run.sh` picks the
right one from the config's `backend:` line automatically.

**Locally (Apple Silicon, mlx):**

```sh
# one-time setup
cd lean && lake build && cd ..                 # build the verifier (+ theorems)
uv sync --extra mlx

# launch (config = the entire experiment definition)
bash finetune/run.sh finetune/configs/sft-baseline.yaml
bash finetune/run.sh finetune/configs/sft-then-grpo.yaml   # after the SFT run
```

**On a CUDA box (Lambda etc.):**

```sh
bash scripts/lambda_setup.sh                   # uv + elan + lake build + uv sync
bash finetune/run.sh finetune/configs/cuda-smoke.yaml       # ~5 min sanity check
bash finetune/run.sh finetune/configs/cuda-sft-baseline.yaml
bash finetune/run.sh finetune/configs/cuda-sft-then-grpo.yaml
```

The cuda backend trains full-parameter for SFT (no LoRA bottleneck where the
model absorbs new vocabulary) and LoRA for GRPO (where the reference model
comes free: TRL computes KL log-probs by disabling the adapter). Rollouts go
through vLLM colocated on the training GPU. Everything runs in bf16 — the
4-bit quantization of the mlx pipeline, including the lossy fuse-requantize
handoff, does not exist here.

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
  (`data/in_fragment/sft` or `data/in_fragment/grpo`).
- `model.init_from_run` — chain runs (the SFT→GRPO handoff). cuda: the named
  run's final full-model checkpoint becomes this run's base, losslessly.
  mlx: fuses the named run's final adapter into its base and re-quantizes to
  4-bit (the quantization cost is measured into `metrics.jsonl`).
- `hyperparameters` — mirrored onto the backend trainer; `iters: null` +
  `epochs: N` derives the count for SFT. GRPO knobs: `group_size`, `beta`
  (KL leash), `temperature`, `max_completion_length`; cuda adds the LoRA
  shape (`lora_rank`, `lora_alpha`) and vLLM controls (`use_vllm`,
  `vllm_gpu_memory_utilization`).
- `eval` — which prompts, how many per checkpoint, decoding temperature,
  number of checkpoints.
- `backend: mlx | cuda` — which trainer runs the experiment (validated at
  startup); everything else in the config means the same thing on both.

### Benchmarking any model

```sh
uv run python -m finetune.evaluate --run sft-then-grpo \
    --benchmark data/in_fragment/eval.jsonl
uv run python -m finetune.evaluate --model mlx-community/Qwen3-4B-Instruct-2507-4bit \
    --tag base --benchmark data/out_of_fragment/eval.jsonl
# on a CUDA box, raw models need the backend spelled out:
#   ... --model Qwen/Qwen3-4B-Instruct-2507 --backend cuda --tag base ...
```

Each row is judged per its `judge` field: `lean+chrf` (compile-rate, QA
exact-match, reward, chrF++, TER) or `chrf` (reference similarity only —
used out of fragment, where Lean has no model to judge with). Because
Sanskrit word order is free, read chrF++ and TER (↓) as a pair: high chrF++
with high TER means right words in a different order. Outputs land in
`results/<tag>__<group>_eval.json`.

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
