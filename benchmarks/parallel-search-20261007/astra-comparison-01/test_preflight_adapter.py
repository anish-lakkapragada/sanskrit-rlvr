"""Offline fixture tests only. Never construct a provider client or touch a ledger."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from misc import vp_simple_astra_compare as c


def receipt(status='completed'):
 return dict(id='resp-fixture',model='gpt-6-astra',service_tier='default',status=status,
  usage=dict(input_tokens=10,output_tokens=20,total_tokens=30,
   input_tokens_details=dict(cached_tokens=0,cache_write_tokens=0),output_tokens_details=dict(reasoning_tokens=15)))


class FakeRaw:
 def __init__(self,body):
  self.http_response=SimpleNamespace(json=lambda:copy.deepcopy(body));self.status_code=200
  self.headers=SimpleNamespace(multi_items=lambda:[])


class FakeSDK:
 def __init__(self,directory,body,call_history=None):
  self.directory=directory;self.response=body;self.calls=[] if call_history is None else call_history
  self.responses=self;self.with_raw_response=self;self.max_retries=0;self.options=[]
 def with_options(self,**opts):
  self.options.append(opts);return self
 def create(self,**body):
  p=self.directory/'task-00000.effective-request.json'
  if not p.exists():raise AssertionError('SDK called before durable effective request')
  saved=json.loads(p.read_text());assert saved['body']==body and saved['effective_body_digest']==c.r.digest(body)
  self.calls.append(body);return FakeRaw(self.response)


class ReceiptTests(unittest.TestCase):
 def test_terminal_statuses(self):
  for status in ['completed','incomplete','failed','cancelled']:
   self.assertEqual(c.validate_receipt(receipt(status))['output_tokens'],20)
 def test_bad_receipts(self):
  mutations=[
   ('missing input',lambda b:b['usage'].pop('input_tokens')),
   ('missing output',lambda b:b['usage'].pop('output_tokens')),
   ('bool input',lambda b:b['usage'].update(input_tokens=True)),
   ('negative input',lambda b:b['usage'].update(input_tokens=-1)),
   ('negative output',lambda b:b['usage'].update(output_tokens=-1)),
   ('input overflow',lambda b:b['usage'].update(input_tokens=1501)),
   ('output overflow',lambda b:b['usage'].update(output_tokens=65537)),
   ('missing total',lambda b:b['usage'].pop('total_tokens')),
   ('wrong total',lambda b:b['usage'].update(total_tokens=31)),
   ('bool total',lambda b:b['usage'].update(total_tokens=True)),
   ('cache write',lambda b:b['usage']['input_tokens_details'].update(cache_write_tokens=1)),
   ('cache overflow',lambda b:b['usage']['input_tokens_details'].update(cached_tokens=11)),
   ('reasoning overflow',lambda b:b['usage']['output_tokens_details'].update(reasoning_tokens=21)),
   ('bool reasoning',lambda b:b['usage']['output_tokens_details'].update(reasoning_tokens=True)),
   ('wrong model',lambda b:b.update(model='another-model')),
   ('wrong tier',lambda b:b.update(service_tier='priority')),
   ('no identity',lambda b:b.pop('id')),
   ('nonterminal',lambda b:b.update(status='in_progress'))]
  for name,mutate in mutations:
   with self.subTest(name=name):
    b=receipt();mutate(b)
    with self.assertRaises(ValueError):c.validate_receipt(b)
 def test_effective_body_durable_and_no_replay(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);body={'model':'gpt-6-astra','input':[{'role':'user','content':'fixture'}]};request={'custom_id':'task-00000','body':body};before=copy.deepcopy(request)
   sdk=FakeSDK(d,receipt('incomplete'));wrapper=c.StandardClient(sdk,d,[request]).with_options(timeout=600)
   raw=wrapper.responses.with_raw_response.create(**body)
   self.assertEqual(request,before);self.assertEqual(sdk.max_retries,0);self.assertEqual(len(sdk.calls),1)
   self.assertEqual(sdk.calls[0],dict(body,service_tier='default'));self.assertTrue((d/'task-00000.effective.http.json').exists())
   self.assertEqual(raw.http_response.json()['status'],'incomplete')
   with self.assertRaises(ValueError):wrapper.create(**body)
   self.assertEqual(len(sdk.calls),1)
 def test_malformed_receipt_saved_but_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);body={'model':'gpt-6-astra','input':[]};request={'custom_id':'task-00000','body':body};bad=receipt();bad['usage'].pop('output_tokens')
   sdk=FakeSDK(d,bad);wrapper=c.StandardClient(sdk,d,[request])
   with self.assertRaises(ValueError):wrapper.create(**body)
   self.assertTrue((d/'task-00000.effective.http.json').exists());self.assertFalse((d/'task-00000.result.json').exists())
   with self.assertRaises(ValueError):wrapper.create(**body)
   self.assertEqual(len(sdk.calls),1)
 def test_unknown_body_and_duplicate_inputs(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);body={'model':'gpt-6-astra','input':[]};req={'custom_id':'task-00000','body':body};sdk=FakeSDK(d,receipt());w=c.StandardClient(sdk,d,[req])
   with self.assertRaises(KeyError):w.create(model='wrong',input=[])
   with self.assertRaises(ValueError):c.StandardClient(sdk,d,[req,dict(req,custom_id='task-00001')])
   self.assertEqual(sdk.calls,[])

if __name__=='__main__':unittest.main()
