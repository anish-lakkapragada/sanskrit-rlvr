# Separate exact-answer source layer

This offline tool applies the exact **19-form union** adopted in `source-adjudication-adoption-02.json`. It makes no provider calls, reads or writes no credentials, and writes no ledger, task, original result, scorer, or execution file. Preparation used synthetic answers only.

Before loading real result rows, `score.py` checks its pinned code/dependencies, the original input manifest, current all-attempted accounting through the reviewed carry guard, and the completed additive primary-analysis metadata. It then reads only the first seven scalar fields of the independent mechanical review and refuses unless that review passed for 1,800 questions per provider, 3,599 real receipts and the exact missing index 837. The full review must bind the primary analysis and every canonical/finite result fingerprint. A failed or absent review cannot unlock answer access. The original coordinator lock prevents concurrent accounting/execution changes during the read.

The tool retains every question, result order, raw status, extraction, usage, receipt and denominator. Only a separate copy's correctness field can change from false to true for an exact adopted task/answer match. NFC normalization and surrounding-space stripping match the existing contract; no morphological, vowel, puK-insertion or spelling closure is introduced. The source layer preserves any existing unscored value, including Astra index 837. A recognized final answer in a truncated response follows the existing all-request scoring convention, while the response remains nonusable in usable-answer statistics.

Outputs are written once under `completed-<source-policy-digest>/`: source-adjusted rows, each provider's remaining source-review queue, and an analysis containing exact changes/evidence. Canonical and frozen spelling files stay at their original paths and hashes. The same frozen `describe`, paired comparison, seeds/bootstrap counts, and both infrastructure imputations are used. IID and family SE are separately reported. Unrecognized usable answers remain pending, never certified errors merely by this tool. Pending-source bounds cover flagged answers and nonusable questions; they do not bound undetected oracle errors in accepted keys. Readiness and original complete-response qualification remain false.

Run only after independent code review:

```sh
.venv/bin/python benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/astra-infrastructure-carry-01/source-adjusted/score.py --score
```

Synthetic checks (no real result reads):

```sh
.venv/bin/python benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/astra-infrastructure-carry-01/source-adjusted/test_score.py
```

For later additive source decisions, use `--extension-manifest PATH`. Do not edit this frozen tool, its base adoption, or prior outputs. The extension manifest must have schema `reviewed-source-extensions-v1`, the exact tool-manifest SHA, execution-plan SHA, candidate-task SHA, and a `dispositions` array. Each entry contains `path`, `sha256`, `review_path`, and `review_sha256`.

Each disposition document must have schema `exact-task-source-dispositions-v1`, status `adopted`, the exact execution-plan and candidate-task SHAs, `symmetric_across_providers: true`, and nonempty `source_dependencies` mapping evidence paths to hashes. Its independently reviewed JSON must contain `passed: true`, `dispositions_sha256`, `execution_plan_sha256`, and `candidate_tasks_sha256`. Every source dependency, decision and independent review is checked before scoring and again before output publication.

Supported disposition lists are `accepted_additions` (using `additional_forms_devanagari`), `rejected_answers`, and `unresolved_answers` (both using `forms_devanagari`). Every item must include exact `task_id`, `dhatu`, `morphology`, and `prompt_sha256`. Dispositions contain finite lists of single-word answers, never model/provider conditions, wildcards or filtering predicates. A later accepted/rejected decision can resolve an earlier unresolved label. Accepted/rejected contradictions fail. Rejection cannot silently revoke an already accepted canonical/finite form; that would require a separate explicit oracle/scoring revision. A rejected answer stays in the panel with its existing false grade and a source-supported disposition. Unlisted answers stay pending. Apply a cumulative extension manifest to include all desired previously reviewed decisions.

The source policy is symmetric across providers and applies irrespective of a prior grade. It does not remove tasks, change the fixed mixture, invent a response to index 837, settle its unknown cost, or waive a precision gate. No broader root, tense, pada or variant union is implied by these 19 forms.
