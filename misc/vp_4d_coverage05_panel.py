"""Generate the prospectively declared input-only athematic coverage diagnostic."""
from misc.vp_4d_coverage05 import *
from misc.vp_4d_coverage05_athematic import strength_branch
from misc.vp_cartesian_task import validate_task
from misc.vp_5d_release_feasibility import MinCost


def main():
    assert not (OUT / 'pilot-06.questions.json').exists(), 'Preserve frozen panel'
    design = read(OUT / 'athematic-panel-design-r1.json')
    es = entries_by_code()
    split = read(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json')['families']
    history = set()
    for src in read(OUT / 'inventory.json')['source_files']:
        p = ROOT / src['path']
        assert sha(p) == src['sha256']
        for top in read(p):
            for t in top.get('forms', [top]):
                if not isinstance(t, dict) or 'dhatu' not in t or set(t.get('morphology', {})) != set(COORDS):
                    continue
                c = t['dhatu'].get('code')
                if c not in es or split[family(es[c])]['split'] != 'development':
                    continue
                if t.get('derivation'):
                    continue
                history.add(key(t))
    net = MinCost()
    edges, pairs = {}, []
    seed = design['seed']
    rank = lambda s: int(hashlib.sha256((seed+'|'+s).encode()).hexdigest()[:12], 16)
    for g, q in sorted(design['class_family_quotas'].items()):
        net.edge('source', ('gana', g), q)
    for la in sorted(design['control_tense_quotas']):
        for v in ['Dvi', 'Bahu']:
            net.edge(('cell', la, v), 'sink', 8)
    entries_added = set()
    rejected = Counter()
    for rec in read(OUT / 'athematic-development-controls.json'):
        target = rec['target']
        c, f = target['dhatu']['code'], target['campaign']['root_family']
        g, v = target['dhatu']['gana'], target['morphology']['vacana']
        if rec['branch'] not in design['target']['branches']:
            rejected['excluded_singleton_sas_branch'] += 1
            continue
        if key(target) in history:
            rejected['target_previously_asked'] += 1
            continue
        if f not in entries_added:
            net.edge(('gana', g), ('family', f), 1)
            entries_added.add(f)
        for la in sorted(design['control_tense_quotas']):
            control = make_task(es[c], 'development', dict(target['morphology'], lakara=la))
            if control is None or issue(control, es[c]):
                rejected['ineligible_control'] += 1
                continue
            if key(control) in history:
                rejected['control_previously_asked'] += 1
                continue
            if strength_branch(target, control) != rec['branch']:
                rejected['control_lacks_same_weak_rule'] += 1
                continue
            pair = dict(family=f, gana=g, branch=rec['branch'], target=target, control=control)
            idx = len(pairs); pairs.append(pair)
            edges[idx] = net.edge(('family', f), ('cell', la, v), 1,
                                 rank(target['id']+'|'+control['id']))
    flow, cost = net.flow('source', 'sink', 48)
    if flow != 48:
        print('Available families by class:', dict(Counter(
            next(p['gana'] for p in pairs if p['family']==f) for f in {p['family'] for p in pairs})))
        print('Selected by class:', dict(Counter(pairs[i]['gana'] for i,e in edges.items() if e[1]==0)))
    assert flow == 48, (flow, dict(rejected))
    chosen = [pairs[i] for i, e in edges.items() if e[1] == 0]
    chosen.sort(key=lambda p: rank('pair-order|'+p['family']))
    tasks, pairmap = [], []
    for i, p in enumerate(chosen, 1):
        pair_id = f'athematic-pit-{i:02d}'
        pairmap.append(dict(pair_id=pair_id, family=p['family'], gana=p['gana'], branch=p['branch'],
            target_id=p['target']['id'], control_id=p['control']['id']))
        for role in ['target', 'control']:
            t = p[role]
            assert split[t['campaign']['root_family']]['split'] == 'development'
            assert key(t) not in history
            validate_task(t, es[t['dhatu']['code']], 'development')
            t['campaign']['coverage05'] = dict(pair_id=pair_id, role=role, source_branch=p['branch'])
            tasks.append(t)
    # Deterministic transport order; each question remains a separate prompt.
    tasks.sort(key=lambda t: rank('question-order|'+t['id']))
    assert len(tasks) == len({t['id'] for t in tasks}) == len({key(t) for t in tasks}) == 96
    assert Counter(p['gana'] for p in chosen) == Counter(design['class_family_quotas'])
    assert Counter(p['target']['morphology']['vacana'] for p in chosen) == Counter(design['target_numbers'])
    assert Counter(p['control']['morphology']['lakara'] for p in chosen) == Counter(design['control_tense_quotas'])
    write('pilot-06.questions.json', tasks)
    write('pilot-06.pairs.json', pairmap)
    result = dict(created_at=now(), n=96, target_n=48, control_n=48, families=48,
        classes=dict(Counter(t['dhatu']['gana'] for t in tasks)),
        lakaras=dict(Counter(t['morphology']['lakara'] for t in tasks)),
        persons=dict(Counter(t['morphology']['purusha'] for t in tasks)),
        numbers=dict(Counter(t['morphology']['vacana'] for t in tasks)),
        prayogas=dict(Counter(t['morphology']['prayoga'] for t in tasks)),
        branches=dict(Counter(p['branch'] for p in chosen)),
        family_load_histogram=dict(Counter(Counter(t['campaign']['root_family'] for t in tasks).values())),
        gold_variant_histogram=dict(Counter(len(t['gold_slp1']) for t in tasks)),
        generation_policy='oracle-policy-21',
        task_sha256=sha(OUT/'pilot-06.questions.json'), pair_map_sha256=sha(OUT/'pilot-06.pairs.json'),
        design_sha256=sha(OUT/'athematic-panel-design-r1.json'), script_sha256=sha(Path(__file__)),
        source_dependency_hashes={str(p.relative_to(ROOT)):sha(p) for p in [
            ROOT/'misc/vp_4d_coverage05.py',ROOT/'misc/vp_4d_coverage05_athematic.py',
            ROOT/'misc/vp_5d_release_feasibility.py',ROOT/'misc/vp_cartesian_task.py',
            ROOT/'misc/vp_cartesian_prompt_v1.py',ROOT/'benchmarks/creation-campaign-20261006/family-split.json',
            B/'oracle-policy-21.json',OUT/'inventory.json']},
        available_families_with_fresh_choices=len({p['family'] for p in pairs}), candidate_pair_choices=len(pairs),
        assignment_flow=flow, seeded_objective=cost, input_only_rejections=dict(rejected),
        full_regeneration_passed=96, exact_visible_prior_task_overlap=0,
        novelty_scope='Original6687 plus both campaign job input ledgers, including locally excluded records. This does not assert global lexical-family non-exposure; master split acknowledges pre-split legacy exposure.',
        no_test_or_rl_members=True, no_model_answers_read=True, no_paid_calls=True,
        reference_protocol=dict(model='claude-opus-5-5',effort='xhigh',max_output_tokens=65536,prompt_version='cartesian-4d-v1'),
        limitation='One small interaction study: all targets are Kartari/Uttama/Lot and all controls Kartari/Uttama. Exact predicate has only156 reserved-test targets/78 families and cannot constitute a500+ benchmark. No hardness or80% claim.',
        benchmark_ready=False)
    write('pilot-06.manifest.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
