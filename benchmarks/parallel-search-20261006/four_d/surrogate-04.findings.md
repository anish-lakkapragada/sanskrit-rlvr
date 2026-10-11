# Input-feature surrogate diagnostic: bounded handoff

**No new paid 4D pilot is justified by this diagnostic.** Interpretable rules rank the already-known adanta Curadi questions as harder, but do not establish a broad additional weakness. After source screening, the current xHigh data contain only two errors outside adanta, across two lexical groups. The absence of a supported new rule is not proof that every untested classical 4D construction is easy.

This completed offline phase is `overnight-surrogate-04`, frozen under shared policy14 and rechecked under current policy15. It preserves the preceding [handoff](handoff-05.md), frozen questions, raw results, master splits and source policies. No provider call, shared-code edit or test-answer access occurred.

## Data and separation

The [design](surrogate-04.design.json) was saved before running this feature search. Primary evidence is the five existing Opus xHigh/16,384 development panels. Historical High/4,096 discovery data are a separate lower-fidelity transfer comparison, never pooled as current-reference accuracy evidence.

| Evidence | Completed source-screened questions | Errors | Exact families | Broader lexical groups | Error groups |
|---|---:|---:|---:|---:|---:|
| Current xHigh, all | 535 | 19 | 302 | 279 | 11 |
| Current xHigh, excluding adanta | 417 | 2 | 274 | 251 | 2 |
| Historical High, all (policy15) | 4,140 | 76 | 672 | 606 | 48 |
| Historical High, excluding adanta (policy15) | 3,962 | 60 | 642 | 576 | 41 |

The larger historical sample starts from the older 6,000 development questions. Shared source policy, existing pilot04 precautions, unresolved urja, and the preexisting passive-transitivity screen account for exclusions; unusable answers are not grammatical error labels. [The original policy14 dataset provenance](surrogate-04.dataset.json) and [policy15 eligibility delta](surrogate-04.policy15-validation.json) record the exact counts. Policy15 removes four historical rows for code01.0866, including two disagreements; primary xHigh data are unchanged. A [full offline policy15 sensitivity](surrogate-04.policy15-sensitivity.json) repeats the fixed analysis: every top-quintile accuracy and conditional within-fold AUC remains unchanged, while some historical-transfer probability metrics and pooled AUCs change. Policy14 artifacts remain intact. These are source-screened diagnostics, not complete independent certification of every legacy gold set.

Validation uses three fixed seeds, each making five folds by a hash of the initial lexical base after it deletion. Entries with the same base remain together even across ganas and citation-marker variants. Both exact master families and these broader groups have zero train/validation overlap. Historical transfer training also excludes every validation fold's lexical groups. The [fold audit](surrogate-04.fold-audit.json) and [independent metric checks](surrogate-04.validation.json) verify all 180 fitted fold conditions.

The input predictors are gana, the four coordinates, coarse root phonology, visible accent/nasal markers and citation shape. A second feature set adds numeric grammar-rule trace indicators. Exact dictionary code, exact root/meaning identity, panel ID, gold surface forms, variant counts, model answers and model reasoning are excluded. Rule selection searches single features and two-feature conjunctions using training data only, requiring at least 20 rows and eight lexical groups on each side, plus at least two error groups inside the putative hard rule. Family weights and fixed probability shrinkage prevent a heavily repeated root from dominating the fit.

This is retrospective validation: humans previously saw these development results, and the panels were adaptively sampled. Family separation prevents direct within-diagnostic family leakage; it does not erase the prior research history or make the sample representative of all Sanskrit.

## Results

The table shows accuracy in the predeclared hardest-ranked 20% of each validation fold, pooled within each seed. These are diagnostic subsets of development data, not candidate final membership. The three seeds reuse the same questions and must not be counted as three independent samples.

| Training / predictor | Seed 2026100704 | Seed 2026101704 | Seed 2026102704 |
|---|---:|---:|---:|
| xHigh: intercept baseline | 104/109 (95.41%) | 105/109 (96.33%) | 103/108 (95.37%) |
| xHigh: known-adanta baseline | 96/109 (88.07%) | 96/109 (88.07%) | 98/108 (90.74%) |
| xHigh: input rules | 96/109 (88.07%) | 100/109 (91.74%) | 98/108 (90.74%) |
| xHigh: input plus trace rules | 96/109 (88.07%) | 100/109 (91.74%) | 98/108 (90.74%) |
| Historical High: input rules transferred to xHigh | 97/109 (88.99%) | 99/109 (90.83%) | 98/108 (90.74%) |
| Historical High: input plus trace transferred to xHigh | 98/109 (89.91%) | 101/109 (92.66%) | 98/108 (90.74%) |

For the primary seed, within-fold error-ranking AUC is 0.820 for the known-adanta baseline versus 0.808 for either learned xHigh rule model. The learned model's family-weighted Brier score is 0.01584 versus 0.01549 for the known baseline; log loss is 0.07398 versus 0.07208. Trace features add no improvement to the xHigh learned predictions. All metrics, including easy conditions and other seeds, are in [the result artifact](surrogate-04.results.json).

The leading full-data exploratory input rule is “no visible anudatta marker AND lexical base ends in a vowel.” It covers 149 questions and 18 errors, but 118 questions and 17 errors are already-known adanta. Its non-adanta remainder is 30/31 correct. A more apparently difficult rule, “medium-length base AND literal-final-a citation,” has 17 errors in 90 questions—but every question is Curadi adanta. These are restatements or enlargements of the existing lead, not a new broad mechanism. Across 15 xHigh fold fits, the broad proxy is chosen 12 times; the other three choices are literal-final-a refinements.

Once adanta is excluded, all learned and baseline top-quintile selections score 86/86, 85/85 and 84/85 for the three seeds. Both xHigh rule models have **within-fold AUC 0.50 in every seed**. Historical transfer has within-fold AUC approximately 0.46–0.49. It supplies no validated enrichment beyond the two residual current-reference errors.

There is an instructive metric trap: pooled out-of-fold AUC for the residual xHigh models is approximately 0.66–0.71, despite constant predictions within every error-containing validation fold. Different fitted baselines across folds create this apparent ranking. The validation artifact reports within-fold AUC explicitly, so the pooled figure is not presented as a new predictive signal. Likewise, an all-success bootstrap interval of [1,1] is a degenerate resample of observed successes, not certainty about future performance.

The primary seed's learned top-quintile accuracy has a descriptive family-bootstrap interval of approximately 80.9–95.0%. That wide interval does not certify the target or exclude every target-compatible population rate. The decisive limitation is that the enrichment comes from the known narrow mechanism, with no demonstrated new broad error families.

## Decision and remaining uncertainty

The frozen advancement gate called for a distinct interpretable mechanism with current-reference out-of-family support, at least five supported error families overall, at least three represented ganas and a plausible source/supply audit. It fails. Outside adanta there are only two current-reference error groups in the entire available sample; a more flexible statistical model cannot manufacture additional independently observed groups from those labels.

The two residual examples are **Divadi puTa~ 04.0013, Lun**, and **Tudadi kUN 06.0137, AshirLin**. Both were already individually reviewed. A stale prose label in the stable index called 04.0013 “klid”; this diagnostic corrected that label to putha. Raw task identities, scores and source audits always contained the correct puTa~ citation and were not rewritten.

No new dictionary-wide pilot generation or test-tuple ranking was performed. Ranking unmeasured families far from this small, adaptively sampled evidence would be extrapolation. Historical High errors cannot simply be relabeled as likely xHigh errors: the family-disjoint transfer check did not establish that relationship here. A new primary-source hypothesis, broader genuinely fresh development coverage or repaired independent grammatical evidence could reopen the search; this bounded rule class does not exhaust all possible surrogates or classical grammar.

The earlier narrow result remains the strongest verified lead: non-aorist short-vowel adanta 31/39 = 79.49%, but only 13 development and 14 test families, with approximately 8.04 pp development family-cluster SE. The surrogate provides no reason to change the existing feasibility conclusion or to claim a diverse final benchmark. `benchmark_ready` remains false.

## Artifacts

- [Frozen diagnostic design](surrogate-04.design.json), [dataset and source hashes](surrogate-04.dataset.json), [development features and labels](surrogate-04.development-features.json).
- [All metrics and exploratory training rules](surrogate-04.results.json), [all fitted folds](surrogate-04.fold-audit.json), [validation and conditional AUC](surrogate-04.validation.json).
- [Decision record](surrogate-04.decision.json), [current policy15 sensitivity](surrogate-04.policy15-sensitivity.json), [offline implementation](../../../misc/vp_4d_surrogate04.py), [stable research index](current.md).
