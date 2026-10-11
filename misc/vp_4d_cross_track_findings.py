"""Write source-review findings from input/trace controls; no model answers or calls."""
import json,hashlib,datetime
from pathlib import Path
P=Path('benchmarks/parallel-search-20261006/four_d/cross-track-source-review-01')
a=json.loads((P/'lexical-san-controls.json').read_text())
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
base='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
def sutra(s):
 return base+s.split('.')[0]+'/'+s+'.htm'
B='https://sa.wikisource.org/wiki/बृहद्धातुरूपावलिः'
findings=[
 {'id':'aj_late_base_substitution','severity':'block candidate inputs pending coordinator source review','predicate':{'codes':['01.0262'],'sanadi_exact':['san'],'lakaras':['Lit','Lut','Lrt','AshirLin','Lun','Lrn']},
  'source_rules':['2.4.56','7.3.60'],
  'evidence':[{'url':sutra('2.4.56'),'work':'Kashika and Nyasa','claim':'The initial aj-to-vI substitution is optional in the consonant-initial ardhadhatuka environment. This licenses initial alternatives, not a second replacement inside a completed desiderative.'},{'url':B,'work':'Brhaddhaturupavali, aj entry89','quote':'अजिजिषति','claim':'The unsubstituted desiderative is explicitly printed. The neighboring vI-form is OCR-damaged; the aj control is clear.'}],
  'mechanical_defect':'A trace first chooses no substitution, forms a-ji-j-i-sa, then applies 2.4.56 to the residual lexical term before an outer nonpresent ending. It yields ajivayiz- and loses source-supported ajijiz-. AshirLin loses the aj alternative entirely.',
  'candidate_expected_inference':['ajijizizyasi','Ajijizizma'],
  'expected_note':'These finite forms are regular inflectional inferences from the directly sourced desiderative stem, not independently printed forms and not replacement gold.',
  'preserve_controls':{'Lat':['ajijizati','vivIzati'],'Lot':'ajijiza- and vivIza- both survive','Lan':'Ajijiza- and avivIza- both survive','VidhiLin':'ajijize- and vivIze- both survive'},
  'scope_note':'Exact single-san predicate only. Do not extend automatically to arbitrary nested recipes or ordinary four-dimensional aj inflection.'},
 {'id':'didhivevi_repeated_final_deletion','severity':'block candidate inputs pending coordinator source review','predicate':{'codes':['02.0071','02.0072'],'sanadi_exact':['san']},
  'source_rules':['1.1.6','7.4.53'],
  'evidence':[{'url':sutra('7.4.53'),'work':'Kashika, Nyasa and Balamanorama','quote':'ईकारस्य लोपः','claim':'Before y or i-vowels, the deletion is of the final I of dIdhI/vevI. Nyasa invokes alo antyasya; Balamanorama identifies the I explicitly.'},{'url':sutra('1.1.6'),'work':'Kashika and Nyasa','claim':'These exact lexical roots receive the guna/vrddhi prohibition; these are not the independent monosyllabic dI, dhI, ve or vI roots.'}],
  'mechanical_defect':'7.4.53 runs twice on the same residual lexical term. dIDI becomes dID, then dI (erroneously losing D); vevI becomes vev, then ve (erroneously losing v). Later vowel rules create didyiz- and vivayiz-. Bare desiderative and present controls are already affected.',
  'source_rule_stem_inference':['didIDiza','viveviza'],
  'expected_note':'Stem reconstructions follow one I deletion plus regular reduplication; no complete rare paradigm is claimed printed or proposed as edited gold.',
  'scope_note':'The separate classical-versus-Vedic scope dispute is unresolved and is not the basis for this hold. Preserve ordinary dictionary forms and unrelated uses of 7.4.53.'},
 {'id':'rdh_augmented_repeated_ii','severity':'block candidate inputs pending coordinator source review','predicate':{'codes':['04.0160'],'sanadi_exact':['san'],'lakaras':['Lan','Lun','Lrn']},
  'source_rules':['7.2.49','7.4.55','7.4.58'],
  'evidence':[{'url':sutra('7.4.55'),'work':'Kashika and Nyasa','quote':'ईर्त्सति','claim':'The no-it desiderative substitutes I for the original vocalic r and deletes the reduplicative syllable. The it alternative is ardidhisati.'},{'url':sutra('7.2.49'),'work':'Kashika and Nyasa','claim':'Both ardidhisati and irtsati are explicitly licensed for rdh.'},{'url':sutra('7.4.58'),'work':'Kashika','claim':'The reduplicative syllable disappears in these special desideratives.'}],
  'mechanical_defect':'The first7.4.55 application correctly forms Ir. After augment insertion, a second application forms IIr; augment sandhi and6.1.78 then produce AyIrts-. Controls show the defect for all three augmented tenses and correct Irts- in nonaugmented tenses.',
  'candidate_expected_inference':['ErtsizuH'],
  'expected_note':'Finite form inferred from directly sourced Irtsa plus the ordinary augment/aorist rules; not edited gold.',
  'preserve_controls':{'Lat':['Irtsati','ardiDizati'],'Lrt':['Irtsizyati','ardiDizizyati'],'Lit':'both uncorrupted stems','Lut':'both uncorrupted stems','AshirLin':'both uncorrupted stems'},
  'scope_note':'Exact single-san plus augmented-tense predicate. Do not exclude all rdh or all occurrences of7.4.55.'},
 {'id':'jagr_nonmonosyllabic_it_prohibition','severity':'block candidate inputs pending coordinator source review','predicate':{'codes':['02.0067'],'sanadi_exact':['san']},
  'source_rules':['7.2.12','7.3.85'],
  'evidence':[{'url':'https://kosha.sanskrit.today/word/sa/जागृ','work':'Madhaviya Dhatuvrtti, Adadi jAgr entry62, primary text transcribed by Kosha','quote':'जिजागरिषति','claim':'The primary commentary explicitly says the7.2.12 prohibition does not apply because ekac continues in force; jAgr is not monosyllabic. Citation is to the named primary text on an aggregator, not to its modern dictionary paraphrase.'},{'url':'https://jainqq.org/explore/004311/331/','work':'Pancagranthi Vyakaranam, printedp257','quote':'जिजागरिषति','claim':'Independently lists this form among set examples.'},{'url':sutra('7.3.85'),'work':'Kashika and Nyasa','claim':'jAgr has special guna outside the stated exceptions; normal san does not license the engine no-it, long-Ir stem.'}],
  'mechanical_defect':'The engine applies7.2.12 to jAgr, then kit status,6.4.16 and7.1.100, yielding jijAgIrza. The correct source-printed present stem is jijAgariza.',
  'candidate_expected_inference':['ajijAgarizIt'],
  'expected_note':'The exact candidate aorist is a regular inference from the printed desiderative stem; final t/d orthographic variants remain subject to the normal scorer.',
  'scope_note':'Exact single-san input. Do not exclude ordinary jAgr inflection or unrelated monosyllabic vowel-final roots.'}
]
def matches(t,p):
 return t['dhatu']['code'] in p['codes'] and t['derivation']['sanadi']==p['sanadi_exact'] and ('lakaras' not in p or t['morphology']['lakara'] in p['lakaras'])
for f in findings:
 ts=[x for x in a['actual_candidate_inputs'] if matches(x['task'],f['predicate'])]
 f['affected_candidate_count']=len(ts)
 f['affected_candidate_inputs']=[{k:x['task'][k] for k in ['id','dhatu','morphology','gold_slp1','gold_devanagari']} for x in ts]
 f['diagnostic_trace_events']=[]
 for x in ts:
  for v in x['vp_traces']:
   hist=v['history']; ev=[]
   for i,h in enumerate(hist):
    if h['rule'] in f['source_rules'] or (f['id']=='rdh_augmented_repeated_ii' and h['rule'] in ['6.4.72','6.1.90','6.1.78']):
     ev.append({'index':i,'before':hist[i-1]['result'] if i else None,**h})
   sig=json.dumps(ev,sort_keys=True)
   if not any(z['task_id']==x['task']['id'] and z['events']==ev for z in f['diagnostic_trace_events']):f['diagnostic_trace_events'].append({'task_id':x['task']['id'],'vp_output':v['text'],'events':ev})
out={'created_at':now,'kind':'unpaid input/source validity review','shared_policy_at_review':'oracle-policy-16','candidate_path':a['candidate_path'],'candidate_sha256':a['sha256'],'read_final_model_answers':False,'shared_policy_mutated':False,'status':'recommend coordinator review; no policy change made','findings':findings,'total_affected_candidate_inputs':sum(f['affected_candidate_count'] for f in findings)}
(P/'blockers.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('Blockers',len(findings),'affected',out['total_affected_candidate_inputs'])
