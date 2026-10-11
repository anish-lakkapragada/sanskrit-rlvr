# VP creation campaign — 6 October 2026

**Outcome: stopped at the discovery feasibility gate. Neither final benchmark
was created.** All 6,000 Opus High / 4,096-token discovery tasks completed:
5,750 correct (95.83%), with zero truncated answers. Usage-based cost was
**$23.072126 Anthropic and $0 OpenAI**. There are no active campaign jobs.
See the [recorded outcome](outcome.json) and [execution verification](execution-verification.json).

Within the searched construction predicates, even relaxed discovery thresholds
of 70% / 50% did not yield both scalable tiers. Requiring at least 50 development
families per construction left no Hard pool. The tentative VP-Bench union had
540 possible tasks under the two-per-family limit, but its tense distribution
reduced the optimistic bound to 41 under the planned 30% per-tense cap. These
are search-specific upper bounds, not proof that all creation benchmarks fail.
Calibration, Astra screening and final evaluation gates are explicitly closed;
the runner rejects further paid submissions while this campaign is halted.

Authorized new API-credit limits: **$1,000 Anthropic and $2,000 OpenAI**.
The frozen [policy](policy.json) targets 1,000 unique tasks per benchmark
(minimum 500), with each reference model below 70% on VP-Bench and below 50%
on VP-Bench-Hard. These targets are hypotheses, not achieved scores.

The [ledger](ledger.json) records paid submission attempts, provider batch IDs,
full token-cost reservations, and collected usage. Reservations persist after
completion; savings do not automatically authorize additional calls. Generation
retries are disabled. A submission with an unknown outcome is never replayed.
`misc/vp_campaign.py` hard-codes the approved caps and phase request limits,
checks exact request hashes, counts inputs with the selected provider, and
reserves future calibration and final-evaluation allowances before spending.

The score-independent [family split](family-split.json) reserves 1,000 citation
and class groups for testing, 700 for discovery/calibration, and 462 for future
RL training. Existing checkpoints are not certified free of these test families;
a clean RL comparison requires a new learner under this split. Historical
exploration of the full pool is disclosed. Reserved-family historical answers
are excluded from new construction fitting.

Local generation enumerates the existing creation format on development and
test families. All impersonal tasks are excluded to avoid the two known audit
clusters. Candidate generation is not independent linguistic certification.
Construction semantics, spelling variants and gold keys need review before
fresh calibration and final membership. See [discovery audit](discovery-audit.json).

Discovery lists contain 6,000 new task IDs in three batches of 2,000. Each batch
includes 1,000 failure analogues, 500 unusual rule combinations and 500 controls.
Historical absent answers and nasal-only spelling differences are excluded as
difficulty signals. Each batch must pass review before the next is submitted.

Commands, from the repository root:

```sh
.venv/bin/python misc/vp_campaign.py status
.venv/bin/python misc/vp_campaign.py collect --job opus-discovery-01
.venv/bin/python misc/build_benchmark_report.py
```

Collection retrieves existing work; it never generates answers. Only the
explicit `submit` command spends inference credits. All raw request payloads,
token-count receipts, batch receipts and responses are retained under `jobs/`.
Final lists are not selected from final model failures. If creation-only
discovery cannot support both tiers, the campaign must record that outcome and
stop before the protected final spend.
