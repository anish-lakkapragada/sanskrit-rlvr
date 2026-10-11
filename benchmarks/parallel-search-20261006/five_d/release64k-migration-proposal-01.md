# Proposed 64k final-release migration — not operative

A fixed 4,800-question evaluation at common xhigh/65,536 is operationally possible only through smaller payment chunks and an explicit revision of internal reserves. This memo changes no code, ledger, frozen dependency or authorization. Implement only after all eight pilot 08 jobs settle and the coordinator releases and reviews their full aggregate. The policy 21 supply witness establishes input feasibility, not target accuracy, precision, final N or funding.

**Two present blockers are mechanical.** `vp_cartesian_release.freeze` always emits one 1,000-question core job. At 64k its worst-case reservation is $658.36 Anthropic/$1,645.90 OpenAI. OpenAI already has $727.478150 settled, leaving only $1,272.521850 before pending confirmation costs. Even with no other reserve, that single core job cannot fit. Likewise, replacing the old core protection with 1,000 protected 64k questions would require the same unaffordable $1,645.90: splitting requests alone would not fix it.

The existing partition auditor already supports several core stages. The small change is to let the freezer accept an explicit immutable stage-size vector and a versioned protocol. Keep the first 1,000 questions as the core tier and require all of that provider's core questions to settle and collect before its extensions. Check the core against the same release/protocol; an unrelated old 16k core cannot satisfy the new barrier. Final membership and total N remain fixed before any test answers.

## Actual budget snapshot

At 2026-10-07T12:38:33 UTC, using budget metadata only:

| Provider | Settled lifetime | Outstanding maximum | Current protected reserve | Uncommitted after both |
| --- | ---: | ---: | ---: | ---: |
| Anthropic | $246.194768 | $263.344000 | $295.140000 | $195.321232 |
| OpenAI | $727.478150 | $197.508000 | $962.500000 | $112.513850 |

These are live-experiment figures, not a final funding forecast. More confirmation work is unsubmitted. Preserved revoked registrations are not additional pending payment obligations. Refresh the snapshot after all 08 settlements; do not borrow outstanding reservations or assume unsubmitted work is free. No pilot 08 answers, scores or completion outcomes were read.

The hard cumulative caps remain $1,000 Anthropic/$2,000 OpenAI. Current batch accounting reserves 1,500 input tokens per question and enforces counted inputs ≤1,300. At 64k, maximum reservation per question is $0.65836/$1.64590 respectively. Every attempted POST, including an unknown submission, retains its full reservation until terminal usage settles.

## Versioned phases and reserves

Add `hard_final_64k` and `hard_extension_64k` rather than modifying old phase tuples. They share the existing `hard_final` 1,000-question and `hard_extension` 5,000-question allowances per provider; they create no extra task allowance. Keep all old 16k/128k request bodies, request hashes, phase names, usage checks and results immutable. `confirm`/`confirm_64k` continue sharing 20,000 and both sensitivity phases continue sharing 100 questions.

New aliases must enter all final-phase, test-split, release-gate and replay checks. Count attempted questions across old/new aliases, including unknown POSTs. A same-provider rerun cannot bypass the replay guard by changing its phase or job name. A paired provider remains allowed. A new common 64k primary cannot silently reuse old 16k answers.

One explicit reserve option after release approval is to set both obsolete core planning floors to zero for each provider while retaining the sensitivity floor of 100 questions. Anthropic's old 4D floor is already zero. This would retire $166.84 of Anthropic core protection and $834.20 of OpenAI core protection, leaving $128.30 future sensitivity protection for each provider at this snapshot. Every actual 64k payment chunk still reserves its full maximum before POST. This is a replacement planning allocation, not a refund or increased cap, and does not guarantee all 4,800 questions will complete.

The coordinator must record the rationale and before/after allocation under the existing reserve-revision mechanism. Releasing OpenAI's old 4D reserve also requires an explicit plan for the other requested benchmark; it must not silently imply that objective is complete. If later justified, unused sensitivity protection could separately be retired by setting its floor to 0 for Anthropic or 60 for OpenAI, releasing another $128.30 each. The 100-question sensitivity allowance and the already paid 60 OpenAI questions remain unchanged. This optional release is not the default recommendation.

Do not add a duplicate protected bucket for the new aliases. Retaining old core protection and adding full new 64k core protection would block execution. Update the ledger's locked phase-policy fingerprint and the documented planning allocation atomically only after the current confirmation finishes.

## Illustrative fixed transport schedule

The following fixed taper uses the same stage files for both models and preserves all 4,800 questions. It is a proposal, not a frozen schedule or membership.

| Tier / position | Chunks × questions | Cumulative N | Anthropic maximum per chunk | OpenAI maximum per chunk |
| --- | ---: | ---: | ---: | ---: |
| Core | 5 × 200 | 1,000 | $131.672 | $329.180 |
| Early extension | 10 × 200 | 3,000 | $131.672 | $329.180 |
| Middle extension | 10 × 100 | 4,000 | $65.836 | $164.590 |
| Later extension | 10 × 50 | 4,500 | $32.918 | $82.295 |
| Tail | 25 × 10 | 4,750 | $6.5836 | $16.4590 |
| Last tail | 10 × 5 | 4,800 | $3.2918 | $8.2295 |

That is 70 stages per provider, 140 jobs total. Smaller late chunks avoid stranding affordable questions behind a large worst-case reservation. They do not lower the output cap, trim N or make worst-case total funding possible: 4,800 ceiling-length outputs would cost $3,160.128/$7,900.32 before historical spending. Actual settled savings are necessary.

The gate remains `committed + next_chunk_maximum + other_protected ≤ provider_cap`. If expected post-evaluation headroom after other protection is H and a hypothetical average task cost is c, a final chunk of k fits only if `k × (maximum_task_cost − c) ≤ H`. This is an arithmetic sensitivity, not an estimate from current 08 outcomes. If even the next frozen small chunk cannot fit after all pending usage settles, report an incomplete fixed evaluation. Do not reduce N, omit expensive cells, change membership or stop because accuracy/SE appears satisfactory.

The current release executor can pipeline multiple pending stages when the maximum-reservation gate permits; it is not strictly sequential per provider. Retaining that budget-bounded behavior reduces latency. A stricter in-flight cap can be predeclared if desired. The many small stages may require multiple bounded execution windows; resume with the same manifest, prefix, IDs and already attempted jobs, never replay an unknown POST.

## Minimal implementation and verification

- `vp_goal.py`: versioned final aliases, shared allowance cohorts, same-release core proof, canonical planning-reserve accounting, final/replay registration and unchanged durable maximum reservations.
- `vp_cartesian_release.py`: explicit protocol selector and frozen stage-size vector. Its existing ordered-partition invariant stays: exactly the first 1,000 core, then 3,800 extension, with identical metadata and no duplicates or omissions.
- `vp_cartesian_release_run.py`: protocol-aware partition audit and a fresh dependency/authorization check before each new paid action. Preserve financial waits, safe resume and unknown-submission halt.
- Final analyzer and visibility consumers: require every stage for both providers to settle before opening results. The current final analyzer reads settled partial stages and labels them incomplete; that would expose interim metrics. Hide correctness in collector stdout, status, report and monitor too. Continue showing budget, counts and operational failures.
- Coordinator registration: freeze all ordered tasks, source/prompt/policy hashes, model/cap protocol, sampling plan, stages, numerical gates and analysis dependencies before installing the release authorization. No estimator or stopping rule changes are proposed.

Regression checks should establish byte-identical legacy requests; shared 1,000/5,000 limits across aliases; the exact 1,000 settled-core barrier; the 70-stage ordered partition; integer budget arithmetic under the real-spend fixture; documented reserve changes without cap changes; unknown-POST/full-reservation behavior; locked concurrent budget checks; replay rejection across aliases; no result-file reads before all 140 stages settle; and idempotent resume/fingerprint rejection. Extend the existing financial, partition, execution and final-analysis test suites. Proposed changes and tests have not been implemented here; only source review and offline arithmetic were performed.

The [machine-readable proposal](release64k-migration-proposal-01.json) records exact stage sizes, phase mappings, source hashes, checks and the [budget snapshot](release64k-operational-budget-snapshot.json). No final N, membership or payment is authorized.
