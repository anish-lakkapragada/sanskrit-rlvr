"""Offline pilot preparation for the isolated five-coordinate VP benchmark."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_cartesian_task import make_task, validate_task
from misc.vp_cartesian_prompt_v1 import render
from vidyut.prakriya import Vyakarana

OUT = ROOT / 'benchmarks/parallel-search-20261006/five_d'
HISTORY = ROOT / 'benchmarks/iterative-goal-20261006'
SPLIT = old.OUT / 'family-split.json'
SEED = 2026100605
RECIPES = {
    'causative': {'sanadi': ['Ric'], 'n': 10},
    'desiderative': {'sanadi': ['san'], 'n': 10},
    'intensive': {'sanadi': ['yaN'], 'n': 20},
    'intensive_luk': {'sanadi': ['yaNluk'], 'n': 20},
    'causative_of_intensive': {'sanadi': ['yaN', 'Ric'], 'n': 30},
    'desiderative_of_causative_of_intensive': {'sanadi': ['yaN', 'Ric', 'san'], 'n': 30},
}
LAKARAS = ['Lat', 'Lit', 'Lut', 'Lrt', 'Lot', 'Lan', 'VidhiLin', 'AshirLin', 'Lun', 'Lrn']
GANAS = {'Bhvadi': 48, 'Adadi': 10, 'Juhotyadi': 5, 'Divadi': 12,
         'Svadi': 8, 'Tudadi': 16, 'Rudhadi': 6, 'Tanadi': 2, 'Kryadi': 8, 'Curadi': 5}
EXCLUDED_RULES = {'7.4.79', '7.4.80', '7.4.94', '7.4.95', '8.3.61'}
VOWELS = set('aAiIuUfFxXeEoO')


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status(phase, message):
    OUT.mkdir(parents=True, exist_ok=True)
    atomic_json(OUT / 'status.json', {'track': 'five_d', 'updated_at': now(),
        'state': 'running', 'phase': phase, 'message': message, 'benchmark_ready': False})
    with (OUT / 'progress.md').open('a') as f:
        f.write(f'- {now()}: {message}\n')


def entries():
    assignments = json.loads(SPLIT.read_text())['families']
    unique = {}
    for e in old.load_entries():
        if assignments[old.family(e)]['split'] == 'development':
            unique.setdefault(old.family(e), e)
    return unique


def signature(task):
    d = task.get('derivation', {})
    if d.get('prefixes'):
        return None
    m = task.get('morphology', {})
    h = task.get('dhatu', {})
    if not all(x in m for x in ['lakara', 'prayoga', 'purusha', 'vacana']):
        return None
    return (h.get('aupadeshika'), h.get('gana'), tuple(d.get('sanadi', [])),
            *(m[x] for x in ['lakara', 'prayoga', 'purusha', 'vacana']))


def prior_signatures():
    # Only existing top-level development task inputs are traversed; never results.
    used = set()
    def visit(t):
        if not isinstance(t, dict):
            return
        if t.get('campaign', {}).get('split') == 'development':
            s = signature(t)
            if s is not None:
                used.add(s)
        for sub in t.get('forms') or []:
            visit(sub)
    for path in sorted(HISTORY.glob('*.json')):
        if path.name.startswith(('rl-', 'test-', 'reserved-')):
            continue
        data = json.loads(path.read_text())
        if isinstance(data, list):
            for t in data:
                visit(t)
    return used


def lexical_checks(entry, recipe, bases):
    if entry.dhatu.prefixes or entry.dhatu.sanadi:
        return 'hidden_dictionary_modifiers'
    ops = RECIPES[recipe]['sanadi']
    if ops[0] not in {'yaN', 'yaNluk'}:
        return None
    if old.name(entry.dhatu.gana) == 'Curadi':
        return 'intensive_excludes_curadi'
    roots = bases[old.family(entry)]
    if not roots or any(not r or r[0] in VOWELS or sum(c in VOWELS for c in r) != 1 for r in roots):
        return 'intensive_requires_consonant_initial_single_vowel_base'
    if any(r in {'ruc', 'SOB', 'SoB'} for r in roots):
        return 'traditional_nonusage_roch_shobh'
    return None


def task_for(entry, recipe, morphology, bases):
    issue = lexical_checks(entry, recipe, bases)
    if issue:
        return None, issue
    t = make_task(entry, 'development', morphology, recipe_id=recipe, sanadi=RECIPES[recipe]['sanadi'])
    if t is None:
        return None, 'empty_engine_derivation'
    if len(t['gold_slp1']) > 64:
        return None, 'more_than_64_variants'
    # Precautionary exclusion is specific to nested intensive constructions.
    if len(RECIPES[recipe]['sanadi']) > 1 and set(t['campaign']['trace_rule_ids']) & EXCLUDED_RULES:
        return None, 'unresolved_nested_rule_context'
    if (morphology['prayoga'] == 'Karmani' and morphology['lakara'] in {'Lut', 'Lrt'}
            and {'6.4.62', '6.4.92'} <= set(t['campaign']['trace_rule_ids'])):
        return None, 'unresolved_optional_cinvat_lengthening'
    return t, None


def slots():
    result = []
    for r, spec in RECIPES.items():
        for cycle in range(spec['n'] // 10):
            for la in LAKARAS:
                i = len(result)
                # 30 passive questions; only causal recipes in six reviewed tenses.
                passive = (r == 'causative' or (r in {'causative_of_intensive',
                    'desiderative_of_causative_of_intensive'} and cycle < 2)) and la in {
                        'Lat', 'Lan', 'Lot', 'VidhiLin', 'Lut', 'Lrt'}
                result.append({'recipe': r, 'morphology': {'lakara': la,
                    'prayoga': 'Karmani' if passive else 'Kartari',
                    'purusha': ['Prathama', 'Madhyama', 'Uttama'][i % 3],
                    'vacana': ['Eka', 'Dvi', 'Bahu'][(i // 3 + i) % 3]}})
    return result


def supply(es, bases):
    out = {}
    for recipe in RECIPES:
        accepted = []
        rejected = Counter()
        for family, entry in es.items():
            t, why = task_for(entry, recipe, {'lakara': 'Lat', 'prayoga': 'Kartari',
                'purusha': 'Prathama', 'vacana': 'Eka'}, bases)
            if t is None:
                rejected[why] += 1
            else:
                accepted.append(entry)
        out[recipe] = {'probe': 'Lat/Kartari/Prathama/Eka', 'families': len(accepted),
            'gana': dict(Counter(old.name(e.dhatu.gana) for e in accepted)),
            'rejections': dict(rejected)}
        status('Assessing development supply', f"The {recipe} recipe has {len(accepted)} eligible development families in the present-tense supply probe.")
    atomic_json(OUT / 'development-supply.json', {'created_at': now(), 'split': 'development',
        'total_families': len(es), 'recipes': out,
        'limitation': 'One present active probe per family and recipe; this is not a Cartesian supply census.'})


def generate():
    path = OUT / 'pilot-01.tasks.json'
    if path.exists():
        raise RuntimeError('Pilot membership is frozen; use audit or a new version')
    es = entries()
    bases = {f: sorted({p.text for p in Vyakarana().derive(e.dhatu)}) for f, e in es.items()}
    supply(es, bases)
    used_before = prior_signatures()
    all_slots = slots()
    rng = random.Random(SEED)
    rejection = Counter()
    tasks = None
    for attempt in range(100):
        free = list(range(120))
        assigned = {}
        # Place narrowly supplied classes first; class 10 only in simple recipes.
        for gana in ['Curadi', 'Tanadi', 'Juhotyadi', 'Svadi', 'Rudhadi', 'Adadi', 'Kryadi', 'Divadi', 'Tudadi', 'Bhvadi']:
            candidates = [i for i in free if gana != 'Curadi' or
                          all_slots[i]['recipe'] in {'causative', 'desiderative'}]
            if gana in {'Tanadi', 'Juhotyadi'}:
                candidates = [i for i in candidates if len(RECIPES[all_slots[i]['recipe']]['sanadi']) == 1]
            chosen = rng.sample(candidates, GANAS[gana])
            for i in chosen:
                assigned[i] = gana
                free.remove(i)
        families = set()
        chosen_tasks = []
        # Rare root classes first, then by deterministic randomized rank.
        rank = {i: rng.random() for i in range(120)}
        order = sorted(range(120), key=lambda i: (sum(old.name(e.dhatu.gana) == assigned[i] for e in es.values()), rank[i]))
        failed = False
        for i in order:
            slot = all_slots[i]
            candidates = [e for f, e in es.items() if f not in families and old.name(e.dhatu.gana) == assigned[i]]
            rng.shuffle(candidates)
            for e in candidates:
                t, why = task_for(e, slot['recipe'], slot['morphology'], bases)
                if t is None:
                    rejection[why] += 1
                    continue
                if signature(t) in used_before:
                    rejection['prior_development_tuple'] += 1
                    continue
                t['campaign'].update(panel='five-d-pilot-01', sampling_cell={
                    'recipe_id': slot['recipe'], 'lakaras': [slot['morphology']['lakara']],
                    'prayogas': [slot['morphology']['prayoga']],
                    'exclude_rules': sorted(EXCLUDED_RULES) if len(RECIPES[slot['recipe']]['sanadi']) > 1 else [],
                    'exclude_ganas': ['Curadi'] if RECIPES[slot['recipe']]['sanadi'][0] in {'yaN', 'yaNluk'} else []},
                    selection_reason='Predeclared recipe, tense, voice, person, number and class quotas; seeded lexical draw; grammatical validity and input novelty only.',
                    lexical_bases=bases[old.family(e)], slot=i)
                chosen_tasks.append(t)
                families.add(old.family(e))
                break
            else:
                failed = True
                break
        if not failed:
            tasks = chosen_tasks
            break
    if tasks is None:
        raise RuntimeError('The declared quota design has insufficient grammatical supply')
    rng.shuffle(tasks)
    atomic_json(path, tasks)
    atomic_json(OUT / 'pilot-01.manifest.json', {'created_at': now(), 'seed': SEED,
        'filename': path.name, 'n': len(tasks), 'split': 'development', 'recipes': RECIPES,
        'root_families': len({t['campaign']['root_family'] for t in tasks}), 'max_per_family': 1,
        'gana_quotas': GANAS, 'attempts_at_class_slot_assignment': attempt + 1,
        'rejections_during_sampling': dict(rejection), 'prior_tuple_signatures': len(used_before),
        'file_sha256': sha(path), 'generator_sha256': sha(Path(__file__)), 'family_split_sha256': sha(SPLIT),
        'dhatupatha_sha256': sha(old.TSV), 'shared_adapter_sha256': sha(ROOT / 'misc/vp_cartesian_task.py'),
        'prompt_renderer_sha256': sha(ROOT / 'misc/vp_cartesian_prompt_v1.py'),
        'selection': 'All pilot membership chosen without reference-model answers; rejected class-slot assignments use grammatical supply alone.',
        'test_and_training_policy': 'Existing root-family assignments preserved. Novelty checks consult development input coordinates only; no model results or held-out answers are inspected.'})
    status('Auditing generated pilot', f'Generated {len(tasks)} fresh tasks from {len(families)} development root families; beginning complete regeneration and source-example checks.')
    audit()


def audit():
    path = OUT / 'pilot-01.tasks.json'
    tasks = json.loads(path.read_text())
    es = {e.code: e for e in old.load_entries()}
    split = json.loads(SPLIT.read_text())['families']
    used_before = prior_signatures()
    prompt_hashes = set()
    for task in tasks:
        entry = es[task['dhatu']['code']]
        assert split[old.family(entry)]['split'] == 'development'
        validate_task(task, entry, 'development')
        assert signature(task) not in used_before
        assert task['derivation']['sanadi'] == RECIPES[task['derivation']['recipe_id']]['sanadi']
        assert task['campaign']['prompt_sha256'] not in prompt_hashes
        prompt_hashes.add(task['campaign']['prompt_sha256'])
        prompt = render(task)
        assert 'Sanskrit verbal root (dhatu,' in prompt
        assert 'upasarga' not in prompt.lower() and 'dhatu_pada' not in prompt
        assert '<answer></answer>' in prompt
    dist = {key: dict(Counter(t['morphology'][key] for t in tasks))
            for key in ['lakara', 'prayoga', 'purusha', 'vacana']}
    dist.update(recipe=dict(Counter(t['derivation']['recipe_id'] for t in tasks)),
                gana=dict(Counter(t['dhatu']['gana'] for t in tasks)),
                gold_variants=dict(Counter(len(t['gold_slp1']) for t in tasks)),
                person_number=dict(Counter(t['morphology']['purusha'] + '/' + t['morphology']['vacana'] for t in tasks)))
    assert dist['gana'] == GANAS
    assert set(dist['lakara'].values()) == {12}
    assert set(dist['purusha'].values()) == {40}
    assert set(dist['vacana'].values()) == {40}
    assert len({t['campaign']['root_family'] for t in tasks}) == 120
    atomic_json(OUT / 'pilot-01.audit.json', {'created_at': now(), 'n': len(tasks),
        'regeneration_passed': len(tasks), 'transliteration_roundtrip_passed': len(tasks),
        'exact_5d_schema_passed': len(tasks), 'fresh_input_tuples': len(tasks),
        'unique_prompts': len(prompt_hashes), 'root_families': 120, 'distribution': dist,
        'max_lakara_fraction': 0.10, 'max_recipe_fraction': 0.25, 'max_gana_fraction': 0.40,
        'source_example_audit': 'pilot-01.source-checks.json',
        'scope_limit': 'Mechanical audit plus construction references; not independent linguistic certification of all 120 rare-root forms.',
        'file_sha256': sha(path)})
    atomic_json(OUT / 'pilot-01.prompts.json', [{'id': t['id'], 'prompt': render(t)} for t in tasks])
    print(json.dumps({'n': len(tasks), 'families': 120, 'distribution': dist}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['generate', 'audit'])
    args = p.parse_args()
    generate() if args.command == 'generate' else audit()
