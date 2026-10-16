"""Offline report and same-task comparison after frozen-template validation."""
from collections import Counter
import statistics

from data.engine.evaluation import validate_opus_candidates as v


def finish():
    verified = v.verify(v.FOLDER)
    manifest = v.prior.read_json(v.FOLDER / 'manifest.json')
    rows = v.prior.read_json(v.FOLDER / 'results.json')
    plan = {p['request_key']: p for p in v.prior.read_json(v.FOLDER / 'plan.json')}
    originals, sources = {}, {}
    for f in v.FAMILIES:
        path = v.opus.RUN / f'{f}.json'
        original = v.prior.read_json(path)
        assert len(original) == 5000
        originals[f] = {r['task_id']: r for r in original}
        sources[f] = v.opus.descriptor(path)
    pairs, families, failure_records = Counter(), {}, []
    for f in v.FAMILIES:
        subset = [r for r in rows if r['family'] == f]
        old = [originals[f][r['task_id']] for r in subset]
        for r, previous in zip(subset, old):
            task = plan[r['request_key']]['task']
            score = v.opus.score_output(previous['output_text'], task['gold_devanagari'], previous['status'])
            assert all(previous[k] == value for k, value in score.items())
            a = previous['correct'] is True and previous['format_ok']
            b = r['correct'] is True and r['format_ok']
            pairs['both_correct' if a and b else 'original_only_correct' if a else 'candidate_only_correct' if b else 'neither_correct'] += 1
            if not b:
                failure_records.append({'family': f, 'task_id': r['task_id'], 'status': r['status'],
                                        'output_text': r['output_text'], 'answer': r['answer'],
                                        'gold_devanagari': task['gold_devanagari'], 'error': r['error'],
                                        'original_correct': a, 'original_answer': previous['answer']})
        families[f] = {
            'requests': len(subset),
            'candidate_correct': sum(r['correct'] is True and r['format_ok'] for r in subset),
            'original_correct': sum(r['correct'] is True and r['format_ok'] for r in old),
            'candidate_refusals': sum(r['status'] == 'refused' for r in subset),
            'original_refusals': sum(r['status'] == 'refused' for r in old),
            'candidate_statuses': dict(Counter(r['status'] for r in subset)),
            'original_statuses': dict(Counter(r['status'] for r in old)),
            'candidate_mean_cost_usd': statistics.mean(r['cost_usd'] for r in subset if r['cost_usd'] is not None) if subset else None,
            'candidate_mean_output_tokens': statistics.mean(r['usage']['output_tokens'] for r in subset if r['usage']) if subset else None,
        }
    comparison = {'created_at': v.base.now(), 'source_results': sources, 'families': families, 'paired_correctness': dict(pairs),
                  'original_strict_correct': sum(x['original_correct'] for x in families.values()),
                  'candidate_strict_correct': sum(x['candidate_correct'] for x in families.values()),
                  'original_refusals': sum(x['original_refusals'] for x in families.values()),
                  'candidate_refusals': sum(x['candidate_refusals'] for x in families.values()),
                  'original_statuses': dict(Counter(originals[r['family']][r['task_id']]['status'] for r in rows)),
                  'candidate_statuses': dict(Counter(r['status'] for r in rows)),
                  'requests': len(rows),
                  'caveat': 'Descriptive comparison on identical tasks. Call dates, model randomness, and output ceilings differ; this does not isolate a causal prompt effect. Sampling stopped by cost; confidence intervals are descriptive binomial estimates.'}
    assert sum(pairs.values()) == len(rows)
    v.common.write_json(v.FOLDER / 'paired-comparison.json', comparison)
    v.common.write_json(v.FOLDER / 'failures.json', failure_records)
    report = (v.FOLDER / 'report.txt').read_text()
    report += '\nSAME TASKS WITH THE ORIGINAL PROMPTS (EARLIER FULL RUN)\n'
    report += f'Original strict correct: {comparison["original_strict_correct"]}/{len(rows)}; candidate strict correct: {comparison["candidate_strict_correct"]}/{len(rows)}.\n'
    report += f'Original refusals: {comparison["original_refusals"]}; candidate refusals: {comparison["candidate_refusals"]}.\n'
    report += f'Original status counts: {comparison["original_statuses"]}; candidate status counts: {comparison["candidate_statuses"]}.\n'
    report += comparison['caveat'] + '\n'
    report += 'paired-comparison.json includes category counts and source hashes. failures.json preserves every non-correct result and its accepted answers.\n'
    v.base.atomic_write(v.FOLDER / 'report.txt', report)
    provenance_path = v.common.FOLDER / 'candidate-templates/provenance.json'
    provenance = v.prior.read_json(provenance_path)
    for f in v.FAMILIES:
        assert provenance['files'][f] == manifest['template_sources'][f]
    entry = {'experiment': str(v.FOLDER.relative_to(v.ROOT)), 'verified_at': verified['verified_at'],
             'verification': v.opus.descriptor(v.FOLDER / 'verification.json'),
             'summary': verified['summary'], 'output_budget_policy': manifest['output_budget_policy'],
             'cost_usd': verified['cost_usd'], 'templates_modified': False}
    provenance['validation_runs'] = [x for x in provenance.get('validation_runs', []) if x['experiment'] != entry['experiment']] + [entry]
    v.common.write_json(provenance_path, provenance)
    previous_report = v.prior.FOLDER / 'report.txt'
    note = ('\nFRESH FROZEN-TEMPLATE VALIDATION\n'
            f'{len(rows)} further fresh tasks: {comparison["candidate_strict_correct"]} strict correct; '
            f'{comparison["candidate_refusals"]} refusals. See ../opus55-uniform-validation/report.txt for costs, output allowances, and full results. '
            'These results are additional evidence; the exploratory results above are unchanged.\n')
    old_text = previous_report.read_text()
    if note not in old_text:
        v.base.atomic_write(previous_report, old_text + note)
    print(v.base.compact({'requests': len(rows), 'cost_usd': verified['cost_usd'],
                          'current_correct': comparison['candidate_strict_correct'], 'refusals': comparison['candidate_refusals'],
                          'original_correct': comparison['original_strict_correct'], 'original_refusals': comparison['original_refusals'],
                          'failures': len(failure_records), 'report': str(v.FOLDER / 'report.txt')}))


if __name__ == '__main__':
    finish()
