"""Unpaid synthetic tests of the fixed pilot07 aggregate guard and estimands."""
from copy import deepcopy
import math
import unittest
from misc.vp_5d_analyze_07 import verify_panel, verify_results, screen, OUT
from misc.vp_cartesian_final_analyze import panel_statistics

class Pilot07Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks,cls.chunks,_=verify_panel(OUT/'pilot-07')

    def row(self,t,*,ok=True,status='completed',answer='synthetic fixture',truncated=False):
        return dict(task=t,is_correct=ok,status=status,answer=answer,truncated=truncated)

    def test_partial_chunk_cannot_produce_analysis(self):
        rows=[[self.row(t) for t in self.chunks[0]]]
        with self.assertRaises(ValueError):verify_results(self.chunks,rows)

    def test_changed_gold_and_duplicate_are_rejected(self):
        rows=[[self.row(t) for t in chunk] for chunk in self.chunks]
        changed=deepcopy(rows);changed[0][0]['task']['campaign']['synthetic_tamper']=True
        with self.assertRaises(ValueError):verify_results(self.chunks,changed)
        duplicate=deepcopy(rows);duplicate[1][0]=duplicate[1][1]
        with self.assertRaises(ValueError):verify_results(self.chunks,duplicate)
        self.assertEqual(len(verify_results(self.chunks,rows)),2400)

    def test_zero_completion_family_and_truncated_correct(self):
        # Independent arithmetic example: three families with two requests each.
        ts=[]
        for i in range(6):
            t=deepcopy(self.tasks[i]);t['id']=f'fixture-{i}'
            t['campaign']['root_family']=f'family-{i//2}';t['dhatu']['gana']='Bhvadi';ts.append(t)
        rs=[self.row(ts[0]),self.row(ts[1],ok=False),
            self.row(ts[2],ok=False,status='refused',answer=None),
            self.row(ts[3],ok=True,truncated=True),
            self.row(ts[4]),self.row(ts[5],answer=None)]
        st=panel_statistics(ts,rs,repetitions=1000,seed=17)
        self.assertEqual(st['root_families'],3)
        self.assertEqual(st['all_request']['correct'],4)
        self.assertEqual(st['completed_answer']['n'],3)
        self.assertEqual(st['completed_answer']['correct'],2)
        self.assertEqual(st['missing_answer_accuracy_bounds'],[2/6,5/6])
        # Usable family vectors: (correct,n)=(1,2),(0,0),(1,1).
        # Residuals at p=2/3 are (-1/3,0,+1/3); all three families count.
        self.assertAlmostEqual(st['completed_answer']['root_cluster_sandwich_standard_error'],math.sqrt(1.5*(2/9))/3)

    def test_missing_answers_cannot_manufacture_pass(self):
        st=dict(all_results_present=True,unscored_results=0,
                all_request={'accuracy':.80},completed_answer={'accuracy':.80},
                missing_answer_accuracy_bounds=[.78,.82])
        self.assertFalse(screen(st))
        st['missing_answer_accuracy_bounds']=[.79,.81];self.assertTrue(screen(st))
        st['unscored_results']=1;self.assertFalse(screen(st))

if __name__=='__main__':unittest.main()
