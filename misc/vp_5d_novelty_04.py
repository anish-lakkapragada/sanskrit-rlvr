"""Compare input-only normalized finite tuples across both campaign ledgers."""
import json
from collections import Counter,defaultdict
from pathlib import Path
from misc.vp_5d_pilot import OUT,atomic_json,now,sha

ROOT=Path(__file__).resolve().parents[1]
FIELDS=['lakara','prayoga','purusha','vacana']

def normalized(t):
    d=t.get('derivation') or {};m=t.get('morphology') or {};h=t.get('dhatu') or {}
    if d.get('prefixes') or h.get('prefixes') or t.get('prefixes'):return None,'prefixes'
    if any(obj.get(k) not in (None,'',[]) for obj in [d,m,h,t] for k in ['dhatu_pada','pada']):return None,'specified_pada'
    if not all(m.get(k) for k in FIELDS) or not h.get('aupadeshika') or not h.get('gana'):return None,'nonmatching_shape'
    return (h['aupadeshika'],h['gana'],tuple(d.get('sanadi') or []),*(m[k] for k in FIELDS)),None

def walk(t,inherit=None):
    if not isinstance(t,dict):return
    # Historical bundle/paradigm rows carry their own complete finite grammar.
    yield t
    for child in t.get('forms') or []:yield from walk(child,t)

def main():
    seen=defaultdict(list);historyfamilies=set();counts=Counter();files=[];ledgers=[]
    for directory in ['creation-campaign-20261006','iterative-goal-20261006']:
        ledger=ROOT/'benchmarks'/directory/'ledger.json';data=json.loads(ledger.read_text());ledgers.append({'path':str(ledger),'sha256':sha(ledger)})
        for label,job in data['jobs'].items():
            path=ledger.parent/'jobs'/label/'tasks.json'
            if not path.exists():raise RuntimeError('Missing immutable ledger task input: '+str(path))
            tasks=json.loads(path.read_text());files.append({'path':str(path),'sha256':sha(path),'top_level_tasks':len(tasks)})
            for t in tasks:
                for row in walk(t):
                    counts['all_task_or_component_records']+=1
                    family=row.get('campaign',{}).get('root_family')
                    if family:historyfamilies.add(family)
                    sig,issue=normalized(row)
                    if issue:counts[issue]+=1;continue
                    counts['matching_shape_records']+=1
                    seen[sig].append({'job':label,'id':row.get('id'),'source':str(path),'split':row.get('campaign',{}).get('split')})
    current=json.loads((OUT/'pilot-04.provisional.tasks.json').read_text());overlap=[]
    for t in current:
        sig,issue=normalized(t);assert not issue
        if sig in seen:overlap.append({'id':t['id'],'history':seen[sig]})
    fams={t['campaign']['root_family'] for t in current}
    report={'created_at':now(),'scope':'Every immutable task input in both campaign ledgers, recursively including forms in bundles/paradigms. No result or model answer files read.',
      'normalization':'Same visible aupadeshika and gana, no prefix in task/root/derivation, no explicitly specified pada anywhere, identical ordered sanadi operations and lakara/prayoga/purusha/vacana. Task IDs and prompt versions ignored.',
      'ledgers':ledgers,'input_files':files,'counts':dict(counts),'unique_matching_historical_tuples':len(seen),
      'provisional_task_sha256':sha(OUT/'pilot-04.provisional.tasks.json'),'provisional_questions':len(current),'overlap_count':len(overlap),'overlaps':overlap,
      'families_absent_from_all_historical_task_inputs':len(fams-historyfamilies),'families_present_in_any_historical_task_inputs':len(fams&historyfamilies),
      'prior_manifest_novelty_limit':'The154 new and86 reused family counts refer only to earlier named5D pilots; all-history family exposure is separately reported here.',
      'selection_uses_model_errors':False,'heldout_model_answers_read':False,'paid_calls':0}
    atomic_json(OUT/'pilot-04.novelty-audit.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['input_files','ledgers']},indent=2))

if __name__=='__main__':main()
