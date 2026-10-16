"""Offline Vertex request, billing, credential, replay and retry checks."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from jsonschema import Draft202012Validator, ValidationError
from data.engine.evaluation import run_gemini_flash as runner
from data.engine.evaluation import retry_gemini_flash as retry


class FixtureToken:
    def get(self):
        return 'private-fixture-token'
    def invalidate(self):
        pass


def response(text='<answer>भवति</answer>'):
    return {'modelVersion': runner.MODEL, 'responseId': 'vertex-fixture',
            'candidates': [{'content': {'role': 'model', 'parts': [{'text': text}]}, 'finishReason': 'STOP'}],
            'usageMetadata': {'promptTokenCount': 200, 'candidatesTokenCount': 100,
                              'thoughtsTokenCount': 900, 'totalTokenCount': 1200,
                              'promptTokensDetails': [{'modality': 'TEXT', 'tokenCount': 200}],
                              'trafficType': 'ON_DEMAND'}}


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = {'request_defaults': runner.defaults(), 'pricing': runner.pricing_for(),
                         'api': {'url': runner.ENDPOINT, 'headers_without_credentials': {'Content-Type': 'application/json', 'X-Goog-User-Project': runner.PROJECT}}}
        self.task = {'id': 'fixture', 'gold_devanagari': ['भवति']}

    def tearDown(self):
        self.temp.cleanup()

    def test_same_twenty_thousand_v3_prompts_and_exact_user_request(self):
        folder = self.root/runner.RUN_ID
        runner.prepare(folder)
        manifest, tasks, prompts, _ = runner.load_inputs(folder)
        original = json.loads((runner.ROOT/'data/benchmark/results/opus55-xhigh/manifest.json').read_bytes())
        self.assertEqual(len(prompts), 20000)
        for actual, expected in zip(manifest['tasks'], original['tasks']):
            for field in ('dataset', 'sampling_manifest', 'prompt_template', 'renderer'):
                self.assertEqual(actual[field], expected[field])
        body = runner.request_body('hydrated prompt', manifest['request_defaults'])
        self.assertEqual(body, {'contents': [{'role': 'user', 'parts': [{'text': 'hydrated prompt'}]}],
                                'generationConfig': {'thinkingConfig': {'thinkingLevel': 'HIGH'}}})
        self.assertNotIn('maxOutputTokens', json.dumps(body))
        self.assertNotIn('thinkingBudget', json.dumps(body))
        self.assertEqual(manifest['api']['url'], 'https://aiplatform.googleapis.com/v1/projects/sanskrit-project-511705/locations/global/publishers/google/models/gemini-3.8-flash:generateContent')
        self.assertEqual(manifest['output_limit']['documented_model_max_output_tokens'], 65536)
        body['generationConfig']['thinkingConfig']['thinkingLevel'] = 'LOW'
        self.assertEqual(manifest['request_defaults'], runner.defaults())

    def test_thinking_is_added_once_cache_is_subset_and_full_metadata_retained(self):
        r = response()
        usage = runner.normalized_usage(r)
        self.assertEqual(usage['output_tokens'], 1000)
        self.assertEqual(usage['output_tokens_details']['reasoning_tokens'], 900)
        self.assertEqual(usage['provider_usage'], r['usageMetadata'])
        self.assertEqual(runner.estimate_cost(r, runner.pricing_for()), (.0078, None))
        r['usageMetadata']['cachedContentTokenCount'] = 100
        self.assertEqual(runner.estimate_cost(r, runner.pricing_for()), (.007665, None))
        r['usageMetadata']['cachedContentTokenCount'] = 201
        self.assertIsNone(runner.estimate_cost(r, runner.pricing_for())[0])
        r = response(); r['usageMetadata']['totalTokenCount'] = 300
        self.assertIsNone(runner.estimate_cost(r, runner.pricing_for())[0])
        r = response(); r['usageMetadata']['trafficType'] = 'PROVISIONED_THROUGHPUT'
        self.assertIsNone(runner.estimate_cost(r, runner.pricing_for())[0])

    def test_adc_refresh_is_private_cached_and_failure_does_not_leak_output(self):
        first = SimpleNamespace(stdout='first-private-fixture-token\n', stderr='', returncode=0)
        second = SimpleNamespace(stdout='second-private-fixture-token\n', stderr='', returncode=0)
        with patch.object(runner.subprocess, 'run', side_effect=[first, second]) as run, patch.object(runner.time, 'monotonic', return_value=0) as clock:
            token = runner.ADCToken()
            self.assertEqual(token.get(), first.stdout.strip())
            self.assertEqual(token.get(), first.stdout.strip())
            self.assertEqual(run.call_count, 1)
            clock.return_value = 2701
            self.assertEqual(token.get(), second.stdout.strip())
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args.args[0], [runner.GCLOUD, 'auth', 'application-default', 'print-access-token'])
            self.assertTrue(run.call_args.kwargs['capture_output'])
            self.assertNotIn('private-fixture-token', repr(token))
        failure = SimpleNamespace(stdout='do-not-expose-fixture', stderr='do-not-expose-fixture', returncode=1)
        with patch.object(runner.subprocess, 'run', return_value=failure):
            with self.assertRaises(RuntimeError) as raised:
                runner.ADCToken().get()
            self.assertNotIn('do-not-expose-fixture', str(raised.exception))

    def test_priority_cost_uses_returned_tier_and_preserves_standard_prices(self):
        standard = response()
        priority = deepcopy(standard)
        priority['usageMetadata']['trafficType'] = 'ON_DEMAND_PRIORITY'
        self.assertEqual(runner.estimate_cost(standard, runner.pricing_for()), (.0078, None))
        self.assertEqual(runner.estimate_cost(priority, runner.pricing_for()), (.01404, None))
        priority['usageMetadata']['cachedContentTokenCount'] = 100
        self.assertEqual(runner.estimate_cost(priority, runner.pricing_for()), (.013797, None))
        event = {'event': 'response', 'task_id': 'fixture', 'attempt_number': 1,
                 'request_headers': runner.request_headers(priority=True), 'response': standard}
        # A provider downgrade must use standard prices even when priority was requested.
        self.assertEqual(runner.result_row(event, self.task, self.manifest)['cost_usd'], .0078)
        missing = deepcopy(event); missing['response']['usageMetadata'].pop('trafficType')
        self.assertIsNone(runner.result_row(missing, self.task, self.manifest)['cost_usd'])
        standard_manifest = {**self.manifest, 'output_limit': {'documented_model_max_output_tokens': 65536}}
        priority_manifest = deepcopy(standard_manifest)
        priority_manifest['api']['headers_without_credentials'] = runner.request_headers(priority=True)
        self.assertAlmostEqual(runner.reserve_per_request(priority_manifest, {'fixture': 'prompt'}),
                               runner.reserve_per_request(standard_manifest, {'fixture': 'prompt'}) * 1.8)

    def test_priority_headers_change_routing_only_and_remain_in_journal(self):
        manifest = deepcopy(self.manifest)
        manifest['api']['headers_without_credentials'] = runner.request_headers(priority=True)
        journal = runner.base.Journal(self.root/'priority.jsonl')
        body = runner.request_body('prompt', runner.defaults())
        def serve(request):
            self.assertEqual(json.loads(request.content), body)
            self.assertEqual(request.headers['X-Vertex-AI-LLM-Request-Type'], 'shared')
            self.assertEqual(request.headers['X-Vertex-AI-LLM-Shared-Request-Type'], 'priority')
            value = response(); value['usageMetadata']['trafficType'] = 'ON_DEMAND_PRIORITY'
            return httpx.Response(200, json=value)
        with httpx.Client(transport=httpx.MockTransport(serve)) as client:
            event = runner.execute(client, manifest, 'fixture', body, 'fixture-id', journal, FixtureToken())
        self.assertEqual(event['request_headers'], runner.request_headers(priority=True))
        self.assertNotIn('private-fixture-token', journal.path.read_text())
        row = runner.result_row(event, self.task, manifest)
        self.assertEqual(row['cost_usd'], .01404)
        Draft202012Validator(runner.schema()).validate([row])

    def test_response_preserved_without_credentials_refusals_and_mismatches(self):
        journal = runner.base.Journal(self.root/'fixture.jsonl')
        def serve(request):
            self.assertEqual(request.headers['Authorization'], 'Bearer private-fixture-token')
            self.assertEqual(request.headers['X-Goog-User-Project'], runner.PROJECT)
            self.assertEqual(json.loads(request.content), runner.request_body('prompt', runner.defaults()))
            return httpx.Response(200, json=response())
        with httpx.Client(transport=httpx.MockTransport(serve)) as client:
            event = runner.execute(client, self.manifest, 'fixture', runner.request_body('prompt', runner.defaults()), 'fixture-id', journal, FixtureToken())
        self.assertEqual(list(journal.read()), [event])
        self.assertNotIn('private-fixture-token', journal.path.read_text())
        row = runner.result_row(event, self.task, self.manifest)
        self.assertTrue(row['correct'] and row['format_ok'])
        self.assertEqual(row['response_id'], 'vertex-fixture')
        Draft202012Validator(runner.schema()).validate([row])
        bad = deepcopy(event); bad['response']['modelVersion'] = 'gemini-3.8-flash-cyber-permissive'
        row = runner.result_row(bad, self.task, self.manifest)
        self.assertEqual(row['status'], 'api_error'); self.assertIsNone(row['cost_usd'])
        self.assertFalse(runner.transient_failure(row))
        bad = deepcopy(event); bad['response']['candidates'][0]['finishReason'] = 'SAFETY'
        row = runner.result_row(bad, self.task, self.manifest)
        self.assertEqual(row['status'], 'refused'); self.assertIsNone(row['correct'])
        self.assertFalse(runner.transient_failure(row))
        bad = deepcopy(event); bad['response']['candidates'][0]['finishReason'] = 'MAX_TOKENS'
        row = runner.result_row(bad, self.task, self.manifest)
        self.assertEqual(row['status'], 'incomplete'); self.assertFalse(runner.transient_failure(row))
        bad = deepcopy(event); bad['response']['candidates'][0]['content']['parts'].insert(0, {'thought': True, 'text': 'summary of thought'})
        self.assertEqual(runner.result_row(bad, self.task, self.manifest)['output_text'], '<answer>भवति</answer>')
        bad = deepcopy(event); bad['response']['candidates'][0]['content']['parts'].append({'functionCall': {'name': 'unexpected'}})
        self.assertEqual(runner.result_row(bad, self.task, self.manifest)['status'], 'api_error')

    def test_non_200_is_unbilled_but_transport_failure_retains_unknown_cost(self):
        journal = runner.base.Journal(self.root/'failure.jsonl')
        with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(429, json={'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', 'message': 'private-fixture-token'}}))) as client:
            event = runner.execute(client, self.manifest, 'fixture', runner.request_body('prompt', runner.defaults()), 'fixture-id', journal, FixtureToken())
        row = runner.result_row(event, self.task, self.manifest)
        self.assertTrue(runner.transient_failure(row)); self.assertEqual(row['cost_usd'], 0)
        validator = Draft202012Validator(runner.schema())
        validator.validate([row])
        with self.assertRaises(ValidationError):
            validator.validate([{**row, 'cost_usd': .01}])
        self.assertNotIn('private-fixture-token', journal.path.read_text())
        event = {'event': 'error', 'task_id': 'fixture', 'attempt_number': 1, 'status': 'transport_error', 'request_sent': True, 'error': {'type': 'ReadTimeout'}}
        row = runner.result_row(event, self.task, self.manifest)
        self.assertIsNone(row['cost_usd']); self.assertTrue(runner.transient_failure(row))
        Draft202012Validator(runner.schema()).validate([row])

    def test_resume_and_explicit_retry_do_not_duplicate_successes(self):
        folder = self.root/runner.RUN_ID
        runner.prepare(folder)
        manifest, all_tasks, all_prompts, validator = runner.load_inputs(folder)
        tasks = {f: dict(list(rows.items())[:1]) for f, rows in all_tasks.items()}
        prompts = {(f, k): all_prompts[f, k] for f in tasks for k in tasks[f]}
        calls = []
        original_client = httpx.Client
        def serve(request):
            body = json.loads(request.content); calls.append(body)
            if len(calls) == 1:
                return httpx.Response(429, json={'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED'}})
            gold = next(t['gold_devanagari'][0] for f in tasks for k, t in tasks[f].items() if prompts[f, k] == body['contents'][0]['parts'][0]['text'])
            return httpx.Response(200, json=response(f'<answer>{gold}</answer>'))
        def load(folder):
            return json.loads((folder/'manifest.json').read_bytes()), tasks, prompts, validator
        with patch.object(runner, 'load_inputs', side_effect=load), patch.object(runner, 'BACKOFF_SECONDS', 0), \
             patch.object(runner.httpx, 'Client', side_effect=lambda **kwargs: original_client(transport=httpx.MockTransport(serve))), \
             patch.object(runner, 'ADCToken', return_value=FixtureToken()):
            runner.run(folder, concurrency=1, budget=.01)
            self.assertEqual(len(calls), 0)
            runner.run(folder, concurrency=1, budget=10, max_new=1)
            runner.run(folder, concurrency=1, budget=10)
            primary = runner.inspect(folder, verify=True)
            self.assertEqual(len(calls), 4); self.assertEqual(primary['unknown_cost_attempts'], 0)
            before = {f: json.loads((folder/f'{f}.json').read_bytes()) for f in tasks}
            retry.retry_failed(folder, 'fixture', 1, concurrency=1, budget=10)
            report = retry.retry_failed(folder, 'fixture', 1, concurrency=1, budget=10)
            self.assertEqual(len(calls), 5)
            self.assertEqual(report['attempts_settled'], 5)
            self.assertEqual(report['unknown_cost_attempts'], 0)
            self.assertAlmostEqual(report['known_cost_usd'], .0312)
            for f in tasks:
                after = json.loads((folder/f'{f}.json').read_bytes())
                if before[f][0]['status'] == 'completed':self.assertEqual(after, before[f])
                else:
                    self.assertEqual(after[0]['attempt_number'], 2)
                    self.assertTrue(after[0]['correct'])
            for p in (folder/'journals').glob('*.jsonl.gz'):
                import gzip
                self.assertNotIn('private-fixture-token', gzip.decompress(p.read_bytes()).decode())


if __name__ == '__main__':
    unittest.main()
