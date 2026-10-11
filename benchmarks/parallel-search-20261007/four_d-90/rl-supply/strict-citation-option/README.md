# Prospective RL option with no exact-citation overlap

**A stricter training pool is feasible without losing any of the nine short-adanta or fifteen other-adanta families.** This option excludes every eligible RL entry whose exact raw dictionary citation appears anywhere in the master development or test inventory, ignoring class. It checks all 1,571 distinct development/test citations, not just the proposed final questions.

The original RL audit, inventory and 1,400-question manifest remain byte-unchanged. No split is reassigned and no test question changes. This is an additional prospective training option, not an executed training run.

| Component | Remaining families | Remaining public tuples | Change from original RL pool |
|---|---:|---:|---:|
| Short-adanta, non-Lun | 9 | 729 | None |
| Other-adanta, Lun | 15 | 135 | None |
| Broad non-Curadi | 308 | 28,170 | −37 families; −3,420 questions |
| Total | **332** | **29,034** | All removal is in the broad component |

The removed 37 families have 36 raw citations, because one citation occurs in two RL classes. [excluded-family-audit.json](excluded-family-audit.json) lists every removed family and its master development/test match. Remaining distinct family-coordinate capacity is 28,584; meaning-distinct public questions explain the additional 450 tuples.

The separate [curriculum](curriculum-1400-metadata.json) still contains **728/112/560 questions**, arranged as 56 blocks of 13/2/10. It reuses the original deterministic input-only algorithm and seed on the restricted pool, preserves all remaining families, covers all ten classes and ten tenses, and has no question repetition. All 1,400 selected questions were regenerated and source-filtered using the same policy as the original pool. There are **332 families**, maximum load **81**, and family-load sum of squares **60,792**. Short-family loads remain 80–81, other-aorist loads 7–8, and broad loads 1–2. Persons and numbers are balanced 466/467/467 overall.

Both the full remaining inventory and this curriculum have **zero exact raw-citation overlap with any master development/test entry**, as well as zero overlap under the declared citation-plus-class family key. This closes that specific cross-class diagnostic. It does not merge different marker/accent spellings, synonymous roots, shared stems or related meanings, and cannot establish that a pretrained model has never encountered these lexemes.

The tradeoff is loss of 37 broad training families and a changed broad-class mix. The nine-family short-stem bottleneck is unchanged; additional persons, numbers or replayed epochs do not add families. No learning-effect, difficulty or precision claim follows from these counts.

For a future fresh learner, this stricter option provides the clearer train/evaluation citation separation while retaining the full intended hard-cell supply. It is still metadata only: export must recheck master split/citation hashes, regenerate every prompt and full answer union, separate public prompts from private keys, and apply a consistent accepted-spelling policy. All source-certification and checkpoint-provenance limitations in the original audit remain in force. No gold export, training, API call, ledger change or model-output read occurred.

The [manifest](curriculum-manifest.json) pins the strict files, original manifest, master split and source dependencies. The [supply audit](supply-audit.json) records capacities, exclusions, exact-citation guards and unchanged original-file hashes.
