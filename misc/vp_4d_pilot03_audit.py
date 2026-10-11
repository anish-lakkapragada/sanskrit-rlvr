#!/usr/bin/env python3
"""Proportionate primary-source controls for fresh pilot03; never reads answers."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,write,now,sha,load_entries
from misc.vp_4d_search03 import status
from misc.vp_cartesian_task import make_task
BASE='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
LEX='https://jainqq.org/booktext/Dhatupradip/004319'
CONTROLS=[
 ('01.0015','Lat','Prathama','Eka',['klindate'],['7.1.58','1.3.12'], 'direct'),
 ('01.0076','Lat','Prathama','Eka',['klindati'],[LEX,'1.3.78'],'direct'),
 ('01.0015','Lit','Prathama','Eka',['ciklinde'],[LEX],'direct'),
 ('01.0076','Lit','Prathama','Eka',['ciklinda'],[LEX],'direct'),
 ('01.0136','Lat','Prathama','Eka',['oKati'],[LEX],'direct'),
 ('01.0137','Lat','Prathama','Eka',['uNKati'],[LEX,'7.1.58'],'lexical_entry_plus_rule'),
 ('01.0148','Lat','Prathama','Eka',['eKati'],[LEX,'7.3.86'],'lexical_entry_plus_rule'),
 ('01.0149','Lat','Prathama','Eka',['iNKati'],[LEX,'7.1.58'],'lexical_entry_plus_rule'),
 ('01.1136','Lit','Prathama','Dvi',['nematuH'],['6.4.120'],'direct'),
 ('01.1136','Lit','Madhyama','Eka',['nemiTa'],['6.4.121'],'direct'),
 ('04.0100','Lit','Prathama','Dvi',['dematuH'],['6.4.120'],'direct'),
 ('01.0608','Lit','Prathama','Dvi',['PelatuH'],['6.4.122'],'direct'),
 ('01.1153','Lit','Prathama','Dvi',['BejatuH'],['6.4.122'],'direct'),
 ('01.0955','Lit','Prathama','Dvi',['PeRatuH','paPaRatuH'],['6.4.125'],'direct'),
 ('01.0017','Lit','Prathama','Eka',['dadade'],['6.4.126'],'direct'),
 ('01.0984','Lit','Prathama','Dvi',['vavamatuH'],['6.4.126'],'direct'),
 ('09.0016','Lit','Madhyama','Eka',['lulaviTa'],['6.4.126'],'direct'),
 ('09.0014','Lit','Madhyama','Eka',['pupaviTa'],['6.4.126'],'direct'),
 ('01.0545','Lut','Prathama','Eka',['kramitA'],['7.2.36'],'rule_inference_unprefixed_control'),
 ('09.0071','Lut','Prathama','Eka',['grahItA'],['7.2.37'],'direct'),
 ('01.1124','Lut','Prathama','Eka',['taritA','tarItA'],['7.2.38'],'direct'),
 ('09.0045','Lut','Prathama','Eka',['varitA','varItA'],['7.2.38'],'direct'),
 ('04.0092','Lut','Prathama','Eka',['traptA','tarptA','tarpitA'],['7.2.45'],'direct'),
 ('04.0093','Lut','Prathama','Eka',['draptA','darptA','darpitA'],['7.2.45'],'direct'),
 ('01.0988','Lut','Prathama','Eka',['soQA','sahitA'],['7.2.48'],'direct'),
 ('04.0010','Lrt','Prathama','Eka',['nartizyati','nartsyati'],['7.2.57'],'direct'),
 ('04.0010','Lrn','Prathama','Eka',['anartizyat','anartsyat'],['7.2.57'],'direct'),
 ('07.0008','Lrt','Prathama','Eka',['Cardizyati','Cartsyati'],['7.2.57'],'direct'),
 ('07.0009','Lrt','Prathama','Eka',['tardizyati','tartsyati'],['7.2.57'],'direct'),
 ('01.0863','Lrt','Prathama','Eka',['vartsyati','varDizyate'],['7.2.59'],'direct'),
 ('01.1014','Lrt','Prathama','Eka',['Sartsyati','SarDizyate'],['7.2.59'],'direct'),
 ('01.0866','Lrt','Prathama','Eka',['kalpsyati','kalpizyate','kalpsyate'],['7.2.44','7.2.60'],'direct'),
 ('01.0866','Lut','Madhyama','Eka',['kalptAsi','kalpitAse','kalptAse'],['7.2.44','7.2.60'],'direct'),
 ('08.0010','Lrt','Prathama','Eka',['karizyati'],['7.2.70'],'direct'),
 ('01.1046','Lrt','Prathama','Eka',['harizyati'],['7.2.70'],'direct'),
]
def source(x):
 if x.startswith('https:'):return x
 if x=='7.2.45':return 'https://ashtadhyayi.github.io/suutra/7.2/7.2.45/'
 return BASE+x[0]+'/'+x+'.htm'
def main():
 status('Primary control verification','Comparing independently read forms and explicit rule inferences against VP before pilot03 selection; preserving every licensed variant.')
 es={e.code:e for e in load_entries()};checks=[]
 for code,la,pu,va,expected,sources,level in CONTROLS:
  t=make_task(es[code],'source_control',dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va))
  checks.append(dict(code=code,aupadeshika=es[code].dhatu.aupadeshika,artha=es[code].artha,morphology=t['morphology'],expected_slp1=expected,vp_gold_slp1=t['gold_slp1'],source_urls=list(map(source,sources)),evidence_level=level,pass_expected_subset=set(expected)<=set(t['gold_slp1'])))
 data=dict(created_at=now(),controls=checks,source_controls_passed=sum(c['pass_expected_subset'] for c in checks),total_controls=len(checks),all_passed=all(c['pass_expected_subset'] for c in checks),generator_sha256=sha(__file__),mechanisms=[
 dict(label='same_gana_marker_contrast',predicate='Same gana and same phonemic root after lexical it deletion, but different full citation strings; source-safe dictionary entries only.',rationale='Different it vowels and accent positions license nasal insertion or ending selection. The prompt retains those visible distinctions. The metadata grouping does not compare generated surface answers.',source_urls=list(map(source,['7.1.58','1.3.12','1.3.78',LEX]))),
 dict(label='weak_perfect_alternation',predicate='Non-Curadi Kartari Lit traces include6.4.120/121/122/125 or prohibition6.4.126; no6.4.123.',rationale='A fixed positive/prohibition quota probes conditioned e substitution and reduplication deletion, including it-bearing2sg behavior and genuine exceptions. Some prohibition traces involve a derived guna vowel rather than a visually simple CVC base; report these separately.',source_urls=list(map(source,['6.4.120','6.4.121','6.4.122','6.4.125','6.4.126']))),
 dict(label='special_it_nonpresent',predicate='Non-Curadi Kartari Lut/Lrt/Lrn with at least one of7.2.36/37/38/44/45/48/57/59/60/70.',rationale='Root or marker-conditioned obligatory/optional/prohibited it may interact with endings and internal consonant sandhi. Optional branches remain accepted; lack of an independent pada coordinate is preserved.',source_urls=list(map(source,['7.2.36','7.2.37','7.2.38','7.2.44','7.2.45','7.2.48','7.2.57','7.2.59','7.2.60','7.2.70'])))],
 pre_freeze_control_corrections=['Initial manual draft wrote uKati/iKati and omitted guna. Re-reading Dhatupradipa printed page18 confirms oKati; eKati follows7.3.86. This was a researcher transcription/inference error, not an oracle defect. Corrected before question selection.'],limits=['Representative primary controls plus explicit rule inference, not full independent certification of every paradigm.','Source controls may use dictionary families from any split solely to validate grammar; none loads held-out model answers or chooses panel membership by failure.','The source lexicon has OCR noise. The uKh/iKh idit pair uses explicit lexical readings and general num inference; no OCR-string match is represented as printed exact-form proof.','The grammatical supply does not establish model difficulty. All three mechanisms remain hypotheses.','No Vedic entries in the new shared policy04 may enter pilot03. Classical status of the entire dictionary is not certified by this audit.'])
 write(OUT/'pilot-03.source-audit.json',data)
 print({'pass':data['source_controls_passed'],'total':len(checks)})
 for c in checks:
  if not c['pass_expected_subset']:print(c)
 if not data['all_passed']:raise SystemExit(1)
if __name__=='__main__':main()
