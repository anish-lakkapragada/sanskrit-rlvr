# Opus 5.5 xHigh evaluation

Results live in `data/benchmark/results/opus55-xhigh/`. The manifest pins the
same 5,000 tasks per family, renderers, and exact answer-membership scorer as
the Astra run. The new Opus configuration uses `data/engine/prompts/v3/`;
Astra used v2. The runner hydrates the exact template pinned for each family
in the manifest, independently of the renderers' default template paths.
Each request contains one hydrated user prompt and
uses `claude-opus-5-5`, adaptive thinking, `output_config.effort: xhigh`, and
standard capacity. There are no tools, extra system instructions, model
fallbacks, or automatic retries.

Anthropic requires `max_tokens`; use its full 128,000-token model allowance,
including hidden thinking. This is the provider ceiling, with no smaller
benchmark-imposed output cap. Prices are $4/million uncached input tokens
and $20/million output tokens. Thinking is already included in output usage.
The manifest also records cache and refusal billing rules and their sources.

The four result arrays use the same 13 fields as Astra. Refusals preserve
`stop_details`, including the category. Incomplete responses and failures
have `correct: null`. Interrupted streams retain their partial response in
the journal; partial usage is never presented as a final charge.

The runner durably writes a started marker before each request and a full
response/error record before scoring. A process lock blocks duplicate workers.
Resume replays the four journals and submits only unsent tasks. A request with
a start but no terminal record blocks resume. Completed journals are verified
and gzip-compressed. Never delete journals while a run may need recovery.

The spending guard reserves the full possible output charge for every active
request and every failed attempt with unknown usage. The $1,500 ceiling applies
to this run; the local ledger does not know account-wide remaining credit.
Transient failures are preserved and trigger a cooldown before unrelated tasks
continue. Rate limits lower concurrency, honoring Retry-After when supplied.
Five consecutive transient failures pause for inspection. Refusals remain
benchmark outcomes and do not cause model fallback or prompt modification.

```bash
uv run --python 3.11 --with httpx==0.28.1 --with python-dotenv==1.1.1 \
  --with vidyut==0.4.0 --with jsonschema==4.23.0 python \
  data/engine/evaluation/run_opus.py run --concurrency 64 --budget-usd 1500
```

`prepare --prompt-version v3` creates a new run locally and refuses to replace
an existing nonempty folder. Omitting `--prompt-version` retains the original
v2 preparation default. Once prepared, the manifest controls the version;
`run`, `status`, and `verify` do not accept a template-version override.
`status` and `verify` are offline; `verify` checks result arrays against journal
replay and rejects unresolved attempts. `--max-new N` limits a staged invocation
to N unsent benchmark tasks. `run-control.json` can adjust live concurrency with
`{"concurrency":64}`. SIGINT/SIGTERM stops admission and saves active requests
before pausing. `watch_opus.py` verifies completion and notifies this Mac.

Explicit infrastructure retries use `retry_opus.py`. Each batch pins its
authorized task IDs and next attempt numbers before sending. It replaces only
those selected result rows, preserves all earlier attempts in the journals,
and retains every attempt's costs, including unknown original costs.
Re-running the same batch never resends a settled attempt. Incorrect completed
answers and refusals are not retry candidates. After a retry batch exists,
the primary `run` command rejects execution; `status` and `verify` still work
offline and account for all attempts.

The completed v3 run's explicit batch was:

```bash
uv run --python 3.11 --with httpx==0.28.1 --with python-dotenv==1.1.1 \
  --with vidyut==0.4.0 --with jsonschema==4.23.0 python \
  data/engine/evaluation/retry_opus.py --batch-id connection-retry-20261015 \
  --expected-count 14 --concurrency 7 --budget-usd 1500
```
