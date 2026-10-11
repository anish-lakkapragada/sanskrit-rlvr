"""Offline exact-answer source layer. No network, ledger writes, or task filtering."""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent
RUN = OVERLAY.parent
ROOT = next(p for p in HERE.parents if (p / 'misc/vp_goal.py').exists())
PROVIDERS = ('Anthropic', 'OpenAI')
N, MISSING = 1800, 837


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def normalize(value):
    return unicodedata.normalize('NFC', value.strip())


def usable(row):
    return row['status'] == 'completed' and row['answer'] is not None and not row['truncated']


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def review_header(path):
    """Read only the first seven scalar metadata fields, never following scores."""
    keys = ('created_at', 'passed', 'mechanical_review_only', 'n_per_provider',
            'provider_responses', 'explicit_infrastructure_missing', 'missing_index')
    with Path(path).open() as stream:
        count = 0

        def char():
            nonlocal count
            value = stream.read(1)
            count += 1
            require(value and count <= 2048, 'Missing/oversized mechanical-review header')
            return value

        def nonspace():
            value = char()
            while value.isspace():
                value = char()
            return value

        def string(first=None):
            value = first if first is not None else nonspace()
            require(value == '"', 'Expected string metadata')
            raw, escaped = value, False
            while True:
                value = char()
                raw += value
                if value == '"' and not escaped:
                    return json.loads(raw)
                escaped = value == '\\' and not escaped

        require(nonspace() == '{', 'Mechanical review is not an object')
        header = {}
        for key in keys:
            require(string() == key and nonspace() == ':', 'Mechanical-review header changed')
            first = nonspace()
            if key == 'created_at':
                value = string(first)
                require(nonspace() == ',', 'Expected metadata separator')
            else:
                raw = first
                while True:
                    c = char()
                    if c == ',':
                        break
                    raw += c
                value = json.loads(raw)
                require(type(value) in (bool, int), 'Expected scalar metadata')
            header[key] = value
            if key == 'passed':
                require(value is True, 'Mechanical review has not passed; no result access')
            if key in ('n_per_provider', 'provider_responses', 'explicit_infrastructure_missing', 'missing_index'):
                require(type(value) is int, 'Counts must be integers, not booleans')
    require(header['mechanical_review_only'] is True and
            header['n_per_provider'] == N and header['provider_responses'] == 3599 and
            header['explicit_infrastructure_missing'] == 1 and header['missing_index'] == MISSING,
            'Mechanical review is for another cohort or missingness pattern')
    return header


def checked_path(path, expected):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    require(sha(path) == expected, 'Pinned file changed: ' + str(path))
    return path


def verify_tool():
    pin = read(HERE / 'tool-manifest.json')
    require(pin['schema'] == 'source-adjusted-tool-v1', 'Unknown tool manifest')
    for path, digest in pin['dependencies'].items():
        checked_path(path, digest)
    require(sha(Path(__file__)) == pin['tool_sha256'], 'Wrong source-layer implementation')
    return pin


def permission(pin, primary, independent):
    """Accounting, scalar headers, and passing review required before result loads."""
    carry = primary.carry
    plan, tasks, requests = primary.original.inspect_manifest(RUN)
    require(sha(RUN / 'execution-plan.json') == pin['execution_plan_sha256'], 'Plan changed')
    guard = carry.Guard(RUN, OVERLAY, plan, requests)
    require(guard.amendment_sha == pin['continuation_amendment_sha256'], 'Amendment changed')
    primary.check_review(OVERLAY, guard)
    state = primary.legacy.load()
    jobs = guard.state(state, adopted=True, allow_active=True)
    progress = guard.accounting.snapshot()
    independent.require_read_permission(OVERLAY, plan, guard.plan_sha, progress, jobs, guard.amendment_sha)
    review_path = OVERLAY / 'independent-review/completed-review/review.json'
    review_header(review_path)  # Stops before score fields if absent/failed.
    receipt = read(review_path)
    require(receipt['passed'] is True and receipt['score_disagreement_count'] == 0 and
            receipt['all_attempted_guard_passed'] is True and
            receipt['all_public_prompts_private_key_isolation_passed'] is True and
            receipt['execution_plan_sha256'] == guard.plan_sha and
            receipt['review_manifest_sha256'] == pin['mechanical_review_manifest_sha256'] and
            receipt['primary_analysis_sha256'] == sha(OVERLAY / 'analysis.json'),
            'Mechanical review does not bind this completed analysis')
    fingerprints = receipt['result_fingerprints']
    for provider in PROVIDERS:
        for filename in ('canonical.json', 'predeclared-spelling.json'):
            relative = str((OVERLAY / 'results' / provider / filename).relative_to(RUN))
            require(relative in fingerprints, 'Mechanical result fingerprint absent')
    for relative, digest in fingerprints.items():
        path = (RUN / relative).resolve()
        require(path.is_relative_to(RUN), 'Result fingerprint outside fixed run')
        checked_path(path, digest)
    return plan, tasks, receipt, review_path


def identity(item, tasks):
    require(item['task_id'] in tasks, 'Disposition for a question outside the fixed panel')
    task = tasks[item['task_id']]
    require(item['dhatu'] == task['dhatu'] and item['morphology'] == task['morphology'] and
            item['prompt_sha256'] == task['campaign']['prompt_sha256'] and
            task['campaign']['construction'] == 'ordinary_conjugation' and
            task['campaign']['split'] == 'test', 'Disposition identity differs from frozen input')
    return task['id']


def build_policy(pin, tasks, extension_path=None):
    """Exact additions plus independently reviewed future dispositions; no regex rules."""
    by_id = {t['id']: t for t in tasks}
    accepted, rejected, unresolved = {}, {}, {}
    evidence = []
    adoption_path = checked_path(pin['adoption_path'], pin['adoption_sha256'])
    adoption = read(adoption_path)
    require(adoption['execution_plan_sha256'] == pin['execution_plan_sha256'] and
            adoption['candidate_tasks_sha256'] == pin['tasks_sha256'] and
            adoption['public_prompts_sha256'] == pin['public_prompts_sha256'] and
            adoption['continuation_amendment_sha256'] == pin['continuation_amendment_sha256'] and
            adoption['status'] == 'adopted_exact_additions_for_separate_source_adjudicated_scoring' and
            len(adoption['accepted_additions']) == 19, 'Adoption identity or exact union changed')

    def add(items, field, destination, document_hash):
        seen = set()
        for item in items:
            task_id = identity(item, by_id)
            require(task_id not in seen, 'Duplicate disposition task in one category')
            seen.add(task_id)
            forms = item[field]
            require(isinstance(forms, list) and forms and all(isinstance(s, str) and normalize(s) and
                    not any(c.isspace() for c in normalize(s)) for s in forms), 'Require nonempty exact single-word forms')
            require(len({normalize(s) for s in forms}) == len(forms), 'Duplicate normalized answer')
            for form in forms:
                destination.setdefault((task_id, normalize(form)), []).append(document_hash)

    add(adoption['accepted_additions'], 'additional_forms_devanagari', accepted, pin['adoption_sha256'])
    require(len(accepted) == 19, 'Exact base 19-form union required')
    evidence.append(dict(kind='base_adoption', path=str(adoption_path.relative_to(ROOT)), sha256=sha(adoption_path)))
    if extension_path is not None:
        extension_path = Path(extension_path).resolve()
        manifest = read(extension_path)
        require(manifest['schema'] == 'reviewed-source-extensions-v1' and
                manifest['tool_manifest_sha256'] == sha(HERE / 'tool-manifest.json') and
                manifest['execution_plan_sha256'] == pin['execution_plan_sha256'] and
                manifest['candidate_tasks_sha256'] == pin['tasks_sha256'], 'Wrong extension manifest')
        evidence.append(dict(kind='extension_manifest', path=str(extension_path), sha256=sha(extension_path)))
        for entry in manifest['dispositions']:
            path = checked_path(entry['path'], entry['sha256'])
            rp = checked_path(entry['review_path'], entry['review_sha256'])
            review, document = read(rp), read(path)
            require(review.get('passed') is True and review['dispositions_sha256'] == entry['sha256'] and
                    review['execution_plan_sha256'] == pin['execution_plan_sha256'] and
                    review['candidate_tasks_sha256'] == pin['tasks_sha256'], 'Unreviewed source dispositions')
            require(document['schema'] == 'exact-task-source-dispositions-v1' and document['status'] == 'adopted' and
                    document['execution_plan_sha256'] == pin['execution_plan_sha256'] and
                    document['candidate_tasks_sha256'] == pin['tasks_sha256'] and document['symmetric_across_providers'] is True,
                    'Dispositions must retain fixed input identity and provider symmetry')
            require(document.get('source_dependencies'), 'Source evidence fingerprints required')
            for name, digest in document['source_dependencies'].items():
                checked_path(name, digest)
                evidence.append(dict(kind='extension_primary_source', path=name, sha256=digest))
            add(document.get('accepted_additions', []), 'additional_forms_devanagari', accepted, entry['sha256'])
            add(document.get('rejected_answers', []), 'forms_devanagari', rejected, entry['sha256'])
            add(document.get('unresolved_answers', []), 'forms_devanagari', unresolved, entry['sha256'])
            evidence.extend([dict(kind='disposition', path=str(path), sha256=sha(path)),
                             dict(kind='independent_source_review', path=str(rp), sha256=sha(rp))])
    require(not (set(accepted) & set(rejected)), 'Accepted and rejected dispositions conflict')
    # A later supported decision may resolve an earlier explicitly unresolved form.
    return dict(accepted=accepted, rejected=rejected, unresolved=unresolved, evidence=evidence)


def adjust_rows(rows, policy):
    adjusted, changes, queue, dispositions = copy.deepcopy(rows), [], [], []
    for original, row in zip(rows, adjusted):
        answer = row.get('answer')
        require(answer is None or isinstance(answer, str), 'Malformed extracted answer')
        key = (row['task']['id'], normalize(answer)) if answer is not None else None
        before = original['is_correct']
        require(before is None or type(before) is bool, 'Invalid original grade')
        require(not (key in policy['rejected'] and before is True),
                'Cannot silently revoke canonical/finite acceptance; a separate oracle revision is required')
        if before is None:
            disposition = 'unscored_original_status_preserved'
        elif before is True:
            disposition = 'canonical_or_finite_recognized'
        elif key in policy['accepted']:
            row['is_correct'] = True
            disposition = 'accepted_exact_source_form'
        elif key in policy['rejected']:
            disposition = 'source_rejected_exact_form'
        elif answer is None:
            disposition = 'unparsed_original_status_preserved'
        else:
            disposition = 'unresolved_requires_source_review'
        row['source_adjudication'] = dict(disposition=disposition, finite_is_correct=before,
            source_is_correct=row['is_correct'], accepted_policy_hashes=policy['accepted'].get(key, []),
            rejected_policy_hashes=policy['rejected'].get(key, []),
            unresolved_policy_hashes=policy['unresolved'].get(key, []))
        if row['is_correct'] is not before:
            changes.append(dict(task_id=row['task']['id'], task_index=row['task_index'], answer=answer,
                from_finite=before, to_source=row['is_correct'], evidence=policy['accepted'][key]))
        if usable(row) and disposition == 'unresolved_requires_source_review':
            queue.append(dict(task_id=row['task']['id'], task_index=row['task_index'], answer=answer,
                task=row['task'], disposition=disposition))
        if disposition in ('accepted_exact_source_form', 'source_rejected_exact_form'):
            dispositions.append(dict(task_id=row['task']['id'], task_index=row['task_index'],
                                     answer=answer, disposition=disposition))
        require({k: v for k, v in row.items() if k not in ('is_correct', 'source_adjudication')} ==
                {k: v for k, v in original.items() if k not in ('is_correct', 'source_adjudication')},
                'Source layer altered a raw field')
    return adjusted, changes, queue, dispositions


def compute(tasks, rowsets, policy, primary):
    models, adjusted, changes, pending, decisions = {}, {}, {}, {}, {}
    for provider in PROVIDERS:
        rows, changes[provider], pending[provider], decisions[provider] = adjust_rows(rowsets[provider], policy)
        adjusted[provider] = rows
        models[provider] = primary.describe(tasks, rows)
        stats = models[provider]['statistics']
        count = sum(r['is_correct'] is True for r in rows)
        stats['genuine_response_receipts'] = len(tasks) - (provider == 'OpenAI')
        stats['expected_infrastructure_missing'] = int(provider == 'OpenAI')
        stats['infrastructure_only_accuracy_bounds'] = [count/len(tasks), (count + int(provider == 'OpenAI'))/len(tasks)]
        # Bound only questions already flagged unresolved, plus genuinely nonusable
        # answers. This is not a bound on undetected oracle errors in accepted gold.
        known_usable = sum(r['is_correct'] is True and usable(r) for r in rows)
        nonusable = sum(not usable(r) for r in rows)
        stats['pending_source_and_missing_bounds'] = [known_usable/len(tasks),
            (known_usable + len(pending[provider]) + nonusable)/len(tasks)]
    require(adjusted['OpenAI'][MISSING]['is_correct'] is None and
            adjusted['OpenAI'][MISSING]['status'] == 'infrastructure_error' and
            adjusted['OpenAI'][MISSING]['answer'] is None, 'Infrastructure hole was changed')
    sensitivity = primary.sensitivity(tasks, adjusted['OpenAI'])
    paired_sensitivity = {}
    for label, value in [('missing_incorrect', False), ('missing_correct', True)]:
        imputed = copy.deepcopy(adjusted['OpenAI'])
        imputed[MISSING]['is_correct'] = value
        paired_sensitivity[label] = primary.contrast(imputed, adjusted['Anthropic'], imputation=value)
    return dict(models=models, paired=primary.contrast(adjusted['OpenAI'], adjusted['Anthropic']),
        infrastructure_sensitivity=dict(source=sensitivity, paired=paired_sensitivity),
        source_changes=changes, dispositions=decisions, unrecognized_usable_answers=pending,
        all_observed_usable_answers_dispositioned=not any(pending.values()),
        source_adjudication_complete=False, original_complete_gate_met=False,
        qualification_changed=False, benchmark_ready=False), adjusted


def run(extension_path=None):
    pin = verify_tool()
    sys.path.insert(0, str(ROOT))
    primary = module('source_layer_primary', OVERLAY / 'analyze.py')
    independent = module('source_layer_independent', OVERLAY / 'independent-review/review.py')
    # Retain the original coordinator exclusion around metadata and immutable reads.
    with primary.carry.prior.coordinator(RUN):
        plan, tasks, review, review_path = permission(pin, primary, independent)
        require(len(tasks) == N and len({t['id'] for t in tasks}) == N, 'Wrong fixed membership')
        policy = build_policy(pin, tasks, extension_path)
        policy_digest = hashlib.sha256(json.dumps(policy['evidence'], sort_keys=True).encode()).hexdigest()
        output = HERE / ('completed-' + policy_digest[:16])
        require(not output.exists(), 'Preserve prior source-layer output; use a new reviewed disposition version')
        rows = {}
        for provider in PROVIDERS:
            canonical = read(OVERLAY / 'results' / provider / 'canonical.json')
            finite = read(OVERLAY / 'results' / provider / 'predeclared-spelling.json')
            require(len(canonical) == len(finite) == N and
                    [r['task'] for r in canonical] == [r['task'] for r in finite] == tasks and
                    [r['task_index'] for r in finite] == list(range(N)), 'Result membership/order changed')
            require([r['task_index'] for r in finite if r['status'] == 'infrastructure_error'] ==
                    ([MISSING] if provider == 'OpenAI' else []), 'Unexpected infrastructure status')
            rows[provider] = finite
        value, adjusted = compute(tasks, rows, policy, primary)
        value = dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            state='complete_source_layer_pending_any_remaining_adjudication', n_per_provider=N,
            execution_plan_sha256=pin['execution_plan_sha256'],
            continuation_amendment_sha256=pin['continuation_amendment_sha256'],
            tool_manifest_sha256=sha(HERE / 'tool-manifest.json'),
            mechanical_review_sha256=sha(review_path), primary_analysis_sha256=review['primary_analysis_sha256'],
            source_policy_digest=policy_digest, source_evidence=policy['evidence'],
            preserved_original_result_fingerprints=review['result_fingerprints'],
            infrastructure_missing=dict(provider='OpenAI', index=MISSING, task_id=tasks[MISSING]['id'],
                is_correct=None, width=1/N, response_received=False, usage_settled=False),
            canonical_and_finite_layers='Preserved byte-identically at their reviewed paths; no original row rewritten.',
            uncertainty='Same describe/paired and both infrastructure imputations as primary analysis. IID and family SE remain separate. Pending-source bounds cover flagged answers only, not unknown errors in accepted gold.',
            no_outcome_membership_filtering=True, paid_calls=0, ledger_writes=0, **value)
        # Abort rather than publish a report if any reviewed input changes meanwhile.
        verify_tool()
        for relative, digest in review['result_fingerprints'].items():
            checked_path(RUN / relative, digest)
        for e in policy['evidence']:
            checked_path(e['path'], e['sha256'])
        with tempfile.TemporaryDirectory(dir=HERE, prefix='.source-layer-') as temporary:
            staging = Path(temporary) / 'output'
            staging.mkdir()
            for provider in PROVIDERS:
                (staging / (provider + '-source-adjusted.json')).write_text(json.dumps(adjusted[provider], ensure_ascii=False, indent=2) + '\n')
                (staging / (provider + '-pending-source.json')).write_text(json.dumps(value['unrecognized_usable_answers'][provider], ensure_ascii=False, indent=2) + '\n')
            (staging / 'analysis.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
            staging.rename(output)
        return dict(state=value['state'], output=str(output), benchmark_ready=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--score', action='store_true')
    parser.add_argument('--extension-manifest', type=Path)
    args = parser.parse_args()
    if not args.score:
        parser.error('Use --score only after complete primary analysis and passing independent review; tests use synthetic rows only')
    print(json.dumps(run(args.extension_manifest), indent=2))
