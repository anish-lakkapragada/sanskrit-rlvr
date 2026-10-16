"""Offline billing, request-isolation and crash/retry tests; no network calls."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from jsonschema import Draft202012Validator
from data.engine.evaluation import run_openai as runner
from data.engine.evaluation import retry_openai as retry


def response(model, text='<answer>भवति</answer>'):
    return {'id': 'resp_fixture', 'status': 'completed', 'model': model, 'service_tier': 'default',
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': text}]}],
            'usage': {'input_tokens': 200, 'output_tokens': 1000, 'total_tokens': 1200,
                      'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0},
                      'output_tokens_details': {'reasoning_tokens': 900}}}


def wire(value):
    return ('data: '+json.dumps({'type': 'response.completed', 'response': value})+'\n\n').encode()


class OpenAITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_all_twenty_thousand_v3_prompts_match_the_anthropic_inputs(self):
        source = json.loads((runner.ROOT/'data/benchmark/results/opus55-xhigh/manifest.json').read_bytes())
        previous = None
        for model in runner.MODELS:
            folder = self.root/model
            runner.prepare(folder, model)
            manifest, tasks, prompts, _ = runner.load_inputs(folder)
            self.assertEqual(len(prompts), 20000)
            for actual, expected in zip(manifest['tasks'], source['tasks']):
                for field in ('dataset', 'sampling_manifest', 'prompt_template', 'renderer'):
                    self.assertEqual(actual[field], expected[field])
            if previous is not None:
                self.assertEqual(prompts, previous)
            previous = prompts
            body = runner.request_body(next(iter(prompts.values())), manifest['request_defaults'])
            self.assertEqual(body['model'], runner.MODELS[model]['id'])
            self.assertEqual(body['reasoning'], {'effort': 'xhigh'})
            self.assertEqual(set(body), {'model', 'reasoning', 'service_tier', 'store', 'stream', 'input'})
            body['reasoning']['effort'] = 'low'
            self.assertEqual(manifest['request_defaults'], runner.defaults(model))
            with self.assertRaises(ValueError):
                runner.check_budget(manifest, runner.MODELS[model]['budget_usd'] + 1)
        self.assertEqual(sum(m['budget_usd'] for m in runner.MODELS.values()), 6750)

    def test_billing_cache_subsets_and_reasoning_not_double_counted(self):
        for model, expected in (('astra-xhigh', .052), ('sol-xhigh', .0104), ('luna-xhigh', .00052)):
            r = response(runner.MODELS[model]['id'])
            pricing = runner.pricing_for(model)
            self.assertEqual(runner.estimate_cost(r, pricing), (expected, None))
            r['usage']['input_tokens_details'] = {'cached_tokens': 100, 'cache_write_tokens': 50}
            rates = pricing['rates_usd_per_million_tokens']
            cost = (50*rates['uncached_input']+100*rates['cached_input']+50*rates['cache_write_input']+1000*rates['output'])/1e6
            self.assertAlmostEqual(runner.estimate_cost(r, pricing)[0], cost)
            r['usage']['input_tokens_details']['cached_tokens'] = 201
            self.assertIsNone(runner.estimate_cost(r, pricing)[0])
            r['usage']['input_tokens'] = 272001
            r['usage']['input_tokens_details'] = {}
            long_rates = pricing['long_context_rates_usd_per_million_tokens']
            self.assertAlmostEqual(runner.estimate_cost(r, pricing)[0], (272001*long_rates['uncached_input']+1000*long_rates['output'])/1e6)

    def test_stream_persistence_model_mismatch_refusal_and_tool_detection(self):
        task = {'id': 'fixture', 'gold_devanagari': ['भवति']}
        for model in runner.MODELS:
            manifest = {'api': {'url': runner.ENDPOINT}, 'request_defaults': runner.defaults(model), 'pricing': runner.pricing_for(model)}
            journal = runner.base.Journal(self.root/f'{model}.jsonl')
            r = response(manifest['request_defaults']['model'])
            with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, content=wire(r)))) as client:
                event = runner.execute(client, manifest, task['id'], runner.request_body('fixture', manifest['request_defaults']), 'client-fixture', journal, 'fixture-key')
            self.assertEqual(list(journal.read()), [event])
            row = runner.result_row(event, task, manifest)
            self.assertTrue(row['correct'] and row['format_ok'])
            bad = deepcopy(event); bad['response']['model'] = 'another-model'
            row = runner.result_row(bad, task, manifest)
            self.assertEqual(row['status'], 'api_error')
            self.assertIsNone(row['cost_usd'])
            self.assertFalse(runner.transient_failure(row))
            bad = deepcopy(event); bad['response']['output'].append({'type': 'web_search_call'})
            self.assertEqual(runner.result_row(bad, task, manifest)['status'], 'api_error')
            bad = deepcopy(event); bad['response']['output'][0]['content'] = [{'type': 'refusal', 'refusal': 'fixture refusal'}]
            row = runner.result_row(bad, task, manifest)
            self.assertEqual(row['status'], 'refused')
            self.assertIsNone(row['correct'])
            self.assertFalse(runner.transient_failure(row))

    def test_resume_retry_and_budget_preserve_all_paid_attempts(self):
        folder = self.root/'sol-xhigh'
        runner.prepare(folder, 'sol-xhigh')
        manifest, all_tasks, all_prompts, validator = runner.load_inputs(folder)
        tasks = {f: dict(list(rows.items())[:1]) for f, rows in all_tasks.items()}
        prompts = {(f, k): all_prompts[f, k] for f in tasks for k in tasks[f]}
        calls = []
        original_client = httpx.Client
        def serve(request):
            body = json.loads(request.content); calls.append(body)
            if len(calls) == 1:
                raise httpx.ConnectError('fixture failure')
            gold = next(t['gold_devanagari'][0] for f in tasks for k, t in tasks[f].items() if prompts[f, k] == body['input'])
            return httpx.Response(200, content=wire(response(body['model'], f'<answer>{gold}</answer>')))
        def load(folder):
            return json.loads((folder/'manifest.json').read_bytes()), tasks, prompts, validator
        with patch.object(runner, 'load_inputs', side_effect=load), patch.object(runner, 'BACKOFF_SECONDS', 0), \
             patch.object(runner.httpx, 'Client', side_effect=lambda **kwargs: original_client(transport=httpx.MockTransport(serve))), \
             patch.dict(os.environ, {'OPENAI_API_KEY': 'fixture-key'}):
            runner.run(folder, concurrency=1, budget=.01)
            self.assertEqual(len(calls), 0)
            runner.run(folder, concurrency=1, budget=10, max_new=1)
            runner.run(folder, concurrency=1, budget=10)
            primary = runner.inspect(folder, verify=True)
            self.assertEqual(len(calls), 4)
            self.assertEqual(primary['unknown_cost_attempts'], 1)
            before = {f: json.loads((folder/f'{f}.json').read_bytes()) for f in tasks}
            retry.retry_failed(folder, 'fixture', 1, concurrency=1, budget=10)
            report = retry.retry_failed(folder, 'fixture', 1, concurrency=1, budget=10)
            self.assertEqual(len(calls), 5)
            self.assertEqual(report['attempts_settled'], 5)
            self.assertEqual(report['unknown_cost_attempts'], 1)
            self.assertAlmostEqual(report['known_cost_usd'], .0416)
            for f in tasks:
                after = json.loads((folder/f'{f}.json').read_bytes())
                if before[f][0]['status'] == 'completed':
                    self.assertEqual(after, before[f])
                else:
                    self.assertEqual(after[0]['attempt_number'], 2)
                    self.assertTrue(after[0]['correct'])
            self.assertEqual(sum(v['strict_correct'] for v in report['families'].values()), 4)
            journals = {f: runner.base.Journal(folder/'journals'/f'{f}.jsonl') for f in tasks}
            current = load(folder)[0]
            for journal in journals.values():
                for event in journal.read():
                    if event['event'] == 'started':
                        self.assertNotIn('max_output_tokens', event['request'])
            current['request_defaults']['reasoning']['effort'] = 'low'
            with self.assertRaises(RuntimeError):
                runner.recover_attempts(journals, tasks, current, prompts)

    def test_interrupted_request_is_never_silently_resent(self):
        task = {'id': 'fixture', 'gold_devanagari': ['भवति']}
        manifest = {'request_defaults': runner.defaults('sol-xhigh'), 'pricing': runner.pricing_for('sol-xhigh'), 'execution': {}}
        journal = runner.base.Journal(self.root/'partial.jsonl')
        journal.append({'event': 'started', 'task_id': 'fixture', 'attempt_number': 1, 'request': runner.request_body('prompt', manifest['request_defaults'])})
        _, _, unresolved = runner.recover_attempts({'subanta': journal}, {'subanta': {'fixture': task}}, manifest, {('subanta', 'fixture'): 'prompt'})
        self.assertEqual(unresolved, [('subanta', 'fixture', 1)])
        event = {'event': 'error', 'task_id': 'fixture', 'attempt_number': 1, 'status': 'transport_error', 'partial_output': '<answer>भ', 'error': {'type': 'ReadTimeout'}}
        row = runner.result_row(event, task, manifest)
        self.assertEqual(row['output_text'], '<answer>भ')
        self.assertIsNone(row['cost_usd'])
        self.assertTrue(runner.transient_failure(row))
        Draft202012Validator(runner.schema()).validate([row])


if __name__ == '__main__':
    unittest.main()
