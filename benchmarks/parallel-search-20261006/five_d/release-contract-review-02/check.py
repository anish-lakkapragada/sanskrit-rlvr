"""Development-only export/TRL-interface smoke test; no trainer/model is created."""
import copy,importlib.util,json,hashlib,sys,unittest,tempfile,shutil
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(HERE))
shutil._use_fd_functions=False
from misc.vp_goal_dataset import task_reward,score
from misc.vp_goal_validate import validate,RENDERERS
from misc.vp_cartesian_task import entries_by_code,make_task
from misc import oai_batch_eval as io,vp_goal as runner,ant_batch_eval as ant
from finetune.prompts import render_vp_task
from finetune.rewards.vp import vp_exact as legacy_reward
from contract_bundle import package,verified_records,rows,public_input,sha
calls=[]
def forbid(*a,**k):calls.append('blocked');raise AssertionError('No provider clients or API calls')
runner.client_for=io.api_client=ant.api_client=forbid

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
module('finetune.frozen_cartesian',HERE/'isolated/finetune/frozen_cartesian.py')
recorder_class=module('isolated_contract_callbacks',HERE/'isolated/finetune/callbacks.py').RewardHistoryRecorder
adapter=module('isolated_contract_data',HERE/'isolated/finetune/data.py')
reward=module('isolated_contract_reward',HERE/'isolated/finetune/rewards/cartesian_exact.py').vp_cartesian_exact
TASKS=json.loads((HERE/'development-fixture.json').read_text());MENU=json.loads((HERE/'recipe-menu.json').read_text())
BUNDLE=HERE/'demo-bundle'
if BUNDLE.exists():verified_records(BUNDLE/'manifest.json','development')
else:package(HERE/'development-fixture.json',BUNDLE,MENU)
OBS={}

def benchmark_score(task,text):
 fake={'response':{'status_code':200,'body':{'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':text}]}]}}}
 return int(io.apply_result({'task':task},fake,'offline-fixture')['is_correct'])

class ContractChecks(unittest.TestCase):
 def test_public_assets_have_exact_contract_and_frozen_api_messages(self):
  public,keys=verified_records(BUNDLE/'manifest.json','development')
  self.assertEqual(len(public),4)
  for t,pub,key in zip(TASKS,public,keys):
   self.assertEqual(set(pub),{'id','input','prompt','messages'})
   self.assertEqual(set(pub['input']),{'dhatu','morphology'}|({'sanadi_recipe'} if t['task_type']=='cartesian_5d' else set()))
   self.assertEqual(set(pub['input']['dhatu']),{'aupadeshika','gana','artha'})
   self.assertEqual(set(pub['input']['morphology']),{'lakara','prayoga','purusha','vacana'})
   self.assertEqual(pub['prompt'],RENDERERS[t['prompt_version']](t))
   for provider in runner.PROVIDERS:
    request=runner.request(t,provider,'confirm_64k',0)
    messages=request['params']['messages'] if provider=='Anthropic' else request['body']['input']
    self.assertEqual(messages,pub['messages'])
   mutated=copy.deepcopy(t);mutated.update(id='private-sentinel',gold_devanagari=['private-sentinel'],gold_slp1=['private-sentinel'],campaign={})
   self.assertEqual(RENDERERS[t['prompt_version']](mutated),pub['prompt'])
   self.assertEqual(key['gold_devanagari'],t['gold_devanagari'])
  OBS['public_and_verifier_assets_separate']=True

 def test_every_accepted_alternate_has_exact_binary_reward(self):
  checks=[]
  for t in TASKS:
   self.assertGreater(len(t['gold_devanagari']),1)
   for gold in t['gold_devanagari']:
    completion='<answer>'+gold+'</answer>'
    self.assertEqual(task_reward(completion,t),1)
    self.assertEqual(reward(['unused'],[completion],[t['gold_devanagari']]),[1.0])
    self.assertEqual(benchmark_score(t,completion),1)
    self.assertEqual(task_reward('<answer> '+gold+' \n</answer>',t),1)
    checks.append({'task_id':t['id'],'accepted_form':gold,'reward':1})
  OBS['variant_checks']=checks

 def test_wrong_malformed_conflicting_and_extra_text_match_current_scorer(self):
  t=TASKS[0];g=t['gold_devanagari'];cases={
   'correct_answer_only':('<answer>'+g[0]+'</answer>',1),
   'accepted_alternate':('<answer>'+g[1]+'</answer>',1),
   'wrong_answer':('<answer>UNRELATED</answer>',0),
   'missing_tags':(g[0],0),
   'empty_answer':('<answer> </answer>',0),
   'unclosed_answer':('<answer>'+g[0],0),
   'two_conflicting_answers':('<answer>'+g[0]+'</answer><answer>UNRELATED</answer>',0),
   'two_identical_answers':('<answer>'+g[0]+'</answer>'+'<answer>'+g[0]+'</answer>',0),
   'two_forms_in_one_answer':('<answer>'+','.join(g)+'</answer>',0),
   'extra_text_current_parser_accepts':('outside text <answer>'+g[0]+'</answer>',1),
   'thinking_no_bonus':('<thinking>synthetic</thinking><answer>'+g[0]+'</answer>',1)}
  for label,(text,expected) in cases.items():
   with self.subTest(label=label):
    self.assertEqual(task_reward(text,t),expected)
    self.assertEqual(reward([''],[text],[g]),[float(expected)])
    self.assertEqual(benchmark_score(t,text),expected)
  self.assertEqual(reward([''],[None],[g]),[0.0])
  with self.assertRaisesRegex(ValueError,'alignment'):reward([''],['x'],[])
  OBS['parser_cases']={k:v[1] for k,v in cases.items()}

 def test_legacy_loader_and_reward_are_not_the_new_contract(self):
  t=next(t for t in TASKS if t['task_type']=='cartesian_5d')
  self.assertNotEqual(render_vp_task(t,'v2/vp_task_eval.txt'),RENDERERS[t['prompt_version']](t))
  plain='<answer>'+t['gold_devanagari'][0]+'</answer>'
  old=legacy_reward([''],[plain],[t['gold_devanagari']])[0]
  self.assertEqual(old,.85);self.assertEqual(task_reward(plain,t),1)
  OBS['legacy_correct_answer_only_reward']=old;OBS['new_exact_reward']=1

 def test_native_dataset_only_templates_frozen_messages(self):
  class SpyTokenizer:
   def __init__(self):self.calls=[]
   def apply_chat_template(self,messages,**kw):
    self.calls.append((copy.deepcopy(messages),kw));return 'CHAT:'+json.dumps(messages,ensure_ascii=False)
  tok=SpyTokenizer();dataset=adapter.load_frozen_cartesian_dataset(BUNDLE/'manifest.json',expected_split='development',tokenizer=tok)
  public=rows(BUNDLE/'prompts.jsonl')
  self.assertEqual(set(dataset.column_names),{'prompt','id','gold_devanagari'})
  self.assertEqual(len(dataset),4)
  for i,(messages,kw) in enumerate(tok.calls):
   self.assertEqual(messages,public[i]['messages']);self.assertEqual(kw,{'tokenize':False,'add_generation_prompt':True,'enable_thinking':False})
   self.assertEqual(dataset[i]['prompt'],'CHAT:'+json.dumps(messages,ensure_ascii=False))
  scores=reward(dataset['prompt'],['<answer>'+g[0]+'</answer>' for g in dataset['gold_devanagari']],dataset['gold_devanagari'])
  self.assertEqual(scores,[1]*4)
  OBS['native_dataset_columns']=dataset.column_names;OBS['tokenizer_calls']=len(tok.calls)

 def test_conversational_dataset_and_actual_trl_completion_shape(self):
  from finetune.rewards import get
  self.assertIs(get('vp_cartesian_exact'),reward)
  dataset=adapter.load_frozen_cartesian_dataset(BUNDLE/'manifest.json',expected_split='development')
  public=rows(BUNDLE/'prompts.jsonl')
  completions=[]
  for i,row in enumerate(dataset):
   self.assertEqual(row['prompt'],public[i]['messages'])
   completions.append([{'role':'assistant','content':'<answer>'+row['gold_devanagari'][-1]+'</answer>'}])
  self.assertEqual(reward(dataset['prompt'],completions,dataset['gold_devanagari']),[1]*4)
  g=TASKS[0]['gold_devanagari'];content='<answer>'+g[0]+'</answer>'
  cases={
   'single_assistant_correct':([{'role':'assistant','content':content}],1),
   'single_assistant_wrong':([{'role':'assistant','content':'<answer>UNRELATED</answer>'}],0),
   'single_assistant_conflicting_answers':([{'role':'assistant','content':content+'<answer>UNRELATED</answer>'}],0),
   'user_role':([{'role':'user','content':content}],0),
   'two_assistant_messages':([{'role':'assistant','content':content}]*2,0),
   'user_plus_assistant':([{'role':'user','content':'x'},{'role':'assistant','content':content}],0),
   'missing_role':([{'content':content}],0),
   'content_blocks':([{'role':'assistant','content':[{'type':'text','text':content}]}],0),
   'additional_tool_fields':([{'role':'assistant','content':content,'tool_calls':[]}],0),
   'message_dict_not_list':({'role':'assistant','content':content},0),
   'empty_message_list':([],0)}
  for label,(completion,expected) in cases.items():
   with self.subTest(label=label):self.assertEqual(reward([''],[completion],[g]),[float(expected)])
  OBS['conversational_trl_cases']={k:v[1] for k,v in cases.items()}
  OBS['reward_registry_name']='vp_cartesian_exact'

 def test_actual_training_recorder_preserves_conversational_structure(self):
  g=TASKS[0]['gold_devanagari'];answer='<answer>'+g[0]+'</answer>'
  chat=[{'role':'assistant','content':answer}]
  malformed=[{'role':'user','content':answer}]
  with tempfile.TemporaryDirectory(dir=HERE/'tmp') as directory:
   recorder=recorder_class(reward,Path(directory),preserve_completion_structure=True)
   self.assertEqual(recorder(['']*3,[answer,chat,malformed],gold_devanagari=[g]*3),[1,1,0])
   log=rows(Path(directory)/'reward_history.jsonl')
   self.assertEqual(log[0]['rewards'],[1,1,0])
  # Existing reward behavior remains the default for older configurations.
  with tempfile.TemporaryDirectory(dir=HERE/'tmp') as directory:
   old=recorder_class(legacy_reward,Path(directory))
   self.assertEqual(old([''],[chat],gold_devanagari=[g]),[.85])
  OBS['training_recorder_exact_scores']=[1,1,0]
  OBS['legacy_recorder_default_preserved']=True

 def test_rl_test_separation_survives_metadata_relabeling(self):
  split=json.loads((ROOT/'benchmarks/creation-campaign-20261006/family-split.json').read_text())['families']
  groups={label:{family for family,value in split.items() if value['split']==label} for label in ['rl_train','development','test']}
  self.assertFalse(groups['rl_train'] & groups['test']);self.assertFalse(groups['development'] & groups['test'])
  spoof=copy.deepcopy(TASKS[0]);spoof['campaign']['split']='test'
  with self.assertRaisesRegex(ValueError,'Root-family split'):validate([spoof],'test')
  # Synthetic rejection probe uses real RL identity metadata; no RL/test gold is generated.
  from misc.vp_campaign_candidates import family,name
  e=next(e for e in entries_by_code().values() if family(e) in groups['rl_train'])
  spoof['dhatu']={'code':e.code,'aupadeshika':e.dhatu.aupadeshika,'gana':name(e.dhatu.gana),'artha':e.artha}
  spoof['campaign']['root_family']=family(e)
  with self.assertRaisesRegex(ValueError,'Root-family split'):validate([spoof],'test')
  with self.assertRaisesRegex(ValueError,'split differs'):adapter.load_frozen_rl_training_dataset(BUNDLE/'manifest.json')
  with self.assertRaisesRegex(ValueError,'split differs'):verified_records(BUNDLE/'manifest.json','test')
  OBS['master_family_counts']={k:len(v) for k,v in groups.items()};OBS['rl_to_test_probe']='rejected before gold regeneration'

 def test_finite_menu_is_bound_at_release_package_boundary(self):
  t=next(t for t in TASKS if t['campaign']['construction']=='desiderative');e=entries_by_code()[t['dhatu']['code']]
  other=make_task(e,'development',t['morphology'],'undeclared-menu-value',['san'],prompt_version=t['prompt_version'])
  validate([other],'development') # Generic mechanics intentionally supports wider menus.
  with self.assertRaisesRegex(ValueError,'finite recipe menu'):public_input(other,MENU)
  bad=copy.deepcopy(t);bad['derivation']['sanadi']=['Ric']
  with self.assertRaisesRegex(ValueError,'finite recipe menu'):public_input(bad,MENU)
  nested=next(t for t in TASKS if len(t.get('derivation',{}).get('sanadi',[]))==2)
  reordered=copy.deepcopy(nested);reordered['derivation']['sanadi'].reverse()
  with self.assertRaisesRegex(ValueError,'finite recipe menu'):public_input(reordered,MENU)
  OBS['generic_exporter_menu_binding_required']=True

 def test_tampered_private_key_and_missing_response_are_rejected(self):
  with tempfile.TemporaryDirectory(dir=HERE/'tmp') as tmp:
   cloned=Path(tmp)/'bundle';shutil.copytree(BUNDLE,cloned)
   with (cloned/'private/answer-key.jsonl').open('a') as f:f.write('{}\n')
   with self.assertRaisesRegex(ValueError,'fingerprint'):verified_records(cloned/'manifest.json','development')
  with self.assertRaisesRegex(ValueError,'exactly once'):score(TASKS,[])
  completions=[{'id':t['id'],'completion':'<answer>'+t['gold_devanagari'][0]+'</answer>'} for t in TASKS]
  self.assertEqual(score(TASKS,completions)['accuracy'],1)

if __name__=='__main__':
 suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(ContractChecks),unittest.defaultTestLoader.loadTestsFromName('misc.test_vp_goal_dataset')])
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 snapshot=json.loads((HERE/'source-snapshot.json').read_text());unchanged={p:sha(ROOT/p)==h for p,h in snapshot.items()};assert all(unchanged.values())
 receipt={'at':datetime.now(timezone.utc).isoformat(),'passed':result.wasSuccessful(),'tests':result.testsRun,'errors':len(result.errors),'failures':len(result.failures),'checks':OBS,'source_files_unchanged':unchanged,'api_clients_instantiated':len(calls),'no_training':True,'no_model_outputs_read':True,'fixture_scope':'Four existing development questions; eight accepted gold variants. All completion strings are synthetic.'}
 (HERE/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 if not result.wasSuccessful():sys.exit(1)
