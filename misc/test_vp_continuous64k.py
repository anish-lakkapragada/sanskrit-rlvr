"""Offline financial/crash/concurrency checks; no live ledger or provider calls."""
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from misc import vp_continuous64k as c
from misc import vp_goal as legacy, oai_batch_eval as io


def receipt(provider, index=0):
    usage = dict(input_tokens=100, output_tokens=20)
    if provider == 'Anthropic':
        return dict(id=f'msg-{index}', type='message', model='claude-opus-5-5',
                    stop_reason='end_turn', usage=dict(usage, service_tier='standard', inference_geo='global'))
    return dict(id=f'resp-{index}', model='gpt-6-astra', status='completed',
                service_tier='default', usage=dict(usage, total_tokens=120))


class AccountingTests(unittest.TestCase):
    def setUp(self):
        # Copy genuine immutable authorization/dependency declarations, but every
        # test mutation uses a fresh temporary ledger and fake receipt bodies.
        state = copy.deepcopy(legacy.load())
        state.update(jobs={}, status='review_confirm_64k',
                     historical_spend_micro={'Anthropic':311430394, 'OpenAI':801130500})
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.patch = patch.object(legacy, 'OUT', self.out)
        self.patch.start(); self.addCleanup(self.patch.stop)
        io.atomic_json(self.out/'ledger.json', state)
        self.plan = dict(run_id='fixture-final', n=4,
            pool_caps_micro={'Anthropic':10_000_000, 'OpenAI':20_000_000},
            concurrency={'Anthropic':2, 'OpenAI':2},
            protected_allocation=legacy.protected_allocations(state))
        self.tasks = [dict(id=f'test-{i}') for i in range(4)]
        self.plan.update(fixed_task_ids=[t['id'] for t in self.tasks],tasks_digest=legacy.digest(self.tasks),
                         request_digests={p:[f'request{i}' for i in range(4)] for p in c.HARD_CAPS})
        self.a = c.Accounting(self.plan, 'frozen-plan-sha')
        # Linguistic input checking is independently covered by manifest tests;
        # these unit fixtures exercise financial and operational behavior only.
        with patch('misc.vp_goal_validate.validate'):
            self.a.register(self.tasks)

    def mutate(self, fn):
        with c.transaction():
            s = legacy.load(); fn(s); legacy.save(s)

    def test_legacy_caps_and_collector_see_liability_without_collecting(self):
        before = legacy.committed(legacy.load(), 'OpenAI')
        self.a.reserve('OpenAI', 0, 'request0')
        state = legacy.load()
        self.assertEqual(legacy.committed(state, 'OpenAI')-before, 3291800)
        self.assertEqual([j for j in state['jobs'].values() if j['batch_id'] and not j.get('collected_at')], [])
        with self.assertRaisesRegex(ValueError, 'halted'):
            legacy.budget_gate(state, dict(provider='OpenAI', phase='confirm_64k',
                transport='direct', n=1, attempted_at=None))

    def test_exact_global_cap_and_one_micro_over_cap(self):
        def update(s):
            s['historical_spend_micro']['OpenAI'] = c.HARD_CAPS['OpenAI']-legacy.protected_remaining(s,'OpenAI')-c.maximum('OpenAI')
        self.mutate(update)
        self.a.reserve('OpenAI', 0, 'request0')
        s=legacy.load()
        self.assertEqual(legacy.committed(s,'OpenAI')+legacy.protected_remaining(s,'OpenAI'),2_000_000_000)
        with self.assertRaises(c.CapacityUnavailable): self.a.reserve('OpenAI',1,'request1')

    def test_pool_ceiling_and_reclaimed_known_usage(self):
        self.plan['pool_caps_micro']['OpenAI'] = c.maximum('OpenAI')+2000
        self.a.reserve('OpenAI',0,'request0')
        with self.assertRaises(c.CapacityUnavailable): self.a.reserve('OpenAI',1,'request1')
        self.a.settle('OpenAI',0,'request0',receipt('OpenAI'), 'receipt0')
        self.a.reserve('OpenAI',1,'request1')
        self.assertEqual(self.a.snapshot()['OpenAI']['admitted'],2)

    def test_concurrent_duplicate_admission_has_one_winner(self):
        def enter(_):
            try: self.a.reserve('Anthropic',0,'request0'); return True
            except ValueError: return False
        with ThreadPoolExecutor(max_workers=12) as pool:
            outcomes=list(pool.map(enter, range(12)))
        self.assertEqual(sum(outcomes),1)
        self.assertEqual(self.a.snapshot()['Anthropic']['admitted'],1)
        self.assertEqual(self.a.snapshot()['Anthropic']['committed_usd'],1.31672)

    def test_partial_usage_not_cohort_completion(self):
        self.a.reserve('Anthropic',0,'request0')
        self.a.settle('Anthropic',0,'request0',receipt('Anthropic'), 'receipt0')
        s=self.a.snapshot()['Anthropic']
        self.assertEqual(s['terminal_usage'],1)
        self.assertFalse(s['complete'])
        j=legacy.load()['jobs'][self.a.job_id('Anthropic')]
        self.assertNotIn('summary',j)
        self.assertNotIn('completed_correct',j)
        self.assertEqual(j['reservation_micro'],800)
        self.assertIsNone(j['collected_at'])

    def test_malformed_usage_keeps_full_maximum(self):
        self.a.reserve('OpenAI',0,'request0')
        for usage in [{}, {'input_tokens':100,'output_tokens':False,'total_tokens':100},
                      {'input_tokens':100,'output_tokens':65537,'total_tokens':65637}]:
            bad=receipt('OpenAI');bad['usage']=usage
            with self.assertRaises(ValueError): self.a.settle('OpenAI',0,'request0',bad,'bad')
        self.assertEqual(self.a.snapshot()['OpenAI']['committed_usd'],3.2918)
        self.assertEqual(self.a.snapshot()['OpenAI']['terminal_usage'],0)

    def test_unknown_request_and_process_restart_never_replay(self):
        self.a.reserve('Anthropic',0,'request0')
        other=c.Accounting(self.plan,'frozen-plan-sha')
        with self.assertRaisesRegex(ValueError,'never replay'): other.reserve('Anthropic',0,'request0')
        self.a.fail('Anthropic',0,'TimeoutError')
        with self.assertRaisesRegex(ValueError,'operational failure'): other.reserve('Anthropic',1,'request1')
        self.assertEqual(other.snapshot()['Anthropic']['committed_usd'],1.31672)

    def test_rejected_receipt_above_token_ceiling_increases_known_liability(self):
        self.a.reserve('OpenAI',0,'request0')
        bad=receipt('OpenAI');bad['usage']=dict(input_tokens=100,output_tokens=70000,total_tokens=70100)
        with self.assertRaises(ValueError):self.a.settle('OpenAI',0,'request0',bad,'bad')
        self.a.fail('OpenAI',0,'ReceiptPolicyViolation',bad)
        self.assertEqual(self.a.snapshot()['OpenAI']['committed_usd'],3.501)
        self.assertEqual(self.a.snapshot()['OpenAI']['terminal_usage'],0)
        with self.assertRaises(ValueError):self.a.reserve('OpenAI',1,'request1')

    def test_response_identity_and_digest_cannot_cross_questions(self):
        self.a.reserve('OpenAI',0,'request0')
        with self.assertRaises(ValueError): self.a.settle('OpenAI',0,'other',receipt('OpenAI'),'sha')
        self.a.settle('OpenAI',0,'request0',receipt('OpenAI'),'sha0')
        self.a.reserve('OpenAI',1,'request1')
        with self.assertRaisesRegex(ValueError,'reused'): self.a.settle('OpenAI',1,'request1',receipt('OpenAI'),'sha0')
        self.assertEqual(self.a.snapshot()['OpenAI']['terminal_usage'],1)

    def test_concurrent_settlements_preserve_other_provider_and_legacy_jobs(self):
        for provider in c.HARD_CAPS:
            for i in range(2): self.a.reserve(provider,i,f'request{i}')
        self.mutate(lambda s: s['jobs'].update(legacy_prepared=dict(provider='Anthropic',phase='explore',
            reservation_micro=0,attempted_at=None,batch_id=None,n=1)))
        def settle(pair):
            p,i=pair;self.a.settle(p,i,f'request{i}',receipt(p,i),f'receipt-{p}-{i}')
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(settle,[(p,i) for p in c.HARD_CAPS for i in range(2)]))
        state=legacy.load()
        self.assertIn('legacy_prepared',state['jobs'])
        self.assertTrue(all(x['terminal_usage']==2 for x in self.a.snapshot().values()))

    def test_fence_reserve_or_plan_changes_fail_closed(self):
        before=legacy.load()
        for change in [lambda s:s.update(status='running_other'),
                       lambda s:s['jobs'][self.a.job_id('Anthropic')].update(execution_plan_sha256='changed'),
                       lambda s:s['jobs'][self.a.job_id('Anthropic')].update(reservation_micro=1)]:
            self.mutate(change)
            with self.assertRaises(ValueError):self.a.reserve('Anthropic',0,'request0')
            io.atomic_json(self.out/'ledger.json',before)

    def test_false_aggregate_settlement_or_request_rewriting_cannot_release_credits(self):
        self.a.reserve('OpenAI',0,'request0')
        before=legacy.load()
        def job(s):return s['jobs'][self.a.job_id('OpenAI')]
        changes=[lambda s:job(s).update(settled=True),
                 lambda s:job(s).update(actual_cost_upper_micro=-1),
                 lambda s:job(s).update(collected_at='false-completion'),
                 lambda s:job(s).update(fixed_task_ids=['different']),
                 lambda s:job(s)['request_accounts']['0'].update(request_digest='different'),
                 lambda s:job(s)['request_accounts']['0'].update(maximum_cost_micro=1),
                 lambda s:job(s)['request_accounts']['0'].update(actual_cost_upper_micro=0)]
        for change in changes:
            self.mutate(change)
            with self.assertRaises(ValueError):self.a.reserve('OpenAI',1,'request1')
            io.atomic_json(self.out/'ledger.json',before)

    def test_full_cohort_can_settle_without_exposing_scores(self):
        for provider in c.HARD_CAPS:
            for i in range(4):
                self.a.reserve(provider,i,f'request{i}')
                self.a.settle(provider,i,f'request{i}',receipt(provider,i),f'receipt{i}')
        snapshot=self.a.snapshot()
        self.assertTrue(all(s['complete'] and s['admitted']==4 for s in snapshot.values()))
        self.assertTrue(all(j['batch_id'] is None and 'summary' not in j for j in legacy.load()['jobs'].values()))

    def execute_fake(self, callback, *, repeat=False):
        directory=self.out/'fake-execution';directory.mkdir()
        requests={p:[{'index':i} for i in range(4)] for p in c.HARD_CAPS}
        self.plan.update(dependencies={},request_digests={p:[legacy.digest(x) for x in rows] for p,rows in requests.items()})
        io.atomic_json(directory/'execution-plan.json',self.plan)
        self.mutate(lambda s:s.update(jobs={},status='review_confirm_64k'))
        class Client:
            api_key='fake-no-secret'
            def __init__(self,provider):
                self.provider=provider;self.messages=self;self.responses=self;self.with_raw_response=self
            def with_options(self,**options):
                assert options['max_retries']==0 and options['timeout']==600.0
                return self
            def create(self,**body):
                # Prove the network operation does not hold the shared ledger lock.
                with c.transaction(timeout=.1):pass
                index=body['index']
                intent=io.read_json(directory/'receipts'/self.provider/f'{index:05d}.intent.json')
                account=legacy.load()['jobs'][self_outer.a.job_id(self.provider)]['request_accounts'][str(index)]
                assert intent['request_digest']==legacy.digest(body)==account['request_digest']
                assert account['state']=='reserved_unknown'
                result=callback(self.provider,index)
                headers=SimpleNamespace(multi_items=lambda:[])
                return SimpleNamespace(status_code=200,headers=headers,http_response=SimpleNamespace(json=lambda:result,headers=headers))
        self_outer=self
        with patch.object(c,'inspect_manifest',return_value=(self.plan,self.tasks,requests)), \
             patch('misc.vp_goal_validate.validate'),patch.object(legacy,'client_for',side_effect=Client):
            result=c.execute(directory)
            if repeat:
                result=c.execute(directory)
        return result,io.read_json(directory/'execution.json'),directory

    def test_continuous_scheduler_refills_before_slow_question_finishes(self):
        replacement_started=threading.Event();slow_done=threading.Event();observed=[]
        def call(provider,index):
            if provider=='Anthropic' and index==0:
                if not replacement_started.wait(3):raise AssertionError('Wave barrier remains')
                slow_done.set()
            if provider=='Anthropic' and index==2:
                observed.append(not slow_done.is_set());replacement_started.set()
            return receipt(provider,index)
        result,status,_=self.execute_fake(call)
        self.assertEqual(result,'complete_pending_paired_analysis')
        self.assertEqual(observed,[True])
        self.assertFalse(status['scores_visible'])
        self.assertTrue(all(x['terminal_usage']==4 for x in status['providers'].values()))

    def test_transport_failure_drains_outstanding_without_paid_retry(self):
        calls=[]
        def call(provider,index):
            calls.append((provider,index))
            if provider=='Anthropic' and index==0:raise TimeoutError('unknown')
            return receipt(provider,index)
        result,status,directory=self.execute_fake(call)
        self.assertEqual(result,'stopped_incomplete')
        self.assertEqual(len(calls),len(set(calls)))
        self.assertEqual(status['providers']['Anthropic']['admitted']-status['providers']['Anthropic']['terminal_usage'],1)
        self.assertTrue((directory/'receipts/Anthropic/00000.error.json').exists())
        self.assertFalse(status['scores_visible'])

    def test_completed_restart_performs_no_new_paid_calls(self):
        calls=[]
        def call(p,i):calls.append((p,i));return receipt(p,i)
        result,_,_=self.execute_fake(call,repeat=True)
        self.assertEqual(result,'complete_pending_paired_analysis')
        self.assertEqual(len(calls),8)
        self.assertEqual(len(set(calls)),8)

    def test_single_provider_completion_is_not_paired_completion(self):
        self.plan['pool_caps_micro']['OpenAI']=1
        result,status,_=self.execute_fake(receipt)
        self.assertEqual(result,'budget_limited_incomplete')
        self.assertTrue(status['providers']['Anthropic']['complete'])
        self.assertFalse(status['providers']['OpenAI']['complete'])
        self.assertEqual(status['providers']['OpenAI']['admitted'],0)


class ManifestTests(unittest.TestCase):
    """Exact-input binding tests; fixtures never register in the shared ledger."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.tasks=io.read_json(legacy.ROOT/'benchmarks/parallel-search-20261007/four_d-90/candidate-1800-v1/tasks.json')[:500]
        self.files={}
        def put(key,filename,data):
            path=self.directory/filename;io.atomic_json(path,data);self.files[key]=str(path)
        put('tasks_path','tasks.json',self.tasks)
        requests={p:[c.request_for(t,p,i) for i,t in enumerate(self.tasks)] for p in c.HARD_CAPS}
        put('requests_path','requests.json',requests)
        public=[dict(id=t['id'],prompt=b['messages'][0]['content']) for t,b in zip(self.tasks,requests['Anthropic'])]
        put('public_prompts_path','public.json',public)
        put('input_counts_path','counts.json',{p:dict(requests_digest=legacy.digest(rows),counts={str(i):300 for i in range(500)}) for p,rows in requests.items()})
        put('source_policy_path','source.json',{'fixture_only':True})
        for key in ['scorer_path','spelling_rules_path']:
            put(key,key+'.json',{'fixture_only':True})
        self.files['paired_analyzer_path']='misc/vp_continuous64k_analyze.py'
        task_sha=io.sha256(self.files['tasks_path']);source_sha=io.sha256(self.files['source_policy_path'])
        public_sha=io.sha256(self.files['public_prompts_path'])
        put('candidate_manifest_path','candidate.json',dict(n=500,tasks_sha256=task_sha,
            public_prompts_sha256=public_sha,source_policy_sha256=source_sha,
            dependencies={'misc/vp_cartesian_task.py':io.sha256(legacy.ROOT/'misc/vp_cartesian_task.py')}))
        put('input_review_path','input-review.json',dict(passed=True,tasks_sha256=task_sha,
            manifest_sha256=io.sha256(self.files['candidate_manifest_path']),
            public_prompts_sha256=public_sha,source_policy_sha256=source_sha))
        put('alias_policy_path','aliases.json',dict(task_count=500,canonical_tasks_sha256=task_sha,
            items=[dict(task_id=t['id'],canonical_forms_slp1=t['gold_slp1'],canonical_forms_devanagari=t['gold_devanagari']) for t in self.tasks]))
        scorer_sha=io.sha256(self.files['scorer_path']);policy_sha=io.sha256(self.files['alias_policy_path'])
        put('scoring_review_path','spelling-review.json',dict(passed=True,tasks_sha256=task_sha,policy_sha256=policy_sha,scorer_sha256=scorer_sha))
        put('scoring_adoption_path','adoption.json',dict(candidate_tasks_sha256=task_sha,
            scorer_sha256=scorer_sha,alias_policy_sha256=policy_sha,
            independent_review_sha256=io.sha256(self.files['scoring_review_path'])))
        code=['misc/vp_continuous64k.py','misc/vp_goal.py','misc/vp_goal_validate.py','misc/vp_cartesian_task.py',
              'misc/vp_cartesian_prompt_v1.py','misc/oai_batch_eval.py','misc/ant_batch_eval.py',
              'misc/vp_simple_astra_compare.py','misc/vp_ending_screen_run.py','finetune/prompts.py',
              'misc/vp_simple_search_analyze.py','misc/vp_cartesian_final_analyze.py',
              'misc/vp_cartesian_analyze.py','misc/vp_goal_stats.py','misc/vp_cartesian_visibility.py',
              'prompts/v2/vp_task_eval.txt','benchmarks/creation-campaign-20261006/family-split.json']
        self.plan=dict(schema=c.VERSION,phase=c.PHASE,split='test',run_id='manifest-fixture',n=500,
            provider_caps_micro=c.HARD_CAPS,rates_micro_per_token={p:list(v) for p,v in c.RATES.items()},
            effort='xhigh',max_output_tokens=65536,pool_caps_micro={'Anthropic':100000000,'OpenAI':200000000},
            concurrency={'Anthropic':16,'OpenAI':16},fixed_task_ids=[t['id'] for t in self.tasks],
            tasks_digest=legacy.digest(self.tasks),request_digests={p:[legacy.digest(x) for x in rows] for p,rows in requests.items()},
            dependencies={name:io.sha256(legacy.ROOT/name) for name in code},**self.files)
        self.plan['dependencies'].update({path:io.sha256(legacy.ROOT/path) for path in self.files.values()})
        self.write_plan()

    def write_plan(self):
        io.atomic_json(self.directory/'execution-plan.json',self.plan)
        io.atomic_json(self.directory/'execution-review.json',dict(passed=True,
            execution_plan_sha256=io.sha256(self.directory/'execution-plan.json'),
            independent_input_review_sha256=io.sha256(self.files['input_review_path']),
            test_split_verified=True,source_scoring_review_passed=True,
            precision_limitations_declared='Fixture only; no release or new-family precision claim.'))

    def change_file(self,key,mutate):
        path=self.files[key];value=io.read_json(path);mutate(value);io.atomic_json(path,value)
        self.plan['dependencies'][path]=io.sha256(path);self.write_plan()

    def test_exact_bound_fixture_passes_without_instantiating_provider(self):
        with patch.object(legacy,'client_for') as client:
            plan,tasks,_=c.inspect_manifest(self.directory)
        self.assertEqual(plan['n'],500);self.assertEqual(len(tasks),500);client.assert_not_called()

    def test_same_shape_review_from_another_candidate_is_rejected(self):
        self.change_file('input_review_path',lambda d:d.update(tasks_sha256='another-candidate'))
        with self.assertRaisesRegex(ValueError,'Independent input review'):c.inspect_manifest(self.directory)

    def test_request_edit_rejected_even_if_file_hash_is_updated(self):
        self.change_file('requests_path',lambda d:d['OpenAI'][0].update(max_output_tokens=16384))
        with self.assertRaisesRegex(ValueError,'Frozen requests'):c.inspect_manifest(self.directory)

    def test_canonical_answer_rewrite_is_not_a_spelling_alias(self):
        self.change_file('alias_policy_path',lambda d:d['items'][0].update(canonical_forms_slp1=['wrong']))
        with self.assertRaisesRegex(ValueError,'canonical membership'):c.inspect_manifest(self.directory)

    def test_changed_scoring_review_cannot_inherit_adoption(self):
        self.change_file('scoring_review_path',lambda d:d.update(passed=False))
        with self.assertRaisesRegex(ValueError,'Independent scoring review'):c.inspect_manifest(self.directory)

    def test_missing_independent_execution_review_blocks_paid_entry(self):
        (self.directory/'execution-review.json').unlink()
        with patch.object(legacy,'client_for') as client:
            with self.assertRaises(FileNotFoundError):c.execute(self.directory)
            client.assert_not_called()

    def test_dependency_edit_and_excess_concurrency_fail_closed(self):
        io.atomic_json(self.files['source_policy_path'],{'changed':True})
        with self.assertRaisesRegex(ValueError,'Frozen final dependency'):c.inspect_manifest(self.directory)
        self.plan['concurrency']={'Anthropic':32,'OpenAI':32};self.write_plan()
        with self.assertRaisesRegex(ValueError,'At most32'):c.inspect_manifest(self.directory)


if __name__ == '__main__':
    unittest.main()
