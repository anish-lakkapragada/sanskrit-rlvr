This is a separate, read-only mechanical reviewer for the exact frozen paired 1,800-question evaluation. It has **not** been run on the live results. Preparation and nine synthetic smoke tests used no final answers, provider calls, ledger writes or training. All 44 paid-run dependencies remain unchanged.

After both cohorts have settled and the primary analyzer has completed, invoke from the repository root:

```sh
.venv/bin/python benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/independent-review/review.py --review
```

The reviewer first verifies its own pinned code and the exact execution plan/dependencies. It checks usage-only accounting for both providers: each must have exactly 1,800 admitted and validated terminal records, full settlement and no operational failure. It then reads only the first four metadata values of `analysis.json`, refusing before any subsequent answer content unless the primary analysis reports the matching complete cohort. Missing, incomplete or differently bound analysis refuses. It never triggers the primary analyzer, collection, generation or reconciliation.

After these gates, it independently reproduces assistant-text extraction, single-answer-tag parsing, NFC matching, canonical matching and the finite whitelist. Thinking/reasoning content is ignored. Refusal, truncation, API failure and unparsed responses preserve the frozen contract. It checks all 3,600 exact task/request/intent/receipt identities, validated token costs, unique response IDs, raw receipt hashes, full question composition and public-prompt isolation from private gold/code/trace metadata.

It compares each independently extracted/scored response with both saved primary result layers, checks aggregate counts, paired transitions and score differences, and independently recomputes iid and unstratified family sandwich SEs. Zero-usable families remain in the completed-answer ratio variance. It does not rerun the primary family/class bootstraps or change their interpretation, and it does not install the separate development-only fixed-cell sensitivity as a new gate.

Outputs are written once under `completed-review/`:

- `review.json`: mechanical disposition, independent counts and SEs, immutable result fingerprints and explicit source-review limitations.
- `Anthropic-regraded.json` and `OpenAI-regraded.json`: independently extracted/status-classified/scored rows.
- Per-provider `*-source-adjudication-queue.json`: every unrecognized usable answer, with exact task, canonical union, finite aliases and receipt hash.
- `score-disagreements.json`: all discrepancies for investigation; none are silently patched.

A score disagreement produces `passed:false` and remains saved. An identity, hash or completion violation aborts before a completed review is written. Existing completed reviews are never overwritten. Canonical/finite recognition is not full Sanskrit certification; source adjudication is a separate next step, with symmetric corrections across affected questions and models. The reviewer never declares benchmark readiness.

The synthetic tests check both incomplete gates before answer access, completed-header isolation, malformed tags, canonical and alternate spellings, unfamiliar outputs, refusals/truncations/terminal failures, ignoring reasoning text, and analytic SEs including families with no usable response. Run them separately with:

```sh
.venv/bin/python benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/independent-review/test_review.py
```

`review-manifest.json` pins this reviewer, tests, documentation, the exact execution plan and unchanged shared dependencies. Do not edit the pinned files during review; any later correction needs an additive version and an explicit comparison with preserved artifacts.
