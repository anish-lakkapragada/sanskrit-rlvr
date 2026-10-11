"""Independent, additive verification of the parent's215 Curadi source dispositions."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
from vidyut.lipi import Scheme,transliterate

HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'pyproject.toml').exists())
BASE=HERE.parent.parent.parent
PACK=BASE/'final1800-source-pack'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent_path=HERE/'OpenAI-curadi-review.json'
parent=json.loads(parent_path.read_text())
assert sha(parent_path)=='ee204ef7b1ea54d664384771c4af15881f3eee8b3339a6b128d73b74ac308810'
queue_path=HERE.parent/'independent-review/completed-review/OpenAI-source-adjudication-queue.json'
queue=json.loads(queue_path.read_text())
curadi={q['task_id']:q for q in queue if q['task']['dhatu']['gana']=='Curadi'}
records=parent['records']
assert len(curadi)==len(records)==215 and set(curadi)=={r['task_id'] for r in records}
assert sha(queue_path)==parent['queue_sha256']
for p,h in parent['source_dependencies'].items():assert sha(ROOT/p)==h,p
adopt=json.loads((PACK/'source-adjudication-adoption-02.json').read_text())
puk={r['task_id']:r['additional_forms_devanagari'] for r in adopt['accepted_additions']}
opus={r['task_id']:r for r in json.loads((HERE/'Anthropic-review.json').read_text())['rows']}

stem={'Cada':('CAd','Cad'),'laja':('lAj','laj'),'kuha':('koh','kuh'),'paWa':('pAW','paW'),
      'pada':('pAd','pad'),'gada':('gAd','gad'),'caha':('cAh','cah'),'raha':('rAh','rah'),
      'svara':('svAr','svar'),'vraRa':('vrAR','vraR')}
nasal={'anka':('AYcik','AYcak'),'anga':('AYjig','AYjag'),'anDa':('AndiD','AndaD'),'ansa':('AMsis','AMsas')}
groups={
 'literal_a_stem_strengthening':{
   'conclusion':'rejected','rules':['3.1.25','6.4.48','7.2.116','7.3.86'],
   'basis':'Exact literal-a entries and kathadi final-a deletion/retained-position explanation; first-vowel strengthening is not licensed. Printed or previously source-audited short stems for Cada,laja,kuha,pada,gada,caha,raha,svara,vraRa; paTha short finite stem is explicit general-rule inference from the printed aspirated entry.',
   'caveat':'Does not turn diagnostic stem replacement into acceptance normalization. Some answers additionally use a wrong pada.'},
 'intrinsic_middle_ending_mismatch':{
   'conclusion':'rejected','rules':['3.4.78','3.4.102','1.3.63'],
   'basis':'Independently re-viewed SK1938 scan241 printed237: padadi through garva heading is Atmanepada, with padayate and kuhayate. Kartari is compatible with Atmanepada and does not authorize a free para ending.',
   'caveat':'The kṛ auxiliary specifically follows main-entry pada. Do not reject valid as/bhu alternatives, nor equate every -etām with a middle optative.'},
 'adanta_aorist_unlicensed_i_reduplication':{
   'conclusion':'rejected','rules':['3.1.48','6.4.48','7.4.93'],
   'basis':'Kashika7.4.93 explicitly excludes aglopin stems, with acakathat control. Printed andha/anka/anga representatives retain the source a in their reduplication. Ansa dental-s entry follows the same general rule.',
   'caveat':'A complete general-rule inference is used for the selected endings; no printed attestation of every selected paradigm cell is claimed.'},
 'mixed_intrinsic_nic_and_no_nic_branches':{
   'conclusion':'rejected','rules':['3.1.48','3.1.43','3.1.44'],
   'basis':'Independently viewed SK237 includes garva in the middle group, prints garvayate, then allows nic optionally. With nic its caN stem ajagarv- takes middle endings; the no-nic para branch uses the sigmatic aorist. These cannot be combined into ajagarv- plus para endings.',
   'caveat':'The entire no-nic paradigm is not independently certified; the branch compatibility contradiction suffices for these five submitted forms.'},
 'adanta_aorist_reversed_vowel_quantities':{
   'conclusion':'rejected','rules':['7.4.2','7.4.93','7.4.94'],
   'basis':'Independently viewed SK237 directly prints ababhamat(with long ā), ajugomat and atitirat(with long ī in the second root syllable). Ag-lopa blocks the ordinary shortening/san-like long-reduplication treatment. All four answers use the reversed quantity pattern.',
   'caveat':'Printed3sg controls plus general tense/person endings; not every final form printed.'},
}
checked=[]
for r in records:
 q=curadi[r['task_id']];t=q['task']
 assert r['index']==q['index'] and r['answer']==q['answer']
 assert r['dhatu']==t['dhatu'] and r['morphology']==t['morphology']
 assert r['canonical_forms_devanagari']==q['canonical_forms_devanagari']
 assert r['prompt_sha256']==t['campaign']['prompt_sha256']
 assert r['answer_slp1']==transliterate(r['answer'],Scheme.Devanagari,Scheme.Slp1)
 assert r['answer'] not in puk.get(r['task_id'],[])
 cat=r['category'];root=r['dhatu']['aupadeshika'];ans=r['answer_slp1'];g=groups[cat]
 item={'task_id':r['task_id'],'index':r['index'],'answer':r['answer'],'answer_slp1':ans,
  'dhatu':r['dhatu'],'morphology':r['morphology'],'category':cat,
  'parent_disposition':r['disposition'],'independent_disposition':'rejected',
  'concur':True,'evidence_group':cat,'rule_ids':g['rules'],
  'exact_queue_identity_verified':True,'adopted_puk_alias_match':False}
 if cat=='literal_a_stem_strengthening':
  wrong,right=stem[root];assert wrong in ans
  item['diagnostic_wrong_stem']=wrong
  item['diagnostic_after_stem_change_matches_canonical']=ans.replace(wrong,right) in t['gold_slp1']
 elif cat=='adanta_aorist_unlicensed_i_reduplication':
  wrong,right=nasal[root];assert wrong in ans
  item['diagnostic_after_stem_change_matches_canonical']=ans.replace(wrong,right) in t['gold_slp1']
 elif cat=='intrinsic_middle_ending_mismatch':
  assert root in ['pada','kuha']
  if r['index']==718:
   assert ans=='padayAYcakfma'
   item['specific_derivation']='1.3.63 requires middle kṛ after middle main entry: padayāñcakṛmahe. The rule explicitly exempts as/bhū, which may retain para endings; those alternatives cannot rescue the actual kṛ answer.'
  elif r['index']==1123:
   assert ans=='kuhayetAm'
   item['specific_derivation']='3.4.102 siyuT + thematic stem,7.2.79 s-deletion,6.1.87 guṇa gives kuhayeyātām. Kashika prints paceyātām as direct generic control. kuhayetām instead matches para optative3dual or a different middle tense.'
  else:item['specific_derivation']='The submitted para ending does not match the source-specified intrinsic middle entry in these coordinates.'
 elif cat=='mixed_intrinsic_nic_and_no_nic_branches':
  assert root=='garva' and ans.startswith('ajagarv')
  item['specific_derivation']='caN reduplicated nic stem plus a para ending mixes the source-separated intrinsic branches.'
 elif cat=='adanta_aorist_reversed_vowel_quantities':
  assert root in ['goma','BAma','tIra']
 if r['task_id'] in opus and opus[r['task_id']]['answer_devanagari']==r['answer']:
  assert opus[r['task_id']]['disposition']=='rejected'
  item['identical_opus_answer_has_same_disposition']=True
 checked.append(item)

plan=BASE/'final1800-64k-01/execution-plan.json'
deps=json.loads(plan.read_text())['dependencies']
changed=[p for p,h in deps.items() if sha(ROOT/p)!=h];assert not changed
corrections=[
 {'id':'correct_strengthening_rule_identifiers','scope':'literal_a_stem_strengthening records',
  'change':'Replace7.2.115 as the putative first-vowel strengthening rule with7.2.116 for a-upadha vṛddhi and7.3.86 for light-upadha guṇa (kuha). Retain6.4.48 and the explicit retained-position explanation.',
  'disposition_impact':'none; argument already rejects the same wrong stem'},
 {'id':'cada_printed_witness_attribution','scope':'Cada reason text',
  'change':'Use the inspected1938 Siddhantakaumudi238 and Kshiratarangini333 entry321 as the exact short-Cada witnesses. The reviewed dependency list does not establish a photographed Balamanorama Cada passage; its puK/kathadi page is a different source finding.',
  'disposition_impact':'none; two inspected exact lexical witnesses remain'},
 {'id':'explicit_special_case_rule_locators','scope':'indices718 and1123',
  'change':'Add exact1.3.63 for kṛ auxiliary inheritance and3.4.102 for thematic middle optative dual. Preserve valid para as/bhū alternatives and no blanket-pada normalization.',
  'disposition_impact':'none; source documentation made more precise'}]
inputs={str(parent_path.relative_to(ROOT)):sha(parent_path),str(queue_path.relative_to(ROOT)):sha(queue_path),
 str(HERE/'Anthropic-review.json'):sha(HERE/'Anthropic-review.json')}
inputs.update(parent['source_dependencies'])
for p in sorted((HERE/'OpenAI-curadi-independent-sources').glob('*')):inputs[str(p.relative_to(ROOT))]=sha(p)
result={'schema':'independent-curadi-source-review-v1','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'all215_dispositions_concur_with_documentation_corrections',
 'reviewed_draft_sha256':sha(parent_path),'review_scope':'All215 actual Curadi answers, exact queue identities, source-group inference and exceptional endings; no full success/gold-union certification.',
 'counts':{'reviewed':215,'rejected':215,'accepted':0,'unresolved':0,'disposition_disagreements':0},
 'category_counts':dict(collections.Counter(r['category'] for r in checked)),
 'evidence_groups':groups,'documentation_corrections':corrections,'records':checked,
 'limits':['No automatic adoption of unsubmitted puK paradigms or extra operations. All19 adopted exact additions were checked and rescue none of these215.',
   'General-rule derivations can reject the actual wrong stem/ending; this is not exhaustive certification of canonical gold or successful outputs.',
   'No conclusion about the47 broad cases, the missing837 transport attempt, or full release qualification.',
   'Intrinsic-pada labels are lexical constraints, not a fifth user-selected coordinate.'],
 'original_dependencies_count':len(deps),'original_dependencies_changed':changed,
 'inputs':inputs,'paid_calls':0,'ledger_changes':0,'raw_or_frozen_files_changed':False,'scores_applied':False}
(HERE/'OpenAI-curadi-independent-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sha256':sha(HERE/'OpenAI-curadi-independent-review.json'),'counts':result['counts'],'identical_opus_cases':sum(r.get('identical_opus_answer_has_same_disposition',False) for r in checked),'documentation_corrections':len(corrections)},indent=2))
