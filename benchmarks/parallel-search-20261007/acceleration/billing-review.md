# Independent terminal-batch billing review — 2026-10-07 22:17 UTC

**Verdict: no critical blocker found for the three original batches, under the existing collector's receipt/state invariants.** The proposed reconciliation can release an unused reservation after complete terminal receipts establish the actual bill. A cancellation request, cancellation intent or processing summary alone is insufficient.

Final reviewed helper: `misc/vp_simple_search_fast_reconcile.py`, SHA256 `dc4cce634e60459e3bb686aec67f66f98a9a05e7e5bd0d390d95373459903639`. The initial two-positive/seventeen-negative test pass used the preceding `07c2158ef67a330143e95fe0f246522f3f99c416f41db8fb13a8f78cc536f96e` revision; the terminal-identity addendum below covers the final change. This review used helper/collector source, public provider documentation and synthetic data only. It made no provider API calls, read no actual model outcomes and changed neither ledger nor shared source. The helper itself was not executed in reconciliation mode.

## Primary billing evidence

Anthropic's [retrieving batch results documentation](https://platform.claude.com/docs/en/build-with-claude/batch-processing#retrieving-batch-results), checked2026-10-07, explicitly classifies `errored`, `canceled` and `expired` requests as unbilled. Successful requests include their generated message. The same page's [pricing section](https://platform.claude.com/docs/en/build-with-claude/batch-processing#pricing) lists Opus5.5 batch prices of $2/M input tokens and $10/M output tokens, matching the runner's rates. This supports zero cost for those precise non-success result types after terminal receipt verification; it does not support assuming an entire canceled batch is free.

## What the helper correctly requires

`reconcile()` is restricted to the three original named batches imported from the frozen acceleration helper. It holds the existing shared ledger lock, verifies frozen requests through the established runner and reads the original collected results. It skips already-settled jobs, non-ended jobs and jobs lacking collection evidence.

`audited_cost()` requires Anthropic batch transport, ended status and collection. Every expected custom ID must have exactly one raw result receipt, and the complete receipt count must equal the job size. Unknown result types and duplicate/missing IDs fail. Nonbillable results carrying a conflicting nonempty message fail.

Each successful receipt must provide nonnegative integer input/output counts; booleans are rejected. Input/output maxima, cache creation and cache reads are checked. The independent sum uses batch rates and must match the collector's recorded actual upper cost, remain within the reserved maximum and have no recorded token-policy violations. Terminal aggregate counts must match all observed result types, with processing zero. Thus neither an unbilled count estimate nor partial success usage can silently release the remaining reservation.

The helper writes a reconciliation receipt containing the raw-result file hash, source URL and per-type counts before marking the job settled under the lock. It leaves requests, responses, grades and actual cost unchanged. It does not submit, cancel, retry or modify an answer; it also does not clear a halted runner state. The only financial transition is from the original outstanding maximum to an independently checked collected bill.

## Independent pure checks

I exercised a synthetic complete200-request batch containing8 successful receipts and64 each of errored, canceled and expired. Successful usage was100 input plus500 output tokens each, giving a total **41,600 microdollars ($0.041600)**. Both original and shuffled receipt orders were accepted with the same cost.

Seventeen negative checks all rejected as expected:

- Missing and duplicate receipts; unknown result type.
- Nonterminal status, still-processing count and aggregate count disagreement.
- Missing, Boolean or negative successful token usage.
- Cache creation, cache reads, input overrun and output overrun.
- A nonbillable result with a conflicting message.
- Disagreement with collected actual cost, exceeding reservation and an existing token-policy violation.

These tests did not inspect live ledger records or actual outputs, and did not invoke the mutating reconciliation function.

## Terminal identity hardening — implemented and checked

The initial helper trusted `job.status == ended`, relying on the existing collector to persist that status with the corresponding provider batch. The coordinator implemented the suggested additional guard in this new unfrozen helper: the stored provider batch must also have `processing_status == ended`, its ID must equal the nonempty `job.batch_id`, and ordinary membership/cost checks still apply. I independently reran the synthetic mixed200-request case: it accepted the same41,600-microdollar cost. Both a mismatched batch ID and a provider batch still marked `canceling` were rejected. These three addendum checks used the final helper hash printed above. The running frozen executor, runner and analysis files were unchanged.

The result JSON contains raw receipts embedded by the existing collector. This review assumes those collector-produced artifacts have not been manually substituted; it does not independently redownload provider billing evidence. The additive reconciliation receipt preserves their exact hash for subsequent audit.

**Recommendation:** once originals are terminal and fully collected, apply this helper under the shared lock. Keep reservations intact for any case it rejects. Archive the originals separately from the authoritative complete direct panels, as already declared.
