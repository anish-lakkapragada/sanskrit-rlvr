"""Transfer the frozen finite alias rules; no new grammatical rule or model reads."""
from pathlib import Path
import collections,datetime,hashlib,importlib.util,json,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
BASE=ROOT/'benchmarks/parallel-search-20261007/four_d-90';TARGET=BASE/'candidate-1800-v1';SOURCE=BASE/'ending-screen-01';OUT=Path(__file__).resolve().parent
EXPECTED_TASK_SHA='695e7284d06a555aaabfcb7671d000db5622157984221c261b9500e86f72d38f'
EXPECTED_RULE_HELPER_SHA='95aa681cf454a6f71e63acc4fd34ff52ae9b9341a2a9e6c68050c0a073003825'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
if (OUT/'alias-policy.json').exists():raise RuntimeError('Preserve the existing proposal; create a new version to rebuild')
assert sha(TARGET/'tasks.json')==EXPECTED_TASK_SHA
assert sha(SOURCE/'alias_policy.py')==EXPECTED_RULE_HELPER_SHA
s=importlib.util.spec_from_file_location('ending_frozen_alias_rules',SOURCE/'alias_policy.py');rules=importlib.util.module_from_spec(s);s.loader.exec_module(rules)
tasks=json.loads((TARGET/'tasks.json').read_text());oldreview=json.loads((SOURCE/'independent-source-review.json').read_text())
# Reuse the exact frozen builder; replace its panel-specific metadata, not its rules/items.
policy=rules.build(tasks)
policy.update(kind='Candidate1800v2 pre-output task-specific spelling whitelist proposal',task_count=len(tasks),canonical_tasks_sha256=EXPECTED_TASK_SHA,
 status='proposal_not_final_benchmark_freeze',parent_alias_helper_sha256=EXPECTED_RULE_HELPER_SHA,
 parent_alias_policy_sha256=sha(SOURCE/'alias-policy.json'),parent_source_review_sha256=sha(SOURCE/'independent-source-review.json'),
 no_new_grammar_rules=True,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
assert policy['task_count']==len(policy['items'])==1800
byid={i['task_id']:i for i in policy['items']};tm={t['id']:t for t in tasks}
canon_n=sum(len(t['gold_slp1']) for t in tasks);alias_n=sum(len(i['aliases_slp1']) for i in policy['items'])
unknown=[i for i in policy['items'] if i['unresolved_contexts']]
counts={'tasks':1800,'canonical_forms':canon_n,'additional_task_form_aliases':alias_n,'tasks_with_aliases':sum(bool(i['aliases_slp1']) for i in policy['items']),
 'tasks_with_unresolved_contexts':len(unknown),'unresolved_context_occurrences':sum(len(i['unresolved_contexts']) for i in unknown),
 'unresolved_clusters':dict(collections.Counter(u['cluster'] for i in unknown for u in i['unresolved_contexts'])),
 'alias_tasks_by_class':dict(collections.Counter(tm[i['task_id']]['dhatu']['gana'] for i in policy['items'] if i['aliases_slp1'])),
 'alias_tasks_by_tense':dict(collections.Counter(tm[i['task_id']]['morphology']['lakara'] for i in policy['items'] if i['aliases_slp1'])),
 'all_final_ntd_sites_after_vowels':all(len(f)>1 and f[-2] in rules.VOWELS for t in tasks for f in t['gold_slp1'] if f[-1] in 'ntd'),
 'max_independent_original_sites':max(len(rules.sites(f)[0]) for t in tasks for f in t['gold_slp1'])}
# Choose one representative per class and tense, independently of model behavior.
pairs={}
for t in tasks:
 item=byid[t['id']]
 if item['aliases_slp1']:pairs.setdefault((t['dhatu']['gana'],t['morphology']['lakara']),[]).append(t)
classes=sorted({g for g,l in pairs});tenses=sorted({l for g,l in pairs})
def match(index,used,chosen):
 if index==len(classes):return chosen
 g=classes[index]
 for l in tenses:
  if l not in used and (g,l) in pairs:
   result=match(index+1,used|{l},chosen+[(g,l)])
   if result:return result
 return None
selected=match(0,set(),[]);assert selected
controls=[]
def add_control(t,label,alias=None):
 item=byid[t['id']];a=alias or min(item['aliases_slp1'],key=lambda x:(len(x),x));proof=next(e for e in item['evidence'] if e['alias_slp1']==a)
 controls.append({'label':label,'id':t['id'],'code':t['dhatu']['code'],'gana':t['dhatu']['gana'],'morphology':t['morphology'],'canonical_slp1':proof['derivations'][0]['canonical_slp1'],'alias_slp1':a,'canonical_devanagari':rules.slp1_to_devanagari(proof['derivations'][0]['canonical_slp1']),'alias_devanagari':rules.slp1_to_devanagari(a),'proof':proof})
for g,l in selected:
 t=min(pairs[g,l],key=lambda t:(min(map(len,t['gold_slp1'])),t['id']));add_control(t,'Class/tense transfer control')
for label,predicate in [('Aspirate-copy deaspiration',lambda a:a['original'] in rules.DEASP),('Postvocalic r/h',lambda a:a['rule']=='8.4.46'),('Final dental n retained',lambda a:a['original']=='n' and a['condition'].startswith('Word-final'))]:
 found=False
 for item in policy['items']:
  for evidence in item['evidence']:
   if any(predicate(a) for d in evidence['derivations'] for a in d['applications']):add_control(tm[item['task_id']],label,evidence['alias_slp1']);found=True;break
  if found:break
 assert found
write('alias-policy.json',policy)
write('unresolved-contexts.json',[{'id':i['task_id'],'dhatu':tm[i['task_id']]['dhatu'],'morphology':tm[i['task_id']]['morphology'],'contexts':i['unresolved_contexts']} for i in unknown])
write('controls.json',controls)
write('transfer-review.json',{'created_at':policy['created_at'],'bounded_spelling_rule_transfer_passed':True,'execution_authorized':False,'benchmark_ready':False,
 'source_basis':'The same finite phonological conditions are generic across gana/lakara and preserve stem, vowels, consonant place/voicing and ending set. Final n/t/d controls in this candidate all follow vowels. No new phonological closure is inferred.',
 'counts':counts,'source_snapshots':[r for r in oldreview['source_snapshots'] if r['rule'] in {'8.4.46','8.4.47','8.4.49','8.4.50','8.4.51','8.4.53','8.4.55','8.4.56'}],
 'frozen_dependencies':{str(p.relative_to(ROOT)):sha(p) for p in [TARGET/'tasks.json',TARGET/'public-prompts.json',TARGET/'source-policy.json',SOURCE/'alias_policy.py',SOURCE/'alias-policy.json',SOURCE/'independent-source-review.json']},
 'proposal_hashes':{name:sha(OUT/name) for name in ['alias-policy.json','controls.json','unresolved-contexts.json','prepare.py']},
 'mandatory_adjudication':'Every usable answer absent from canonical plus this exact whitelist must receive source adjudication before it contributes to an error claim or benchmark advancement. Preserve raw, canonical-only, predeclared-whitelist and later adjudicated scores separately. Apply established corrections symmetrically across all tasks and models, including already recognized answers where affected. Keep unresolved cases explicit; do not silently drop them.',
 'unresolved_scope':'Existing gemination/cC and original consonant clusters of length >=3 are not exhaustively expanded. Additional classical spelling branches outside the original finite rules are not generated. Lexical variants and complete paradigm validity remain separate reviews.',
 'paid_calls':0,'model_responses_read':False,'canonical_keys_changed':False,'prompts_changed':False})
print(json.dumps(counts,ensure_ascii=False,indent=2));print('policy_sha256',sha(OUT/'alias-policy.json'))
