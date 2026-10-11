"""Post-settlement review of the complete frozen ordinary4D pilot06 only."""
import hashlib
import json
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_cartesian_task import entry_scope_issue, oracle_issue, entries_by_code
from misc.vp_cartesian_prompt_v1 import render

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'benchmarks/parallel-search-20261006/four_d/coverage-05'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, data):
    p = BASE / name
    assert not p.exists(), 'Preserve completed review'
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    job = read(ROOT/'benchmarks/iterative-goal-20261006/ledger.json')['jobs']['opus-four-d-pilot-06']
    assert job['settled'] and job['collected_at']
    a = read(BASE/'pilot-06.analysis.json')
    assert a['all96_settled_and_collected']
    assert sha(BASE/'pilot-06.analysis.json') == 'd69e0bdd9054578ccb2e892eb6e525ceabce456cb49057d6e1d49a4600bcc356'
    rp = Path(a['result_path'])
    assert sha(rp) == a['result_sha256']
    rs, decl, es = read(rp), read(BASE/'analysis-predeclaration.json'), entries_by_code()
    assert len(rs) == 96 and all(r['is_correct'] is True and r['status']=='completed'
        and r['answer'] is not None and not r['truncated'] for r in rs)
    for base, table in [(BASE, decl['files']), (ROOT, decl['dependencies'])]:
        for f, h in table.items():
            assert sha(base/f) == h
    issues = []
    strict = prompt = single = 0
    for r in rs:
        t = r['task']
        why = entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)
        if why:
            issues.append(dict(id=t['id'], reason=why))
        strict += unicodedata.normalize('NFC', r['answer'].strip()) in {
            unicodedata.normalize('NFC', g) for g in t['gold_devanagari']}
        single += len(r['answer'].strip().split()) == 1
        prompt += hashlib.sha256(render(t).encode()).hexdigest() == t['campaign']['prompt_sha256']
    assert not issues and strict == prompt == single == 96
    codes = {'02.0038','03.0009','05.0005','05.0021','07.0007','07.0013',
             '08.0002','09.0001','09.0008','09.0010','09.0045'}
    representatives = [dict(id=r['task']['id'], code=r['task']['dhatu']['code'],
        role=r['task']['campaign']['coverage05']['role'],
        branch=r['task']['campaign']['coverage05']['source_branch'],
        morphology=r['task']['morphology'], answer=r['answer'],
        accepted_forms=r['task']['gold_devanagari'], correct=True)
        for r in rs if r['task']['dhatu']['code'] in codes]
    now = datetime.now(timezone.utc).isoformat()
    review = dict(
        created_at=now, run_id='overnight-pilot06-review-06',
        disposition='Close this mechanism as an unsupported hardness lead under the frozen trigger. No further paid exploration recommended.',
        analysis_sha256=sha(BASE/'pilot-06.analysis.json'), result_sha256=sha(rp),
        task_sha256=sha(BASE/'pilot-06.questions.json'),
        analysis_predeclaration_sha256=sha(BASE/'analysis-predeclaration.json'),
        review_script_sha256=sha(Path(__file__)),
        raw_data_or_frozen_artifacts_changed=False,
        full96_settled_before_answer_access=True, pilot08_outcomes_read=False,
        reference_protocol=dict(model='claude-opus-5-5', effort='xhigh',
                                max_output_tokens=65536, prompt='cartesian-4d-v1'),
        results=dict(all_correct=96, all_submitted=96, all_usable=96,
            target_correct=48, target_n=48, control_correct=48, control_n=48,
            wrong_completed_target_families=0, wrong_completed_control_families=0,
            refusals=0, truncations=0, unparsed_completed=0,
            paired_difference=0, paid_cost_usd=0.382422),
        trigger=a['trigger'], disagreements=[], nonusable=[],
        success_audit=dict(strict_NFC_membership_matches=strict,
            single_form_answers=single, prompt_hash_matches=prompt,
            current_scope_issues=issues, correct_and_incorrect_treated_symmetrically=True,
            representatives=representatives, representative_count=len(representatives),
            accepted_union_sizes=dict(Counter(len(r['task']['gold_devanagari']) for r in rs))),
        source_review=dict(
            frozen_source_audit_sha256=sha(BASE/'pilot-06.source-audit.json'),
            frozen_source_controls_sha256=sha(BASE/'pilot-06.source-controls.json'),
            independent_review_path='../pilot-06-independent-review/review.json',
            independent_review_sha256=sha(BASE.parent/'pilot-06-independent-review/review.json'),
            finding='No concrete source/prompt issue found in representative successes or optional branches. All 96 retain complete allowed gold unions. No disagreements exist, so no disagreement-driven exclusion is proposed.',
            optional_variants='Stumbh 09.0008 and skumbh 09.0010 return the valid sna branch; snu alternatives remain accepted. Ubhayapada entries retain both valid padas; exclusively middle entries such as 05.0021, 07.0013 and 09.0045 return their middle forms.'),
        uncertainty=dict(role_n=48, role_families=48,
            role_nominal_Wilson95=a['roles']['target']['all_request_wilson95'],
            empirical_family_bootstrap='All observed family pairs succeed, so resampling yields 100% role accuracy and zero difference in every draw. Zero SE and zero-width intervals reflect degeneracy, not proof of zero population uncertainty or guaranteed sub-one-point precision.',
            missingness='All 96 complete; response bounds equal observed scores, with no missing-completion sensitivity.',
            scope='Conditional coverage diagnostic: no claimed population inclusion probabilities, selection-adjusted inference or independence between morphologically similar families.'),
        scaling=dict(reserved_test_target_tuples=156, reserved_test_families=78,
            max_share_at1660=156/1660, standalone500_feasible=False,
            finding='No observed target difficulty to add to a broader mixture. Scarce target supply would limit contribution even if future evidence differed.'),
        proposed_shared_policy_changes=[], new_provider_calls=0,
        new_generation_requested=False, benchmark_ready=False,
        global_impossibility_claim=False)
    save('pilot-06.result-review.json', review)
    save('result-verdict.json', dict(created_at=now,
        status='lead_closed_after_full96', prior_prospective_decision_preserved='decision.json',
        review='pilot-06.result-review.json', review_sha256=sha(BASE/'pilot-06.result-review.json'),
        all_correct=96, target_correct=48, control_correct=48,
        frozen_trigger_passed=False, further_paid_exploration_recommended=False,
        current_four_d_goal='Unresolved: no source-clean, diverse 79–81% benchmark established.',
        global_impossibility_claim=False, benchmark_ready=False))
    print('Reviewed', len(representatives), 'representative success rows; scope/prompt checks applied to all 96.')
    print('Result review SHA', sha(BASE/'pilot-06.result-review.json'))


if __name__ == '__main__':
    main()
