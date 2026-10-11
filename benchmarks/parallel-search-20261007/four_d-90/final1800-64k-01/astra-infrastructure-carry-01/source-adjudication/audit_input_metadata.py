"""Input-only metadata diagnostic over every frozen selected family.

No response, result, score, receipt body, or accounting file is opened. Engine
pada probes diagnose visible-entry behavior; they are not independent grammar.
"""
from pathlib import Path
from collections import defaultdict, Counter
import hashlib, json, re, unicodedata, sys, os
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'misc/vp_cartesian_task.py').exists())
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
from functools import lru_cache
import vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Pada, Lakara, Prayoga, Purusha, Vacana, DhatuPada
from misc.vp_cartesian_task import entries_by_code, GRAMMAR
from misc.vp_cartesian_prompt_v1 import render
from finetune.prompts import slp1_to_devanagari
BASE=Path('benchmarks/parallel-search-20261007/four_d-90')
OUT=BASE/'final1800-64k-01/astra-infrastructure-carry-01/source-adjudication'
INV=OUT/'lexical-holds-sources/ashta-dhatu-data.json'
TASKS=BASE/'candidate-1800-v1/tasks.json'
PUBLIC=BASE/'candidate-1800-v1/public-prompts.json'
GANAS={n+1:g for n,g in enumerate(['Bhvadi','Adadi','Juhotyadi','Divadi','Svadi','Tudadi','Rudhadi','Tanadi','Kryadi','Curadi'])}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def nfc(s):return unicodedata.normalize('NFC',s)
def norm(s):return re.sub(r'[\\^\s\u0951\u0952]','',nfc(s))
def slp(s):return transliterate(s,Scheme.Devanagari,Scheme.Slp1)
def cform(d):return slp1_to_devanagari(d['aupadeshika'])
@lru_cache(maxsize=None)
def probe(code,l,p,u,v):
 d=entries_by_code()[code].dhatu;out={}
 for label,dp in [('P',DhatuPada.Parasmaipada),('A',DhatuPada.Atmanepada)]:
  xs=GRAMMAR.derive(Pada.Tinanta(dhatu=d,lakara=getattr(Lakara,l),prayoga=getattr(Prayoga,p),purusha=getattr(Purusha,u),vacana=getattr(Vacana,v),dhatu_pada=dp))
  out[label]={'forms_slp1':sorted({x.text for x in xs}), 'licensing_trace_references':sorted({str(s.source)+':'+s.code for x in xs for s in x.history if s.code.startswith(('1.3.','3.1.')) or str(s.source)!='azwADyAyI'})}
 return out
def pset(q):return ''.join(k for k in ['P','A'] if q[k]['forms_slp1'])
# Explanations categorize diagnostics, not automatic grammar/scorer decisions.
EXPLAIN={
 '01.0150':('missing_it_accent_candidate','Inventory A but literal unaccented a-it drives engine P. Exact jabh/jabhi reading and num are already source-unresolved; inventory alone cannot settle them.','Read the exact Kshiratarangini jabha alternate and distinguish jabhi/jrbhi at the same meaning.'),
 '01.0248':('independently_confirmed_visible_entry_conflict','Inventory A agrees with independent primary middle-only reb. Public citation rebf~ omits the final marker anudatta; frozen local engine produces P.','Primary Dhatupradipa scans43/50; preserve existing independent source adjudication.'),
 '01.0946':('independently_confirmed_visible_entry_conflict','Inventory A agrees with independent primary middle-only khund. Public Kuqi~ omits final marker anudatta; frozen local engine produces P.','Primary Kshiratarangini scan110 printed53; preserve existing independent source adjudication.'),
 '01.0507':('intrinsic_derivation_or_context_not_bare_pada_conflict','Inventory A summarizes the bare pan entry; trace3.1.28 intrinsic aya adds a P branch. This is not missing anudatta.','Apply already reviewed3.1.28/31 semantic/optionality conditions; no blanket P/A hold.'),
 '01.0508':('intrinsic_derivation_or_context_not_bare_pada_conflict','Inventory A summarizes pana, while intrinsic aya is P; nonpresent conditions3.1.31 can restore the bare A branch. Present-only probes would misleadingly suggest A was lost.','Review3.1.28/31 if grammar certification is needed; compare actual selected conditional union.'),
 '10.0449':('intrinsic_derivation_or_context_not_bare_pada_conflict','Inventory tags nic-optional; garvayate is middle intrinsic nic, garvati bare P. The single A label does not describe the full optional construction union.','Use existing Curadi nic-optionality source review; do not hold all7 tasks solely from the flat pada label.'),
 '07.0017':('conditional_pada_rule_not_inventory_contradiction','Root-level P label is not exhaustive: engine1.3.66 licenses middle in the appropriate bhuj meaning.','Verify1.3.66 semantic scope against palanabhyavahara; inventory label alone cannot prohibit the middle branch.'),
 '01.1077':('conditional_pada_rule_not_inventory_contradiction','Engine1.3.23 provides the stha middle condition; broad P inventory label is a default.','Verify1.3.23 prakasha/stheya conditions if needed; do not invent an explicit pada coordinate.'),
 '01.1164':('conditional_pada_rule_not_inventory_contradiction','Engine1.3.47 licenses middle for particular vad meanings; broad P label is not an exhaustive union.','Check1.3.47 semantic coverage in the supplied vyaktayam vaci entry.'),
 '01.0991':('lakara_condition_not_general_pada_conflict','Lat probe takes middle via1.3.60 (shiti), but the selected Lit has P and matches the inventory.','No selected-task pada conflict; present probe must not be extrapolated to Lit.'),
 '01.0862':('lakara_condition_explicitly_explained_by_inventory','The inventory pada_note expressly licenses P under1.3.91/92. Selected Lrn has sya and local1.3.92; Lat remains A.','No new contradiction; preserve complete conditional union.'),
 '01.0229':('inventory_field_vs_own_note','Inventory says P but its own dhaturoopnandini_note cites Kaumudi and examples supporting middle too. Local engine explicitly cites Kaumudi2291.','A flat-label diagnostic is not a source hold; use the note and primary Kaumudi2291 before formal truth claims.'),
 '08.0008':('pada_label_scope_needs_primary_confirmation','Inventory Tanadi vanu yacane says A; local P branch cites Kaumudi2547.2 plus a Bhvadi dhatupatha reference. This may be an intentional cross-gana prescription, not missing it-accent.','Check exact Kaumudi2547.2 and Tanadi/Bhvadi van scope; do not assert engine error from inventory label.'),
}

def main():
 ts=load(TASKS);ps=load(PUBLIC);inv=load(INV)['data']
 assert len(ts)==len(ps)==1800
 grouped=defaultdict(list);index=defaultdict(list)
 for r in inv:index[r['baseindex']].append(r)
 for i,t in enumerate(ts):
  assert ps[i]['id']==t['id'] and ps[i]['prompt']==render(t)
  assert hashlib.sha256(ps[i]['prompt'].encode()).hexdigest()==t['campaign']['prompt_sha256']
  grouped[t['campaign']['root_family']].append((i,t))
 assert len(grouped)==755
 families=[];matrix=Counter();actual_matrix=Counter();sources=[]
 for fam,pairs in sorted(grouped.items()):
  d=pairs[0][1]['dhatu'];code=d['code'];rr=index.get(code,[])
  assert len(rr)==1,('nonunique inventory code',code,len(rr))
  r=rr[0];assert all(t['dhatu']==d for _,t in pairs)
  inventory_citation=slp(r['aupadeshik']);citation_same=norm(d['aupadeshika'])==norm(inventory_citation)
  artha_same=re.sub(r'\s','',d['artha'])==re.sub(r'\s','',slp(r['artha']))
  gana_same=GANAS[int(r['gana'])]==d['gana'] and int(code.split('.')[0])==int(r['gana'])
  expected={'A':'A','P':'P','U':'PA'}[r['pada']]
  lat=probe(code,'Lat','Kartari','Prathama','Eka');observed=pset(lat);matrix[(r['pada'],observed)]+=1
  root_anu=bool(re.search(r'(?<!~)\\',d['aupadeshika']))
  marker_anu=bool(re.search(r'~\\',d['aupadeshika']))
  root_tag='anudatta' if 'अनुदात्तोपदेशः' in r.get('tags','') else 'udatta' if 'उदात्तोपदेशः' in r.get('tags','') else 'unspecified'
  accent_tag_difference=(root_tag=='anudatta')!=root_anu if root_tag!='unspecified' else False
  selected=[]
  for i,t in pairs:
   m=t['morphology'];a=probe(code,m['lakara'],m['prayoga'],m['purusha'],m['vacana']);actual=pset(a);actual_matrix[(r['pada'],actual)]+=1
   union=set(a['P']['forms_slp1'])|set(a['A']['forms_slp1']);assert union==set(t['gold_slp1']),('gold differs',i)
   selected.append({'index':i,'task_id':t['id'],'morphology':m,'prompt_sha256':t['campaign']['prompt_sha256'],'engine_pada_set':actual,'flat_inventory_label_difference':actual!=expected,'probe':a})
  flags=[]
  if not gana_same:flags.append('code_class_difference')
  if not citation_same:flags.append('citation_segment_difference')
  if not artha_same:flags.append('artha_reading_difference')
  if accent_tag_difference:flags.append('root_accent_tag_difference')
  if observed!=expected:flags.append('present_probe_pada_label_difference')
  if any(x['flat_inventory_label_difference'] for x in selected):flags.append('selected_context_pada_label_difference')
  if r.get('no_forms_note'):flags.append('inventory_marks_no_independent_forms')
  if any(s in r.get('tags','') for s in ['छान्दस','वैदिक']):flags.append('vedic_tag_with_preexisting_classical_exception')
  reason=EXPLAIN.get(code)
  secondary=[]
  if accent_tag_difference:secondary.append({'classification':'root_accent_tag_needs_primary_comparison','scope':'This compares root accent tags only, never the unaccented editorial citation string. It is not proof the local accent is wrong.','source_needed':('Resolve the mit-placeholder identification first.' if code=='01.0922' else 'Compare exact accented dhatupatha reading and its anit/vet prescription; inventory tags may summarize another tradition.')})
  if code=='01.0208':secondary.append({'classification':'editorial_nasal_marker_omission_candidate','scope':'Inventory pebf lacks candrabindu; local pebf~\\ contains an r-it marker and its accent. Both inventory and engine are A. Treat as a notation/readings diagnostic, not a proven public-input contradiction.','source_needed':'Compare the exact pebr/pevr alternative in Dhatupradipa.'})
  if code=='01.1114':secondary.append({'classification':'explicit_variant_reading_in_inventory_note','scope':'Artha gatiroshanayoh vs gatireshanayoh: the inventory note itself explicitly records the roshana reading. Not a demonstrated input error.','source_needed':'Primary reading comparison only if this meaning changes the requested derivation.'})
  if r.get('no_forms_note'):secondary.append({'classification':'placeholder_entry_source_hold_candidate','scope':'Inventory explicitly says this is a common reference to other entries rather than an independent root; the supplied class/citation should be checked against primary interpretation.','source_needed':('SK2353/Tattvabodhini and Dhatupradipa printed57, jna/ jnap mit prescription.' if code=='01.0923' else 'SK/Tattvabodhini shrai/shra mit common reference; exact Lan form licensing.')})
  if any(s in r.get('tags','')for s in ['छान्दस','वैदिक']):secondary.append({'classification':'previously_reviewed_classical_exception_not_new_hold','scope':'Shared policy explicitly retains this exact code despite the surrounding Vedic group. A flat Vedic tag is not grounds to reverse the independently sourced exception.','source_needed':'Existing policy04/07 source evidence for03.0017/05.0033, preserved by policy21.'})
  families.append({'root_family':fam,'dhatu':d,'public_citation_devanagari':cform(d),'public_artha_devanagari':slp1_to_devanagari(d['artha']),'inventory':{k:r[k] for k in r if k in ['i','baseindex','aupadeshik','dhatu','gana','pada','settva','artha','tags','pada_note','pathabhed_note','no_forms_note','dhaturoopnandini_note','antarganas']},'inventory_citation_slp1':inventory_citation,'comparison':{'unique_code_match':True,'class_matches':gana_same,'citation_matches_ignoring_accents_and_whitespace':citation_same,'artha_matches_ignoring_whitespace':artha_same,'local_root_anudatta_mark':root_anu,'local_anudatta_it_mark':marker_anu,'inventory_root_accent_tag':root_tag,'root_accent_tag_difference':accent_tag_difference,'inventory_pada_set':expected,'lat_pada_set':observed},'present_diagnostic_probe':lat,'selected_task_count':len(pairs),'selected_tasks':selected,'diagnostic_flags':flags,'pada_disposition':({'classification':reason[0],'basis':reason[1],'source_needed':reason[2]} if reason else None),'other_dispositions':secondary})
 flagged=[f for f in families if f['diagnostic_flags']]
 flags=sorted({x for f in families for x in f['diagnostic_flags']})
 byflag={k:{'families':sum(k in f['diagnostic_flags']for f in families),'all_selected_tasks_in_those_families':sum(f['selected_task_count'] for f in families if k in f['diagnostic_flags']),'codes':[f['dhatu']['code']for f in families if k in f['diagnostic_flags']]}for k in flags}
 known=['01.0248','01.0946']
 source_files=['lexical-holds-sources/dhatupradipa-43.jpg','lexical-holds-sources/dhatupradipa-50.jpg','lexical-holds-sources/kshira-110.jpg','lexical-holds-sources/1.3.12.html','lexical-holds-sources/1.3.78.html']
 result={'schema':'selected-input-metadata-diagnostic-v1','status':'complete_metadata_diagnostic_no_automatic_hold_or_grade_change','scope':{'fixed_tasks':1800,'selected_families':755,'family_key':'exact aupadeshika + gana','inventory_records':len(inv),'join_key':'baseindex; i is retained for reference only','inventory_url':'https://raw.githubusercontent.com/ashtadhyayi-com/data/master/dhatu/data.txt','outcomes_read':False,'all_selected_inputs_included_regardless_of_correctness':True},'counts':{'unique_code_matches':len(families),'code_class_differences':byflag.get('code_class_difference',{}).get('families',0),'accent_free_citation_matches':sum(f['comparison']['citation_matches_ignoring_accents_and_whitespace']for f in families),'artha_matches':sum(f['comparison']['artha_matches_ignoring_whitespace']for f in families),'inventory_citations_with_explicit_accent_signs':sum(any(z in r['aupadeshik'] for z in ['॒','॑'])for r in inv),'flagged_union_families':len(flagged),'flagged_union_tasks':sum(f['selected_task_count']for f in flagged),'present_pada_label_differences':sum(f['comparison']['lat_pada_set']!=f['comparison']['inventory_pada_set']for f in families),'selected_pada_label_difference_families':sum(any(t['flat_inventory_label_difference']for t in f['selected_tasks'])for f in families),'selected_pada_label_difference_tasks':sum(t['flat_inventory_label_difference']for f in families for t in f['selected_tasks']),'known_primary_missing_it_accent_conflicts':2,'known_primary_missing_it_accent_tasks':sum(f['selected_task_count'] for f in families if f['dhatu']['code']in known)},'counts_by_flag':byflag,'pada_comparison_matrices':{'present_family_probe':[{'inventory':k[0],'engine':k[1],'families':n}for k,n in sorted(matrix.items())],'selected_task_context':[{'inventory':k[0],'engine':k[1],'tasks':n}for k,n in sorted(actual_matrix.items())]},'interpretation':['No inventory citation contains accent marks, so their absence cannot diagnose a missing local anudatta. We separately compare explicit root-accent tags and effective engine pada.','A/P/U is a broad lexical label. Intrinsic derivatives, semantic pada conditions and tense-specific rules mean a label mismatch is not automatically an input/gold conflict.','Two exact missing-it-accent cases reb/khund are independently confirmed by the prior primary review, not established by this metadata audit. jaBa remains a separate source-identity case.','All1800 selected-context P/A probe unions equal the frozen canonical SLP1 unions; this confirms the diagnostic measures the frozen engine behavior, not its linguistic validity.','755 exact families and1800 inputs were reviewed without response files or accuracy flags. Success cases are included automatically, but no successful-answer count is inferred.','No source-policy change, task removal, spelling adoption or regrading is performed. Further adjudication must be symmetric across outcomes and providers.'],'sources_needed_prioritized':[{'priority':1,'codes':['01.0150','01.0922','01.0923'],'need':'Exact classical lexical identity and placeholder status; do not assume public class creates an independent dictionary entry.'},{'priority':2,'codes':['08.0008'],'need':'Kaumudi2547.2 P allowance for Tanadi vanu yacane vs a cross-gana limitation.'},{'priority':2,'codes':['06.0168','04.0094','04.0095','04.0096','04.0121'],'need':'Accented root reading/anit-vet conditions for the explicit inventory root-accent tag mismatches.'},{'priority':3,'codes':['01.0208'],'need':'Editorial omitted nasal marker for pebr/pevr; current A classifications agree.'}],'families':families,'inputs':{str(p):sha(p)for p in [TASKS,PUBLIC,INV,Path(__file__),Path('misc/vp_cartesian_task.py'),Path('misc/vp_cartesian_prompt_v1.py'),Path('misc/vp_campaign_candidates.py'),Path('finetune/prompts.py'),Path('prompts/v2/vp_task_eval.txt')]},'independent_primary_reference_hashes':{str(OUT/p):sha(OUT/p)for p in source_files},'runtime':{'vidyut_version':getattr(vidyut,'__version__','unknown')},'effects':{'paid_calls':0,'model_outputs_read':False,'ledger_mutated':False,'candidate_modified':False,'grades_modified':False}}
 (OUT/'input-metadata-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 lines=['# Input-only inventory audit','', 'All **755 selected families / 1,800 fixed tasks** were compared against2,259 inventory records, joined uniquely by `baseindex`. No response, outcome, receipt body or score file was opened. The audit does not adopt source truth or change grades.','',f"Code/class matches:755/755. Accent-stripped citations match754/755. Meaning text matches754/755. Inventory citations carry no accent signs at all (0/2,259), so missing accents in its text are not evidence of missing accents in the public prompt.",'',f"There are12 present-probe pada-label differences. The actual selected contexts also show12 families /18 tasks, but the sets differ: śad has a present-only middle condition absent in selected perfect; vṛt gains P specifically in the selected conditional. The union of all metadata flags covers{len(flagged)} families /{sum(f['selected_task_count']for f in flagged)} tasks. These overlapping diagnostics are not a proposed exclusion count.",'','**Known public-entry conflicts:** reb01.0248 and khund01.0946 lack the source-required final it-marker anudatta in the visible citation. Independent primary reviews establish middle-only entries; literal input drives frozen VP P. This audit finds both without using correctness. Jabh01.0150 has the same inventory-A/engine-P pattern but retains separate unresolved lexical/num evidence.','','**Other priority source checks:** śrā01.0922 and jñā01.0923 are explicitly described by the inventory as common references rather than independent roots. Six root-accent tag discrepancies include śrā plus vid06.0168, druh/muh/sṇuh04.0094–96, and puṣ04.0121. Tanadi vanu08.0008 has a Kaumudi2547.2 P branch needing exact scope verification. These are diagnostic leads, not newly certified oracle errors.','','**Differences that must not become blanket holds:** intrinsic āya/optional ṇic and specific pada rules explain most label differences. Ṣasj01.0229 has P in the flat field but its own note explicitly supports both padas. Vṛt has an explicit inventory pada_note allowing P in sya contexts. The lone citation segment difference is omitted candrabindu in inventory pebr01.0208, with A classification agreeing; the lone meaning difference for ruṅ01.1114 is itself recorded as an alternate reading in the inventory note. Vedic tags on03.0017 and05.0033 coexist with already independently reviewed classical exceptions.','','Every family row records visible citation, full matching metadata notes, local accent tests, present and actual selected-context pada probes, exact task IDs/indices/coordinates/prompt hashes, and source work needed. All1,800 probe unions reproduce frozen canonical keys. This is a reproducible metadata diagnostic, not a fresh independent Sanskrit certification.','','| Code | Tasks | Flags | Interpretation |','|---|---:|---|---|']
 for f in flagged:
  explanations=([f['pada_disposition']['classification']]if f['pada_disposition'] else [])+[x['classification']for x in f['other_dispositions']]
  lines.append('| '+f['dhatu']['code']+' | '+str(f['selected_task_count'])+' | '+', '.join(f['diagnostic_flags'])+' | '+('; '.join(explanations)or'needs exact metadata review')+' |')
 lines+=['','Reproduce from repository root:','.venv/bin/python -m '+str(Path(__file__).with_suffix('')).replace('/','.'),'','The script and JSON pin the task, public-prompt, inventory and local interpretation-code hashes. Canonical-success tasks are included by full input enumeration; no outcome was used to identify or prioritize a family.']
 # Long path is executable directly; -m package import is unnecessary.
 lines[-3]='.venv/bin/python '+str(Path(__file__))
 (OUT/'input-metadata-audit.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'counts':result['counts'],'flags':byflag,'json_sha256':sha(OUT/'input-metadata-audit.json')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
