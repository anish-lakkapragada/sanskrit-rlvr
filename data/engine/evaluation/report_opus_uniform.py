"""Offline verification, candidate installation, and report for the $5 study."""
from collections import Counter
import fcntl
from data.engine.evaluation import experiment_opus_uniform as e


def finish():
    folder = e.FOLDER
    manifest = e.read_json(folder / 'manifest.json')
    if manifest['stages']['final_confirmation']['status'] != 'completed':
        raise RuntimeError('Final confirmation is incomplete')
    if manifest['stages']['final_stress']['status'] != 'completed':
        raise RuntimeError('Final stress stage is incomplete; inspect budget before finalizing')
    selected = 'table_rules_first'
    result = e.verify(folder, selected)
    if result['matching_final_templates']['refusals']:
        raise RuntimeError('Selected templates still refused; report and inspect instead of installing as zero observed')
    e.verify(folder, selected, install=True)
    with (folder / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest, cases, journal, starts, records = e.load(folder)
        journal.archive()
        manifest.update(status='completed', finished_at=e.base.now(), selected_variant=selected,
                        actual_requests=len(records),
                        selected_templates={f: e.opus.descriptor(e.common.FOLDER / 'candidate-templates' / f'vp_{f}.txt') for f in e.FAMILIES})
        e.common.write_json(folder / 'manifest.json', manifest)
    # Verify replay from the archived journal as well as the installed files.
    result = e.verify(folder, selected, install=True)
    rows = e.read_json(folder / 'results.json')
    summary = e.summarize({r['request_key']: r for r in rows})
    selected_rows = [r for r in rows if r['variant'] == selected]
    templates = e.read_json(folder / 'followup-candidates.json')[selected]
    for f in e.FAMILIES:
        assert (e.common.FOLDER / 'candidate-templates' / f'vp_{f}.txt').read_text() == templates[f]
    assert len({t.split('Write ONLY the final form', 1)[1] for t in templates.values()}) == 1
    report = [
        'UNIFORM ORIGINAL-V2 PROMPT EXPERIMENT',
        '',
        f'Finished: {manifest["finished_at"]}',
        'Model: claude-opus-5-5; adaptive thinking; xhigh effort; standard tier.',
        'No tools, system prompt, fallback model, automatic retries, or Internet access in model requests.',
        'Output allowance: full provider maximum, 128000 tokens including thinking; no smaller benchmark cap.',
        f'New requests: {len(rows)}. Estimated usage-based cost: ${summary["total"]["known_cost_usd"]:.6f} of the $5 ceiling.',
        f'Unknown-cost requests: {summary["total"]["unknown_cost_requests"]}. Full-output dollar reservations checked before every call.',
        '',
        'SELECTED TEMPLATE SET',
        'All four templates use: one parallel task sentence, task-specific grammatical rules, a two-column input table, and the same answer-only instruction.',
        'All original v2 hydration fields and grammatical inputs are preserved. Optional prefix and participle fields remain renderer-compatible.',
        'Only candidate templates were updated. Production v2 templates, hydrated production samples, and benchmark results are unchanged.',
        'Candidate folder: data/benchmark/experiments/opus55-cyber-wording/candidate-templates/',
        '',
        'Requests matching the final templates (includes selection trials and repeated tasks):',
        'Family       Requests   Refusals   Strict-correct   Unique tasks',
    ]
    for f in e.FAMILIES:
        group = [r for r in selected_rows if r['family'] == f]
        stat = e.common.metrics(group)
        report.append(f'{f:12} {stat["requests"]:8} {stat["refusals"]:10} {stat["strict_correct"]:16} {len({r["task_id"] for r in group}):14}')
    stat = result['matching_final_templates']
    report += [f'Total        {stat["requests"]:8} {stat["refusals"]:10} {stat["strict_correct"]:16} {len({(r["family"], r["task_id"]) for r in selected_rows}):14}', '']
    final = summary['stages']['final_confirmation']['variants'][selected]
    stress = summary['stages']['final_stress']['variants'][selected]
    report += [
        f'Untouched final confirmation: {final["refusals"]}/{final["requests"]} refusals, {final["strict_correct"]}/{final["requests"]} strict correct; 15 tasks per family.',
        f'Final repeated challenges: {stress["refusals"]}/{stress["requests"]} refusals, {stress["strict_correct"]}/{stress["requests"]} strict correct.',
        'Each hard taddhitanta case was tested twice during final-variant selection and three more times after selection.',
        '',
        'ALL EXPLORATORY RESULTS ARE RETAINED',
        'Stage / variant                        Requests   Refusals   Strict-correct',
    ]
    for phase, stage in summary['stages'].items():
        for variant, stat in stage['variants'].items():
            report.append(f'{phase}/{variant:25} {stat["requests"]:8} {stat["refusals"]:10} {stat["strict_correct"]:16}')
    report += [
        '',
        'The first table variant refused miraPa + Iyasun once during the 80-task validation stage. That failure prompted additional tuning; it was not erased or replaced by a successful retry.',
        'The original 80-task confirmation plan was superseded before any request was sent. Final confirmation used the first 15 prospectively selected tasks per family, chosen before seeing their outcomes, to leave room for full-output dollar reservations.',
        'Discovery tasks deliberately included known refusals and repetitions. Validation was fresh but enriched for earlier benchmark refusals. It became tuning data after the new failure. Final confirmation tasks were disjoint from all tuning and prior wording experiments.',
        'Zero observed refusals is a finite test result, not a guarantee of zero future refusal probability or a benchmark-wide population estimate.',
        '',
        'REPRODUCIBILITY',
        'manifest.json: model settings, pinned sources, template texts, budgets, prospective samples, stage decisions.',
        'cases.json and *-plan.json: exact tasks and every sent prompt; unsent historical plans are labeled in the manifest.',
        'results.json and journals/requests.jsonl.gz: every outcome, provider response, token usage and cost, including failures.',
        'verification.json: schema, journal replay, prompt hydration, provider settings, dollar admissions, production source hashes.',
        'candidate-templates-before/ and candidate-templates-after/: complete candidate snapshots.',
        'tested-templates/: all candidate wording and initial diffs.',
        '',
        'Pricing source: https://platform.claude.com/docs/en/models/opus-5-5/overview (verified 2026-10-14).',
        'Costs use provider usage at $4/M input and $20/M output; no-output cyber refusals are unbilled under the provider policy. Invoice taxes, credits and adjustments are excluded.',
    ]
    e.base.atomic_write(folder / 'report.txt', '\n'.join(report) + '\n')
    note = ('\nLATER UNIFORM-TEMPLATE EXPERIMENT\n'
            'The current candidate templates are now the shared rules-before-table set from opus55-uniform-v2. '
            'This historical report and its outcomes are preserved; see ../opus55-uniform-v2/report.txt for the current evidence.\n')
    for name in ('opus55-cyber-wording', 'opus55-cyber-wording-round2', 'opus55-cyber-wording-round3'):
        path = folder.parent / name / 'report.txt'
        text = path.read_text()
        if note not in text:
            e.base.atomic_write(path, text + note)
    print(e.base.compact({'requests': len(rows), 'total_cost_usd': summary['total']['known_cost_usd'],
                          'selected': result['matching_final_templates'],
                          'confirmation': final, 'report': str(folder / 'report.txt')}))


if __name__ == '__main__':
    finish()
