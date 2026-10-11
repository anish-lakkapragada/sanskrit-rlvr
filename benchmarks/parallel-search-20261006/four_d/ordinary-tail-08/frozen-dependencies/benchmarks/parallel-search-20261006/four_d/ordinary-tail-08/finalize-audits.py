"""Additive input-only receipts; no result files or network calls."""
import hashlib,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from misc.vp_4d_coverage05 import key
ROOT=Path.cwd();OUT=ROOT/'benchmarks/parallel-search-20261006/four_d/ordinary-tail-08'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,x):
 p=OUT/n;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def fam(t):return t['dhatu']['aupadeshika']+'|'+t['dhatu']['gana']
def ordinary(t):
 if not isinstance(t,dict) or 'dhatu' not in t or set(t.get('morphology',{}))!={'lakara','prayoga','purusha','vacana'}:return False
 d=t.get('derivation')or{}
 return not(d.get('sanadi')or d.get('prefixes')) and not any(o.get(k)not in(None,'',[])for o in[t,t['dhatu'],t['morphology']]for k in['prefixes','sanadi','pada','dhatu_pada'])
inv=read(OUT/'inventory.json');ts=read(OUT/'panel.questions.json');tk={key(t)for t in ts};tf={fam(t)for t in ts}
assert len(tk)==len(tf)==96
hkeys=set();hfamilies=set();ordinary_n=0
for s in inv['history_sources']:
 p=ROOT/s['path'];assert sha(p)==s['sha256']
 for top in read(p):
  for t in top.get('forms',[top]):
   if ordinary(t):hkeys.add(key(t));hfamilies.add(fam(t));ordinary_n+=1
prior=set();rules=set()
for s in inv['current_sources']:
 for t in read(ROOT/s['path']):
  prior.add(fam(t));rules.update(t['campaign']['trace_rule_ids'])
pending=read(ROOT/'benchmarks/parallel-search-20261006/four_d/coverage-gap-06/cin-candidate-inputs.json')
pf={fam(t)for t in pending}
assert not(tk&hkeys or tf&prior or tf&pf)
write('novelty-audit.json',dict(created_at=datetime.now(timezone.utc).isoformat(),
 tasks_sha256=sha(OUT/'panel.questions.json'),history_file_count=len(inv['history_sources']),ordinary_historical_rows=ordinary_n,
 exact_visible_input_overlap=0,current_six_raw_family_overlap=0,pending_cin_family_overlap=0,
 panel_families_with_older_ordinary_input_exposure=len(tf&hfamilies),
 history_sources=inv['history_sources'],current_sources=inv['current_sources'],
 pending_inputs_sha256=sha(ROOT/'benchmarks/parallel-search-20261006/four_d/coverage-gap-06/cin-candidate-inputs.json'),
 comparison='Exact visible citation + class + four coordinates. Ordinary and zero-operation records only; no result files read. Current family exclusion uses every raw prior-panel input, not only policy-eligible rows.',
 limitation='Two saved campaign job directories plus original 6687 inputs; not a proof of global nonexposure. Every selected family has older ordinary input exposure.',no_model_answers_read=True))
new_rules=sorted(set().union(*(set(t['campaign']['trace_rule_ids'])for t in ts))-rules)
new_contexts=[dict(id=t['id'],code=t['dhatu']['code'],new_rule_ids=sorted(set(t['campaign']['trace_rule_ids'])-rules))for t in ts if set(t['campaign']['trace_rule_ids'])-rules]
url=lambda n:'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'+n.split('.')[0]+'/'+n+'.htm'
sk='https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०'
controls=[]
for code in ['01.1166','04.0080','10.0372','09.0060','02.0019','02.0016','02.0054','09.0038','09.0040']:
 for t in ts:
  if t['dhatu']['code']==code:controls.append(dict(id=t['id'],dhatu=t['dhatu'],morphology=t['morphology'],gold_slp1=t['gold_slp1'],trace_rule_ids=t['campaign']['trace_rule_ids']))
write('source-audit.json',dict(created_at=datetime.now(timezone.utc).isoformat(),policy='oracle-policy-21',tasks_sha256=sha(OUT/'panel.questions.json'),
 full_trace_paths='panel-source-paths.json',full_trace_sha256=sha(OUT/'panel-source-paths.json'),
 all96_regenerate=True,all96_full_explicit_pada_union_matches=True,multiple_form_questions=28,
 new_rule_ids_vs_six_raw_panels=new_rules,new_rule_contexts=new_contexts,
 primary_checks=[
 dict(context='01.1166 fti, Lrt Madhyama Dvi',sources=[url('3.1.29'),url('3.1.31')],
 conclusion='The instructional consonant-final rt base has intrinsic iyang in the stated disgust/compassion senses; the formation is optional before ardhadhatuka. Commentary prints both future stems. artizyaTaH and ftIyizyeTe are ordinary second-dual ending inferences, not separately printed exact forms. Retain both; no independently chosen derivation or pada.'),
 dict(context='04.0080 Suza, Lun Prathama Dvi',sources=[url('3.1.55')],
 conclusion='Divadi pusadi takes ang before parasmaipada endings. The commentary includes sus and distinguishes other-class homonyms. aSuzatAm uses this stem rule and ordinary third-dual ending; full accepted union retained.'),
 dict(context='10.0372 DUY, VidhiLin Uttama Dvi',sources=[sk],
 conclusion='Siddhantakaumudi Curadi entry1836 and the adhRsad va group support optional intrinsic nic and the dhunaya/dhavaya/dhava stem alternatives. The six returned dual-optative forms apply ordinary endings and both permitted padas to these variants. They remain accepted, not selectively scored.'),
 dict(context='09.0060 u~Drasa, Lan Madhyama Eka',sources=[sk],
 conclusion='Siddhantakaumudi entry1525 explicitly supports u as it and the dhrasna stem, while recording a different reading where u belongs to the root. The supplied nasal-marked u~ chooses the marker reading visibly. The unmarked lexical reading is not an extra hidden prefix or an independent allowed input choice.'),
 dict(context='02.0016 kaSa and 02.0019 Siji',sources=['https://jainqq.org/explore/002377/476/'],
 conclusion='The primary Adadi inventory records kash as a reading alongside kasi/kasa, and shiji avyakte shabde in the middle-voice section. Exact personal endings are rule inferences.'),
 dict(context='Broad ending-region inventory',sources=[url(n)for n in['7.4.50','7.4.52','3.4.105','3.4.106','3.4.108','3.4.109']],
 conclusion='Sources support tas/as ending changes, ling middle/third-plural replacements and sic-related third-plural jus. Rule3.4.106 concerns the it personal ending, not the it augment. These are established grammar, sparsely sampled at current effort, not newly discovered rules.')],
 representative_controls=controls,
 local_primary_sources=[dict(path=p,sha256=sha(ROOT/p))for p in['benchmarks/parallel-search-20261006/four_d/source-02/dhatupatha.txt','benchmarks/parallel-search-20261006/four_d/source-03/dhatupradipa-clean.txt']],
 source_blockers_found=[],
 scope='Proportionate direct checks of new contexts, visible citation interpretation and optional stem/pada unions, plus full engine regeneration. Not a claim that all96 exact paradigms are printed independently or that any automated oracle is infallible.',
 accepted_variant_policy='Accept any member of the full regenerated ordinary union. No chosen pada; no prefixes, added sanadi operations or dialect switch. Intrinsic class morphology remains part of ordinary dictionary conjugation.',
 comparator_note='Rule novelty is against six current panels only; older historical grammar coverage is separately disclosed.',
 no_model_answers_read=True,no_paid_calls=True,benchmark_ready=False))
print(json.dumps(dict(history_files=len(inv['history_sources']),ordinary_rows=ordinary_n,older_family_exposure=len(tf&hfamilies),new_rules=new_rules),indent=2))
