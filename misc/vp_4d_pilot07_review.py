"""Unpaid, development-only pilot07 validity audit. Writes only four_d artifacts.

No provider, runner, ledger writer, held-out model answer, or shared-policy edit.
The proposed predicate is source-defined; task outcomes are counted afterwards.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Sanadi, Vacana
from misc.vp_cartesian_task import GRAMMAR, entries_by_code, entry_scope_issue, oracle_issue

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'benchmarks/parallel-search-20261006'
OUT = BASE / 'four_d/pilot-07-validity-review-01'
JOBS = ROOT / 'benchmarks/iterative-goal-20261006/jobs'
CODES = {'01.0504', '06.0055', '06.0056', '06.0057', '08.0006', '08.0007'}
PILOT_JOBS = ['opus-five-d-pilot-07-r1-a', 'opus-five-d-pilot-07-r1-b']
NEGATIVES = ['08.0005', '08.0001', '01.1137', '01.0514', '01.0805', '06.0077']
OPS = [[], ['san'], ['Ric'], ['yaN'], ['yaNluk'], ['yaN', 'Ric'], ['yaNluk', 'Ric']]


def read(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def usable(r):
    return r['status'] == 'completed' and r['answer'] is not None and not r['truncated']


def hit(t):
    return (t['dhatu']['code'] in CODES
            and t.get('derivation', {}).get('sanadi', [])[:1] in [['yaN'], ['yaNluk']]
            and '7.4.85' in t['campaign']['trace_rule_ids'])


def scope(t):
    return entry_scope_issue(entries_by_code()[t['dhatu']['code']]) or oracle_issue(t)


def metric(rs):
    u = [r for r in rs if usable(r)]
    c = sum(r['is_correct'] is True for r in rs)
    uc = sum(r['is_correct'] is True for r in u)
    return dict(n=len(rs), correct=c, usable=len(u), usable_wrong=len(u)-uc,
                nonusable=len(rs)-len(u), all_accuracy=c/len(rs) if rs else None,
                usable_accuracy=uc/len(u) if u else None,
                bounds=[uc/len(rs), (uc+len(rs)-len(u))/len(rs)] if rs else None)


def compact(r):
    t = r['task']
    return dict(id=t['id'], code=t['dhatu']['code'], citation=t['dhatu']['aupadeshika'],
                gana=t['dhatu']['gana'], recipe=t.get('derivation', {}).get('sanadi', []),
                morphology=t['morphology'], gold_slp1=t['gold_slp1'],
                answer=r['answer'], is_correct=r['is_correct'], usable=usable(r),
                prior_scope_issue=scope(t), proposed_hold=hit(t))


def main():
    OUT.mkdir(exist_ok=True)
    source_hashes = {}
    rows = []
    for job in PILOT_JOBS:
        p=JOBS/job/'results.json';source_hashes[str(p.relative_to(ROOT))]=digest(p)
        rs=read(p)
        assert len(rs)==1200 and all(r['task']['campaign']['split']=='development' for r in rs)
        rows.extend(rs)
    assert len({r['task_id'] for r in rows}) == 2400
    assert all(scope(r['task']) is None for r in rows), 'Snapshot no longer policy18; keep raw files and review change.'
    assert metric(rows) == dict(n=2400,correct=1854,usable=2381,usable_wrong=527,nonusable=19,
        all_accuracy=1854/2400,usable_accuracy=1854/2381,bounds=[1854/2400,1873/2400])

    # Exhaustive lexical inventory is input-only and independent of pilot outcomes.
    inventory=[]
    for code,e in entries_by_code().items():
        bases=sorted({p.text for p in GRAMMAR.derive(e.dhatu)})
        if any('f' in b and b.endswith(tuple('mMnNYR')) for b in bases):
            inventory.append(dict(code=code,citation=e.dhatu.aupadeshika,gana=e.dhatu.gana.name,
                                  meaning=e.artha,bases=bases,entry_scope_issue=entry_scope_issue(e)))
    assert {x['code'] for x in inventory} == CODES | {'08.0005'}
    controls=[]
    for code in sorted(CODES)+NEGATIVES:
        e=entries_by_code()[code]
        for ops in OPS:
            d=e.dhatu.with_sanadi([getattr(Sanadi, op) for op in ops])
            ps=GRAMMAR.derive(Pada.Tinanta(dhatu=d,lakara=Lakara.Lat,
                prayoga=Prayoga.Kartari,purusha=Purusha.Prathama,vacana=Vacana.Eka))
            rs=sorted({h.code for p in ps for h in p.history})
            controls.append(dict(code=code,citation=e.dhatu.aupadeshika,ops=ops,
                coordinates={'lakara':'Lat','prayoga':'Kartari','purusha':'Prathama','vacana':'Eka'},
                forms=sorted({p.text for p in ps}),rules=rs,
                passes_proposed_hold=(code in CODES and ops[:1] in [['yaN'],['yaNluk']] and '7.4.85' in rs),
                traces=[dict(form=p.text,history=[dict(rule=h.code,result=h.result) for h in p.history]) for p in ps]))
    # All six show the mismatch in both intensive kinds and both nested recipes;
    # ordinary, san and Ric are outside this hold, as are independent negatives.
    assert sum(c['passes_proposed_hold'] for c in controls)==24
    assert all(not c['passes_proposed_hold'] for c in controls if c['ops'] in [[],['san'],['Ric']])
    write('rnasal-controls.json',dict(inventory=inventory,controls=controls,
        scope='Lat controls establish inner-stem discrepancy and recipe propagation, not a guessed complete replacement paradigm.',
        directly_printed_single_yan={'01.0504':'jarIGfRRyate','08.0006':'tarItfRyate','08.0007':'jarIGfRyate'},
        rule_inference_codes=['06.0055','06.0056','06.0057']))

    summary=read(BASE/'development-results.json')
    impacts={}
    for job in list(summary['experiments'])+['astra-five-d-cap-development-01']:
        p=JOBS/job/'results.json'
        if not p.exists():continue
        rs=read(p)
        # Only these named completed development panels are read; no release answers.
        assert all(r['task']['campaign']['split']=='development' for r in rs)
        affected=[r for r in rs if hit(r['task'])]
        eligible=[r for r in rs if scope(r['task']) is None]
        added=[r for r in eligible if hit(r['task'])]
        impacts[job]=dict(raw_affected=metric(affected),newly_affected=metric(added),
                         codes=dict(Counter(r['task']['dhatu']['code'] for r in affected)),
                         currently_eligible=metric(eligible),prospective_retained=metric([r for r in eligible if not hit(r['task'])]),
                         affected_rows=[compact(r) for r in affected],results_sha256=digest(p))
    input_impacts={}
    input_paths=[BASE/'five_d/candidate-4800/revision-04/tasks.json', BASE/'five_d/astra-cap-development-01.tasks.json']
    for p in input_paths:
        ts=read(p); selected=[t for t in ts if hit(t)]
        input_impacts[str(p.relative_to(ROOT))]=dict(n=len(ts),affected=len(selected),
            by_code=dict(Counter(t['dhatu']['code'] for t in selected)),ids=[t['id'] for t in selected],sha256=digest(p),
            candidate_model_answers_read=False)
    write('rnasal-hold-proposal.json',dict(
        status='Source-backed prospective proposal; coordinator alone owns shared policy decisions.',
        predicate=dict(codes=sorted(CODES),first_operation_in=['yaN','yaNluk'],required_trace_rule='7.4.85'),
        rationale='Direct printed intensive controls use rI augmentation; 7.4.90 and its rtvat extension require rI-family augmentation on these r-bearing bases. VP instead takes 7.4.85 nasal augmentation, which propagates through added Ric. Quarantine the uncertified intensive branch rather than guessing replacement gold.',
        preserves=['all ordinary 4D','single san','single Ric','other nasal-final roots','other r-bearing roots without this nasal-augment branch','08.0005 vowel-initial rnu'],
        source_tiers=dict(direct_printed_controls=['01.0504','08.0006','08.0007'],explicit_rule_inference=['06.0055','06.0056','06.0057']),
        development_impacts=impacts,input_impacts=input_impacts,
        pilot07_raw=metric(rows),pilot07_newly_affected=metric([r for r in rows if hit(r['task'])]),
        pilot07_prospective_retained=metric([r for r in rows if not hit(r['task'])])))

    unusable=[]
    for r in rows:
        if usable(r):continue
        msg=r['raw_batch_result'].get('result',{}).get('message',{})
        item=compact(r)
        item.update(status=r['status'],truncated=r['truncated'],stop_reason=r['stop_reason'],
                    refusals=r['refusals'],output_text=r['output_text'],usage=msg.get('usage',{}),
                    response_block_types=[c.get('type') for c in msg.get('content',[])])
        same_family=[x for x in rows if x['task']['campaign']['root_family']==r['task']['campaign']['root_family'] and x['task_id']!=r['task_id']]
        item['same_family_other_rows']=dict(metric=metric(same_family),ids=[x['task_id'] for x in same_family])
        item['disposition']=('Retain raw parser failure; multiple answer tags include malformed final alternatives. No retry or answer salvage.' if r['status']=='completed' and not r['truncated'] else
            'Retain truncation as nonusable; no replacement or retry proposed.' if r['truncated'] else
            'Retain refusal as nonusable; provider supplies no visible refusal explanation, so no causal/category attribution.')
        unusable.append(item)
    assert Counter(x['status'] for x in unusable)=={'refused':16,'incomplete':2,'completed':1}
    assert sum(x['truncated'] for x in unusable)==2
    write('nonusable.json',dict(n=19,refusals=16,truncated=2,unparsed_completed=1,items=unusable,
        explanation='No response is removed for difficulty or assigned a linguistic scope exclusion by noncompletion. Blank visible refusal outputs do not establish a cyber-safety explanation. The five Self refusals are a lexical cluster of missingness, not evidence of invalid Sanskrit.'))

    equivalent=[]; mechanical=[]
    for r in rows:
        if not usable(r) or r['is_correct']:continue
        ans=transliterate(r['answer'],Scheme.Devanagari,Scheme.Slp1)
        if ans in r['task']['gold_slp1']:equivalent.append(r['task_id'])
        # Mechanical screen only: removing a short near-initial segment matches gold.
        # Exact examples still require independent grammatical interpretation.
        if r['task']['morphology']['lakara']=='Lun' and r['task'].get('derivation',{}).get('sanadi',[])[:1] in [['yaN'],['yaNluk']]:
            matches=[]
            for i in range(1,min(5,len(ans))):
                for n in range(1,5):
                    if ans[:i]+ans[i+n:] in r['task']['gold_slp1']:
                        matches.append(dict(index=i,removed=ans[i:i+n],gold=ans[:i]+ans[i+n:]))
            if matches:mechanical.append(dict(**compact(r),answer_slp1=ans,deletion_matches=matches))
    rules85=[r for r in rows if '7.4.85' in r['task']['campaign']['trace_rule_ids']]
    codes85=sorted({r['task']['dhatu']['code'] for r in rules85})
    pattern=dict(usable_wrong=527,transliteration_equivalent_false_negatives=equivalent,
                 short_near_initial_deletion_screen=dict(n=len(mechanical),items=mechanical,
                    limits='Descriptive string relation, not proof that every match is extra reduplication. No score or scope change.'),
                 nasal_rule_all_outcome_controls={c:metric([r for r in rules85 if r['task']['dhatu']['code']==c]) for c in codes85},
                 reviewed_families={c:dict(metric=metric([r for r in rows if r['task']['dhatu']['code']==c]),rows=[compact(r) for r in rows if r['task']['dhatu']['code']==c]) for c in ['01.0105','04.0020','06.0077','05.0018','01.0623']})
    write('pattern-groups.json',pattern)
    primary=[
       dict(url='https://jainqq.org/explore/004319/46',local='dhatupradipa-page46.jpg',printed_page='36',role='Direct ghṛṇi intensive jarīghṛṇṇyate.'),
       dict(url='https://jainqq.org/explore/004319/132',local='dhatupradipa-page132.jpg',printed_page='122',role='Direct tṛṇu and ghṛṇu intensives tarītṛṇyate / jarīghṛṇyate.'),
       dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.90.htm',role='Kashika + Nyasa: ṛ-upadha intensive augment and explicit extension to ṛ-bearing bases.'),
       dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.85.htm',role='Ordinary nasal augment controls; does not negate the specific rI rule.'),
       dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.1.11.htm',role='CaN reduplication inherits anabhyasa; no second reduplication on an already reduplicated intensive base.'),
       dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.1.8.htm',role='Anabhyasa restriction context.'),
       dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.1.64.htm',role='Explicit ṣvaṣk exception; ordinary initial ṣ is source-valid for 01.0105.'),
       dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.1.4.htm',role='Intensive-lopa guṇa control, already reviewed before pilot07.'),
    ]
    for s in primary:
        if s.get('local'):s['sha256']=digest(OUT/s['local'])
    write('review.json',dict(created_at=datetime.now(timezone.utc).isoformat(),
        scope='Bounded development validity triage; no paid calls, shared edits, candidate outcomes, retries, or membership changes.',
        baseline_policy='oracle-policy-18',baseline_scope_code_sha256=digest(ROOT/'misc/vp_cartesian_task.py'),
        raw=metric(rows),source_hashes=source_hashes,primary_sources=primary,
        proposals=['Only new proposed hold: explicit six-code initial-intensive + trace7.4.85 predicate.'],
        statistical_outcome='Even if the proposed hold is adopted, full07 remains below the 79–81% all-request advance target. Scope validation is independent of that target.',
        limitations=['Not a complete independent certification of every generated form.','Rule inference extends the three direct printed lexical controls to the other three explicit ṛ-upadha entries.','Completed-response accuracy conditions on missing outputs; the 19 nonusable outcomes stay reported.','The string screen is descriptive and does not select future benchmark questions.']))
    print(json.dumps(dict(raw=metric(rows),affected=metric([r for r in rows if hit(r['task'])]),
                         prospective=metric([r for r in rows if not hit(r['task'])]),
                         mechanical_screen=len(mechanical),controls=len(controls)),indent=2))


if __name__=='__main__':main()
