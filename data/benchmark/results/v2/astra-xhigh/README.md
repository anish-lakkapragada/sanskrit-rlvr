# Astra xHigh evaluation contract

The [runner](../../../engine/evaluation/run_astra.py) executes this run and
records its live progress in [manifest.json](manifest.json). The manifest
pins 20,000 tasks, request settings, templates, source hashes, scoring and
prices once for the run.

| Family | Benchmark input (repository-relative) | Prompt template (repository-relative) | Result file |
| --- | --- | --- | --- |
| tinanta | `data/benchmark/tinanta/tinanta.json` | `data/engine/prompts/v2/vp_tinanta.txt` | `tinanta.json` |
| taddhitanta | `data/benchmark/taddhitanta/taddhitanta.json` | `data/engine/prompts/v2/vp_taddhitanta.txt` | `taddhitanta.json` |
| krdanta | `data/benchmark/krdanta/krdanta.json` | `data/engine/prompts/v2/vp_krdanta.txt` | `krdanta.json` |
| subanta | `data/benchmark/subanta/subanta.json` | `data/engine/prompts/v2/vp_subanta.txt` | `subanta.json` |

Each family has 5,000 tasks. Hydrate its pinned template with the existing
`common.render_task` function. Send one independent Responses API request
with `model: gpt-6-astra`, `reasoning.effort: xhigh`, `service_tier: default`,
`store: false`, and `stream: true`. The hydrated prompt is `input`.

**Omit max_output_tokens entirely.** Provider limits still apply. Add no
extra instructions, history, tools or generation seed. Seed 69 belongs to
dataset selection.

## Compact result rows

[result.schema.json](result.schema.json) defines a JSON array for each
family, with **13 fields per attempt**:

| Field | Meaning |
| --- | --- |
| `task_id` | Join to the original benchmark row for inputs and accepted answers |
| `attempt_number` | Initially 1; an explicitly authorized retry replaces this task's selected row with attempt 2 (or later) |
| `status` | completed, refused, incomplete, api_error, transport_error, or unknown |
| `output_text` | Original visible response, including tags or available partial text |
| `answer` | Extracted answer with surrounding whitespace removed, or null |
| `correct` | Exact membership in the task's gold list; null for non-completed outcomes |
| `format_ok` | One nonempty answer block, no nested markup, only whitespace outside |
| `usage` | Full provider token counts; **output length is usage.output_tokens** |
| `cost_usd` | Usage-based cost estimate, or null when unknown |
| `request_id` | Provider request ID, or null |
| `response_id` | Provider response ID, or null |
| `elapsed_ms` | Attempt duration, or null |
| `error` | Compact error/refusal/incomplete or unknown-cost details; normally null |

Family comes from the filename. Gold answers and grammatical coordinates
stay in the pinned benchmark files. Model settings, template hashes, prices
and scoring version stay in the manifest. Derived lengths, format issues,
strict correctness and price breakdowns can be recomputed without storing
them on every row. Save results as UTF-8 JSON, one compact row per line.
Each family retains exactly 5,000 task rows in source order. The latest settled,
explicitly authorized attempt is selected; all older attempts remain in journals.

## Scoring and costs

The [scorer](../../../engine/evaluation/scoring.py) extracts exactly one
literal `<answer>...</answer>` block and strips surrounding whitespace.
Compare the answer directly with `task.gold_devanagari` using string
membership. Do not normalize Unicode, change spelling, remove punctuation
or choose among alternatives. Missing, empty, nested or multiple blocks
yield no answer.

A correct answer with extra commentary has `correct: true` and
`format_ok: false`. Refusals, incomplete responses and failures have
`correct: null`; retain any extracted answer for review. Derive strict
accuracy from `correct is true and format_ok` across the 20,000 selected task
rows. Report errors and refusals separately. The user explicitly requested
in-place replacement of the seven infrastructure failures on October 14.
First-attempt results remain in the journals, with their original summary in
`execution.primary_attempt_progress`. The complete pre-retry manifest is retained
under `manifest_history` in the current `manifest.json`; the separate snapshot
file was consolidated at the user's request.
All attempts' costs still count, including unknown costs of original failures.

Use the manifest's rates and the full provider usage to calculate costs.
`usage.output_tokens` already includes reasoning tokens; do not add them
again. Check cache counters and the returned tier before pricing.
Unavailable usage or unresolved billing details mean `cost_usd: null`,
with a reason in `error`. Estimates exclude credits, taxes and invoice
adjustments.

## Four journals for recovery

Keep one append-only `journals/{family}.jsonl` per family, keyed by
`task_id` and `attempt_number`:

1. Before sending, durably append the exact request, including its hydrated
   prompt, timestamp and client request ID.
2. Before scoring, durably append the complete terminal provider response,
   timestamp, request ID and elapsed time. On a handled interruption, save
   the error and available partial output.
3. Atomically update the family result array. Rebuild missing results from
   journal entries on resume.
4. After completion, gzip the journal, verify it, then remove the plain copy.
   Keep four `.jsonl.gz` archives alongside the four result files.

There are no per-request folders or permanent per-event stream logs. Shared
task data is not copied into journals. An abrupt process crash can lose
in-memory partial output; a started request without a terminal record
remains unresolved and must never be automatically resent. Automatic
retries and model fallbacks are disabled.

The complete returned responses remain available for offline rescoring,
repricing and debugging. A process lock prevents concurrent runners from
sending the same tasks. SIGINT/SIGTERM pauses new submissions and waits for
in-flight responses to be saved. A transport/API error or unknown cost also
pauses new submissions for inspection; requests are never automatically retried.

A terminal `server_is_overloaded` response or a recognized interrupted stream
with a response ID is the exception: retain that failed attempt and pause new
submissions for 60 seconds, then continue unsent tasks. Recognized interruptions
are an EOF without a terminal response or HTTPX `RemoteProtocolError`; other
errors still stop the run for inspection.
Missing usage remains `cost_usd: null`; the spending guard reserves its full
possible request charge alongside in-flight reservations. Five new transient failures
in one invocation pause the run for inspection. No failed task is retried.
The manifest's `execution.submission_state` distinguishes submitting, cooling
down and draining while the worker is alive; `stopped_reason` is updated during
the drain, rather than waiting for the process to exit.

The runner defaults to a $3,000 ceiling for this run, based on the earlier
OpenAI budget target. It reserves each in-flight request's full provider
output allowance plus estimated input cost before sending; this does not
set an output-token cap. Account-wide remaining credit and spending on other
runs are not available from this ledger. The manifest reports known cost,
unknown-cost attempts and a projection from observed per-family averages.

Run all remaining primary tasks with the existing repository API key:

```bash
uv run --python 3.11 --with httpx==0.28.1 --with python-dotenv==1.1.1 \
  --with vidyut==0.4.0 --with jsonschema==4.23.0 python \
  data/engine/evaluation/run_astra.py run --concurrency 32 --budget-usd 3000
```

Use `status` to inspect results or `verify` to compare all results with journal
replay. Both are offline. `--max-new N` runs only the next N unsent tasks for
a staged launch; those responses remain part of the primary benchmark.

`run-control.json`, when present, overrides the command-line concurrency with
`{"concurrency": 256}`. The runner reads it between submissions. Values 1–512
are supported; reducing concurrency lets active requests finish. The HTTP
transport and worker pool both support 512 connections/workers, while the
control file and spending guard determine actual admission. This changes
throughput only; model settings and prompt bodies remain pinned.

When the runner changes during a planned restart, the previous code is saved
once in `runner-history/` and its descriptor is retained in the manifest's
`execution.runner_revisions`. Completed responses are replayed before the
new runner starts any unsent tasks.

Explicit infrastructure retries use [retry_astra.py](../../../engine/evaluation/retry_astra.py).
The batch ID pins the target list before sending. Re-running the same batch
resumes only unsent attempts; it never sends a completed attempt again, even
if that retry failed. Incorrect completed answers are never retry candidates.
Archived journals are expanded before appending and re-compressed after the
batch finishes. The main runner's `verify` checks the selected rows against
all journal attempts. Manifest costs include every attempt, while task counts
and accuracy count each task once.

```bash
uv run --python 3.11 --with httpx==0.28.1 --with python-dotenv==1.1.1 \
  --with vidyut==0.4.0 --with jsonschema==4.23.0 python \
  data/engine/evaluation/retry_astra.py --batch-id infra-retry-20261014 \
  --expected-count 7 --concurrency 7 --budget-usd 3000
```

Rebuild the scaffold locally before execution, without API calls. The
generator rejects changes after run artifacts exist:

```bash
python3 data/engine/evaluation/scaffold_astra.py
```
