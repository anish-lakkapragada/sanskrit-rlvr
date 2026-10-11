"""Offline, input-only nested 1,800-question proposal. Never reads model answers."""
from collections import Counter, defaultdict
from pathlib import Path
import argparse, copy, hashlib, json, math, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_4d_pilot import HISTORY, load_entries, family, name, now, sha, write
from misc.vp_4d_pilot04 import COORDS, LAS, LOCAL_CODES, local_issue
from misc.vp_4d_pilot05 import short
from misc.vp_cartesian_task import make_task, validate_task, entry_scope_issue, oracle_issue
from misc.vp_cartesian_prompt_v1 import render
from finetune.prompts import slp1_to_devanagari

BASE = ROOT / 'benchmarks/parallel-search-20261007/four_d-90'
OLD = BASE / 'candidate-1250-v2'
OUT = BASE / 'candidate-1800-v1'
RL = BASE / 'rl-supply/strict-citation-option/training-inventory-metadata.json'
SEED = 'nested-exact4d-1800-v1-20261008'
QUOTAS = {'short_adanta_non_aorist': 936, 'other_adanta_aorist': 144, 'broad_non_curadi': 720}
PERSONS = ['Prathama', 'Madhyama', 'Uttama']
NUMBERS = ['Eka', 'Dvi', 'Bahu']

def read(p): return json.loads(p.read_text())
def rank(s): return hashlib.sha256((SEED + ':' + s).encode()).hexdigest()
def key(t): return (t['dhatu']['aupadeshika'], t['dhatu']['gana'], *(t['morphology'][k] for k in COORDS))
def rowkey(r): return (r['aupadeshika'], r['gana'], *(r[k] for k in COORDS))
def fam(t): return t['dhatu']['aupadeshika'] + '|' + t['dhatu']['gana']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--census-only', action='store_true')
    args = parser.parse_args()
    if (OUT / 'tasks.json').exists(): raise RuntimeError('Preserve existing proposal; use a new version')
    old = read(OLD / 'tasks.json')
    assert len(old) == 1250
    policy = read(OLD / 'source-policy.json')
    predicates = policy['previous_holds']['predicates'] + [policy['additional_exclusion']]
    assignments = read(HISTORY / 'family-split.json')['families']
    es = {e.code: e for e in load_entries()}
    rl = read(RL)
    rl_citations = {r['aupadeshika'] for r in rl}
    rl_rendered_citations = {slp1_to_devanagari(c) for c in rl_citations}
    inputs = sorted((ROOT / 'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json'))
    inputs += sorted((HISTORY / 'jobs').glob('*/tasks.json'))
    inputs += [ROOT / 'benchmarks/full-tasks.json', *sorted(HISTORY.glob('discovery-??.json'))]
    input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    prior, registered = set(), set()
    history_rows = 0
    for p in inputs:
        for outer in read(p):
            for t in outer.get('forms', [outer]):
                history_rows += 1
                d = t.get('dhatu', {})
                if '/jobs/' in str(p):
                    if 'aupadeshika' in d: registered.add(fam(t))
                    registered.update(m['aupadeshika'] + '|' + m['gana'] for m in d.get('members', []))
                    registered.update(t.get('campaign', {}).get('root_families', []))
                op = t.get('derivation', {})
                if ('aupadeshika' in d and set(t.get('morphology', {})) == set(COORDS)
                        and not any(op.get(k) for k in ('sanadi', 'prefixes', 'pada')) and not d.get('pada')):
                    prior.add(key(t))
    hard_families = {c: {fam(t) for t in old if t['campaign']['sampling_cell']['label'] == c}
                     for c in QUOTAS if c != 'broad_non_curadi'}
    assert {c: len(f) for c, f in hard_families.items()} == {'short_adanta_non_aorist': 14, 'other_adanta_aorist': 21}
    def held(code, la, cell):
        return any(code == p['code'] and p['lakara'] in ('all', la)
                   and ('sampling_cell' not in p or p['sampling_cell'] == cell) for p in predicates)

    rows, dedup, rejects = [], set(), Counter()
    attempts = 0
    for e in sorted(es.values(), key=lambda x: x.code):
        f, g = family(e), name(e.dhatu.gana)
        if assignments[f]['split'] != 'test' or f in registered: continue
        if entry_scope_issue(e) or e.code in LOCAL_CODES: continue
        if e.dhatu.aupadeshika in rl_citations or slp1_to_devanagari(e.dhatu.aupadeshika) in rl_rendered_citations: continue
        if g != 'Curadi': cell, las = 'broad_non_curadi', LAS
        elif f in hard_families['short_adanta_non_aorist']:
            assert short(e)
            cell, las = 'short_adanta_non_aorist', [la for la in LAS if la != 'Lun']
        elif f in hard_families['other_adanta_aorist']:
            assert e.dhatu.aupadeshika.endswith('a') and not short(e)
            cell, las = 'other_adanta_aorist', ['Lun']
        else: continue
        for la in las:
            if held(e.code, la, cell): continue
            for pu in PERSONS:
                for va in NUMBERS:
                    attempts += 1
                    m = dict(lakara=la, prayoga='Kartari', purusha=pu, vacana=va)
                    t = make_task(e, 'test', m)
                    if not t: rejects['no_forms'] += 1; continue
                    if oracle_issue(t): rejects['oracle_hold'] += 1; continue
                    if local_issue(t): rejects['local_hold'] += 1; continue
                    k = key(t)
                    if k in prior: rejects['historical_tuple'] += 1; continue
                    if k in dedup: rejects['duplicate_raw_family_coordinate'] += 1; continue
                    dedup.add(k)
                    rows.append(dict(id=t['id'], code=e.code, family=f, gana=g,
                                     aupadeshika=e.dhatu.aupadeshika, cell=cell, **m))
    supply = {}
    for c in QUOTAS:
        rs = [r for r in rows if r['cell'] == c]
        fc = Counter(r['family'] for r in rs)
        supply[c] = dict(families=len(fc), fresh_tuples=len(rs), per_family=dict(sorted(fc.items())),
                         minimum_per_family=min(fc.values()), maximum_per_family=max(fc.values()))
    print(json.dumps({'phase': 'regenerated_supply', 'supply': {c: {k: v for k, v in s.items() if k != 'per_family'} for c, s in supply.items()}, 'attempts': attempts,
                      'rejections': dict(rejects), 'history_input_files': len(inputs)}), flush=True)
    if args.census_only: return
    assert supply['short_adanta_non_aorist']['fresh_tuples'] >= 936
    assert supply['other_adanta_aorist']['fresh_tuples'] >= 144
    assert supply['broad_non_curadi']['families'] >= 720
    assert {key(t) for t in old} <= dedup, 'Existing tasks no longer meet current input-only eligibility'
    assert not {fam(t) for t in old} & registered
    chosen = copy.deepcopy(old)
    occupied = {key(t) for t in old}
    remaining = [r for r in rows if rowkey(r) not in occupied]
    # Choose extra broad families by current class load, then a fixed input hash.
    # This distributes the extra coverage to scarce classes before common ones.
    old_broad = [t for t in old if t['campaign']['sampling_cell']['label'] == 'broad_non_curadi']
    old_broad_families = {fam(t) for t in old_broad}
    new_broad = {r['family']: r['gana'] for r in remaining if r['cell'] == 'broad_non_curadi' and r['family'] not in old_broad_families}
    class_load = Counter(t['dhatu']['gana'] for t in old_broad)
    new_broad_families = set()
    for _ in range(220):
        f = min(new_broad, key=lambda f: (class_load[new_broad[f]], rank('family:' + f)))
        new_broad_families.add(f)
        class_load[new_broad.pop(f)] += 1

    # All optimization inputs are coordinates, lexical membership and input hashes.
    # Exact balancing is independent of any gold text, trace complexity or model outcome.
    import highspy
    solvers, added = {}, []
    for cell, target in QUOTAS.items():
        existing = [t for t in old if t['campaign']['sampling_cell']['label'] == cell]
        rs = [r for r in remaining if r['cell'] == cell and
              (cell != 'broad_non_curadi' or r['family'] in new_broad_families)]
        rs.sort(key=lambda r: rank(cell + ':' + r['id']))
        h = highspy.Highs()
        for k, v in [('output_flag', False), ('threads', 1), ('random_seed', 20261008), ('time_limit', 60.)]: h.setOptionValue(k, v)
        xs = [h.addVariable(lb=0, ub=1, type=highspy.HighsVarType.kInteger) for r in rs]
        maps = {k: defaultdict(list) for k in ('family', 'lakara', 'purusha', 'vacana')}
        for r, x in zip(rs, xs):
            for k in maps: maps[k][r[k]].append(x)
        h.addConstr(h.qsum(xs) == target - len(existing))
        fc = Counter(fam(t) for t in existing)
        for f, vs in maps['family'].items():
            lo, hi = ((66, 67) if cell == 'short_adanta_non_aorist' else
                      (6, 7) if cell == 'other_adanta_aorist' else (1, 1))
            h.addConstr(h.qsum(vs) + fc[f] >= lo)
            h.addConstr(h.qsum(vs) + fc[f] <= hi)
        las = [la for la in LAS if la != 'Lun'] if cell == 'short_adanta_non_aorist' else ['Lun'] if cell == 'other_adanta_aorist' else LAS
        lc = Counter(t['morphology']['lakara'] for t in existing)
        for la in las: h.addConstr(h.qsum(maps['lakara'][la]) == target // len(las) - lc[la])
        for field, vals in [('purusha', PERSONS), ('vacana', NUMBERS)]:
            counts = Counter(t['morphology'][field] for t in existing)
            for value in vals: h.addConstr(h.qsum(maps[field][value]) == target // 3 - counts[value])
        h.minimize(h.qsum((i + 1) * x for i, x in enumerate(xs)))
        solution = h.getSolution()
        assert solution.value_valid, (cell, str(h.getModelStatus()))
        selected = [r for r, x in zip(rs, xs) if solution.col_value[int(x)] > .5]
        assert len(selected) == target - len(existing)
        solvers[cell] = {'status': str(h.getModelStatus()), 'candidate_rows': len(rs), 'selected_additions': len(selected)}
        for r in selected:
            t = make_task(es[r['code']], 'test', {k: r[k] for k in COORDS})
            assert t['id'] == r['id']
            t['campaign'].update(panel='source-filtered-1800-v1-proposal', seed=SEED,
                sampling_cell={'label': cell, 'n': target},
                selection={'method': 'Nested input-only extension of1250v2; class-balanced new broad families; exact tense/person/number and bounded-family constraints; seeded input-hash objective.'})
            chosen.append(t); added.append(t)
    assert len(chosen) == 1800
    chosen.sort(key=lambda t: rank('order:' + t['id']))
    tm = {t['id']: t for t in chosen}
    assert all(tm[t['id']] == t for t in old)
    public = [{'id': t['id'], 'prompt': render(t)} for t in chosen]
    assert len(tm) == len({key(t) for t in chosen}) == len({p['prompt'] for p in public}) == 1800
    for t in chosen:
        validate_task(t, es[t['dhatu']['code']], 'test')
        assert not entry_scope_issue(es[t['dhatu']['code']]) and not oracle_issue(t) and not local_issue(t)
        assert assignments[fam(t)]['split'] == 'test' and fam(t) not in registered and key(t) not in prior
        assert not held(t['dhatu']['code'], t['morphology']['lakara'], t['campaign']['sampling_cell']['label'])
        assert t['task_type'] == 'cartesian_4d' and t['prompt_version'] == 'cartesian-4d-v1'
        assert set(t['morphology']) == set(COORDS) and 'derivation' not in t
        assert render({k: v for k, v in t.items() if k not in ('campaign', 'gold_slp1', 'gold_devanagari')}) == render(t)
    fc = Counter(fam(t) for t in chosen)
    composition = dict(Counter(t['campaign']['sampling_cell']['label'] for t in chosen))
    distribution = {k: dict(Counter(t['morphology'][k] for t in chosen)) for k in COORDS}
    distribution['gana'] = dict(Counter(t['dhatu']['gana'] for t in chosen))
    assert composition == QUOTAS and len(fc) == 755 and max(fc.values()) == 67
    assert distribution['lakara'] == {la: 216 if la == 'Lun' else 176 for la in LAS}
    assert set(distribution['purusha'].values()) == set(distribution['vacana'].values()) == {600}
    assert len(distribution['gana']) == 10
    rl_keys = {(r['aupadeshika'], r['gana'], *(r[k] for k in COORDS)) for r in rl}
    assert not set(fc) & {r['family'] for r in rl}
    assert not {t['dhatu']['aupadeshika'] for t in chosen} & rl_citations
    assert not {slp1_to_devanagari(t['dhatu']['aupadeshika']) for t in chosen} & rl_rendered_citations
    assert not {key(t) for t in chosen} & rl_keys
    assert not {hashlib.sha256(p['prompt'].encode()).hexdigest() for p in public} & {r['prompt_sha256'] for r in rl}
    assert all(sha(ROOT / p) == s for p, s in input_hashes.items()), 'Historical inputs changed during generation'
    write(OUT / 'tasks.json', chosen)
    write(OUT / 'public-prompts.json', public)
    # Preserve the exact source declaration as a byte-for-byte copy.
    (OUT / 'source-policy.json').write_bytes((OLD / 'source-policy.json').read_bytes())
    write(OUT / 'supply.json', {'created_at': now(), 'attempts': attempts, 'rejections': dict(rejects), 'cells': supply,
        'scope': 'Fresh, source-policy-filtered master-test tuple regeneration; canonical VP regeneration is not independent full-form source certification.'})
    audit = {'created_at': now(), 'mechanical_audit_passed': True, 'retained_objects_unchanged': 1250,
        'removed_or_replaced_objects': 0, 'added_objects': 550, 'added_ids': [t['id'] for t in added],
        'added_by_cell': dict(Counter(t['campaign']['sampling_cell']['label'] for t in added)),
        'new_broad_families': sorted(new_broad_families), 'all1800_regenerate_with_complete_canonical_unions': True,
        'unique_ids_raw_family_coordinate_keys_and_prompts': 1800, 'gold_campaign_removal_leaves_all_prompts_unchanged': True,
        'original_four_coordinates_only': True, 'all_Kartari': True, 'selected_pada_prefixes_or_added_sanadi': False,
        'source_policy_identical_to1250v2': True, 'history': {'files': len(inputs), 'records': history_rows,
            'ordinary_unique_tuples': len(prior), 'registered_families': len(registered), 'tuple_overlap': 0, 'registered_family_overlap': 0},
        'strict_rl': {'inventory_rows': len(rl), 'families': len({r['family'] for r in rl}), 'family_overlap': 0,
            'raw_citation_overlap': 0, 'rendered_citation_overlap': 0, 'tuple_overlap': 0, 'prompt_hash_overlap': 0},
        'all_master_test': True, 'solvers': solvers, 'inputs': input_hashes,
        'full_source_certification': False, 'model_outputs_read': False, 'paid_calls': 0, 'split_changes': False}
    write(OUT / 'membership-audit.json', audit)
    dependencies = [Path(__file__), ROOT / 'misc/vp_cartesian_task.py', ROOT / 'misc/vp_cartesian_prompt_v1.py',
        ROOT / 'misc/vp_4d_pilot.py', ROOT / 'misc/vp_4d_pilot04.py', ROOT / 'misc/vp_4d_pilot05.py', ROOT / 'misc/vp_campaign_candidates.py',
        ROOT / 'finetune/prompts.py', ROOT / 'data/finetune/task-data/vidyut_dhatupatha_5.tsv',
        HISTORY / 'family-split.json', OLD / 'tasks.json', OLD / 'public-prompts.json', OLD / 'manifest.json',
        OLD / 'source-policy.json', OLD / 'independent-input-review.json', BASE / 'reading-clarification.json', RL]
    write(OUT / 'manifest.json', {'created_at': now(), 'status': 'unscored_proposal_pending_independent_review_not_registered',
        'n': 1800, 'families': len(fc), 'max_questions_per_family': max(fc.values()), 'family_size_histogram': dict(Counter(fc.values())),
        'composition': QUOTAS, 'distribution': distribution, 'retained1250_objects_unchanged': True, 'additions': 550,
        'tasks_sha256': sha(OUT / 'tasks.json'), 'public_prompts_sha256': sha(OUT / 'public-prompts.json'),
        'source_policy_sha256': sha(OUT / 'source-policy.json'), 'membership_audit_sha256': sha(OUT / 'membership-audit.json'),
        'supply_sha256': sha(OUT / 'supply.json'), 'seed': SEED,
        'selection': 'Keep all1250v2 full objects. Add286/44/220 using only source eligibility and coordinates. All14/21 hard families retained with66–67/6–7 each. Broad cell has720 distinct families;220 new families selected by least current class load then fixed input hash. Per-cell tenses and person/number are exactly balanced using a deterministic single-thread integer solver.',
        'retained_metadata_note': 'Old objects retain their original panel, seed and sampling_cell.n provenance; this manifest alone declares the new aggregate1800 allocation.',
        'precision': {'iid_se_percentage_points': {str(p): 100 * math.sqrt(p * (1-p) / 1800) for p in [.8, .805, .875, .9, .5]},
            'interpretation': 'N1800 projects less than1pp iid Bernoulli SE at current development rates and throughout80–90% accuracy. This is not a new-family SE claim and is not a95% interval half-width claim.',
            'family_limit': 'The52% hard short-adanta share still rests on14 test families. More coordinates cannot substitute for more independent lexical families; no sub1pp family-generalization SE is established.'},
        'source_review_extent': 'Inherited bounded lexical/rule controls and exclusions; every selected canonical form mechanically regenerated. Newly added forms are not each independently attested in primary sources. Full-paradigm certification not claimed.',
        'exposure_limit': 'No prior public ordinary tuples or registered-job root families overlap. Legacy dictionary-wide discovery inspected all families before the master split; never-inspected lexical families are not claimed.',
        'required_before_execution_or_release': ['Independent input and source-policy review', 'Review/adopt a finite spelling policy symmetrically before evaluating answers', 'Adjudicate every usable unrecognized answer against sources before final error claims', 'Register release allocation, budget and stopping/analysis policy; no outcome-based selection from this panel', 'Report both question-conditional and family-dependent uncertainty'],
        'inputs': input_hashes, 'dependencies': {str(p.relative_to(ROOT)): sha(p) for p in dependencies},
        'paid_calls': 0, 'test_model_answers_read': False, 'split_changes': False, 'benchmark_ready': False})
    print(json.dumps({'phase': 'complete', 'n': 1800, 'families': len(fc), 'distribution': distribution,
                      'solvers': solvers, 'tasks_sha256': sha(OUT / 'tasks.json')}), flush=True)

if __name__ == '__main__': main()
