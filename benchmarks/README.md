# Morphology benchmark tasks

[full-tasks.json](full-tasks.json) contains all **6,687 unique tasks** from:

- `data/finetune/task-data/finetune.json`: 6,018 tasks.
- `data/finetune/task-data/validation.json`: 669 tasks.

The file is a JSON array containing the finetune tasks followed by the validation
tasks, preserving source order and every original field, including the root,
morphology, and accepted gold answers. It assigns no difficulty labels.

Earlier subsets, results, frequency analyses, figures, and their original
documentation are preserved in [archive/](archive/README.md). The archived
`manifest.json` contains task IDs and split/difficulty metadata, not full task
objects. Archived scripts and reproduction commands retain their historical paths.

## Interactive performance study

Open [report.html](report.html) in a browser. It includes all seven current
model/effort configurations and the archived GRPO/SFT checkpoints, with task-pool
filters, root-bootstrap intervals, task-option and interaction comparisons,
historical cost estimates, an answer explorer, and benchmark redesign suggestions.
The report highlights prompt differences, training-pool overlap, and answer-key
audit candidates. All data is embedded, so the HTML also works offline.

The [Moving forward section](report.html#moving-forward) tracks an **active iterative goal**:
create VP-Bench and VP-Bench-Hard with 1,000 unique tasks each (minimum 500),
scoring **strictly below 70% and 50% respectively on each reference model**.
Cumulative caps across all attempts are **$1,000 Anthropic / $2,000 OpenAI**.
The original primary-conjugation search scored 95.83% on Opus and cost $23.072126;
that unsuccessful experiment is preserved in the expandable iteration archive.

The [revised plan](iterative-goal-20261006/plan.json) expands to generated causatives,
desideratives, intensives and ordered compositions with prefixes. Most experiments
retain one-form creation answers; a separately scored two/four-form paradigm pilot
tests consistency across tenses. Both models receive xHigh and 16,384 output tokens. The initial 400-task pilot exposed substantial Opus classifier refusals. A paired
prompt diagnostic recovered 31/32 completions. Subsequent pilots test tense
interactions, specified ending sets and prefixes; the report and ledger contain
the current results. The broad 480-task pilot was too easy on both models. The
paradigm pilot did not meet Hard among completed Opus answers: almost all errors
affected the shared stem and therefore every requested form. A fresh 300-task
benedictive calibration also missed Hard (55% overall on Opus). A 120-task contrast
pilot was dominated by Opus refusals (93/120). A 320-task one-form nominal-derivative
pilot scored 235/320 (73.4%), also missing Hard. Six independent reference checks
and all regenerated task keys passed. New versioned multi-form prompts explicitly
say “Sanskrit verbal root (dhatu)” and gloss the grammatical terms throughout,
following `prompts/v2/vp_task_eval.txt`. Complete-panel paired Opus comparisons reran all 120 contrast and 160 paradigm
tasks; refusals persisted. Word-only and line-format probes also failed to restore
completion. A minimal extension of the established single-form template recovered
57/64 usable completions, with 32 correct. This repeated diagnostic is not fresh
calibration and does not establish Hard. Repeated questions do not add unique tasks.

Astra has now completed the corrected aorist calibration (334/500; 334/413 among
completed answers, with 87 truncations) and the deeper single-word pilot (159/200;
159/191 completed). Neither establishes Hard. A new compound-creation pilot uses
two/four independent verbal derivatives and returns one inflected dvandva. Its
initial 64-task prompt was dominated by refusals; a 32-task field-template
comparison also failed to restore completion. The pinned Rust compound oracle and its scope are documented
in `iterative-goal-20261006/samasa-grammar-review-01.json`.

At the October 6, 9 PM Pacific checkpoint, **neither final benchmark is qualified**.
The conservative single-form Bench candidate contains 279 development questions:
Opus scores 182/264 completed answers (68.94%), and Astra 166/238 (69.75%).
These estimates have insufficient margin, with 15 and 41 incomplete answers.
The requested standard error below one percentage point remains unmet.

Independent-dhatu two/four-form sets and lexical uṇādi stems also failed to
establish the targets. Sanskrit-language direct diagnostics returned no refusals:
27/32 correct for uṇādi and 25/32 for finite sets (25/29 completed; three truncated).
Both language and transport changed from the original Batch pilots, so this does
not isolate the cause of improved completion. Repeated diagnostics add no unique tasks.

A fresh **64-question passive-voice pilot** is submitted to Opus. It uses two
derived-stem constructions, present and non-present tenses, and explicit middle
endings. All questions regenerate; four elementary independent reference examples
match. Aorists and unresolved rule contexts are excluded. Larger compositions
still require error adjudication. See `passive-grammar-review-01.json`.

Settled cumulative cost is **$140.82 Anthropic / $589.16 OpenAI**. The pending
passive pilot reserves at most another **$10.68 Anthropic**. These totals include
historical work; caps remain $1,000/$2,000. The report reads the live ledger.

All active candidates remain creation/construct tasks sampled from valid Cartesian
feature combinations. No modification or correction tasks have been submitted.
The [checkpoint](iterative-goal-20261006/checkpoint.json) records the 9 PM Pacific
status with actual artifacts, scores, uncertainty, costs and remaining gaps.

Two possible nested-derivation oracle edge cases are recorded in
`iterative-goal-20261006/nested-oracle-review-02.json`; they remain open and must
be resolved or excluded before final certification.
Neither final
benchmark is yet created.
The new `misc/vp_goal.py` runner carries forward historical spending, reserves the
maximum before each paid request, protects both final evaluations and sensitivity
checks, and releases savings only after complete usage reconciliation. The
[cumulative ledger](iterative-goal-20261006/ledger.json) is authoritative for this goal.
A failed pilot changes the next experiment; it does not end the broader goal.

A provisional [1,000-task RL seed export](iterative-goal-20261006/rl-seed-candidate-02.jsonl)
uses 326 reserved training families, with no overlap under the declared
exact-citation-plus-gana family split. It contains the current candidate
constructions, not certified benchmark tiers. Each row includes complete
`messages` and `prompt` fields plus separate gold fields for the reward function.
**Use the exported prompts directly:** the legacy root-only VP training renderer
omits the new suffix, prefix and ending-set requirements. Gold fields must not
be included in the model input. No training has been launched. The first export was withdrawn after an SLP1 prefix-encoding error; the replacement requires reviewed prefix spellings.

`misc/vp_goal_dataset.py` exports audited panels and exposes `task_reward(completion,
task)`, a binary reward matching the task's evaluation metric. `exact_reward` remains
available for one-form tasks. Paradigm tasks require a JSON object with every
specified row correct; per-form diagnostics are reported separately. Neither
requires a thinking block. To score a JSONL completion file containing exactly
one `{ "id": ..., "completion": ... }` row per task:

```sh
.venv/bin/python misc/vp_goal_dataset.py score \
  benchmarks/iterative-goal-20261006/rl-seed-candidate-02.jsonl \
  completions.jsonl scores.json
```

Missing answers must be represented by empty text; missing or duplicate IDs are
rejected. The [export manifest](iterative-goal-20261006/rl-seed-candidate-02.manifest.json)
records dependency hashes, split checks and reproducibility limits. Existing
checkpoints are not certified clean against this split.

The report explains construction selection, reserved root families, validation and
why N=1,000 alone cannot promise standard error below one percentage point.
Historical data and the [first campaign](creation-campaign-20261006/README.md) remain
unchanged. Refresh the execution snapshot without model calls with
` .venv/bin/python misc/vp_campaign_watch.py --refresh-only`.

Regenerate without model calls:

```sh
.venv/bin/python misc/build_benchmark_report.py
```

The builder re-extracts and verifies all 46,809 current answers against the
recorded gold sets. Supporting JSON and CSV files are written to
[analysis/performance-study/](analysis/performance-study/). The page template is
`misc/benchmark_report.template.html`. Raw results and benchmark membership are
not changed by this analysis.
The moving-forward analysis in `misc/benchmark_forward.py` also regenerates VP
histories locally and verifies their gold sets before measuring derivation length.
