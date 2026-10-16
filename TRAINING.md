# Training handoff: vidyut-prakriya-bench

This branch prepares a four-family Sanskrit morphology benchmark and the inputs
for later post-training of Qwen3-4B. Build and validate the benchmarks first;
rewrite the training integration against that fixed contract afterwards.

Created on 2026-10-10 as `finetune/vidyut-prakriya-bench`, based on
`finetune/vidyut-prakriya` at `e94499639cf58a6518aa99139fab6818e93346d1`.
This branch contains the new benchmark sources and all four morphology
generators/exports, the requested old trace archive, v2 prompts, and this handoff. The old
training code, configs, benchmarks, reports, and dependency files live on the
previous branch. Harbor datasets and the new training code are still to be built.

## 1. Start here

```text
data/
  engine/
    files/
      vidyut_dhatupatha_5.tsv    # existing verbal-root inventory, unchanged
      nominal-stems.csv         # Monier-Williams nominal stems + genders
      nominal-stems.LICENSE     # upstream data license, unchanged
      mw-lexnorm/               # selected sole lexical source for nominal tasks
      sources.json             # source revisions, checksums, counts
      README.md                # how to interpret these inputs
    prompts/v2/
      vp_tinanta.txt            # v2 thinking + answer prompt
      vp_krdanta.txt
      vp_subanta.txt
      vp_taddhitanta.txt
    tinanta/
      generate.py               # pinned exhaustive VP enumeration
      verify.py                 # full-grid validation and re-derivation
      README.md
    krdanta/                   # reviewed krt enumeration and verification
    subanta/                   # MWlexnorm normalization, enumeration, row audits
    taddhitanta/               # all 175 VP suffixes; historical pilot preserved
  datasets/
    traces-opus-5/
      tinanta_old.json          # unchanged copy of the original SFT corpus
      README.md                # schema and v1 prompt provenance
    tinanta/                   # 423,324 eligible tasks + manifest and exclusions
    subanta/                   # 1,780,632 tasks + manifest and source-row audits
    krdanta/                   # 27,470 reviewed tasks + manifest
    taddhitanta/               # 3,342,776 tasks + complete request/source audits
TRAINING.md                    # this handoff
```

The [tiṅanta export](data/datasets/tinanta/README.md) contains **423,324**
eligible tasks. Of 601,830 candidates, 178,320 invalid bhāve coordinates are
excluded before VP is called, and 186 conflicting prompts are excluded after
hydration. Every retained answer has been rederived. The legacy comparison
accounts for 4,711 matching records and 1,976 now-excluded records.

The [kṛdanta export](data/datasets/krdanta/README.md) contains **27,470** tasks.
The [subanta export](data/datasets/subanta/README.md) contains **1,780,632** tasks
from the 74,193 filtered stem–gender pairs in the shared MWlexnorm inventory.
The [taddhitānta export](data/datasets/taddhitanta/README.md) uses those same
inputs and all 175 VP suffixes, with unrestricted meaning, yielding
**3,342,776** tasks. Source gender and basic/nyap interpretation are preserved
in both nominal families; unsupported raw headwords are not reintroduced.
All four families total **5,574,202** records; see the
[dataset index](data/datasets/README.md) and
[eligibility audit](data/datasets/validity-audit.json). Future splits will live
at `data/datasets/<family>/{train,dev,test}/<task-id>/`. Run Harbor on a specific
split, never on all of `data/` or a mixed train/test directory.

The old code and results are archived on
[`finetune/vidyut-prakriya`](https://github.com/anish-lakkapragada/sanskrit-rlvr/tree/finetune/vidyut-prakriya).
All historical file links below point to the fixed checkpoint
`e94499639cf58a6518aa99139fab6818e93346d1`, not files in this branch.
New builders should use `data/engine/files/` and the family template under `data/engine/prompts/v2/`.
The old `vp_task_eval.txt` filename is absent here.

Read an archived file without restoring the old project into this checkout:

```bash
git show e94499639cf58a6518aa99139fab6818e93346d1:finetune/grpo.py
```

For a separate working copy of the old implementation, use a sibling worktree:

```bash
git worktree add --detach ../sanskrit-vp-training-reference e94499639cf58a6518aa99139fab6818e93346d1
```

This handoff describes that archived implementation so a later agent can
rewrite the parts needed by the new four-family benchmark.

The [plain-language morphology guide](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/benchmarks/a-b-c/VP-Other-Tasks-Explained.html)
explains stems, roots, suffixes, and the API options. The
[generation guide](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/benchmarks/a-b-c/VP-Bench-ABC-Generation.md) describes the older
VP and A/B/C experiments. Those diagnostic A/B/C tasks are not the four new
forward-generation families.

## 2. What the four families predict

| Family / VP function | Starting material | Requested choices | Expected answer |
| --- | --- | --- | --- |
| [Tiṅanta / `derive_tinantas`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/struct.Vyakarana.html#method.derive_tinantas) | Dhātu: a verbal root, with its citation markers and class | Tense/mood, voice, person, number | A conjugated verb, such as भवति |
| [Subanta / `derive_subantas`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/struct.Vyakarana.html#method.derive_subantas) | Prātipadika: a nominal stem, the starting form of a noun or adjective | Gender, case, number | An inflected noun/adjective, such as देवेन |
| [Kṛdanta / `derive_krdantas`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/struct.Vyakarana.html#method.derive_krdantas) | Dhātu | A kṛt suffix, plus any conditions required by that suffix | A derived stem or indeclinable, such as कृत |
| [Taddhitanta / `derive_taddhitantas`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/struct.Vyakarana.html#method.derive_taddhitantas) | Prātipadika | A taddhita suffix and any explicit meaning condition | A derived stem or indeclinable, such as धनवत् |

There are **four families total**, with three additions to the existing finite
verb task. Nominal tasks do not take a dhātu. The two suffix tasks do not
automatically ask for case/number inflection of their result; doing that is a
second, subanta operation. Specify whether an initial suffix benchmark includes
indeclinables or only declinable stems.

The familiar tiṅanta “4D coordinates” are lakāra × prayoga × puruṣa × vacana.
The old classical candidate grid has 10 × 3 × 3 × 3 = 270 combinations per root.
Subanta has 8 cases × 3 numbers = 24 candidates per resolved stem–gender pair.
A row listing three genders ordinarily gives 72; explicit alternative stems
can increase that count. The implemented adapter contributes 0, 24, 48, 72,
96, or 120 tasks per source row before deduplication across rows. Eligibility
is restricted by source genders and grammatical behavior. Suffix tasks have
base × suffix candidate grids, with further conditions. None is an unrestricted
Cartesian product of valid Sanskrit requests. Current JSON inventories retain eligible, nonempty, renderable tasks and audit
excluded candidates separately. Engine errors abort publication. In particular,
a classical bhāve request needs third-person singular; that restriction is
enforced before calling VP. A nonempty engine result alone is not sufficient
evidence that arbitrary coordinates are suitable.

The implemented tiṅanta, kṛdanta, and subanta generators pin `vidyut==0.4.0`, matching the archived
generator. The Rust source used by A/B/C was
`8da2f90bee3ce1c07505fa432fc3729e3f7e02ea`. The taddhitanta pilot builds the Rust
engine from the checksum-pinned Python 0.4.0 source archive to pass explicit
meaning conditions. In Python 0.4.0, the simple kṛdanta/taddhita constructors expose fewer
controls than the Rust builders. A prompt's meaning condition must actually
reach the engine; use a pinned Rust builder where the Python API cannot express
it. Check the [Python API](https://vidyut.readthedocs.io/en/latest/prakriya.html)
and [Rust arguments](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/index.html)
against the selected version.

## 3. Sources, old traces, and deterministic generation

[data/engine/files/README.md](data/engine/files/README.md) and
[sources.json](data/engine/files/sources.json) record the lexical sources. The TSV is
the exact existing project file: 2,259 rows, of which 2,229 are usable roots.
The nominal CSV contains 186,119 records and 170,576 distinct stem spellings;
it is a raw input pool, not a list of validated VP tasks.

Load dhātus with `Data.load_dhatu_entries()` or the corresponding Rust
Dhātupāṭha loader. Root citation, class, and entry number matter: the loader
preserves subclass metadata that a bare string constructor can lose. Preserve
SLP1 capitalization and citation markers. Render Devanagari for the prompt,
but retain the exact engine inputs in the task record.

The nominal source supplies `stem` and `stem_genders`, without meanings or
stable dictionary entry IDs. Preserve source row numbers and checksums, define
duplicate handling, map genders, and review stem construction before deriving
forms. Some feminine stems need `Pratipadika.nyap` instead of `basic`; upstream
Vidyut's lexicon builder also adapts/filter source spellings. That preprocessing
must become an explicit, versioned rule, not a silent edit to the raw CSV.

[tinanta_old.json](data/datasets/traces-opus-5/tinanta_old.json) contains **7,851 traces
for 4,564 distinct task IDs**. All have stored reward 1.0 under the old reward,
and all contain `<thinking>`. Each record stores `id`, `sample`, conversational
`prompt`/`completion`, gold answers, dhātu, morphology, and teacher metadata.
The archive is byte-identical to the previous branch's
`data/finetune/sft-r1/claude-opus-5.json` at the checkpoint above.
Its embedded prompts and metadata still say `v1/vp_task_eval.txt`; moving the
file does not convert it to v2. Do not silently train v2 on these v1 pairs.
Any conversion must create a separate, reverified corpus with its own manifest.

The old [generator](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/misc/data/generate_dataset.py) samples three coordinate
tuples per usable root with seed 42, derives sorted unique gold forms, and
splits by dictionary code, yielding 6,018 training and 669 validation tasks.
Different dictionary codes can describe the same root/class family, so a split
by code alone is not a guarantee of lexical-family isolation.

For the new generators, make regeneration reproducible by recording:

1. Source hashes, engine revision, generator revision, and all engine flags.
2. Reviewed candidate filters, explicit ordering of entries/options, RNG seed,
   sampling quotas, and the split policy where applicable. The current exhaustive
   tiṅanta export uses no RNG, sampling, filtering, or split. Sort gold sets
   and output records.
3. Complete engine arguments and every accepted gold form in both SLP1 and
   Devanagari. An empty derivation may mean unsupported input; log exclusions
   separately from engine exceptions.
4. Stable semantic IDs based on family + canonical request, rather than prompt
   wording. Hash rendered prompts separately. Record every prompt field's
   lexical source or enum-to-English mapping.
5. Split manifests, exclusion counts, duplicate checks, source-group overlaps,
   and output hashes. Keep wall-clock timestamps outside deterministic content.

Freeze train/dev/test before generating teacher traces. For an unseen-lexeme
benchmark, group related roots/stems across all four families. If the intended
test instead holds out grammatical combinations on familiar bases, declare
that explicitly. Audit inherited traces and old benchmark tasks against the
new test requests before reusing them. Deterministic engine labels still need
spot checks for linguistic validity.

## 4. Harbor packaging and the tool-free evaluation contract

A Harbor dataset collects task directories. Each task combines a rendered
instruction, environment configuration, and verifier; a trial is one attempt.
Our proposed task layout below follows the
[official task format](https://docs.harborframework.com/tasks/overview):

```text
data/datasets/tinanta/test/<task-id>/
  instruction.md          # fully rendered vp_tinanta.txt; no answer key
  task.toml               # task metadata and resource/time limits
  environment/Dockerfile # minimal, pinned runtime
  tests/test.sh           # verifier entrypoint
  tests/task.json         # canonical request + complete accepted answer set
  tests/verify.py         # packaged shared scorer
  solution/solve.sh       # reference answer for oracle smoke checks
```

Use the same layout for the other three families. The shown task files are a
design, not files created by this branch setup. Tasks should be self-contained;
a container must not need an absolute path to the developer's checkout. Package
the verifier at generation time and keep its version/hash in the manifest.
See [local datasets](https://docs.harborframework.com/datasets/datasets).

The verifier should read the saved model response and write a binary number
to `/logs/verifier/reward.txt`. Keep detailed parsing/correctness diagnostics in
a separate JSON artifact. With Harbor's standard shared environment, `tests/`
is uploaded after the attempt. Keep gold and oracle solutions out of the
agent image. If selecting a separate verifier environment, explicitly arrange
transfer of the saved response. See the
[verifier contract](https://docs.harborframework.com/tasks/verifier).

**Our intended model evaluation remains one prompt and one completion, with no
model tools or internet search.** Harbor packaging does not establish this by
itself. Implement a [custom external agent](https://docs.harborframework.com/agents/custom-agents)
that sends only the rendered instruction to the model, supplies no tools,
records the response/usage, and writes the raw final response to an agreed
artifact such as `/app/answer.txt` for grading. That file write is harness work;
the model should not be asked to use a terminal. Keep any provider reasoning
channel separate from final answer text and record the reasoning setting.

Pin Harbor and validate the chosen task schema before generating the first
release. This branch does not yet have a dependency manifest or custom Harbor agent. The reviewed docs are linked above (reviewed 2026-10-10);
they may evolve independently of this repository.

Once implemented, the planned invocation is of this form; the custom class
below is a placeholder, **not a runnable command today**:

```bash
harbor run -p data/datasets/tinanta/test \
  -a '<module>:<ToolFreeAgent>' -m '<model-id>' -k 4 \
  -o runs/harbor --job-name '<unique-run-name>'
```

Harbor documents `-k` as attempts per task; concurrency and retries are separate
settings. Save a job config alongside outputs and check the pinned CLI's help.
See [running jobs](https://docs.harborframework.com/jobs/run-a-job).

For four completed trials with `c` correct answers, task-level pass@1 is `c/4`
and pass@4 is `1` if `c > 0`, otherwise `0`. Average over tasks within each
family and report the four families separately. This sampled pass@1 is not a
greedy-decoding score. The general estimator is preserved in the archived
[finetune/evals.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/evals.py): `1 - C(n-c, k) / C(n, k)`.
Infrastructure retries must not become extra best-of attempts. Retain failed
requests and incomplete tasks explicitly; complete their assigned trials or
report incomplete coverage, without silently changing the denominator.

## 5. Archived training implementation to consult

| Archived location | Previous behavior | Rewrite implication |
| --- | --- | --- |
| [finetune/config.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/config.py) | YAML dataclasses; rejects unknown keys; checks dataset paths and selected settings | Add family/split and release-manifest configuration. Existing validation requires legacy VP and Samayik paths even for SFT. |
| [finetune/data.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/data.py) | GRPO requires tiṅanta-specific `dhatu`/`morphology` columns; SFT reads conversational prompt/completion pairs | Introduce a family-dispatched task schema and a Harbor-to-training adapter. |
| [finetune/prompts.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/prompts.py) | Tiṅanta rendering, English glosses, Devanagari conversion, answer extraction | Add one renderer per family and version the shared parser. Existing extraction permits text outside the answer block. |
| [finetune/rewards/vp.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/rewards/vp.py) | Old exact/chrF/chrF++ rewards | Implement a separate v2 binary scorer shared with the Harbor verifier. Preserve the old scorer for reproduction. |
| [finetune/sft.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/sft.py) | TRL + LoRA, completion-only loss; drops overlength examples | Export new verified SFT pairs with per-family length/drop statistics. |
| [finetune/grpo.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/grpo.py) | TRL GRPO, vLLM rollouts, registered rewards, checkpoint probes | Replace tiṅanta-only data/eval wiring; preserve rollout synchronization and truncation handling. |
| [finetune/sdpo/](https://github.com/anish-lakkapragada/sanskrit-rlvr/tree/e94499639cf58a6518aa99139fab6818e93346d1/finetune/sdpo/) | Self-distillation with privileged teacher context and KL loss | Optional experimental path; teacher-only fields must stay out of student/test prompts. |
| [finetune/model.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/model.py) | HF model loading, bf16/optional 4-bit, LoRA attention/MLP targets | Reuse after checking the chosen model and tokenizer revision. |
| [finetune/evals.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/evals.py), [callbacks.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/finetune/callbacks.py) | pass@k, generation samples, reward history, checkpoint callbacks, translation probes | Add per-family aggregation and explicit error/coverage reporting. |

On the previous branch, the training modules accept `--config <yaml>`. SFT additionally supports
`--merge`; GRPO supports `--resume`. Their `--dry-run` paths create a run
directory, and may load a tokenizer if its dependencies are installed. They
are not pure validation functions. `--force` deletes an existing run directory;
use a new run name for a new experiment.

In the archived code, `RunConfig.run_dir` is `runs/<run_name>/`. Outputs include a frozen `config.yml`
with `_resolved` model/prompt/git/argv metadata, TensorBoard events, checkpoint
directories, evaluation metrics and samples, and a final `adapter/`. SFT can
also save `merged/`. Extend provenance to include full commit, dirty state,
source/prompt/parser hashes, dependency lock, base-model revision, and parent
adapter identity; the legacy constant `PROMPT_VERSION = 1` is insufficient.

### Prompt and reward mismatch to fix before v2 training

[vp_tinanta.txt](data/engine/prompts/v2/vp_tinanta.txt) asks for exactly one Devanagari form
inside `<answer>...</answer>` and no other text. The old `vp_exact` gives
`0.15 * format + 0.85 * correctness`, where format requires both `<thinking>`
and `<answer>`. Thus a correct answer-only response gets 0.85, while an old
reasoning-formatted response gets 1.0. A threshold of 0.85 counts either as
content-correct, but training incentives conflict with v2.

For the new benchmark, define one strict v2 parser: one nonempty answer block,
one form, no surrounding prose; normalize Unicode NFC and boundary whitespace;
accept any member of the complete gold set. Report formatting errors separately.
Use the same binary success predicate for SFT filtering, GRPO correctness,
Harbor verification, and pass@k. Keep any experimental shaped training reward
separate from evaluation. Do not strip meaningful Sanskrit marks or silently
add transliteration schemes to an answer-only Devanagari contract.

The archived Qwen SFT, GRPO rendering, and generation probes explicitly use
`enable_thinking=False` in the chat template. This suppresses Qwen's native
reasoning channel; it does not remove literal `<thinking>` tags in old targets.
SFT consumes the stored prompt text, so changing `sft.prompt_template` only
changes probe rendering/provenance, not the archived training pairs. Verify
identical rendering in training, evaluation, and serving when migrating.

## 6. Existing recipes and checkpoint lineage

These are historical configurations to inspect, not approved hyperparameters
for the new four-family benchmark:

| Recipe | Config | Main settings |
| --- | --- | --- |
| Original Opus R1 SFT | [r1/sft-qwen3-4b-opus-r1.yml](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/configs/r1/sft-qwen3-4b-opus-r1.yml) | Qwen/Qwen3-4B; LoRA r32/alpha64; LR 2e-4; 2 epochs; effective single-GPU batch 16; max sequence 4,096; v1 traces |
| 20M-token mixture SFT | [mixture-samayik-67.yml](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/configs/sft-data-mixture/token-budget-20m/mixture-samayik-67.yml) | 67% translation / 33% morphology by tokens; one epoch; r64/alpha128; LR 2e-4; batch 16; max sequence 4,096 |
| GRPO-r3 | [grpo-vp-exact-mixture-samayik-67.yml](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/configs/sft-data-mixture/token-budget-20m/grpo-vp-exact-mixture-samayik-67.yml) | Merged mixture SFT parent; 731 steps; 8 rollouts per prompt; LR 5e-5; beta .04; r64/alpha128; 4,096 completion cap; 8,192 context |
| Optional SDPO | [sdpo-opus-r1.yml](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/configs/sdpo-opus-r1.yml), [sdpo-upsample-2.yml](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/configs/sdpo-upsample-2.yml) | Privileged-context self-distillation; read `finetune/sdpo/` before adapting |

GRPO-r3 used eight workers with per-device batch 4 and accumulation 2:
64 rollouts = eight groups of eight per optimizer step. Preserve valid batch
divisibility when changing world size. Its RL prompt pool contains 5,844 tasks;
174 morphology validation tasks were removed from the original 6,018.

Checkpoint paths used by the previous campaign were
`runs-final/sft-qwen3-4b-tb20m-samayik67/adapter/` and
`runs-final/grpo-r3-final/adapter/`. GRPO-r3's adapter belongs on its **merged
SFT parent**, not directly on stock Qwen3-4B. Checkpoint weights and large
generated mixtures were ignored by Git; they are not supplied by this branch
or a fresh clone. Local copies were moved outside this checkout during cleanup.
To reproduce the old campaign in its separate checkout, rebuild mixtures using [make_data_mixture.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/misc/data/make_data_mixture.py)
and inspect [make_grpo_prompts.py](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/misc/data/make_grpo_prompts.py) for the RL
pool. Keep training model directories separate from evaluation model copies.

The future run configuration must explicitly freeze model/parent revisions,
dataset release and split hashes, family sampling weights, prompt/parser
versions, LoRA settings, batch/world size, optimizer/schedule, seed, evaluation
cadence, output path, and decoding parameters. Store per-family metrics so a
large nominal pool cannot hide regressions on smaller families. Select models
using dev results; reserve test for final comparisons.

Record the completion-token cap separately from SFT total sequence length and
model context length. Historical limits above include long reasoning traces;
they are not a chosen limit for the current thinking-plus-answer benchmark. Measure
token lengths, set an explicit cap, and log truncation rates before the next
run. Evaluation uses four trials per task; GRPO group size can independently
remain eight. Freeze temperature, top-p/top-k, seed behavior, and reasoning
settings when comparing models.

## 7. Build the new implementation after the benchmarks

There is no training package, run configuration, `pyproject.toml`, or lockfile
in this branch. The standalone [tiṅanta scripts](data/engine/tinanta/README.md)
pin their own dependency through inline uv metadata and are runnable now:

```bash
uv run --python 3.11 data/engine/tinanta/generate.py --output /tmp/tinanta-rebuild
uv run --python 3.11 data/engine/tinanta/verify.py --rederive
```

Create the new training environment and code after
settling the task definitions. The archived [pyproject.toml](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/pyproject.toml)
and [uv.lock](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/uv.lock) document the previous stack: CPU utilities plus a
`train` extra with PyTorch, Transformers, TRL, PEFT, Accelerate, bitsandbytes,
and vLLM. Choose and pin dependencies for the new integration rather than
assuming the previous GPU environment remains suitable. Pin Harbor as well.

For reference, these lightweight checks belong to the **previous branch** and
must run from its separate checkout with its dependencies installed:

```bash
python -m finetune.rewards.vp
python -m finetune.evals
```

They validate the archived reward/evaluation behavior only. They are not
commands available in this new scaffold. Before training, implement and check:

1. A canonical four-family task schema; validated stem/root loading; reviewed
   suffix/coordinate scopes; deterministic builders with independent splits.
2. Three new prompt templates alongside the preserved tiṅanta template. Render
   every requested field from actual engine inputs, with understandable glosses.
3. A shared v2 parser/scorer; rejection tests for wrong, malformed, repeated,
   multiple-form, and truncated answers; acceptance of all valid gold variants.
4. Harbor export plus the tool-free model adapter. Run reference/oracle tasks
   to success and deliberately wrong/no-answer responses to zero. Confirm that
   the model request contains neither tools nor gold answers.
5. Training exports: SFT conversational pairs and GRPO prompt/task records.
   Retain IDs and provenance without leaking gold into rendered prompts. Align
   all family renderers, trainer rewards, and checkpoint evaluations.
6. A small GPU smoke run and four-trial evaluation, then a frozen full run
   configuration. Save raw outputs, finish reasons, token counts, per-trial
   rewards, per-family pass@1/pass@4, coverage, and a readable summary.

The next work is to settle and build the task definitions and Harbor datasets,
then implement the new training pipeline against those artifacts using the
archived code and configurations as references.
