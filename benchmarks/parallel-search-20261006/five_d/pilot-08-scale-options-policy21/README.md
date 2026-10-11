# Policy 21 allocation options: 3,000–4,800 questions

**Aggregate input-only options, not final membership or authorization. No N is selected.** The three new allocations and the preserved 4,800 witness are feasible under the same 56% yaN→Ric / 24% yaNluk→Ric / 20% san, 45% Lun, 10% passive composition, all ten classes and all ten lakaras. Recipe-by-voice and every lakara total remain exact scaled copies of pilot 08 revision 02.

| N | Families | Actual max family load | Sum of squared loads | Families with Lun | Lun assignments beyond first/family | Σm²/N − 1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3,000 | 949 | 5 | 10,866 | 707 | 643 | 2.622000 |
| 3,600 | 971 | 6 | 15,640 | 761 | 859 | 3.344444 |
| 4,200 | 971 | 7 | 21,252 | 815 | 1,075 | 4.060000 |
| 4,800 | 971 | 8 | 27,646 | 869 | 1,291 | 4.759583 |

All options retain the configured caps of eight questions and five aorists per family, at most one question in each other lakara, and unique person-number combinations per family. An integral matching verifies global PN counts differing by at most one, with exactly equal person and number margins. The observed maximum aorist load is five at every N.

At N=3,000, the proportionally rounded Curadi margin is 181 questions for 203 eligible Curadi families. Consequently 949 is the class-quota upper bound and the attained maximum; 22 Curadi families are omitted. Every other eligible family is covered. N=3,600 and above cover all 971 eligible families. No class margin was changed to repair the smaller option's coverage shortfall.

## Within-family pair structure

| N | Lun–Lun pairs | Lun–other pairs | Other–other pairs | Nonzero joint-cell pair types |
| ---: | ---: | ---: | ---: | ---: |
| 3,000 | 931 | 1,932 | 1,070 | 497 |
| 3,600 | 1,520 | 2,897 | 1,603 | 510 |
| 4,200 | 2,203 | 3,837 | 2,486 | 525 |
| 4,800 | 2,869 | 4,864 | 3,690 | 559 |

Each allocation JSON contains all unordered recipe×lakara×voice cell-pair counts and recipe-pair totals. The same-tense pairs are exclusively Lun. The repeated-Lun pairs remain confined to the two intensive recipes; there are no san-containing repeated-Lun pairs. Input counts show which pair types would have support if evaluated, but estimate no covariance themselves. Pair counts are dependent comparisons, not additional independent observations. Different seeded optima can have different pair structure even when the three allocation objectives coincide.

## Exact rounding and allocation procedure

The targets are rational multiples N/2400 of the fixed pilot 08 plan. Floor/ceiling rounding of joint cells is constrained by an integral bipartite flow to preserve exact recipe×voice margins and all ten lakara totals. Fractional-edge insertion uses SHA256 ties from `vp-five-d-pilot08-scale-options-policy21-v1`. At N=3,000 and N=4,200, exactly 12 joint cells differ from their ideal by ±0.5 question, with total absolute deviation six questions; all other cells are exact. N=3,600 and N=4,800 have no joint-cell rounding. The largest joint deviation is 0.016667 percentage points at N=3,000.

Class margins use largest remainder with the same named seed and a separate class tag. Only Bhvadi and Curadi need rounding: N=3,000 has Bhvadi 1,919 (+0.25), Curadi 181 (−0.25); N=3,600 has Bhvadi 2,303 (+0.5), Curadi 217 (−0.5); N=4,200 has Bhvadi 2,686 (−0.25), Curadi 254 (+0.25). At N=4,800, all margins are exact. Every ideal, integer target, signed fractional difference and percentage-point difference appears in the respective rounding JSON.

After rounding, the existing allocation algorithm maximizes distinct families, then minimizes repeated family-lakara assignments, then minimizes squared family loads. The same integer priority costs, cap settings, input-only seed format and no-block-preference rule are used. The existing helper accepts 2,400-unit weights, so the new driver passes an equivalent normalized plan and asserts that its rounding restores every already-fixed integer quota exactly. No frozen/shared implementation was changed. Allocation seed format remains `vp-five-d-pilot08-aggregate-witness:san20_lun45_fullcoverage:test:N`.

## Scope and limits

The unchanged policy 21 supply contains 271,719 eligible exact tuples from 971 test families, with source controls and unresolved roots excluded. The current task-input histories in both campaign ledgers have zero matching eligible tuples or families. RL families are separate. Legacy 6,687-item analysis inspected all dictionary families, so these are not globally unseen roots. The policy 21 SAN/7.4.7 mask removal is inherited through the checked current census and its saved proof.

These outputs contain aggregate counts, not selected question IDs, forms, prompts, or family membership. A later fixed candidate requires full regeneration and renewed scope/novelty checks. The 4,800 allocation was read as an unchanged comparator, not rerun or overwritten. The new scenarios are independently optimized; they are not nested prefixes of that witness or of each other.

Smaller N reduces paid questions and pair dependence but also reduces observations and changes family weights. N=3,000 additionally changes lexical composition by omitting some Curadi families. Thus constant global grammar proportions do not establish constant accuracy, cost or covariance. The stored common-rho examples use hypothetical p and rho values only; they are not forecasts from pilot 08. Completion losses, class/recipe differences, unequal variances and separate repeated-Lun/mixed/non-Lun correlations require the full development evidence. Both iid and family-sandwich SE still must be below 1 percentage point for both models; feasibility proves neither precision nor the 79–81% accuracy target.

All eight pilot 08 jobs must settle before its aggregate is read. Any final N, membership, protocol and funding decision must occur before final answers; these options authorize no adaptive stopping on final scores.

[Summary](summary.json), [provenance manifest](manifest.json), [supply/input-history check](supply-audit.json), and [independent arithmetic/fingerprint verification](verification.json) accompany `N3000`, `N3600`, and `N4200` allocation/rounding files. The [unchanged N4800 witness](../pilot-08-scale-policy21/N4800.allocation.json) remains authoritative for that comparator. Reusable input-only driver: `misc/vp_5d_scale_options_policy21.py`.

## Prospective use of the complete calibration

The [post08 scenario declaration](post08-scenarios-predeclaration.json) freezes a common comparison of all four sizes before pilot08 scores are read. It reports empirical and smoothed moments, coarse and exact grammar cells, both covariance centerings and explicit correlation sensitivities for both models. Unsupported cells and incoherent covariance assumptions remain visible. Conditional costs are shown separately; no N is automatically selected. Seven synthetic tests cover the complete-cohort read guard, missing support, response-state accounting, exact family-mean/covariance arithmetic and invalid correlations.

A read-only watcher will run `misc.vp_5d_scale_after08` once the full frozen aggregate exists. It makes no API calls, changes no reserve and produces no final membership. Its [operational state](post08-scenarios-watch.json) is separate from the experiment and benchmark qualification.

The [independent mathematical review](../../four_d/post08-scale-review-01/review.md) found no blocking calculation or read-guard defect. Interpret projected SE as a conditional plug-in/asymptotic second-moment forecast, not the exact expectation of a realized sample-centered SE. Multiplying a bootstrap mean-cost interval by N gives uncertainty about the transported expected total, not a predictive95% interval for the realized API bill. Only the locked maximum reservations enforce the spending caps.
