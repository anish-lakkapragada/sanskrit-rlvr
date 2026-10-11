"""Offline fake-ledger/fake-SDK carry tests; no live outputs or API calls."""
import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
r=load('carry_driver',HERE/'continue.py')
old=load('old_tests',HERE.parent/'astra-concurrency-32/test_resume.py')
io,legacy,c=r.io,r.legacy,r.original


class CarryTests(unittest.TestCase):
    def setUp(self):
        # Reuse only temporary fixture construction; no live ledger reads.
        self.f=old.ResumeTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.directory,self.out,self.plan,self.requests,self.a=(self.f.directory,self.f.out,self.f.plan,self.f.requests,self.f.a)
        self.f.prepare(); previous=self.f.guard(); previous.adopt()
        self.overlay=self.directory/'astra-infrastructure-carry-01';self.overlay.mkdir()
        for key,value in [('KNOWN',2),('FINAL_N',40)]:
            p=patch.object(r,key,value);p.start();self.addCleanup(p.stop)
        self.a.reserve('OpenAI',2,self.plan['request_digests']['OpenAI'][2])
        self.a.fail('OpenAI',2,'RuntimeError')
        stem=self.directory/'receipts/OpenAI/00002'
        io.atomic_json(stem.with_suffix('.intent.json'),dict(request_digest=self.plan['request_digests']['OpenAI'][2],body=self.requests['OpenAI'][2]))
        io.atomic_json(stem.with_suffix('.error.json'),dict(type='InternalServerError',status_code=502,request_id='fixture502'))
        io.atomic_json(self.directory/'execution.json',dict(state='stopped_incomplete',providers=self.a.snapshot(),
            execution_plan_sha256=self.f.plan_sha,scheduling_amendment_sha256=previous.amendment_sha))
        for name in ['continue.py','test_continue.py','README.md']:(self.overlay/name).write_bytes((HERE/name).read_bytes())
        io.atomic_json(self.overlay/'independent-review.json',dict(passed=True,execution_plan_sha256=self.f.plan_sha,
            driver_sha256=io.sha256(self.overlay/'continue.py'),tests_sha256=io.sha256(self.overlay/'test_continue.py'),
            acknowledged_failure=dict(index=2,request_digest=self.plan['request_digests']['OpenAI'][2],
                intent_sha256=io.sha256(stem.with_suffix('.intent.json')),error_sha256=io.sha256(stem.with_suffix('.error.json')))))

    def prepare(self):return r.prepare(self.directory,self.overlay)
    def guard(self):return r.Guard(self.directory,self.overlay,self.plan,self.requests)
    def mutate(self,fn):self.f.mutate(fn)

    def test_prepare_is_read_only_and_preserves_full_failure(self):
        before=(self.out/'ledger.json').read_bytes();self.prepare()
        self.assertEqual(before,(self.out/'ledger.json').read_bytes())
        g=self.guard();g.adopt();state=legacy.load();j=g.accounting.job(state,'OpenAI')
        self.assertEqual(j['request_accounts']['2']['state'],'reserved_unknown')
        self.assertEqual(j['reservation_micro'],4000+3291800)
        self.assertEqual(len(state[r.prior.AMENDMENTS]),2)
        self.assertFalse(j['settled']);self.assertIsNone(j['collected_at'])
        g.adopt();self.assertEqual(len(legacy.load()[r.prior.AMENDMENTS]),2)

    def test_requires_exact502_no_http_no_extra_unknown(self):
        path=self.directory/'receipts/OpenAI/00002.error.json';before=path.read_bytes()
        io.atomic_json(path,dict(status_code=429))
        with self.assertRaisesRegex(ValueError,'HTTP502'):self.prepare()
        path.write_bytes(before)
        io.atomic_json(self.directory/'receipts/OpenAI/00002.http.json',dict(status_code=200))
        with self.assertRaisesRegex(ValueError,'HTTP502'):self.prepare()
        (self.directory/'receipts/OpenAI/00002.http.json').unlink()
        self.mutate(lambda s:s['jobs'][self.a.job_id('OpenAI')].pop('operational_failure'))
        self.a.reserve('OpenAI',3,self.plan['request_digests']['OpenAI'][3])
        self.a.fail('OpenAI',2,'RuntimeError')
        with self.assertRaisesRegex(ValueError,'Only exact'):self.prepare()

    def test_replay_and_modified_failure_or_amendment_refuse(self):
        self.prepare();g=self.guard();g.adopt()
        with self.assertRaisesRegex(ValueError,'never replay'):g.accounting.reserve('OpenAI',2,self.plan['request_digests']['OpenAI'][2])
        self.mutate(lambda s:s['jobs'][self.a.job_id('OpenAI')]['operational_failure'].update(error_type='changed'))
        with self.assertRaisesRegex(ValueError,'Acknowledged'):g.accounting.reserve('OpenAI',3,self.plan['request_digests']['OpenAI'][3])

    def test_31_new_plus_one_hold_and_exact_cap(self):
        self.prepare();g=self.guard();g.adopt();a=g.accounting
        for i in range(3,34):a.reserve('OpenAI',i,self.plan['request_digests']['OpenAI'][i])
        j=a.job(legacy.load(),'OpenAI')
        self.assertEqual(sum(x['state']=='reserved_unknown' for x in j['request_accounts'].values()),32)
        self.assertEqual(j['reservation_micro'],4000+32*3291800)
        with self.assertRaisesRegex(c.CapacityUnavailable,'window'):a.reserve('OpenAI',34,self.plan['request_digests']['OpenAI'][34])
        with self.assertRaisesRegex(ValueError,'Anthropic'):a.reserve('Anthropic',40,'x')

    def test_exact_lifetime_boundary_includes_original_hold(self):
        self.prepare();g=self.guard();g.adopt();a=g.accounting
        actual=a.job(legacy.load(),'OpenAI')['reservation_micro']
        self.mutate(lambda s:s['historical_spend_micro'].update(OpenAI=c.HARD_CAPS['OpenAI']-actual-c.maximum('OpenAI')+1))
        with self.assertRaisesRegex(c.CapacityUnavailable,'Lifetime'):a.reserve('OpenAI',3,self.plan['request_digests']['OpenAI'][3])
        self.mutate(lambda s:s['historical_spend_micro'].update(OpenAI=s['historical_spend_micro']['OpenAI']-1))
        a.reserve('OpenAI',3,self.plan['request_digests']['OpenAI'][3])
        self.assertEqual(legacy.committed(legacy.load(),'OpenAI'),c.HARD_CAPS['OpenAI'])

    def fake_execute(self,callback):
        outer=self
        class Client:
            api_key='fake'
            def __init__(self,p):
                assert p=='OpenAI';self.responses=self.with_raw_response=self
            def with_options(self,**kw):
                assert kw==dict(timeout=600.0,max_retries=0);return self
            def create(self,**body):
                i=body['index'];assert i>=3
                with c.transaction(timeout=.5):
                    state=legacy.load();assert len(state[r.prior.AMENDMENTS])==2
                    assert state['jobs'][outer.a.job_id('OpenAI')]['request_accounts'][str(i)]['state']=='reserved_unknown'
                assert io.read_json(outer.directory/'receipts/OpenAI'/f'{i:05d}.intent.json')['body']==body
                value=callback(i);headers=SimpleNamespace(multi_items=lambda:[])
                return SimpleNamespace(status_code=200,headers=headers,http_response=SimpleNamespace(json=lambda:value))
        with patch.object(legacy,'client_for',side_effect=Client):return r.execute(self.directory,self.overlay)

    def test_31_simultaneous_suffix_no_replay_original_analyzer_stays_blocked(self):
        self.prepare();calls=[];lock=threading.Lock();event=threading.Event()
        def call(i):
            with lock:
                calls.append(i)
                if len(calls)==31:event.set()
            if i<34 and not event.wait(15):raise AssertionError('Expected31 active')
            return old.response('OpenAI',i)
        self.assertEqual(self.fake_execute(call),'complete_attempted_pending_paired_analysis')
        self.assertEqual(sorted(calls),list(range(3,40)))
        self.assertEqual(self.fake_execute(call),'complete_attempted_pending_paired_analysis');self.assertEqual(len(calls),37)
        snapshot=self.a.snapshot();self.assertFalse(snapshot['OpenAI']['complete'])
        self.assertEqual(snapshot['OpenAI']['terminal_usage'],39)
        j=self.a.job(legacy.load(),'OpenAI');self.assertEqual(j['request_accounts']['2']['state'],'reserved_unknown')
        self.assertEqual(j['operational_failure']['index'],2)
        status=io.read_json(self.directory/'execution.json');self.assertFalse(status['scores_visible'])
        self.assertEqual(status['runtime_concurrency'],{'Anthropic':0,'OpenAI':31})

    def test_novel_error_preserves_original_failure_and_stops_restart(self):
        self.prepare();original=legacy.load()['jobs'][self.a.job_id('OpenAI')]['operational_failure'];calls=[]
        def call(i):
            calls.append(i)
            if i==3:raise TimeoutError('uncertain')
            return old.response('OpenAI',i)
        self.assertEqual(self.fake_execute(call),'stopped_incomplete')
        j=legacy.load()['jobs'][self.a.job_id('OpenAI')]
        self.assertEqual(j['operational_failure'],original);self.assertTrue(j[r.NOVEL])
        self.assertEqual(j['request_accounts']['3']['state'],'reserved_unknown')
        self.assertEqual(len(calls),len(set(calls)))
        with self.assertRaisesRegex(ValueError,'Novel'):self.fake_execute(call)

    def test_error_evidence_and_newcode_tamper_refuse(self):
        self.prepare();path=self.directory/'receipts/OpenAI/00002.error.json';path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.guard()


if __name__=='__main__':unittest.main()
