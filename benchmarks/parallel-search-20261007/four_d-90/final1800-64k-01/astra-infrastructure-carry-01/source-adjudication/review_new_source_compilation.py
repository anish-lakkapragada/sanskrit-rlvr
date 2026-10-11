"""Independent bounded compilation/provenance checks, without grammar recertification."""
import hashlib
import json
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
CARRY = HERE.parent
LAYER = CARRY / 'source-adjusted/completed-45828abcf2a5e9e0'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(s):
    return unicodedata.normalize('NFC', s.strip())


def save(p, x):
    assert not p.exists(), str(p)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')


def main():
    ap = LAYER / 'analysis.json'
    analysis = read(ap)
    accounting_path = HERE / 'bounded-answer-audit-v1.json'
    accounting = read(accounting_path)
    tasks_path = CARRY.parent.parent / 'candidate-1800-v1/tasks.json'
    tasks = read(tasks_path)
    by_id = {t['id']: t for t in tasks}
    assert len(tasks) == len(by_id) == 1800
    evidence_files = []
    for item in analysis['source_evidence']:
        p = ROOT / item['path']
        assert sha(p) == item['sha256']
        evidence_files.append(str(p.relative_to(ROOT)))
    for p, expected in analysis['preserved_original_result_fingerprints'].items():
        assert sha(CARRY.parent / p) == expected
    for p, expected in accounting['input_fingerprints'].items():
        assert sha(ROOT / p) == expected
    assert analysis['primary_analysis_sha256'] == sha(CARRY / 'analysis.json')
    base = ROOT / 'benchmarks/parallel-search-20261007/four_d-90/final1800-source-pack/source-adjudication-adoption-02.json'
    docs = [(base,19),(HERE/'puadi-exact-dispositions-v1.json',2),(HERE/'sr-exact-disposition-v1.json',1)]
    accepted = {}
    for path, count in docs:
        doc = read(path)
        assert doc['candidate_tasks_sha256'] == sha(tasks_path)
        assert len(doc['accepted_additions']) == count
        for entry in doc['accepted_additions']:
            task = by_id[entry['task_id']]
            assert entry['dhatu'] == task['dhatu']
            assert entry['morphology'] == task['morphology']
            assert entry['prompt_sha256'] == task['campaign']['prompt_sha256']
            for form in entry['additional_forms_devanagari']:
                key = (task['id'], norm(form))
                assert key not in accepted
                accepted[key] = [sha(path)]
    assert len(accepted) == 22
    extension = read(HERE/'reviewed-source-extensions-v2.json')
    assert extension['tool_manifest_sha256'] == sha(CARRY/'source-adjusted/tool-manifest.json')
    for item in extension['dispositions']:
        doc_path, review_path = ROOT/item['path'], ROOT/item['review_path']
        assert sha(doc_path) == item['sha256'] and sha(review_path) == item['review_sha256']
        review = read(review_path)
        assert review['passed'] and review['dispositions_sha256'] == sha(doc_path)
    hold = {372,437,481,495,566,712}
    repair_codes = {'01.0150','01.0248','01.0946'}
    identity_codes = {'01.0253','01.0922','01.0923'}
    assert {i for i,t in enumerate(tasks) if t['dhatu']['code'] in repair_codes|identity_codes} == hold
    initial = {
        'Anthropic':read(HERE/'Anthropic-review.json')['rows'],
        'OpenAI':read(HERE/'OpenAI-curadi-review-v2.json')['records'] + read(HERE/'OpenAI-broad-review.json')['rows'],
    }
    summaries = {}
    for provider, expected_changed, expected_wrong, expected_positive in [
        ('Anthropic',[229],209,1580), ('OpenAI',[229,984],258,1535)]:
        original_path = CARRY/f'results/{provider}/predeclared-spelling.json'
        copy_path = LAYER/f'{provider}-source-adjusted.json'
        old, new = read(original_path), read(copy_path)
        assert len(old) == len(new) == 1800
        changed = []
        for i,(before,after) in enumerate(zip(old,new)):
            assert before['task_index'] == after['task_index'] == i
            assert before['task_id'] == after['task_id'] == tasks[i]['id']
            assert before['task'] == after['task'] == tasks[i]
            assert set(after) == set(before)|{'source_adjudication'}
            assert all(after[k] == v for k,v in before.items() if k != 'is_correct')
            key = (before['task_id'],norm(before['answer'])) if before['answer'] is not None else None
            expected = before['is_correct']
            if expected is False and key in accepted:
                expected = True
            assert after['is_correct'] is expected
            assert after['source_adjudication']['accepted_policy_hashes'] == accepted.get(key,[])
            assert after['source_adjudication']['finite_is_correct'] is before['is_correct']
            assert after['source_adjudication']['source_is_correct'] is expected
            if before['is_correct'] is not after['is_correct']:
                changed.append(i)
        assert changed == expected_changed
        assert [r['task_index'] for r in analysis['source_changes'][provider]] == changed
        if provider == 'OpenAI':
            assert new[837]['is_correct'] is None and new[837]['answer'] is None
            assert new[837]['status'] == 'infrastructure_error'
        # Reconstruct the exact initial miss cohort and final source categories independently.
        items = initial[provider]
        item_by_index = {r['index']:r for r in items}
        assert len(item_by_index) == len(items) == (214 if provider == 'Anthropic' else 262)
        missed = {i for i,r in enumerate(old) if r['status']=='completed' and r['answer'] is not None and r['is_correct'] is False and not r['truncated']}
        assert set(item_by_index) == missed
        for i,r in item_by_index.items():
            assert r['task_id'] == tasks[i]['id']
            answer = r.get('answer',r.get('answer_devanagari'))
            if answer is None:
                assert len(r['forms_devanagari']) == 1
                answer = r['forms_devanagari'][0]
            assert answer == old[i]['answer']
        compiled = accounting['models'][provider]
        assert len(compiled['rows']) == 1800
        observed = Counter()
        for i,(original,row) in enumerate(zip(old,compiled['rows'])):
            assert row['index'] == i and row['task_id'] == tasks[i]['id']
            assert row['answer'] == original['answer'] and row['historical_is_correct'] is original['is_correct']
            code = tasks[i]['dhatu']['code']
            if code in repair_codes: expected = 'input_repair_required'
            elif code in identity_codes: expected = 'input_identity_unresolved'
            elif original['status']=='refused': expected = 'refusal'
            elif original['status']=='infrastructure_error': expected = 'infrastructure_missing'
            elif i in item_by_index:
                decision = item_by_index[i]['disposition']
                if i == 229: decision = 'accepted'
                if (provider,i) in [('Anthropic',1186),('OpenAI',1122)]: decision='rejected'
                assert decision in ('accepted','rejected')
                expected = 'source_accepted_variant' if decision=='accepted' else 'source_rejected'
            else:
                assert original['is_correct'] is True
                expected = 'original_key_match_not_individually_recertified'
            assert row['source_audit_disposition'] == expected
            observed[expected] += 1
        assert dict(observed) == compiled['counts']
        assert observed['source_rejected'] == expected_wrong
        positive = observed['source_accepted_variant']+observed['original_key_match_not_individually_recertified']
        nonanswer = observed['refusal']+observed['infrastructure_missing']
        assert positive == expected_positive == compiled['known_positive_under_unflagged_keys']
        assert observed['input_repair_required']+observed['input_identity_unresolved'] == 6
        bounds = [positive/1800,(positive+6+nonanswer)/1800]
        assert compiled['audit_accounting_bounds'] == bounds and compiled['fixed_denominator']==1800
        summaries[provider] = dict(changed_indices=changed,initial_misses=len(missed),counts=dict(observed),
            positive=positive,conditional_bounds=bounds,hold_indices=sorted(hold),
            prior_correct_hold_indices=[i for i in sorted(hold) if old[i]['is_correct'] is True],
            original_sha256=sha(original_path),source_copy_sha256=sha(copy_path))
    assert sum(x['initial_misses'] for x in summaries.values()) == 476
    assert 'Conditional on unflagged original key matches' in accounting['bounds_interpretation']
    assert 'not a bound on undetected oracle defects or performance on repaired prompts' in accounting['bounds_interpretation']
    assert accounting['full_linguistic_certification'] is False
    critical_path = HERE/'critical-stem-followup.json'
    critical = read(critical_path)
    caveat = dict(followup_path=str(critical_path.relative_to(ROOT)),followup_sha256=sha(critical_path),
        decision='Keep the adopted short-Cada decision for this accounting; its linguistic certainty is not established by this compilation review.',
        uncertainty='Two printed editions and explicit lexical contrast support short Cada, while the electronic same-locus long reading has unresolved edition provenance. The numerical range is conditional on that choice.',
        nonadopted_sensitivity='Accepting 66 additional Opus Cada responses would raise canonical accuracy to 91.5%; this is not an adopted grade change and is outside the displayed six-hold/nonanswer interval.',
        robust_to_all_source_uncertainty=False)
    shared = dict(created_at=datetime.now(timezone.utc).isoformat(),passed=True,
        analysis_sha256=sha(ap),review_script_sha256=sha(Path(__file__)),
        critical_stem_caveat=caveat,
        scope='Independent compilation/provenance verification of the new exact22-form layer and bounded source accounting; not independent recertification of all Sanskrit.',
        reviewed_records=3600,paid_calls=0,ledger_writes=0,frozen_or_shared_mutations=False,
        summaries=summaries,limitations=['Source judgments and their reviewed adoption documents are treated as inputs; this check does not rederive all linguistic decisions.',
          'Conditional bounds are historical accounting under unflagged keys and source decisions, not accuracy on repaired prompts and not bounds on undetected oracle defects.',
          'The source-layer pending queue remains its immutable pre-accounting queue; the separate bounded audit supplies the later decisions.'])
    save(HERE/'bounded-answer-audit-v1-review.json',dict(shared,
        bounded_answer_audit_sha256=sha(accounting_path),source_accounting_script_sha256=sha(HERE/'reconcile_source_audit.py'),
        all476_initial_misses_accounted=True,all_six_holds_applied_to_both_providers=True,
        prior_correct_rows_included=True,no_filtering=True,input_fingerprints_verified=len(accounting['input_fingerprints'])))
    save(LAYER/'independent-application-review.json',dict(shared,
        source_policy_digest=analysis['source_policy_digest'],exact_addition_counts=[19,2,1],
        exact_union_size=22,all3600_task_and_raw_fields_preserved=True,
        symmetric_application=True,missing837_is_none=True,
        preserved_original_fingerprints_verified=len(analysis['preserved_original_result_fingerprints']),
        source_evidence_fingerprints_verified=len(evidence_files)))
    for p in [HERE/'bounded-answer-audit-v1-review.json',LAYER/'independent-application-review.json']:
        print(p.relative_to(ROOT),sha(p))
    print('analysis_sha256',sha(ap))


if __name__=='__main__':
    main()
