# 4D release feasibility 01

Both required sizes have feasible aggregate allocations after grammatical quarantine: **1,000 questions with at most three per family**, and **1,601 with at most five per family**, each using **464 master-test families**. This establishes supply and diversity feasibility only. The observed Opus pilot remains too easy, and neither model accuracy nor sub-one-point standard error is established for a release.

No final task IDs or membership lists were emitted. The optimizer used capacities of grammar bins, stripped of root code, dictionary text, task IDs, and surface forms. Test model answers and test gold forms were not loaded. The master development/test/RL assignments are unchanged. The old 500/500 test suballocation is not imposed on these calculations.

## Scope and allocation constraints

Every hypothetical task remains a dictionary dhatu plus exactly lakara, prayoga, purusha, and vacana. There are no added derivations, prefixes, or independently selected padas. Passive questions use the pilot’s exact transitive-meaning allowlist. All ten pilot grammar predicates are retained.

The common feasibility constraints require all ten classical lakaras (each at least 3%, at most 25%), all ten ganas (at least one task each, at most 30%), each person and number between 20% and 40%, passive between 3% and 15%, and each grammar cell between 2% and 25%. The family maximum is varied as a diagnostic; it is not a user-mandated ceiling. The objective preserves pilot proportions where feasible, then spreads tasks across families. Pilot scores are not optimization inputs.

The screened predicate union contains **11,650 unique model-visible tuples across 464 families**. Overlapping cells share capacity constraints, preventing double counting. Integer witnesses were checked independently against all capacity and diversity constraints. HiGHS 1.15.1 solved each reported case.

## Feasible compositions

| Grammar cell | N = 1,000, max 3/family | N = 1,601, max 5/family |
|---|---:|---:|
| Internal r/v lengthening | 27 | 45 |
| Svadi perfect | 42 | 70 |
| Other athematic perfect | 50 | 115 |
| Perfect reduplication changes | 108 | 215 |
| Divadi sigmatic aorist | 100 | 161 |
| Aorist consonant changes | 100 | 161 |
| Athematic present system | 213 | 253 |
| Dictionary Curadi futures | 215 | 345 |
| Transitive Curadi nonpresent passive | 45 | 75 |
| Primary benedictive stem changes | 100 | 161 |

| Diagnostic | N = 1,000 | N = 1,601 |
|---|---:|---:|
| Families | 464 | 464 |
| Maximum tasks per family | 3 | 5 |
| Maximum family share | 0.300% | 0.312% |
| Maximum lakara share | 20.400% | 24.984% |
| Maximum gana share | 30.000% | 29.981% |

For N=1,000, the family-size histogram is 1 tasks: 124 families, 2 tasks: 144 families, 3 tasks: 196 families.
Lakara counts: Lit 204; Lot 69; VidhiLin 69; Lun 200; Lat 32; AshirLin 125; Lut 95; Lrn 64; Lan 55; Lrt 87.
Gana counts: Adadi 114; Curadi 300; Kryadi 92; Juhotyadi 41; Bhvadi 196; Tudadi 40; Rudhadi 38; Divadi 123; Svadi 42; Tanadi 14.

For N=1,601, the family-size histogram is 1 tasks: 1 families, 2 tasks: 162 families, 3 tasks: 28 families, 4 tasks: 173 families, 5 tasks: 100 families.
Lakara counts: Lan 72; Lit 400; Lot 79; VidhiLin 76; Lun 325; Lat 49; AshirLin 208; Lut 164; Lrn 119; Lrt 109.
Gana counts: Adadi 173; Curadi 480; Kryadi 137; Juhotyadi 62; Bhvadi 339; Tudadi 70; Rudhadi 56; Divadi 192; Svadi 70; Tanadi 22.

All person, number, voice, and cell distributions are in the JSON artifact. These are examples of feasible compositions, not recommended final weights.

Two tasks per family cannot supply 1,000 questions under the proposed gana limit. Four per family cannot supply 1,601. These lower bounds follow from summed family capacities capped by gana, independently of the solver; the feasible witnesses show that maxima of three and five, respectively, suffice.

## Narrow-cell limits

The full master test split has only nine internal-lengthening families, 14 Svadi-perfect families, and 15 families in the narrow transitive Curadi passive cell. Their upper capacities at a common family maximum K are:

| K | Lengthening | Svadi perfect | Narrow passive |
|---:|---:|---:|---:|
| 3 | 27 | 42 | 45 |
| 5 | 45 | 70 | 75 |
| 6 | 54 | 84 | 90 |
| 8 | 72 | 112 | 120 |
| 10 | 90 | 126 | 150 |

These individual upper bounds need not be jointly attainable because families and grammar cells overlap. The reported integer allocations account for that overlap. Increasing the family maximum increases narrow-cell weight but does not create new independent families.

## Precision and family dependence

For an illustrative exchangeable within-family correlation ρ, independent families, common accuracy p, and m_f tasks in family f, the variance of the unweighted accuracy is:

`Var(accuracy) = p(1-p)/N × [1 + ρ × (Σ m_f²/N − 1)]`

The bracket is the design effect. This is a sensitivity model, not an estimated correlation or a precision certificate. Here is SE in percentage points at p=0.80:

| Feasible N / family maximum | ρ = 0 | ρ = .02 | ρ = .05 | ρ = .10 | ρ = .20 |
|---|---:|---:|---:|---:|---:|
| 1,000 / 3 | 1.2649 | 1.2833 | 1.3104 | 1.3543 | 1.4382 |
| 1,601 / 5 | 0.9997 | 1.0278 | 1.0686 | 1.1334 | 1.2529 |
| 2,000 / 8 | 0.8944 | 0.9295 | 0.9797 | 1.0581 | 1.1997 |
| 2,400 / 10 | 0.8165 | 0.8563 | 0.9127 | 0.9997 | 1.1541 |

For the 1,601-task witness, SE is below one point only for ρ below approximately **0.000219** under these assumptions. That is effectively an independence requirement. At accuracy 79%, even 1,601 independent tasks miss the one-point threshold: at least 1,660 are required. The 2,400-task sensitivity case also has almost no margin at ρ=.10 and p=.80; near 79% it exceeds one point.

More tasks within the same 464 families have diminishing precision returns. The JSON includes sum-of-squared family counts and effective family counts for every scenario. Exact-citation-plus-gana grouping can also split related lexical roots across families, so dependence may extend beyond the declared groups.

Before final evaluation, freeze an extension rule tied to a prespecified family-aware SE estimator, maximum authorized size, and shared budget. Report family-cluster uncertainty and a sensitivity analysis for related-root grouping. Do not choose an extension because the observed score is outside 79–81%; that would adapt membership to the score target. The current work does not alter the coordinator’s budget or reserve.

## Development results and validity review

**Opus 5.5 xHigh/16,384 scored 108/120 overall and 108/118 usable answers (91.53%)**, with two refusals and no truncations. The exploratory family-cluster ratio SE is about 3.02 points. The coordinator records a $0.6912 upper cost for this job. This worker made no paid calls or ledger changes.

Five of ten exact-answer misses are internal vowel-lengthening errors concentrated in three root families. The broad present-system, other athematic perfect, perfect-reduplication, aorist-consonant, and primary-benedictive cells scored 100% in this small pilot. The passive cell had two refusals and 10/10 correct usable answers; refusals provide no evidence of grammatical hardness.

Two remaining scored misses reveal strong oracle concerns, so the raw score is preserved and the contexts are quarantined rather than used to increase difficulty:

- **Svadi rādh, meaning saṃsiddhau:** VP applies 6.4.123 and accepts रेध, while the model supplied रराध. The [primary commentary](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.123.htm) restricts the reduction to the injuring sense and contrasts unreduced forms otherwise. Upstream code checks the gana without a semantic condition and includes a TODO. Exclude these rule contexts pending certification.
- **Divadi ñitṛṣā̃ aorist:** dictionary `YitfzA~` differs from the hard-coded PUSH_ADI string `Yitfza~`. A local marker-only reproduction switches VP from the scored sigmatic form to the model’s अतृषाव and activates [3.1.55](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.55.htm). The [primary Dhatupatha](https://sa.wikisource.org/wiki/अष्टाध्यायी-धातुपाठः) places this root in puṣādi. A score-independent list audit also found `04.0113 yusa~` absent from the list; its test-family aorists are conservatively excluded without reading any test answers.

The putha aorist disagreement is different: that root occurs before puṣādi in the primary Dhatupatha, supporting the engine’s sigmatic analysis. The two Curadi future/conditional errors concern dictionary Akusmiya roots for which the model chose Parasmaipada. [Dhatupatha and Dhatupradipa evidence](https://jainqq.org/booktext/Dhatupradip/004319) supports an Atmanepada subgroup; exact variant entries still deserve direct review before this becomes a sampling lead.

The Data loader also silently attaches prefixes to dictionary entries 02.0012, 02.0041, 02.0042, and 10.0368. None occurs in the pilot. All inherited-prefix or inherited-sanadi entries are excluded from the revised feasibility census. The three affected master-test families and one missing-list aorist family reduce the original union from 468 to 464 families. Master split membership is unchanged.

A coordinated passive audit found no pilot overlap with the missing optional Cinvat lengthening reported by the 5D worker: all 12 4D passives have rule 6.4.62, but none has 6.4.92. The future exclusion checks both rules across all nonpresent passive lakaras, including the benedictive. It removes zero current master-test candidate rows. The [primary commentary on 6.4.62](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.62.htm) documents the relevant causal-passive long and short alternatives; this targeted diagnostic is not complete passive-key certification.

A dictionary-only audit also found four pairs with identical visible citation, gana, and meaning but different intrinsic antargana metadata: jvala, cala, dhvana, and arha. None appears in this pilot or the current master-test predicate union. Future generation must use a complete audited union for indistinguishable entries or quarantine them; a hidden dictionary code must not select a narrower answer key. The feasibility code now quarantines these identities, with zero additional supply impact.

These exclusions were developed after development-result discovery and are explicitly recorded as such. The frozen pilot, raw gold, raw responses, and historical headline score are untouched. Omitting the two contested usable questions gives a diagnostic 108/116 (93.10%), reinforcing that this mixture is too easy; it is not a revised certified benchmark score.

## Next useful experiment

The only new bounded lead supported by this pilot is the lexical Atmanepada restriction of the Akusmiya subgroup. There are 17 development, 18 test, and 10 RL-training families. Both of the pilot’s Akusmiya active questions failed, but two examples cannot estimate subgroup difficulty. A fresh development probe across tenses and persons could test the mechanism after direct variant-entry audit. It would remain exactly 4D: the ending restriction is a property of the dictionary root, not an added coordinate.

A proposal is recorded in `next-experiment-proposal-02.json`, explicitly non-submittable until questions and lexical audits are prepared. No new paid request has been submitted. Even if the lead works, its small family supply and the maximum Curadi concentration must be considered before fitting final weights. Current results do not justify an Astra replication of an already-too-easy aggregate merely to seek 80%.

## Reproduction and artifacts

- `misc/vp_4d_release_feasibility.py`: reads grammar metadata, aggregates capacities, solves and validates allocations, emits only aggregate results.
- `release-feasibility-01.json`: all eight allocation cases, capacity bounds, distributions and uncertainty sensitivities.
- `release-feasibility-01.before-grammar-quarantine.json`: preserved initial calculation before validity findings.
- `pilot-01.disagreement-review.json`: raw development scores and per-disagreement audit classifications.
- `pilot-01.oracle-evidence.json` and `misc/vp_4d_oracle_evidence.py`: reproducible citation-only diagnostic, passive cross-check, and visible-identity audit.
- `pilot-01.scope-audit.json`: all 120 tasks regenerate, with 120 unique prompts and no inherited operations; this is not full oracle certification.
- `misc/vp_4d_release_report.py`: renders this report.

The solver dependency is scoped to this worker’s artifact folder; the shared Python environment is unchanged. Recreate it with `uv pip install --target benchmarks/parallel-search-20261006/four_d/_solver_deps --no-deps highspy==1.15.1`, then run the two worker scripts with `.venv/bin/python`.
