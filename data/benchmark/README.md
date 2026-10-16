# Benchmark tasks and evaluation costs

The benchmark contains **20,000 tasks**: 5,000 from each of the four families.
Every subset uses seed **69**, samples without replacement, and preserves
complete source JSON rows and accepted answer sets. Subanta and tinanta
balance valid grammatical cells; krdanta and taddhitanta preserve source
suffix proportions, subject to integer rounding.

## Subanta benchmark

[subanta/subanta.json](subanta/subanta.json) contains 5,000 distinct source rows sampled without
replacement from `data/datasets/subanta/full.json`, using random seed **69**.
The 24 case × number cells receive 208 rows each, with one extra row in eight
randomly selected cells: 16 × 208 + 8 × 209 = 5,000. Genders are pooled within
each cell. IDs, grammatical inputs, and every accepted answer are preserved.

[subanta/subanta.manifest.json](subanta/subanta.manifest.json) records the seed, per-cell counts,
source/output hashes, and source row indices in exported order. Reproduce with:

```bash
python3 data/engine/subanta/export_benchmark.py
```

## Tinanta benchmark

[tinanta/tinanta.json](tinanta/tinanta.json) contains 5,000 distinct source rows sampled
without replacement from `data/datasets/tinanta/full.json`, using random seed
**69**. Each of the ten tenses/moods has nine active cells, nine passive cells,
and one impersonal cell (third-person singular), giving **190 valid cells**.
Each receives 26 rows, with one extra in 60 randomly selected cells:
130 × 26 + 60 × 27 = 5,000. Roots are sampled uniformly within each cell.
IDs, grammatical inputs, and every accepted answer are preserved.

[tinanta/tinanta.manifest.json](tinanta/tinanta.manifest.json) records the seed, per-cell counts,
source/output hashes, and source row indices in exported order. Reproduce with:

```bash
python3 data/engine/tinanta/export_benchmark.py
```

## Krdanta benchmark

[krdanta/krdanta.json](krdanta/krdanta.json) contains 5,000 distinct source rows
sampled without replacement from `data/datasets/krdanta/full.json`, using random
seed **69**. Each of the 14 suffixes receives its proportional share of the
27,470 eligible source tasks. Quotas are rounded down, then the remaining slots
go to the largest fractional remainders; ties follow source-manifest suffix
order. Tasks are sampled uniformly within each suffix, then shuffled together.
IDs, grammatical inputs, and every accepted answer are preserved.

| Suffix | Source tasks | Benchmark tasks |
| --- | ---: | ---: |
| `kta` | 2,229 | 406 |
| `ktavatu` | 2,229 | 406 |
| `tfc` | 2,227 | 405 |
| `Rvul` | 2,229 | 406 |
| `tumun` | 2,227 | 405 |
| `ktvA` | 2,227 | 405 |
| `tavya` | 2,227 | 405 |
| `tavyat` | 2,227 | 405 |
| `anIyar` | 2,229 | 406 |
| `yat` | 752 | 137 |
| `Ryat` | 1,615 | 294 |
| `lyuw` | 2,229 | 406 |
| `Satf` | 1,722 | 314 |
| `SAnac` | 1,101 | 200 |
| **Total** | **27,470** | **5,000** |

[krdanta/krdanta.manifest.json](krdanta/krdanta.manifest.json) records the quotas,
seed, source/output hashes, and source row indices in exported order. Reproduce with:

```bash
python3 data/engine/krdanta/export_benchmark.py
```

## Taddhitanta benchmark

[taddhitanta/taddhitanta.json](taddhitanta/taddhitanta.json) contains 5,000 distinct
source rows sampled without replacement from
`data/datasets/taddhitanta/full.json`, using random seed **69**. Each suffix
receives its proportional share of the 3,342,776 eligible source tasks.
Quotas are rounded down, then the remaining slots go to the largest fractional
remainders; ties follow source-manifest suffix order. Tasks are sampled
uniformly within each suffix, then shuffled together. IDs, grammatical inputs,
and every accepted answer are preserved.

All 175 suffixes were attempted during source generation, and 129 have tasks
in the full dataset. The proportional benchmark covers **51 suffixes**;
78 nonempty groups receive zero samples after rounding, while 46 suffixes
have no source tasks. No minimum quota is imposed on rare suffixes. The sample
contains **4,763 distinct stem spellings** and **4,857 stem–gender inputs**.

[taddhitanta/taddhitanta.manifest.json](taddhitanta/taddhitanta.manifest.json)
records all 175 suffix populations and quotas, including zeros, along with
the seed, coverage, source/output hashes, and source row indices in exported
order. Reproduce with:

```bash
python3 data/engine/taddhitanta/export_benchmark.py
```

## Astra evaluation scaffold

[results/astra-xhigh/](results/astra-xhigh/README.md) contains the planned
20,000-task Astra xHigh run manifest, exact input/template hashes, result
compact JSON schema, scoring rules, and four request/response journals. The
runner is `data/engine/evaluation/run_astra.py`; its manifest tracks progress,
costs and run status. Its four result
files will be `tinanta.json`, `taddhitanta.json`, `krdanta.json`, and `subanta.json`.

## Evaluation cost calculator

Open [pricing.html](pricing.html) directly in a browser. It is a standalone HTML
file with inline JavaScript, no CSS, no external dependencies, and no API calls.

Use the four sliders or exact-count inputs to choose tasks per model, and the
six checkboxes to choose models. OpenAI defaults to a $3,000 budget; Anthropic
defaults to $1,500. Costs assume one response per task per selected model at
xHigh, without an additional benchmark output cap. Provider output limits
still apply. The page offers separate provider totals, a breakdown by task,
Batch pricing, output-usage multipliers, and equal-count budget fitting.

The current baseline is the 200-request answer-only pilot: 25 tasks from each
family sent to both GPT-6 Astra and Opus 5.5. The calculator uses separate
provider-reported input and output averages for those two measured models.
Sol and Luna use Astra's token usage as an explicit proxy; Sonnet and Haiku use
Opus's. A 2× output scenario is a sensitivity calculation, not a confidence
interval or guaranteed ceiling.

[pricing-data.json](pricing-data.json) records rates, official source links,
calibration IDs, dataset counts, and source hashes. Prices were verified on
2026-10-13. The page assumes standard global uncached short-input pricing and
excludes retries, tools, taxes, regional premiums, and historical spend.

Rebuild from the current dataset manifests and verified pilot receipts:

```bash
python3 data/engine/reports/pricing.py
node --test data/engine/reports/test_pricing.cjs
```

The builder rejects mismatched dataset, template, and calibration
hashes. Recheck the official pricing links before changing the stored rates.
The HTML template and calculation code live under `data/engine/reports/`.

## Answer-only pilot

[Open the current report](answer-only-pilot-20261013/report.html) for the
200-request run used by the calculator. Exact prompts, requests, raw streams,
responses, provider usage, source hashes, scores, and the receipt verification
are saved beside it. Astra returned 100 answers with no flags. Opus returned 98
answers and two provider-reported cyber refusals. Refusals, API errors, format
compliance, and exact-match accuracy are counted separately.

The two Opus flags occurred on tasks whose displayed traditional meanings
concern theft. The report preserves the provider's `cyber` label and notes that
false positives are plausible. It does not silently count either refusal as an
incorrect Sanskrit answer. One refusal happened before output and is unbilled
under Anthropic's documented policy; one generated reasoning before refusal
and is billed. The calculator excludes both from its successful-response token
baseline and shows their costs in the observed per-attempt figures.

## Earlier thinking-block pilot

[Open the refusal report](flagging-pilot-20261013/report.html) for the separate
200-request pilot: 25 randomly sampled tasks from each of the four current
datasets, sent unchanged to GPT-6 Astra and Opus 5.5 at xHigh. Exact requests,
raw streams, responses, usage, scores, and source hashes are saved beside it.
Policy refusals, cyber flags, API errors, and accuracy are counted separately.

The runner is `data/engine/reports/flagging_pilot.py`. Its `prepare` action freezes
a sample without API calls; `run` makes paid calls and requires authorization.
There are no automatic retries or model fallbacks. A started request without a
receipt blocks resumption to prevent accidental duplicate charges. `report`
and `verify` only read receipts and write local reports; neither makes API calls.

This archived pilot used the former templates, which requested a visible
`<thinking>` section. Opus refused all 100 requests as `reasoning_extraction`.
It is retained as evidence for the prompt change and is not used by the current
calculator. Removing the visible section does not disable native reasoning or
its output-token billing.
