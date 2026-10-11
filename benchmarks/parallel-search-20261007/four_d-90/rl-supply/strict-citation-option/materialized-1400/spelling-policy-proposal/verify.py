"""Offline finite-map reconstruction and scorer checks; no model responses."""
from pathlib import Path
import collections,datetime,hashlib,importlib.util,itertools,json,re,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('candidate_finite_scorer',OUT/'scorer.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
from finetune.prompts import slp1_to_devanagari
scorer=m.FiniteScorer();p=json.loads((OUT/'alias-policy.json').read_text());ts=json.loads((OUT.parent/'tasks.json').read_text());stats=collections.Counter()
v='aAiIuUfFxXeEoO';cons='kKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzsh';deasp=dict(zip('KGCJWQTDPB','kgcjwqtdpb'))
def independent_variants(form):
 edits={}
 if form[-1] in 'ntd':edits[len(form)-1]=form[-1]*2
 for hit in re.finditer('(?=(['+v+'][rh])(['+cons+']))',form):
  pos=hit.start()+2;c=form[pos]
  if c in 'rh':continue
  if c in 'Szs' and pos+1<len(form) and form[pos+1] in v:continue
  edits[pos]=deasp.get(c,c)+c
 for hit in re.finditer('(?<=['+v+'])(?=(['+cons+']{2,}))',form):
  run=hit.group(1);pos=hit.start();c=run[0]
  if len(run)!=2 or c in 'rh' or deasp.get(c,c)==deasp.get(run[1],run[1]):continue
  edits[pos]=deasp.get(c,c)+c
 variants=set()
 for mask in itertools.product((0,1),repeat=len(edits)):
  replacements={i:rep for (i,rep),bit in zip(edits.items(),mask) if bit}
  variants.add(''.join(replacements.get(i,c) for i,c in enumerate(form)))
 return variants
for t,item in zip(ts,p['items']):
 expected=set().union(*(independent_variants(f) for f in t['gold_slp1']))-set(t['gold_slp1'])
 assert expected==set(item['aliases_slp1']),t['id'];stats['exact_reconstructed_task_maps']+=1
 for group in ['canonical_forms_devanagari','aliases_devanagari']:
  for form in item[group]:
   r=scorer.grade('<answer>'+form+'</answer>',t['id']);assert r['alias_aware_correct'] and not r['requires_source_adjudication']
   assert r['canonical_correct']==(group=='canonical_forms_devanagari');stats['accepted_'+group]+=1
 # Structural negative controls: disallowed spelling changes must not be normalized away.
 accepted=set(t['gold_slp1'])|expected
 bad=t['gold_slp1'][0]+'k';assert bad not in accepted
 r=scorer.grade('<answer>'+slp1_to_devanagari(bad)+'</answer>',t['id']);assert not r['alias_aware_correct'] and r['requires_source_adjudication'];stats['unlisted_changes_routed_to_review']+=1
 for f in t['gold_slp1']:
  if f.endswith('n'):
   bad=f[:-1]+'RR'
   if bad not in accepted:
    r=scorer.grade('<answer>'+slp1_to_devanagari(bad)+'</answer>',t['id']);assert not r['alias_aware_correct'] and r['requires_source_adjudication'];stats['final_n_retroflex_mutations_not_accepted']+=1
  if f.endswith(('t','d')):
   bad=f+f[-1]*2
   if bad not in accepted:
    r=scorer.grade('<answer>'+slp1_to_devanagari(bad)+'</answer>',t['id']);assert not r['alias_aware_correct'] and r['requires_source_adjudication'];stats['triple_final_stop_mutations_not_accepted']+=1
try:scorer.grade('<answer>भवति</answer>','unknown-id')
except ValueError:stats['unknown_id_rejected']=1
else:raise AssertionError('Unknown ID accepted')
# A correct form belonging to a different task must not be accepted globally.
foreign=ts[0]['gold_devanagari'][0]
b=next(t for t,i in zip(ts,p['items']) if foreign not in i['canonical_forms_devanagari']+i['aliases_devanagari'])
assert not scorer.grade('<answer>'+foreign+'</answer>',b['id'])['alias_aware_correct'];stats['cross_task_form_not_accepted']=1
report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':True,'statistics':dict(stats),'hashes':{f:hashlib.sha256((OUT/f).read_bytes()).hexdigest() for f in ['alias-policy.json','scorer.py','prepare.py','verify.py','transfer-review.json','controls.json','unresolved-contexts.json']},'not_claimed':'Negative controls test whitelist boundaries, not independent grammatical invalidity of every invented spelling. Unrecognized usable outputs remain pending source review.','paid_calls':0,'model_responses_read':False}
(OUT/'verification-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
