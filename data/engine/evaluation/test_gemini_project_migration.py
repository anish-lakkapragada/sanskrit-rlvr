"""Offline checks for preserving attempts across a user-authorized project move."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from data.engine.evaluation import run_gemini, run_gemini_flash
from data.engine.evaluation import retry_gemini, retry_gemini_flash


def old_api(runner):
    project = runner.PREVIOUS_PROJECT
    return {'project': project, 'location': 'global', 'method': 'POST',
            'url': runner.ENDPOINT.replace(runner.PROJECT, project),
            'headers_without_credentials': runner.request_headers(priority=True, project=project)}


def review(row):
    return {'task_id': row['task_id'], 'attempt_number': row['attempt_number'],
            'error_sha256': hashlib.sha256(json.dumps(row['error'], sort_keys=True,
                                                    ensure_ascii=False).encode()).hexdigest()}


class ProjectMigrationTests(unittest.TestCase):
    def test_flash_second_migration_preserves_both_declared_historical_routes(self):
        runner = run_gemini_flash
        manifest = {"execution": {"project_migrations": []}}
        for project in runner.HISTORICAL_PROJECTS:
            api = {"project": project, "location": "global", "method": "POST",
                   "url": runner.ENDPOINT.replace(runner.PROJECT, project),
                   "headers_without_credentials": runner.request_headers(priority=True, project=project)}
            self.assertNotIn(api["headers_without_credentials"], runner.journal_headers(manifest))
            manifest["execution"]["project_migrations"].append({"previous_api": api})
            self.assertIn(api["headers_without_credentials"], runner.journal_headers(manifest))
        for project in (*runner.HISTORICAL_PROJECTS, runner.PROJECT):
            self.assertIn(runner.request_headers(priority=True, project=project), runner.journal_headers(manifest))
        manifest["execution"]["project_migrations"][1]["previous_api"]["url"] = "https://example.com/wrong-route"
        with self.assertRaisesRegex(RuntimeError, "historical Google project"):
            runner.journal_headers(manifest)

    def test_historical_headers_require_a_declared_known_project(self):
        for runner in (run_gemini, run_gemini_flash):
            with self.subTest(model=runner.MODEL):
                historical = old_api(runner)
                self.assertNotIn(historical['headers_without_credentials'], runner.journal_headers({}))
                manifest = {'execution': {'project_migrations': [{'previous_api': historical}]}}
                self.assertIn(historical['headers_without_credentials'], runner.journal_headers(manifest))
                self.assertIn(runner.request_headers(priority=True), runner.journal_headers(manifest))
                historical['project'] = 'unapproved-project'
                with self.assertRaisesRegex(RuntimeError, 'historical Google project'):
                    runner.journal_headers(manifest)

    def test_billing_retry_review_is_scoped_to_the_exact_failed_attempt(self):
        row = {'task_id': 'fixture', 'attempt_number': 1, 'status': 'api_error',
               'error': {'http_status': 403, 'provider_error': {'error': {
                   'details': [{'reason': 'BILLING_DISABLED'}]}}}}
        manifest = {'execution': {'reviewed_infrastructure_failures': [review(row)]}}
        for runner in (run_gemini, run_gemini_flash):
            with self.subTest(model=runner.MODEL):
                self.assertFalse(runner.transient_failure(row))
                self.assertFalse(runner.retryable_failure(row, {}))
                self.assertTrue(runner.retryable_failure(row, manifest))
                self.assertFalse(runner.retryable_failure({**row, 'attempt_number': 2}, manifest))
                self.assertFalse(runner.retryable_failure({**row, 'task_id': 'other'}, manifest))
                for status in ('completed', 'refused', 'incomplete'):
                    self.assertFalse(runner.retryable_failure({**row, 'status': status}, manifest))
                changed = deepcopy(row)
                changed['error']['provider_error']['error']['details'][0]['reason'] = 'IAM_PERMISSION_DENIED'
                self.assertFalse(runner.retryable_failure(changed, manifest))

    def test_resume_and_billing_recovery_preserve_history_without_duplicate_successes(self):
        for runner, retry in ((run_gemini, retry_gemini), (run_gemini_flash, retry_gemini_flash)):
            with self.subTest(model=runner.MODEL), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)/runner.RUN_ID
                runner.prepare(folder)
                manifest, all_tasks, all_prompts, validator = runner.load_inputs(folder)
                tasks = {f: dict(list(rows.items())[:1]) for f, rows in all_tasks.items()}
                prompts = {(f, k): all_prompts[f, k] for f in tasks for k in tasks[f]}
                historical = old_api(runner)
                current_api = deepcopy(manifest['api'])
                manifest['api'] = historical
                manifest['execution']['project_migrations'] = [{'previous_api': historical}]
                (folder/'manifest.json').write_text(json.dumps(manifest))
                calls = []
                original_client = httpx.Client

                def serve(request):
                    body = json.loads(request.content)
                    calls.append((str(request.url), request.headers['X-Goog-User-Project'], body))
                    if len(calls) == 1:
                        return httpx.Response(403, json={'error': {'code': 403,
                            'status': 'PERMISSION_DENIED', 'details': [{'reason': 'BILLING_DISABLED'}]}})
                    gold = next(t['gold_devanagari'][0] for f in tasks for k, t in tasks[f].items()
                                if prompts[f, k] == body['contents'][0]['parts'][0]['text'])
                    return httpx.Response(200, json={'modelVersion': runner.MODEL,
                        'candidates': [{'content': {'parts': [{'text': f'<answer>{gold}</answer>'}]},
                                        'finishReason': 'STOP'}],
                        'usageMetadata': {'promptTokenCount': 200, 'candidatesTokenCount': 100,
                                          'thoughtsTokenCount': 900, 'totalTokenCount': 1200,
                                          'trafficType': 'ON_DEMAND'}})

                def load(path):
                    return json.loads((path/'manifest.json').read_bytes()), tasks, prompts, validator

                token = type('FixtureToken', (), {'get': lambda self: 'private-fixture'})()
                with patch.object(runner, 'load_inputs', side_effect=load), \
                     patch.object(runner.httpx, 'Client', side_effect=lambda **kw: original_client(transport=httpx.MockTransport(serve))), \
                     patch.object(runner, 'ADCToken', return_value=token):
                    runner.run(folder, concurrency=1, budget=10, max_new=1)
                    manifest = json.loads((folder/'manifest.json').read_bytes())
                    self.assertEqual(manifest['status'], 'paused')
                    failed = next(r for f in tasks for r in json.loads((folder/f'{f}.json').read_bytes()))
                    self.assertEqual(failed['status'], 'api_error')
                    manifest['api'] = current_api
                    manifest['execution']['reviewed_infrastructure_failures'] = [review(failed)]
                    (folder/'manifest.json').write_text(json.dumps(manifest))
                    runner.run(folder, concurrency=1, budget=10)
                    before = {f: json.loads((folder/f'{f}.json').read_bytes()) for f in tasks}
                    retry.retry_failed(folder, 'reviewed-billing-recovery', 1, concurrency=1, budget=10)
                    retry.retry_failed(folder, 'reviewed-billing-recovery', 1, concurrency=1, budget=10)
                    result = runner.inspect(folder, verify=True)
                self.assertEqual(len(calls), 5)
                self.assertEqual(calls[0][0], historical['url'])
                self.assertEqual(calls[0][1], runner.PREVIOUS_PROJECT)
                self.assertTrue(all(url == runner.ENDPOINT and project == runner.PROJECT
                                    for url, project, _ in calls[1:]))
                self.assertEqual(result['unresolved'], 0)
                self.assertEqual(result['attempts_settled'], 5)
                for family in tasks:
                    after = json.loads((folder/f'{family}.json').read_bytes())
                    self.assertTrue(after[0]['correct'])
                    if before[family][0]['status'] == 'completed':
                        self.assertEqual(after, before[family])
                    else:
                        self.assertEqual(after[0]['attempt_number'], 2)


if __name__ == '__main__':
    unittest.main()
