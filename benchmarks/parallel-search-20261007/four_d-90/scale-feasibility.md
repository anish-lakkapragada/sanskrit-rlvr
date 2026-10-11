# Exact-4D scale and precision feasibility

2026-10-07. Offline assessment after the completed 175/200 Opus development result. No paid calls or held-out model outcomes were used. These are **candidate allocations, not frozen benchmarks**.

**There are enough valid, fresh questions for 1,250 or 1,800 items. The binding limitation is the number of difficult verbal-root families, not the number of conjugations.** A 1,250-item version would have approximately 0.94 percentage points of conventional iid standard error at the observed 87.5% rate, but the current evidence suggests roughly 3 percentage points of uncertainty when transferring to new families. Sub-1pp family-generalization precision is not supported by this mixture.

## Recomputed supply

I regenerated the relevant dictionary entries across all ten tenses, three persons, and three numbers, with Kartari fixed, preserving complete oracle answer sets and applying current shared policy21 and local source holds. This extends beyond the old 6.7K questions. “Family” retains the established grouping: exact dictionary citation plus class; meaning/code duplicates stay together.

| Grammar cell | RL train: families / valid tuples | Development: families / valid tuples | Test: families / valid tuples | Test tuples after prior visible tuples excluded |
| --- | ---: | ---: | ---: | ---: |
| Short-penultimate literal-a-final Curadi, non-Lun | 9 / 729 | 13 / 1,053 | 14 / 1,134 | 1,119 |
| Other literal-a-final Curadi, Lun | 15 / 135 | 16 / 144 | 25 / 225 | 224 |
| Classes other than Curadi | 345 / 31,590 | 531 / 48,889 | 774 / 70,668 | 69,907 |

All cells retain exactly `(dhatu, lakara, prayoga, purusha, vacana)`, without added operations, prefixes, or a selected ending set. **Prayoga is present but fixed to Kartari** in these allocations; this is not full coverage of every option in the four-dimensional space.

The original 500-family initial-release reserve has only **5 short-hard families and 400 fresh short-hard forms**. At 52% hard weight it cannot supply a 1,000-item benchmark. The other reserve half contains 9 additional hard families and 719 forms. The proposals below therefore draw on the full existing test split, including future-version reserve families. Nothing has changed their assignments or registered them for evaluation.

No registered job input contains a test-split family. However, the master split explicitly records that legacy analysis inspected all families before the split; the legacy input corpus covers all 2,162 families. Thus “family-disjoint from the new development campaign” is accurate, while “never seen by previous analysis” is not. Current train/development/test assignments remain disjoint; moving development failures into test would invalidate that protection.

## Concrete candidate allocations

The first four preserve the pilot's grammar-defined 52% / 8% / 40% weights. All include ten classes and ten tenses, 60% Curadi, and 12% Lun. Broad items use one question per family; hard-family load is balanced before tense/person/number allocation.

| Items | Short non-Lun / other Lun / broad | Total families | Maximum questions per family | iid SE at 87.5% | Family-transfer diagnostic SE |
| ---: | --- | ---: | ---: | ---: | ---: |
| 500 | 260 / 40 / 200 | 239 | 19 | 1.479pp | 2.995pp |
| 1,000 | 520 / 80 / 400 | 439 | 38 | 1.046pp | 2.986pp |
| 1,250 | 650 / 100 / 500 | 539 | 47 | 0.935pp | 2.985pp |
| 1,800 | 936 / 144 / 720 | 759 | 67 | 0.780pp | 2.983pp |

A second **1,250-item proposal** reduces concentration in the shortest hard roots: **500 short non-Lun + 188 other-adanta Lun + 562 broad**, across **601 families**, maximum **36 questions per family**. Its class/tense shares are **55.04% Curadi and 19.52% Lun**. Transporting the three observed cell rates gives **87.99%**, iid SE **0.920pp**, and a family-transfer diagnostic of **2.608pp**. This is an exploratory change in weights, not an independently validated improvement: the other-adanta rate is measured from only one question in each of 16 development families. Allocating approximately 7–8 questions to each test family extrapolates beyond that evidence.

Both proposals select all eligible hard families under their predicates, rather than selecting roots because they failed. The metadata files identify concrete fresh tuples. They are mechanically regenerated under the current oracle and source exclusions; **the fresh lexical entries and every generated form have not received independent source certification**. The completed development disagreement review does not certify these new forms.

## What precision can mean here

The current 200-item score has iid SE **2.34pp**, root-cluster SE **3.27pp**, and an iid 95% interval extending above 90%. It establishes a development signal, not a guaranteed below-90% population rate or strongest-model result.

Within the short-hard cell, the 13 family accuracies range from **37.5% to 100%**, with eight questions per family. Their sample variance is 0.043269; a balanced random-effects decomposition estimates intraclass correlation **0.169** and between-family variance **0.026786**. At the original 52% weight, transferring to 14 new families gives an estimated **2.27pp uncertainty floor from this cell alone**, even with arbitrarily many questions per family. Approximately **73 independent hard families** would be needed merely to push that contribution below 1pp under the same estimated variance and weight. The current predicate supplies only 36 families across all three splits, including just 14 test families.

The table's family-transfer diagnostic uses `sqrt(sum(weight² × observed variance of family means / target family count))`. It is a planning sensitivity calculation, not a calibrated confidence interval: the small one-question cells confound family and question variation, family samples are small, and hard/easy rates may not transfer. The 2.27pp random-effects floor is also estimated, not a proven mathematical lower bound.

For an independently sampled Bernoulli question population, strict SE below 1pp requires **1,094 items at 87.5%, 1,276 at 85%, 1,601 at 80%, or 2,501 at worst-case 50%**. A 1,250-item panel therefore does not guarantee this threshold across the whole 80–90% range. A 1,800-item panel does under the iid assumption, but not under family dependence. Once a fixed benchmark is chosen, its exact observed score has no item-sampling error; repeat-run stochastic variance and extrapolation to unseen roots are separate quantities. A design that fixes all test roots and samples forms could estimate a narrower finite-root target with smaller uncertainty, but must explicitly limit that claim and use a prespecified sampling estimator. It cannot turn those same roots into independent evidence about new roots.

## Limits and next decision

The measured difficulty is overwhelmingly a real non-aorist stem effect: **21/25 misses are outside Lun**, including 20 in the short-adanta cell. More question generation preserves this mechanism but does not manufacture more lexical families. RL can train on the 9 disjoint short-hard training families and evaluate transfer to the 14 test families; repeating their conjugations produces hundreds of examples, not hundreds of independent mechanisms.

A precise broader hypothesis is to expand from short-penultimate adanta roots to **all literal-a-final Curadi across non-Lun tenses**. The census adds 17 development families / 1,377 forms and 25 test families / 2,025 forms outside the short predicate. However, the previous pilot04 exploratory other-adanta/non-Lun slice was **23/23 correct**, so this is additional coverage without current evidence of useful difficulty. The already completed broad-tail and ciN probes likewise do not support reopening those leads. A passive extension could test interactions involving the existing prayoga coordinate, but requires transitivity/source audits and does not by itself solve the limited-family problem. The earlier nonpresent Curadi passive pilot's two policy-valid non-successes were missing answers; its nine usable policy-valid answers were all correct, so they should not be advertised as demonstrated grammatical errors.

**Recommendation:** finish the same-panel Astra comparison and decide whether a deliberately weighted, finite-root challenge benchmark satisfies the intended claim. If so, 1,250 items is a feasible development-to-release proposal, with 1,800 providing better question-level precision. Independently audit the 39 test hard families before a final freeze and evaluate the fixed selection once. If sub-1pp uncertainty about new-root generalization and broad lexical diversity are both mandatory, this current 4D mechanism is insufficient; the data do not justify claiming that a larger N resolves it.

Artifacts: [full census and statistical calculations](scale-feasibility.json), [500-item proposal](scale-candidate-500-metadata.json), [1,000-item proposal](scale-candidate-1000-metadata.json), [1,250-item proposal](scale-candidate-1250-metadata.json), [1,800-item proposal](scale-candidate-1800-metadata.json), and [broader-weight 1,250-item proposal](scale-candidate-1250-broader-metadata.json). The standalone helper is `misc/vp_4d_90_scale_feasibility.py`; the broader-weight alternative was added as an offline supplemental calculation. Source hashes, individual family capacities, entry/tuple holds, and input-exposure hashes are recorded in the JSON. No raw results, frozen panels, budget ledger, runner, or shared report were changed.
