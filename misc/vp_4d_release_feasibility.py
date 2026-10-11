#!/usr/bin/env python3
"""Offline aggregate allocation witnesses; never emits benchmark membership."""
from __future__ import annotations
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_4d_pilot import OUT, CELLS, load_entries, source_rows, matches, name, row_identity, write, now, sha
sys.path.insert(0, str(OUT / '_solver_deps'))
import highspy

RUN_ID = 'release-feasibility-01'
LABELS = [c['label'] for c in CELLS]


def status(phase, message):
    write(OUT / 'status.json', {'track': 'four_d', 'run_id': RUN_ID,
        'updated_at': now(), 'state': 'running', 'phase': phase,
        'message': message, 'benchmark_ready': False})
    with (OUT / 'progress.md').open('a') as f:
        f.write(f'\n- {now()}: {phase}: {message}\n')


def load_supply():
    entries = {e.code: e for e in load_entries()}
    visible_groups = defaultdict(list)
    for e in entries.values():
        visible_groups[e.dhatu.aupadeshika, name(e.dhatu.gana), e.artha].append(e)
    ambiguous_codes = {e.code for es in visible_groups.values()
                       if len({str(e.dhatu.antargana) for e in es}) > 1 for e in es}
    bins = Counter()
    seen = set()
    for row in source_rows(entries):
        if row['split'] != 'test':
            continue
        entry = entries[row['code']]
        # The Data loader supplies lexical prefixes on four entries. They are
        # outside exact 4D scope even though no with_prefixes call was made.
        if entry.dhatu.prefixes or entry.dhatu.sanadi:
            continue
        if row['code'] in ambiguous_codes:
            continue
        if row['prayoga'] in {'Karmani', 'Bhave'} and {'6.4.62', '6.4.92'} <= set(row['rules']):
            continue
        # Post-pilot grammatical quarantine, independent of test answers:
        # semantic-conditioned rAdh perfect and pusadi citation-list mismatches.
        if '6.4.123' in row['rules']:
            continue
        if row['code'] in {'04.0113', '04.0141'} and row['lakara'] == 'Lun':
            continue
        key = row_identity(row, entries)
        if key in seen:
            continue
        eligible = tuple(i for i, c in enumerate(CELLS) if matches(row, c, entries))
        if not eligible:
            continue
        seen.add(key)
        # Drop code, citation, artha, ID, and all surface forms from the solver.
        # A bin is a capacity of indistinguishable grammatical allocation units.
        b = (row['family'], name(entries[row['code']].dhatu.gana), row['lakara'],
             row['prayoga'], row['purusha'], row['vacana'], eligible)
        bins[b] += 1
    return sorted(bins.items())


def solve(bins, n, family_cap):
    started = time.monotonic()
    h = highspy.Highs()
    h.setOptionValue('output_flag', False)
    h.setOptionValue('time_limit', 55.0)
    h.setOptionValue('threads', 2)
    h.setOptionValue('random_seed', 20261007)
    h.setOptionValue('mip_rel_gap', 0.001)
    x = []
    by_family, by_gana, by_la, by_voice, by_person, by_number, by_cell = [defaultdict(list) for _ in range(7)]
    metadata = []
    for b, capacity in bins:
        f, g, la, pr, pu, va, cells = b
        assigned = []
        for cell in cells:
            v = h.addVariable(lb=0, ub=capacity, type=highspy.HighsVarType.kInteger)
            x.append(v)
            assigned.append(v)
            metadata.append((b, cell))
            for mapping, key in [(by_family, f), (by_gana, g), (by_la, la),
                                 (by_voice, pr), (by_person, pu), (by_number, va), (by_cell, cell)]:
                mapping[key].append(v)
        h.addConstr(h.qsum(assigned) <= capacity)
    h.addConstr(h.qsum(x) == n)
    objective = []
    for f, variables in by_family.items():
        # Convex m^2 penalty encourages spreading tasks within the feasible cells.
        slots = [h.addVariable(lb=0, ub=1, type=highspy.HighsVarType.kInteger) for _ in range(family_cap)]
        h.addConstr(h.qsum(variables) == h.qsum(slots))
        objective.extend((2*k + 1) * slot for k, slot in enumerate(slots))
    for variables in by_gana.values():
        h.addConstr(h.qsum(variables) <= math.floor(.30*n))
        h.addConstr(h.qsum(variables) >= 1)
    for variables in by_la.values():
        h.addConstr(h.qsum(variables) <= math.floor(.25*n))
        h.addConstr(h.qsum(variables) >= math.ceil(.03*n))
    for mapping in [by_person, by_number]:
        for variables in mapping.values():
            h.addConstr(h.qsum(variables) >= math.ceil(.20*n))
            h.addConstr(h.qsum(variables) <= math.floor(.40*n))
    h.addConstr(h.qsum(by_voice['Karmani']) >= math.ceil(.03*n))
    h.addConstr(h.qsum(by_voice['Karmani']) <= math.floor(.15*n))
    for i, variables in by_cell.items():
        total = h.qsum(variables)
        h.addConstr(total >= math.ceil(.02*n))
        h.addConstr(total <= math.floor(.25*n))
        target = n * CELLS[i]['n'] / 120
        deviation = h.addVariable(lb=0)
        h.addConstr(deviation >= total - target)
        h.addConstr(deviation >= target - total)
        # Primary objective: preserve pilot construction proportions where feasible.
        # Secondary objective: minimize sum of squared family counts.
        objective.append(100000 * deviation)
    h.minimize(h.qsum(objective))
    status_string = str(h.getModelStatus())
    solution = h.getSolution()
    result = {'n': n, 'family_cap': family_cap, 'solver_status': status_string,
              'elapsed_seconds': round(time.monotonic()-started, 3), 'feasible': False}
    if not solution.value_valid:
        return result
    amounts = [solution.col_value[int(v)] for v in x]
    if any(abs(v-round(v)) > 1e-5 for v in amounts):
        result['no_integer_solution'] = True
        return result
    amounts = list(map(lambda v: int(round(v)), amounts))
    if sum(amounts) != n:
        return result
    families, ganas, lakaras, voices, persons, numbers, cells, bin_usage = [Counter() for _ in range(8)]
    for amount, (b, cell) in zip(amounts, metadata):
        if not amount:
            continue
        f, g, la, pr, pu, va, _ = b
        for mapping, key in [(families, f), (ganas, g), (lakaras, la), (voices, pr),
                             (persons, pu), (numbers, va), (cells, LABELS[cell]), (bin_usage, b)]:
            mapping[key] += amount
    capacities = dict(bins)
    assert all(v <= capacities[b] for b, v in bin_usage.items())
    assert max(families.values()) <= family_cap
    assert all(1 <= v <= math.floor(.30*n) for v in ganas.values()) and len(ganas) == 10
    assert all(math.ceil(.03*n) <= v <= math.floor(.25*n) for v in lakaras.values()) and len(lakaras) == 10
    assert all(math.ceil(.20*n) <= v <= math.floor(.40*n) for v in list(persons.values()) + list(numbers.values()))
    assert math.ceil(.03*n) <= voices['Karmani'] <= math.floor(.15*n)
    assert all(math.ceil(.02*n) <= v <= math.floor(.25*n) for v in cells.values())
    assert len(cells) == 10
    sum_squares = sum(v*v for v in families.values())
    m_weighted = sum_squares/n
    sensitivity = []
    for rho in [0, .02, .05, .10, .20]:
        deff = 1 + rho*(m_weighted-1)
        sensitivity.append({'within_family_icc': rho, 'design_effect': deff,
            'effective_independent_n': n/deff,
            'se_at_80_percent_in_percentage_points': 100*math.sqrt(.16*deff/n),
            'n_needed_if_this_cluster_profile_could_be_maintained': math.floor(1600*deff)+1})
    result.update(feasible=True, root_families=len(families),
        max_tasks_per_family=max(families.values()), max_family_fraction=max(families.values())/n,
        family_size_histogram=dict(sorted(Counter(families.values()).items())),
        family_task_sum_squares=sum_squares, task_weighted_family_size=m_weighted,
        kish_effective_family_count=n*n/sum_squares,
        root_families_by_gana=dict(Counter(f.split('|')[-1] for f in families)),
        distributions={'gana':dict(ganas), 'lakara':dict(lakaras), 'prayoga':dict(voices),
                       'purusha':dict(persons), 'vacana':dict(numbers)},
        cells=dict(cells), max_lakara_fraction=max(lakaras.values())/n,
        max_gana_fraction=max(ganas.values())/n,
        uncertainty_sensitivity=sensitivity,
        maximum_positive_icc_compatible_with_se_strictly_below_one_point=(n/1600-1)/(m_weighted-1) if m_weighted>1 else None,
        witness_policy='Only aggregate capacities and counts emitted. No benchmark task IDs or final membership selected or frozen.')
    info = h.getInfo()
    result['objective_mip_gap'] = info.mip_gap
    return result


def main():
    status('Overlap-aware allocation model', 'Counting unique master-test grammar bins and solving capacity-constrained hypothetical releases; all surface answers excluded from solver.')
    bins = load_supply()
    family_supply, gana_family_supply = Counter(), defaultdict(Counter)
    for b, count in bins:
        family_supply[b[0]] += count
        gana_family_supply[b[1]][b[0]] += count
    result = {'created_at': now(), 'run_id': RUN_ID,
        'grammar_union_unique_tuples': sum(n for _,n in bins),
        'grammar_union_root_families': len(family_supply), 'solver_bins': len(bins),
        'root_families_by_gana': {g:len(v) for g,v in gana_family_supply.items()},
        'coordinate_scope': 'Exactly dictionary dhatu + four morphology coordinates; no sanadi, prefixes or pada coordinate.',
        'data_policy': 'Read-only SQLite grammar metadata; test model answers and gold surface forms not loaded; full unchanged master test split.',
        'grammar_exclusions': ['Any preexisting dictionary prefix or sanadi',
            'Any 6.4.123 trace until meaning-conditioned use is certified',
            'Lun for 04.0113 and 04.0141: PUSH_ADI membership/citation mismatch pending independent resolution',
            'Visible lexical identities with different intrinsic antargana until complete union keys are certified',
            'Karmani/Bhave contexts with both 6.4.62 and 6.4.92 pending Cinvat variant certification'],
        'solver': {'name':'HiGHS', 'version':highspy.Highs().version(),
                   'dependency_location':str((OUT/'_solver_deps').relative_to(ROOT)),
                   'generator_sha256':sha(__file__)},
        'constraints': {'unique_tasks':[1000,1601,2000,2400], 'all_ten_lakaras':True,
            'min_lakara_fraction':.03,'max_lakara_fraction':.25,
            'all_ten_ganas':True,'max_gana_fraction':.30,
            'each_person_and_number_fraction':[.20,.40],
            'passive_fraction':[.03,.15], 'each_grammar_cell_fraction':[.02,.25],
            'max_per_family':'varied diagnostic, not user-mandated'},
        'capacity_upper_bounds':[], 'allocations':[],
        'limits':['Feasible grammar counts are not proof of desired reference-model accuracy.',
            'Cluster ICC values are sensitivity assumptions, not measurements.',
            'Final construction weights, membership, extension rule, and audits remain to be frozen before final model exposure.',
            'Exact-citation-plus-gana families can share an underlying root; the declared family grouping may still understate dependence.']}
    for n in [1000,1601]:
        for k in [2,3,4,5,6,8]:
            raw = sum(min(k,v) for v in family_supply.values())
            gana_limited = sum(min(math.floor(.30*n),sum(min(k,v) for v in families.values()))
                               for families in gana_family_supply.values())
            result['capacity_upper_bounds'].append({'n':n,'family_cap':k,
                'raw_family_capacity':raw,'capacity_after_gana_30_percent_upper_bound':gana_limited,
                'impossible_if_below_n':gana_limited<n,
                'note':'Necessary upper bound only; ignores tense, cell and agreement quotas.'})
    path = OUT/'release-feasibility-01.json'
    write(path,result)
    for n,k in [(1000,3),(1000,4),(1000,6),(1601,5),(1601,6),(1601,8),(2000,8),(2400,10)]:
        status('Solving hypothetical allocation', f'N={n}, maximum {k} per family; final membership remains unfrozen.')
        allocation = solve(bins,n,k)
        result['allocations'].append(allocation)
        result['updated_at']=now()
        write(path,result)
        print(json.dumps({key:allocation.get(key) for key in ['n','family_cap','solver_status','feasible','root_families','elapsed_seconds']}),flush=True)


if __name__ == '__main__':
    main()
