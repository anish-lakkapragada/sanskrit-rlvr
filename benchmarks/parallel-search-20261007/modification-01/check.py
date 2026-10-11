"""Bounded offline paired contract/collision regressions; no model calls."""
from pathlib import Path
import sys,json,copy,hashlib,unittest
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from misc import vp_modification_task_v1 as mod
from misc.vp_modification_prompt_v1 import render
from misc.vp_goal_dataset import exact_reward
HERE=Path(__file__).resolve().parent
TASKS=json.loads((HERE/'tasks.json').read_text());CONTROLS=json.loads((HERE/'controls.json').read_text());INDEX=json.loads((HERE/'inverse-index.json').read_text())
class Checks(unittest.TestCase):
 def test_full_regeneration_and_exact_pair(self):
  for t,c in zip(TASKS,CONTROLS):
   self.assertTrue(mod.validate_task(t,'development'));self.assertEqual(t['gold_devanagari'],c['gold_devanagari']);self.assertEqual(t['gold_slp1'],c['gold_slp1']);self.assertEqual(t['campaign']['control_task_id'],c['id'])
 def test_public_only_renderer_and_source_surface(self):
  for t in TASKS:
   p={k:t[k] for k in ['source_form_devanagari','source_morphology','target_morphology']};self.assertEqual(render(t),render(p));self.assertNotIn(t['source_form_devanagari'],t['gold_devanagari'])
   q=copy.deepcopy(t);q.update(dhatu={'secret':'HIDDEN'},gold_devanagari=['HIDDEN'],campaign={'secret':'HIDDEN'},morphology={'secret':'HIDDEN'});self.assertEqual(render(q),render(t))
 def test_exact_distribution(self):
  self.assertEqual(len(TASKS),200);self.assertEqual(len({t['campaign']['root_family'] for t in TASKS}),200)
  self.assertEqual(set(Counter(t['target_morphology']['lakara'] for t in TASKS).values()),{20})
  self.assertEqual(Counter(t['source_morphology']['lakara'] for t in TASKS),dict.fromkeys(['Lat','Lit','Lan','Lun'],50))
  for t in TASKS:
   self.assertNotEqual(t['source_morphology']['lakara'],t['target_morphology']['lakara'])
   self.assertEqual({k:v for k,v in t['source_morphology'].items() if k!='lakara'},{k:v for k,v in t['target_morphology'].items() if k!='lakara'})
 def test_gold_and_split_tampering_rejected(self):
  t=copy.deepcopy(TASKS[0]);t['gold_devanagari']=['असत्यम्']
  with self.assertRaisesRegex(ValueError,'Full target union'):mod.validate_task(t,'development')
  t=copy.deepcopy(TASKS[0]);t['campaign']['split']='test'
  with self.assertRaisesRegex(ValueError,'Root-family split'):mod.validate_task(t,'test')
 def test_held_shadow_collision_rejected(self):
  found=None
  for p in INDEX['profiles']:
   for word,codes in p['keys'].items():
    if p['shadow_all_dictionary_keys'].get(word)!=codes:found=p,word,codes;break
   if found:break
  self.assertIsNotNone(found);p,word,codes=found;t=copy.deepcopy(TASKS[0]);t['source_morphology']=p['morphology'];t['source_form_devanagari']=word;t['target_morphology']=dict(p['morphology'],lakara='Lrt');t['modification_audit']['candidate_codes']=codes
  with self.assertRaisesRegex(ValueError,'Excluded or uncertain colliding'):mod.validate_task(t,'development')
 def test_full_accepted_union_binary_reward(self):
  for t in TASKS:
   for g in t['gold_devanagari']:self.assertEqual(exact_reward('<answer>'+g+'</answer>',t['gold_devanagari']),1)
   self.assertEqual(exact_reward('<answer>असत्यम्</answer>',t['gold_devanagari']),0)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
 receipt=dict(passed=result.wasSuccessful(),tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),paid_calls=0,model_outputs_read=False,tasks_sha256=mod.sha(HERE/'tasks.json'),controls_sha256=mod.sha(HERE/'controls.json'),accepted_target_forms_checked=sum(len(t['gold_devanagari']) for t in TASKS))
 (HERE/'test-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 if not result.wasSuccessful():raise SystemExit(1)
