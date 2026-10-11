**Independent statistical review — candidate04, 7 October 2026.** No design-based justification has been established for replacing the existing family-sandwich gate with a smaller adjusted estimator. A prospectively specified cell/class-adjusted family sandwich is defensible as a **conditional, model-based sensitivity**, subject to substantive assumptions below. The unadjusted estimator is a useful conservative working diagnostic under those assumptions, not a universally exact or necessarily conservative estimator. **Keep the existing gates unchanged.**

This unpaid review used candidate inputs, the allocator, the frozen analyzer and existing dev04/06-derived forecasts. It read no pilot07 results or final model answers. Candidate task SHA256: `ef95605fd09227b61d197802454188cd9c095dbff16bbf18a68109970939a21a`. The input-only support audit is [saved separately](fixed-composition-variance-review-01.inputs.json).

The estimand must come first. Realized accuracy on the fixed 4,800 answered tasks is a descriptive number with no task-sampling uncertainty. Expected performance over repeated model calls on those inputs, performance over new lexical families at the same composition, and performance over reseeded allocations are distinct targets. Declaring the first target cannot establish precision for the latter targets. The importance of specifying the sampling or assignment source of uncertainty is the relevant principle from [Abadie et al., *When Should You Adjust Standard Errors for Clustering?*](https://arxiv.org/abs/1710.02926); their treatment-effect results do not themselves certify this benchmark.

For all-request success indicators \(Y_i\), \(N=4800\), \(G=929\), the current estimator is

\[
\widehat V_U=\frac{G}{G-1}\frac1{N^2}
\sum_g\left[\sum_{i\in g}(Y_i-\widehat p)\right]^2,
\qquad \widehat p=N^{-1}\sum_iY_i.
\]

Why adjustment could be legitimate: condition on the selected covariates \(X\), write \(\mu_i=E(Y_i\mid X)\), \(p_X=N^{-1}\sum_i\mu_i\), and \(M_g=\sum_{i\in g}(\mu_i-p_X)\). Then

\[
E\!\left[\sum_g\left\{\sum_{i\in g}(Y_i-p_X)\right\}^2\mid X\right]
=\sum_g\operatorname{Var}\!\left(\sum_{i\in g}Y_i\mid X\right)+\sum_gM_g^2.
\]

With conditionally uncorrelated families, the first term divided by \(N^2\) is the variance of the mean. The second includes fixed differences in family composition. Removing predictable composition effects can therefore be appropriate. This identity centers on the **true** \(p_X\); estimating the center adds finite-sample terms. The existing forecast labeled “expected unstratified sandwich” is an approximation, not an exact expectation of the fitted finite-sample statistic.

A concrete conditional specification would use 42 cell indicators plus nine gana contrasts, with an intercept in their span. Its 51 columns have full rank on candidate04. Under a suitable selected-sample mean model \(E(Y\mid X)=X\beta\), conditionally uncorrelated families and adequate cluster leverage, the cluster sandwich for \(\bar x'\widehat\beta\) is

\[
\bar x'(X'X)^{-1}\!\left[\sum_gX_g'\widehat e_g\widehat e_g'X_g\right]
(X'X)^{-1}\bar x
=N^{-2}\sum_g\left(\sum_{i\in g}\widehat e_i\right)^2
\]

before finite-sample correction. The point estimate remains the raw mean because OLS includes an intercept. Thus this is not a change to question weights. The relevant conditional-mean and between-cluster assumptions, and the need for adequate effective cluster support, are those of [Cameron and Miller, *A Practitioner’s Guide to Cluster-Robust Inference*, §II and §VI](https://faculty.econ.ucdavis.edu/faculty/cameron/research/Cameron_Miller_JHR_2015_February.pdf). “Robust” does not make conditioning or informative lexical selection harmless.

The actual allocation does **not** supply the missing design-based argument. It maximizes family coverage, minimizes repeated tenses, then minimizes squared family loads; seeded shuffles break optimization ties. This is not documented as uniform sampling of feasible panels or self-weighting probability sampling. Even treating the seed as random leaves unknown inclusion probabilities and joint inclusion probabilities, potentially unsupported population units, and dependence across families induced by exact quotas. A fixed chosen seed is reproducible, not itself a sampling law. Proper balanced probability sampling can reduce variance through known auxiliary totals, but requires the corresponding sampling assumptions; see [Deville and Tillé, *Variance approximation under balanced sampling*](https://www.sciencedirect.com/science/article/abs/pii/S0378375804000035). A generic finite-population correction based on 929 out of 1,000 reserved families is consequently unjustified. So is subtracting a dev-estimated composition variance from the observed gate statistic.

The following limitations prevent treating adjustment as an automatic precision gain:

- Exact margins fix the 42 cell counts and ten class counts, not every cell×class intersection. There are 270 occupied intersections, 64 represented by one family and 147 by fewer than five. Tanadi has only five families; Juhotyadi has eight. Fully crossed adjustment risks severe leverage and unstable mean estimates. An additive specification avoids that saturation but assumes away interactions in its mean model. Declare the specification and a leverage-aware correction, such as CR2, before outcomes; assess its assumptions rather than selecting the smallest SE.
- Keep each family intact across cells. Cell-wise independent bootstrapping loses within-family covariance. Class-stratified family resampling fixes family counts per class, not exact task quotas when loads differ. Family fixed effects would erase the variation being assessed and are unsuitable for this purpose.
- For usable-answer accuracy, let \(C_i\) indicate completion, \(U_i=C_iY_i\), and \(\widehat\theta=\sum U_i/\sum C_i\). Adjustment must preserve the joint ratio influence \((U_i-\widehat\theta C_i)/\bar C\), for example through joint numerator/denominator regressions and the delta method. Keep zero-completion families. Fixed input quotas do not fix completed quotas, and adjusting complete cases alone cannot recover missing answers.

Existing forecasts illustrate the uncertainty, not validation. At the assumed repeated-Lun correlation 0.20, dev-derived **smoothed** scenarios give:

| Mean scenario | Conditional all-request SE | Approximate unstratified SE |
| --- | ---: | ---: |
| Coarse | 0.985 pp | 1.036 pp |
| Fine | 1.007 pp | 1.043 pp |

These are from [the existing cost/variance assessment](../five_d/candidate-4800/revision-04/cost-variance-assessment.json), not adjusted SEs computed from candidate answers. The fine development cells can contain only two observations; repeated-Lun dependence at the candidate’s larger family loads is not identified by the earlier two-tense design. Neither scenario certifies sub-1-pp precision.

**Disposition:** no design-based replacement is presently supported. A predeclared additive adjustment may accompany the unchanged primary estimator as a conditional sensitivity, with its assumptions and support diagnostics stated. A stronger design-based claim would require an explicit target population and randomization law, inclusion-probability/variance justification or a validated approximation under the actual allocator; input-only reseeding alone cannot demonstrate outcome coverage. This review changes no release gate, policy, candidate membership or payment authorization.
