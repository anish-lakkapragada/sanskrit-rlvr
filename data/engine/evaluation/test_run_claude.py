"""Offline model isolation, pricing, streaming and resume checks for Claude runs."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from data.engine.evaluation import run_claude as runner
from data.engine.evaluation import retry_claude as retry
from data.engine.evaluation.test_run_opus import events, wire


class ClaudeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_same_twenty_thousand_prompts_as_opus_with_isolated_model_settings(self):
        original, original_tasks, original_prompts, _ = runner.opus.load_inputs()
        for model in runner.MODELS:
            folder = self.root / model
            runner.prepare(folder, model)
            manifest, tasks, prompts, _ = runner.load_inputs(folder)
            self.assertEqual(manifest['tasks'], original['tasks'])
            self.assertEqual(tasks, original_tasks)
            self.assertEqual(prompts, original_prompts)
            self.assertEqual(len(prompts), 20000)
            body = runner.request_body(next(iter(prompts.values())), manifest['request_defaults'])
            self.assertEqual(body['model'], runner.MODELS[model]['id'])
            self.assertEqual(body['thinking'], {'type': 'adaptive'})
            self.assertEqual(body['output_config'], {'effort': 'xhigh'})
            self.assertEqual(body['max_tokens'], 128000)
            self.assertFalse({'tools', 'system', 'fallbacks'} & body.keys())
            body['output_config']['effort'] = 'low'
            self.assertEqual(manifest['request_defaults'], runner.defaults(model))

    def test_model_specific_cost_cache_counters_and_hidden_thinking(self):
        usage = {'input_tokens': 200, 'output_tokens': 1000, 'cache_read_input_tokens': 500,
                 'cache_creation_input_tokens': 200,
                 'cache_creation': {'ephemeral_5m_input_tokens': 100, 'ephemeral_1h_input_tokens': 100},
                 'output_tokens_details': {'thinking_tokens': 990}}
        for model in runner.MODELS:
            pricing = runner.pricing_for(model)
            rates = pricing['rates_usd_per_million_tokens']
            cost, error = runner.estimate_cost({'usage': usage}, pricing)
            self.assertIsNone(error)
            self.assertAlmostEqual(cost, (200*rates['uncached_input'] + 1000*rates['output'] +
                                          500*rates['cached_input'] + 100*rates['cache_write_5m_input'] +
                                          100*rates['cache_write_1h_input'])/1e6)
        pricing = runner.pricing_for('haiku55-xhigh')
        self.assertIsNotNone(runner.estimate_cost({'usage': {'input_tokens': 100000, 'output_tokens': 1}}, pricing)[0])
        cost, error = runner.estimate_cost({'usage': {'input_tokens': 100000, 'cache_read_input_tokens': 1, 'output_tokens': 1}}, pricing)
        self.assertIsNone(cost)
        self.assertIn('pricing tier', error)

    def test_streams_validate_returned_model_and_preserve_refusals(self):
        task = {'id': 'fixture', 'gold_devanagari': ['भवति']}
        for model in runner.MODELS:
            manifest = {'request_defaults': runner.defaults(model), 'pricing': runner.pricing_for(model)}
            for refusal in (False, True):
                parts = events(text='' if refusal else '<answer>भवति</answer>',
                               reason='refusal' if refusal else 'end_turn',
                               category='cyber' if refusal else None, output_tokens=0 if refusal else 1000)
                parts[0]['message']['model'] = manifest['request_defaults']['model']
                with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=wire(parts)))) as client:
                    event = runner.execute(client, manifest, task['id'], runner.request_body('fixture', manifest['request_defaults']),
                                           'fixture-client', runner.base.Journal(self.root / f'{model}-{refusal}.jsonl'), 'fixture-key')
                row = runner.result_row(event, task, manifest)
                self.assertEqual(row['status'], 'refused' if refusal else 'completed')
                self.assertEqual(row['correct'], None if refusal else True)
                if refusal:
                    self.assertEqual(row['error']['stop_details']['category'], 'cyber')
                    self.assertEqual(row['cost_usd'], 0)
                else:
                    expected = .0104 if model == 'sonnet55-xhigh' else .00052
                    self.assertAlmostEqual(row['cost_usd'], expected)
                event['response']['model'] = 'claude-opus-5-5'
                bad = runner.result_row(event, task, manifest)
                self.assertEqual(bad['status'], 'api_error')
                self.assertIsNone(bad['cost_usd'])
                self.assertFalse(runner.transient_failure(bad))

    def test_primary_resume_and_failure_retry_only_send_needed_requests(self):
        for model in runner.MODELS:
            folder = self.root / model
            runner.prepare(folder, model)
            manifest, all_tasks, all_prompts, validator = runner.load_inputs(folder)
            tasks = {f: dict(list(rows.items())[:1]) for f, rows in all_tasks.items()}
            prompts = {(f, task_id): all_prompts[f, task_id] for f in tasks for task_id in tasks[f]}
            calls = []
            original_client = httpx.Client
            def serve(request):
                body = json.loads(request.content)
                calls.append(body)
                if len(calls) == 1:
                    raise httpx.ConnectError('fixture connection error')
                text = next(t['gold_devanagari'][0] for f in tasks for k, t in tasks[f].items()
                            if prompts[f, k] == body['messages'][0]['content'])
                parts = events(f'<answer>{text}</answer>')
                parts[0]['message']['model'] = manifest['request_defaults']['model']
                return httpx.Response(200, content=wire(parts))
            def load(folder):
                return json.loads((folder / 'manifest.json').read_bytes()), tasks, prompts, validator
            with patch.object(runner, 'load_inputs', side_effect=load), patch.object(runner, 'BACKOFF_SECONDS', 0), \
                 patch.object(runner.httpx, 'Client', side_effect=lambda **kwargs: original_client(transport=httpx.MockTransport(serve))), \
                 patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'fixture-key'}):
                runner.run(folder, concurrency=1, budget=10, max_new=1)
                runner.run(folder, concurrency=1, budget=10)
                primary = runner.inspect(folder, verify=True)
                self.assertEqual(len(calls), 4)
                self.assertEqual(primary['unknown_cost_attempts'], 1)
                before = {f: json.loads((folder / f'{f}.json').read_bytes()) for f in tasks}
                report = retry.retry_failed(folder, 'fixture', 1, concurrency=1, budget=10)
                self.assertEqual((report['settled'], report['attempts_settled']), (4, 5))
                self.assertEqual(report['unknown_cost_attempts'], 1)
                retry.retry_failed(folder, 'fixture', 1, concurrency=1, budget=10)
                self.assertEqual(len(calls), 5)
                self.assertEqual(calls[0], calls[-1])
                for f in list(tasks)[1:]:
                    self.assertEqual(before[f], json.loads((folder / f'{f}.json').read_bytes()))

    def test_wrong_model_or_price_manifest_rejected_before_requests(self):
        folder = self.root / 'run'
        original = runner.prepare(folder, 'sonnet55-xhigh')
        for field in ('model', 'price'):
            manifest = deepcopy(original)
            if field == 'model':
                manifest['request_defaults']['model'] = 'claude-haiku-5-5'
            else:
                manifest['pricing']['rates_usd_per_million_tokens']['output'] = .5
            (folder / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(RuntimeError):
                runner.load_inputs(folder)


if __name__ == '__main__':
    unittest.main()
