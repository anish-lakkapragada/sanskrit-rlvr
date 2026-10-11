"""Account for bounded source decisions; never regrade or filter historical files."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'pyproject.toml').exists())
CARRY = HERE.parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    names = ['Anthropic-review.json', 'OpenAI-curadi-review-v2.json',
             'OpenAI-broad-review.json', 'lexical-holds-followup.json',
             'shared-holds-followup.json', 'jna-shuth-followup.json',
             'metadata-priority-followup.json', 'input-metadata-audit.json']
    docs = {name: read(HERE / name) for name in names}
    tasks_path = CARRY.parent.parent / 'candidate-1800-v1/tasks.json'
    tasks = read(tasks_path)
    repairs = {'01.0150', '01.0248', '01.0946'}
    identity_holds = {'01.0253', '01.0922', '01.0923'}
    held = {i for i, t in enumerate(tasks) if t['dhatu']['code'] in repairs | identity_holds}
    assert held == {372, 437, 481, 495, 566, 712}
    assert all(sum(t['dhatu']['code'] == code for t in tasks) == 1
               for code in repairs | identity_holds)
    inputs = {str((HERE / n).relative_to(ROOT)): sha(HERE / n) for n in names}
    inputs[str(tasks_path.relative_to(ROOT))] = sha(tasks_path)
    models = {}
    initial = {
        'Anthropic': docs['Anthropic-review.json']['rows'],
        'OpenAI': docs['OpenAI-curadi-review-v2.json']['records'] + docs['OpenAI-broad-review.json']['rows'],
    }
    for provider in ('Anthropic', 'OpenAI'):
        path = CARRY / 'results' / provider / 'predeclared-spelling.json'
        originals = read(path)
        inputs[str(path.relative_to(ROOT))] = sha(path)
        decisions = {}
        for item in initial[provider]:
            i = item['index']
            assert i not in decisions and originals[i]['is_correct'] is False
            assert item['task_id'] == tasks[i]['id'] == originals[i]['task_id']
            answer = item.get('answer', item.get('answer_devanagari'))
            if answer is None:
                assert len(item['forms_devanagari']) == 1
                answer = item['forms_devanagari'][0]
            assert answer == originals[i]['answer']
            decisions[i] = item['disposition']
        assert len(decisions) == (214 if provider == 'Anthropic' else 262)
        # Exact bounded follow-ups. They are source annotations, not mutations of the original grades.
        decisions[229] = 'accepted'
        if provider == 'Anthropic':
            decisions[1186] = 'rejected'
        else:
            decisions[1122] = 'rejected'
        rows = []
        for i, original in enumerate(originals):
            code = tasks[i]['dhatu']['code']
            if code in repairs:
                disposition = 'input_repair_required'
            elif code in identity_holds:
                disposition = 'input_identity_unresolved'
            elif original['status'] == 'refused':
                disposition = 'refusal'
            elif original['status'] == 'infrastructure_error':
                disposition = 'infrastructure_missing'
            elif i in decisions:
                assert decisions[i] in ('accepted', 'rejected'), (provider, i, decisions[i])
                disposition = 'source_accepted_variant' if decisions[i] == 'accepted' else 'source_rejected'
            else:
                assert original['is_correct'] is True, (provider, i)
                disposition = 'original_key_match_not_individually_recertified'
            rows.append({'index': i, 'task_id': tasks[i]['id'], 'code': code,
                         'answer': original['answer'], 'historical_is_correct': original['is_correct'],
                         'source_audit_disposition': disposition})
        counts = Counter(row['source_audit_disposition'] for row in rows)
        known = counts['source_accepted_variant'] + counts['original_key_match_not_individually_recertified']
        unresolved = counts['input_repair_required'] + counts['input_identity_unresolved']
        nonanswers = counts['refusal'] + counts['infrastructure_missing']
        assert sum(counts.values()) == 1800 and unresolved == 6
        models[provider] = {'counts': dict(counts), 'known_positive_under_unflagged_keys': known,
                            'audit_accounting_bounds': [known / 1800, (known + unresolved + nonanswers) / 1800],
                            'fixed_denominator': 1800, 'rows': rows}
    assert models['Anthropic']['counts']['source_rejected'] == 209
    assert models['OpenAI']['counts']['source_rejected'] == 258
    # One newly admitted form must be supported by the separately bound adoption review.
    sr = read(HERE / 'sr-exact-disposition-v1-review.json')
    assert sr['passed'] and sr['dispositions_sha256'] == sha(HERE / 'sr-exact-disposition-v1.json')
    inputs.update({str((HERE / f).relative_to(ROOT)): sha(HERE / f)
                   for f in ('sr-exact-disposition-v1.json', 'sr-exact-disposition-v1-review.json')})
    output = {
        'schema': 'bounded-answer-and-input-source-accounting-v1',
        'created_at': datetime.now(timezone.utc).isoformat(), 'n_per_provider': 1800,
        'models': models, 'input_fingerprints': inputs,
        'input_repair_codes': sorted(repairs), 'unresolved_identity_codes': sorted(identity_holds),
        'scope': 'All 476 initially unmatched usable answers plus input-wide source flags on both models, including prior canonical successes.',
        'bounds_interpretation': 'Historical panel accounting with all six flagged inputs and all nonanswers assigned either no credit or credit. Conditional on unflagged original key matches and bounded rejected-form decisions remaining valid; not a bound on undetected oracle defects or performance on repaired prompts.',
        'no_item_removed': True, 'historical_grades_unchanged': True,
        'all_initial_mismatches_have_bounded_dispositions': True,
        'full_linguistic_certification': False, 'benchmark_ready': False, 'paid_calls': 0,
    }
    for name, digest in inputs.items():
        assert sha(ROOT / name) == digest
    out = HERE / 'bounded-answer-audit-v1.json'
    assert not out.exists(), 'Preserve this version; changes need an explicit new audit version.'
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({p: {k: v for k, v in m.items() if k != 'rows'} for p, m in models.items()}, indent=2))


if __name__ == '__main__':
    main()
