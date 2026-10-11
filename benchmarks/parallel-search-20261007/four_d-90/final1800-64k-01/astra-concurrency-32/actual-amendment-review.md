# Actual checkpoint and amendment review

**Pass: no concrete blocker found.** Amendment SHA `d6b6bf83f5cbe8d79263bcd077f1e93bea0c0611a557aed0578d439e760303e0` binds checkpoint SHA `64ee186e45dd28b587b6a99cf60717c88f5a89180ca0745eb44c710cf4671c34` and the independently reviewed driver, tests, README and code-review receipt.

The old PID 51839 was absent. I acquired the original coordinator lock nonblocking during this read-only audit. The original STOP, drained execution metadata, exact ledger hash/digest, original plan and all 44 frozen dependencies match the checkpoint. No scheduling amendment had yet been adopted into the ledger.

| Provider | Validated settled prefix | Next index | Remaining fixed questions | Unknowns/failures |
|---|---:|---:|---:|---:|
| Anthropic | 0–1799: 1800 | 1800 | 0 | 0 |
| OpenAI | 0–644: 645 | 645 | 1155 | 0 |

All 2445 public request intents match the original frozen requests and digests. All 2445 intent hashes, raw HTTP receipt hashes and accounting-record hashes match the checkpoint and ledger. No unexpected receipt, intent or error file exists outside those exact prefixes. HTTP bytes were hashed without parsing their bodies; usage values come from the already validated settlement metadata. The reviewed prepare/settlement paths perform strict receipt identity and terminal-usage validation.

OpenAI's settled cohort cost is **$55.398690**. A fresh 32-request maximum window reserves **$105.337600**, bringing cohort liability to **$160.736290**. This leaves **$64.263710** in the unchanged $225 pool and **$75.633210** under the $2,000 lifetime cap after retaining $962.50 protected. Anthropic is complete at $22.370872, with its $100 pool, $1,000 lifetime cap and $166.84 protection unchanged.

Only the existing OpenAI account continues at 32 workers; no new jobs, replay, questions, protocol, source or scorer change is introduced. This point-in-time pass relies on the reviewed execute path rechecking the exact checkpoint under the coordinator lock and durably adopting the amendment before new reservations or POST. Slot-by-slot financial checks remain operative and may taper concurrency; completion within the fixed pool is not guaranteed.

[Machine-readable receipt](actual-amendment-review.json) includes exact hashes, counts and microdollar arithmetic. No API call, ledger mutation, final-answer parsing or score access occurred. The reviewed driver, tests, README, independent review, original plan and frozen dependencies remain unchanged.
