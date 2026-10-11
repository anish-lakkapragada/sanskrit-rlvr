#!/usr/bin/env python3
"""Source-first lexical audit for pilot02; never reads model answers."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT, HISTORY, load_entries, name, now, sha, write
from misc.vp_campaign_candidates import family
from misc.vp_cartesian_task import entry_scope_issue, make_task, oracle_issue

RUN_ID='pilot-preparation-02'
LEXICON='https://jainqq.org/booktext/Dhatupradip/004319'
DHATUPATHA='https://sa.wikisource.org/wiki/अष्टाध्यायी-धातुपाठः'
BASE='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
# Exact development readings checked before sampling, independent of correctness.
# Four entries with optional no-Nic branches are retained in the lexical audit
# but excluded from the focused 36-case mechanism probe.
AKUSMIYA_DEV={
 '10.0194':('daMsayate','direct_present_example','optional_branch'),
 '10.0197':('qepayate','direct_present_example','focused'),
 '10.0199':('mantrayate','direct_present_example','optional_branch'),
 '10.0201':('tarjayate','direct_present_example','focused'),
 '10.0202':('Bartsayate','direct_present_example_ocr_spacing_reviewed','focused'),
 '10.0213':('BrURayate','direct_present_example_meaning_gloss_varies','focused'),
 '10.0214':('SAWayate','direct_present_example','focused'),
 '10.0220':('kutsayate','direct_present_example_ocr_reviewed_against_dhatupatha','focused'),
 '10.0221':('trowayate','direct_present_example_ocr_reviewed_against_dhatupatha','focused'),
 '10.0223':('gAlayate','lexical_entry_plus_rules_3.1.25_7.2.116','focused'),
 '10.0227':('vaYcayate','direct_present_example','optional_branch'),
 '10.0230':('devayate','direct_present_example','optional_branch'),
 '10.0233':('mAnayate','direct_present_example_with_long_short_citation_editions','focused'),
 '10.0235':('yAvayate','direct_present_example','focused'),
}
UNVERIFIED_AKUSMIYA={'10.0205','10.0206','10.0222','10.0226'}
FOCUSED_CODES={c for c,(_,_,role) in AKUSMIYA_DEV.items() if role=='focused'}
# Positive ordinary Curadi controls with clear lexical readings. The matched
# coordinate controls are generated later, independently of model outcomes.
CURADI_CONTROL_CODES={'10.0001','10.0017','10.0034','10.0036','10.0088','10.0089',
 '10.0093','10.0101','10.0119','10.0134','10.0139','10.0145','10.0148','10.0150',
 '10.0168','10.0172','10.0177','10.0187','10.0189'}


def status(phase,message):
    s={'track':'four_d','run_id':RUN_ID,'updated_at':now(),'state':'running',
       'phase':phase,'message':message,'benchmark_ready':False}
    write(OUT/'status.json',s)
    with (OUT/'progress.md').open('a') as f:f.write(f"\n- {s['updated_at']}: {phase}: {message}\n")


def canonical_citation(e):
    # Accent removal defines the contrast pool only. Prompts preserve the full
    # dictionary citation, including accent and every it-marker.
    return e.dhatu.aupadeshika.replace('\\','').replace('^','')


def contrast_families(entries):
    g=defaultdict(list)
    for e in entries:
        if not entry_scope_issue(e):g[canonical_citation(e)].append(e)
    return {family(e) for es in g.values() if len({name(e.dhatu.gana) for e in es})>1 for e in es}


def main():
    status('Source-first lexical audit','Checking exact Akusmiya readings and class-specific forms before selecting new tuples.')
    entries=load_entries(); bycode={e.code:e for e in entries}
    splits=json.loads((HISTORY/'family-split.json').read_text())['families']
    checks=[]
    for c,(expected,level,role) in AKUSMIYA_DEV.items():
        e=bycode[c]
        t=make_task(e,'source_control',{'lakara':'Lat','prayoga':'Kartari','purusha':'Prathama','vacana':'Eka'})
        checks.append({'code':c,'citation':e.dhatu.aupadeshika,'artha':e.artha,
            'expected_source_form_slp1':expected,'vp_forms_slp1':t['gold_slp1'],
            'source_matches':expected in t['gold_slp1'],'evidence_level':level,
            'pilot_role':role,'sources':[LEXICON,DHATUPATHA]+([BASE+'7/7.2.116.htm'] if c=='10.0223' else []),
            'scope_issue':entry_scope_issue(e),'antargana':name(e.dhatu.antargana),
            'optional_branch_policy':'Full engine union is never narrowed. Optional no-Nic entries excluded from this focused probe.'})
    # Independently sourced class controls; expected forms precede derivation.
    examples=[
      ('10.0001','Lat','corayati','3.1.25'),
      ('04.0001','Lat','dIvyati','3.1.69'),
      ('04.0001','Lit','dideva','3.1.69'),
      ('04.0001','Lut','devitA','3.1.69'),
      ('04.0001','Lrt','devizyati','3.1.69'),
      ('04.0001','Lot','dIvyatu','3.1.69'),
      ('04.0001','Lan','adIvyat','3.1.69'),
      ('04.0001','VidhiLin','dIvyet','3.1.69'),
      ('04.0001','AshirLin','dIvyAt','3.1.69'),
      ('04.0001','Lun','adevIt','3.1.69'),
      ('04.0001','Lrn','adevizyat','3.1.69'),
      ('05.0001','Lat','sunoti','3.1.73'),
      ('08.0001','Lat','tanoti','3.1.79'),
      ('08.0002','Lat','sanoti','3.1.79'),
      ('08.0010','Lat','karoti','3.1.79'),
      ('02.0001','Lat','atti','2.4.72'),
      ('03.0001','Lat','juhoti','2.4.75'),
    ]
    class_checks=[]
    for code,la,expected,rule in examples:
        t=make_task(bycode[code],'source_control',{'lakara':la,'prayoga':'Kartari','purusha':'Prathama','vacana':'Eka'})
        class_checks.append({'code':code,'morphology':t['morphology'],
            'expected_source_form_slp1':expected,'vp_forms_slp1':t['gold_slp1'],
            'source_matches':expected in t['gold_slp1'],
            'source':BASE+rule.split('.')[0]+'/'+rule+'.htm'})
    contrasts=contrast_families(entries)
    counts={}
    for spl in ['development','test','rl_train']:
        unique={family(e):e for e in entries if not entry_scope_issue(e) and splits[family(e)]['split']==spl}
        ak={family(e):e for e in entries if not entry_scope_issue(e) and splits[family(e)]['split']==spl
            and name(e.dhatu.antargana)=='Akusmiya'}
        ak_reviewed={family(e) for e in entries if not entry_scope_issue(e) and splits[family(e)]['split']==spl
            and name(e.dhatu.antargana)=='Akusmiya' and e.code not in UNVERIFIED_AKUSMIYA}
        cross=[e for f,e in unique.items() if f in contrasts]
        counts[spl]={'akusmiya_all_families':len(ak),
            'akusmiya_excluding_unverified_readings':len(ak_reviewed),
            'cross_gana_citation_families':len(cross),
            'cross_gana_noncuradi_families':len([e for e in cross if name(e.dhatu.gana)!='Curadi']),
            'cross_gana_by_gana':dict(Counter(name(e.dhatu.gana) for e in cross))}
    scope_issues=[{'code':e.code,'issue':entry_scope_issue(e)} for e in entries if entry_scope_issue(e)]
    data={'created_at':now(),'run_id':RUN_ID,'generator_sha256':sha(__file__),
        'policy':'Source-first prospective audit; no model responses loaded by this script. Full dictionary citation/class/meaning remains in unchanged prompt.',
        'sources':[{'url':LEXICON,'edition':'Maitreya-raksita; edition published 1919; printed pages 137–139 (online pages 147–149)'},
                   {'url':DHATUPATHA,'section':'Curadi Akusmiya subgroup; lexical variants checked across both primary editions'}],
        'lexical_checks':checks,'class_source_examples':class_checks,
        'focused_akusmiya_development_codes':sorted(FOCUSED_CODES),
        'unverified_akusmiya_codes_excluded':sorted(UNVERIFIED_AKUSMIYA),
        'unverified_reading_explanation':'kila/pila not found in these editions; kuwa Chedane and kuwwa pratapane do not match the cited kuṭa variant. Absence here is not proof of ungrammaticality; exclude pending another primary reading.',
        'hidden_entry_scope_issues':scope_issues,
        'contrast_predicate':'Exact aupadeshika with only accent signs removed occurs in at least two ganas among scope-safe dictionary entries. No final question or gold comparison defines membership.',
        'split_family_supply':counts,
        'all_source_examples_passed':all(x['source_matches'] for x in checks+class_checks),
        'limitations':['Representative source controls are not independent certification of every paradigm member.',
            'Cross-gana lexical homography is a difficulty hypothesis, not an established effect.',
            'Dictionary census is a family upper bound; grammatical tuple capacity and shared oracle filters are checked separately.',
            'Optional no-Nic readings in four otherwise attested development roots are excluded from the focused probe to avoid an unsettled interpretation and preserve the intended mechanism.']}
    write(OUT/'pilot-02.lexical-audit.json',data)
    print(json.dumps({'sources_passed':sum(x['source_matches'] for x in checks+class_checks),'sources_total':len(checks+class_checks),
        'failed':[x for x in checks+class_checks if not x['source_matches']], 'supply':counts},ensure_ascii=False,indent=2))
    assert data['all_source_examples_passed']


if __name__=='__main__':main()
