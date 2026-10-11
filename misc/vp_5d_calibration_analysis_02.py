"""Audit two clean development panels and a prospective finite recipe contrast."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_5d_pilot import OUT,EXCLUDED_RULES,atomic_json,now,sha
from misc.vp_cartesian_task import entry_scope_issue,oracle_issue,make_task
from vidyut.prakriya import Vyakarana,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana

RUN='calibration-analysis-02'
BASE='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
SOURCES={
 'no_redup':[BASE+'6/6.1.8.htm',BASE+'6/6.1.11.htm'],
 'guna_block':['https://sanskritdocuments.org/~sanskrit/learning_tools/sarvanisutrani/1.1.4.htm',BASE+'6/6.4.49.htm'],
 'guna':[BASE+'7/7.3.86.htm'],
 'mit':[BASE+'6/6.4.92.htm'],
 'svap':[BASE+'6/6.1.15.htm',BASE+'7/7.4.83.htm'],
 'lengthening':[BASE+'8/8.2.78.htm'],
 'vrddhi_block':[BASE+'1/1.1.57.htm',BASE+'6/6.4.49.htm'],
 'long_r':[BASE+'7/7.1.100.htm',BASE+'6/6.4.49.htm',BASE+'8/8.2.77.htm'],
 'nasal':[BASE+'7/7.4.85.htm'],
 'nic_loss':[BASE+'6/6.4.51.htm',BASE+'2/2.4.54.htm'],
}
REVIEWS={
 '01.0058':('extra_aorist_reduplication','no_redup','The existing intensive reduplication blocks a fresh causal-aorist reduplication; the model added an extra na.'),
 '04.0061':('unlicensed_guna_after_intensive_deletion','guna_block','The model strengthened Suc to Soc after the intensive-causal construction. Deletion under 6.4.49/48 does not license this guna; the passive retains Suc.'),
 '06.0005':('missing_intensive_luk_guna','guna','The intensive-luk periphrastic future takes the regular light-penultimate guna kzip to kzep. Unlike suffix-conditioned ya deletion, independent luk does not trigger the same blocking condition.'),
 '05.0031':('mit_shortening','mit','In this mit context, the causal layer has short cam rather than cAm. The accepted set already includes the optional nasal spellings.'),
 '02.0063':('samprasarana_scope','svap','Samprasarana affects the root portion svap to sup in the knit benedictive; the intensive reduplicative syllable remains sA. The model applied a different desiderative-style reduplicative vowel.'),
 '01.0022':('missing_root_cluster_lengthening','lengthening','The root vowel before its r-plus-consonant cluster lengthens under 8.2.78. The model retained short u.'),
 '06.0105':('unlicensed_guna_after_intensive_deletion','guna_block','The model strengthened CuT to CoT inside the intensive-causal passive. The source-conditioned guna block preserves u; the engine also records the regular cC consonant sequence.'),
 '07.0016':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The model introduced long A in the intensive-causal stem. The deleted intensive vowel retains the relevant blocking effect under 1.1.56, so the apparent new penultimate a is not an unrestricted target for causal vrddhi.'),
 '04.0151':('extra_aorist_reduplication','no_redup','The model added tu before the already intensive-reduplicated causal aorist. The anabhyasa restriction blocks that extra syllable.'),
 '07.0015':('unlicensed_guna_after_intensive_deletion','guna_block','The model strengthened piz to pez in the passive imperfect, although the intensive deletion does not license a new guna.'),
 '01.0920':('nested_long_r_order','long_r','The same explicitly reviewed long-r ordering as jF/JF applies: 7.1.100 gives ir, ya is deleted before causal nic, and 8.2.77 lacks a following consonant. Retain short i. This is rule composition, not a directly printed full triple passive form.'),
 '10.0180':('missing_root_cluster_lengthening','lengthening','The r-plus-consonant root cluster requires long U under 8.2.78; the model retained short u. This entry is not one of the four policy-03 lexical quarantines.'),
 '08.0007':('nasal_reduplicative_augment','nasal','The nasal-final root uses the nasal augment under 7.4.85, not an r augment. This family also appeared in pilot01; its repeated failure is not independent evidence of broad supply.'),
 '02.0007':('retained_causal_suffix_in_aorist','nic_loss','The causal suffix disappears before the anit aorist environment under 6.4.51. The model retained an extra aya segment; the key already accepts both documented cakz substitution branches.'),
}


def status(phase,message):
    stamp=now();atomic_json(OUT/'status.json',{'track':'five_d','run_id':RUN,'updated_at':stamp,
        'state':'running','phase':phase,'message':message,'benchmark_ready':False})
    with (OUT/'progress.md').open('a') as f:f.write(f'- {stamp}: {message}\n')


def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [center-half,center+half]


def summarize(rs):
    n=len(rs);complete=[r for r in rs if r['status']=='completed'];k=sum(bool(r['is_correct']) for r in complete)
    return {'requests':n,'completed':len(complete),'correct':k,'statuses':dict(Counter(r['status'] for r in rs)),
        'completed_accuracy':k/len(complete) if complete else None,'all_request_accuracy':k/n,
        'completed_wilson_95':wilson(k,len(complete)) if complete else None,
        'families':len({r['task']['campaign']['root_family'] for r in rs})}


def main():
    es={e.code:e for e in old.load_entries()};v=Vyakarana();bases={c:sorted({p.text for p in v.derive(e.dhatu)}) for c,e in es.items()}
    ids={t['id'] for t in json.loads((OUT/'pilot-01.audited-pair.tasks.json').read_text())}
    panels={};paths={}
    for name in ['01','02']:
        path=ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-{name}/results.json';paths[name]=str(path)
        rs=json.loads(path.read_text())
        panels[name]=[r for r in rs if name=='02' or r['task']['id'] in ids]
        assert all(r['task']['campaign']['split']=='development' for r in panels[name])
    groups={};registry={}
    for name,rs in dict(panels,pooled=panels['01']+panels['02']).items():
        cells=defaultdict(list)
        for r in rs:
            t=r['task'];m=t['morphology'];recipe=t['derivation']['recipe_id'];b=bases[t['dhatu']['code']][0]
            vowels=''.join(c for c in b if c in 'aAiIuUfFxXeEoO');tr=set(t['campaign']['trace_rule_ids'])
            keys=[('recipe',recipe),('lakara',m['lakara']),('voice',m['prayoga']),('gana',t['dhatu']['gana']),
                ('vowel',vowels),('recipe_lakara',recipe+'|'+m['lakara']),('recipe_voice',recipe+'|'+m['prayoga']),
                ('recipe_vowel',recipe+'|'+vowels),('consonant_cluster','contains_cluster' if any(b[i] not in 'aAiIuUfFxXeEoO' and b[i+1] not in 'aAiIuUfFxXeEoO' for i in range(len(b)-1)) else 'no_cluster')]
            for rule in ['6.4.92','6.4.49','7.4.85','7.4.86','7.4.91','7.1.100','8.2.78','7.4.83','7.3.86','3.1.48']:
                if rule in tr:keys.extend([('trace',rule),('recipe_trace',recipe+'|'+rule)])
            if recipe=='causative_of_intensive':
                keys.append(('causal_mechanism','aorist' if m['lakara']=='Lun' else 'other_lakaras'))
                keys.append(('causal_mechanism','short_i_u_or_long_r' if vowels in {'i','u','F'} else 'other_vowels'))
                keys.append(('causal_mechanism','ya_deletion' if '6.4.49' in tr else 'ya_retained'))
            for dim,label in keys:cells[dim+'::'+label].append(r)
        groups[name]={key:summarize(items) for key,items in cells.items()}
    reviews=[]
    for r in panels['02']:
        t=r['task'];e=es[t['dhatu']['code']]
        assert not entry_scope_issue(e) and not oracle_issue(t)
        if r['status']!='completed' or r['is_correct']:continue
        regenerated=make_task(e,'development',t['morphology'],recipe_id=t['derivation']['recipe_id'],sanadi=t['derivation']['sanadi'])
        assert regenerated['gold_slp1']==t['gold_slp1']
        category,key,note=REVIEWS[e.code]
        reviews.append({'id':t['id'],'code':e.code,'root':e.dhatu.aupadeshika,'recipe':t['derivation']['recipe_id'],
            'morphology':t['morphology'],'model_answer':r['answer'],'original_gold_slp1':t['gold_slp1'],
            'category':category,'review':note,'sources':SOURCES[key],
            'evidence_level':'Explicit rule applied to the full construction; not a direct printed example of every complete form.',
            'trace_rules':t['campaign']['trace_rule_ids'],'regeneration_passed':True,'gold_changed':False})
    assert len(reviews)==14
    analysis={'created_at':now(),'run_id':RUN,'panels':{name:summarize(rs) for name,rs in panels.items()},
        'pooled':summarize(panels['01']+panels['02']),'groups':groups,'reviews':reviews,
        'error_categories':dict(Counter(x['category'] for x in reviews)),
        'confirmed_new_oracle_errors':0,'raw_gold_or_results_changed':False,
        'posthoc_analysis_warning':'All conditional groups below are development analyses. Sparse cells and multiple comparisons make them hypotheses; no same-item failure is selected into a new panel.',
        'main_findings':['Intensive-luk rose from 15/19 to 55/59; pooled 70/78 is 89.74%, so the first approximately 79% estimate did not replicate.',
            'Intensive-causative is stable at 23/28 and 41/49, pooled 64/77 = 83.12%.',
            'Intensive-causal aorist is 0/3 then 2/5; outside aorist it is 23/25 then 39/44. This is a grammar-defined inherited-reduplication hypothesis with very small denominators.',
            'Stem-preservation errors recur across several other lakaras; coarse root-vowel filtering alone does not isolate a reliable 80% group.',
            'Repeated rare-root failure in Ghrin is specifically not a scalable sampling rationale.'],
        'input_sha256':{name:sha(Path(path)) for name,path in paths.items()},'script_sha256':sha(Path(__file__))}
    atomic_json(OUT/'calibration-analysis-02.json',analysis)

    source='https://sa.wikisource.org/wiki/शब्दकौस्तुभः/अध्यायः_१-पादः_१/आह्निकम्_८'
    diagnostics=[]
    definitions=[('04.0098',['yaNluk','Ric'],'Lun','Karmani','aSaMSAmi',source,'Direct Paninian Shabdakaustubha example expressly derived from intensive-luk plus nic.'),
        ('01.0001',['yaNluk','Ric'],'Lat','Kartari','boBAvayati','https://jainqq.org/explore/022970/141/','Direct Hemacandra-tradition corroboration only; not used alone to certify Paninian rule behavior.'),
        ('01.0001',['Ric','Ric'],'Lat','Kartari','BAvayati','https://jainqq.org/booktext/Dhatu_Parayan/034254','Repeated-causative comparison: length of chain does not imply a harder surface form.')]
    for code,ops,la,voice,expected,url,note in definitions:
        t=make_task(es[code],'source_control',{'lakara':la,'prayoga':voice,'purusha':'Prathama','vacana':'Eka'},recipe_id='source_control',sanadi=ops)
        diagnostics.append({'code':code,'sanadi':ops,'morphology':t['morphology'],'expected':expected,
            'engine_forms':t['gold_slp1'],'source_example_found':expected in t['gold_slp1'],'source':url,'note':note,
            'scope_issue':entry_scope_issue(es[code]),'oracle_issue':oracle_issue(t)})
    contrasts=[]
    for code in ['01.0001','02.0059','07.0002','01.1151']:
        forms={}
        for label,ops in [('causative_of_intensive',['yaN','Ric']),('causative_of_intensive_luk',['yaNluk','Ric'])]:
            t=make_task(es[code],'source_control',{'lakara':'Lat','prayoga':'Kartari','purusha':'Prathama','vacana':'Eka'},recipe_id=label,sanadi=ops)
            forms[label]=t['gold_slp1']
        contrasts.append({'code':code,'root':es[code].dhatu.aupadeshika,'forms':forms,
            'evidence_level':'Composition inference from independent luk versus suffix-conditioned deletion; source-controlled recipe, not direct full-form evidence for every root.'})
    controls={'created_at':now(),'recipe_candidate':{'id':'causative_of_intensive_luk','sanadi':['yaNluk','Ric']},
        'diagnostics':diagnostics,'all_expected_examples_found':all(x['source_example_found'] for x in diagnostics),
        'contrast_controls':contrasts,'primary_rule_sources':['https://sanskritdocuments.org/~sanskrit/learning_tools/sarvanisutrani/1.1.4.htm',BASE+'2/2.4.74.htm',BASE+'3/3.1.26.htm'],
        'mechanism':'Independent intensive-luk precedes nic; the later causal suffix does not cause that deletion. Contrast suffix-conditioned deletion of ordinary intensive ya and its blocked guna/vrddhi.',
        'prospective_filters':'Apply all shared policy-03 gates and conservatively extend the existing nested-rule quarantine to both intensive and intensive-luk causal recipes.',
        'repeated_causative_disposition':'Do not promote merely longer [Ric,Ric]; the source and engine often collapse it to the ordinary causal surface.',
        'limits':'The direct Paninian construction example plus rule analysis supports a fresh test. Broad recipe difficulty is unmeasured.'}
    atomic_json(OUT/'calibration-analysis-02.recipe-source-audit.json',controls)
    status('Disagreement audit complete','All fourteen new disagreements regenerate and have explicit rule reviews; no new oracle corrections found. A primary grammatical example supports intensive-luk followed by causative as a fresh stem-preservation contrast.')
    print(json.dumps({'panels':analysis['panels'],'categories':analysis['error_categories'],'new_recipe_source_controls_pass':controls['all_expected_examples_found']},indent=2))


if __name__=='__main__':main()
