This audit maps different precision questions. It uses only the completed 200-question development comparison and the 1,800-question input manifest. It does **not** read live final responses, alter membership, change the frozen analyzer or relax a qualification gate.

The development panel has 104 short-adanta non-aorists from 13 families (eight questions each), 16 other-adanta aorists from 16 families, and 80 broad questions from 80 families. All 200 responses are usable for both models. Canonical development scores remain 175/200 Opus and 161/200 Astra; no source or spelling regrading is performed here.

| Development uncertainty estimate | Opus SE, percentage points | Astra SE, percentage points |
|---|---:|---:|
| Pooled iid Bernoulli approximation | 2.339 | 2.802 |
| Fixed-cell independent-question approximation | 2.244 | 2.694 |
| Existing unstratified family sandwich | 3.265 | 4.016 |
| Existing unstratified family bootstrap | 3.253 | 4.012 |
| Existing class-stratified family bootstrap | 3.109 | 3.789 |
| **Fixed 52/8/40, families resampled within cells** | **3.053** | **3.766** |
| Fixed-cell family sandwich with small-sample correction | 3.170 | 3.897 |

Existing bootstraps use their original 20,000 draws; the new bootstrap uses 100,000 seeded draws. Its analytic bootstrap variance independently agrees within 1%. All-request and usable estimates coincide in this complete development panel. The fixed-cell bootstrap 95% intervals are 81–93% Opus and 73–87.5% Astra. They are development sensitivity intervals, not final qualification intervals.

For each replicate, independently resample the observed number of families within each cell, retain each sampled family's entire observed vector, and calculate `0.52*p_short + 0.08*p_other + 0.40*p_broad`. The same draws preserve pairing between models. This matches the declared three mixture weights; stratified estimation combines fixed stratum weights with within-stratum estimates. [Statistics Canada, stratified sampling](https://www150.statcan.gc.ca/n1/pub/12-001-x/2019002/article/00006/02-eng.htm)

The original unstratified bootstrap permits the hard-short question weight to vary: its central 95% range is 35.4–64.3%, although the benchmark fixes 52%. Stratifying only by class still permits 38.8–61.3%, because Curadi contains two cells with different family loads. Fixing the cells removes that source of variation but only modestly lowers these development estimates. The new method still assumes exchangeability between families and does not reproduce every class, tense, person/number or solver constraint. It is not an exact randomization SE for the seeded constrained selector. Within-stratum cluster resampling has formal design requirements; deterministic quota balance alone does not establish known inclusion probabilities. [Survey package methodology](https://r-survey.r-forge.r-project.org/survey/html/bootweights.html), [Statistics Canada, non-probability samples](https://www150.statcan.gc.ca/n1/pub/12-001-x/2022002/article/00002/01-eng.htm)

The reported census of all 14 eligible hard-short **test** families changes one possible interpretation. If the target is precisely that bounded dictionary inventory, the split and family weights are fixed, and every eligible family is included, there is no uncertainty from randomly omitting a hard-short family at a first sampling stage. That does not make the benchmark's total uncertainty zero: the selected coordinates do not census all licensed forms, provider responses can vary between runs, accepted-form coverage can be incomplete, and the broad component has a different selection design. No numerical finite-population correction is applied here. The 200 development responses cannot identify those separate uncertainty components. Cluster adjustments depend on the target population and sampling mechanism, not merely the presence of similar answers within a family. [Abadie, Athey, Imbens and Wooldridge](https://www.nber.org/papers/w24003)

Four questions must remain distinct:

- **Descriptive fixed-panel score:** once every response and grading decision is settled, its observed ratio is known. Calling its sampling error zero says nothing about repeatability or generalization.
- **A fresh coordinate sample from this finite inventory:** requires the actual selection design, inclusion probabilities or explicit modeling assumptions; a census of families is not a census of questions.
- **Repeated independent model runs on these exact questions:** requires repeated-query evidence or justified response-independence assumptions. One response per question does not establish run-to-run variance or stochastic stability.
- **New lexical families beyond the inventory:** requires a population/generalization assumption. Family bootstrap and sandwich estimates are relevant sensitivities, but do not prove independence between distinct dictionary citations.

The user's phrase “stddev <1%” does not by itself specify one of these targets, a standard error versus repeated-run standard deviation, absolute percentage points versus relative error, or a 95% interval half-width. It does **not necessarily demand unseen-root population generalization**. The project nevertheless froze a conservative requirement checking both iid and family SE. This audit preserves that requirement; it does not choose the smallest estimate after seeing results.

For orientation only, applying the two observed development proportions to N=1,800 gives iid SEs of 0.780 and 0.934 percentage points; fixing the cell rates gives 0.748 and 0.898. Those arithmetic illustrations ignore family dependence, changed class/tense composition, adaptive development selection and run-to-run variability. They cannot establish final precision. The final hard component has 14 families with 66–67 questions each, so scaling the development family SE by `sqrt(200/1800)` would be unjustified.

`audit.py` reproduces all calculations and fingerprints its explicit input files; `audit.json` records formulas, cells, covariance-preserving resampling and limitations. No live ledger, final response, paid service or frozen source was accessed or modified.
