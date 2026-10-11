"""Unpaid primary-source controls and input-only impact review."""
import json
from collections import Counter
from misc.vp_5d_candidate_nested_audit import B,A,traces
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_5d_prepare_05 import history
from misc.vp_5d_novelty_04 import walk
M=dict(lakara='Lat',prayoga='Kartari',purusha='Prathama',vacana='Eka')
def probe(code,ops,la='Lat'):
 ps=traces(code,ops,{**M,'lakara':la});return dict(code=code,operations=ops,morphology={**M,'lakara':la},gold_slp1=sorted({p['text'] for p in ps}),derivations=ps)
def affected(t):
 return t.get('dhatu',{}).get('code')=='01.1043' and t.get('derivation',{}).get('sanadi',[])[:2]==['yaN','Ric'] and '6.4.89' in t.get('campaign',{}).get('trace_rule_ids',[])
def main():
 ts=json.loads((B/'revision-01/tasks.json').read_text());cs=[probe('01.1043',ops,la) for ops in [['yaN'],['Ric'],['yaN','Ric'],['yaNluk','Ric']] for la in ['Lat','Lut','Lun']]
 bcs=[probe('06.0004',ops,la) for ops in [['yaN'],['yaNluk'],['yaNluk','Ric']] for la in ['Lat','Lut','Lrt']]
 _,_,hist=history();hits=[]
 for fp in hist['task_files']:
  for t in json.loads(open(fp['path']).read()):
   for row in walk(t):
    if affected(row):hits.append(dict(path=fp['path'],id=row.get('id'),code=row['dhatu']['code'],morphology=row.get('morphology')))
 artifact=dict(created_at=now(),status='Independent source/trace finding for parent verification; no shared policy mutation.',shared_generator_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),candidate_sha256=sha(B/'revision-01/tasks.json'),guh=dict(proposed_predicate="exact code01.1043 AND first two operations [yaN,Ric] AND trace6.4.89",qualification='Narrow conservative oracle-coverage quarantine proposed. No replacement gold or model-success relabel. The complete nested form is inferred from source conditions, not independently printed.',source_reason='Nyasa6.4.89 requires a context in which guṇa is possible. Ordinary yaN→Ric deletes ya by6.4.49+48, whose root-part deletion is the environment of1.1.4 prohibition; the installed trace nevertheless changes guh to gUh after Ric. The same long vowel in luk→Ric is not implicated because the independent prior luk was not caused by the later Ric. Preserve ordinary Ric and luk→Ric.',sources=[dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.89.htm',brief_excerpt='यत्र प्रत्यये गुणः सम्भवति तस्मिन्? कृतेऽकृत एव गुणे यथा स्यात्(), अन्यत्र मा भूदिति।',supports='Guṇa need not already have occurred, but must be possible; a bare u in the input alone is not proof of error.'),dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.1.4.htm',supports='Root-part deletion caused by the same ardhadhatuka prevents its guṇa/vṛddhi.'),dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.49.htm',supports='ya after a consonant is deleted before ardhadhatuka; printed bebhidita preserves the intensive vowel.'),dict(url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/2/2.4.74.htm',supports='Independent yaNluk occurs first; it differs from subsequent suffix-conditioned root-part deletion.')],controls=cs,candidate_hits=[dict(id=t['id'],morphology=t['morphology'],gold_slp1=t['gold_slp1']) for t in ts if affected(t)],historical_input_hits=hits),bhrasj_negative_control=dict(conclusion='Do not extend prcch/vrasc first-yaNluk hold to06.0004 on reduplication appearance alone.',source='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.47.htm',brief_excerpt='रुगादिरहितं बाभर्जिता बाभर्जिष्यतीत्यादि रूपं नैव सिध्येत्।',reading='Tattvabodhini rejects the proposed alternative analysis precisely because it would fail to produce the accepted rī-free intensive-luk futures. The installed bare-luk union contains bABarjitA and bABarjizyati, unlike the source contradictions for vrasc and prcch.',controls=bcs),no_model_answers_read=True,no_paid_calls=True,no_gold_changed=True,no_shared_policy_changed=True)
 assert 'bABarjitA' in next(x['gold_slp1'] for x in bcs if x['operations']==['yaNluk'] and x['morphology']['lakara']=='Lut')
 assert 'bABarjizyati' in next(x['gold_slp1'] for x in bcs if x['operations']==['yaNluk'] and x['morphology']['lakara']=='Lrt')
 atomic_json(A/'guh-and-bhrasj-controls.json',artifact)
 print(json.dumps(dict(guh_candidate_hits=artifact['guh']['candidate_hits'],historical_input_hits=hits,bhrasj_source_controls_pass=True),ensure_ascii=False,indent=2))
 status('source-audit','Saved the narrow guh guṇa-context concern and source-supported bhrasj negative controls. Brū is under independent review by the other worker; candidate revision 02 remains unpublished.')
if __name__=='__main__':main()
