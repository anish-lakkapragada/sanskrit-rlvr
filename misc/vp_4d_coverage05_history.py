"""Broader historical-input exposure audit, including earlier Bhave inputs.

Separates source-certification eligibility from whether a rule was ever probed.
No results, scores, or reserved-family engine derivations are read.
"""
import itertools
from collections import Counter, defaultdict

from misc.vp_4d_coverage05 import *


def main():
    base = read(OUT / 'inventory.json')
    es = entries_by_code()
    splits = read(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json')['families']
    rows = {}
    rejected = Counter()
    sources = []
    for rec in base['source_files']:
        if rec['cohort'] == 'current_five':
            continue
        p = ROOT / rec['path']
        assert sha(p) == rec['sha256']
        included = 0
        for top in read(p):
            for t in top.get('forms', [top]):
                if not isinstance(t, dict) or 'dhatu' not in t or set(t.get('morphology', {})) != set(COORDS):
                    continue
                code = t['dhatu'].get('code')
                if code not in es or splits[family(es[code])]['split'] != 'development':
                    continue
                if t.get('derivation') or any(o.get(k) not in (None, '', []) for o in [t, t['dhatu'], t['morphology']] for k in ['prefixes', 'sanadi', 'pada', 'dhatu_pada']):
                    continue
                e = es[code]
                if (t['dhatu']['aupadeshika'], t['dhatu']['gana']) != (e.dhatu.aupadeshika, name(e.dhatu.gana)):
                    continue
                if entry_scope_issue(e):
                    rejected['shared_entry_scope'] += 1
                    continue
                if t['morphology']['prayoga'] == 'Bhave' and (t['morphology']['purusha'], t['morphology']['vacana']) != ('Prathama', 'Eka'):
                    rejected['noncanonical_bhave'] += 1
                    continue
                if key(t) not in rows:
                    fresh = make_task(e, 'development', t['morphology'])
                    if not fresh or oracle_issue(fresh):
                        rejected['shared_oracle_scope'] += 1
                        continue
                    m = metadata(fresh)
                    m['local_census_issue'] = issue(fresh, e)
                    rows[key(t)] = m
                included += 1
        sources.append(dict(path=rec['path'], sha256=rec['sha256'], included_records=included))
    legacy = list(rows.values())
    hist = read(OUT / 'historical-metadata.json')
    current = hist['current_five']
    universe = [r for r in read(OUT / 'universe-metadata.json') if not repeat_mechanism(r)]
    li, ci, ui = index(legacy), index(current), index(universe)
    rule_report = []
    for rule, rr in ui.items():
        if len({r['family'] for r in rr}) >= 15 and len({r['family'] for r in ci.get(rule, [])}) < 8:
            rule_report.append(dict(rule=rule, supply=stats(rr), current=stats(ci.get(rule, [])),
                broader_legacy=stats(li.get(rule, [])), legacy_unapproved_for_proposed_panel=sum(bool(r['local_census_issue']) for r in li.get(rule, [])),
                legacy_examples=[dict(code=r['code'], gana=r['gana'], lakara=r['lakara'], prayoga=r['prayoga'], local_census_issue=r['local_census_issue']) for r in li.get(rule, [])[:8]]))
    rule_report.sort(key=lambda r: (r['broader_legacy']['families'], -r['supply']['families']))
    # Exhaustive co-occurrence pairs among substantial rules; no outcome ranking.
    vocab = {r for r, rr in ui.items() if len({t['family'] for t in rr}) >= 20}
    def pairs_present(rows):
        seen = set()
        for r in rows:
            seen.update(itertools.combinations(sorted(set(r['rules']) & vocab), 2))
        return seen
    lp, cp = pairs_present(legacy), pairs_present(current)
    masks = {r: bytearray((len(universe) + 7)//8) for r in vocab}
    fams = defaultdict(set)
    for i, row in enumerate(universe):
        for r in set(row['rules']) & vocab:
            masks[r][i//8] |= 1 << (i % 8)
            fams[r].add(row['family'])
    bits = {r: int.from_bytes(b, 'little') for r, b in masks.items()}
    novelties = []
    for a, b in itertools.combinations(sorted(vocab), 2):
        if (a, b) in lp or (a, b) in cp or len(fams[a] & fams[b]) < 20:
            continue
        mask = bits[a] & bits[b]
        if mask.bit_count() < 20:
            continue
        rr = []
        while mask:
            bit = mask & -mask; i = bit.bit_length() - 1
            rr.append(universe[i]); mask ^= bit
        if len({r['family'] for r in rr}) >= 20:
            novelties.append(dict(rules=[a, b], supply=stats(rr),
                examples=[dict(code=r['code'], lakara=r['lakara'], prayoga=r['prayoga'], purusha=r['purusha'], vacana=r['vacana']) for r in rr[:4]]))
    result = dict(created_at=now(), source_inventory_sha256=sha(OUT / 'inventory.json'),
        correction='The earlier zero-ciN legacy figure was conditional on a narrow exact transitive-meaning allowlist. It was not full historical grammar absence. This addendum includes shared-policy-eligible ordinary development inputs outside that local screen, and canonical Bhave, as exposure evidence only.',
        broader_legacy=stats(legacy), excluded=dict(rejected), sources=sources,
        new_coverage_versus_old_local_screen=len(legacy)-base['full_legacy_development']['n'],
        low_modern_rule_coverage=rule_report,
        absent_rule_pairs_with_at_least20_development_families=novelties,
        pair_search_vocabulary=len(vocab), no_model_answers_read=True,
        no_reserved_family_derivations=True, no_paid_calls=True,
        caveat='Historical rule exposure outside a conservative meaning screen is not proof of grammatical gold validity or current-model accuracy. Lack of a new broad rule pair is not an impossibility proof for higher-order interactions.')
    write('historical-coverage-addendum.json', result)
    write('broader-legacy-metadata.json', legacy)
    print('BROADER HISTORY',stats(legacy))
    print('CURRENT-ABSENT BROAD RULES',[(r['rule'],r['supply']['families'],r['broader_legacy']['n'],r['broader_legacy']['families'])for r in rule_report if not r['current']['n']])
    print('NEW SUBSTANTIAL PAIRS',novelties)
    progress('Broader historical exposure correction complete: the narrow passive meaning screen must not manufacture grammar novelty. Current source eligibility and historical mechanism exposure are reported separately.')


if __name__ == '__main__':
    main()
