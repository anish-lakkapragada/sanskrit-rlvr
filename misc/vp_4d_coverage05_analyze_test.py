"""Synthetic-only tests of complete-panel guards and paired missingness arithmetic."""
from copy import deepcopy
import unittest

from misc.vp_4d_coverage05_analyze import (
    OUT, read, verify_panel, verify_results, verify_settled, summarize, digest)


class PairedCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks=read(OUT/'pilot-06.questions.json')
        cls.pairs=read(OUT/'pilot-06.pairs.json')

    def rows(self):
        return [dict(task=t,task_id=t['id'],is_correct=True,status='completed',
                     answer='synthetic fixture',truncated=False) for t in self.tasks]

    def test_incomplete_job_gate(self):
        d=dict(job_id='fixture',provider='Anthropic',phase='confirm_64k',n=96,
               tasks_digest=digest(self.tasks))
        for j in [None,dict(d),dict(d,settled=True),dict(d,settled=True,collected_at='now',n=95)]:
            with self.assertRaises(ValueError):verify_settled({'jobs':{'fixture':j}},d)
        self.assertTrue(verify_settled({'jobs':{'fixture':dict(d,settled=True,collected_at='now')}},d))

    def test_membership_metadata_and_partial_results(self):
        verify_panel(self.tasks,self.pairs)
        rs=self.rows();self.assertEqual(len(verify_results(self.tasks,rs)),96)
        for bad in [rs[:48],rs[:-1]+[rs[0]]]:
            with self.assertRaises(ValueError):verify_results(self.tasks,bad)
        bad=deepcopy(rs);bad[0]['task']['gold_slp1']=['tampered']
        with self.assertRaises(ValueError):verify_results(self.tasks,bad)
        bad=deepcopy(rs);bad[0]['is_correct']=None
        with self.assertRaises(ValueError):verify_results(self.tasks,bad)
        bad=deepcopy(rs);bad[0]['task_id']='wrong'
        with self.assertRaises(ValueError):verify_results(self.tasks,bad)

    def test_mismatched_completion_bounds(self):
        rs=self.rows();rm={r['task']['id']:r for r in rs}
        t=rm[self.pairs[0]['target_id']];t.update(is_correct=False,status='refused',answer=None)
        c=rm[self.pairs[1]['control_id']];c.update(truncated=True)
        z=summarize(rs,self.pairs,repetitions=1000)
        self.assertEqual(z['roles']['target']['correct'],47)
        self.assertEqual(z['roles']['control']['correct'],48)
        self.assertEqual(z['roles']['target']['completed'],47)
        self.assertEqual(z['roles']['control']['completed'],47)
        self.assertEqual(z['paired']['both_completed_pairs'],46)
        self.assertEqual(z['paired']['completion_pattern_counts'],{'0/1':1,'1/0':1,'1/1':46})
        lo,hi=z['paired']['missing_response_difference_bounds']
        self.assertAlmostEqual(lo,-1/48);self.assertAlmostEqual(hi,1/48)
        self.assertAlmostEqual(z['paired']['point_estimates']['all_request'],-1/48)
        self.assertEqual(z['paired']['point_estimates']['usable_ratio'],0)

    def test_family_pair_bootstrap_retains_covariance(self):
        rs=self.rows();rm={r['task']['id']:r for r in rs}
        for p in self.pairs[:10]:
            for k in ['target_id','control_id']:rm[p[k]]['is_correct']=False
        z=summarize(rs,self.pairs,repetitions=1000)
        self.assertEqual(z['paired']['whole_family_bootstrap']['all_request']['percentile95'],[0,0])
        self.assertEqual(z['paired']['whole_family_bootstrap']['usable_ratio']['standard_error'],0)
        self.assertGreater(z['roles']['target']['whole_family_bootstrap']['all_request']['standard_error'],0)

    def test_zero_completion_families_not_dropped(self):
        rs=self.rows()
        for r in rs:r.update(is_correct=False,status='refused',answer=None)
        z=summarize(rs,self.pairs,repetitions=1000)
        self.assertEqual(z['families'],48)
        self.assertIsNone(z['roles']['target']['completed_accuracy'])
        self.assertEqual(z['paired']['missing_response_difference_bounds'],[-1,1])
        self.assertEqual(z['paired']['whole_family_bootstrap']['usable_ratio']['invalid_replicates'],1000)
        self.assertFalse(z['trigger']['all_mechanical_conditions_met'])

    def test_distributed_error_trigger_and_missingness_caution(self):
        rs=self.rows();rm={r['task']['id']:r for r in rs}
        chosen=[]
        for g in sorted({p['gana'] for p in self.pairs}):
            chosen.append(next(p for p in self.pairs if p['gana']==g))
        chosen += [p for p in self.pairs if p not in chosen][:8-len(chosen)]
        for p in chosen:rm[p['target_id']]['is_correct']=False
        z=summarize(rs,self.pairs,repetitions=1000)
        self.assertTrue(z['trigger']['all_mechanical_conditions_met'])
        self.assertEqual(z['trigger']['wrong_completed_target_families'],8)
        for p in self.pairs[:4]:rm[p['control_id']]['is_correct']=False
        # One additional missing control can erase an observed excess of4.
        rm[self.pairs[4]['control_id']].update(is_correct=False,status='refused',answer=None)
        z=summarize(rs,self.pairs,repetitions=1000)
        self.assertTrue(z['trigger']['all_mechanical_conditions_met'])
        self.assertFalse(z['trigger']['missingness_robust'])
        self.assertFalse(z['trigger']['release_advance_authorized'])


if __name__=='__main__':
    unittest.main()
