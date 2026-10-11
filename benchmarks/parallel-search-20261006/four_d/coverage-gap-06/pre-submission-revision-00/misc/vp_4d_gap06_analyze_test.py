"""Synthetic checks for complete-panel gating and distributed-error accounting."""
import copy
import unittest

from misc.vp_4d_gap06_analyze import OUT, read, summarize, verify_panel, verify_results, verify_settled


class CinAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tasks=read(OUT/'cin-candidate-inputs.json')
        self.branches=read(OUT/'cin-branches.json')
        self.rows=[dict(task=copy.deepcopy(t),task_id=t['id'],is_correct=True,
                       status='completed',answer=t['gold_devanagari'][0],truncated=False) for t in self.tasks]

    def test_perfect_result_is_not_a_trigger(self):
        verify_panel(self.tasks,self.branches);verify_results(self.tasks,self.rows)
        a=summarize(self.rows,self.branches)
        self.assertEqual(a['metrics']['one_per_family_sandwich_se'],0)
        self.assertLess(a['metrics']['all_request_wilson95'][0],1)
        self.assertFalse(a['trigger']['all_mechanical_conditions_met'])

    def test_nonusable_correct_is_unknown_in_bounds_and_not_wrong(self):
        self.rows[0]['truncated']=True
        self.rows[1].update(status='refused',answer=None,is_correct=False)
        a=summarize(self.rows,self.branches)
        self.assertEqual(a['metrics']['correct'],45)
        self.assertEqual(a['metrics']['usable_correct'],44)
        self.assertEqual(a['metrics']['completion_bounds'],[44/46,1])
        self.assertEqual(a['trigger']['wrong_completed_families'],0)

    def test_zero_usable_denominator(self):
        for r in self.rows:r.update(status='refused',answer=None,is_correct=False)
        a=summarize(self.rows,self.branches)
        self.assertIsNone(a['metrics']['usable_accuracy'])
        self.assertIsNone(a['metrics']['usable_family_se'])
        self.assertEqual(a['metrics']['completion_bounds'],[0,1])

    def test_distributed_trigger_and_concentration_fail(self):
        byid={r['task']['id']:r for r in self.rows}
        chosen=[];seen=set()
        for b in self.branches:
            if b['gana'] not in seen:
                chosen.append(b['id']);seen.add(b['gana'])
        for tid in chosen:byid[tid]['is_correct']=False
        self.assertEqual(len(chosen),8)
        self.assertTrue(summarize(self.rows,self.branches)['trigger']['all_mechanical_conditions_met'])
        for r in self.rows:r['is_correct']=True
        for r in self.rows[:8]:r['is_correct']=False
        self.assertFalse(summarize(self.rows,self.branches)['trigger']['all_mechanical_conditions_met'])

    def test_membership_and_metadata_fail_closed(self):
        with self.assertRaises(ValueError):verify_results(self.tasks,self.rows[:-1])
        with self.assertRaises(ValueError):verify_results(self.tasks,self.rows[:-1]+[self.rows[0]])
        self.rows[0]['task']['gold_devanagari']=['changed']
        with self.assertRaises(ValueError):verify_results(self.tasks,self.rows)

    def test_complete_settlement_gate(self):
        d=dict(job_id='unit',provider='Anthropic',phase='confirm_64k',n=46,tasks_digest='fixed')
        j=dict(d,settled=False,collected_at='timestamp')
        with self.assertRaises(ValueError):verify_settled({'jobs':{'unit':j}},d)
        j['settled']=True
        self.assertIs(verify_settled({'jobs':{'unit':j}},d),j)
        j['n']=45
        with self.assertRaises(ValueError):verify_settled({'jobs':{'unit':j}},d)


if __name__=='__main__':unittest.main()
