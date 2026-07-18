# Sanskrit is a programmable language — we ran it on a compiler

```lean
-- "Rāma goes to the village" — the kernel accepts the proof ✓
example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide
-- plural subject, singular verb — this file DOES NOT BUILD ✗
example : Grammatical "bālāḥ grāmaṃ gacchati" := by native_decide
```

Pāṇini compressed Sanskrit into ~4,000 ordered rewrite rules around 400 BCE —
the oldest formal system we have. This repo ports a fragment of that grammar to
**Lean 4**, making grammaticality a decidable, kernel-checkable proposition —
and then trains a language model against the compiler (RLVR/GRPO), with zero
human labels: the grammar generates its own gold answers and judges every
output. On one 18 GB MacBook, the share of the model's Sanskrit sentences that
compile went from **2% → 85%**.

**Read the report → [`index.html`](index.html)** (no Sanskrit or Lean
background assumed). X-post draft: [`POST.md`](POST.md).

## Layout

| Path | What |
|---|---|
| `lean/` | The formalization: phonology, sandhi undoing, 7 vowel-stem declension classes (8 cases × 3 numbers, retroflexion derived by rule), present-tense conjugation both voices, ~100-lemma lexicon, agreement checks. `Sanskrit/Tests.lean` re-proves gold paradigms + positive/negative sentence judgments at every `lake build`. Executables: `check` (20 ms judgment) and `export` (all 1,989 forms). |
| `rlvr.py` | All the Python: tasks generated from the Lean export, Lean-judgment → scalar reward, evaluation (greedy + sampled), checkpoint snapshots. |
| `rewards.py` | 20-line shim registering the reward with mlx-lm-lora's GRPO trainer. |
| `results/` | All eval JSONs and generation snapshots. |
| `plan.html` | The report's design sketch. |

## Results (150 held-out prompts, judged by Lean)

| condition | compiles | QA exact | mean reward | chrF++ |
|---|---|---|---|---|
| Qwen3-4B, untrained | 1.9% | 9.5% | 0.25 | 13.0 |
| RL (GRPO) alone — no examples | 2.8% | 9.5% | 0.26 | 14.1 |
| **SFT on grammar-generated answers** | **85.2%** | **69.0%** | **0.90** | **78.9** |
| → re-quantized 4-bit (RL starting point) | 81.5% | 64.3% | 0.88 | 77.3 |
| → + GRPO (1,200 iters) | 82.4% | 64.3% | 0.88 | 77.6 |

The SFT-vs-RL finding, straight: both signals come from the same compiler.
Distillation does the lifting; RL alone cannot bootstrap a model that is almost
never right; RL after distillation recovers about a point over its true
starting point — less than the between-stage quantization cost. Teach by
example where you can enumerate the truth; RL's room begins where enumeration
ends.

## Reproduce

```sh
cd lean && lake build                    # replays every grammar theorem
cd .. && uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python mlx-lm-lora sacrebleu
.venv/bin/python rlvr.py data && .venv/bin/python rlvr.py data-sft
.venv/bin/python rlvr.py eval --tag base
# SFT -> quantize -> GRPO commands are in the git log; then:
.venv/bin/python rlvr.py eval --tag grpo --model training/sft_4bit --adapter training/adapters
.venv/bin/python rlvr.py snapshots --model training/sft_4bit
```

## Scope

A fragment, honestly: no consonant stems, one tense, no compounds; the checker
verifies structure, not meaning. Declension tables cross-verified against
vidyut-prakriya (2,496 cells). Prior art: type-theoretic NL *semantics* (GF,
Coq-NLI); to our knowledge this is the first machine-checked Pāṇinian fragment
in a general-purpose prover, and the first RLVR run whose reward is a
prover-checked judgment of natural-language grammaticality.

*Pāṇini's grammar was always a program. It just waited 2,300 years for a runtime.*
