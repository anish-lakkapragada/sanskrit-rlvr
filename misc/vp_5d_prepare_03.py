"""Freeze and audit fresh five-coordinate development calibration; no paid calls."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_5d_pilot import OUT, SPLIT, EXCLUDED_RULES, LAKARAS, VOWELS, atomic_json, now, sha, signature, prior_signatures, entries
from misc.vp_cartesian_task import entry_scope_issue, oracle_issue, make_task, validate_task
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_goal_validate import validate
from vidyut.prakriya import Vyakarana

RUN = 'overnight-calibration-03'
RECIPES = {'causative_of_intensive': ['yaN', 'Ric'],
           'causative_of_intensive_luk': ['yaNluk', 'Ric'], 'desiderative': ['san']}
GANAS = {'Bhvadi': 110, 'Adadi': 8, 'Juhotyadi': 2, 'Divadi': 20, 'Svadi': 4,
         'Tudadi': 18, 'Rudhadi': 3, 'Tanadi': 1, 'Kryadi': 8, 'Curadi': 6}
PASSIVE = {'Lat', 'Lan', 'Lot', 'VidhiLin', 'Lut', 'Lrt'}
BASE = 'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
SOURCE_ROOTS = {'01.0001', '02.0059', '07.0002', '01.1151', '04.0098', '09.0051',
                '09.0071', '01.1164', '08.0010', '01.1047', '01.1075', '01.1121',
                '03.0003', '09.0014', '09.0016'}


def status(phase, message):
    stamp = now()
    atomic_json(OUT/'status.json', {'track': 'five_d', 'run_id': RUN, 'updated_at': stamp,
        'state': 'running', 'phase': phase, 'message': message, 'benchmark_ready': False})
    with (OUT/'progress.md').open('a') as f:
        f.write(f'- {stamp}: {message}\n')


def slots():
    result = []
    for recipe, cycles in [('causative_of_intensive', 10), ('causative_of_intensive_luk', 4), ('desiderative', 1)]:
        for la in LAKARAS:
            for cycle in range(cycles * (3 if la == 'Lun' else 1)):
                passive = recipe != 'desiderative' and la in PASSIVE and cycle < cycles//2
                result.append({'recipe': recipe, 'morphology': {'lakara': la,
                    'prayoga': 'Karmani' if passive else 'Kartari'}})
    # Every PN combination occurs20 times; shuffle assignment independently of grammar slots.
    pn = [(p, v) for p in ['Prathama', 'Madhyama', 'Uttama'] for v in ['Eka', 'Dvi', 'Bahu']] * 20
    random.Random(202610070503).shuffle(pn)
    for slot, (p, v) in zip(result, pn):
        slot['morphology'].update(purusha=p, vacana=v)
    assert len(result) == 180
    return result


def lexical_issue(e, recipe, bases):
    issue = entry_scope_issue(e)
    if issue:
        return issue
    if RECIPES[recipe][0] not in {'yaN', 'yaNluk'}:
        return None
    if old.name(e.dhatu.gana) == 'Curadi':
        return 'intensive_excludes_curadi'
    roots = bases[old.family(e)]
    if not roots or any(not r or r[0] in VOWELS or sum(c in VOWELS for c in r) != 1 for r in roots):
        return 'intensive_requires_consonant_initial_single_vowel_base'
    if any(r in {'ruc', 'SOB', 'SoB'} for r in roots):
        return 'traditional_nonusage_roch_shobh'
    return None


def task_for(e, recipe, morphology, bases, split='development'):
    issue = lexical_issue(e, recipe, bases)
    if issue:
        return None, issue
    t = make_task(e, split, morphology, recipe_id=recipe, sanadi=RECIPES[recipe])
    if t is None:
        return None, 'empty_engine_derivation'
    issue = oracle_issue(t)
    if issue:
        return None, issue
    if len(t['gold_slp1']) > 64:
        return None, 'more_than_64_variants'
    if len(RECIPES[recipe]) > 1 and set(t['campaign']['trace_rule_ids']) & EXCLUDED_RULES:
        return None, 'extended_nested_rule_quarantine'
    return t, None


def source_audit():
    es = {e.code: e for e in old.load_entries()}
    direct = [
        ('04.0098', ['yaNluk', 'Ric'], 'Lun', 'Karmani', 'Prathama', 'aSaMSAmi',
         'https://sa.wikisource.org/wiki/शब्दकौस्तुभः/अध्यायः_१-पादः_१/आह्निकम्_८',
         'Direct Paninian example explicitly attributed to intensive-luk followed by nic.'),
        ('02.0059', ['yaN', 'Ric'], 'Lat', 'Kartari', 'Uttama', 'vevidayAmi',
         'https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV#1025',
         'Direct ordinary-intensive causative control from the earlier audited source panel.'),
        ('08.0010', ['san'], 'Lat', 'Kartari', 'Prathama', 'cikIrzati',
         BASE+'3/3.1.7.htm', 'Direct simple desiderative control.')]
    checks = []
    for code, ops, la, voice, person, expected, url, note in direct:
        m = dict(lakara=la, prayoga=voice, purusha=person, vacana='Eka')
        t = make_task(es[code], 'source_control', m, recipe_id='source_control', sanadi=ops)
        checks.append(dict(code=code, sanadi=ops, morphology=m, expected=expected,
            actual=t['gold_slp1'], passed=expected in t['gold_slp1'], source=url, note=note,
            evidence_level='direct source example; membership only, not exhaustive alternatives'))
    comparisons = []
    expected_lat = {'01.0001': ('boBUyayati', 'boBAvayati'), '02.0059': ('vevidayati', 'vevedayati'),
        '07.0002': ('beBidayati', 'beBedayati'), '01.1151': ('pApacayati', 'pApAcayati')}
    expected_lun = {'01.0001': ('aboBUyat', 'aboBavat'), '02.0059': ('avevidat', 'avevidat'),
        '07.0002': ('abeBidat', 'abeBidat'), '01.1151': ('apApacat', 'apApacat')}
    for code in expected_lat:
        for la, expected in [('Lat', expected_lat[code]), ('Lun', expected_lun[code])]:
            forms = {}
            for i, recipe in enumerate(list(RECIPES)[:2]):
                t = make_task(es[code], 'source_control', dict(lakara=la, prayoga='Kartari',
                    purusha='Prathama', vacana='Eka'), recipe_id=recipe, sanadi=RECIPES[recipe])
                assert expected[i] in t['gold_slp1']
                forms[recipe] = {'expected_rule_derived_form': expected[i], 'gold': t['gold_slp1'],
                    'trace_rules': t['campaign']['trace_rule_ids']}
            comparisons.append({'code': code, 'lakara': la, 'forms': forms,
                'evidence_level': 'Rule-composition control, not direct full-form attestation.',
                'mechanism': 'Independent luk permits ordinary causal strengthening; suffix-caused intensive deletion blocks it. Aorist shortening may neutralize the contrast.'})
    # The same primary passage discusses grah and explicitly rejects indiscriminate it lengthening.
    grah = []
    for la in ['Lut', 'Lrt', 'AshirLin']:
        t = make_task(es['09.0071'], 'source_control', dict(lakara=la, prayoga='Kartari',
            purusha='Prathama', vacana='Eka'), recipe_id='source_control', sanadi=['yaNluk', 'Ric'])
        assert '7.2.37' not in t['campaign']['trace_rule_ids']
        grah.append({'lakara': la, 'forms': t['gold_slp1'], 'long_it_rule_present': False})
    data = {'created_at': now(), 'run_id': RUN, 'direct_checks': checks,
        'all_direct_examples_found': all(c['passed'] for c in checks), 'contrast_controls': comparisons,
        'grah_lengthening_checks': grah,
        'primary_mechanism_sources': [
            {'rule': '1.1.4', 'url': 'https://sanskritdocuments.org/~sanskrit/learning_tools/sarvanisutrani/1.1.4.htm',
             'supports': 'Blocking requires deletion caused by the ardhadhatuka suffix, not every earlier deletion.'},
            {'rule': '2.4.74', 'url': BASE+'2/2.4.74.htm', 'supports': 'Independent intensive-luk and classical finite examples.'},
            {'rule': '1.1.62', 'url': BASE+'1/1.1.63.htm', 'supports': 'Luk does not preserve every deleted-suffix-conditioned stem operation; archive filename offset noted.'},
            {'rule': '6.1.8/11', 'url': BASE+'6/6.1.8.htm', 'supports': 'Existing reduplication prevents another reduplication when causative aorist cang is added.'},
            {'rule': '7.4.1', 'url': BASE+'7/7.4.1.htm', 'supports': 'Causative aorist penultimate shortening can neutralize non-aorist stem contrasts.'},
            {'rule': '7.4.91', 'url': BASE+'7/7.4.91.htm', 'supports': 'Three reduplicative augment alternatives for intensive-luk r-penultimate roots.'},
            {'rule': '7.3.86', 'url': BASE+'7/7.3.86.htm', 'supports': 'Guna of a light penultimate vowel in the eligible causal context.'},
            {'rule': '7.2.116', 'url': BASE+'7/7.2.116.htm', 'supports': 'Causal vrddhi of eligible penultimate a.'},
            {'rule': '6.4.51', 'url': BASE+'6/6.4.51.htm', 'supports': 'Loss of nic in anit passive/aorist environments.'},
            {'rule': '7.2.37', 'url': BASE+'7/7.2.37.htm', 'supports': 'Do not extend simple-root grah it lengthening indiscriminately to nested derivatives.'}],
        'extended_quarantine': sorted(EXCLUDED_RULES),
        'policy': 'All shared policy04 scope and oracle gates, plus existing five nested-rule exclusions extended to yaNluk→Ric.',
        'new_confirmed_oracle_errors': 0, 'new_additional_quarantines': [],
        'limits': ['Only selected direct forms have source attestation. The complete new recipe panel is supported by rule composition and regeneration, not exhaustive independent certification.',
                   'The inspected grah corner did not reveal a new disagreement; this is not a proof that existing exclusions are exhaustive.',
                   'A paid development pilot needs systematic disagreement review before any release.'],
        'source_control_codes_excluded_from_pilot03': sorted(SOURCE_ROOTS)}
    atomic_json(OUT/'pilot-03.source-audit.json', data)
    assert data['all_direct_examples_found']


def freeze():
    path = OUT/'pilot-03.plan.json'
    if path.exists():
        raise RuntimeError('Preserve frozen plan')
    ss = slots()
    plan = {'frozen_at': now(), 'run_id': RUN, 'seed': 202610070503, 'n': 180,
        'recipe_operations': RECIPES, 'recipe_counts': dict(Counter(s['recipe'] for s in ss)),
        'gana_quotas': GANAS, 'lakara_quotas': dict(Counter(s['morphology']['lakara'] for s in ss)),
        'voice_quotas': dict(Counter(s['morphology']['prayoga'] for s in ss)),
        'person_number_quotas': {'/'.join((p,v)):20 for p in ['Prathama','Madhyama','Uttama'] for v in ['Eka','Dvi','Bahu']},
        'family_cap': 1, 'slots': ss, 'source_control_codes_excluded': sorted(SOURCE_ROOTS),
        'reason': 'Test stable intensive-causal stem preservation and a new independently supported intensive-luk-causal contrast; 25% aorist tests inherited reduplication and shortening while each other lakara retains 8.33%.',
        'class_reason': '61.1% Bhvadi and smaller remaining-class quotas reflect eligible dictionary supply more closely than equal or original pilot quotas. Every class remains represented, with Curadi assigned only to simple desiderative.',
        'phonology_policy': 'No error-derived vowel whitelist. Seeded sampling across eligible dictionary roots; publish vowel/cluster distributions and score prespecified mechanism groups.',
        'novelty': 'Exclude all known prior development tuple signatures and all source-control roots; prefer families absent from both earlier five_d pilots. Family reuse across panels is reported.',
        'selection': 'All weights fixed before pilot03 evaluation; no held-out model answers or same-item failure selection.',
        'interpretation': 'Development hypothesis only. New recipe performance is unknown; earlier intensive-causal aorist cell contains only8 completed answers.',
        'oracle_policy': 'Shared policy04; five nested exclusions extended to intensive-luk→causative.', 'benchmark_ready': False}
    atomic_json(path, plan)
    status('Pilot03 grammar weights frozen', 'Frozen180-task plan:120 intensive→causative,48 intensive-luk→causative,12 desiderative;45 aorists and15 of every other lakara, all ten classes.')


def generate():
    path = OUT/'pilot-03.tasks.json'
    if path.exists():
        raise RuntimeError('Preserve frozen membership')
    plan_path = OUT/'pilot-03.plan.json'
    plan = json.loads(plan_path.read_text())
    assert json.loads((OUT/'pilot-03.source-audit.json').read_text())['all_direct_examples_found']
    es = entries(); v = Vyakarana()
    bases = {f: sorted({p.text for p in v.derive(e.dhatu)}) for f,e in es.items()}
    prior = [t for name in ['01','02'] for t in json.loads((OUT/f'pilot-{name}.tasks.json').read_text())]
    prior_families = {t['campaign']['root_family'] for t in prior}
    used_before = prior_signatures() | {signature(t) for t in prior}
    rng = random.Random(plan['seed']); rejected = Counter(); ss = plan['slots']; tasks = None
    for attempt in range(200):
        free = list(range(len(ss))); assigned = {}
        for gana in ['Curadi','Tanadi','Juhotyadi','Svadi','Rudhadi','Adadi','Kryadi','Divadi','Tudadi','Bhvadi']:
            eligible = [i for i in free if gana != 'Curadi' or ss[i]['recipe'] == 'desiderative']
            for i in rng.sample(eligible, GANAS[gana]):
                assigned[i] = gana; free.remove(i)
        family_set = set(); chosen = []; rank = {i: rng.random() for i in range(len(ss))}
        order = sorted(range(len(ss)), key=lambda i: (sum(old.name(e.dhatu.gana)==assigned[i] for e in es.values()),rank[i]))
        for i in order:
            slot = ss[i]
            candidates = [e for f,e in es.items() if f not in family_set and old.name(e.dhatu.gana)==assigned[i] and e.code not in SOURCE_ROOTS]
            rng.shuffle(candidates); candidates.sort(key=lambda e: old.family(e) in prior_families)
            for e in candidates:
                t, issue = task_for(e, slot['recipe'], slot['morphology'], bases)
                if issue:
                    rejected[issue] += 1; continue
                if signature(t) in used_before:
                    rejected['previous_development_tuple'] += 1; continue
                t['campaign'].update(panel='five-d-pilot-03', slot=i,
                    sampling_cell={'recipe_id':slot['recipe'], 'lakaras':[slot['morphology']['lakara']],
                        'prayogas':[slot['morphology']['prayoga']],
                        'exclude_rules':sorted(EXCLUDED_RULES) if len(RECIPES[slot['recipe']])>1 else [],
                        'exclude_ganas':['Curadi'] if len(RECIPES[slot['recipe']])>1 else []},
                    lexical_bases=bases[old.family(e)], plan_sha256=sha(plan_path),
                    selection_reason=plan['selection'], oracle_policy=plan['oracle_policy'],
                    audit_status='Shared regeneration/roundtrip and source-controlled recipe; rare full forms use rule-composition evidence.')
                chosen.append(t); family_set.add(old.family(e)); break
            else:
                break
        if len(chosen)==len(ss):
            tasks=chosen;break
    if tasks is None:
        raise RuntimeError('Frozen quotas have insufficient supply under current greedy attempts')
    rng.shuffle(tasks)
    for t in tasks:
        validate_task(t, es[t['campaign']['root_family']], 'development')
    audit = validate(tasks, 'development')
    assert len({signature(t) for t in tasks})==180 and len(family_set)==180
    assert all(signature(t) not in used_before for t in tasks)
    distribution = {k:dict(Counter(t['morphology'][k] for t in tasks)) for k in ['lakara','prayoga','purusha','vacana']}
    distribution.update(recipe=dict(Counter(t['derivation']['recipe_id'] for t in tasks)),
        gana=dict(Counter(t['dhatu']['gana'] for t in tasks)),
        person_number=dict(Counter(t['morphology']['purusha']+'/'+t['morphology']['vacana'] for t in tasks)),
        lexical_vowels=dict(Counter(''.join(c for c in t['campaign']['lexical_bases'][0] if c in VOWELS) for t in tasks)),
        gold_variants=dict(Counter(len(t['gold_slp1']) for t in tasks)))
    assert distribution['gana']==GANAS and distribution['person_number']==plan['person_number_quotas']
    atomic_json(path,tasks); atomic_json(OUT/'pilot-03.runner-audit.json',audit)
    atomic_json(OUT/'pilot-03.prompts.json',[{'id':t['id'],'prompt':render(t)} for t in tasks])
    manifest={'created_at':now(),'run_id':RUN,'n':180,'root_families':180,'family_cap':1,
        'families_absent_from_prior_five_d_pilots':len(family_set-prior_families),
        'families_reused_from_prior_five_d_pilots':len(family_set&prior_families),
        'fresh_tuple_count':180,'seed':plan['seed'],'task_file':str(path),'task_file_sha256':sha(path),
        'plan_sha256':sha(plan_path),'generator_sha256':sha(Path(__file__)),
        'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'renderer_sha256':sha(ROOT/'misc/vp_cartesian_prompt_v1.py'),
        'dictionary_sha256':sha(old.TSV),'family_split_sha256':sha(SPLIT),
        'source_audit_sha256':sha(OUT/'pilot-03.source-audit.json'),'vp_version':tasks[0]['campaign']['vp_version'],
        'distribution':distribution,'sampling_rejections':dict(rejected),'class_assignment_attempts':attempt+1,
        'prior_tuple_signatures':len(used_before),'benchmark_ready':False}
    atomic_json(OUT/'pilot-03.manifest.json',manifest)
    request={'created_at':now(),'track':'five_d','label':'opus-five-d-pilot-03','n':180,
        'phase':'fresh_development_pilot','status':'ready_for_coordinator_review_not_submitted',
        'task_file':str(path),'relative_task_file':str(path.relative_to(ROOT)),'task_file_sha256':sha(path),
        'split':'development','provider':'Anthropic','reference_model':'Opus5.5','reasoning_effort':'xhigh',
        'max_output_tokens':16384,'prompt_version':'cartesian-5d-v1','task_type':'cartesian_5d',
        'recipe_menu':RECIPES,'recipe_counts':plan['recipe_counts'],
        'manifest':str(OUT/'pilot-03.manifest.json'),'plan':str(plan_path),
        'audit':str(OUT/'pilot-03.runner-audit.json'),'source_review':str(OUT/'pilot-03.source-audit.json'),
        'rationale':plan['reason'],'pairing_recommendation':'Pair identical audited tasks with Astra after Opus disagreement review, subject to coordinator budget.',
        'frozen_diagnostic_groups':['recipe','recipe×aorist/other','recipe×voice','recipe×lexical vowel i/u/F versus other','recipe×trace6.4.49','recipe×trace7.4.91'],
        'worker_paid_calls':0,'spending_authority':'Coordinator only under shared cumulative caps.',
        'benchmark_ready':False}
    atomic_json(OUT/'pilot-03.experiment-request.json',request)
    status('Fresh180-task pilot validated', f'All180 tasks regenerate and pass scope, split and prompt audits; {len(family_set-prior_families)} families are absent from both earlier five_d pilots. Preparing cross-panel and scale limitations.')
    print(json.dumps({'n':180,'new_families':len(family_set-prior_families),'hash':sha(path),'distribution':distribution},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['sources','freeze','generate']);a=p.parse_args()
    {'sources':source_audit,'freeze':freeze,'generate':generate}[a.command]()
