"""Materialize frozen RL metadata offline; no sampling, model calls or training."""
from collections import Counter
from pathlib import Path
import copy, datetime, hashlib, json, sys

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / 'misc/vp_cartesian_task.py').is_file())
sys.path.insert(0, str(ROOT))
from misc.vp_cartesian_task import entries_by_code, make_task, validate_task, entry_scope_issue, oracle_issue
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_4d_pilot04 import COORDS, local_issue
from misc.vp_4d_pilot05 import short
from misc.vp_campaign_candidates import family, name
from finetune.prompts import slp1_to_devanagari

SOURCE = OUT.parent
BASE = SOURCE.parent.parent
BENCH = BASE / 'candidate-1800-v1'
PLAN = BASE / 'final1800-64k-01/execution-plan.json'
CELLS = {'short_adanta_non_aorist': 728, 'other_adanta_aorist': 112, 'broad_non_curadi': 560}
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v): return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n, v):
    p = OUT / n
    if p.exists(): raise RuntimeError('Preserve existing export: ' + n)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')
def jsonl(n, rows):
    p = OUT / n
    if p.exists(): raise RuntimeError('Preserve existing export: ' + n)
    p.write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in rows))
def fam(t): return t['dhatu']['aupadeshika'] + '|' + t['dhatu']['gana']
def family_coordinate(t): return (t['dhatu']['aupadeshika'], t['dhatu']['gana'], *(t['morphology'][k] for k in COORDS))
def public_tuple(t): return (t['dhatu']['aupadeshika'], t['dhatu']['gana'], t['dhatu']['artha'], *(t['morphology'][k] for k in COORDS))

def main():
    if (OUT / 'tasks.json').exists(): raise RuntimeError('Materialized export already exists')
    plan = read(PLAN)
    protected = plan['dependencies']
    assert not any((ROOT / p).resolve().is_relative_to(OUT) for p in protected)
    assert all(sha(ROOT / p) == h for p, h in protected.items()), 'Paid execution dependency mismatch before export'
    strict_files = {str(p.relative_to(ROOT)): sha(p) for p in SOURCE.iterdir() if p.is_file()}
    source_manifest = read(SOURCE / 'curriculum-manifest.json')
    for group in ('files', 'source_dependencies'):
        for rel, h in source_manifest[group].items(): assert sha(ROOT / rel) == h, rel
    master_path = ROOT / source_manifest['master_split_path']
    assert sha(master_path) == source_manifest['master_split_sha256']
    master = read(master_path)['families']
    blocked_citations = {f.rsplit('|', 1)[0] for f, v in master.items() if v['split'] in ('development', 'test')}
    blocked_rendered = {slp1_to_devanagari(c) for c in blocked_citations}
    source_policy = read(BENCH / 'source-policy.json')
    predicates = source_policy['previous_holds']['predicates'] + [source_policy['additional_exclusion']]
    rows = read(SOURCE / 'curriculum-1400-metadata.json')
    inventory = {r['id']: r for r in read(SOURCE / 'training-inventory-metadata.json')}
    assert len(rows) == 1400 and [r['position'] for r in rows] == list(range(1400))
    assert len({r['id'] for r in rows}) == 1400 and Counter(r['cell'] for r in rows) == CELLS
    for block in range(56):
        block_rows = rows[block * 25:(block + 1) * 25]
        assert {r['block'] for r in block_rows} == {block}
        assert Counter(r['cell'] for r in block_rows) == dict(zip(CELLS, [13, 2, 10]))
    es = entries_by_code()
    tasks, prompts, publics, golds, failures = [], [], [], [], []
    for r in rows:
        try:
            assert {k: v for k, v in r.items() if k not in ('position', 'block')} == inventory[r['id']]
            e = es[r['code']]
            assert not entry_scope_issue(e)
            assert family(e) == r['family'] and master[r['family']]['split'] == r['split'] == 'rl_train'
            assert r['code'] in master[r['family']]['codes']
            assert all(family(es[c]) == r['family'] and master[family(es[c])]['split'] == 'rl_train' for c in r['equivalent_codes'])
            assert e.dhatu.aupadeshika == r['aupadeshika'] and name(e.dhatu.gana) == r['gana'] and e.artha == r['artha']
            assert r['aupadeshika'] not in blocked_citations and slp1_to_devanagari(r['aupadeshika']) not in blocked_rendered
            t = make_task(e, 'rl_train', {k: r[k] for k in COORDS})
            assert t is not None and t['id'] == r['id']
            validate_task(t, e, 'rl_train')
            assert not oracle_issue(t) and not local_issue(t)
            assert not any(r['code'] == p['code'] and p['lakara'] in ('all', r['lakara'])
                and ('sampling_cell' not in p or p['sampling_cell'] == r['cell']) for p in predicates)
            if r['cell'] == 'short_adanta_non_aorist': assert short(e) and r['lakara'] != 'Lun'
            elif r['cell'] == 'other_adanta_aorist': assert r['gana'] == 'Curadi' and r['aupadeshika'].endswith('a') and not short(e) and r['lakara'] == 'Lun'
            else: assert r['cell'] == 'broad_non_curadi' and r['gana'] != 'Curadi'
            assert t['task_type'] == 'cartesian_4d' and t['prompt_version'] == 'cartesian-4d-v1'
            assert set(t['morphology']) == set(COORDS) and t['morphology']['prayoga'] == 'Kartari'
            assert 'derivation' not in t and not any(k in t['dhatu'] for k in ('prefixes', 'sanadi', 'pada'))
            assert digest(t['gold_slp1']) == r['canonical_gold_slp1_sha256']
            assert len(t['gold_slp1']) == r['canonical_gold_variants']
            prompt = render(t)
            assert 'Sanskrit verbal root' in prompt
            assert hashlib.sha256(prompt.encode()).hexdigest() == r['prompt_sha256'] == t['campaign']['prompt_sha256']
            assert render({k: v for k, v in t.items() if k not in ('campaign', 'gold_slp1', 'gold_devanagari')}) == prompt
            t['campaign']['curriculum'] = {'position': r['position'], 'block': r['block'], 'cell': r['cell'],
                'metadata_id': r['id'], 'membership_or_order_changed': False}
            tasks.append(t)
            prompts.append({'id': t['id'], 'position': r['position'], 'block': r['block'], 'prompt': prompt})
            publics.append({'id': t['id'], 'position': r['position'], 'block': r['block'], 'split': 'rl_train',
                'task_type': t['task_type'], 'prompt_version': t['prompt_version'], 'dhatu': copy.deepcopy(t['dhatu']),
                'morphology': copy.deepcopy(t['morphology']), 'prompt': prompt})
            golds.append({'id': t['id'], 'position': r['position'], 'gold_slp1': t['gold_slp1'],
                'gold_devanagari': t['gold_devanagari'], 'canonical_gold_variants': len(t['gold_slp1']),
                'canonical_gold_slp1_sha256': digest(t['gold_slp1']), 'acceptance': 'Any member of the complete canonical union; finite spelling proposal is separate and not yet adopted.'})
        except Exception as exc:
            failures.append({'position': r['position'], 'id': r['id'], 'code': r['code'],
                             'type': type(exc).__name__, 'detail': str(exc) or 'Validation assertion failed'})
    if failures:
        save('blockers.json', {'created_at': stamp(), 'blocked': failures, 'membership_changed': False,
            'partial_export_written': False, 'training_started': False, 'provider_calls': 0})
        raise RuntimeError(f'{len(failures)} original curriculum rows blocked; no rows replaced')
    assert len(tasks) == len({t['id'] for t in tasks}) == len({public_tuple(t) for t in tasks}) == len({p['prompt'] for p in prompts}) == 1400
    assert [t['id'] for t in tasks] == [r['id'] for r in rows]
    heldout = read(BENCH / 'tasks.json')
    heldout_prompts = read(BENCH / 'public-prompts.json')
    overlap = {
        'family': len({fam(t) for t in tasks} & {fam(t) for t in heldout}),
        'raw_citation': len({t['dhatu']['aupadeshika'] for t in tasks} & {t['dhatu']['aupadeshika'] for t in heldout}),
        'rendered_citation': len({slp1_to_devanagari(t['dhatu']['aupadeshika']) for t in tasks} & {slp1_to_devanagari(t['dhatu']['aupadeshika']) for t in heldout}),
        'family_coordinate': len({family_coordinate(t) for t in tasks} & {family_coordinate(t) for t in heldout}),
        'public_tuple': len({public_tuple(t) for t in tasks} & {public_tuple(t) for t in heldout}),
        'prompt': len({p['prompt'] for p in prompts} & {p['prompt'] for p in heldout_prompts})}
    assert not any(overlap.values())
    assert all(sha(ROOT / p) == h for p, h in strict_files.items()), 'Original strict-citation file changed'
    assert all(sha(ROOT / p) == h for p, h in protected.items()), 'Paid execution dependency mismatch after regeneration'
    fc = Counter(fam(t) for t in tasks)
    save('tasks.json', tasks)
    save('public-prompts.json', prompts)
    jsonl('public-tasks.jsonl', publics)
    jsonl('canonical-gold.jsonl', golds)
    (OUT / 'curriculum-metadata.json').write_bytes((SOURCE / 'curriculum-1400-metadata.json').read_bytes())
    (OUT / 'source-policy.json').write_bytes((BENCH / 'source-policy.json').read_bytes())
    distribution = {k: dict(Counter(t['morphology'][k] for t in tasks)) for k in COORDS}
    distribution['gana'] = dict(Counter(t['dhatu']['gana'] for t in tasks))
    audit = {'created_at': stamp(), 'mechanical_audit_passed': True, 'n': 1400, 'families': len(fc),
        'blocks': 56, 'every_block_composition': dict(zip(CELLS, [13, 2, 10])), 'component_counts': CELLS,
        'max_family_load': max(fc.values()), 'family_load_sum_of_squares': sum(n*n for n in fc.values()),
        'distinct_family_coordinate_keys': len({family_coordinate(t) for t in tasks}), 'distribution': distribution,
        'metadata_ids_positions_blocks_order_preserved': True, 'all_canonical_unions_and_prompt_hashes_match_metadata': True,
        'canonical_task_form_entries': sum(len(t['gold_slp1']) for t in tasks), 'unique_public_prompts': 1400,
        'public_exports_contain_no_gold_or_trace_fields': True, 'gold_removal_leaves_prompts_unchanged': True,
        'original_four_coordinates_only': True, 'added_sanadi_prefixes_or_selected_pada': False,
        'all_master_rl_train': True, 'all_current_source_guards_passed': True,
        'all_master_development_test_raw_citation_overlap': 0, 'all_master_development_test_rendered_citation_overlap': 0,
        'heldout1800_overlap_counts': overlap, 'protected_paid_dependencies_checked_unchanged': len(protected),
        'preserved_original_file_hashes': strict_files, 'paid_execution_plan_sha256': sha(PLAN),
        'source_certification': 'Mechanical regeneration and inherited bounded source policy; not independent primary-source certification of every form or complete spelling universe.',
        'blockers': [], 'replacements': 0, 'model_outputs_read': False, 'provider_calls': 0,
        'training_started': False, 'split_changes': False, 'heldout_inputs_changed': False}
    save('materialization-audit.json', audit)
    manifest = {'created_at': stamp(), 'status': 'materialized_training_data_not_a_trained_model; spelling_reward_policy_pending_independent_review',
        'n': 1400, 'split': 'rl_train', 'families': len(fc), 'component_counts': CELLS,
        'metadata_membership_and_order_preserved': True, 'public_tasks_path': 'public-tasks.jsonl',
        'private_canonical_gold_path': 'canonical-gold.jsonl', 'combined_inspection_path': 'tasks.json',
        'files': {n: sha(OUT/n) for n in ['materialize.py', 'tasks.json', 'public-prompts.json', 'public-tasks.jsonl', 'canonical-gold.jsonl', 'curriculum-metadata.json', 'source-policy.json', 'materialization-audit.json']},
        'dependencies': {str(p.relative_to(ROOT)): sha(p) for p in [SOURCE/'curriculum-manifest.json', SOURCE/'curriculum-1400-metadata.json', SOURCE/'training-inventory-metadata.json', master_path, BENCH/'tasks.json', BENCH/'public-prompts.json', BENCH/'source-policy.json', PLAN]},
        'inherited_source_dependencies': source_manifest['source_dependencies'],
        'export_format': {'public': 'One JSON object per line, in original curriculum order; give only prompt to the model.',
            'gold': 'One keyed answer-union object per line in the same order; retain every accepted canonical variant, not only the first.',
            'blocks': '56 consecutive25-question blocks each retain13 short-adanta non-Lun,2 other-adanta Lun and10 broad questions.'},
        'limitations': ['No model has been trained, scored or shown to improve using this export.',
            'The hard short-adanta training component contains nine lexical families; many coordinates do not add independent families.',
            'Exact citation/family separation does not prove absence of shared stems, related meanings or pretraining exposure.',
            'Canonical unions inherit the audited VP oracle and remaining source limitations; do not penalize a source-licensed unfamiliar spelling without adjudication.',
            'A separate finite spelling proposal requires independent review before becoming a reward policy; unknown usable outputs require source review.',
            'All questions use Kartari within the original four-coordinate format; no claim to cover the full voice Cartesian product.'],
        'training_started': False, 'provider_calls': 0, 'model_outputs_read': False, 'paid_dependencies_changed': False}
    save('manifest.json', manifest)
    assert all(sha(ROOT / p) == h for p, h in protected.items())
    print(json.dumps({'n': len(tasks), 'families': len(fc), 'distribution': distribution,
        'canonical_forms': audit['canonical_task_form_entries'], 'overlap': overlap,
        'tasks_sha256': sha(OUT/'tasks.json'), 'public_jsonl_sha256': sha(OUT/'public-tasks.jsonl'),
        'gold_jsonl_sha256': sha(OUT/'canonical-gold.jsonl'), 'paid_dependencies_unchanged': True}, indent=2))

if __name__ == '__main__': main()
