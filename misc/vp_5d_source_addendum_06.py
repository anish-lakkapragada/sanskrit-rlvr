"""Outcome-independent source/accepted-alias review; development rows only."""
import json
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_cartesian_task import make_task,entry_scope_issue,oracle_issue
from misc import vp_campaign_candidates as old
from vidyut.lipi import Scheme,transliterate

def main():
 es={e.code:e for e in old.load_entries()};panels={}
 for num in ['01','02','03','04','05','06']:
  p=ROOT/f'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-{num}/results.json'
  rows=json.loads(p.read_text());hits=[]
  for i,r in enumerate(rows):
   t=r['task'];code=t['dhatu']['code'];which=[]
   if code=='01.0866' and any('x' in g or 'X' in g for g in t['gold_slp1']):which.append('vocalic_l_scorer_coverage')
   if code=='06.0012' and 'yaNluk' in t['derivation']['sanadi']:which.append('vrasc_luk_stem_source')
   if which:hits.append(dict(raw_index=i,id=t['id'],code=code,operations=t['derivation']['sanadi'],morphology=t['morphology'],concerns=which,trace_8_2_18='8.2.18' in t['campaign']['trace_rule_ids'],gold_slp1=t['gold_slp1'],gold_devanagari=t['gold_devanagari'],answer=r['answer'],correct=r['is_correct'],status=r['status'],existing_issue=entry_scope_issue(es[code]) or oracle_issue(t)))
  panels[num]={'source_sha256':sha(p),'rows':hits,'counts':dict(Counter((x['concerns'][0]+':'+str(x['correct'])+':'+x['status']) for x in hits))}
 controls=[]
 m=dict(lakara='Lat',prayoga='Kartari',purusha='Prathama',vacana='Eka')
 for ops in [['yaN'],['yaNluk'],['yaNluk','Ric']]:
  for voice in ['Kartari','Karmani']:
   t=make_task(es['06.0012'],'source_control',{**m,'prayoga':voice},'source_control',ops,prompt_version='cartesian-5d-v3-sanskrit')
   controls.append(dict(operations=ops,voice=voice,gold_slp1=t['gold_slp1'],trace_rules=t['campaign']['trace_rule_ids']))
 r=json.loads((ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-06/results.json').read_text())[384]
 artifact=dict(created_at=now(),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),scope='Development-only outcome-independent predicates; raw answers and gold untouched',
 vocalic_l=dict(proposed_predicate="dhatu.code == '01.0866' AND any('x' or 'X' in gold_slp1) AND trace8.2.18",reason='Canonical vocalic l uses U+0962 in these gold forms; the answer spells the same traditional vocalic l with la+virama+vocalic-r. Primary commentary itself uses the latter representation. The fixed SLP1 scorer distinguishes them, so this is scorer coverage, not a demonstrated grammatical model error.',source='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.18.htm',brief_excerpt='ऋकारस्य अप्येकदेशविकारद्वारेण लृकारः ... चिक्लृप्सति। क्लृप्तः।',answer=r['answer'],answer_slp1=transliterate(r['answer'],Scheme.Devanagari,Scheme.Slp1),answer_codepoints=[f'U+{ord(c):04X}' for c in r['answer']],gold=r['task']['gold_devanagari'],gold_codepoints=[[f'U+{ord(c):04X}' for c in g] for g in r['task']['gold_devanagari']],all_affected_rows_have_trace8_2_18=all(x['trace_8_2_18'] for p in panels.values() for x in p['rows'] if 'vocalic_l_scorer_coverage' in x['concerns']),preserved_control='Pilot06 row65 has kalp aorist gold without x/X and is not covered.'),
 vrasc=dict(proposed_predicate="dhatu.code == '06.0012' AND 'yaNluk' in derivation.sanadi",source='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.90.htm',brief_excerpt='रीगृत्वत इति वक्तव्यम्। ... वरीवृश्च्यते। वरीवृश्चीति।',primary_bare_luk_expected='varIvfScIti',primary_bare_luk_present_in_engine=any('varIvfScIti' in c['gold_slp1'] for c in controls if c['operations']==['yaNluk'] and c['voice']=='Kartari'),controls=controls,reason='The primary yaNluk example has samprasarana and rI augmentation, absent from VP bare yaNluk output. The derived passive stem in the paid panel inherits this mismatch. Quarantine source uncertainty without replacing gold by the model answer. The exact complete nested form is not independently printed here.',rejected_hypothesis='A blanket stip-designation claim that samprasarana cannot apply after yaNluk is contradicted by this explicit primary example.'),
 panels=panels,gold_changed=False,model_answers_relabelled=False,paid_calls=0)
 atomic_json(OUT/'pilot-06.source-addendum-01.json',artifact)
 print(json.dumps({k:v['counts'] for k,v in panels.items()},indent=2));status('Source and scorer coverage review','The600-question numerical screen passes provisionally. Source review found one vocalic-l spelling coverage issue and a vrasc yaNluk stem contradiction; outcome-independent predicates are quantified across all six panels. Astra04 is complete and current paired statistics are saved.')
if __name__=='__main__':main()
