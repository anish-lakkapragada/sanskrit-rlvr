"""Unpaid exact-entry scope inventory and VP controls; no model output/API access."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_cartesian_task import GRAMMAR, entries_by_code, entry_scope_issue
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Sanadi, Vacana

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'benchmarks/parallel-search-20261006'
OUT = B / 'four_d/svadi-three-scope-review-01'
CODES = {'05.0013', '05.0014', '05.0015'}
CONTROLS = ['05.0013', '05.0014', '05.0015', '01.0919', '01.1082',
            '03.0004', '03.0005', '09.0022', '10.0022']


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    master = read(ROOT / 'benchmarks/creation-campaign-20261006/family-split.json')
    entries = entries_by_code()
    controls = []
    for code in CONTROLS:
        e = entries[code]
        family = next(f for f, v in master['families'].items() if code in v['codes'])
        for ops in [[], ['san']]:
            dhatu = e.dhatu.with_sanadi([getattr(Sanadi, x) for x in ops])
            rs = GRAMMAR.derive(Pada.Tinanta(dhatu=dhatu, lakara=Lakara.Lat,
                prayoga=Prayoga.Kartari, purusha=Purusha.Prathama, vacana=Vacana.Eka))
            controls.append(dict(code=code, citation=e.dhatu.aupadeshika,
                gana=str(e.dhatu.gana), artha=e.artha, family=family,
                split=master['families'][family]['split'], operations=ops,
                morphology=dict(lakara='Lat', prayoga='Kartari', purusha='Prathama', vacana='Eka'),
                held_by_this_predicate=code in CODES,
                current_entry_scope_issue=entry_scope_issue(e),
                engine_forms=sorted({r.text for r in rs}),
                trace_rules=sorted({h.code for r in rs for h in r.history}),
                interpretation='Identity/mechanical control only; no claim of classical licensing or independent grammatical certification.'))
    assert all(c['current_entry_scope_issue'] is not None for c in controls if c['held_by_this_predicate'])
    assert all(c['current_entry_scope_issue'] is None for c in controls if not c['held_by_this_predicate'])
    panels = {}
    for name, rel in [
        ('original_unsubmitted_pilot08', 'five_d/pilot-08/tasks.json'),
        ('original_unsubmitted_astra240', 'five_d/pilot-08/astra-subset/tasks.json'),
        ('candidate04_inputs_only', 'five_d/candidate-4800/revision-04/tasks.json'),
        ('astra_cap_development60', 'five_d/astra-cap-development-01.tasks.json'),
    ]:
        p = B / rel
        ts = read(p)
        affected = [dict(id=t['id'], code=t['dhatu']['code'],
            family=t['campaign']['root_family'], operations=t.get('derivation', {}).get('sanadi', []),
            morphology=t['morphology']) for t in ts if t['dhatu']['code'] in CODES]
        panels[name] = dict(path=str(p.relative_to(ROOT)), sha256=sha(p), n=len(ts),
                            affected_n=len(affected), affected=affected)
    expected = {'original_unsubmitted_pilot08': 3, 'original_unsubmitted_astra240': 0,
                'candidate04_inputs_only': 6, 'astra_cap_development60': 0}
    assert {k: v['affected_n'] for k, v in panels.items()} == expected
    evidence = [
        ('madhaviya-page506.jpg', 'https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha/mdhvscan/MDhVjpg/madhaviyahdhatuv00sayauoft_bw_0506.jpg', 452),
        ('kshiratarangini-page295.jpg', 'https://s3.us-east-2.wasabisys.com/jainqq-hq/90f27ddcd39ca7763a0e1158f597c3911e2fc0f0935340dd81b038f14a8aa7c6.jpg', 238),
        ('kshiratarangini-page296.jpg', 'https://s3.us-east-2.wasabisys.com/jainqq-hq/01332a2775dadcd644f33e20d2d7c2ca0decb265186a843d1c8d50f558980a96.jpg', 239),
    ]
    out = dict(created_at=datetime.now(timezone.utc).isoformat(),
        policy='oracle-policy-20', policy_sha256=sha(B / 'oracle-policy-20.json'),
        adapter_sha256=sha(ROOT / 'misc/vp_cartesian_task.py'),
        disposition='Parent adopted conservative unresolved-classical-scope hold; not a universal ungrammaticality or unanimous Vedic-only finding.',
        predicate=dict(exact_codes=sorted(CODES), coordinates='all', recipes='all', trace_condition=None),
        sources=[dict(local_file=n, sha256=sha(OUT / n), url=u, printed_page=p, visually_inspected=True) for n, u, p in evidence],
        corroborating_primary_text='https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌४१-५०',
        source_qualification='Madhaviya reports Parayana restricting spr/smr, and Svamin/Kashyapa all three. Kshiratarangini says chandasapraya; its editorial number correction does not remove praya. Kaumudi reports the restriction with ity ahuh. No contrary direct classical finite-use example was established in this bounded review.',
        prior_review='search-03.lexical-scope-scan.json already retained these as disputed/predominantly Vedic and avoided them as fresh hardness leads; the new primary scan supports a conservative unresolved-scope hold, not a stronger unanimity claim.',
        rule_1_3_57_caution='Nyasa names smr adhyane; the examples do not by themselves prove a separate exclusive cintayam condition or an engine bug for Svadi. The adopted entry-scope hold does not depend on a 1.3.57 trace.',
        controls=controls, input_effects=panels,
        historical_development_effects=read(OUT / 'historical-affected-counts.json'),
        original_panels_immutable=True, no_pilot08_answers_read=True, no_test_answers_read=True,
        no_paid_calls=True, no_shared_policy_edits=True)
    (OUT / 'review.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(input_effects={k: v['affected_n'] for k, v in panels.items()}, controls=len(controls), policy=out['policy']), indent=2))


if __name__ == '__main__':
    main()
