#!/usr/bin/env python3
"""Fresh 4D grammar-stratified pilot. Offline only; never reads model answers."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_campaign_candidates import load_entries, family, name
from misc.vp_cartesian_task import make_task, validate_task
from misc.vp_cartesian_prompt_v1 import render

OUT = ROOT / 'benchmarks/parallel-search-20261006/four_d'
HISTORY = ROOT / 'benchmarks/creation-campaign-20261006'
SEED = 2026100604
ATHEMATIC = {'Adadi', 'Juhotyadi', 'Svadi', 'Rudhadi', 'Tanadi', 'Kryadi'}
TRANSITIVE_ARTHAS = {'hiMsAyAm', 'Cedane', 'Bedane', 'banDane', 'dAne',
                    'AdAne', 'BakzaRe', 'tyAge', 'vileKane', 'saMcUrRane'}
CELLS = [
    {'label': 'internal_rv_lengthening', 'n': 12,
     'prayogas': ['Kartari'], 'require_rules_all': ['8.2.78'],
     'lakaras': ['Lat', 'Lit', 'Lut', 'Lrt', 'Lot', 'Lan', 'VidhiLin', 'AshirLin', 'Lun', 'Lrn']},
    {'label': 'svadi_perfect', 'n': 12, 'prayogas': ['Kartari'],
     'ganas': ['Svadi'], 'lakaras': ['Lit']},
    {'label': 'other_athematic_perfect', 'n': 6, 'prayogas': ['Kartari'],
     'ganas': ['Adadi', 'Juhotyadi', 'Rudhadi', 'Tanadi', 'Kryadi'], 'lakaras': ['Lit']},
    {'label': 'perfect_reduplication_changes', 'n': 12, 'prayogas': ['Kartari'],
     'exclude_ganas': ['Curadi'], 'lakaras': ['Lit'],
     'require_rules_any': ['6.1.15', '6.1.16', '6.1.17', '6.1.18', '7.4.70']},
    {'label': 'divadi_sigmatic_aorist', 'n': 12, 'prayogas': ['Kartari'],
     'ganas': ['Divadi'], 'lakaras': ['Lun'], 'require_rules_all': ['3.1.44']},
    {'label': 'aorist_consonant_changes', 'n': 12, 'prayogas': ['Kartari'],
     'lakaras': ['Lun'], 'require_rules_any': ['8.3.78', '8.4.53', '8.4.54', '8.4.55']},
    {'label': 'athematic_present_system', 'n': 18, 'prayogas': ['Kartari'],
     'ganas': sorted(ATHEMATIC), 'lakaras': ['Lat', 'Lan', 'Lot', 'VidhiLin'],
     'lakara_quotas': {'Lat': 3, 'Lan': 5, 'Lot': 5, 'VidhiLin': 5},
     'require_rules_any': ['6.1.10', '3.4.99', '7.3.87', '6.4.112', '6.4.113']},
    {'label': 'dictionary_curadi_futures', 'n': 12, 'prayogas': ['Kartari'],
     'ganas': ['Curadi'], 'lakaras': ['Lut', 'Lrt', 'Lrn'],
     'lakara_quotas': {'Lut': 6, 'Lrt': 3, 'Lrn': 3}},
    {'label': 'transitive_curadi_nonpresent_passive', 'n': 12,
     'prayogas': ['Karmani'], 'ganas': ['Curadi'], 'lakaras': ['Lut', 'AshirLin'],
     'lakara_quotas': {'Lut': 6, 'AshirLin': 6},
     'require_rules_all': ['6.4.51'], 'transitive_artha_allowlist': sorted(TRANSITIVE_ARTHAS)},
    {'label': 'primary_benedictive_stem_changes', 'n': 12, 'prayogas': ['Kartari'],
     'exclude_ganas': ['Curadi'], 'lakaras': ['AshirLin'],
     'require_rules_any': ['6.4.16', '6.4.37', '6.4.38', '7.1.100', '7.1.101', '7.2.10', '8.2.41']},
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)


def status(phase, message):
    write(OUT / 'status.json', {'track': 'four_d', 'updated_at': now(), 'state': 'running',
                              'phase': phase, 'message': message, 'benchmark_ready': False})
    with (OUT / 'progress.md').open('a') as f:
        f.write(f'\n- {now()}: {phase}: {message}\n')


def identity(task):
    d, m = task['dhatu'], task['morphology']
    return (d['aupadeshika'], d['gana'], d['artha'],
            *(m[k] for k in ['lakara', 'prayoga', 'purusha', 'vacana']))


def row_identity(row, entries):
    e = entries[row['code']]
    return (e.dhatu.aupadeshika, name(e.dhatu.gana), e.artha,
            row['lakara'], row['prayoga'], row['purusha'], row['vacana'])


def matches(row, cell, entries):
    e = entries[row['code']]
    g, rules = name(e.dhatu.gana), set(row['rules'])
    for key, coord in [('lakaras', 'lakara'), ('prayogas', 'prayoga'),
                       ('purushas', 'purusha'), ('vacanas', 'vacana')]:
        if key in cell and row[coord] not in cell[key]:
            return False
    if g in cell.get('exclude_ganas', []) or ('ganas' in cell and g not in cell['ganas']):
        return False
    if 'transitive_artha_allowlist' in cell and e.artha not in cell['transitive_artha_allowlist']:
        return False
    if not set(cell.get('require_rules_all', [])) <= rules:
        return False
    if cell.get('require_rules_any') and not set(cell['require_rules_any']) & rules:
        return False
    return True


def source_rows(entries):
    # URI read-only mode guarantees this worker cannot modify the historical DB.
    db = sqlite3.connect(f'file:{HISTORY / "candidates.sqlite"}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    rows = []
    for r in db.execute('SELECT id,family,split,code,lakara,prayoga,purusha,vacana,rules FROM candidates'):
        r = dict(r)
        r['rules'] = json.loads(r['rules'])
        rows.append(r)
    db.close()
    return rows


def exclusions():
    paths = [ROOT / 'benchmarks/full-tasks.json', *sorted(HISTORY.glob('discovery-??.json'))]
    used = set()
    for path in paths:
        for task in json.loads(path.read_text()):
            used.add(identity(task))
    return used, [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in paths]


def summarize(rows, entries):
    families = Counter(r['family'] for r in rows)
    return {'unique_tuples': len({row_identity(r, entries) for r in rows}),
            'root_families': len(families),
            'max_tasks_at_six_per_family': sum(min(6, n) for n in families.values()),
            'lakaras': dict(Counter(r['lakara'] for r in rows)),
            'ganas': dict(Counter(name(entries[r['code']].dhatu.gana) for r in rows))}


def prepare():
    path = OUT / 'pilot-01.questions.json'
    if path.exists():
        raise ValueError('Frozen pilot exists; preserve membership')
    entries = {e.code: e for e in load_entries()}
    rows = source_rows(entries)
    prior, inputs = exclusions()
    assignments = json.loads((HISTORY / 'family-split.json').read_text())['families']
    reserve = json.loads((ROOT / 'benchmarks/iterative-goal-20261006/test-family-reserve.json').read_text())
    initial = set(reserve['initial_release_families'])
    seen = set()
    fresh = []
    for r in rows:
        key = row_identity(r, entries)
        if r['split'] == 'development' and key not in prior and key not in seen:
            seen.add(key)
            fresh.append(r)
    supply = {}
    for cell in CELLS:
        supply[cell['label']] = {}
        for split in ['development_fresh', 'test_initial', 'test_reserve']:
            eligible = fresh if split == 'development_fresh' else [
                r for r in rows if r['split'] == 'test' and ((r['family'] in initial) == (split == 'test_initial'))]
            supply[cell['label']][split] = summarize([r for r in eligible if matches(r, cell, entries)], entries)
    write(OUT / 'pilot-01.cells.json', CELLS)
    write(OUT / 'supply-01.json', {'created_at': now(), 'cells': supply,
        'scope': 'No held-out model answers accessed. Counts use grammar traces and family membership only.',
        'limits': 'Cells overlap; six-per-family counts are per-cell upper bounds, not jointly feasible quotas. RL census pending.'})
    status('Selecting fresh tuples', 'Censused ten grammar cells; selecting 120 new development tuples with at most two per family.')
    tasks = []
    family_counts, gana_counts, person_counts, number_counts = Counter(), Counter(), Counter(), Counter()
    selected = set()
    # Scarce cells first protects supply; this order is fixed from grammar counts.
    ordered_cells = sorted(CELLS, key=lambda c: (supply[c['label']]['development_fresh']['root_families'] / c['n'], c['label']))
    for cell in ordered_cells:
        eligible = [r for r in fresh if matches(r, cell, entries)]
        tense_counts = Counter()
        for _ in range(cell['n']):
            possible = [r for r in eligible if row_identity(r, entries) not in selected
                        and family_counts[r['family']] < 2
                        and gana_counts[name(entries[r['code']].dhatu.gana)] < 42
                        and ('lakara_quotas' not in cell or tense_counts[r['lakara']] < cell['lakara_quotas'][r['lakara']])]
            if not possible:
                raise ValueError('Insufficient constrained supply: ' + cell['label'])
            def rank(r):
                g = name(entries[r['code']].dhatu.gana)
                return (family_counts[r['family']], person_counts[r['purusha']] + number_counts[r['vacana']],
                        gana_counts[g], tense_counts[r['lakara']], digest([SEED, cell['label'], r['id']]))
            r = min(possible, key=rank)
            e = entries[r['code']]
            morphology = {k: r[k] for k in ['lakara', 'prayoga', 'purusha', 'vacana']}
            t = make_task(e, 'development', morphology)
            assert t is not None and set(t['campaign']['trace_rule_ids']) == set(r['rules'])
            assert assignments[family(e)]['split'] == 'development'
            t['campaign'].update(panel='four-d-pilot-01', sampling_cell=cell,
                historical_candidate_id=r['id'], selection_seed=SEED,
                selection_reason='Grammar-defined cell, family breadth and coordinate balance, then SHA256 tie-break; no same-item model outcomes.')
            tasks.append(t)
            selected.add(identity(t))
            family_counts[r['family']] += 1
            gana_counts[name(e.dhatu.gana)] += 1
            person_counts[r['purusha']] += 1
            number_counts[r['vacana']] += 1
            tense_counts[r['lakara']] += 1
    tasks.sort(key=lambda t: digest([SEED, 'presentation-order', t['id']]))
    assert len(tasks) == 120
    assert len({t['id'] for t in tasks}) == len(tasks)
    assert len({t['campaign']['prompt_sha256'] for t in tasks}) == len(tasks)
    assert not selected & prior
    for t in tasks:
        validate_task(t, entries[t['dhatu']['code']], 'development')
        row = {'code': t['dhatu']['code'], **t['morphology'], 'rules': t['campaign']['trace_rule_ids']}
        assert matches(row, t['campaign']['sampling_cell'], entries)
        assert set(t['morphology']) == {'lakara', 'prayoga', 'purusha', 'vacana'}
        assert 'derivation' not in t
        assert 'dhatu_pada' not in t['morphology']
    write(path, tasks)
    distributions = {key: dict(Counter(t['morphology'][key] for t in tasks)) for key in ['lakara', 'prayoga', 'purusha', 'vacana']}
    distributions['gana'] = dict(gana_counts)
    manifest = {'created_at': now(), 'n': len(tasks), 'root_families': len(family_counts),
        'maximum_tasks_per_family': max(family_counts.values()), 'seed': SEED,
        'task_file': str(path.relative_to(ROOT)), 'task_sha256': sha(path),
        'task_digest': digest(tasks), 'generator_sha256': sha(__file__),
        'split_sha256': sha(HISTORY / 'family-split.json'),
        'test_reserve_sha256': sha(ROOT / 'benchmarks/iterative-goal-20261006/test-family-reserve.json'),
        'dictionary_sha256': sha(ROOT / 'data/finetune/task-data/vidyut_dhatupatha_5.tsv'),
        'vp_version': tasks[0]['campaign']['vp_version'],
        'prompt_sha256': sha(ROOT / 'prompts/v2/vp_task_eval.txt'),
        'source_panels_excluded': inputs, 'distributions': distributions,
        'cells': {c['label']: c['n'] for c in CELLS},
        'max_lakara_fraction': max(distributions['lakara'].values()) / len(tasks),
        'max_gana_fraction': max(gana_counts.values()) / len(tasks),
        'max_family_fraction': max(family_counts.values()) / len(tasks),
        'no_reserved_test_model_answers_accessed': True,
        'selection_policy': 'Grammar cell definitions motivated by historical development groups, fresh same-item tasks excluded, no model-output reading in this generator.',
        'audit_status': 'Mechanical regeneration passed; independent source controls in separate audit; not final certification.'}
    write(OUT / 'pilot-01.manifest.json', manifest)
    write(OUT / 'pilot-01.audit.json', {'created_at': now(), 'passed_mechanical_checks': True,
        'n': len(tasks), 'root_families': len(family_counts), 'task_sha256': sha(path),
        'checks': ['All four morphology coordinates exactly present; no sanadi/prefix/pada fields',
                   '120 unique model-visible prompts and canonical IDs',
                   'Fresh versus full legacy task pool and all three historical discovery panels',
                   'Every family is in unchanged development split',
                   'VP regeneration reproduces all gold variants, rule metadata and prompt hashes',
                   'All output forms round-trip SLP1/Devanagari',
                   'Karmani limited to exact transitive artha allowlist; all other tasks Kartari',
                   'Bhave and Vedic Let excluded'],
        'certified_final_benchmark': False,
        'limits': 'Rule-selection and engine consistency do not independently certify every gold form. Fresh pilot answers require disagreement audit.'})
    status('Pilot generated', f'120 fresh questions / {len(family_counts)} families generated and regenerated; preparing independent linguistic controls and experiment request.')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    prepare()
