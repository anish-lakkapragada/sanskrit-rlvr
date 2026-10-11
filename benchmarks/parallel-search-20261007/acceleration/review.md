# Independent financial and execution review — 2026-10-07 22:09 UTC

**Verdict: no critical blocker found in the reviewed direct-transport design.** The corrected reserve revision, shared locked runner and separate $100 spending pool can safely admit the first40-question wave while retaining all pending batch reservations. Completing600 questions is conditional on actual usage savings; $100 does not fund their theoretical maximum output cost. This review made no API calls, read no model outputs, and changed neither shared source nor ledger.

Reviewed source SHA256 values:

- `misc/vp_goal.py`: `c317278d15f3a05e3948e22678a346cc33a7274122f9ac5f66ed082e3373b65d`
- `misc/vp_simple_search_fast.py`: `43896351c1dc7b9c518518113f286de15268b90cb065c00e734be3e001605705`
- `misc/vp_simple_search_fast_analyze.py`: `433f30acd8ce0d62a788ad0954c3aeabcd11d3dd7d149d560e041e0c13618a1e`

## Verified financial baseline and correction

At review start, the authoritative ledger had Anthropic commitment **$694.549222**: settled campaign costs plus three pending200-question batch reservations of **$131.672 each**. Original Anthropic protected future allocations were hard_final1000, cap_check100 and bench_final0, costing **$295.14**. The bench_final reserve was previously *released*, not consumed by1000 final evaluations; the ledger has zero Anthropic bench_final attempts.

The implementation correctly preserves bench_final0 and hard_final1000, and changes only Anthropic cap_check100→0. This frees **$128.30** of internal planning protection and leaves **$166.84** protected. Lifetime caps remain **$1,000 Anthropic and $2,000 OpenAI**. OpenAI is untouched by this acceleration.

At the declared direct rates of $4/M input and $20/M output,1500 reserved input tokens plus65,536 maximum output tokens cost **$1.316720 per request**. Therefore:

| Quantity | Maximum or reserved amount |
|---|---:|
| One40-question direct wave | $52.668800 |
| All600 direct questions at maximum output | $790.032000 |
| Additional execution pool ceiling | $100.000000 |
| Headroom after corrected reserve revision, before direct work | $138.610778 |
| Commitment + protected reserve + first wave | $914.058022 |

The $100 pool is a limit on settled actual costs **plus full outstanding reservations**, with the next wave's maximum added before admission. It is not an estimate used to admit all600 at once. A later wave can proceed only after a complete terminal usage receipt releases sufficient savings. For example, a new40-question wave is admissible at a pool prior cost of $47.331200, but not $47.331201. If usage is too high, execution stops before all questions finish; that is correct budget behavior and must remain visibly incomplete.

Restoring bench_final1000 would have made protection $333.68 and caused the first wave to exceed the global cap. The reviewed implementation avoids that error.

## Fail-closed behavior inspected

The runner holds the existing shared ledger lock while checking the provider hard cap, protected allocation and new spending pool, and durably reserves the full wave before any paid POST. The pool sums settled upper costs or unsettled maxima; partial usage never releases an unknown request's reservation. The helper requires the exact pool provider, cap, job-ID list and plan hash at startup and between waves. Each prepared direct job also names its required spending pool, and the runner rejects a missing pool or membership mismatch.

I independently exercised nine gate cases using only copies of ledger state in memory: first-wave admission after the intended revision; rejection with original reserves; full accounting for an unsettled previous wave despite a tiny partial actual cost; exact-$100 admission; one-microdollar-over rejection; replay rejection; direct-final-phase rejection; provider-pool mismatch; and lifetime-cap rejection despite available pool space. All behaved as expected. These arithmetic tests first ran on the immediately preceding runner revision; the final reviewed revision additionally contains the required-pool guard. The coordinator separately reports22 offline runner tests, including that new guard; this review does not substitute that report for its own source inspection.

Direct calls retain SDK max_retries0, an eight-worker limit, a durable per-request intent, and a saved receipt. An attempted job with uncertain status stops the helper rather than issuing the same POST again. A complete local direct receipt can be collected without re-generation. Provider timeouts, missing usage or incomplete waves retain reservations. In a thread-pool failure, already queued calls may continue, but the entire40-question wave was reserved in advance; the helper submits no following wave.

The generic collector rejects duplicate and unknown custom IDs. Complete settlement requires the full request count, per-result usage, no token-policy violation and actual cost within the reservation. A cancellation response alone is never a reason to zero the original batch reservation. Canceled/missing-usage batches may consequently remain conservatively reserved until explicit reconciliation; this is safe, although it can restrict later spending.

## Fixed inputs, analysis and cancellation

The helper deterministically partitions the same three frozen200-question panels into15 waves of40, interleaving arms. It compares each direct request's complete parameters with the corresponding original batch parameters before reusing token counts; only custom IDs are relabeled. It preserves Opus5.5 xHigh,65,536 output tokens, prompts and all gold. Pool and source dependencies are hash checked. The final helper revision also checks that600 additional requests fit the shared development phase allowance before registration and binds the original coordinator registration and previous runner snapshot. Registration is permitted before any original completed outcomes are recorded; no per-question transport or membership selection follows correctness.

The analyzer requires full200-question creation coverage or both full200-question modification/control arms. It validates direct protocol and exact original task slices, and the shared statistics function checks complete task dictionaries and duplicate membership. The source-based paired199 sensitivity remains separate. Incomplete direct runs are reported as waiting, with no substitution from original batch outcomes. The new `opus-fast-simple4d` name avoids accidental inclusion in older partial-result selectors.

I originally recommended cancellation after the first entire40-question direct wave had settled successfully, based solely on transport—not correctness. The coordinator chose the more conservative implemented rule: **cancel unfinished original batches only after all600 replacement questions have settled**. That rule preserves fallback longer and is acceptable within the budget because both transports remain fully accounted. It can incur duplicate batch charges, already included in commitment. Original results remain archived separately; the uniformly declared direct panel is authoritative, rather than choosing the favorable transport for each question.

A crash during registration or preparation can leave partial local artifacts, but subsequent checks fail before spending unless the plan, pool, registry, token counts and task hashes agree. Such a stop requires read-only diagnosis and explicit local reconciliation; it does not authorize restarting an uncertain paid request.

## Practical conclusion

Launching the reviewed first direct wave is consistent with the stated caps and corrected reserves. Preserve the $100 pool, all existing reservations and the full-panel analysis barrier. Do not promise that600 maximum-length requests fit $100 or declare the benchmark finished merely because this operational acceleration succeeds.
