"""Bounded independent audit of the two-input policy21 pilot08 repair."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_4d_subset08_review import read, sha, family, cell, cross, norm, walk, pairstats
from misc.vp_cartesian_task import entries_by_code, entry_scope_issue, oracle_issue, validate_task

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'benchmarks/parallel-search-20261006'
P = B / 'five_d/pilot-08/revision-02'
S = P / 'astra-subset'
OLD = P.parent / 'revision-01'
OUT = B / 'four_d/subset08-review/revision-02'
REPLACEMENTS = {
    'cart5-3407cf02c7272a95e35aa5d2': 'cart5-cb80bcbbb4a6d0de9546d536',
    'cart5-95a72032f74081e76f462424': 'cart5-8f33981e77d582f64a166270',
}


def contexts(rows):
    return {(t['derivation']['recipe_id'], r) for t in rows for r in t['campaign']['trace_rule_ids']}


def main():
    OUT.mkdir(exist_ok=True)
    ts, ss = read(P / 'tasks.json'), read(S / 'tasks.json')
    oldts, oldss = read(OLD / 'tasks.json'), read(OLD / 'astra-subset/tasks.json')
    pp, sp = read(P / 'plan.json'), read(S / 'plan.json')
    master = read(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json')
    paths = [P / 'tasks.json', S / 'tasks.json', P / 'plan.json', S / 'plan.json',
             P / 'manifest.json', S / 'manifest.json', ROOT / 'misc/vp_cartesian_task.py', B / 'oracle-policy-21.json']
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    assert len(ts) == len({t['id'] for t in ts}) == 2400
    assert len(ss) == len({t['id'] for t in ss}) == 240
    assert pp['oracle_policy'] == sp['policy'] == 'oracle-policy-21'
    assert sha(P / 'tasks.json') == sp['source_tasks_sha256']
    assert sha(ROOT / 'misc/vp_cartesian_task.py') == sp['adapter_sha256']
    for d in [P, S]:
        manifest = read(d / 'manifest.json')
        for name, v in manifest['files'].items():
            assert sha(d / name) == v['sha256'], (d, name)
        for v in manifest.get('source_hashes', {}).values():
            assert sha(Path(v['path'])) == v['sha256'], v['path']
    pm = {t['id']: t for t in ts}
    assert all(t == pm[t['id']] for t in ss)
    assert len({norm(t) for t in ts}) == 2400 and all(norm(t) for t in ts)
    for t in ts:
        e = entries_by_code()[t['dhatu']['code']]
        assert entry_scope_issue(e) is None and oracle_issue(t) is None
        assert master['families'][family(t)]['split'] == t['campaign']['split'] == 'development'
        assert t['dhatu']['code'] in master['families'][family(t)]['codes']
        assert set(t['morphology']) == {'lakara', 'prayoga', 'purusha', 'vacana'}
        assert t['task_type'] == 'cartesian_5d'
        assert set(t['derivation']) == {'recipe_id', 'sanadi', 'prefixes', 'order'}
        assert t['derivation']['prefixes'] == [] and t['derivation']['order'] == 'innermost_to_outermost'
        assert pp['recipe_operations'][t['derivation']['recipe_id']] == t['derivation']['sanadi']
    for t in ss:
        validate_task(t, entries_by_code()[t['dhatu']['code']], 'development')
    for rows, oldrows, plan in [(ts, oldts, pp), (ss, oldss, sp)]:
        assert [t['id'] for t in rows] == [REPLACEMENTS.get(t['id'], t['id']) for t in oldrows]
        before = {t['id']: t for t in oldrows}
        for t in rows:
            if t['id'] not in before:
                continue
            old = before[t['id']]
            for k in ['task_type', 'prompt_version', 'dhatu', 'morphology', 'derivation', 'gold_slp1', 'gold_devanagari']:
                assert t[k] == old[k]
            for k in ['prompt_sha256', 'trace_rule_ids', 'root_family']:
                assert t['campaign'][k] == old['campaign'][k]
        assert Counter(cell(t) for t in rows) == Counter(cell(t) for t in oldrows) == Counter(plan['cell_counts'])
        assert Counter(t['dhatu']['gana'] for t in rows) == Counter(t['dhatu']['gana'] for t in oldrows) == Counter(plan['gana_counts'])
        assert Counter(family(t) for t in rows) == Counter(family(t) for t in oldrows)
        for key in ['lakara', 'prayoga', 'purusha', 'vacana']:
            assert Counter(t['morphology'][key] for t in rows) == Counter(t['morphology'][key] for t in oldrows)
        assert Counter((t['morphology']['purusha'], t['morphology']['vacana']) for t in rows) == Counter((t['morphology']['purusha'], t['morphology']['vacana']) for t in oldrows)
    for d, olddir, rows, sizes in [(P, OLD, ts, [400] * 6), (S, OLD / 'astra-subset', ss, [120] * 2)]:
        chunks = [read(d / f'chunk-{i:02}.tasks.json') for i in range(1, len(sizes) + 1)]
        assert [len(c) for c in chunks] == sizes and sum(chunks, []) == rows
        for i, c in enumerate(chunks, 1):
            oc = read(olddir / f'chunk-{i:02}.tasks.json')
            assert [t['id'] for t in c] == [REPLACEMENTS.get(t['id'], t['id']) for t in oc]
            assert Counter(cell(t) for t in c) == Counter(cell(t) for t in oc)
            assert Counter((t['morphology']['purusha'], t['morphology']['vacana']) for t in c) == Counter((t['morphology']['purusha'], t['morphology']['vacana']) for t in oc)
        for c, tr in zip(chunks, read(d / 'transport-plan.json')['chunks']):
            assert [t['id'] for t in c] == tr['ids'] and sha(Path(tr['tasks_path'])) == tr['sha256']
        if d == S:
            assert not {family(t) for t in chunks[0]} & {family(t) for t in chunks[1]}
    hist = read(P / 'historical-inputs.json')
    seen, hf = set(), set()
    for rec in hist['task_files']:
        p = Path(rec['path'])
        assert sha(p) == rec['sha256']
        for top in read(p):
            for t in walk(top):
                if norm(t):
                    seen.add(norm(t))
                if t.get('campaign', {}).get('root_family'):
                    hf.add(family(t))
    assert not {norm(t) for t in ts} & seen
    parents, subs = pairstats(ts), pairstats(ss)
    for new, old in [(parents, pairstats(oldts)), (subs, pairstats(oldss))]:
        for key in ['counts', 'families', 'LL_recipes', 'LL_classes', 'family_count', 'load_histogram']:
            assert new[key] == old[key], key
    assert parents['family_count'] == 670 and subs['family_count'] == 116
    assert subs['counts'] == {'LL': 43, 'LN': 82, 'NN': 45}
    assert len({cell(t) for t in ss}) == 42 and len({t['dhatu']['gana'] for t in ss}) == 10
    assert not contexts(ts) - contexts(oldts)
    missing = {k: v for k, v in Counter(cross(t) for t in ts).items() if k not in Counter(cross(t) for t in ss)}
    family_rows = defaultdict(list)
    for t in ts:
        family_rows[family(t)].append(t)
    objective = dict(distinct_families=len(family_rows),
        repeated_lakara_assignments=sum(sum(max(v - 1, 0) for v in Counter(t['morphology']['lakara'] for t in rows).values()) for rows in family_rows.values()),
        sum_squared_family_loads=sum(len(rows)**2 for rows in family_rows.values()))
    declared_objective = read(P / 'minimal-repair-audit.json')['objective']
    assert all(declared_objective[k] == v for k, v in objective.items())
    result = dict(created_at=datetime.now(timezone.utc).isoformat(), policy='oracle-policy-21',
        disposition='PASS: bounded two-task revision, source blocker removed, input/mechanical/support checks pass.',
        source_hashes=hashes, parent_scope_and_split_checked=2400, subset_fully_regenerated=240,
        exact_parent_dictionary_membership=True, exact_only_two_id_replacements=REPLACEMENTS,
        common_primary_grammar_gold_trace_prompt_unchanged=2398,
        common_subset_grammar_gold_trace_prompt_unchanged=238,
        replacements=[pm[i] for i in REPLACEMENTS.values()],
        fixed_order_and_chunk_cell_PN_counts_unchanged=True, family_loads_and_all_aggregate_pair_support_unchanged=True,
        subset_families_disjoint_across_transport=True, no_new_recipe_rule_contexts_versus_revision01=True,
        parent=parents, subset=subs, unsupported_class_recipe_Lun_cells=missing,
        independently_recomputed_objective=objective,
        replacement_trace_path=str((OUT / 'replacement-controls.json').relative_to(ROOT)),
        replacement_trace_sha256=sha(OUT / 'replacement-controls.json'),
        unsupported_parent_question_count=sum(missing.values()),
        history=dict(task_files=len(hist['task_files']), normalized_tuples=len(seen),
            overlap=0, parent_previously_exposed_families=len({family(t) for t in ts} & hf),
            subset_previously_exposed_families=len({family(t) for t in ss} & hf),
            prior_exposure=master['prior_exposure']),
        limits='Input-only development diagnostic, not independent-family replication or final qualification. Unknown inclusion probabilities, only43LLfamilies, noSANLLsupport, and fine-cell transport gaps remain. No exhaustive grammatical certification.',
        no_model_answers_read=True, no_paid_calls=True, no_shared_or_frozen_edits=True)
    for path, expected in hashes.items():
        assert sha(ROOT / path) == expected
    (OUT / 'membership-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['disposition', 'source_hashes', 'history', 'unsupported_parent_question_count']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
