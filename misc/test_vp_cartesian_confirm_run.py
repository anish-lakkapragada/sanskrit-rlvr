import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from misc import vp_cartesian_confirm_run as execution
from misc.test_vp_goal import state, job


class SequentialConfirmationTests(unittest.TestCase):
    def panel(self):
        s = state()
        parts = []
        for name in ('part-a', 'part-b'):
            j = job('Anthropic', 'confirm', 1200)
            j.update(id=name, tasks_digest=name)
            s['jobs'][name] = j
            parts.append({k: j[k] for k in ('id', 'provider', 'phase', 'n', 'tasks_digest')})
        return s, {'fixed_n': 2400, 'chunks': parts}

    def test_second_chunk_cannot_submit_before_first_settles(self):
        s, plan = self.panel()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'manifest.json'
            path.write_text('{}')
            with patch.object(execution, 'inspect', return_value=plan), \
                    patch.object(execution.runner, 'load', return_value=s), \
                    patch.object(execution.runner, 'count_inputs') as counts, \
                    patch.object(execution.runner, 'submit') as submit, \
                    patch.object(execution.time, 'sleep', side_effect=InterruptedError):
                with self.assertRaises(InterruptedError):
                    execution.execute(path)
                counts.assert_called_once_with('part-a')
                submit.assert_called_once_with('part-a')

    def test_unknown_submission_never_replays_or_advances(self):
        s, plan = self.panel()
        s['jobs']['part-a'].update(attempted_at='unknown', batch_id=None)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'manifest.json'
            path.write_text('{}')
            with patch.object(execution, 'inspect', return_value=plan), \
                    patch.object(execution.runner, 'load', return_value=s), \
                    patch.object(execution.runner, 'count_inputs') as counts, \
                    patch.object(execution.runner, 'submit') as submit:
                with self.assertRaisesRegex(ValueError, 'never retry'):
                    execution.execute(path)
                counts.assert_not_called()
                submit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
