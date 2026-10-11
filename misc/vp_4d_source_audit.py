#!/usr/bin/env python3
"""Independent primary-grammar examples for the 4D pilot; offline VP checks."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_4d_pilot import OUT, load_entries, make_task, write, now, sha, identity

BASE = 'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'


def url(rule):
    return BASE + rule.split('.')[0] + '/' + rule + '.htm'


CONTROLS = [
    ('01.0022', 'Lat', 'Kartari', 'Prathama', 'Eka', ['KUrdate'], '8.2.78'),
    ('01.0022', 'Lit', 'Kartari', 'Prathama', 'Eka', ['cuKUrde'], '8.2.78'),
    ('03.0001', 'Lat', 'Kartari', 'Prathama', 'Eka', ['juhoti'], '6.1.10'),
    ('03.0001', 'Lat', 'Kartari', 'Prathama', 'Dvi', ['juhutaH'], '6.1.10'),
    ('03.0007', 'Lat', 'Kartari', 'Prathama', 'Eka', ['mimIte'], '6.4.113'),
    ('09.0016', 'Lat', 'Kartari', 'Prathama', 'Dvi', ['lunItaH'], '6.4.113'),
    ('09.0014', 'Lat', 'Kartari', 'Prathama', 'Dvi', ['punItaH'], '6.4.113'),
    ('08.0010', 'Lit', 'Kartari', 'Prathama', 'Eka', ['cakAra'], '7.4.62'),
    ('01.1020', 'Lit', 'Kartari', 'Prathama', 'Eka', ['caKAna'], '7.4.62'),
    ('01.1046', 'Lit', 'Kartari', 'Prathama', 'Eka', ['jahAra'], '7.4.62'),
    ('08.0010', 'Lun', 'Kartari', 'Prathama', 'Eka', ['akArzIt'], '3.1.44'),
    ('01.1046', 'Lun', 'Kartari', 'Prathama', 'Eka', ['ahArzIt'], '3.1.44'),
    ('01.1108', 'AshirLin', 'Kartari', 'Madhyama', 'Bahu', ['cyozIQvam'], '8.3.78'),
    ('01.1112', 'AshirLin', 'Kartari', 'Madhyama', 'Bahu', ['plozIQvam'], '8.3.78'),
    ('01.1108', 'Lun', 'Kartari', 'Madhyama', 'Bahu', ['acyoQvam'], '8.3.78'),
    ('01.1112', 'Lun', 'Kartari', 'Madhyama', 'Bahu', ['aploQvam'], '8.3.78'),
    ('08.0010', 'Lit', 'Kartari', 'Madhyama', 'Bahu', ['cakfQve'], '8.3.78'),
    ('05.0005', 'Lrt', 'Karmani', 'Prathama', 'Eka', ['cAyizyate', 'cezyate'], '6.4.62'),
    ('05.0005', 'Lut', 'Karmani', 'Prathama', 'Eka', ['cAyitA', 'cetA'], '6.4.62'),
    ('05.0005', 'AshirLin', 'Karmani', 'Prathama', 'Eka', ['cAyizIzwa', 'cezIzwa'], '6.4.62'),
    ('09.0071', 'Lrt', 'Karmani', 'Prathama', 'Eka', ['grAhizyate', 'grahIzyate'], '6.4.62'),
    ('06.0015', 'Lit', 'Kartari', 'Prathama', 'Eka', ['ucCAYcakAra'], '3.1.36'),
]


def main():
    entries = {e.code: e for e in load_entries()}
    results = []
    for code, la, pr, pu, va, expected, rule in CONTROLS:
        task = make_task(entries[code], 'source_control',
                         {'lakara': la, 'prayoga': pr, 'purusha': pu, 'vacana': va})
        result = {'dhatu_code': code, 'citation': entries[code].dhatu.aupadeshika,
                  'morphology': task['morphology'], 'expected_source_forms_slp1': expected,
                  'generated_forms_slp1': task['gold_slp1'], 'source_url': url(rule),
                  'source_matches': set(expected) <= set(task['gold_slp1'])}
        results.append(result)
    questions = json.loads((OUT / 'pilot-01.questions.json').read_text())
    keys = {identity(t) for t in questions}
    overlaps, current_panel_mirrors = [], []
    paths = sorted((ROOT / 'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json'))
    for path in paths:
        panel = json.loads(path.read_text())
        if path.parent.name in {'opus-four-d-pilot-01', 'astra-four-d-pilot-01'} and panel == questions:
            current_panel_mirrors.append(str(path.relative_to(ROOT)))
            continue
        for t in panel:
            for x in t.get('forms', [t]):
                if 'dhatu' not in x or set(x.get('morphology', {})) != {'lakara', 'prayoga', 'purusha', 'vacana'}:
                    continue
                d = x.get('derivation', {})
                if d.get('sanadi') or d.get('prefixes'):
                    continue
                if identity(x) in keys:
                    overlaps.append({'task': x['id'], 'path': str(path.relative_to(ROOT))})
    result = {'created_at': now(), 'controls': results,
              'passed_source_examples': sum(r['source_matches'] for r in results),
              'number_of_source_examples': len(results),
              'additional_pure_4d_prior_prompt_overlaps': overlaps,
              'additional_prior_panels_checked': len(paths),
              'excluded_current_panel_evaluation_copies': current_panel_mirrors,
              'all_passed': all(r['source_matches'] for r in results) and not overlaps,
              'generator_sha256': sha(__file__),
              'source_status': 'Primary Sanskrit grammatical commentaries consulted via web on 2026-10-07 UTC; expected forms transcribed before local verification.',
              'construction_reviews': [
                  {'cells': ['internal_rv_lengthening'], 'source': url('8.2.78'),
                   'rationale': 'The commentaries explain internal r/v-conditioned vowel lengthening and directly give the Khurd present/perfect examples. The narrow root supply is an explicit limitation.'},
                  {'cells': ['perfect_reduplication_changes', 'svadi_perfect', 'other_athematic_perfect'],
                   'sources': [url('7.4.62'), url('7.4.70'), url('3.1.36')],
                   'rationale': 'Perfect reduplication changes coexist with periphrastic perfects for eligible stems. In compound perfects, a selected trace rule can operate on the auxiliary rather than the lexical root.'},
                  {'cells': ['athematic_present_system'], 'sources': [url('6.1.10'), url('6.4.113')],
                   'rationale': 'Reduplication and weak-stem vocalism have explicit conditioned rules and worked examples; dictionary root class is part of the lexical identity.'},
                  {'cells': ['divadi_sigmatic_aorist', 'aorist_consonant_changes', 'primary_benedictive_stem_changes'],
                   'sources': [url('3.1.44'), url('8.3.78')],
                   'rationale': 'Sigmatic aorist formation and conditioned dh-retroflexion are explicitly attested; controls cover both aorist and benedictive.'},
                  {'cells': ['transitive_curadi_nonpresent_passive'],
                   'sources': [url('6.4.51'), url('6.4.62')],
                   'rationale': 'Nonpresent passive alternatives and suffix deletion are grammatical, including optional treatment under 6.4.62. Candidate roots are restricted to exact dictionary meanings of cutting, breaking, binding, giving, taking, eating, killing/injury, abandoning, scraping, or crushing.'},
              ],
              'known_context_review': [
                  'All Bhave tasks are excluded, avoiding the historical impersonal clusters.',
                  'No added sanadi or prefixes: prior nested yaN/Ric/san oracle concerns are not selected constructions.',
                  'Curadi uses only the entry.dhatu dictionary object. Its class-inherent formation is not an independently added derivation coordinate.',
                  'No separately fixed pada. The answer key accepts the full VP union; a model may give any licensed form.',
              ],
              'limits': ['Representative source examples are independent of VP test assertions, but are not an exhaustive linguistic certification of all 120 task keys.',
                         'Some source passages are editorially imperfect; expected example strings were read alongside the grammatical context.',
                         'The audit does not establish the accuracy target or standard error requirement. All substantive model-oracle disagreements remain reviewable.']}
    write(OUT / 'source-audit-01.json', result)
    print(json.dumps({'passed': result['passed_source_examples'], 'total': len(results),
                      'failed': [r for r in results if not r['source_matches']],
                      'prior_overlaps': overlaps}, ensure_ascii=False, indent=2))
    if not result['all_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
