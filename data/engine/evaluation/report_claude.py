"""Verify and write final Claude benchmark artifacts; never sends API requests."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import run_claude as runner


def save_json(path, value):
    runner.base.atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def finalize(folder):
    folder = Path(folder).resolve()
    report = runner.inspect(folder, verify=True)
    manifest, tasks, prompts, _ = runner.load_inputs(folder)
    if manifest['status'] != 'completed' or report['settled'] != 20000 or report['unresolved']:
        raise RuntimeError('Only finalize a completed, fully settled 20000-task benchmark')
    journals = {f: runner.base.Journal(folder / 'journals' / f'{f}.jsonl') for f in tasks}
    started, attempts, unresolved = runner.recover_attempts(journals, tasks, manifest, prompts)
    selected = runner.base.latest_records(attempts)
    report.update(run_id=manifest['run_id'], model=manifest['request_defaults']['model'],
                  prompt_version=manifest['prompt_version'], started_at=manifest['started_at'],
                  finished_at=manifest['finished_at'])
    all_rows = [row for family in attempts.values() for row in family.values()]
    rows = [row for family in selected.values() for row in family.values()]
    refusal_rows = [{'family': f, 'task_id': task_id, 'attempt_number': attempt,
                     'category': ((row.get('error') or {}).get('stop_details') or {}).get('category', 'unspecified')}
                    for f, family in attempts.items() for (task_id, attempt), row in family.items()
                    if row['status'] == 'refused']
    report.update(strict_correct=sum(r['correct'] is True and r['format_ok'] for r in rows),
                  format_failures=sum(r['status'] == 'completed' and not r['format_ok'] for r in rows),
                  refusals={'total': len(refusal_rows), 'categories': dict(Counter(r['category'] for r in refusal_rows)),
                            'attempts': refusal_rows},
                  remaining_infrastructure_errors=sum(runner.transient_failure(r) for r in rows),
                  selected_statuses=dict(Counter(r['status'] for r in rows)),
                  all_attempt_statuses=dict(Counter(r['status'] for r in all_rows)),
                  max_output_tokens=max((r.get('usage') or {}).get('output_tokens', 0) for r in all_rows),
                  retry_cost_usd=round(sum(r['cost_usd'] or 0 for r in all_rows if r['attempt_number'] > 1), 10))
    report['answer_correct'] = sum(r['correct'] is True for r in rows)
    report['answer_accuracy_percent'] = report['answer_correct'] / 200
    report['strict_accuracy_percent'] = report['strict_correct'] / 200
    report['unknown_cost_reserve_usd'] = round(report['unknown_cost_attempts'] * runner.base.reserve_per_request(manifest, prompts), 8)
    manifest['execution']['last_verification'] = {'at': runner.base.now(), 'passed': True,
                                                'tasks': report['settled'], 'attempts': report['attempts_settled']}
    manifest['execution']['progress'] = report
    manifest['scoring']['selected_attempt'] = 'Latest explicitly authorized settled attempt; accuracy counts each task once and costs include all attempts.'
    save_json(folder / 'manifest.json', manifest)
    save_json(folder / 'summary.json', report)
    for journal in journals.values():
        journal.archive()
    save_json(folder / 'verification.json', {
        'verified_at': runner.base.now(), 'manifest': runner.descriptor(folder / 'manifest.json'),
        'summary': runner.descriptor(folder / 'summary.json'),
        'all_request_bodies_match_pinned_v3_prompts_and_settings': True,
        'all_results_match_journal_replay_and_schema': True,
        'source_order_and_unique_task_ids_verified': True,
        'attempts_verified': len(started), 'unresolved_requests': len(unresolved),
        'all_attempt_costs_preserved': True,
        'result_files': [runner.descriptor(folder / f'{f}.json') for f in tasks],
        'journal_archives': [runner.descriptor(folder / 'journals' / f'{f}.jsonl.gz') for f in tasks],
        'report_implementation': runner.descriptor(Path(__file__)),
    })
    write_readme(folder, manifest, report)
    return report


def write_readme(folder, manifest, report=None):
    name = runner.MODELS[manifest['run_id']]['name']
    text = f'# {name} with v3 prompts\n\n'
    if report:
        text += (f"Evaluated **20,000 tasks**, 5,000 per family. Exact-answer accuracy: **{report['answer_correct']:,}/20,000 "
                 f"({report['answer_accuracy_percent']:.3f}%)**. Accuracy also requiring the exact output format: **{report['strict_correct']:,}/20,000 "
                 f"({report['strict_accuracy_percent']:.3f}%)**. Recorded cost across all attempts: **${report['known_cost_usd']:.6f}**. "
                 f"There are **{report['refusals']['total']} refusals**, **{report['remaining_infrastructure_errors']} remaining infrastructure failures**, "
                 f"and **{report['unknown_cost_attempts']} attempts with unknown charges**. Unknown charges are not treated as zero.\n\n")
        text += '| Family | Exact answers correct | Exact-answer accuracy | Answer + format accuracy | Recorded cost, all attempts |\n| --- | ---: | ---: | ---: | ---: |\n'
        for f, s in report['families'].items():
            text += f"| {f} | {s['correct']:,} / 5,000 | {s['correct']/50:.2f}% | {s['strict_correct']/50:.2f}% | ${s['known_cost_usd']:.6f} |\n"
        text += (f"\nAll {report['attempts_settled']:,} attempts were verified against durable journals; "
                 f"{report['retry_attempts']} were infrastructure retries. Costs include original failures and retries when usage is available. "
                 f"The conservative reserve for unknown charges is ${report['unknown_cost_reserve_usd']:.6f}; this is not a recorded charge.\n\n")
    else:
        text += 'Evaluation in progress: 20,000 tasks, 5,000 per family. See manifest.json for current progress and refusal-monitor.json for flagging.\n\n'
    text += '''[manifest.json](manifest.json) pins every input file, prompt text, renderer, scorer, request setting and price.
[result.schema.json](result.schema.json) defines the compact result rows. Final summaries and reproducibility checks
are written to [summary.json](summary.json) and [verification.json](verification.json).

| Family | Benchmark input | Prompt template | Result |
| --- | --- | --- | --- |
'''
    for f in runner.FAMILIES:
        text += f'| {f} | [input](../../{f}/{f}.json) | [v3](../../../engine/prompts/v3/vp_{f}.txt) | [{f}.json]({f}.json) |\n'
    rates = manifest['pricing']['rates_usd_per_million_tokens']
    text += f'''
Each independent request uses `{manifest['request_defaults']['model']}`, adaptive thinking and `xhigh` effort,
with the exact same hydrated v3 user prompt as Opus. There are no tools, internet access, system messages,
conversation history or model fallbacks. All 20,000 hydrated prompts were checked against the completed Opus run.
Seed 69 refers to the existing benchmark sample; no new sampling or generation seed is used.

Anthropic requires `max_tokens`; it is set to the full supported **128,000**, including hidden thinking.
There is no smaller benchmark output cap. Requests use streaming and `standard_only` service.
Model availability, adaptive thinking and xHigh support were verified through the Models API;
the response is saved in [model-capabilities.json](model-capabilities.json).

The scorer trims whitespace inside one `<answer>...</answer>` block and checks exact membership in
`gold_devanagari`, without spelling or Unicode normalization. Strict accuracy additionally requires
exactly one nonempty answer block with only whitespace outside. Refusals, errors and incomplete responses
stay in the 20,000-task denominator. Answers and task IDs are not included in prompts.

Each of the four result arrays contains the same 13 fields as Opus: task_id, attempt_number, status,
output_text, answer, correct, format_ok, usage, cost_usd, request_id, response_id, elapsed_ms and error.
Output length is `usage.output_tokens`, which already includes hidden thinking. Accepted answers remain
in the source task file. `schema_version: 2` describes the storage layout; `prompt_version: v3` describes the prompts.

Rates verified on 2026-10-14: **${rates['uncached_input']:g}/million input tokens** and
**${rates['output']:g}/million output tokens**, with cache rates recorded separately in the manifest.
Haiku's rates apply to prompts of at most 100,000 tokens; all benchmark prompts are much shorter.
An unexpected pricing tier stops execution for review. These are usage-based estimates excluding taxes and credits.
The per-run ceiling is ${manifest['execution']['budget_usd']:g}; the new Sonnet and Haiku ceilings total $600,
within the earlier $1,500 Anthropic target after known prior runs. This is not a measured account balance.

Requests and responses/errors are saved to append-only journals before scoring; completed journals are
verified and compressed to `journals/*.jsonl.gz`. Resuming sends only unsent tasks. Unresolved started
attempts block resume. Infrastructure retries are explicitly recorded in the manifest, replace only
failed result rows, and preserve every original attempt and cost. Completed wrong answers and refusals
are never retried. Templates remain fixed throughout the run.

Offline verification (no API calls), from the repository root:

```bash
uv run --python 3.11 --with httpx==0.28.1 --with python-dotenv==1.1.1 \\
  --with vidyut==0.4.0 --with jsonschema==4.23.0 python \\
  data/engine/evaluation/run_claude.py verify --folder data/benchmark/results/{manifest['run_id']}
```

The primary runner is [run_claude.py](../../../engine/evaluation/run_claude.py), infrastructure retries use
[retry_claude.py](../../../engine/evaluation/retry_claude.py), and final artifacts are generated by
[report_claude.py](../../../engine/evaluation/report_claude.py). The completed Opus runner and results remain unchanged.
'''
    runner.base.atomic_write(folder / 'README.md', text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.folder), ensure_ascii=False, indent=2))
