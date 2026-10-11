# Independent offline preflight — Astra exact-4D comparison

Review date: 2026-10-07. This is an offline review of the existing runner and ledger snapshot, before review of the coordinator's new execution plan. No requests, input-count calls, shared-source edits, registry or ledger writes were made. It is not execution authorization.

**The existing runner can support the identical 200-question development comparison under unchanged xhigh/65,536 settings, but a $100 pool with ten mandatory 20-question stages does not guarantee completion. The new coordinator must address or explicitly bound the receipt/pricing limitations below.**

## Verified protocol and budget

Read-only ledger SHA256 at review: `3b3d32e2ae01b28fc495d7017e5be132d194517b22d20cbcb1ff35d355322d8f`.

| Quantity | USD |
|---|---:|
| OpenAI lifetime committed | 780.255070 |
| OpenAI protected planning allocation remaining | 962.500000 |
| OpenAI hard cap | 2,000.000000 |
| Available beyond existing commitments and protection | 257.244930 |
| Proposed additional pool | 100.000000 |
| One 20-question maximum reservation | 65.836000 |
| Anthropic lifetime committed, unaffected | 310.707678 |

The current combined OpenAI confirmation allowance has 18,480 unattempted question slots left. No planning reserve change is necessary for a bounded $100 additional commitment.

`vp_goal.rates` correctly doubles its recorded batch rates for direct transport: $10/M input and $50/M output under the ledger's standard-price assumption. The reservation is `(1500 × 10 + 65536 × 50)/1e6 = $3.2918` per question. Cached input is charged at the full input rate in the upper-cost calculation, which is conservative at that assumed tier. Output accounting uses total output tokens, including reasoning, rather than visible answer length.

Offline request construction and validation preserve the original task/prompt, model `gpt-6-astra`, xhigh reasoning, maximum 65,536 output tokens, one user input, empty tools, `tool_choice=none`, no storage, no streaming and disabled input truncation. The input-count gate requires all exact request IDs, a matching request digest and a maximum count of 1,300, below the 1,500 billed-input allowance. No input counts were requested during this review.

## Concrete findings for the new executor

1. **Fixed 20-question stages can strand a funded cohort.** The pool sums settled upper costs and outstanding full reservations. It permits the next $65.836 stage only when prior pool commitment is at most $34.164. I exercised `budget_gate` on detached synthetic ledger copies: $34.164 passes and $34.164001 fails. Thus a projected full cost below $100 is insufficient to ensure ten such stages can run. A prospective transport taper may split later fixed membership into smaller consecutive pieces, with no score-based choice. The per-question maximum is unchanged, and even a one-question stage needs $3.2918 of remaining pool headroom. Alternatively keep ten stages, but explicitly declare possible financial incompletion and never report a partial cohort as the full comparison. This is a transport constraint, not grounds to alter membership or reuse results.

2. **Standard pricing is assumed, not pinned in the request.** Current OpenAI request bodies omit `service_tier`. Existing saved Astra batch receipts inspected for usage have `service_tier=default`, but that does not prove the new direct project's inherited tier. The frozen runner does not check the returned tier. A nonstandard higher-cost tier could invalidate its upper-cost estimate. Before spending, establish the new requests' standard-tier contract from existing account evidence or use an explicitly versioned isolated execution path that records/pins it; do not silently mutate the saved request body after validation. Before releasing reservation, require an acceptable returned tier and halt for reconciliation otherwise. Receipt inspection detects a mismatch after the fact; it does not retroactively make the first stage's assumed maximum safe.

3. **The shared settlement predicate is weaker than a complete usage receipt.** `finish_job` currently accepts any truthy usage dictionary and treats absent input/output counts as zero. It does not require integer, nonnegative `input_tokens` and `output_tokens`, check their sum against `total_tokens`, or validate tier/model/terminal response ID. The new executor can inspect all 20 saved raw receipts before invoking collection, keeping the existing full reservation if any count is absent/invalid, tier/model is unexpected or response is nonterminal. Require exact task/custom-ID coverage and distinct response IDs. Cached/reasoning detail must be consistent where present; cache writes or allowance breaches already trigger the shared halt. Checking only `job.settled` after collection would be too late to prevent weak-receipt settlement.

4. **Duplicate prevention works by fixed job identity, not arbitrary new development names.** Existing SDK construction sets `max_retries=0`; direct execution preserves that when extending timeout to 600 seconds. The durable job reservation and `attempted_at` precede all billable work. Each request writes an intent digest before the single POST. Unknown outcomes retain the whole stage reservation and the same job cannot be replayed. The shared cross-job duplicate guard applies to final phases, so this development executor must enforce its frozen stage IDs, exact disjoint partition and resume behavior itself. Never re-create failed stages under new IDs. A completed transport with an uncollected receipt can be collected without a new generation; unknown submission must be reconciled manually.

5. **Unknown failure stops advancement after the admitted stage quiesces.** The runner submits all stage futures to an eight-worker pool. If one future raises, already queued work may still execute while the context manager waits. The entire stage is already reserved, so this does not escape its maximum; it does mean “stop on error” is not an immediate cancellation of every remaining task in that stage. No next stage may start. Keep every intent and receipt, and do not release partial unknown reservations.

6. **Per-stage manifest verification belongs in the new wrapper.** The runner rechecks saved task/request digests, registered renderer fingerprints, input counts, split and regeneration before each submission. It does not independently bind this new 200-question comparison plan and all wrapper dependencies. The wrapper should freshly verify the exact pool, plan/dependency/source-panel hashes and the union/disjointness of all stage membership before each count/submission/collection step. Source/rendering hashes must remain unchanged. Keep a process lock to prevent two wrappers from advancing the same plan.

## Meaningful preflight checks

The isolated coordinator tests should reject a changed task/prompt or stage union, a removed/mutated spending pool, a resumed attempted stage, an unknown receipt, missing/negative/noninteger usage, an unexpected tier, and a changed dependency. Test the exact $34.164 pool boundary and any declared transport taper. Test full-cohort-only comparison against the same 200 Opus target questions, with source exclusions applied symmetrically and original raw records retained. No model score may change stage membership, stopping or retry behavior.

Until the coordinator plan is reviewed, this note identifies runner capabilities and integration requirements only. All prices here are the existing ledger's recorded standard-rate assumption, not a new live pricing verification.

## Coordinator's prospective response (not yet code-reviewed)

The coordinator proposes 20 stages of ten fixed questions, a $150 pool (or $100 if demonstrably sufficient), and an isolated cloned runner/client wrapper. The wrapper will add only `service_tier=default` to the effective SDK parameters, persist their exact digest before POST, and reject incomplete billing receipts before the shared collector can release reservations. Canonical model-input fields and all prior frozen runner files will remain unchanged.

This design addresses the principal gaps if implemented as described. The client wrapper must survive the runner's `with_options(timeout=600)` call and preserve zero retries. A terminal `incomplete` response with valid usage is a legitimate truncation outcome, not permission to retry; nonterminal/unknown outcomes retain reservations. Unexpected/malformed receipts should still be saved for reconciliation while withholding the per-request `.result.json` needed by collection.

A ten-question stage reserves $32.918, so the preceding pool-spend threshold is $67.082 for a $100 pool or $117.082 for a $150 pool. Both pool maxima fit the current $257.244930 unprotected OpenAI headroom, without changing reserves or the $2,000 cap. I tested all three proposed stage/pool combinations at zero, exact threshold and one microdollar above threshold: nine detached synthetic gate cases pass, saved in `preflight-budget-checks.json`. This demonstrates accounting boundaries, not a guarantee that all 200 questions fit either pool at realized usage. Revised executor code and effective-request receipt tests remain to be reviewed before a code-level pass is issued.

## Code-level disposition after revised executor review

**Bounded pass: no concrete blocking error found in the revised isolated executor/analyzer.** Reviewed `misc/vp_simple_astra_compare.py` SHA256 `07a2c778f154237061bfdb77b932b57a5dbab60054f1e4e7713b0c561c3e7774` and `misc/vp_simple_astra_analyze.py` SHA256 `96a9c65b1f9f1c0b06018c40e657a681e83d69462617db85dbc6a116936c39d2`. This disposition supersedes the pending-code-review language above for exactly these versions.

The implementation fixes twenty ordered ten-question stages and a $150 additional pool. It pins standard/default pricing in a separately persisted effective request, retaining unchanged canonical model input and the old shared runner. It validates integer input/output/total tokens, total equality, cached/reasoning-token bounds, model, response identity, terminal status and service tier before emitting a collectable per-request result. Invalid receipts are preserved for review and retain the stage reservation. Legitimate incomplete or failed terminal outcomes with valid usage remain outcomes; they do not trigger a paid retry.

The isolated clone prevents replacing the live shared runner's client. `with_options` retains the wrapper, and the effective request is fsynced through the existing atomic writer before the fake SDK observes it. Canonical request objects remain unchanged. The executor rechecks dependency and pool/source/stage fingerprints as it advances; its process lock and fixed job IDs preserve resume/no-replay behavior. The analyzer waits for all twenty stages to settle and collect, checks exact full-panel and effective-request membership, and compares against all 200 matching direct Opus rows.

Five offline fixture tests passed, including 18 negative receipt subcases and all four allowed terminal statuses. The fake SDK tests cover pre-POST durability, wrapper persistence, the single default-tier augmentation, rejection of replay after success or malformed receipt, preservation of invalid response evidence without a `.result.json`, and unknown/duplicate input rejection. Test source and versioned hashes are in `test_preflight_adapter.py` and `preflight-adapter-test-receipt.json`. These tests use temporary files and fake SDK objects only; they never instantiate a provider client or mutate the actual ledger.

Residual limits are operational rather than new blockers: the complete 200-question worst-case cost is $658.36, so the $150 ceiling may stop the fixed cohort; a ten-question stage needs $32.918 remaining pool headroom. A timeout/unknown response halts advancement without replay. All in-stage futures can quiesce after an error under the already reserved maximum. The successful preflight makes no claim about model accuracy, live service availability or final benchmark qualification.
