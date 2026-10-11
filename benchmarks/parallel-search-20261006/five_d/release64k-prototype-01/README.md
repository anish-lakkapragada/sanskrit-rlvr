This is an isolated, unpaid common-64k release-runner prototype. It has not been installed. No final N, real membership, reserve change, or evaluation is authorized by these files.

The [exact patch](migration.patch) applies only to the copied baseline in this directory. [53 offline regression checks](test-receipt.json) pass. The [round-trip receipt](patch-roundtrip.json) proves the patch reproduces every tested worktree file. The [isolation audit](isolation-audit.json) verifies 55 live source snapshots, all 21 pilot08 fingerprints, and the six post08 scenario dependencies. The live ledger changed through concurrent coordinator activity; this worker only hashed it and never parsed or modified it. No pilot08 results were read.

The implementation adds `hard_final_64k` and `hard_extension_64k`, both xhigh/65,536, sharing the original 1,000-core and 5,000-extension task allowances. Old phases, saved requests and provider caps remain unchanged. Every new job binds to the exact release manifest. An extension requires all exact 1,000 core questions for the same provider, release and protocol to be settled and collected. A core from another release or the old protocol cannot satisfy that barrier.

The staging tool accepts an explicit positive size vector, requires its ordered union to equal the full fixed cohort, and prohibits a payment chunk from crossing the 1,000-core boundary. The synthetic 4,800 test uses 70 stages per provider: five 200-question core stages, then ten 200, ten 100, ten 50, twenty-five 10 and ten 5-question extension stages. This vector is a test fixture, not a recommended or approved funding schedule. Existing budget gates use maximum reservations, and an unfunded fixed cohort remains incomplete. No accuracy or SE is consulted for staging or stopping.

Dependency, input, model, protocol and exact authorization hashes are checked before counting and again immediately before submission under the existing budget lock. The executor also refreshes checks after counting. The durable unknown-submission reservation and no-retry behavior survive simulated client initialization failure. Final-question replay protection spans old and new aliases while preserving paired providers and the existing sensitivity allowance.

The final analyzer refuses to read any result file until every stage for both references is settled and collected. Its full-N estimators and numerical gates are byte-unchanged. Runner collection/status, the report and the dashboard suppress partial scores through the new visibility adapter; cached score summaries are masked too. The generic development reader explicitly skips final or release-bound rows. Raw collected records stay intact. Collection necessarily parses responses to reconcile usage and grade records, but the analysis and visible-score boundary is held until the complete cohort.

Legacy prepared jobs without binding fields can resume through the legacy protocol without changing their metadata. New common64k jobs require binding, and already-bound legacy jobs must match their original release. Synthetic regressions cover both paths.

One existing preflight incompatibility was found: policy21's current `adapter_sha256` differs from its inherited `generator_sha256`. The isolated release tool prefers the adapter field, with the old field retained as fallback for older policies. No policy or live adapter was edited.

Remaining integration decisions:

- Complete and review all eight pilot08 jobs before deciding whether any final evaluation is justified. The prototype supplies no difficulty, precision, or funding qualification.
- Atomically register the new phase-policy aliases and prospective source hashes after the running experiment finishes. Preserve all legacy phases and attempted records. This prototype deliberately does not migrate the live ledger, registry, gate or monitor.
- Review and document any retirement or replacement of protected planning reserves separately. The prototype counts aliases against the old buckets once and retains their original planning rates. Those internal reserves are not proof that a 64k cohort is funded; hard $1,000/$2,000 provider caps remain fixed.
- Choose the real fixed N, full validated membership and transport vector before final answers. Install authorization for both the manifest SHA and exact stage digests only after that review. Old attempts consume the shared allowances; transport must never create an extra task allowance.
- Install the included report/dashboard changes together with the runner and reload any long-lived processes. Standard consumers are covered and tested here; any additional ad hoc reader of preserved raw `summary.json` or ledger data must still respect the same embargo.
- Review package/environment pinning and perform the real source/grammar regeneration audit. Synthetic freeze tests mock grammatical validation intentionally; they exercise operations, not Sanskrit validity. Actual SDK calls, network behavior, provider access and live registration were not exercised.

Reproduce the guarded offline checks from the repository root:

```sh
benchmarks/parallel-search-20261006/five_d/release64k-prototype-01/run-tests.sh
```

The test process blocks network, subprocesses, outside-directory writes, live ledger/results and credential reads, and disables provider clients. The exported production regression test includes compact canonical request hashes for all 18 legacy phase/provider combinations. The separate isolation test and harness are prototype-only. Baseline copies and earlier failing test logs are retained for review; live shared files are never patched by this command.
