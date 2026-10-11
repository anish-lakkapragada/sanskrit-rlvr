"""Input-only family source index. Does not inspect evaluation receipts or scores."""
from collections import Counter, defaultdict
from pathlib import Path
import datetime, hashlib, json, re, sys
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'misc/vp_cartesian_task.py').is_file())
sys.path.insert(0,str(ROOT))
from finetune.prompts import slp1_to_devanagari
BASE=OUT.parent;CAND=BASE/'candidate-1800-v1'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 p=OUT/n;assert not p.exists(),n
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
planpath=BASE/'final1800-64k-01/execution-plan.json'
protected=read(planpath)['dependencies']
assert all(sha(ROOT/p)==h for p,h in protected.items())
assert not any((ROOT/p).resolve().is_relative_to(OUT) for p in protected)
tasks=read(CAND/'tasks.json');old=read(BASE/'test-hard-family-source-review.json')
clar=read(BASE/'reading-clarification.json');policy=read(CAND/'source-policy.json')
prior={r['family']:r for r in old['families']}
grouped=defaultdict(list)
for t in tasks:
 if t['campaign']['sampling_cell']['label'] in ('short_adanta_non_aorist','other_adanta_aorist'):
  grouped[t['campaign']['root_family']].append(t)
assert len(grouped)==35 and sum(map(len,grouped.values()))==1080
assert Counter(v[0]['campaign']['sampling_cell']['label'] for v in grouped.values())=={'short_adanta_non_aorist':14,'other_adanta_aorist':21}
assert not {t['dhatu']['code'] for ts in grouped.values() for t in ts}&{'10.0108','10.0430','10.0466','10.0467'}
dp_path=ROOT/'benchmarks/parallel-search-20261006/four_d/source-03/dhatupradipa-clean.txt'
pages={}
for page,body in re.findall(r'Page #(\d+)(.*?)(?=Page #\d+|$)',dp_path.read_text(),re.S):
 if 157<=int(page)<=163:pages.setdefault(int(page),body)
rules={
 '3.1.25':{'topic':'Class-intrinsic nic','use':'Curadi nic in the root own meaning is expressly described; this is not an independently requested causative coordinate.'},
 '6.4.48':{'topic':'Literal-final-a deletion and its retained conditioning','use':'The commentary explicitly uses kathayati to explain why deletion of lexical a does not license ordinary penultimate strengthening.'},
 '1.3.74':{'topic':'Nic and middle endings','use':'Middle endings depend on the action fruit accruing to the agent; this unspecified context permits relevant alternatives, subject to lexical subgroup restrictions.'},
 '1.3.78':{'topic':'Remaining active-agent endings','use':'Parasmaipada applies outside specified Atmanepada conditions. Do not treat every root as freely interchangeable in pada.'},
 '3.1.33':{'topic':'Future/conditional bases','use':'sya for Lrt/Lrn and tasi for Lut; retain the correct lexical stem and check it/ending realization separately.'},
 '3.1.35':{'topic':'Periphrastic perfect','use':'The relevant derivative base receives am in Lit. A short-root citation does not justify strengthening the inherited lexical stem.'},
 '3.1.40':{'topic':'Perfect auxiliary alternatives','use':'The am construction permits kr/bhu/as auxiliaries. Auxiliary agreement and surface sandhi still require task-specific derivation.'},
 '6.4.51':{'topic':'Nic loss before an anit ardhadhatuka ending','use':'Needed for benedictive/aorist branch distinctions. Compare the explicit para choryat versus middle chorayisista examples in1.3.74 commentary; do not retain or delete aya uniformly.'},
 '6.4.71':{'topic':'Past/conditional augment','use':'Lan, Lun and Lrn receive the augment under this rule; vowel-initial bases and junctions require their own sandhi analysis.'},
 '3.1.48':{'topic':'Curadi-nic aorist construction','use':'For the nic branch in Kartari Lun, cang replaces cli. An independently licensed no-nic branch must be derived separately.'},
 '7.4.2':{'topic':'Aglopin aorist vowel protection','use':'The commentary explicitly discusses kathadi literal-a roots and restriction of the ordinary shortening/reduplicative behavior.'},
 '7.4.93':{'topic':'Conditioned reduplicative vowel changes','use':'The anaglope qualification blocks generic san-like treatment for examples such as acakathat; do not apply a memorized ordinary causative template to all adantas.'},
 '7.3.36':{'topic':'puK boundary','use':'General puK conditions are distinct from merely lengthening a root vowel. The concrete kathadi alternative is addressed in the separate source finding, not inferred from this rule alone.'},
 '7.2.115':{'topic':'Strengthening condition in the reported alternative','use':'The Balamonorama passage invokes this strengthening rule when explaining the competing final-a treatment. It does not license p-less kathAyati.'}}
for r,v in rules.items():
 p=OUT/'primary-source-cache'/(r+'.html');assert p.is_file()
 v.update(url=f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{r[0]}/{r}.htm',snapshot_path=str(p.relative_to(ROOT)),snapshot_sha256=sha(p),evidence_level='primary_commentary_inspected; bounded_rule_reference_not_complete_derivation')
profiles={
 'Lat':{'rules':['3.1.25','6.4.48','1.3.74','1.3.78'],'review':'Preserve the source-supported stem and intrinsic pada; inflect for the requested person/number.'},
 'Lan':{'rules':['3.1.25','6.4.48','6.4.71','1.3.74','1.3.78'],'review':'Present-system stem plus augment and secondary endings; inspect junctions and final spelling.'},
 'Lot':{'rules':['3.1.25','6.4.48','1.3.74','1.3.78'],'review':'Imperative endings/options must be derived for the exact person/number. A printed present singular alone does not certify them.'},
 'VidhiLin':{'rules':['3.1.25','6.4.48','1.3.74','1.3.78'],'review':'Ordinary optative formation on the correct stem; verify the exact para/middle ending.'},
 'Lit':{'rules':['3.1.25','6.4.48','3.1.35','3.1.40','1.3.74','1.3.78'],'review':'Periphrastic perfect: include licensed auxiliary alternatives, correct auxiliary agreement, and sandhi. Do not mistake multiple gold forms for ambiguous root identity.'},
 'Lut':{'rules':['3.1.25','6.4.48','3.1.33','6.4.51','1.3.74','1.3.78'],'review':'Periphrastic future tasi/it formation and person/number endings; preserve lexical vowel quantity.'},
 'Lrt':{'rules':['3.1.25','6.4.48','3.1.33','6.4.51','1.3.74','1.3.78'],'review':'sya future with relevant it/aya realization; a correct stem still requires correct endings and sibilant sandhi.'},
 'Lrn':{'rules':['3.1.25','6.4.48','3.1.33','6.4.51','6.4.71','1.3.74','1.3.78'],'review':'Conditional future system plus augment and secondary endings.'},
 'AshirLin':{'rules':['3.1.25','6.4.48','6.4.51','1.3.74','1.3.78'],'review':'Distinguish the para ni-lopa branch from middle it/retained-aya behavior; do not conflate ordinary optative with benedictive.'},
 'Lun':{'rules':['3.1.25','3.1.48','6.4.48','6.4.51','6.4.71','7.4.2','7.4.93','1.3.74','1.3.78'],'review':'Separate intrinsic nic/cang and any explicitly licensed no-nic/sigmatic branches; preserve lexical length and derive augment, reduplication, junctions and endings separately.'}}
families=[]
for f,ts in sorted(grouped.items(),key=lambda x:x[1][0]['dhatu']['code']):
 t=ts[0];d=t['dhatu'];p=prior[f];c=d['code'];cell=t['campaign']['sampling_cell']['label']
 assert p['aupadeshika']==d['aupadeshika'] and p['artha']==d['artha'] and p['entry_scope_issue'] is None
 controls=[]
 for control in p['controls']:
  direct=control['direct_expected_slp1']
  witnesses=[]
  for form in direct:
   deva=slp1_to_devanagari(form)
   matched=[n for n,body in pages.items() if deva in body or deva.rstrip('्') in body]
   witnesses.append({'slp1':form,'devanagari':deva,'source_level':'direct representative according to the prior bounded primary-source audit',
      'source_urls':p['source_urls'],'cached_Dhatupradipa_matching_scan_pages':matched,
      'locator_limit':'OCR matches assist navigation only; use the named entry/photo to resolve readings.'})
  controls.append({'lakara':control['lakara'],'prayoga':'Kartari','purusha':'Prathama','vacana':'Eka',
   'source_attested_witnesses':witnesses,'inferred_control_slp1':control.get('inferred_control_slp1',[]),
   'canonical_vp_representative_slp1':control['vp_gold_slp1'],'source_evidence':control['source_evidence'],
   'full_union_independently_attested':False,'selected_tense':control['lakara'] in {x['morphology']['lakara'] for x in ts}})
 branch={'nic':'ordinary/class-intrinsic nic; no independently added sanadi operation',
  'pada':'Relevant para and middle branches remain accepted when licensed; beneficiary context is not supplied. See1.3.74/1.3.78.',
  'basis':'General Curadi rule plus inspected lexical representative; no complete paradigm certification.'}
 if c in {'10.0440','10.0443'}:
  branch.update(pada='Intrinsic Atmanepada in this lexical subgroup; do not add an ordinary Parasmaipada counterpart.',
   basis='SK1938 printed237/scan241 explicitly introduces the padadi-to-garva Atmanepada group and prints padayate/kuhayate.')
 if c=='10.0449':
  branch.update(nic='Intrinsic nic/no-nic alternative',pada='nic branch middle (garvayate); no-nic branch para (garvati). Keep the analyses separate.',
   basis='SK1938 printed237 and Dhatupradipa scan160; the latter prints garvayate and separately garvati. Complete Lun propagation is rule inference.')
 if c=='10.0456':
  branch.update(nic='Intrinsic nic/no-nic alternative',pada='nic branch permits the relevant para/middle alternatives; no-nic para branch is distinct.',
   basis='SK1938 printed238/scan242 explicitly prints katrayati and katrati. karta is a separately specified alternate root, not a free answer.')
 residual=['Full requested person/number paradigms and all accepted spelling variants are not independently printed/verified for this family.',
  'The reported kathadi puK alternative needs the same task-level source treatment for successes and misses; broader propagation is not certified.']
 note=p['note']
 if c=='10.0481':
  note=clar['findings'][c]['public_declaration']
  residual.append('The older audit statement that printed SK has CAdayati is superseded: printed SK238 and Kshiratarangini333 both show Cadayati. Do not import another chad lexeme or the conflicting transcription as an automatic long-stem answer.')
 elif c=='10.0394':residual.append('The aspirated paTha lexical citation is printed in SK236. Its paThayati stem is an explicit rule inference in the prior audit, not a directly inspected finite printed witness.')
 elif p['status']!='lexical_supported':residual.append(p['note'])
 skpage=240 if c in {'10.0389','10.0390','10.0391','10.0394','10.0396','10.0399'} else 241 if int(c.split('.')[1])<=454 else 242
 families.append({'family':f,'dictionary_identity':d,'citation_devanagari':slp1_to_devanagari(d['aupadeshika']),
  'meaning_devanagari':slp1_to_devanagari(d['artha']),'cell':cell,'selected_questions':len(ts),
  'selected_tense_counts':dict(Counter(x['morphology']['lakara'] for x in ts)),
  'selected_item_ids':[x['id'] for x in ts],
  'selected_coordinates':[{'id':x['id'],**x['morphology']} for x in ts],
  'lexical_evidence_status':'source_supported_under_frozen_reading; full_paradigm_not_certified',
  'lexical_note':note,'intrinsic_branches':branch,'primary_lexical_locators':p['source_urls']+
   [f'https://jainqq.org/explore/002377/{skpage}'],
  'representative_controls':controls,'needed_tense_profiles':sorted({x['morphology']['lakara'] for x in ts}),
  'residual_uncertainties':residual,'added_prefix_or_sanadi':False,'new_source_hold_imposed':False})
snapshots=read(OUT/'primary-source-cache/index.json')
for p in [BASE/'reading-clarification-sources/siddhanta-kaumudi-1938-scan-242.jpg',
 ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01/independent-source-cache/sk1938-scan241.jpg',
 BASE/'reading-clarification-sources/kshira-tarangini-scan-390.jpg',dp_path,
 BASE/'test-hard-family-sources/madhaviya-scan-625.jpg',BASE/'test-hard-family-sources/madhaviya-scan-627.jpg',BASE/'test-hard-family-sources/madhaviya-scan-629.jpg']:
 snapshots.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'origin':'Existing primary-source cache; reused without modification.'})
summary={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'Input-only adjudication reference pack',
 'candidate_tasks_sha256':sha(CAND/'tasks.json'),'questions_covered':1080,'families_covered':35,
 'short_non_lun':{'families':14,'questions':936},'other_adanta_lun':{'families':21,'questions':144},
 'family_records':families,'tense_review_profiles':profiles,'primary_rule_references':rules,'source_snapshots':snapshots,
 'source_scope_finding':{'path':str((OUT/'puk-scope-adjudication.json').relative_to(ROOT)),
  'sha256':sha(OUT/'puk-scope-adjudication.json'),'exact_direct_correction_recommendations':2,
  'frozen_policy_changed':False,'broader_propagation':'unresolved; not an automatic alias map'},
 'uniform_adjudication_protocol':['Use exact dictionary citation, class, meaning and four requested coordinates before comparing the answer.',
  'Separate direct printed witnesses, ordinary rule inference, alternative lexical readings and unresolved source scope.',
  'Apply supported corrections symmetrically to both providers and every affected task, including successes where the same issue applies.',
  'Preserve raw/canonical/predeclared-whitelist scores and membership. Report later source-adjudicated scores and unresolved cases separately.',
  'Every usable unrecognized answer needs source adjudication; this reference pack does not pre-label any model response or certify every canonical success.'],
 'limits':['Representative controls prove only the displayed forms/lexical facts, not entire unions or paradigms.',
  'General rules listed are a reviewer navigation aid, not a complete executable independent Sanskrit oracle.',
  'The broader ordinary kathadi puK alternative remains open outside the two directly attested exact cells.',
  'No final receipts, responses or scores were read; no question was chosen using a model outcome.'],
 'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),CAND/'tasks.json',CAND/'source-policy.json',CAND/'scoring-adoption.json',BASE/'test-hard-family-source-review.json',BASE/'reading-clarification.json',OUT/'puk-scope-adjudication.json',dp_path,planpath]},
 'paid_dependencies_unchanged':len(protected),'provider_calls':0,'final_model_outputs_read':False,
 'existing_source_decisions_or_frozen_files_changed':False,'full_paradigm_certification':False}
assert all(sha(ROOT/p)==h for p,h in protected.items())
save('reference-pack.json',summary)
lines=['# Final 1,800-question source reference pack','',
 '2026-10-07 Pacific / 2026-10-08 UTC. This input-only pack covers all **35 hard-component families and1,080 questions**:14 short-adanta/non-Lun families (936questions) and21 other-adanta/Lun families (144questions). It reads no final-evaluation outputs or scores and changes no task, key, scorer or prior source decision.','',
 'The [JSON pack](reference-pack.json) maps every family and selected item ID to its exact dictionary identity, intrinsic branches, representative primary-source controls, selected tenses and residual uncertainties. Its tense profiles point to inspected primary commentaries; they are review guidance, not full-paradigm certification.','',
 'The substantive new issue is the [puK source finding](puk-scope-adjudication.md): two exact ordinary kathadi present forms are directly attested as alternatives. They are recommendations for a separate symmetric source-adjudicated score, pending independent review; the canonical and frozen spelling policies remain unchanged. Broader propagation is unresolved.','',
 '| Code / supplied root | Questions | Representative printed/source-audited Lat witness | Intrinsic branch note |',
 '|---|---:|---|---|']
for f in families:
 lat=next(x for x in f['representative_controls'] if x['lakara']=='Lat')
 witness=', '.join(x['devanagari'] for x in lat['source_attested_witnesses']) or 'Lexical entry printed; finite stem inferred'
 c=f['dictionary_identity']['code']
 branch='Class nic; relevant para/middle alternatives'
 if c in {'10.0440','10.0443'}:branch='Intrinsic middle endings'
 if c=='10.0449':branch='nic middle / no-nic para'
 if c=='10.0456':branch='nic and no-nic alternatives'
 if c=='10.0481':branch+='; literal-a Cada reading'
 lines.append(f'| {c} {f["citation_devanagari"]} | {f["selected_questions"]} | {witness} | {branch} |')
lines += ['',
 'For the short families, preserve the literal-final-a stem behavior across the nine selected non-aorist tenses. The [6.4.48 commentary](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.48.htm) explicitly uses कथयति to explain the conditioning. The perfect requires the appropriate am construction and auxiliary alternatives; futures and the conditional require their own markers; the benedictive distinguishes ni deletion and retained-aya branches. A correct present stem alone does not certify these forms.','',
 'For the other-adanta aorists, inspect the intrinsic nic/cang and any separately licensed no-nic branch. The [7.4.2](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.2.htm) and [7.4.93 commentaries](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.93.htm) explain why generic causative shortening/reduplication templates cannot be applied uniformly. The JSON preserves direct representative aorists separately from inferred ones.','',
 'पद and कुह remain in the printed intrinsic-Atmanepada subgroup. गर्व and कत्र have documented intrinsic nic/no-nic alternatives; keep their analyses separate. छद follows the exact frozen literal-final-a declaration, supported by the photographed short छदयति in both inspected editions. The earlier conflicting SK transcription is not a reason to insert a blanket long stem. लज, अंस, चित्र and छिद्र retain the recorded lexical/meaning distinctions.','',
 'The35 included families exclude the four previously held codes10.0108,10.0430,10.0466and10.0467. Those existing decisions are unchanged. Finite spelling aliases still follow the separately adopted frozen policy; unrecognized spellings require source review.','',
 'Later review must apply the same lexical, morphological and spelling policy to successes and misses, across both providers. Preserve raw, canonical-only and predeclared-whitelist scores; report supported source corrections separately and keep unresolved answers visible. No full linguistic certification or model-error disposition is claimed by this pack. All44 live paid-execution dependency hashes were checked unchanged.']
(OUT/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'families':35,'questions':1080,'source_snapshots':len(snapshots),'reference_pack_sha256':sha(OUT/'reference-pack.json'),'protected_dependencies_unchanged':len(protected)},indent=2))
