"""Input-only ordinary4D grammar coverage census. Never opens model results."""
import hashlib
import itertools
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_cartesian_task import entries_by_code, entry_scope_issue, oracle_issue, make_task
from misc.vp_campaign_candidates import family, name
from misc.vp_4d_pilot import TRANSITIVE_ARTHAS

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'benchmarks/parallel-search-20261006'
OUT = B / 'four_d/coverage-05'
COORDS = ['lakara', 'prayoga', 'purusha', 'vacana']
LOCAL = {'10.0023', '10.0400', '10.0490', '10.0492', '04.0137'}
SPECIAL_IT = {'7.2.36', '7.2.37', '7.2.38', '7.2.44', '7.2.45', '7.2.48', '7.2.57', '7.2.59', '7.2.60', '7.2.70'}


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(n, d):
    (OUT / n).write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def progress(message):
    p = B / 'four_d/status.json'
    s = read(p)
    assert s['run_id'] == 'overnight-coverage-05'
    s.update(updated_at=now(), message=message)
    p.write_text(json.dumps(s, indent=2) + '\n')
    with (B / 'four_d/progress.md').open('a') as f:
        f.write('\n' + now() + ' — Coverage05: ' + message + '\n')


def key(t):
    return (t['dhatu']['aupadeshika'], t['dhatu']['gana'], *(t['morphology'][k] for k in COORDS))


def metadata(t):
    return dict(id=t['id'], code=t['dhatu']['code'], family=t['campaign']['root_family'],
                gana=t['dhatu']['gana'], **t['morphology'], rules=t['campaign']['trace_rule_ids'])


def issue(t, e):
    return (entry_scope_issue(e) or oracle_issue(t) or
        ('Existing local unresolved source precaution' if e.code in LOCAL or (e.code == '10.0412' and t['morphology']['lakara'] == 'Lun') else None) or
        ('Outside existing exact transitive-meaning screen' if t['morphology']['prayoga'] == 'Karmani' and e.artha not in TRANSITIVE_ARTHAS else None) or
        ('Bhave not in declared census domain' if t['morphology']['prayoga'] == 'Bhave' else None))


def repeat_mechanism(t):
    rs = set(t['rules'])
    e = entries_by_code()[t['code']]
    if t['gana'] == 'Curadi' and e.dhatu.aupadeshika.endswith('a'):
        return 'adanta'
    if t['lakara'] == 'Lit':
        return 'perfect_system_conservatively_not_new'
    if t['purusha'] == 'Madhyama' and t['vacana'] == 'Bahu' and rs & {'8.3.78', '8.3.79'}:
        return 'dhvam'
    if t['gana'] != 'Curadi' and t['lakara'] in {'Lut', 'Lrt', 'Lrn'} and rs & SPECIAL_IT:
        return 'specialized_it'
    if '1.2.1' in rs:
        return 'previously_considered_kutadi'
    return None


def stats(rows):
    return dict(n=len(rows), families=len({r['family'] for r in rows}),
                ganas=dict(Counter(r['gana'] for r in rows)), lakaras=dict(Counter(r['lakara'] for r in rows)))


def index(rows):
    out = defaultdict(list)
    for row in rows:
        for rule in row['rules']:
            out[rule].append(row)
    return out


def main():
    OUT.mkdir(exist_ok=True)
    assert not (OUT / 'inventory.json').exists(), 'Preserve completed inventory'
    es = entries_by_code()
    split = read(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json')
    design = dict(created_at=now(), run_id='overnight-coverage-05', policy='oracle-policy-21',
        purpose='Identify substantial, interpretable ordinary4D coverage gaps; no outcome predictor or accuracy inference.',
        sources='Five current pilot input files; original6687 input-only file after master-development filter; all ordinary development inputs in both campaign job input directories; read-only development rows from full ordinary Cartesian metadata database.',
        domain='Development families only; ten classical lakaras, Kartari plus Karmani under existing exact transitive-meaning allowlist. Bhave remains outside this census; no claim of exhaustion beyond this domain.',
        novelty='Rule and meaningful interaction novelty, not merely new tuples. Report modern versus full legacy coverage separately.',
        exclusions='Current shared21 plus explicitly recorded preexisting local uncertainties; no exclusion using model behavior.',
        proposed_panel_cap=96, no_model_answers=True, no_paid_calls=True,
        decision='Recommend exploration only if new or materially undercovered source-defined interactions have multiple-family support and can test a concrete uncertainty. Do not repackage adanta, dhvam, weak-perfect or specialized-it. No final-target or precision relaxation.')
    write('design.json', design)
    # Complete existing development Cartesian metadata: no reserved-family query.
    dbpath = ROOT / 'benchmarks/creation-campaign-20261006/candidates.sqlite'
    db = sqlite3.connect('file:' + str(dbpath) + '?mode=ro', uri=True)
    allrows = list(db.execute("SELECT * FROM candidates WHERE split='development'")); db.close()
    universe, lookup, excluded = [], {}, Counter()
    for row in allrows:
        tid, fam, spl, code, la, pr, pu, va, gold, rules, steps, variants = row
        e = es[code]
        assert split['families'][family(e)]['split'] == spl == 'development'
        t = dict(id=tid, dhatu=dict(code=code, aupadeshika=e.dhatu.aupadeshika, gana=name(e.dhatu.gana)),
                 morphology=dict(zip(COORDS, [la, pr, pu, va])), gold_slp1=json.loads(gold),
                 campaign=dict(root_family=fam, trace_rule_ids=json.loads(rules)))
        if (why := issue(t, e)):
            excluded[why] += 1
            continue
        k = key(t)
        if k not in lookup:
            m = metadata(t); universe.append(m); lookup[k] = m
    progress(f'Eligible development metadata census contains {len(universe)} tuples across {len({r["family"] for r in universe})} families; loading only historical question inputs next.')
    currentpaths = [ROOT / f'benchmarks/iterative-goal-20261006/jobs/opus-four-d-pilot-{i:02d}/tasks.json' for i in range(1, 6)]
    paths = [ROOT / 'benchmarks/full-tasks.json']
    for folder in ['creation-campaign-20261006', 'iterative-goal-20261006']:
        paths += sorted((ROOT / 'benchmarks' / folder / 'jobs').glob('*/tasks.json'))
    cohorts = defaultdict(dict); sources = []; input_exclusions = Counter(); all_prior_keys = set()
    for path in paths:
        is_current = path in currentpaths
        cohort = 'current_five' if is_current else 'original6687' if path.name == 'full-tasks.json' else 'legacy_other'
        kept, devordinary = 0, 0
        for top in read(path):
            for t in top.get('forms', [top]):
                if not isinstance(t, dict) or 'dhatu' not in t or set(t.get('morphology', {})) != set(COORDS):
                    continue
                code = t['dhatu'].get('code')
                if code not in es or split['families'][family(es[code])]['split'] != 'development':
                    continue
                if t.get('derivation') or any(o.get(k) not in (None, '', []) for o in [t, t['dhatu'], t['morphology']] for k in ['prefixes', 'sanadi', 'pada', 'dhatu_pada']):
                    continue
                e = es[code]
                if (t['dhatu']['aupadeshika'], t['dhatu']['gana']) != (e.dhatu.aupadeshika, name(e.dhatu.gana)):
                    continue
                devordinary += 1
                k = key(t); all_prior_keys.add(k)
                if k not in lookup:
                    input_exclusions[cohort + ':outside_current_census'] += 1
                    continue
                cohorts[cohort][k] = lookup[k]; kept += 1
        sources.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), cohort=cohort,
                            ordinary_development_rows_before_scope=devordinary, in_scope_rows=kept))
    current = list(cohorts['current_five'].values())
    legacy_map = {**cohorts['legacy_other'], **cohorts['original6687']}
    legacy = list(legacy_map.values())
    strict_new = [r for r in universe if not repeat_mechanism(r)]
    ui, ci, li, ni = map(index, [universe, current, legacy, strict_new])
    coverage = []
    for rule, rows in ui.items():
        rr = ni.get(rule, [])
        coverage.append(dict(rule=rule, full=stats(rows), nonrepeat=stats(rr),
            current=stats(ci.get(rule, [])), legacy=stats(li.get(rule, [])),
            examples=[dict(code=r['code'], lakara=r['lakara'], prayoga=r['prayoga'], purusha=r['purusha'], vacana=r['vacana']) for r in rr[:3]]))
    coverage.sort(key=lambda r: (-r['nonrepeat']['families'], r['rule']))
    # Pair census is confined to substantive rules with actual missing/low modern support.
    eligible_rules = {r['rule'] for r in coverage if r['nonrepeat']['families'] >= 15 and r['current']['families'] < 8 and r['rule'].split('.')[0] in {'1', '3', '6', '7', '8'}}
    pairrows = defaultdict(list)
    for r in strict_new:
        for a, b in itertools.combinations(sorted(set(r['rules']) & eligible_rules), 2):
            pairrows[(a, b)].append(r)
    pairs = []
    for (a, b), rows in pairrows.items():
        if len({r['family'] for r in rows}) < 20:
            continue
        cr = [r for r in ci.get(a, []) if b in r['rules']]
        lr = [r for r in li.get(a, []) if b in r['rules']]
        pairs.append(dict(rules=[a, b], supply=stats(rows), current=stats(cr), legacy=stats(lr),
            examples=[dict(code=r['code'], lakara=r['lakara'], prayoga=r['prayoga'], purusha=r['purusha'], vacana=r['vacana']) for r in rows[:3]]))
    pairs.sort(key=lambda p: (p['legacy']['families'], p['current']['families'], -p['supply']['families']))
    # Verify every historical current input's rule metadata, plus deterministic universe sentinels.
    sentinels = sorted(universe, key=lambda r: hashlib.sha256(r['id'].encode()).hexdigest())[:128]
    mismatches = []
    for r in sentinels:
        t = make_task(es[r['code']], 'development', {k: r[k] for k in COORDS})
        assert t is not None
        if t['campaign']['trace_rule_ids'] != r['rules']:
            mismatches.append(r['id'])
    assert not mismatches
    result = dict(created_at=now(), policy='oracle-policy-21',
        source_hashes=dict(adapter=sha(ROOT / 'misc/vp_cartesian_task.py'), policy=sha(B / 'oracle-policy-21.json'),
                           master_split=sha(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json'),
                           candidate_database=sha(dbpath), script=sha(Path(__file__))),
        source_files=sources, original_candidate_development_rows=len(allrows), exclusions=dict(excluded),
        universe=stats(universe), current_five=stats(current), full_legacy_development=stats(legacy),
        original6687_development=stats(list(cohorts['original6687'].values())), legacy_other=stats(list(cohorts['legacy_other'].values())),
        nonrepeat_universe=stats(strict_new), rule_count=len(coverage),
        modern_absent_rules=[r for r in coverage if not r['current']['n']],
        full_history_absent_rules=[r for r in coverage if not r['current']['n'] and not r['legacy']['n']],
        substantial_low_modern_rules=[r for r in coverage if r['rule'] in eligible_rules],
        substantial_low_modern_rule_pairs=pairs, all_rules=coverage,
        sentinel_regeneration=dict(n=len(sentinels), mismatches=mismatches),
        no_model_answers_read=True, no_reserved_family_rows_queried=True, no_paid_calls=True,
        caution='Rule occurrence and arbitrary pair absence are coverage diagnostics, not difficulty evidence or grammatical interaction proof. Metadata universe is complete in its declared coordinate domain, not all possible Sanskrit uses.')
    write('inventory.json', result)
    write('universe-metadata.json', universe)
    write('historical-metadata.json', {k: list(v.values()) for k, v in cohorts.items()})
    print(json.dumps({k: result[k] for k in ['universe', 'current_five', 'full_legacy_development', 'original6687_development', 'nonrepeat_universe', 'rule_count', 'sentinel_regeneration']}, indent=2))
    print('Broad modern-absent rules:', [(r['rule'], r['nonrepeat']['families'], r['legacy']['families']) for r in coverage if not r['current']['n'] and r['nonrepeat']['families'] >= 15])
    print('Full-history-absent rules:', [(r['rule'], r['nonrepeat']['families']) for r in result['full_history_absent_rules']])
    print('Low-modern substantial pairs:', len(pairs))
    progress('Input-only coverage inventory saved with current/legacy rule support and fresh regeneration sentinels; evaluating whether any gap is a meaningful source-defined interaction.')


if __name__ == '__main__':
    main()
