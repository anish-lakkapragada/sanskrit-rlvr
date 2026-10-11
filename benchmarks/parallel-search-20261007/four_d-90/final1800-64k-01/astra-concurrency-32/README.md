# Scheduling amendment: 32 OpenAI workers

This additive driver continues the original final1800 run at OpenAI32 / Anthropic0 after a graceful drain. It changes scheduling only. The original 44 dependencies, request bodies, question order, two aggregate accounts, 64K xhigh protocol, canonical/alias scoring, source policy, analyzer, $100/$225 run pools, $1,000/$2,000 lifetime caps and protected reserves stay unchanged.

The original `misc/vp_continuous64k.Accounting` class is reused unchanged with the original execution-plan SHA and a deep-copied plan whose only differing field is runtime concurrency. New requests retain the original receipts directory and index. No new jobs, retries, answer scoring or Anthropic client are introduced.

## Parent-controlled activation

1. Independently review `resume.py` and `test_resume.py`. Save `independent-review.json` with `passed: true`, `driver_sha256`, `tests_sha256`, `execution_plan_sha256`, and review limitations. The implementation author does not approve or launch it.
2. Have the original coordinator observe its original `STOP`, gracefully drain admitted calls, and release the existing `coordinator.lock`. Keep that STOP as history. Confirm its execution state is `stopped_incomplete` (or already complete), every admitted request is settled, Anthropic is complete, and neither account has `operational_failure`.
3. Run `python <this-directory>/resume.py prepare`. This takes the same coordinator lock and performs ledger/API read-only checks. It writes only additive `checkpoint.json` and `amendment.json`, refusing to overwrite either. The checkpoint embeds original drained execution metadata, original STOP hash, complete settled account prefix, every intent/receipt/account hash, original plan/dependencies, exact ledger hash and all unrelated ledger state. It verifies raw usage and identities without extracting or scoring answers.
4. Inspect those concrete artifacts. Run `python <this-directory>/resume.py execute` only when ready. It reacquires the same coordinator lock, rejects unknown requests or any changed checkpoint, verifies every settled receipt, and appends/fsyncs a single exact hash-bound amendment to the shared ledger before admitting the first new request. The amendment pins this code, tests, README, independent review, checkpoint and original plan. It never re-registers jobs.

The only paid entry point is `execute`. Neither command is invoked by these tests or by merely importing the file. Both default to this existing run and overlay directory; explicit directory arguments exist for isolated tests.

Every POST rechecks all original dependency hashes plus the code/review/checkpoint/amendment/STOP bindings and durable ledger amendment/reservation. An exclusive intent write prevents replay. Requests use timeout600 and max_retries0. Errors preserve the original maximum reservation and halt further admissions; active requests drain. A later process refuses to restart while any admitted request is unknown or any operational failure exists, even if a raw HTTP file survived. Reconciliation is never automatic replay.

Use **this directory's `STOP`** for the new scheduler. The original STOP remains unchanged and is hash-checked. A completed or budget-limited settled restart with the same amendment is idempotent and only admits the unseen suffix. A local STOP remains effective on restart; archive/removal to resume after an intentional local stop requires explicit parent handling. Checkpoint and amendment are never rewritten. Original drained execution metadata survives embedded in the checkpoint when live `execution.json` updates with `runtime_concurrency`, amendment path/SHA and `execution_driver`.

At most32 unresolved OpenAI reservations cost $105.3376 ($3.2918 each). Admission always checks settled actual costs plus full outstanding maxima against the $225 run pool and $2,000 lifetime cap plus unchanged protected reserves. When a capacity check fails while calls are active, the scheduler waits for settlement and retries admission. With no active calls and insufficient room for one full reservation it exits `budget_limited_incomplete`; it does not lower token limits or change questions. Completing all questions remains conditional on actual usage fitting those fixed caps.

The unchanged paired analyzer still waits for both complete1800 cohorts. No partial outcome scores are calculated here. Receipt validation checks usage, request identity and billing tier, not correctness or exhaustive Sanskrit variants.

## Offline verification

`python <this-directory>/test_resume.py` uses temporary ledgers, synthetic receipts and a fake SDK only. It checks exact prefix/cost bindings, graceful drain and lock gates, unknown/failure rejection, tamper rejection, idempotent adoption and restart,32 concurrent reservations/workers, exact cap refusal, continuous budget taper, separate STOP behavior, no retries, amendment/reservation/intent before POST, and compatibility with the original Accounting/analyzer gate. Tests patch the real manifest inspector only for synthetic small fixtures; the live driver calls the full original inspector and preserves every original dependency.
