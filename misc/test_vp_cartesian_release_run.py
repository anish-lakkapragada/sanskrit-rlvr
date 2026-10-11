import copy
import unittest
from unittest.mock import patch
from misc import vp_goal as runner
from misc.vp_cartesian_release_run import decision
from misc.test_vp_goal import state, job


class ExecutionDecisionTests(unittest.TestCase):
    def test_waits_for_reservations_to_settle_without_spending(self):
        s=state();s['historical_spend_micro']['OpenAI']=800000000
        pending=job('OpenAI',n=100);pending.update(attempted_at='now',reservation_micro=41710000)
        s['jobs']['pending']=pending
        with patch.object(runner,'client_for') as client:
            self.assertEqual(decision(s,job('OpenAI',n=500)), 'waiting_for_settlement')
            client.assert_not_called()
        s['jobs']['pending'].update(settled=True,actual_cost_upper_micro=1)
        self.assertEqual(decision(s,job('OpenAI',n=500)), 'unfunded_fixed_membership')

    def test_waits_for_core_and_does_not_absorb_unexpected_failures(self):
        self.assertEqual(decision(state(),job('OpenAI','hard_extension',100)), 'waiting_for_core_settlement')
        s=state();s['status']='halted_for_reconciliation'
        with self.assertRaisesRegex(ValueError,'halted'):
            decision(s,job())
        j=job();j['attempted_at']='unknown'
        with self.assertRaisesRegex(ValueError,'never replay'):
            decision(state(),j)


if __name__=='__main__':
    unittest.main()
