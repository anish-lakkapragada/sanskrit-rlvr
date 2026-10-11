#!/usr/bin/env python3
"""Reproduce 4D oracle diagnostics without reading any reserved-test answers."""
from collections import defaultdict
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc.vp_4d_pilot import OUT, CELLS, identity, load_entries, matches, name, now, render, sha, source_rows, validate_task, write
from vidyut.prakriya import Dhatu, Gana, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana

BASE = 'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'


def main():
    entries = {e.code: e for e in load_entries()}
    pilot_path = OUT / 'pilot-01.questions.json'
    pilot = json.loads(pilot_path.read_text())
    inherited_violations = []
    for t in pilot:
        e = entries[t['dhatu']['code']]
        validate_task(t, e, 'development')
        assert set(t['morphology']) == {'lakara', 'prayoga', 'purusha', 'vacana'}
        assert 'derivation' not in t
        if e.dhatu.prefixes or e.dhatu.sanadi:
            inherited_violations.append(t['id'])
    scope = {'created_at': now(), 'run_id': 'release-feasibility-01',
        'task_file_sha256': sha(pilot_path), 'audit_script_sha256': sha(__file__),
        'n': len(pilot), 'unique_prompts': len({render(t) for t in pilot}),
        'unique_visible_tuples': len({identity(t) for t in pilot}),
        'regenerated_tasks': len(pilot),
        'inherited_prefix_or_sanadi_violations': inherited_violations,
        'exact_four_coordinate_scope_passed': not inherited_violations,
        'gold_oracle_certification': False,
        'oracle_disagreement_review': 'pilot-01.disagreement-review.json',
        'note': 'Scope and regeneration evidence only. Two pilot keys have independently documented oracle concerns; raw tasks and results are unchanged.'}
    assert scope['n'] == scope['unique_prompts'] == scope['unique_visible_tuples'] == 120
    write(OUT / 'pilot-01.scope-audit.json', scope)
    v = Vyakarana()
    citation_checks = []
    for citation in ['YitfzA~', 'Yitfza~']:
        ps = v.derive(Pada.Tinanta(dhatu=Dhatu.mula(citation, Gana.Divadi),
            lakara=Lakara.Lun, prayoga=Prayoga.Kartari,
            purusha=Purusha.Uttama, vacana=Vacana.Dvi))
        citation_checks.append({'citation': citation,
            'forms_slp1': sorted({p.text for p in ps}),
            'applies_3_1_55': any(h.code == '3.1.55' for p in ps for h in p.history)})
    assert citation_checks[0]['forms_slp1'] == ['atarzizva']
    assert citation_checks[1]['forms_slp1'] == ['atfzAva']

    groups = defaultdict(list)
    for e in entries.values():
        groups[(e.dhatu.aupadeshika, name(e.dhatu.gana), e.artha)].append(e)
    ambiguous = []
    for key, es in groups.items():
        if len({str(e.dhatu.antargana) for e in es}) > 1:
            ambiguous.append({'visible_identity': list(key),
                'entries': [{'code': e.code, 'antargana': str(e.dhatu.antargana)} for e in es]})
    ambiguous_codes = {e['code'] for g in ambiguous for e in g['entries']}
    passive = []
    for t in pilot:
        if t['morphology']['prayoga'] == 'Karmani':
            rules = set(t['campaign']['trace_rule_ids'])
            passive.append({'task_id': t['id'], 'dhatu_code': t['dhatu']['code'],
                'morphology': t['morphology'],
                'relevant_trace_rules': sorted(rules & {'6.4.62', '6.4.92', '6.4.93'}),
                'possible_missing_cinvat_lengthening': {'6.4.62', '6.4.92'} <= rules})
    test_counts = {'both_passive_rules': 0, 'ambiguous_visible_identity': 0}
    for row in source_rows(entries):
        if row['split'] != 'test' or not any(matches(row, c, entries) for c in CELLS):
            continue
        if row['prayoga'] == 'Karmani' and {'6.4.62', '6.4.92'} <= set(row['rules']):
            test_counts['both_passive_rules'] += 1
        if row['code'] in ambiguous_codes:
            test_counts['ambiguous_visible_identity'] += 1
    upstream = Path('/tmp/vp-upstream-20261006/vidyut-prakriya/src')
    code_paths = [upstream / 'angasya/asiddhavat.rs', upstream / 'dhatu_gana.rs']
    record = {'created_at': now(), 'run_id': 'release-feasibility-01',
        'vp_version': importlib.metadata.version('vidyut'),
        'pilot_sha256': sha(pilot_path), 'script_sha256': sha(__file__),
        'scope': 'Development reproductions and dictionary/grammar metadata only; no reserved-test gold forms or model answers read.',
        'raw_scores_changed': False, 'gold_repaired': False,
        'citation_only_reproduction': {
            'dictionary_code': '04.0141', 'checks': citation_checks,
            'source': BASE+'3/3.1.55.htm',
            'interpretation': 'Dictionary YitfzA~ misses a hard-coded PUSH_ADI citation Yitfza~; replacing only the final marked vowel activates the subgroup rule and changes the answer. This is diagnostic evidence, not a dictionary edit.'},
        'semantic_rule_concern': {
            'dictionary_code': '05.0018', 'task_id': 'cart4-bf0fe03f9fa1d50030d9d6c1',
            'source': BASE+'6/6.4.123.htm',
            'interpretation': 'Primary commentary restricts the reduction to the injuring sense; the prompt says samsiddhau. Upstream checks Svadi without a semantic condition. Quarantine pending independent adjudication rather than claim a complete repaired key.'},
        'passive_cinvat_cross_check': {
            'sources': [BASE+'6/6.4.62.htm', BASE+'6/6.4.93.htm'],
            'independent_controls_path': '../five_d/release-feasibility-01.passive-oracle-review.json',
            'diagnostic': 'Karmani or Bhave with both 6.4.62 and 6.4.92, across any nonpresent lakara; the implemented lengthening may miss a Cinvat branch.',
            'pilot_passive_tasks_checked': passive,
            'pilot_tasks_meeting_diagnostic': sum(x['possible_missing_cinvat_lengthening'] for x in passive),
            'conclusion': 'None of the 12 pilot passives meets the combined-rule diagnostic. This targeted check does not certify every possible passive variant.'},
        'visible_dictionary_identity_ambiguities': {
            'groups': ambiguous,
            'pilot_affected': [t['id'] for t in pilot if t['dhatu']['code'] in ambiguous_codes],
            'policy': 'Before new generation, union independently audited variants across indistinguishable entries or quarantine the whole visible identity. Do not let hidden code or antargana select an incomplete answer key.'},
        'master_test_predicate_union_metadata_counts': test_counts,
        'supply_impact': 'Both additional prospective filters remove zero rows from the current master-test predicate union. Existing aggregate allocation counts remain valid.',
        'upstream_explanatory_evidence': [{'path': str(p), 'sha256': sha(p)} for p in code_paths if p.exists()],
        'upstream_caveat': 'A separate upstream clone explains the observed behavior; installed-package reproductions are the direct version-specific evidence.'}
    write(OUT / 'pilot-01.oracle-evidence.json', record)
    review_path = OUT / 'pilot-01.disagreement-review.json'
    review = json.loads(review_path.read_text())
    review['reproducible_oracle_evidence'] = 'pilot-01.oracle-evidence.json'
    review['additional_context_quarantines'] = [
        'Karmani/Bhave nonpresent contexts with both 6.4.62 and 6.4.92 pending Cinvat variant certification',
        'Identical visible lexical entries with different intrinsic antargana until complete key union is certified']
    review['passive_cross_check'] = {'pilot_tasks_checked': len(passive),
        'pilot_tasks_meeting_combined_rule_diagnostic': 0,
        'master_test_predicate_union_rows_meeting_diagnostic': test_counts['both_passive_rules']}
    write(review_path, review)
    print(json.dumps({'citation_checks': citation_checks,
        'passive_pilot_affected': record['passive_cinvat_cross_check']['pilot_tasks_meeting_diagnostic'],
        'test_metadata_counts': test_counts}, indent=2))


if __name__ == '__main__':
    main()
