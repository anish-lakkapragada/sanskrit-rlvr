# Fixed-N release assessment after Opus06 and Astra04

The 5D difficulty calibration passes its frozen development screen: current policy15 gives Opus **478/598 all requests (79.93%)**, **478/594 usable answers (80.47%)**, and missing-response bounds **79.93–80.60%**. All118 original disagreements and four missing responses were reviewed. This supports advancing the grammar distribution; it does not establish final accuracy or sub1pp precision.

The remaining constraint is Astra precision and cost. Its paired current panel has **305/469 recorded-all correct**, **304/419 usable correct**, and50 truncations. One truncated response contains a correct parsed answer, which remains excluded from usable statistics. Opus is stronger on this identical panel. Astra's two-question family sandwichSE is2.59pp all and2.52pp usable. Observed coarse residual correlation is.336 for135 mixed aorist/non-aorist pairs and.171 for95 different-non-aorist pairs. There is **no Astra repeated-aorist pair**, so that dependence cannot be inferred from these data or borrowed from Opus.

A joint recipe×tense×voice cost forecast for the confirmed45%-aorist/10%-passive mix is **$0.24006 per question**, with a conditional family-bootstrap95% interval$0.22783–0.25240. It does not adjust the changed class or family composition. AtN4,800, forecast primary Astra cost is$1,152.31 and cumulative OpenAI spending is$1,865.34 using the coordinator's settled$713.027475. This leaves$134.66 at the point forecast before sensitivity work and other-track funds. At the cost interval's upper endpoint, remaining room is about$75.48. These are forecasts, not guarantees or spending authorization. AtN6,000, the point forecast exceeds the hard$2,000 lifetime cap by$153.41.

The complete input census supports both sizes without touching the462-family RL reserve. Policy15 changes neither test nor RL supply: its two new root predicates concern development families only. N4,800 can use932 families with at most8 forms and5 aorists per family; N6,000 can use972 families with caps10 and6. Every exact recipe/tense/voice cell has nine available person-number options. No final family or question identities have been exported or selected.

## Allocation sensitivity

All comparisons below preserve the **same42 recipe×tense×voice quotas and all ten class quotas**. Only the distribution of those tasks across eligible families changes. The block alternative is a bounded seeded heuristic, not a proof of the optimal allocation.

| N4,800 allocation | Families | Mixed-tense pairs | Repeated-aorist pairs | Different-non-aorist pairs |
|---|---:|---:|---:|---:|
| Balanced-load witness |932|4,181|3,714|4,682|
| Seeded95% aorist-block preference |932|2,085|3,938|6,890|

At assumed repeated-aorist correlation.20 and the observed Astra cross-tense point correlations, the block alternative's expected **unstratified family sandwichSE** is:

| Moment estimate | All requests | Usable answers |
|---|---:|---:|
| Exact-cell empirical |0.993pp|0.965pp|
| Coarse-cell empirical |1.004pp|0.987pp|
| Coarse-cell smoothed |1.006pp|1.000pp|
| Exact-cell smoothed |1.019pp|1.037pp|

The small cells have as few as two observations; smoothing is a sensitivity to their zero-variance estimates. At repeated-aorist correlation.30, all-request SE is1.031–1.057pp across these variants. The calculation includes observed completion loss and the allocation's family mean differences; it does not lower uncertainty by changing the final estimator. Bootstrap upper correlation scenarios are also saved and are less favorable. Reducing mixed pairs therefore helps some margins but does **not** establish a robust precision pass.

## Concrete decision proposal

The coordinator owns the existing **100-question-per-provider development output-cap sensitivity pool at128k**. This is not an added question or funding allowance. No paid calls or final exposure are performed by this worker.

**N4,800 is the largest assessed fundable candidate, with an explicit risk of missing the precision requirement.** Do not describe it as qualified or freeze its membership on a claim that sub1pp is already supported. The confirmed global grammar mix remains400/160/40 recipes per600 questions,45% Lun,10% passive, all ten classes and tenses. The current evidence supports two choices for the coordinator:

1. Resolve the most useful remaining development uncertainties before committing final membership: a bounded Astra higher-cap diagnostic and fresh same-family aorist pairs chosen by grammar and seed, not correctness. Recompute the remaining funding envelope after their actual costs settle. Such diagnostics cannot be treated as independent population accuracy or used to replace final answers.
2. Commit an explicitly at-risk fixedN4,800 after the funding review, accepting that the final analyzer may report failure of the sub1pp requirement. If using the new block allocation, a fresh Opus-only development confirmation is appropriate because within-cell family composition and repeated-tense selection differ from the passed two-distinct-tense panel. Its precision benefit is too uncertain to justify presenting the allocation change as harmless.

A fixedN commitment must precede all held-out answers. Freeze all question IDs, grammar cells, accepted unions, family IDs, order and stage membership. Use1,000 core questions, followed by fixed extensions totaling3,800 (seven500-question groups and one300-question group); smaller immutable transport subdivisions may control reservations. Settle core before extension. Every committed question is primary evaluation; no stopping, replacement or expansion based on observed accuracy or SE. If funding stops the run early, report incomplete evaluation rather than silently changingN.

Report all-request and usable scores, refusals, truncations, missing-response bounds, iidSE, family sandwichSE, and whole-family/class-stratified bootstrap intervals for **both** references. The strongest tested reference must meet the point79–81% target under the declared missing-response rule. Both models must satisfy both iid and sandwichSE<1pp under the unchanged final gate. A95% interval need not fit wholly inside the2pp target band. If the fixed run fails either accuracy or precision, retain and report that failure.

## Reproducible artifacts

- [Opus06 statistics](pilot-06.analysis-opus.json), [complete disagreement audit](pilot-06.disagreement-review.json), [policy15 source evidence](pilot-06.source-addendum-01.json)
- [Paired Opus/Astra04](pilot-04.analysis-opus-astra.json), [Astra cost/completion projection](pilot-04.astra-cost-precision-review.json), [dependence evidence](pilot-06.cross-panel-dependence.json)
- [Policy15 supply provenance](pilot-06.supply-policy15-addendum.json), [full current input census](pilot-06.scale-supply-policy15.json), [N4,800 witness](pilot-06.scale-witness-policy15-N4800.json), [N6,000 witness](pilot-06.scale-witness-policy15-N6000.json)
- [Allocation-specific variance](pilot-06.astra-allocation-variance.json), [block alternative](pilot-06.block-allocation-0_95.json), [all allocation comparisons](pilot-06.block-allocation-variance.json)

All new work is offline and development-only. Frozen tasks, provider answers, raw scores and generation-time hashes are unchanged. No final model answers were read and this worker made no paid calls.
