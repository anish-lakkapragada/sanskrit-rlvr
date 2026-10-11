# VP benchmark search: parallel 4D and 5D tracks

Date: **2026-10-07, America/Los_Angeles**. Objective established on 2026-10-06; research is continuing.

## User objective and task contract

Create two diverse Sanskrit verb-construction benchmarks with **79–81% accuracy on the strongest tested reference model**. Opus 5.5 is the primary reference; GPT-6 Astra is the second. This replaces the earlier below-70% / below-50% designs. The score target is distinct from a confidence interval.

1. **4D:** a dictionary dhatu plus lakara (tense/mood), prayoga (voice), purusha (person), and vacana (number).
2. **5D:** the same input plus one value from a finite menu of ordered Sanadi recipes, implemented through Vidyut-Prakriya `Dhatu.with_sanadi(...)`. A menu value may contain a sequence of operations.

Every question supplies a complete tuple and requests **one accepted Devanagari finite form**. Accept the audited union of grammatical variants. No prefix choices, independently specified pada, synthetic roots, nominal outputs, answer bundles, or hidden extra coordinates. Apply grammatical applicability filters; an arbitrary Cartesian tuple need not be valid Sanskrit.

Minimum **500 unique tasks per benchmark**, preferably **1,000 or more**, with a separate training split. The user's request for standard error below one percentage point remains a real constraint: 1,000 tasks do not automatically suffice. At 80% accuracy, independent Bernoulli sampling requires at least 1,601 tasks; near 79%, at least 1,660. Shared-dhatu dependence can require more. Report unique tasks, family counts, iid SE, family sandwich SE and family bootstrap intervals. The declared final gate requires iid and unstratified family SE **below 0.01** for both all-request and usable-answer scores on both references. These are sampling-uncertainty estimates, not a measured repeated-run standard deviation. Do not select a smaller estimator simply to pass.

## Diversity, selection and splits

The original **6,687 tasks are not the search boundary**. Generate fresh valid tuples and explore new grammatical distributions. Promote diversity across dhatus, classes, tenses, voices and person/number; avoid concentrating everything in aorist or one obscure construction. Publish all concentrations.

Use development evidence to choose grammatical distributions. Freeze new evaluation membership before reading its model answers. Do not select final questions because those exact questions were answered incorrectly. Preserve raw results and apply source-based exclusions equally to successes and failures.

The master split has **700 development / 1,000 reserved-test / 462 RL-training families**. Family means exact dictionary citation including markers, plus gana; it is not an etymological grouping. The split file explicitly records legacy analysis of all dictionary families before the split existed. Current fitting excludes reserved-family legacy records and uses fresh 5D tuples, but this is **not a historically untouched lexical holdout**. Existing model pretraining and old RL checkpoints are not certified free of exposure.

## Current evidence

**4D has no qualifying diverse lead.** The fifth pilot scored 43/52 (82.69%) on only 13 development families. Its non-aorist subset reached 31/39 (79.49%), but the corresponding test supply covers only 14 families. A broader input-feature search with family-disjoint development validation rediscovered the same narrow mechanism and found no useful residual predictor. This is evidence against the current approaches, not proof that every possible 4D design must fail. [Current 4D evidence](parallel-search-20261006/four_d/current.md).

The sixth 4D probe has now finished: **Opus scored 96/96**, comprising **48/48 first-person imperatives and 48/48 same-dhatu controls**, across six athematic classes. All answers were usable; there were no aorist questions. Actual cost was **$0.382422** against a $63.20256 maximum reservation. The [independent source review](parallel-search-20261006/four_d/pilot-06-independent-review/review.md), full regeneration and [predeclared complete-panel analysis](parallel-search-20261006/four_d/coverage-05/pilot-06.analysis.json) are preserved. This closes the imperative lead under its discovery rule. Zero empirical bootstrap spread in an all-success sample does not establish zero uncertainty: each 48-question role has a Wilson 95% interval of approximately **92.59–100%**. Its 156 corresponding test targets across 78 families also cannot supply a standalone benchmark.

The seventh 4D screen has also completed: **46/46 correct and usable**, one passive ciṇ aorist per family across eight classes. Its fixed distributed-error trigger fails, so this lead is closed. Actual cost was **$0.191616**. The nominal Wilson 95% interval is **92.29–100%**; zero empirical variance is not zero uncertainty. [Complete fixed-panel analysis](parallel-search-20261006/four_d/coverage-gap-06/cin-analysis.json). The separate broader 96-family, eight-tense screen remains in progress.

**The larger 5D confirmation failed its advancement screen.** The immutable full pilot07 result is **1,854/2,400 overall (77.25%)**, or **1,854/2,381 usable (77.87%)**, across 606 development families. It contains 16 refusals, two truncations and one completed response without a unique parseable answer. Blank refusals do not establish a cyber-related cause. Raw missing-answer bounds are 77.25–78.04%; family SE is 1.092 points. [Frozen aggregate](parallel-search-20261006/five_d/pilot-07/revision-01/aggregate-analysis.json).

The current policy21 source supplement is **1,847/2,381 overall (77.57%)**, **1,847/2,362 usable (78.20%)**, with missing-answer bounds **77.57–78.37%** and all-request family SE **1.062 points**. It still fails the target. Source-based predicates remove 19 questions equally across outcomes: 12 previously wrong intensive forms and seven previously correct forms with unresolved scope or a faulty SAN rule context. The [current supplement](parallel-search-20261006/five_d/pilot-07/revision-01/scope-supplement-policy21.json), earlier [policy19](parallel-search-20261006/five_d/pilot-07/revision-01/scope-supplement-policy19.json) and [policy20](parallel-search-20261006/five_d/pilot-07/revision-01/scope-supplement-policy20.json) audits, and immutable raw aggregate are all retained.

The corresponding [candidate04](parallel-search-20261006/five_d/candidate-4800/revision-04/README.md), with 4,800 tasks and 929 test families, remains unpaid and unevaluated. It will **not advance unchanged**. Policy19 also affects 27 of its inputs. Earlier small pilots near 80% remain historical development evidence; the larger confirmation supersedes their calibration confidence. [Current 5D evidence](parallel-search-20261006/five_d/current.md).

## Current fixed experiment

The coordinator launched a fresh **2,400-question Opus confirmation** and fixed **240-question Astra subset** on 2026-10-07 at approximately 05:28 PT. By 06:55 PT, both Astra stages (240 requests total) have settled and collected; the first 400-question Opus stage is still processing. All eight stages must settle before the aggregate is examined. The frozen revision02 uses:

- 56% intensive → causative; 24% intensive with suffix deletion → causative; 20% desiderative.
- 45% aorist, 55% other tenses, 10% passive, and all ten classes and tenses.
- Curadi quota raised from 80 to 145, offset by Bhvadi 1,600 → 1,535; other class quotas unchanged. This removes an inherited obstacle to covering all eligible families. The policy21 revision covers all 670 eligible development families. Exactly two tuples were repaired after an additional rule-context audit, preserving every grammar margin, family load and allocation objective. Independent membership, novelty, complete regeneration and bounded source checks pass.
- A prospective common **xHigh / 65,536-token** ceiling. Six fixed 400-question Opus payment stages; no interim accuracy stopping or task replacement.
- A fixed, input-selected **240-question Astra subset**, in two 120-question stages, to measure cost/completion and repeated-aorist dependence. It remains paired with the same Opus questions and adds no unique benchmark tasks. Its constrained selection and covariance support must be disclosed.

Current development-based forecasts put the revised mixture near 80%, including class-margin sensitivity; they are not fresh measurements. The two related intensive recipes still occupy 80%, so derivation-type diversity is limited even with broader families and tenses. Final N and membership remain unset. Input-only sizes of 3,000, 3,600, 4,200 and 4,800 questions are feasible, covering 949, 971, 971 and 971 eligible test families respectively. No size is selected; measured development dependence and conditional cost scenarios will inform that decision before final answers. No final evaluation or RL training is authorized by these preparation artifacts.

## Output-limit and validity checks

Historical primary runs used xHigh / 16,384 tokens. Prompts explicitly identify the Sanskrit verbal root; the current version uses Sanskrit instructions after a refusal-enriched wording diagnostic. Wording changes and diagnostic selection are disclosed separately from population accuracy.

The fixed **60-question Astra 128k diagnostic** completed: 44/60 correct with all answers usable, versus 40/60 overall and 40/50 usable at 16k. The paired gain interval is wide (95% bootstrap −6.67 to +20 points). Opus scored 51/60 overall on those questions. Actual cost was **$14.450675**, and the longest output used 20,577 tokens. Policy19 leaves a separate 59-pair supplement: Astra 40/59 → 44/59 overall, with 50 → 59 usable answers. Full60 records remain preserved. [Diagnostic](parallel-search-20261006/five_d/astra-cap-development-01.analysis.json), [source supplement](parallel-search-20261006/five_d/astra-cap-development-01.policy19.json).

The prospective 65,536-token ceiling is four times the old primary limit and over three times the observed maximum. The full 5D 64k calibration remains pending; its partial outcomes stay hidden. The completed 4D pilot06 is separately labeled 64k. The 128k diagnostic is not relabeled as a 64k run. Both confirmation phases share the existing combined 20,000-question/provider allowance. The two sensitivity phases share one 100-question/provider allowance; OpenAI has used 60.

[Oracle policy21](parallel-search-20261006/oracle-policy-21.json) records the current scope. It also excludes single-SAN traces with rule 7.4.7, whose caN condition is incorrectly extended to a desiderative sic aorist; ordinary 4D caN forms remain eligible. It adds a hold on exact Svadi entries 05.0013–05.0015 because primary sources disagree between Vedic and predominantly Vedic classification; classical scope remains unresolved. Their classical homonyms remain eligible. This prospective discovery affected three unpaid pilot08 inputs and prompted regeneration; it is not evidence that the forms are universally ungrammatical. Answer keys require regeneration, complete prompt checks, exact split checks and source review of systematic disagreements. Engine agreement alone is not independent Sanskrit certification. Source uncertainty is not used as an artificial source of difficulty.

## Shared spending caps and execution

The two workers share lifetime caps of **$1,000 Anthropic / $2,000 OpenAI**, including all earlier work. They do not each receive a separate allowance.

At the 2026-10-07 06:55 PT checkpoint, settled lifetime usage is **$246.577190 Anthropic / $780.255070 OpenAI**. Anthropic has a **$263.344** outstanding maximum reservation for the first pilot08 stage; OpenAI has none. The completed 240-question Astra calibration cost $52.776920. Later fixed Opus stages are still unsubmitted, so this checkpoint is not their total eventual cost. The live [ledger](iterative-goal-20261006/ledger.json) governs further calls. An explicit internal reallocation released the unused Anthropic 4D core reserve ($166.84); protected planning reserves are now $295.14 Anthropic / $962.50 OpenAI under the existing final protocols. No provider cap or task allowance increased.

Only the coordinator submits paid requests. Each submission reserves its maximum possible charge under the shared filesystem lock. Unknown paid submissions retain their reservation and are never replayed automatically. Fixed membership cannot be shortened when a favorable score appears. If financial or external failures prevent completion, report an incomplete evaluation. Expected cost is not guaranteed funding.

The requested workers are **GPT-6 Astra, xHigh**: `vp_4d_overnight` and `vp_5d_overnight`. Workers prepare and independently review artifacts; they do not submit provider generations or edit shared accounting. Codex API-key login is prohibited in this repository; built-in workers use the session's account. Evaluation SDK calls remain within the authorized provider budgets.

## Monitoring and deliverables

- [Live dashboard](http://127.0.0.1:54974/) and [report](report.html#moving-forward).
- Per-track `current.md`, `status.json` and `progress.md` inside [the search directory](parallel-search-20261006/plan.json).
- [Coordinator log](parallel-search-20261006/coordinator-progress.md), immutable task/plan manifests, raw results, source reviews and cost records.
- The monitor plays the requested local completion chime when a worker run finishes. A completed research phase does not mean the benchmark is qualified.

Release partitioning, exact-answer export/reward and family-aware analysis tooling are prepared and tested. There is **no qualified final benchmark, no final training dataset and no RL run yet**. A finite benchmark cannot be guaranteed unsaturable; the generator and reserved training split support subsequent learning experiments.

## Latest continuation — 2026-10-07, 07:22 PDT

The reviewed 4D imperative probe is closed at 96/96 correct (48 target/control pairs), costing $0.382422. It supplies no hard component. An unpaid coverage-gap review continues the exact4D search.

For 5D, [input-only size options](parallel-search-20261006/five_d/pilot-08-scale-options-policy21/README.md) establish feasible N=3,000/3,600/4,200/4,800 allocations covering 949/971/971/971 families under the current 56/24/20 recipe mixture, 45% aorist and 10% passive. These are not selected final questions or verified accuracy/precision claims. Final N depends on the complete frozen calibration, before any final answers. The Anthropic runner continues after the Astra runner completed both stages; all eight pilot08 jobs must settle before outcomes are examined. A release-runner prototype is being developed in isolation without changing active dependencies, accounting, reserves or authorization.

The [prompt surface audit](parallel-search-20261006/prompt-surface-audit-20261007.json) reconstructs all 2,736 prepared requests from only public task inputs and verifies that no gold/trace metadata is required or included. A [prospective scale analysis](parallel-search-20261006/five_d/pilot-08-scale-options-policy21/post08-scenarios-predeclaration.json), with seven passing synthetic tests, will compare every N under common moment/covariance sensitivities after the full frozen aggregate exists. No automatic size selection or payment follows it.

The seventh 4D discovery is now submitted: **46 fresh passive third-person singular aorists, one per development family across eight classes**, still exactly dhatu + four coordinates. Its full gold/variant and source checks pass, including [independent review](parallel-search-20261006/four_d/pilot-07-independent-review/review.md). This narrow predicate has only 80 test targets and is not a benchmark by itself. Job `opus-four-d-pilot-07` was accepted at07:20:30PT with a **$30.284560 maximum** reservation. The entire panel must settle before its error-family trigger is evaluated. Its prospective SE correction, seven passing synthetic tests, frozen40dependencies and registration are preserved in [coverage-gap-06](parallel-search-20261006/four_d/coverage-gap-06/experiment-request-07.json). No provider cap or protected reserve changed.

The scale-scenario calculations passed [independent mathematical review](parallel-search-20261006/four_d/post08-scale-review-01/review.md). Their projected SE and cost ranges remain conditional forecasts; cost ranges concern transported expected totals, not guaranteed or predictive bills. Actual final SE and accuracy still require the full fixed evaluation.

## Latest continuation — 2026-10-07, 08:07 PDT

The broad 4D coverage screen is now submitted: **96 fresh questions across 96 families, six classes and eight equally weighted tenses; only 12.5% aorist**. It keeps the original dhatu + four coordinates and all accepted variants. These families are absent from all six completed xHigh panels and the still-processing 46-family ciṇ panel; all have older input exposure. The [coverage rationale](parallel-search-20261006/four_d/ordinary-tail-08/review.md) and [fixed analysis](parallel-search-20261006/four_d/ordinary-tail-08/analysis-predeclaration.json) are preserved. The discovery trigger requires 90 usable answers and wrong completed answers across at least 16 families, three classes and four tenses. It does not assume hardness or qualify a benchmark. Eight synthetic tests and coordinator regeneration/public-input checks pass. Maximum new Anthropic charge: **$63.202560**.

The 5D calibration still has two completed Astra stages; Opus processing continues. Its outcomes remain hidden until all eight stages settle. The two 4D panels have separate complete-panel analyzers and completion chimes. The worker completion sounds for both new reviews were played successfully. No final N, benchmark qualification or RL run is claimed.

An [isolated RL interface review](parallel-search-20261006/five_d/release-contract-review-02/README.md) found legacy prompt/reward incompatibilities and demonstrated a proposed adapter with **12 passing offline checks**, including the actual reward-recorder path and conversational completions. It separates public prompts from private keys, preserves binary full-variant rewards, and enforces the exact ordered recipe menu and master split. Live training files remain unchanged; GRPO and checkpoint evaluation still need integration. The [runtime snapshot](parallel-search-20261006/runtime-20261007-01/README.md) verifies 4,259 critical installed files, including the compiled Vidyut engine.

Settled lifetime usage is **$246.577190 Anthropic / $780.255070 OpenAI**. Pending maximum reservations are **$356.831120 / $0.000000**. Anthropic committed spending plus protected reserves is **$898.548310**, under the unchanged $1,000 cap. OpenAI's cap remains $2,000. All future submissions still pass the locked maximum-cost gate.

## Result update — 2026-10-07, 08:16 PDT

The complete ciṇ screen is **46/46 correct and usable**. [Post-result review](parallel-search-20261006/four_d/coverage-gap-06/result-review.md) reproduces every score and the failed discovery trigger, regenerates all full accepted unions and 50 derivation paths, and verifies the 40 frozen dependencies. No new source issue was found. This lead is closed; the 96-family broad ordinary screen continues.

The first 400-question Opus stage of 5D pilot08 has now settled, joining both Astra stages: **three of eight stages complete**. The next fixed 400-question Opus stage was submitted automatically after settlement. All 5D scores remain hidden until the complete calibration. Settled lifetime spend is **$255.648318 Anthropic / $780.255070 OpenAI**; pending maximum reservations are **$326.546560 / $0** at this checkpoint. Provider caps remain unchanged.
