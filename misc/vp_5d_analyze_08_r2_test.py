"""Synthetic guard/estimand tests. No provider results are read."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from misc import vp_5d_analyze_08_r2 as a
from misc.vp_cartesian_final_analyze import panel_statistics

class Pilot08Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.ts,cls.ch,cls.sub,cls.ach=a.verify_panel(a.OUT/'pilot-08/revision-02')
 def row(self,t,ok=True,status='completed',answer='fixture',truncated=False):return dict(task=t,is_correct=ok,status=status,answer=answer,truncated=truncated)
 def test_settlement_before_any_result_read(self):
  decl={'expected_jobs':[dict(id=j,n=n,provider=p,tasks_digest='fixture') for j,n,p in a.JOBS]}
  state={'jobs':{x['id']:{**x,'phase':'confirm_64k','settled':True,'collected_at':'fixture'} for x in decl['expected_jobs']}}
  a.verify_settled(state,decl)
  for j,_,_ in a.JOBS:
   bad=deepcopy(state);bad['jobs'][j]['settled']=False
   with self.assertRaises(ValueError):a.verify_settled(bad,decl)
  bad=deepcopy(state);bad['jobs'][a.JOBS[0][0]]['phase']='confirm'
  with self.assertRaises(ValueError):a.verify_settled(bad,decl)
 def test_all8_partitions_and_metadata_required(self):
  chunks=self.ch+self.ach;rs=[[self.row(t) for t in ch] for ch in chunks]
  op,ast=a.verify_results(chunks,rs);self.assertEqual((len(op),len(ast)),(2400,240))
  with self.assertRaises(ValueError):a.verify_results(chunks,rs[:-1])
  bad=deepcopy(rs);bad[-1][0]=bad[-1][1]
  with self.assertRaises(ValueError):a.verify_results(chunks,bad)
  bad=deepcopy(rs);bad[0][0]['task']['gold_slp1']=['tamper']
  with self.assertRaises(ValueError):a.verify_results(chunks,bad)
 def test_zero_completion_family_and_paired_direction(self):
  ts=deepcopy(self.ts[:4])
  for i,t in enumerate(ts):t['campaign']['root_family']='f'+str(i//2);t['dhatu']['gana']='Bhvadi'
  op=[self.row(t) for t in ts];ast=[self.row(ts[0]),self.row(ts[1],False),self.row(ts[2],False,'refused',None),self.row(ts[3],True,truncated=True)]
  z=a.paired(op,ast,1000)
  self.assertEqual(z['differences']['recorded_all_accuracy'],-.5)
  self.assertEqual(z['differences']['completion'],-.5)
  self.assertEqual(z['differences']['usable_accuracy'],-.5)
  self.assertGreater(z['whole_family_bootstrap']['usable_accuracy']['invalid_replicates'],0)
  stats=panel_statistics(ts,ast,repetitions=1000,seed=1)
  self.assertEqual(stats['completed_answer']['n'],2);self.assertEqual(stats['missing_answer_accuracy_bounds'],[.25,.75])
 def test_cost_unknown_cells_not_silently_filled(self):
  ts=deepcopy(self.ts[:2]);rs=[]
  for t in ts:
   r=self.row(t);r['raw_batch_result']={'response':{'body':{'usage':{'input_tokens':100,'output_tokens':200}}}};rs.append(r)
  target={a.cell(t):1 for t in ts};target['desiderative|Imaginary|Kartari']=1
  z=a.costs(rs,'OpenAI',target,100)
  self.assertFalse(z['standardized']['joint']['all_target_cells_supported'])
  self.assertIsNone(z['standardized']['joint']['calibrated_cost_mean'])
  self.assertAlmostEqual(z['total_usage_cost'],.011)
 def test_no_missingness_manufactured_screen(self):
  s=dict(all_results_present=True,unscored_results=0,all_request={'accuracy':.8},completed_answer={'accuracy':.8},missing_answer_accuracy_bounds=[.78,.82])
  self.assertFalse(a.screen(s))

if __name__=='__main__':unittest.main()
