# Isolated 5D pilot 02

The fresh development panel contains **120 new input tuples from 120 families**, with 103 families absent from pilot 01. It passed the hardened shared validator and eight direct source controls. It is ready for coordinator evaluation, not a completed benchmark. The task file and recipe weights are frozen.

## The two executable panels

`pilot-01.audited-pair.tasks.json` contains 119 unchanged original tasks. The complete ID/reason map in `pilot-01.audited-pair.manifest.json` applies adopted exclusions to every original question without consulting correctness. Only 01.1136, a passive periphrastic future with the combined 6.4.62/6.4.92 context, is removed. The retained objects, prompts and gold are unchanged. The original Opus scores remain 98/115 completed and 98/120 requests; the audit-derived subset is separately 98/114 completed (85.96%), with five refusals among 119 requests. The pairing request is `pilot-01.audited-pair.experiment-request.json`.

`pilot-02.tasks.json` is the fresh 120-question panel. Its plan was frozen at **2026-10-07T05:44:21.413221+00:00**, before generating membership or seeing any pilot-02 model answers. `pilot-02.experiment-request.json` requests Opus 5.5 xHigh with 16,384 output tokens; paired Astra evaluation uses the same questions. The coordinator owns submissions and the cumulative ledger.

## Fixed menu and distribution

The input is a dictionary dhatu plus lakara, prayoga, purusha, vacana and one recipe value. The recipe applies the listed operations from inner to outer. Prefixes and independent pada choices are absent. Each question asks for one finite form.

| Recipe | Ordered sanadi | Tasks |
|---|---|---:|
| Intensive-luk | `[yaNluk]` | 60 |
| Causative of intensive | `[yaN, Ric]` | 50 |
| Desiderative of causative of intensive | `[yaN, Ric, san]` | 5 |
| Desiderative | `[san]` | 5 |

All ten classical lakaras have 12 tasks. Kartari has 90 and Karmani 30; passive tasks occur only in causal recipes and the six previously reviewed lakaras. Every person and number has 40 tasks, and each person-number pair has 13 or 14. Gana counts remain Bhvadi 48, Adadi 10, Juhotyadi 5, Divadi 12, Svadi 8, Tudadi 16, Rudhadi 6, Tanadi 2, Kryadi 8 and Curadi 5. The Curadi questions necessarily occupy the simple desiderative control, so recipe/class interactions are not separately identifiable from this panel.

The two main groups were chosen from the earlier development evidence. Under the audited Opus group estimates, this mixture gives an approximately 81.00% weighted heuristic. Its naive component sampling SE is 5.59 percentage points, before accounting for selection, changed voice/class composition, refusals or reference-model differences. This is a hypothesis for fresh calibration, not a strongest-reference prediction. The menu deliberately concentrates on two related but different derivations; maximum recipe share is 50%, while tense and root-class diversity remain broad.

Membership uses the frozen seed, grammatical filters and input novelty. Previous question signatures and source-control tuples are excluded. Families absent from pilot 01 are preferred, but rare classes require reuse across panels: pilot 01 already used both development Tanadi families. There is no repeated family within pilot 02 and no filtering by an individual model answer.

## Scope and source checks

Both panels use the shared `entry_scope_issue` and `oracle_issue` checks. These exclude hidden dictionary prefixes/sanadi, ambiguous visible dictionary identities, the uncertified 6.4.123 semantic condition, the two dictionary-mismatch aorist entries, incomplete Cinvat/mit passive-future variants and the previously unresolved nested rule interactions. Intensive lexical constraints and the maximum of 64 gold variants remain active; the actual fresh panel has at most nine variants per question.

The three outstanding jF/JF/lih vowel objections were reviewed with explicit traditional rules and component evidence. Their original keys are retained. Rule 1.1.4 strengthens the lih non-guṇa analysis; 7.1.100, 6.4.49/48 and 8.2.77 explain the short-i nested jF/JF forms. A printed jF derivative paradigm corroborates the present/nonpresent alternation. These narrow feature reviews are complete, while the entire uncommon nested finite forms remain labeled as rule composition rather than directly printed examples. See [the source review](pilot-02.nested-source-review.md) and its JSON records.

Eight direct source controls passed under the current adapter; they cover the recipe shapes and supporting passive construction. They check membership of documented forms, not exhaustive correctness of every engine alternative. Source controls are separate from paid membership. The known optional Cinvat-vowel gap is quarantined, not repaired.

## Transport and scale

Class reweighting of the old audited Opus panel to the earlier release-class proposal changes its marginal estimate from 85.96% to about 86.88%, a rise of 0.92 points. Sparse cells, recipe/class confounding and the changed pilot-02 recipe weights prevent using this as a release prediction. Full figures and limitations are in `pilot-02.class-transport-sensitivity.json`.

The earlier 1,601-task feasibility proposal used different recipe weights. Pilot 02 has only 5/120 non-intensive questions. Even the earlier optimistic ceiling of 719 intensive-eligible test families permits at most 1,438 intensive questions with a two-question family cap; adding approximately 67 non-intensive questions yields an upper bound of **1,505**, below 1,601. A later release must evaluate a higher family cap or more non-intensive weight. The previous 51.7% Bhvadi / 12.7% Curadi class mix also cannot be copied directly when only about 4.2% of tasks can use Curadi. No new release allocation is fixed here.

The 120-question panel remains a pilot, with about 3.65-point independent SE at 80%. The strongest-reference target, final sample-size/cluster uncertainty, frozen release membership and RL-training examples remain outstanding. `benchmark_ready` stays false.

## Handoff artifacts

The paired subset and fresh panel each have an executable experiment request, manifest and shared runner audit. Pilot 02 additionally has the frozen plan, rendered prompts, source checks, nested source review and class-transport sensitivity. `pilot-preparation-02.integrity-audit.json` verifies hashes and cross-artifact consistency. The worker made no paid calls, changed no shared code or ledger, and inspected no held-out model answers.
