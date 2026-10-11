"""Input-only strong/weak athematic imperative coverage and source controls.

Never opens model results. Test access is aggregate grammar supply only,
explicitly requested by the coordinator after the development-only census.
"""
from misc.vp_4d_coverage05 import *

GANAS = {'Adadi', 'Juhotyadi', 'Svadi', 'Rudhadi', 'Tanadi', 'Kryadi'}
CONTROL_TENSES = ['Lat', 'Lan', 'VidhiLin']


def outer(r):
    return (r['gana'] in GANAS and r['lakara'] == 'Lot' and r['prayoga'] == 'Kartari'
            and r['purusha'] == 'Uttama' and r['vacana'] in {'Dvi', 'Bahu'})


def strength_branch(target, present):
    """Fixed trace conditions establishing a real pit-conditioned contrast.

    Both compared inputs are ordinary dictionary entry + four coordinates.
    No condition consults gold strings or any model result.
    """
    t, p = map(lambda x: set(x['campaign']['trace_rule_ids']), [target, present])
    if '3.4.92' not in t:
        return None
    if '6.4.111' in p and '6.4.111' not in t:
        return 'nasal_infix_a_retention'
    if '6.4.113' in p and '6.4.113' not in t:
        return 'sna_or_reduplicated_A_retention'
    if p & {'1.1.5', '6.4.107'} and (t-p) & {'7.3.84', '7.3.86'}:
        return 'guna_permitted_before_pit'
    if '6.4.34' in p and '6.4.34' not in t:
        return 'sas_weak_stem_blocked'
    return None


def main():
    assert not (OUT / 'athematic-coverage.json').exists()
    es = entries_by_code()
    universe = read(OUT / 'universe-metadata.json')
    current = read(OUT / 'historical-metadata.json')['current_five']
    legacy = read(OUT / 'broader-legacy-metadata.json')
    dev_outer = [r for r in universe if outer(r)]
    matched = []
    all_regenerated = []
    for row in dev_outer:
        e = es[row['code']]
        target = make_task(e, 'development', {k: row[k] for k in COORDS})
        present = make_task(e, 'development', dict(target['morphology'], lakara='Lat'))
        branch = strength_branch(target, present)
        if branch:
            matched.append(dict(row, branch=branch))
            all_regenerated.append(dict(target=target, present=present, branch=branch))
    codes = {r['code'] for r in matched}
    # Broad history supplied as exposure evidence, without local transitivity screen.
    coverage = dict(outer_supply=stats(dev_outer), strength_supply=stats(matched),
        outer_current=stats([r for r in current if outer(r)]),
        outer_full_legacy=stats([r for r in legacy if outer(r)]),
        strength_current=stats([r for r in current if outer(r) and r['code'] in codes]),
        strength_full_legacy=stats([r for r in legacy if outer(r) and r['code'] in codes]),
        branches={b: stats([r for r in matched if r['branch']==b]) for b in sorted({r['branch'] for r in matched})},
        by_gana={g: dict(supply=stats([r for r in matched if r['gana']==g]),
            current=stats([r for r in current if outer(r) and r['code'] in codes and r['gana']==g]),
            legacy=stats([r for r in legacy if outer(r) and r['code'] in codes and r['gana']==g])) for g in sorted(GANAS)})
    # Parent authorized test INPUT aggregate supply only, not answers or selection.
    splits = read(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json')['families']
    test_outer, test_strength, test_excluded = [], [], Counter()
    for e in es.values():
        if name(e.dhatu.gana) not in GANAS or splits[family(e)]['split'] != 'test':
            continue
        if entry_scope_issue(e):
            test_excluded['shared_entry_scope'] += 1
            continue
        for v in ['Dvi', 'Bahu']:
            m = dict(lakara='Lot', prayoga='Kartari', purusha='Uttama', vacana=v)
            t = make_task(e, 'test', m)
            p = make_task(e, 'test', dict(m, lakara='Lat'))
            if not t or not p or issue(t, e) or issue(p, e):
                test_excluded['no_eligible_target_or_present'] += 1
                continue
            test_outer.append(metadata(t))
            if (b := strength_branch(t, p)):
                test_strength.append(dict(metadata(t), branch=b))
    # Deduplicate visible identities by code-free family and coordinates.
    test_outer = list({(r['family'], *(r[k] for k in COORDS)): r for r in test_outer}.values())
    test_strength = list({(r['family'], *(r[k] for k in COORDS)): r for r in test_strength}.values())
    coverage.update(test_input_only_aggregate=dict(outer=stats(test_outer), strength=stats(test_strength),
        branches={b: stats([r for r in test_strength if r['branch']==b]) for b in sorted({r['branch'] for r in test_strength})},
        exclusions=dict(test_excluded), no_test_tasks_selected=True, no_test_model_answers_read=True),
        created_at=now(), policy='oracle-policy-21', source_sha256=dict(
            script=sha(Path(__file__)), adapter=sha(ROOT/'misc/vp_cartesian_task.py'),
            broader_legacy=sha(OUT/'broader-legacy-metadata.json')),
        exact_predicate='Kartari, Lot, Uttama, Dvi/Bahu; six athematic classes; present counterpart has one of the explicitly recorded pit-sensitive weak-stem rules which the Lot derivation blocks. See strength_branch in the hashed script.',
        bounds='Candidate domain excludes Bhave and counts this specific interaction only. Test figures are aggregate input supply; they cannot certify all held-out gold or predict model accuracy.',
        no_model_answers_read=True, no_paid_calls=True)
    write('athematic-coverage.json', coverage)
    write('athematic-development-controls.json', all_regenerated)
    print(json.dumps(coverage, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
