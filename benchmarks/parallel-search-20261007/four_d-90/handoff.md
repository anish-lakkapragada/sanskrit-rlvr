# Exact 4D bounded challenge pilot — 2026-10-07

The 200-question panel is ready for the coordinator's independent validation and budget-controlled submission. No worker model calls were made. Its purpose is to test whether the remaining grammatical lead survives the fair xHigh / 65,536-token setting and can give a simple 4D benchmark below 90%. It does not seek either superseded two-benchmark target.

- Frozen tasks SHA256: `63b7f801151bc5ea15678519f54a19da37e6940641c0cde1b08104f33ab2906c`.
- `plan.json`: exact membership rationale, protocol, quotas, forecast and predeclared decision.
- `manifest.json`, `dependency-supplement.json`: frozen file hashes, imported source dependencies, original dictionary, family split, current policy21, and historical novelty inputs.
- `audit.json`: 200 unique prompts and tuples, 109 families, zero historical-visible-tuple overlap, complete regeneration and policy/local scope checks.
- `source-controls.json`: 48 passing controls reproduced from the earlier primary-source audits. These representative controls plus rule inference are not independent certification of every complete paradigm.
- `experiment-request.json`: coordinator submission specification. Conservative 1,500-input-token reservation assumption gives $131.672 maximum for Opus batch; coordinator must compute the actual reservation and maintain the shared cap.

The mixture is 104 non-aorist short-penultimate adanta Curadi tasks, 16 other-adanta Curadi aorists and 80 broad non-Curadi controls. Every one of the 13 eligible short-adanta development families appears exactly eight times in eight distinct non-aorist tenses. Every one of the 16 other eligible adanta aorist families appears once, and each broad-control family appears once. The source-uncertain sUca aorist and all current shared/local exclusions remain excluded uniformly. Selection never uses individual correctness.

All ten tenses and all ten classes appear. Curadi supplies 60%; Lun supplies 12%. The remaining 40% spans all nine other classes; tiny Juhotyadi and Tanadi each have only two families. All questions are Kartari to avoid unresolved passive meaning conditions. Person and number each have 66/67 examples per category. Class or tense representation is not a claim of uniform Sanskrit coverage.

The transported point prediction is 87.49%, using the old 31/39 short-adanta non-aorist rate, the more tentative exploratory 10/13 other-adanta aorist rate, and 100% for the broad controls. This is a conditional planning calculation from small 16k cells, not a measured forecast at 64k. The pilot includes all grammar-eligible hard families, including families without known previous errors.

The serious limitation is family supply: the short-adanta predicate has only 13 development, 14 test and nine RL-training families. Keeping its 52% share in a 1,000-question test would require about 37 examples per eligible test family. This is a meaningful transfer-learning and uncertainty bottleneck; 1,000 strings are not 1,000 independent roots. Historic original-corpus inspection also predates the current split, so the reserved test families are not historically untouched lexical roots.

After complete results exist, run `.venv/bin/python misc/vp_4d_90_analyze01.py RESULTS_JSON`. The analyzer requires the exact 200 frozen task dictionaries, reports all-request and usable accuracy, refusal/truncation bounds, iid and unstratified family-sandwich SE, a fixed-seed family bootstrap, and cell/tense/class breakdowns. It preserves the raw score and reports any subsequent policy exclusions separately. The numerical exploration screen requires both scores strictly below 90% and usable errors in at least five families; source-supported interpretation remains pending a bounded review. This is not final qualification, a strongest-model claim, or sub-one-percentage-point precision evidence.
