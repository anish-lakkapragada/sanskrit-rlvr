# 4D pilot 03: visible markers, weak perfects, and specialized iṭ

The revised panel contains **178 fresh questions from 140 development families**, with at most two questions per family. Use `experiment-request-03-r1.json` and `pilot-03-r1.questions.json`. The task SHA256 is `bd22abe7592b5bbe29ed9c3aab95ba3bfe25f007afb78cb76d7920e2471dc0ec`. The preliminary 180-question panel remains preserved and must not be submitted.

This is a test of three new grammatical hypotheses, not a benchmark satisfying the 79–81% target. All questions retain the original 4D renderer and ask for one Devanagari form from the complete dictionary identity plus lakara, prayoga, purusha and vacana. No added derivation, prefix, separately chosen pada, invented root or hidden choice is introduced.

## Prespecified mechanisms and selection

| Mechanism | Questions | Families | Fixed comparison |
|---|---:|---:|---|
| Same-gana marker contrast | 60 | 60 | 15 accent contrasts and 45 other anubandha contrasts |
| Weak-perfect alternation | 60 | 47 | 30 positive/optional e-change traces and 30 prohibition traces |
| Specialized nonpresent iṭ | 58 | 33 | Future, periphrastic future and conditional |

The first predicate requires identical gana and identical phonemic root immediately after lexical it-deletion, but different complete dictionary citations. Pool membership uses initial lexical metadata; it never compares final forms. Every accent and anubandha remains visible in the actual prompt. The relevant mechanisms include nasal insertion under 7.1.58 and ending selection under 1.3.12/78. This differs from pilot02's cross-gana homography test. The accent-only subset is small; the larger marker subset provides the broader supply.

The second predicate requires Kartari Lit, a non-Curadi entry, and a trace in 6.4.120/121/122/125 or the prohibition 6.4.126. The semantic condition under 6.4.123 remains excluded. The positive/prohibition quota is fixed before evaluation. Some prohibition traces involve a derived guna vowel; these should not be described as identical CVC stems that simply declined e-substitution. No development entry supplies 6.4.125 here, although independently sourced controls validate that rule. Its reserved-test supply is consequently uncalibrated by this panel.

The third predicate requires non-Curadi Kartari Lut/Lrt/Lrn and a trace in 7.2.36/37/38/44/45/48/57/59/60/70. It tests obligatory, optional and prohibited iṭ behavior and its interaction with consonant sandhi. All licensed variants stay in the key. Earlier probes of Curadi futures or aorist consonants do not directly measure this construction.

Selection uses seed 2026100703, fixed grammatical predicates and a seeded integer objective. All historical pure-4D exposure files are excluded by the full visible tuple. The smallest cell is selected first, followed by the marker cell and perfect cell, with no family reused between cells. The initial marker gana maximum of 54/60 was infeasible after family separation, so it was relaxed to 56/60 **before freezing or seeing any model answers**. No scarce class quota was satisfied with invalid input.

The final distribution spans nine ganas and all ten classical lakaras. Bhvadi is 114/178 (64.04%); Lit is 66/178 (37.08%); Lun is 6/178 (3.37%). Lut/Lrt/Lrn together are 76/178 (42.70%). All questions use Kartari to isolate the mechanisms. Person counts are 60/60/58 and number counts 60/59/59. These are exploratory weights, not proposed final release quotas. The final benchmark still needs an independently declared distribution with broad grammatical diversity.

## Sources, corrections and mechanical audit

The source audit passes **35/35 controls**, comprising directly printed examples and four explicit rule inferences. It includes representative marker pairs, perfect e-changes and exceptions, iṭ lengthening, optional insertion, and pada-dependent prohibitions. Source controls validate constructions; they do not constitute independent proof of every paradigm member. Two initial manual control entries omitted guna; re-reading the source corrected the researcher's transcription before selection. That correction is recorded in the audit.

Primary references include [7.1.58](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.1.58.htm), [6.4.120](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.120.htm), [6.4.121](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.121.htm), [6.4.122](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.122.htm), [6.4.126](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.126.htm), [7.2.44](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.44.htm), [7.2.57](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.57.htm), and [Dhatupradipa](https://jainqq.org/booktext/Dhatupradip/004319). The JSON records additional rules and exact controls.

Final lexical review found that **Bhvadi ghṛ 01.1088** is restricted to named nominal formations by [Balamanorama, printed page 150](https://sa.wikisource.org/wiki/पृष्ठम्:सिद्धान्तकौमुदी_(बालमनोरमा_उत्तर-१).djvu/१६१). The two affected future questions were deleted without replacement, producing the 178-question revision before evaluation. The preliminary panel is preserved. The exclusion is uniform across coordinates and outcomes; it does not apply to independently licensed Bhvadi gṛ or Juhotyadi ṛ. The coordinator subsequently adopted this shared scope restriction.

All 178 revised questions pass the shared validator, regeneration, transliteration, prompt uniqueness and unchanged master-family membership. Full dictionary citations are present in every prompt. No question contains 8.2.78, so the separate historical vowel-lengthening concern below does not affect this panel. No provider calls or shared ledger edits were made by this worker.

## What pilot02 established

Its sole exact-answer disagreement was Juhotyadi ghṛ: VP `जघृयाव` versus Opus `जिघृयाव`. [Balamanorama, printed page 228](https://sa.wikisource.org/wiki/पृष्ठम्:सिद्धान्तकौमुदी_(बालमनोरमा_उत्तर-२).djvu/२६) marks ghṛ and the following class3 subgroup Vedic, with an explicit classical exception for ṛ. The i-reduplication is explained as Vedic. This is not evidence for classical benchmark hardness.

The coordinator adopted a uniform exclusion of 03.0015–03.0026 except 03.0017. It removes one success and the sole miss from pilot02. The original raw score remains **106/107 completed** and **106/108 overall**. The current scope-filtered diagnostic is **105/105 completed** and **105/106 overall**, with one refusal. Each of the three cells has 35 completed correct answers. Neither licensed Akusmiya nor cross-gana homography showed useful difficulty.

Under the same consistent policy, pilot01 has **102/108 completed** (94.44%) and **102/110 overall**, with two refusals. These are post-discovery diagnostics, not new independent evaluations. The remaining old lengthening signal also needs caution: Dhatupradipa reports a tradition allowing short forms of urd/kurd/khurd, potentially relevant to the model's `चुखुर्दिरे` answer. That issue is being referred to the coordinator for source review; no historical scores have been changed to count it correct.

## Supply and precision

After the current scope exclusions, the two prior grammar unions contain 17,588 master-test tuples across 572 families. The new predicates contain 12,218 tuples across 387 families, of which **10,680 tuples are outside both prior unions**. Combined coverage is **28,268 tuples across 756 master-test families**. These are grammatical metadata counts, not final task membership or accuracy estimates. No test model answers or test surface forms were used to select these predicates.

| Pool | At most 3 per family | At most 5 | At most 6 | At most 10 |
|---|---:|---:|---:|---:|
| New predicates | 869 | 1,349 | 1,589 | 2,375 |
| Combined prior and new predicates | 2,142 | 3,528 | 4,221 | 6,832 |

The counts are upper bounds before joint diversity constraints. They establish that the original 6,687 questions and prior 17,849-tuple union were not the search boundary. They do not establish that a sufficiently large, diverse 79–81% mixture exists.

At 79% accuracy, independent sampling requires at least **1,660** tasks for SE strictly below one percentage point; at 80%, at least **1,601**. A 1,000-task panel has approximately 1.27 points of iid SE at 79%. This 178-task pilot has approximately 3.05 points, before family dependence. Repeating roots can increase uncertainty, and the exact citation/gana split separates some related roots whose markers differ. Final uncertainty should include clustering by a broader marker-stripped lexical group as a sensitivity analysis, in addition to the master family definition. No claim of sub-one-point SE is made here.

The master development/test/RL assignments remain unchanged. This panel contains development families only; no test or RL membership has been selected. Source controls drawn from dictionary entries in other splits are grammar checks, not model evaluations or training examples.

## Analysis fixed before evaluation

Report exact accuracy for all requests and completed answers separately, with refusals, truncations, invalid outputs and infrastructure problems shown independently. Report all three cells and the fixed marker/perfect subgroups, including easy results. Review every disagreement against the sources before treating it as useful difficulty.

A main cell with at least eight source-supported errors across six families warrants a fresh confirmation panel. A 30-question perfect subgroup with at least five errors across four families may motivate targeted follow-up. These are pragmatic discovery triggers, not significance tests or benchmark acceptance criteria. They cannot justify selecting the same missed questions for a release.

If these mechanisms remain easy, report that negative result. Other untested constructions could still exist; neither this pilot nor current evidence proves impossibility. A credible new lead requires an independently defined grammatical mechanism and sufficient diverse supply. Final weights and membership must be frozen before final model exposure, and the strongest tested reference must actually fall within 79–81%.

The maximum planning reservation is **$29.69752 Anthropic**, computed with 1,500 input tokens and 16,384 output tokens per question. The coordinator must recompute and reserve under the cumulative shared ledger before submission. The worker has spent zero. Astra pairing is conditional on informative, source-supported Opus signal. **Benchmark readiness remains false.**
