"""Offline complete-panel and pairing checks using synthetic answers, no provider calls."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from misc import vp_goal as r,oai_batch_eval as io,vp_simple_search_fast_analyze as a
class Checks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.out=self.base/'acceleration';self.out.mkdir()
  self.s={'jobs':{}};self.taskmap={};self.plan={'sources':{},'stages':[]};self.rows={}
  paths={'four_d':'four_d-90/tasks.json','modification':'modification-01/tasks.json','control':'modification-01/controls.json'}
  for arm,path in paths.items():
   ts=io.read_json(ROOT/'benchmarks/parallel-search-20261007'/path);original='original-'+arm
   self.s['jobs'][original]={'id':original};self.taskmap[original]=ts;self.plan['sources'][arm]={'job':original,'tasks_digest':r.digest(ts)}
   for start in range(0,200,40):
    name=arm+str(start);chunk=ts[start:start+40];self.taskmap[name]=chunk
    self.plan['stages'].append({'id':name,'arm':arm,'start':start,'stop':start+40,'n':40})
    self.s['jobs'][name]={'id':name,'provider':'Anthropic','phase':'confirm_64k','transport':'direct','settled':True,'collected_at':'synthetic','n':40,'actual_cost_upper_micro':1,'reservation_micro':52668800}
    wrong={'four_d':20,'modification':40,'control':2}[arm]
    rows=[{'task':copy.deepcopy(t),'is_correct':start+i>=wrong,'status':'completed','answer':'synthetic','truncated':False} for i,t in enumerate(chunk)]
    p=self.base/'jobs'/name/'results.json';p.parent.mkdir(parents=True);io.atomic_json(p,rows);self.rows[name]=p
  io.atomic_json(self.out/'plan.json',self.plan)
  (self.base/'source-sensitivity-predeclaration.json').write_bytes((ROOT/'benchmarks/parallel-search-20261007/source-sensitivity-predeclaration.json').read_bytes())
 def tearDown(self):self.tmp.cleanup()
 def run_analysis(self):
  with patch.object(a,'OUT',self.out),patch.object(r,'OUT',self.base),patch.object(r,'load',return_value=self.s),patch.object(r,'verify_job',side_effect=lambda j:(self.taskmap[j['id']],[])):
   return a.analyze()
 def test_complete_counts_pairing_and_symmetric_hold(self):
  x=self.run_analysis();self.assertEqual(x['tracks']['four_d']['primary']['statistics']['all_request']['correct'],180)
  self.assertEqual(x['tracks']['modification']['primary']['statistics']['all_request']['correct'],160)
  self.assertEqual(x['tracks']['modification']['control']['statistics']['all_request']['correct'],198)
  self.assertAlmostEqual(x['tracks']['modification']['paired']['all_request_accuracy_difference'],-.19)
  self.assertEqual(x['source_sensitivity']['paired']['n_pairs'],199);self.assertEqual(x['acceleration']['settled_requests'],600)
 def test_incomplete_control_withholds_both_modification_scores(self):
  self.s['jobs']['control160']['settled']=False
  x=self.run_analysis();self.assertNotIn('primary',x['tracks']['modification']);self.assertNotIn('paired',x['tracks']['modification']);self.assertEqual(x['tracks']['four_d']['state'],'complete_pending_source_review')
 def test_mutated_gold_cannot_be_scored(self):
  p=self.rows['four_d0'];rows=io.read_json(p);rows[0]['task']['gold_devanagari']=['wrong'];io.atomic_json(p,rows)
  with self.assertRaisesRegex(ValueError,'changed final question'):self.run_analysis()
 def test_mixed_transport_rejected(self):
  self.s['jobs']['control0']['transport']='batch'
  with self.assertRaisesRegex(ValueError,'Changed direct protocol'):self.run_analysis()
if __name__=='__main__':unittest.main(verbosity=2)
