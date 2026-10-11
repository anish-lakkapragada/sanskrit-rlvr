# Repeat-run standard deviation is a different precision question

Prepared 2026-10-07 Pacific before reading any final model answers. This is a prospective mathematical note, not a new qualification rule or a measured final result. The current conservative root-generalization gate remains unchanged, and the user's intended meaning of “stddev <1%” remains unconfirmed.

For a fixed benchmark, the standard deviation across repeated model runs can be smaller than uncertainty about performance on new verbal roots. A root that consistently confuses a model contributes a systematic mistake on this panel; it need not make repeated scores fluctuate. Resampling roots asks how much the score might change if the panel's lexical composition changed.

Assume a fixed model and fixed grading rule, with independent fresh calls across questions and stable correctness probabilities p_i. Let S be the fraction correct on the same N questions in a new run, and let p̄ be their average correctness probability. Then

```
Var(S) = sum_i p_i(1-p_i) / N²
       = [p̄(1-p̄) - mean_i (p_i-p̄)²] / N
       <= p̄(1-p̄) / N.
```

The probabilities may differ by question. This calculation does not assume that two questions from the same verbal root have the same difficulty. It does assume independent stochastic outcomes conditional on the fixed model and tasks. Shared provider drift, correlated randomness, changing prompts or a changing grading policy can invalidate that interpretation.

A one-sided Hoeffding bound gives a conservative lower confidence limit on p̄ from one fixed-panel run: L = max(0, observed_fraction_correct − sqrt(log(1/α)/(2N))). This concentration bound permits independent, non-identically distributed bounded variables. [CMU probability lecture, Hoeffding inequality](https://www.stat.cmu.edu/~larry/=stat700/Lecture5.pdf), [Isabelle's formal Hoeffding theory](https://isabelle.in.tum.de/library/HOL/HOL-Probability/Hoeffding.html).

For L > 0.5, the largest p̄(1-p̄) over p̄ ∈ [L,1] is L(1−L). Therefore sqrt(L(1−L)/N) is a one-sided upper confidence bound on fixed-panel repeat-run SD under these assumptions. If L ≤ 0.5, use 1/(2sqrt(N)). This application and the following numbers are derived here from the stated inequality; the cited sources do not analyze this benchmark.

At N = 1,800, allocating α = 0.025 to each of the two reference models gives at least 95% simultaneous coverage by a union bound; independence between the two models is unnecessary. **At least 1,434 known-correct answers per model (79.667%) is sufficient for this conditional SD upper bound to be strictly below one percentage point.** This is a prospective numerical threshold, not the unseen final count. If a final panel happened to repeat the development rates of 87.5% and 80.5%, the respective upper bounds would be 0.858 pp and 0.987 pp. These are illustrations, not final measurements or empirical rerun SDs.

The coverage is frequentist: over repetitions satisfying the stated fixed-panel assumptions, the two upper bounds jointly cover the two fixed SD parameters at least 95% of the time. It is **not** a 95% probability conditional on observing counts that pass the threshold, or a posterior probability that these assumptions or SD claims are true. Here “conditional” refers to the modeling assumptions and fixed panel, not to conditioning coverage on a favorable observed result.

For missing responses, counting only verified correct answers in the full denominator supplies a conservative lower-bound statistic, provided each missing item has a well-defined latent binary correctness outcome under the stated model. The observed known-correct fraction can only be lower than the full hypothetical fraction, so the one-sided concentration argument remains conservative. This does not create a response, settle unknown billing, turn an outage into a grammatical error, or bypass the separate source-review requirement. If correctness or the latent response is undefined, do not apply this claim to it.

This missingness argument bounds the repeat SD of the **latent complete model-answer score**. It does not automatically bound the operational score obtained when future missing responses count as zero: shared outages or other correlated delivery failures can add covariance even if the latent model answers are independent. Independence and stability of the model calls, a valid latent coupling, and the grading assumptions have not been established by this calculation or by a single panel.

The coverage statement is for these two prespecified references, this fixed panel and this fixed scoring rule. It is not an anytime guarantee after repeated optional testing, a confidence bound on the maximum over an adaptively selected collection of models, or validation of answer-key correctness. No score-based task changes are permitted. Source changes must be documented and assessed separately rather than silently presenting this as a bound for every scoring variant.

This could address a repeat-run interpretation of the requested precision, subject to its assumptions and independent review. It does **not** establish below-one-point precision for generalization to unseen roots, negate the 14-family concentration in the difficult component, demonstrate robustness to provider drift, or change the currently adopted benchmark gate. No extra model calls were made. [Reproducible calculation and exact small-distribution checks](audit.py), [illustrative numeric output](audit.json).
