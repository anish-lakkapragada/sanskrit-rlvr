"""Additive exact-row source review; never changes keys, model responses, or grades."""
from pathlib import Path
import json,hashlib,datetime,collections
B=Path('benchmarks/parallel-search-20261007/four_d-90')
RUN=B/'final1800-64k-01'; C=RUN/'astra-infrastructure-carry-01'; OUT=C/'source-adjudication'; SRC=OUT/'OpenAI-broad-sources'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
queue_path=C/'independent-review/completed-review/OpenAI-source-adjudication-queue.json'
queue=read(queue_path); rows=[r for r in queue if r['task']['campaign']['sampling_cell']['label']=='broad_non_curadi']
tasks_path=B/'candidate-1800-v1/tasks.json';tasks=read(tasks_path)
assert len(rows)==47 and len(tasks)==1800
# A rejection is of this exact answer for this public entry, not blanket certification of all engine gold.
D={}
def add(i,status,rules,basis,pages=(),group=None): D[i]={'disposition':status,'rule_ids':rules.split(','),'basis':basis,'dhatupradipa_page_locators':list(pages),'mechanism':group or rules.split(',')[0]}
add(15,'rejected','1.3.78,3.4.86','Exact maha pujayam is parasmaipada (Dhatupradipa mahati); Lot third singular takes tu or the licensed tat alternative. mahatam is the wrong ending/pada.',[61],'pada_or_person')
add(90,'rejected','1.2.1,1.1.5','Tudadi dip kshepe is inside kutadi; the non-nit/nnit ending is ngit and guna is blocked. didepitha imports guna into this exact class entry.',[121,122],'kutadi_guna')
add(105,'rejected','3.1.55','Divadi vrsha is in pushadi; parasmaipada aorist has ang. avarshishta uses the wrong sic/middle construction for this entry.',[110],'aorist_vikarana')
add(106,'rejected','1.3.12,1.3.78,3.4.78','Exact rage shankayam is parasmaipada; Dhatupradipa ragati. Optative middle -eyatham is not licensed by the supplied citation.',[66],'pada_or_person')
add(115,'rejected','1.2.1,1.1.5','Tudadi chuta chedane is a kutadi entry; the conditional sya is not nnit/nit, so ngit blocks guna. achotishyan wrongly changes u to o.',[121,122],'kutadi_guna')
add(131,'rejected','1.3.78,3.4.78','The supplied snai root has no atmanepada it marker; its root accent is not an anudatta-it suffix. Dhatupradipa snayati confirms P. asnayathah uses M.',[77],'pada_or_person')
add(138,'rejected','1.3.12,1.3.78','Supplied shatha is P; Dhatupradipa shathati. -ishyante is middle rather than requested ordinary P union for this exact entry.',[41],'pada_or_person')
add(229,'unresolved','3.1.56','Kashika explicitly gives sr gatau -> asarat without a class restriction; Madhaviya restricts the ang rule to the Juhotyadi entry by association with shas. The supplied Bhvadi sr and returned asaran therefore have a genuine commentary-scope conflict; do not resolve it from VP alone.',[],'aorist_commentary_scope')
add(234,'rejected','1.3.12,1.3.78','Supplied shita anadare is P; Dhatupradipa shetati. shetavahe is middle, not the P first dual shetavah.',[38],'pada_or_person')
add(287,'rejected','7.2.73','The a-final dhma aorist P requires sag and it before sic. adhmastam omits the resulting -sishtam material; compare the primary ayas-ishtam construction.',[77],'aorist_sag_it')
add(289,'rejected','8.3.78,8.3.79','The optional dh->dh-retroflex after it requires an in-final preceding anga. vas is consonant-final s; a preceding inserted i alone does not satisfy the lexical condition. avasidhvam dental dh remains required.',[],'dh_retroflex_scope')
add(303,'rejected','1.3.12,1.3.78,7.3.86','Exact hudr is P (r-it is not an atmanepada marker); hodishiya is M. Also long medial u is not the laghu upadha entitled to guna.',[],'pada_or_person')
add(372,'unresolved','1.3.76','Dhatupradipa treats marana/toshana/nishamana jna in the mit group as a mit prescription on janati, rather than an unequivocally independent Bhvadi lexeme. Kashika permits unprefixed janati middle for agent-directed fruit. Thus jajnjivahe cannot safely be rejected solely from the engine treating this code as Bhvadi P; exact identity/scope needs resolution.',[67],'lexical_identity_pada')
add(399,'rejected','7.1.59','Kashika/Nyasa explicitly distinguish trpha/trmpha: only the already nasal/anushanga entry receives the obligatory nasal extension; the nonnasal entry yields trphati. The supplied nonnasal trpha does not license trmphami.',[118],'distinct_nonnasal_entry')
add(412,'rejected','1.3.78,3.4.78','Adadi ra dane is a P entry; root accent is not an anudatta-it marker. rasiyastam is an M benedictive and is not licensed by unspecified pada for this exact citation.',[],'pada_or_person')
add(437,'unresolved','7.1.61,1.3.12','Dhatupradipa gatravinama listings associate jabh/jrbhi with jambhate and a jabhi alternative with jabhate; 7.1.61 supplies num to jabhi. The supplied jaBa~ has no anudatta-it or i-it but the same meaning. This is unresolved dictionary-identity evidence, not grounds to accept any nasal/middle replacement or reject it solely from VP.',[44],'lexical_identity_pada_num')
add(457,'rejected','7.2.73,3.4.101','The requested aorist first singular P requires mip->am (and the a-final sic formation). ajasi lacks that first-singular ending; it is not a licensed contraction of ajasisham.',[77],'aorist_person_ending')
add(458,'rejected','7.3.86','Pish has short laghu medial i before sarvadhatuka P thematic formation, so guna e is required. pisheva incorrectly retains i.',[],'stem_guna')
add(515,'rejected','1.3.78,3.4.78','Daip shodhane is P (Dhatupradipa dayati). dayasva is M; the lexical p-it does not confer middle.',[77],'pada_or_person')
add(691,'rejected','3.1.36,7.3.84','In the periphrastic perfect, the long-vowel initial ing root takes am, an ardhadhatuka formation, with guna and subsequent e->ay before am. iyancakrath e incorrectly uses the present iyang stem instead of ayam-.',[],'periphrastic_stem')
add(758,'rejected','7.3.80,6.4.113','Druñ occurs before puñ, outside both primary puadi scope readings. shna weak-ending a->i does not shorten the root u. drunitah has an unlicensed short root vowel; drunitah with long u is required.',[135],'outside_puadi')
add(760,'rejected','6.1.64','Kashika explicitly exempts sthivu (initial retroflex sh) from the otherwise general dhatvadi sh->s replacement. The returned asthivyam dentalizes the initial sh; Divadi membership does not remove this exception.',[],'initial_sibilant_exception')
add(815,'rejected','1.3.12,1.3.78,3.4.78','Cadi ahlade diptau has nasal i but no anudatta-it marker. The prescribed P second-dual perfect ending is athuh; c acandathe is M.',[],'pada_or_person')
add(829,'rejected','7.4.11,7.4.12','The exact long-r pF perfect weak stem has compulsory guna or optional short-r+yan, yielding papar-/papr-. Nyasa 7.4.12 explicitly says short-r blocks the u substitution. papurathuh wrongly uses labial u in this context.',[96,135],'perfect_r_stem')
add(834,'rejected','6.1.45','Ch o chedane becomes a-final before the non-shit benedictive construction; chayat follows. cheyat substitutes e without this licensing.',[],'ech_to_a')
add(873,'rejected','1.3.78,3.4.78','The exact svana entry has no middle marker, and is treated in the P/mit group; svaneyatham is M rather than P second dual. This does not resolve unrelated svan/svanj lexical substitutions.',[68],'pada_or_person')
add(896,'rejected','7.3.86','Ija gatikutsana has long medial i, corroborated by Dhatupradipa ijate/periphrastic ijancakre. Laghupadha guna does not turn that long vowel into e; ejishyete is the wrong stem.',[31],'stem_guna')
add(949,'rejected','1.3.78,3.4.78','Dy ai is P; dyayamahai uses the middle first-plural imperative. The unmarked public pada requires accepting licensed P/M possibilities, not arbitrary substitution of M endings.',[],'pada_or_person')
add(984,'accepted','7.3.80,8.4.1,8.4.2','Kashika gives a puadi-through-end-of-Kryadi reading alongside the shorter range. The visually checked Dhatupradipa printed127 footnote explicitly includes kshish among roots with short-vowel and long-vowel school readings. kshi + shna + si, with sh-conditioned hrasva and subsequent natva, yields ksh inasi. Accept exact क्षिणासि alongside canonical क्षीणासि; no school is chosen in the prompt.',[137],'puadi_scope_variant')
add(1038,'rejected','3.4.99','Conditional is ngit; first-person final s is obligatorily deleted. amedishyamah retains the present/future first-plural visarga in a conditional form.',[],'ngit_person_ending')
add(1063,'rejected','7.1.59','Primary commentary explicitly distinguishes nonnasal drpha from drmph a; only the latter licenses the obligatory nasal treatment. adrmphah imports another lexical entry into the supplied drpha.',[118],'distinct_nonnasal_entry')
add(1122,'unresolved','7.3.86','Literal supplied SUWa with long u does not permit laghupadha guna, but Dhatupradipa has short shutha at the same Bhvadi meaning gatipratighata (shothati), which would support shothita. This unresolved entry-reading conflict should not be certified as a model error from the frozen long-vowel engine key.',[41],'lexical_vowel_reading')
add(1157,'rejected','1.3.12,1.3.78','Haya gatau is P (Dhatupradipa hayati). hayishyavahe is the middle first dual, unsupported for the supplied entry.',[50],'pada_or_person')
add(1164,'rejected','7.1.59,7.3.86','Kashika distinguishes gupha from gumpha, expressly retaining nonnasal guphati. Thus agumphishva imports the nasal entry; the nonnasal root also has ordinary laghupadha guna in this sic P formation.',[118],'distinct_nonnasal_entry')
add(1271,'rejected','3.4.85,3.4.101','Lot third-dual P takes tam and thematic a gives bindatam. bindetam introduces the middle/optative e pattern instead of the specified imperative P ending.',[],'lakara_ending')
add(1272,'rejected','1.3.12,1.3.78','Maghi mandane has nasal i, not an anudatta-it marker, and is P in the supplied entry. manghedhvam is the middle optative second plural.',[],'pada_or_person')
add(1360,'rejected','1.3.12,1.3.78','Sage samvarane is P; Dhatupradipa sagati in the same mit group. segimahe uses a middle ending instead of P first-plural -ima.',[66],'pada_or_person')
add(1369,'rejected','7.2.73','A-final jya takes the sag/it sic P formation. ajyastam drops the required -sishtam sequence, matching neither the specified P second dual nor a licensed variant.',[137],'aorist_sag_it')
add(1415,'rejected','7.3.86,7.2.4','Tudadi muna is before the kutadi subsection, so its short medial u undergoes guna in the it-sic construction. amunishva omits the required guna; 7.2.4 blocks vrddhi, not this guna.',[],'stem_guna')
add(1451,'rejected','1.3.12,1.3.78','Kakhe hasane is P (Dhatupradipa kakhati). akakhathah is middle second singular, unsupported by its supplied citation.',[66],'pada_or_person')
add(1505,'rejected','3.4.101','Conditional is ngit; second-plural tha is replaced with ta. adhvarishyatha retains the simple-future ending instead of the conditional ending.',[],'ngit_person_ending')
add(1517,'rejected','6.1.64','The explicit sthivu exception prohibits initial sh->s dentalization. sthivyas ma begins with dental s, independently invalid even before considering the separate lengthening context.',[],'initial_sibilant_exception')
add(1533,'rejected','8.4.39','Kashika explicitly lists trpnu/trpnoti under the shubhnadi natva prohibition. atrpnutam must keep dental n; atrpnutam with retroflex n violates this named exception.',[],'natva_exception')
add(1586,'rejected','7.1.58','Nyasa/Kashika explain that ir-it is one composite marker, so its i is not independently idit. Thus the supplied skhadir does not acquire num by idito num dhatoh. skhanderan improperly adds n.',[],'composite_ir_marker')
add(1620,'rejected','1.3.12,1.3.78','Raha tyage is P (Dhatupradipa rahati), and the conditional first dual is -ava. ara hishyavahi imports the M ending.',[61],'pada_or_person')
add(1656,'rejected','1.2.1,1.1.5','Chuda samvarane belongs to kutadi, for which the non-nit/nnit future suffix is ngit. chodishyamah violates guna blocking for this exact entry.',[121,122],'kutadi_guna')
add(1738,'rejected','7.3.80,1.3.78','The short-root branch bhri-nati is valid under the wider puadi reading (Nyasa explicitly names bhri bhaye), so root shortening alone is not an error. The returned bhrinite nevertheless uses unlicensed middle pada; source variant is भ्रिणाति, not भ्रिणीते.',[137],'valid_shortening_wrong_pada')
assert set(D)=={r['index'] for r in rows}
# Cache references record exact bytes consulted. Failed placeholder fetches are never used.
def source_for(rule):
 p=SRC/(rule+'.web.txt')
 if p.exists() and 'Internal Error' not in p.read_text()[:100]:return p
 if rule in ['7.4.11','7.4.12']:return SRC/'7.4.11-12.web.txt'
 if rule in ['6.1.64','7.1.58','7.1.59']:return SRC/'web-primary-01.txt'
 p=OUT/'Anthropic-sources'/(rule+'.html')
 assert p.exists(),(rule,p)
 return p
catalog={}
for d in D.values():
 for rule in d['rule_ids']:
  p=source_for(rule);catalog[rule]={'path':str(p),'sha256':sha(p),'url':f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{rule[0]}/{rule}.htm','kind':'primary_commentary'}
excerpt=SRC/'dhatupradipa-selected-excerpts.json';scan=SRC/'dhatupradipa-page137.jpg'
for r in rows:
 d=D[r['index']];t=r['task'];d.update(index=r['index'],task_id=t['id'],dhatu=t['dhatu'],morphology=t['morphology'],prompt_sha256=t['campaign']['prompt_sha256'],root_family=t['campaign']['root_family'],forms_devanagari=[r['answer']],canonical_forms_devanagari=t['gold_devanagari'],canonical_forms_slp1=t['gold_slp1'],receipt_sha256=r['receipt_sha256'],sources=[catalog[z] for z in d['rule_ids']])
 if d['dhatupradipa_page_locators']:d['sources'].append({'path':str(excerpt),'sha256':sha(excerpt),'kind':'primary_work_OCR_locator','pages':d['dhatupradipa_page_locators']})
 if r['index'] in [984,1738]:d['sources'].append({'path':str(scan),'sha256':sha(scan),'url':'https://jainqq.org/explore/004319/137','kind':'primary_work_scan_visually_read'})
 if r['index'] in [229,437]:d['related_independent_review']={'path':str(OUT/'Anthropic-review.json'),'sha256':sha(OUT/'Anthropic-review.json'),'same_task_index':r['index']}
# Symmetric scope inventory examines inputs, never successful model answers.
new_forms={'09.0042':['क्षिणासि'],'09.0041':['भ्रिणाति']}
all_kry=[(i,t) for i,t in enumerate(tasks) if t['dhatu']['gana']=='Kryadi']
present=[(i,t) for i,t in all_kry if t['morphology']['lakara'] in ['Lat','Lan','Lot','VidhiLin']]
entries=[]
for i,t in present:
 code=t['dhatu']['code']; additions=new_forms.get(code,[])
 if additions:
  assert t['morphology']=={'lakara':'Lat','prayoga':'Kartari','purusha':'Madhyama' if code=='09.0042' else 'Prathama','vacana':'Eka'}
 entries.append({'index':i,'task_id':t['id'],'dhatu':t['dhatu'],'morphology':t['morphology'],'prompt_sha256':t['campaign']['prompt_sha256'],'canonical_forms_devanagari':t['gold_devanagari'],'additional_forms_devanagari':additions,'proposed_union_devanagari':sorted(set(t['gold_devanagari']+additions)),'scope_result':'new optional-shortening branch' if additions else ('outside both puadi readings (pre-pu)' if int(code.split('.')[1])<14 else 'no new surface branch for this selected entry; existing shortening/other conditions retained')})
assert len(present)==12 and len([x for x in entries if x['additional_forms_devanagari']])==2
scope={'schema':'exact-input-rule-coverage-review-v1','status':'proposed_for_independent_adoption_not_applied','rule':'7.3.80','examined_all_selected_inputs':1800,'selected_kryadi_inputs':len(all_kry),'selected_present_system_inputs':len(present),'affected_task_count':2,'new_forms_count':2,'selection_method':'Input-only scan of ALL frozen1800 entries by class and present-system lakara; no filter by provider correctness.','sources':[catalog['7.3.80'],catalog['8.4.1'],catalog['8.4.2'],{'path':str(scan),'sha256':sha(scan),'url':'https://jainqq.org/explore/004319/137'}],'derivation':'The broader puadi-through-end reading permits root I->i before shna. Existing shna guna/ending operations and natva remain; only these two selected late-puadi present cells gain new forms. The short root does not independently license middle pada. Roots before pu remain outside both readings. This does not extend hrasva to nonpresent ardhadhatuka forms.','candidate_tasks_sha256':sha(tasks_path),'execution_plan_sha256':sha(RUN/'execution-plan.json'),'symmetric_across_providers':True,'items':entries,'accepted_additions':[x for x in entries if x['additional_forms_devanagari']]}
write(OUT/'OpenAI-broad-puadi-scope.json',scope)
result={'schema':'bounded-source-adjudication-v1','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'provider':'OpenAI','source_review_scope':'All47 broad_non_curadi unrecognized usable answers; no whole-cohort source certification. Includes outcome-independent puadi coverage scan of all1800 selected inputs.','all_queue_rows_individually_mapped':True,'raw_scores_unchanged':True,'counts':dict(collections.Counter(x['disposition'] for x in D.values())),'accepted_indices':[i for i,d in D.items() if d['disposition']=='accepted'],'unresolved_indices':[i for i,d in D.items() if d['disposition']=='unresolved'],'rows':[D[r['index']] for r in rows],'rule_source_catalog':catalog,'symmetric_input_scope_review':{'path':str(OUT/'OpenAI-broad-puadi-scope.json'),'sha256':sha(OUT/'OpenAI-broad-puadi-scope.json')},'inputs':{'queue':{'path':str(queue_path),'sha256':sha(queue_path)},'candidate_tasks':{'path':str(tasks_path),'sha256':sha(tasks_path)},'execution_plan':{'path':str(RUN/'execution-plan.json'),'sha256':sha(RUN/'execution-plan.json')},'mechanical_review':{'path':str(C/'independent-review/completed-review/review.json'),'sha256':None}},'limitations':['Rejections adjudicate only the returned exact answer under its public entry. They do not certify the entire canonical union.','Unresolved dictionary/commentary identities remain unresolved, never silently scored as source-certified errors.','Ordinary pada rules are applied to exact visible citations; no separate pada choice was given, and all source-licensed pada possibilities must be retained.','Dhatupradipa excerpts are OCR locators; the critical optional-shortening page137 image was visually checked.','No model response, frozen key, alias policy, ledger, task membership, or shared policy was changed. Proposed additions require separate adoption and symmetric application.'],'provider_calls':0,'frozen_files_changed':False,'ledger_changes':False,'full_linguistic_certification':False}
# Resolve mechanical receipt filename without opening response bodies.
for p in (C/'independent-review/completed-review').glob('*.json'):
 if p.name in ['review.json','mechanical-review.json','review-result.json']:
  result['inputs']['mechanical_review']={'path':str(p),'sha256':sha(p)};break
write(OUT/'OpenAI-broad-review.json',result)
md=['# Bounded independent review of Astra broad-root answers','',f"Reviewed all 47 `broad_non_curadi` queue entries: {result['counts']}. Raw scores and inputs are unchanged.",'','Accept **क्षिणासि** for kṣīṣ09.0042, index984, under the broader pūādi scope reading of Kāśikā7.3.80. Nyāsa explicitly supports the corresponding bhri alternative; the visually checked Dhātupradīpa p.127 note records the school-dependent shortening. An input-only scan of all1800 selected tasks finds exactly two new unions: क्षीणासि/क्षिणासि and भ्रीणाति/भ्रिणाति. Both are proposed symmetrically, including the currently unreturned alternative. Astra1738 भ्रिणीते remains rejected because shortening does not license middle pada.','','Unresolved: index229 sṛ has conflicting commentary class scope;437 jabh has marker/lexical reading disagreement;372 jñā is described as a mit prescription on jānāti rather than clearly a separate P-only lexical entry;1122 the supplied long-vowel śūṭh conflicts with a short-vowel primary dictionary reading. These are not certified model errors.','','The remaining42 exact answers fail cited rule conditions or the supplied lexical identity: chiefly middle endings substituted for P entries, kutādi guṇa, nonnasal roots replaced by nasal homonyms, aorist or conditional endings, and explicit phonological exceptions. Every row includes exact dhātu, coordinates, prompt hash, receipt hash and source-cache hashes.','', 'This is bounded returned-answer adjudication, not exhaustive certification of Sanskrit, dictionary identity, or every engine gold variant. No raw response or scorer was changed.','','| Index | Entry | Answer | Disposition | Mechanism |','|---:|---|---|---|---|']
for r in rows:
 d=D[r['index']];md.append(f"| {r['index']} | {d['dhatu']['code']} | {r['answer']} | {d['disposition']} | {d['mechanism']} |")
md+=['','Files: `OpenAI-broad-review.json` contains all row evidence; `OpenAI-broad-puadi-scope.json` contains the symmetric12-cell inventory and2 proposed additions. Source caches are in `OpenAI-broad-sources/`.']
(OUT/'OpenAI-broad-review.md').write_text('\n'.join(md)+'\n')
print(json.dumps({'counts':result['counts'],'unresolved':result['unresolved_indices'],'accepted':result['accepted_indices'],'review_sha256':sha(OUT/'OpenAI-broad-review.json'),'scope_sha256':sha(OUT/'OpenAI-broad-puadi-scope.json')},indent=2))
