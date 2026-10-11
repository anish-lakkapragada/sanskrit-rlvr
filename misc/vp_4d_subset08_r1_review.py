"""Independent input-only policy20 revision audit; no model answers or APIs."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_4d_subset08_review import read, sha, family, cell, cross, norm, walk, pairstats
from misc.vp_cartesian_task import entries_by_code, entry_scope_issue, oracle_issue, validate_task

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'benchmarks/parallel-search-20261006'
OLD = B / 'five_d/pilot-08'
P = OLD / 'revision-01'
S = P / 'astra-subset'
OUT = B / 'four_d/subset08-review/revision-01'


def contexts(ts):
    return {(t['derivation']['recipe_id'], r) for t in ts for r in t['campaign']['trace_rule_ids']}


def main():
    OUT.mkdir(exist_ok=True)
    ts, ss = read(P / 'tasks.json'), read(S / 'tasks.json')
    prior, prior_s = read(OLD / 'tasks.json'), read(OLD / 'astra-subset/tasks.json')
    pp, sp = read(P / 'plan.json'), read(S / 'plan.json')
    master = read(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json')
    paths = [P / 'tasks.json', S / 'tasks.json', P / 'plan.json', S / 'plan.json',
             P / 'manifest.json', S / 'manifest.json', ROOT / 'misc/vp_cartesian_task.py',
             ROOT / 'misc/vp_5d_subset_08_r1.py', B / 'oracle-policy-20.json']
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    assert sha(P / 'tasks.json') == '2bdd6cf611d99545d773a10a99c960bda1f25b6a349e74ff6f90952cba3e8f26'
    assert sha(P / 'tasks.json') == sp['source_tasks_sha256']
    assert sha(ROOT / 'misc/vp_cartesian_task.py') == sp['adapter_sha256']
    assert sha(ROOT / 'misc/vp_5d_subset_08_r1.py') == sp['selection_script_sha256']
    assert sp['policy'] == pp['oracle_policy'] == 'oracle-policy-20'
    for d in [P, S]:
        m = read(d / 'manifest.json')
        for name, v in m['files'].items():
            assert sha(d / name) == v['sha256'], (d, name)
        for v in m.get('source_hashes', {}).values():
            assert sha(Path(v['path'])) == v['sha256'], v['path']
    pm = {t['id']: t for t in ts}
    assert len(pm) == len(ts) == 2400 and len(ss) == len({t['id'] for t in ss}) == 240
    assert all(t == pm[t['id']] for t in ss)
    assert len({norm(t) for t in ts}) == 2400 and all(norm(t) for t in ts)
    for t in ts:
        e = entries_by_code()[t['dhatu']['code']]
        assert entry_scope_issue(e) is None and oracle_issue(t) is None
        assert master['families'][family(t)]['split'] == t['campaign']['split'] == 'development'
        assert t['dhatu']['code'] in master['families'][family(t)]['codes']
        assert t['task_type'] == 'cartesian_5d'
        assert set(t['morphology']) == {'lakara', 'prayoga', 'purusha', 'vacana'}
        assert set(t['derivation']) == {'recipe_id', 'sanadi', 'prefixes', 'order'}
        assert t['derivation']['prefixes'] == [] and t['derivation']['order'] == 'innermost_to_outermost'
        assert pp['recipe_operations'][t['derivation']['recipe_id']] == t['derivation']['sanadi']
        assert t['dhatu']['code'] not in {'05.0013', '05.0014', '05.0015'}
    for t in ss:
        validate_task(t, entries_by_code()[t['dhatu']['code']], 'development')
    for rows, plan in [(ts, pp), (ss, sp)]:
        assert dict(Counter(cell(t) for t in rows)) == plan['cell_counts']
        assert dict(Counter(t['dhatu']['gana'] for t in rows)) == plan['gana_counts']
        assert dict(Counter(t['derivation']['recipe_id'] for t in rows)) == plan['recipe_counts']
        assert dict(Counter(t['morphology']['lakara'] for t in rows)) == plan['lakara_counts']
        assert dict(Counter(t['morphology']['prayoga'] for t in rows)) == plan['prayoga_counts']
    for d, rows, sizes in [(P, ts, [400] * 6), (S, ss, [120] * 2)]:
        transport = read(d / 'transport-plan.json')
        chunks = [read(d / f'chunk-{i:02}.tasks.json') for i in range(1, len(sizes) + 1)]
        assert [len(c) for c in chunks] == sizes and sum(chunks, []) == rows
        for c, tr in zip(chunks, transport['chunks']):
            assert [t['id'] for t in c] == tr['ids']
            assert sha(Path(tr['tasks_path'])) == tr['sha256']
        if d == S:
            assert not {family(t) for t in chunks[0]} & {family(t) for t in chunks[1]}
    history = read(P / 'historical-inputs.json')
    seen, oldfamilies = set(), set()
    for rec in history['task_files']:
        p = Path(rec['path'])
        assert sha(p) == rec['sha256']
        for top in read(p):
            for t in walk(top):
                n = norm(t)
                if n:
                    seen.add(n)
                if t.get('campaign', {}).get('root_family'):
                    oldfamilies.add(family(t))
    assert not {norm(t) for t in ts} & seen
    parents, subs = pairstats(ts), pairstats(ss)
    assert parents['family_count'] == 670 and subs['family_count'] == sp['family_count'] == 116
    assert subs['counts'] == {'LL': 43, 'LN': 82, 'NN': 45}
    assert subs['families'] == {'LL': 43, 'LN': 42, 'NN': 33}
    assert subs['LL_recipes'] == sp['Lun_pair_recipe_counts']
    assert max(Counter(family(t) for t in ss).values()) == 3
    assert max(Counter(family(t) for t in ts).values()) <= pp['maximum_tasks_per_family']
    assert max(Counter(family(t) for t in ts if t['morphology']['lakara'] == 'Lun').values()) <= pp['maximum_Lun_per_family']
    assert all('desiderative' not in pair for pair in parents['LL_recipes'])
    oldmap, oldsub = {t['id']: t for t in prior}, {t['id']: t for t in prior_s}
    common = pm.keys() & oldmap.keys()
    for key in common:
        a, b = pm[key], oldmap[key]
        for k in ['task_type', 'prompt_version', 'dhatu', 'morphology', 'derivation', 'gold_slp1', 'gold_devanagari']:
            assert a[k] == b[k]
        for k in ['prompt_sha256', 'trace_rule_ids', 'root_family']:
            assert a['campaign'][k] == b['campaign'][k]
    oldplan = read(OLD / 'plan.json')
    for k in ['seed', 'recipe_counts', 'cell_counts', 'gana_counts', 'lakara_counts', 'prayoga_counts', 'person_number_counts', 'maximum_tasks_per_family', 'maximum_Lun_per_family']:
        assert pp[k] == oldplan[k], k
    for k in ['seed', 'cell_counts', 'gana_counts', 'recipe_counts', 'max_questions_per_family']:
        assert sp[k] == read(OLD / 'astra-subset/plan.json')[k]
    source_delta = read(P / 'source-rule-delta-audit.json')
    broad_prior = []
    for rec in source_delta['previous_input_sources']:
        p = Path(rec['path'])
        assert sha(p) == rec['sha256']
        broad_prior.extend(t for t in read(p)
            if entry_scope_issue(entries_by_code()[t['dhatu']['code']]) is None and oracle_issue(t) is None)
    assert not contexts(ts) - contexts(broad_prior)
    added_to_original = sorted(contexts(ts) - contexts(prior))
    context_support = []
    for recipe, rule in added_to_original:
        t = next(t for t in broad_prior if t['derivation']['recipe_id'] == recipe and rule in t['campaign']['trace_rule_ids'])
        context_support.append(dict(recipe=recipe, rule=rule, prior_current_scope_control_id=t['id'],
            prior_code=t['dhatu']['code'], prior_morphology=t['morphology']))
    pc, sc = Counter(cross(t) for t in ts), Counter(cross(t) for t in ss)
    missing = {c: n for c, n in pc.items() if not sc[c]}
    pcell, scall = Counter(cell(t) for t in ts), Counter(cell(t) for t in ss)
    weights = {c: pcell[c] / 2400 / (scall[c] / 240) for c in scall}
    ws, fw = [weights[cell(t)] for t in ss], defaultdict(float)
    for t in ss:
        fw[family(t)] += weights[cell(t)]
    result = dict(created_at=datetime.now(timezone.utc).isoformat(),
        disposition='PASS: exact input/membership/scope/novelty/support checks; diagnostic limits remain.',
        policy='oracle-policy-20', source_hashes=hashes,
        checks=dict(full_subset_regeneration=240, parent_scope_and_split=2400,
            exact_parent_dictionary_membership=240, exact_normalized_tuple_novelty=True,
            both_campaign_input_files=len(history['task_files']), exact_parent_and_subset_manifests=True,
            same_primary_and_subset_seeds_and_quotas=True, source_delta_no_new_recipe_rule_context_against_broad_comparator=True,
            both_120_chunks_keep_families_intact=True, exact_ordered_chunk_concatenation=True),
        parent=parents, subset=subs,
        revision_delta=dict(parent_shared_ids=len(common), parent_new_ids=len(pm.keys() - oldmap.keys()),
            subset_shared_ids=len({t['id'] for t in ss} & oldsub.keys()),
            subset_new_ids=len({t['id'] for t in ss} - oldsub.keys()),
            common_id_grammar_gold_prompt_unchanged=True, no_new_recipe_rule_contexts_against_broad_comparator=True,
            recipe_rule_contexts_added_versus_original08=context_support,
            explanation='Global input-only seeded allocation rerun after three-entry scope hold; no outputs used.'),
        Curadi={name: dict(Counter('Lun' if t['morphology']['lakara'] == 'Lun' else 'other' for t in rows if t['dhatu']['gana'] == 'Curadi')) for name, rows in [('parent', ts), ('subset', ss)]},
        unsupported_class_recipe_Lun_cells=missing, unsupported_cell_questions=sum(missing.values()),
        unsupported_cell_parent_share=sum(missing.values()) / 2400,
        calibration=dict(min_weight=min(ws), max_weight=max(ws), task_kish=sum(ws)**2 / sum(w*w for w in ws),
            family_total_kish=sum(fw.values())**2 / sum(w*w for w in fw.values()),
            meaning='42-cell weight concentration only; not independent sample size or design-unbiased correction.'),
        history=dict(normalized_tuples=len(seen), parent_previously_exposed_families=len({family(t) for t in ts} & oldfamilies),
            subset_previously_exposed_families=len({family(t) for t in ss} & oldfamilies),
            prior_exposure_caveat=master['prior_exposure'], scope='Two declared campaign histories, not globally never exposed families.'),
        limitations=['Only 43 independent LL families; no san LL support in parent or subset.',
            'LL class/recipe composition differs from parent; whole-family uncertainty and transport sensitivities remain necessary.',
            'Seeded constrained selection has unknown inclusion probabilities; it is not a probability sample.',
            'Full primary regeneration remains coordinator-owned; this independently regenerates all 240 subset questions.',
            'Allocation was not independently replayed; actual membership, code hashes, input-only selection code and constraints were checked.',
            'No mechanical audit certifies every generated paradigm or absence of historical model contamination.'],
        no_model_answers_read=True, no_paid_calls=True, no_shared_or_frozen_edits=True)
    for path, h in hashes.items():
        assert sha(ROOT / path) == h
    (OUT / 'membership-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['disposition', 'revision_delta', 'Curadi', 'unsupported_cell_questions', 'unsupported_cell_parent_share', 'calibration', 'history']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
