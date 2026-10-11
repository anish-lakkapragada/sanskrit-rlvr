#!/usr/bin/env python3
"""Source controls for two fresh 4D interactions; offline, no model calls."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,write,now,sha,load_entries
from misc.vp_4d_search03 import status
from misc.vp_cartesian_task import make_task
SK='https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०'
K78='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.3.78.htm'
K79='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.3.79.htm'
LEX='https://jainqq.org/booktext/Dhatupradip/004319'
CONTROLS=[
 ('10.0389','Lat','Prathama','Eka',['kaTayati'],SK,'direct'),
 ('10.0389','Lun','Prathama','Eka',['acakaTat'],SK,'direct'),
 ('10.0391','Lun','Prathama','Eka',['ajIgaRat','ajagaRat'],SK,'direct'),
 ('10.0392','Lat','Prathama','Eka',['SaWayati'],LEX,'direct'),
 ('10.0401','Lat','Prathama','Eka',['pazayati'],SK,'direct'),
 ('10.0407','Lat','Prathama','Eka',['sArayati'],SK,'direct'),
 ('10.0408','Lat','Prathama','Eka',['kfpayati'],SK,'direct'),
 ('10.0409','Lat','Prathama','Eka',['SraTayati'],SK,'direct'),
 ('10.0411','Lun','Prathama','Eka',['abaBAmat'],SK,'direct'),
 ('10.0412','Lat','Prathama','Eka',['sUcayati'],SK,'direct'),
 ('10.0420','Lun','Prathama','Eka',['asasAmat'],SK,'direct'),
 ('10.0424','Lun','Prathama','Eka',['avavAtat'],SK,'direct'),
 ('10.0425','Lun','Prathama','Eka',['ajagavezat'],SK,'direct'),
 ('10.0427','Lun','Prathama','Eka',['aninivAsat'],SK,'direct'),
 ('10.0429','Lat','Prathama','Eka',['saBAjayati'],SK,'direct'),
 ('10.0432','Lat','Prathama','Eka',['kUwayati'],SK,'direct'),
 ('10.0433','Lat','Prathama','Eka',['saNketayati'],SK,'direct'),
 ('10.0435','Lat','Prathama','Eka',['kuRayati'],SK,'direct'),
 ('10.0436','Lat','Prathama','Eka',['guRayati'],SK,'direct'),
 ('10.0441','Lat','Prathama','Eka',['gfhayate'],SK,'direct'),
 ('10.0461','Lat','Prathama','Eka',['vawayati'],LEX,'direct'),
 ('10.0488','Lat','Prathama','Eka',['vasayati'],LEX,'direct'),
 ('01.1108','AshirLin','Madhyama','Bahu',['cyozIQvam'],K78,'direct'),
 ('01.1112','AshirLin','Madhyama','Bahu',['plozIQvam'],K78,'direct'),
 ('01.1108','Lun','Madhyama','Bahu',['acyoQvam'],K78,'direct'),
 ('01.1112','Lun','Madhyama','Bahu',['aploQvam'],K78,'direct'),
 ('08.0010','Lit','Madhyama','Bahu',['cakfQve'],K78,'direct'),
 ('09.0045','Lit','Madhyama','Bahu',['vavfQve'],K78,'same_phonological_root_and_rule'),
 ('09.0016','AshirLin','Madhyama','Bahu',['lavizIQvam','lavizIDvam'],K79,'direct'),
 ('09.0014','AshirLin','Madhyama','Bahu',['pavizIQvam','pavizIDvam'],K79,'direct'),
 ('09.0016','Lun','Madhyama','Bahu',['alaviQvam','alaviDvam'],K79,'direct'),
 ('09.0016','Lit','Madhyama','Bahu',['luluviQve','luluviDve'],K79,'direct'),
 ('02.0038','Lan','Madhyama','Bahu',['astuDvam'],K78,'direct_negative_control'),
]

def main():
 status('Source controls for pilot04','Verifying adanta Curadi vowel treatment and nonpresent dhvam junctions, including licensed alternative spellings and negative controls.')
 es={e.code:e for e in load_entries()};checks=[]
 for code,la,pu,va,expected,url,level in CONTROLS:
  t=make_task(es[code],'source_control',dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va))
  checks.append(dict(code=code,aupadeshika=es[code].dhatu.aupadeshika,artha=es[code].artha,morphology=t['morphology'],expected_slp1=expected,vp_gold_slp1=t['gold_slp1'],source_url=url,evidence_level=level,pass_expected_subset=set(expected)<=set(t['gold_slp1'])))
 issue_t=make_task(es['04.0029'],'source_control',dict(lakara='Lit',prayoga='Kartari',purusha='Madhyama',vacana='Bahu'))
 issue=dict(created_at=now(),predicate={'code':'04.0029','lakara':'Lit','purusha':'Madhyama','vacana':'Bahu','required_trace_rule':'6.4.63'},recommendation='Quarantine this context uniformly, rather than change old raw gold or scores.',source_urls=[K79,'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.63.htm'],source_evidence='Kashika and Nyasa explicitly discuss the yuT-intervening perfect of diN: dental dh is licensed in both analyses; retroflex dh is optional in one. The printed illustration has upa. Removing that prefix is a rule inference: the disputed conditioning is local to yuT, iT and dhvam, not the prefix.',inferred_unprefixed_accepted_slp1=['didIyiDve','didIyiQve'],vp_gold_slp1=issue_t['gold_slp1'],vp_trace_rule_ids=issue_t['campaign']['trace_rule_ids'],missing_dental_confirmed='didIyiDve' not in issue_t['gold_slp1'],historical_development_evidence='One older High4096 error matches the source-licensed dental answer. This motivated checking the rule; the proposed predicate applies to all outcomes and all splits.',full_independent_paradigm_certification=False)
 write(OUT/'search-04.ding-dhvam-variant-audit.json',issue)
 data=dict(created_at=now(),controls=checks,source_controls_passed=sum(c['pass_expected_subset'] for c in checks),total_controls=len(checks),all_passed=all(c['pass_expected_subset'] for c in checks),generator_sha256=sha(__file__),mechanisms=[
  dict(label='adanta_curadi',predicate='Dictionary Curadi citation ending in literal non-nasal a; Kartari. No added sanadi or denominative construction.',source_url=SK,evidence='The classical Curadi section explicitly groups these dictionary entries as adanta. It states that deletion of final a retains conditioning that blocks ordinary vrddhi and san-like reduplication behavior. Representative present and aorist forms above are direct controls. Other persons and nonpresent stems follow explicit general rule inference.'),
  dict(label='nonpresent_dhvam',predicate='Non-Curadi Kartari Madhyama Bahu in Lit, AshirLin or Lun with rule 8.3.78 or 8.3.79; all intrinsic ending choices remain accepted.',source_urls=[K78,K79],evidence='The primary commentaries give both obligatory and optional retroflexion plus its interaction with iT. The hypothesis concerns these junctions and vowel treatment, not a hidden independent pada selection.')],
  local_preselection_exclusions=[
   {'predicate':'04.0029, Lit, Madhyama, Bahu, trace 6.4.63','reason':'Source-licensed dental alternative is missing from VP.'},
   {'predicate':'10.0400','reason':'Primary source reports competing adanta/non-adanta and nic analyses; this pilot does not certify their full variant union.'},
   {'predicate':'10.0490 or 10.0492','reason':'Exact late lexical readings have not been verified in this bounded source audit.'},
   {'predicate':'10.0412 AND Lun','reason':'The Siddhantakaumudi transcription prints asUsucat while VP and a distinct classical lexicon print asusUcat. Excluded from the fresh pilot pending reconciliation; not a confirmed oracle defect.'},
   {'predicate':'04.0137','reason':'Prior pilot03 exact dental citation remains unresolved.'},
   {'predicate':'02.0071 through 02.0075; 05.0013 through 05.0015','reason':'Sources disagree about classical/Vedic scope; avoid using unresolved entries as new hardness evidence. This is a pilot-local precaution, not a proposed blanket exclusion.'}],
  limits=['Representative direct controls and general rule inference do not independently certify every complete paradigm.','The selected mechanisms have only weak-setting historical development motivation; xHigh target difficulty remains unknown.','No held-out model answers are loaded. Source controls can use any split solely for grammar validation.','The final benchmark cannot inherit this pilot concentration without meeting the requested broader diversity.'])
 write(OUT/'pilot-04.source-audit.json',data)
 print({'passed':data['source_controls_passed'],'total':len(checks)})
 for c in checks:
  if not c['pass_expected_subset']:print(c)
 if not data['all_passed']:raise SystemExit(1)

if __name__=='__main__':main()
