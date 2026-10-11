# Independent pre-outcome request audit

**Pass: all 200 saved canonical requests match the same 200 Opus task prompts exactly, with no extra model-visible fields or gold leakage.** The twenty ten-question stages are an ordered, disjoint, complete partition of the frozen source panel. All 200 task IDs and prompts are unique; the panel retains its original 109 families and all four-coordinate distributions.

Frozen plan SHA256: `14bdcb0f9dce2d456850f733502c3d3512c44180abf3978ad38f68b046fd9af5`. The ledger spending pool exactly matches that plan hash, its twenty fixed job IDs and **$150 OpenAI cap**. Protected allocations remain as declared. Every frozen plan dependency hash matches.

I compared each request against both the original saved Opus request and the corresponding completed direct-transport Opus request, reading **request artifacts only**. Astra uses the identical single user message. It retains `gpt-6-astra`, standard/xhigh reasoning, a 65,536-token ceiling, empty tools, no tool choice, no storage/streaming and disabled truncation. Provider-specific protocol fields are explicit; no hidden system message, prior answer, attachment or additional task metadata is present.

Each prompt also regenerates exactly from only the public dhatu citation, class and meaning plus lakara/prayoga/purusha/vacana. The test omits private dictionary code, task ID, gold, traces and campaign metadata from that rendering input. Thus the match does not depend on a string search that could confuse legitimate Sanskrit stem text with leaked answers.

All twenty saved input-count receipts cover precisely their ten request IDs and match the request digest. Across the full panel, counted input ranges from **259 to 277 tokens**, below the 1,300 counted-input gate and 1,500 billed-input reservation allowance.

At this bounded snapshot, **ten effective SDK request files** were present. All ten preserve the canonical body exactly and add only the declared `service_tier=default`; effective-body and canonical-request digests match, as do the pre-POST intent digests. Later effective requests were not awaited. Their validation remains the frozen executor/analyzer's responsibility.

Machine-readable count proofs, per-file fingerprints, stage checks and the ten effective-request receipts are recorded in `request-review.json`; the offline reproducer is `request-review.py`. No HTTP response file, result JSON, answer text or accuracy was opened. No API call, ledger write, frozen-source edit or membership change was made. This is an input/protocol integrity pass, not a completion, accuracy or grammatical-certification claim.
