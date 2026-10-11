# Astra240 paired subset: independent preselection review

**Disposition:** a prospectively frozen 240-question subset is useful for measuring common-65,536-cap cost, missingness and previously unmeasured Astra repeated-Lun dependence. It cannot by itself establish the final precision target or make the full evaluation financially guaranteed. Preserve the existing advancement and final precision gates. Exact membership is still being prepared; this memo approves no paid call.

The parent proposal is 2,400 questions, recipe shares 56/24/20, 45% Lun and 10% passive. Its class margins include Bhvādi1,535 and Curādi145. The paired subset is to be selected using inputs only, before any Opus08 or Astra08 outcomes. Both providers must answer identical task/prompt/gold records at the same stated effort and 65,536-token cap; provider outputs remain separate observations.

## Concrete selection checks

1. Freeze the parent2,400 input hash, policy19/adapter hashes, exact subset240 hash, seed, objective/tie-breaks, full ordered IDs and transport chunks before exposure. Verify 240 unique IDs, exact parent-task equality and prompt identity, current source eligibility, development-family membership and previous exact-input novelty. Family reuse from prior development is explicitly acknowledged; new tuples are not new independent families. No test/RL family or final model answer may enter the diagnostic.
2. Preserve Lun108, passive24 and approximately recipe134/58/48 when feasible, but audit the actual joint support rather than treating those three margins as sufficient. Record all42 recipe×tense×voice cells and class×recipe×Lun/non-Lun intersections; flag every parent-positive subset-zero cell and its parent weight. All ten tenses/classes should be represented where the input panel permits it. Tiny class cells support controls, not class-specific inference.
3. Do not use the provisional54×(2L+1N)+21×3N+15Curādi-singleton layout unchanged. Its first blocks already exhaust108 Lun, forcing every Curādi singleton to non-Lun. If parent08 contains Curādi Lun, that is an avoidable missing stratum. First allocate Curādi singletons over their parent Lun/non-Lun mixture, then choose feasible repeated-Lun and non-Lun blocks. Raman agreed to revise this arithmetic. Curādi parent families have one task each, so the subset cannot manufacture a Curādi covariance pair.
4. Record unordered within-family pair counts separately for LL, LN and NN, **and the number of contributing families**. Split LL support by unordered recipe pair, same/different citation, and class. Compare the subset's pair-type distribution with the parent and proposed final input allocation. A large aggregate pair count can conceal absent same-recipe intensive-luk or desiderative support. Preserve different person/number coordinates; never count duplicate IDs as pairs.
5. Record family load, Lun load, non-Lun tense diversity, family task weights and parent-family eligibility for the chosen block shape. Report selected versus available families. Selecting only families with two Lun plus a non-Lun record conditions on this support and can miss other family types. A fixed seeded constrained optimum is reproducible; it is not automatically uniform or self-weighting probability sampling.
6. Predeclare what happens if 240 input-only matching cannot satisfy every desired quota. Relax secondary pair-block counts before dropping scientifically relevant support. Record every relaxation before answers; do not replace refused, truncated, expensive or incorrect tasks after exposure. No score-based transport stop or optional continuation is introduced by the subset.

## What to estimate

Report separately for Astra and for the identical paired Opus subset: all-request accuracy, usable-answer accuracy, completion/refusal/truncation rates, observed charged input/output cost, token distribution and family-cluster uncertainty. Pair provider differences by exact task, retaining the same family clusters. The full Opus2,400 can inform its own mixture estimate; an Astra result on240 is not an interchangeable denominator.

For conditional forecasting with independent families, the final mean's variance has the form

\[
V(\bar Y\mid X)=N^{-2}\left[\sum_i V(Y_i\mid X)+2\sum_g\sum_{i<j\in g}\operatorname{Cov}(Y_i,Y_j\mid X)\right].
\]

This makes **pair weighting** explicit. An equal-family LL estimate and an estimate weighted by all candidate LL pairs answer different questions when family loads differ. Preserve both descriptively and use the target input pair counts for any forecast. A single portable correlation assumed across recipes/classes/load types is a modeling assumption, not something50 pairs verify.

For a prespecified pair stratum \(s\), residuals \(e_i=Y_i-\widehat\mu(X_i)\) give the descriptive pair moment

\[
\widehat\gamma_s=\frac{\sum_g\sum_{(i,j)\in P_{gs}}w_{gij}e_i e_j}
 {\sum_g\sum_{(i,j)\in P_{gs}}w_{gij}}.
\]

Freeze weighting and mean adjustment before outcomes. A coarse recipe×Lun/non-Lun×voice adjustment is a reasonable sensitivity; fully crossed42-cell×class fits are too sparse at240. Keep raw and adjusted diagnostics, and do not choose the smaller estimate. If estimating the mean model from this panel, fit it with families kept intact, preferably with prespecified family cross-fitting; re-estimate it inside whole-family resampling and disclose small-cell fallback rules. Cross-fitting avoids training a family's own mean on its outcomes, but is not a proof of unbiased covariance or valid coverage.

Resample **entire selected family blocks**, retaining every pair and both provider outputs, with the prespecified broad sampling strata where feasible. Multiple LL/LN/NN pairs from one family are not independent replications. Report bootstrap valid-replicate counts, intervals, boundary/zero-variance behavior and leave-one-family sensitivity. A one-family class cannot support its own nonparametric bootstrap variance. Do not erase between-family variation with family fixed effects.

For usable-answer accuracy, use the joint ratio influence, not correctness conditional on both responses completing. Let \(A_i\) be all-request success, \(C_i\) usable completion and \(\theta=\sum A_i/\sum C_i\). The relevant influence is

\[
\phi_i=(A_i-\theta C_i)/\bar C.
\]

Measure LL/LN/NN covariance for \(A\), \(C\), and \(\phi\), keeping families with no usable answer. Missingness clustered within a root can materially affect the ratio. If there are no observed missing responses, report that fact and the inability to estimate missingness covariance; a degenerate bootstrap interval is not proof of perfect completion.

Cost should use all billed outcomes, including refusals and capped responses, at the actual common64k protocol. Report the raw subset mean and a prospectively specified standardized/raked estimate for the parent mixture, with effective sample size and maximum weights. Unknown inclusion probabilities and family-block selection mean such extrapolation is **conditional/model-based**: it assumes within-cell transportability from selected families. Missing positive-weight cells require an explicitly pooled model or a stated unsupported component; they cannot silently be assigned zero cost/risk. Neither the old16k panels nor the59 eligible128k diagnostic cases should be pooled as though they used64k. They can provide separately labeled sensitivities.

## Precision and funding limitations

Even the favorable toy model of54 independent equal-mean Bernoulli pairs is imprecise. At known marginal accuracy0.8 and correlation0.2, the standardized product \(Z=(Y_1-.8)(Y_2-.8)/.16\) has variance1.41. Thus the mean-product estimator's standard error is \(\sqrt{1.41/54}=0.162\); the normal-approximation half-width is about0.317. This is an analytic illustration with known means, not a promised interval for the actual heterogeneous design. Estimating means, sparse strata and selection can alter it further. Roughly50 LL families can expose severe dependence; they cannot tightly establish that a correlation is below0.20 or certify a final SE below1pp.

With the existing arithmetic, a120-question Astra chunk has maximum reservation$197.508 at65,536, and240 has total maximum$395.016. The proposed$50–55 expected diagnostic cost is a scenario, not a guarantee. The actual diagnostic spend reduces the same lifetimeOpenAI budget available for the final evaluation. The unchanged funding gate must use settled cost plus all outstanding/unknown maxima. Any final cost forecast must include diagnostic expenditure and tail uncertainty; observed average affordability is not guaranteed full-run funding.

The distinction between sampling/design uncertainty and clustering is explained by [Abadie, Athey, Imbens and Wooldridge](https://arxiv.org/abs/1710.02926). Cluster-robust methods rely on between-cluster independence and sufficient cluster information; see [Cameron and Miller](https://doi.org/10.3368/jhr.50.2.317). These general results do not certify the campaign's constrained allocator or make a selected development subset a probability sample.

Once membership is ready, the independent audit will verify the concrete checks above, regenerate the subset under policy19, and compare newly appearing recipe/rule contexts with prior input panels. It will not read pilot08 outcomes or expand into an exhaustive grammar search.
