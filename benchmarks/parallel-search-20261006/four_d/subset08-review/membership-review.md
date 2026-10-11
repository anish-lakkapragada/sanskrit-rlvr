# Frozen Astra240 subset audit

**The independent input and regeneration checks pass.** No change to the frozen subset or release gates is proposed. This is an informative development diagnostic with limited covariance precision, not a representative probability sample or a final benchmark qualification.

The exact parent task file SHA256 is `6db3cebd9e01b2e5402aa6011677056023b9abd78238fa473c234f53f162eaa8`; subset SHA256 is `2ba4c2bbe1181808349a1c985bbd25a9b67271c9747f101b5407ec6063835598`. [The independent receipt](membership-audit.json) verifies:

- 240 unique questions, each an unchanged complete dictionary from the 2,400-question parent, including gold and prompt identity. All240 were freshly regenerated under policy19.
- All2,400 parent entries satisfy policy19 and the master development split. The subset supports all42 recipe×tense×voice cells, all10 classes and all10 tenses, with108 Lun,24 passive and recipe counts134/58/48.
- Curādi has3 Lun and11 non-Lun controls, resolving the provisional block sketch's missing Curādi-Lun support. The parent has29 Lun and116 non-Lun Curādi questions.
- There are110 families:28 singletons,34 pairs and48 triples. The two120-question chunks concatenate exactly to the subset and share no family.
- There is no input-normalized tuple overlap with the saved61 historical input files from the two campaign ledgers. All110 subset families and all671 parent families were previously exposed. The original split explicitly acknowledges that legacy analysis inspected all families before the prospective split; this audit does not claim global absence of exposure.
- Declared hashes and quotas match. The input-only selection code was read; it uses seeded shuffled candidate pairs and a constrained flow, not model outputs. The min-cost selection itself was not independently replayed; actual frozen membership and constraints were checked directly.

The pair counts are:

| Pair type | Subset pairs | Contributing families |
|---|---:|---:|
| Both Lun | 43 | 43 |
| One Lun | 79 | 40 |
| Two different non-Lun tenses | 56 | 38 |

Within LL,26 pairs use yaN→Ric twice,9 use yaNluk→Ric twice and8 mix those recipes. The corresponding parent pair counts are624,182 and210. There is **no san-containing LL pair in the parent**, so the subset correctly does not claim to identify that covariance. Any future final input allocation with such pairs adds an unsupported dependence component.

The subset LL pairs cover six classes. Bhvādi contributes26/43 =60.47%, compared with758/1,016 =74.61% of parent LL pairs. Rudhādi's11 parent LL pairs have no subset counterpart. These differences do not violate the frozen plan, but matter for transporting a pooled covariance. A recipe-pair-only forecast assumes away any additional class/family-selection effects; disclose that assumption and use sensitivity ranges.

The subset's42 joint cells all have support. A finer class×recipe×Lun/non-Lun crossing has18 parent-positive/subset-zero cells totaling134/2,400 =5.58% of parent questions. The receipt lists each one. Consequently, a fully crossed saturated transport estimator is unsupported. Simple42-cell share weights range over a mild interval and give task Kish effectiveN238.17 and family-total Kish effectiveN96.08; these are weight-concentration diagnostics, **not independent sample sizes or guarantees of SE**. They do not repair within-cell family selection.

The [preselection memo](preselection-memo.md) supplies the estimator and missingness cautions. For the actual43 independent LL pairs, its favorable known-mean Bernoulli illustration has SE `sqrt(1.41/43)=0.181`, with a normal-approximation half-width about0.355. This is not an interval for observed data; it shows why43 pairs cannot tightly certify a low correlation. Preserve all outcomes, use whole-family resampling, report all-request success/completion/usable-ratio influences separately, and wait for both Astra chunks and all six Opus chunks before any aggregate analysis.

The [separate bounded source check](source-review.md) found no concrete blocker in the six assigned new rule contexts. This does not independently certify every rare generated paradigm. No pilot08 model output, test model answer, ledger mutation or paid API call was used in either review.
