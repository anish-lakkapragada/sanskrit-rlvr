"""Offline billing/transport tests; no provider clients or real ledger writes."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from misc import vp_ending_screen_run as c


def receipt(stop='end_turn'):
    return dict(id='msg-fixture',type='message',model='claude-opus-5-5',stop_reason=stop,
                usage=dict(input_tokens=401,output_tokens=100,cache_creation_input_tokens=0,
                           cache_read_input_tokens=0,service_tier='standard',inference_geo='global'))


class FakeSDK:
    def __init__(self,directory,body):
        self.directory=directory;self.body=body;self.calls=[];self.options=[];self.max_retries=0
        self.messages=self;self.with_raw_response=self

    def with_options(self,**options):self.options.append(options);return self

    def create(self,**params):
        saved=json.loads((self.directory/'task-00000.effective-request.json').read_text())
        assert saved['params']==params and saved['effective_body_digest']==c.r.digest(params)
        self.calls.append(params)
        return SimpleNamespace(status_code=200,headers=SimpleNamespace(multi_items=lambda:[]),
                               http_response=SimpleNamespace(json=lambda:copy.deepcopy(self.body)))


class TransportTests(unittest.TestCase):
    def test_terminal_receipts(self):
        for stop in ['end_turn','max_tokens','stop_sequence','refusal','model_context_window_exceeded']:
            self.assertEqual(c.validate_receipt(receipt(stop))['output_tokens'],100)

    def test_malformed_billing_rejected(self):
        changes=[lambda b:b['usage'].pop('input_tokens'),lambda b:b['usage'].pop('output_tokens'),
                 lambda b:b['usage'].update(input_tokens=True),lambda b:b['usage'].update(input_tokens=-1),
                 lambda b:b['usage'].update(input_tokens=1501),lambda b:b['usage'].update(output_tokens=65537),
                 lambda b:b['usage'].update(output_tokens=1.5),lambda b:b['usage'].update(cache_creation_input_tokens=1),
                 lambda b:b['usage'].update(cache_read_input_tokens=1),lambda b:b['usage'].update(service_tier='priority'),
                 lambda b:b['usage'].update(inference_geo='us'),lambda b:b.pop('id'),
                 lambda b:b.update(model='wrong'),lambda b:b.update(type='error'),lambda b:b.update(stop_reason='tool_use')]
        for change in changes:
            b=receipt();change(b)
            with self.assertRaises(ValueError):c.validate_receipt(b)

    def exercise(self,body,invalid=False):
        with tempfile.TemporaryDirectory() as td,patch.object(c.r,'OUT',Path(td)),patch.object(c,'load_plan') as check_plan:
            d=Path(td)/'jobs'/c.JOB
            params={'model':'claude-opus-5-5','messages':[{'role':'user','content':'fixture'}]}
            req={'custom_id':'task-00000','params':params};before=copy.deepcopy(req)
            sdk=FakeSDK(d,body);w=c.StandardClient(sdk,[req]).with_options(timeout=600)
            if invalid:
                with self.assertRaises(ValueError):w.messages.with_raw_response.create(**params)
            else:w.messages.with_raw_response.create(**params)
            self.assertEqual(req,before);self.assertEqual(sdk.max_retries,0)
            self.assertEqual(sdk.calls,[dict(params,service_tier='standard_only',inference_geo='global')])
            self.assertTrue((d/'task-00000.effective.http.json').exists())
            self.assertFalse((d/'task-00000.result.json').exists())
            with self.assertRaises(ValueError):w.create(**params)
            self.assertEqual(len(sdk.calls),1)
            self.assertEqual(check_plan.call_count,2)

    def test_durable_request_and_no_replay(self):self.exercise(receipt('max_tokens'))

    def test_bad_receipt_is_preserved_without_settlement(self):
        b=receipt();b['usage'].pop('output_tokens');self.exercise(b,True)

    def test_whole96_budget_boundary(self):
        s=copy.deepcopy(c.r.load());job=dict(id=c.JOB,provider='Anthropic',phase='confirm_64k',n=96,
                                           transport='direct',attempted_at=None,spending_pool_id=c.POOL)
        s.setdefault('submission_pools',{})[c.POOL]={'provider':'Anthropic','cap_micro':c.CAP,'job_ids':[c.JOB]}
        self.assertEqual(c.r.budget_gate(s,job),126_405_120)
        s['submission_pools'][c.POOL]['cap_micro']-=1
        with self.assertRaises(ValueError):c.r.budget_gate(s,job)


if __name__=='__main__':unittest.main()
