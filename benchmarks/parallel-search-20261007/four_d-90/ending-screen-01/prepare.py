"""Unpaid input-only preparation of the previously selected 96-family witness.

Reads no response/result files. Writes only beside this file; never registers jobs.
"""
import copy
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from vidyut.prakriya import DhatuPada
from misc.vp_cartesian_task import (COORDINATES, GRAMMAR, Pada, Lakara, Prayoga,
    Purusha, Vacana, entries_by_code, entry_scope_issue, oracle_issue, make_task,
    validate_task)
from misc.vp_campaign_candidates import family, name
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_4d_coverage05 import LOCAL, SPECIAL_IT
from misc.oai_batch_eval import normalize
from finetune.prompts import slp1_to_devanagari

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def save(n, v):
    (OUT/n).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')

RULES = {
    'future_ending_lopa': {'7.4.50'},
    'secondary_plural_cluster': {'8.2.23', '8.4.37'},
    'ling_plural_jus': {'3.4.108'},
    'sigmatic_aprkta_repair': {'7.3.96', '8.2.28'},
}
ALL_RULES = set.union(*RULES.values())
split_path = ROOT/'benchmarks/creation-campaign-20261006/family-split.json'
splits = read(split_path)['families']
es = entries_by_code()
witness_path = BASE/'broader-hypothesis-witness.json'
witness = read(witness_path)['metadata']
assert len(witness) == len({r['family'] for r in witness}) == 96

def derive(e, m, pada=None):
    args = dict(dhatu=e.dhatu, lakara=getattr(Lakara,m['lakara']),
        prayoga=getattr(Prayoga,m['prayoga']), purusha=getattr(Purusha,m['purusha']),
        vacana=getattr(Vacana,m['vacana']))
    if pada is not None:
        args['dhatu_pada'] = pada
    return GRAMMAR.derive(Pada.Tinanta(**args))

def events(p, rules=ALL_RULES):
    return [dict(rule=h.code, before=list(p.history[i-1].result) if i else [],
                 after=list(h.result)) for i,h in enumerate(p.history)
            if name(h.source)=='Ashtadhyayi' and h.code in rules]

def check_event(x):
    b,a,r = x['before'],x['after'],x['rule']
    if r == '7.4.50':
        assert len(a)==len(b)
        changed=[i for i in range(len(a)) if a[i]!=b[i]]
        assert len(changed)==1
        i=changed[0]
        assert b[i]=='tAs' and a[i]=='tA'
        assert ''.join(b[i+1:]).startswith('s')
    elif r == '8.2.23':
        assert ''.join(b).endswith('nt') and ''.join(a)==''.join(b)[:-1]
    elif r == '8.4.37':
        assert a==b and ''.join(a).endswith('n')
    elif r == '3.4.108':
        assert b[-1]=='Ji' and a[-1]=='jus' and b[:-1]==a[:-1]
    elif r == '7.3.96':
        assert b[-2]=='s' and b[-1] in {'t','s'}
        assert a==b[:-1]+['Iw',b[-1]]
    elif r == '8.2.28':
        assert len(a)==len(b)
        changed=[i for i in range(len(a)) if a[i]!=b[i]]
        assert len(changed)==1
        i=changed[0]
        assert b[i-1:i+2]==['i','s','I'] and a[i]==''

history_paths=[ROOT/'benchmarks/full-tasks.json']
for campaign in ['creation-campaign-20261006','iterative-goal-20261006']:
    history_paths += sorted((ROOT/'benchmarks'/campaign/'jobs').glob('*/tasks.json'))
exposed=set()
for path in history_paths:
    for top in read(path):
        for t in top.get('forms',[top]):
            if not isinstance(t,dict) or 'dhatu' not in t or len(t.get('morphology',{}))!=4:
                continue
            if any(t.get('derivation',{}).get(k) for k in ['sanadi','prefixes']):
                continue
            if any(o.get(k) for o in [t,t['dhatu'],t['morphology']]
                   for k in ['pada','dhatu_pada','prefixes','sanadi']):
                continue
            d=t['dhatu'];m=t['morphology']
            exposed.add((str(d.get('aupadeshika',d.get('upadesha','UNKNOWN')))+'|'+str(d.get('gana')),
                         *(m.get(k) for k in ['lakara','prayoga','purusha','vacana'])))

tasks=[]; audits=[]; aliases=[]
for r in witness:
    e=es[r['code']];m={k:r[k] for k in ['lakara','prayoga','purusha','vacana']}
    assert splits[family(e)]['split']=='development' and family(e)==r['family']
    assert not entry_scope_issue(e) and e.code not in LOCAL
    assert not(name(e.dhatu.gana)=='Curadi' and e.dhatu.aupadeshika.endswith('a'))
    t=make_task(e,'development',m,prompt_version='cartesian-4d-v1')
    assert t and t['id']==r['id'] and not oracle_issue(t)
    assert not(e.code=='10.0412' and m['lakara']=='Lun')
    assert not any(re.search('[aAiIuUfFxXeEoO]rC',g) for g in t['gold_slp1'])
    rules=set(t['campaign']['trace_rule_ids'])
    assert not rules&{'1.2.1','8.3.78','8.3.79'}
    assert not(name(e.dhatu.gana)!='Curadi' and m['lakara'] in ['Lut','Lrt','Lrn'] and rules&SPECIAL_IT)
    ps=derive(e,m)
    pa={name(dp):sorted({p.text for p in derive(e,m,dp)}) for dp in DhatuPada.choices()}
    assert sorted(set.union(*(set(v) for v in pa.values())))==t['gold_slp1']
    assert len(ps)==r['path_count'] and len(t['gold_slp1'])==r['gold_variants']
    pe=[]
    for p in ps:
        ev=events(p,RULES[r['cell']])
        assert RULES[r['cell']]<={x['rule'] for x in ev}
        for x in ev:check_event(x)
        pe.append(dict(gold_slp1=p.text,events=ev))
    k=(r['family'],*(m[x] for x in ['lakara','prayoga','purusha','vacana']))
    assert k not in exposed
    t['campaign']['sampling_cell']={'label':r['cell'],'require_rules_all':sorted(RULES[r['cell']])}
    validate_task(t,e,'development')
    prompt=render(t)
    scrub=copy.deepcopy(t);scrub['gold_slp1']=['PRIVATE_CANARY'];scrub['gold_devanagari']=['PRIVATE_CANARY'];scrub['campaign']={}
    assert render(scrub)==prompt and 'PRIVATE_CANARY' not in prompt
    assert hashlib.sha256(prompt.encode()).hexdigest()==t['campaign']['prompt_sha256']
    assert set(t['morphology'])==COORDINATES and 'derivation' not in t
    tasks.append(t)
    audits.append(dict(id=t['id'],code=e.code,family=family(e),cell=r['cell'],
        paths=pe,explicit_pada_unions=pa,novel_family_coordinate=True))
    # Only final dental stops are included until the independent reviewer resolves n.
    pairs=[]
    for g in t['gold_slp1']:
        if g.endswith(('t','d')):
            alias=g+g[-1]
            assert alias not in t['gold_slp1']
            gd,ad=map(slp1_to_devanagari,[g,alias])
            assert normalize(ad) not in {normalize(v) for v in t['gold_devanagari']}
            pairs.append(dict(canonical_slp1=g,canonical_devanagari=gd,
                alias_slp1=alias,alias_devanagari=ad,
                applicability='At pause, optional final yar doubling; final dental stop after long I here.',
                evidence_rules=['8.4.47','8.4.56']))
    aliases.append(dict(task_id=t['id'],canonical_gold_slp1=t['gold_slp1'],
        canonical_gold_devanagari=t['gold_devanagari'],accepted_final_gemination_aliases=pairs,
        unresolved_final_n_review=any(g.endswith('n') for g in t['gold_slp1'])))

assert len({t['id'] for t in tasks})==96
assert Counter(r['cell'] for r in witness)=={c:24 for c in RULES}
save('proposedtasks.json',tasks)
save('task-path-audit.json',audits)
save('accepted-final-gemination-aliases.json',dict(
    state='Final dental-stop aliases source-supported; final n review pending',
    canonical_gold_unchanged=True, canonical_and_alias_scores_must_both_be_reported=True,
    general_gemination_normalizer=False, records=aliases))

specs=[
 ('future_positive','08.0010','Lut','Madhyama','Eka',{'7.4.50'},set(),['kartAsi','kartAse']),
 ('future_non_s_initial_ending','08.0010','Lut','Madhyama','Dvi',set(),{'7.4.50'},[]),
 ('secondary_positive','01.0127','Lrn','Prathama','Bahu',{'8.2.23','8.4.37'},set(),[]),
 ('primary_plural_negative','01.0127','Lrt','Prathama','Bahu',set(),{'8.2.23','8.4.37'},[]),
 ('ling_printed_positive','01.1151','VidhiLin','Prathama','Bahu',{'3.4.108'},set(),['paceyuH']),
 ('ling_benedictive_scope','01.1151','AshirLin','Prathama','Bahu',{'3.4.108'},set(),[]),
 ('non_ling_plural_negative','01.1151','Lat','Prathama','Bahu',set(),{'3.4.108'},[]),
 ('it_it_printed_positive','09.0016','Lun','Prathama','Eka',{'7.3.96','8.2.28'},set(),['alAvIt']),
 ('non_aprkta_negative','09.0016','Lun','Prathama','Dvi',set(),{'7.3.96','8.2.28'},['alAvizwAm']),
 ('no_initial_it_negative','08.0010','Lun','Prathama','Eka',{'7.3.96'},{'8.2.28'},['akArzIt']),
 ('extant_as_positive','02.0060','Lan','Prathama','Eka',{'7.3.96'},{'8.2.28'},['AsIt']),
 ('as_substitution_sic_luk_negative','02.0060','Lun','Prathama','Eka',set(),{'7.3.96','8.2.28'},['aBUt']),
 ('dev_printed_positive','04.0001','Lun','Prathama','Eka',{'7.3.96','8.2.28'},set(),['adevIt']),
]
controls=[]
for label,code,la,pu,va,yes,no,printed in specs:
    e=es[code];m=dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va)
    actual_split=splits[family(e)]['split']
    t=make_task(e,actual_split,m)
    assert t and not oracle_issue(t)
    rules=set(t['campaign']['trace_rule_ids'])
    assert yes<=rules and not no&rules and set(printed)<=set(t['gold_slp1'])
    controls.append(dict(label=label,task=t,printed_source_forms_slp1=printed,
        control_scope='Input-only source control; no model answer, exposure or difficulty claim.',
        expected_present=sorted(yes),expected_absent=sorted(no),
        paths=[dict(gold_slp1=p.text,events=events(p)) for p in derive(e,m)]))
save('primary-source-controls.json',controls)

audit=dict(created_at=datetime.now(timezone.utc).isoformat(),n=96,families=96,
    class_counts=dict(Counter(r['gana'] for r in witness)),
    tense_counts=dict(Counter(r['lakara'] for r in witness)),
    person_counts=dict(Counter(r['purusha'] for r in witness)),
    number_counts=dict(Counter(r['vacana'] for r in witness)),
    cell_counts=dict(Counter(r['cell'] for r in witness)),
    all_path_count=sum(len(a['paths']) for a in audits),
    all_path_local_condition_checks=True,full_explicit_pada_union_checks=96,
    regeneration_shared_validator=96,public_prompt_gold_independence_checks=96,
    history_input_file_count=len(history_paths),history_normalized_keys=len(exposed),
    novelty_overlaps=0,primary_source_controls=len(controls),
    final_stop_alias_task_count=sum(bool(x['accepted_final_gemination_aliases']) for x in aliases),
    final_stop_alias_count=sum(len(x['accepted_final_gemination_aliases']) for x in aliases),
    final_n_pending_task_count=sum(x['unresolved_final_n_review'] for x in aliases),
    heldout_answers_read=False,result_files_read=[],provider_calls=0,
    prior_raw_and_shared_files_unchanged=True,
    input_provenance={str(p.relative_to(ROOT)):sha(p) for p in history_paths},
    fingerprints={str(p.relative_to(ROOT)):sha(p) for p in [witness_path,split_path,
       ROOT/'misc/vp_cartesian_task.py',ROOT/'misc/vp_cartesian_prompt_v1.py',
       ROOT/'misc/vp_4d_coverage05.py',ROOT/'misc/oai_batch_eval.py',
       ROOT/'benchmarks/parallel-search-20261006/oracle-policy-21.json',
       OUT/'prepare.py',OUT/'proposedtasks.json',OUT/'task-path-audit.json',
       OUT/'primary-source-controls.json',OUT/'accepted-final-gemination-aliases.json']})
save('audit.json',audit)
print(json.dumps({k:v for k,v in audit.items() if k not in ['input_provenance','fingerprints']},indent=2))
