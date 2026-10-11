The completed Astra comparison lost substantial concurrency to its **twenty sequential ten-question waves**. Its 200 requests took **70.19 minutes** while averaging **3.40 active requests** against an eight-worker limit (42.5% utilization). Request service time had a 47.39-second median and 405.35-second maximum. Total overhead between settled waves was only 0.80 seconds: the avoidable delay was waiting for slow requests before admitting the next wave, rather than preparation between waves.

Using only request-intent and HTTP-receipt timestamps, a fixed-input-order continuous queue gives these retrospective simulations:

| Continuous slots | Simulated minutes | Full outstanding Opus reservation | Full outstanding Astra reservation |
|---|---:|---:|---:|
| 8 | 32.38 | $10.533760 | $26.334400 |
| 16 | 18.24 | $21.067520 | $52.668800 |
| 32 | 11.49 | $42.135040 | $105.337600 |

The timing column uses the observed **Astra** request durations, held fixed; it is not an Opus forecast or a promised completion time. Provider rate limits, queueing and latency changes under greater concurrency remain unknown. The reservation columns include the entire **65,536-token output ceiling plus 1,500 input tokens per outstanding request**, using the existing direct standard-rate protocols.

At the audited ledger snapshot, lifetime committed spend is **Anthropic $311.430394 / $1,000**, and **OpenAI $801.130500 / $2,000**. Preserved reserves are $166.84 and $962.50 respectively. Thus unprotected headroom is $521.729606 and $236.369500. All listed windows fit without moving reserves: even 32 outstanding requests leave lifetime-plus-protection commitments at $520.405434 for Anthropic and $1,868.968100 for OpenAI.

The finished Opus pool has $125.682404 arithmetically unused of its $126.405120 ceiling; the finished Astra pool has $129.124570 unused of $150. Every listed window also fits those arithmetic remainders. **These are closed fixed-membership allowlists, not authorization to spend their unused balances on new questions.** Any future execution needs a new bound plan/pool; remaining capacity must be rechecked on every admission as actual spending and outstanding reservations change.

For future authorized work, first remove wave barriers with a persistent eight-slot queue; 16 or 32 slots can then be considered under an explicitly frozen concurrency policy. Use one coordinator with brief atomic reserve/settle transactions and network calls outside the ledger lock. The present `vp_goal.submit()` holds the shared nonblocking lock throughout network execution, so starting multiple unchanged executors would serialize or fail. Each admitted request or fixed small chunk must retain its full maximum until complete validated usage settles it; unknown submissions retain that maximum and are never replayed. Stop new admission when either the pool or lifetime ceiling, including protected reserves, would be exceeded.

Before using a new scheduler, test concurrent admission against both caps, crash recovery before/after POST, malformed/missing usage, no-replay behavior, concurrent ledger settlement, dependency changes and complete-cohort score visibility. Preserve fixed questions and the model/effort/output-cap protocol. Admission may respond to spending and operational failures, never to intermediate scores.

**No current execution needs acceleration: all actual evaluations are complete.** Do not change their frozen protocols or replay requests. A prospective final 64k evaluation still needs the separate test-split release/core-barrier integration. This audit neither selects final membership nor authorizes it.

`scheduling-audit.py` reproduces the timing-only calculations and current budget snapshot; `scheduling-audit.json` includes durations, file/code fingerprints and exact arithmetic. No Astra answer text or accuracy was used, and no paid call, ledger edit or scheduler implementation was made.
