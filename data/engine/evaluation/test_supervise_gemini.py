"""Offline checks for unattended recovery; never send provider requests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from data.engine.evaluation import supervise_gemini as s


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root/'data/benchmark/results/gemini4-argon-high'
        self.folder.mkdir(parents=True)
        self.path = self.folder/'manifest.json'
        self.manifest = {'status': 'paused', 'api': {'headers_without_credentials': {}},
                         'execution': {'progress': {'settled': 0}}}
        self.save()
        for family in s.runner.FAMILIES:
            (self.folder/f'{family}.json').write_text('[]')
        self.calls = []
        self.sleeps = []
        for target, value in [('ROOT', self.root), ('RUNTIME', self.root/'runtime')]:
            p = patch.object(s, target, value); p.start(); self.addCleanup(p.stop)
        for target in ('notify', 'emit'):
            p = patch.object(s, target); p.start(); self.addCleanup(p.stop)
        p = patch.object(s.runner, 'inspect', return_value={})
        self.inspect = p.start(); self.addCleanup(p.stop)
        p = patch.object(s, 'publish', return_value={'correct': 0, 'cost_usd': 0, 'refusals': 0})
        self.publish = p.start(); self.addCleanup(p.stop)
        p = patch.object(s.time, 'sleep', side_effect=self.sleeps.append)
        p.start(); self.addCleanup(p.stop)

    def save(self):
        self.path.write_text(json.dumps(self.manifest))

    def worker(self, reasons):
        def launch(command, **kwargs):
            self.calls.append(command)
            reason = reasons.pop(0)
            self.manifest['status'] = 'paused' if reason else 'completed'
            self.manifest['execution'].update(stopped_reason=reason, progress={'settled': len(self.calls)})
            self.save()
            return SimpleNamespace(pid=123, poll=lambda: 0, returncode=0)
        return launch

    def test_capacity_failures_continue_beyond_three_attempts_with_backoff(self):
        reason = 'Five consecutive transient failures; inspect before continuing'
        with patch.object(s.subprocess, 'Popen', side_effect=self.worker([reason]*3+[None])), \
             patch.object(s.subprocess, 'run', return_value=SimpleNamespace(returncode=0)):
            s.supervise('gemini4-argon-high', 64, unattended=True, initial_cooldown=300)
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.sleeps, [300, 300, 600, 1200])
        self.assertTrue(all(cmd[-2:] == ['--concurrency', '4'] for cmd in self.calls))
        self.assertEqual(self.inspect.call_count, 4)
        self.publish.assert_called_once()

    def test_budget_stop_never_resumes_or_publishes(self):
        with patch.object(s.subprocess, 'Popen', side_effect=self.worker(['Budget guard: insufficient remaining dollars'])), \
             self.assertRaisesRegex(RuntimeError, 'Budget guard'):
            s.supervise('gemini4-argon-high', 64, unattended=True)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.sleeps, [])
        self.publish.assert_not_called()

    def test_unresolved_requests_block_all_submission(self):
        self.inspect.side_effect = RuntimeError('One unresolved started attempt')
        with patch.object(s.subprocess, 'Popen') as launch, self.assertRaisesRegex(RuntimeError, 'unresolved'):
            s.supervise('gemini4-argon-high', 64, unattended=True)
        launch.assert_not_called()
        self.publish.assert_not_called()

    def test_retries_continue_only_for_infrastructure_errors(self):
        self.manifest['status'] = 'completed'; self.save()
        failed = {'status': 'api_error', 'error': {'http_status': 429}}
        path = self.folder/'tinanta.json'
        path.write_text(json.dumps([failed, {'status': 'refused', 'error': None}]))
        retried = []

        def run(command, **kwargs):
            if command[0] == '/usr/bin/osascript':
                return SimpleNamespace(returncode=0)
            self.assertIn('retry_gemini.py', command[2])
            self.assertEqual(command[command.index('--expected-count')+1], '1')
            batch = command[command.index('--batch-id')+1]
            retried.append(batch)
            self.manifest['execution'].setdefault('retry_batches', []).append({'id': batch, 'state': 'completed'})
            self.save()
            if len(retried) == 3:
                path.write_text(json.dumps([{'status': 'completed', 'error': None}, {'status': 'refused', 'error': None}]))
            return SimpleNamespace(returncode=0)

        with patch.object(s.subprocess, 'Popen') as launch, patch.object(s.subprocess, 'run', side_effect=run):
            s.supervise('gemini4-argon-high', 64, unattended=True)
        launch.assert_not_called()
        self.assertEqual(retried, [f'v3-infrastructure-recovery-{i}' for i in (1, 2, 3)])
        self.assertEqual(self.sleeps, [300, 600])
        self.publish.assert_called_once()


if __name__ == '__main__':
    unittest.main()
