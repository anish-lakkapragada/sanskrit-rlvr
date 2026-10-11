"""Hash-bound finite candidate scorer; unfamiliar usable answers remain reviewable."""
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent
POLICY_SHA='b56b2660ddc23b33e6a55596ed49c37e05d2bc087d098b334e97e2f9187352e3'
TASK_SHA='e7800eb7093a7531dbd92b6965fdbfc90a5260d506b78d698fa586cc7319a1e5'
SOURCE_SHAS={'finetune/prompts.py':'2f474c6a8a14b9445b1686c5f0b63ebf60f8d9fb061e67c6134ccdb4683a4a2e','misc/oai_batch_eval.py':'1472b84916e52676df620b2433f01c956696cde69ad198bf386bb735df5d1525'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class FiniteScorer:
 def __init__(self):
  root=next(p for p in OUT.parents if (p/'finetune/prompts.py').is_file())
  for rel,h in SOURCE_SHAS.items():
   if sha(root/rel)!=h:raise ValueError('Extraction/normalization dependency changed: '+rel)
  from finetune.prompts import extract_answer,slp1_to_devanagari
  from misc.oai_batch_eval import normalize
  if sha(OUT/'alias-policy.json')!=POLICY_SHA or sha(OUT.parent/'tasks.json')!=TASK_SHA:raise ValueError('Policy/task input hash changed')
  policy=json.loads((OUT/'alias-policy.json').read_text());tasks=json.loads((OUT.parent/'tasks.json').read_text())
  if policy['task_count']!=1250 or len(policy['items'])!=1250 or len(tasks)!=1250:raise ValueError('Wrong policy size')
  self._items={};self._extract=extract_answer;self._normalize=normalize
  for t,i in zip(tasks,policy['items']):
   if t['id']!=i['task_id'] or t['id'] in self._items:raise ValueError('Question membership/order changed')
   if t['gold_slp1']!=i['canonical_forms_slp1'] or t['gold_devanagari']!=i['canonical_forms_devanagari']:raise ValueError('Canonical key changed')
   if i['aliases_devanagari']!=[slp1_to_devanagari(x) for x in i['aliases_slp1']]:raise ValueError('Alias transliteration changed')
   self._items[t['id']]=(frozenset(normalize(x) for x in i['canonical_forms_devanagari']),frozenset(normalize(x) for x in i['aliases_devanagari']))
 def grade(self,output_text,task_id):
  if task_id not in self._items:raise ValueError('Unknown task ID')
  canonical,aliases=self._items[task_id];answer=self._extract(output_text);normalized=self._normalize(answer) if answer is not None else None
  recognized=normalized in canonical|aliases
  return {'answer':answer,'canonical_correct':normalized in canonical,'alias_aware_correct':recognized,
   'requires_source_adjudication':answer is not None and not recognized,
   'status':'recognized' if recognized else ('unparsed' if answer is None else 'unrecognized_pending_source_review')}
