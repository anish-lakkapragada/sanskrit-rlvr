"""Additive fake-client test receipt; no real API or ledger mutation."""
from pathlib import Path
import datetime, hashlib, io as textio, json, sys, unittest
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from misc import vp_continuous64k as c, vp_continuous64k_analyze as a, vp_goal as legacy, oai_batch_eval as io
from misc import test_vp_continuous64k as tc, test_vp_continuous64k_analyze as ta
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class IndependentPairedTest(unittest.TestCase):
    def test_fake_complete_pair_canonical_alias_pending_and_receipt_binding(self):
        fixture=tc.AccountingTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        candidate=ROOT/'benchmarks/parallel-search-20261007/four_d-90/candidate-1800-v1'
        tasks=io.read_json(candidate/'tasks.json');aliases=io.read_json(candidate/'spelling-policy-proposal/alias-policy.json')
        tm={t['id']:t for t in tasks};items=[i for i in aliases['items'] if i['aliases_devanagari']][:4]
        fixture.tasks=[tm[i['task_id']] for i in items]
        fixture.plan.update(fixed_task_ids=[t['id'] for t in fixture.tasks],tasks_digest=legacy.digest(fixture.tasks),
            scorer_path=str((candidate/'spelling-policy-proposal/scorer.py').relative_to(ROOT)))
        texts=['<answer>'+fixture.tasks[0]['gold_devanagari'][0]+'</answer>',
               '<answer>'+items[1]['aliases_devanagari'][0]+'</answer>',
               '<answer>UNRECOGNIZED_FIXTURE</answer>','unparsed fixture']
        def callback(provider,index):
            body=tc.receipt(provider,index)
            if provider=='Anthropic':body['content']=[{'type':'text','text':texts[index]}]
            else:body['output']=[{'type':'message','role':'assistant','content':[{'type':'output_text','text':texts[index]}]}]
            return body
        state,execution,directory=fixture.execute_fake(callback)
        self.assertEqual(state,'complete_pending_paired_analysis')
        requests={p:[{'index':i} for i in range(4)] for p in c.HARD_CAPS}
        with patch.object(c,'inspect_manifest',return_value=(fixture.plan,fixture.tasks,requests)):
            result=a.analyze(directory)
            self.assertEqual(result['n'],4);self.assertFalse(result['benchmark_ready'])
            for provider in c.HARD_CAPS:
                raw=io.read_json(directory/'results'/provider/'canonical.json')
                primary=io.read_json(directory/'results'/provider/'predeclared-spelling.json')
                self.assertEqual([r['is_correct'] for r in raw],[True,False,False,False])
                self.assertEqual([r['is_correct'] for r in primary],[True,True,False,False])
                self.assertEqual(len(result['spelling_changes'][provider]),1)
                self.assertEqual([r['task_id'] for r in result['unrecognized_usable_answers'][provider]],[fixture.tasks[2]['id']])
                self.assertEqual(result['primary'][provider]['statistics']['completed_answer']['n'],3)
            self.assertEqual(result['paired']['all_request_accuracy_difference'],0)
            self.assertEqual(result['paired']['n_pairs'],4)
            receipt=directory/'receipts/Anthropic/00000.http.json'
            original=receipt.read_bytes();receipt.write_bytes(original+b' ')
            with self.assertRaisesRegex(ValueError,'Settled raw receipt changed'):a.analyze(directory)
            receipt.write_bytes(original)
            intent=directory/'receipts/Anthropic/00000.intent.json';v=io.read_json(intent);v['body']['index']=999;io.atomic_json(intent,v)
            with self.assertRaisesRegex(ValueError,'Actual paid request differs'):a.analyze(directory)

def main():
    files=['misc/vp_continuous64k.py','misc/vp_continuous64k_analyze.py','misc/test_vp_continuous64k.py','misc/test_vp_continuous64k_analyze.py','misc/vp_goal.py','misc/oai_batch_eval.py','misc/ant_batch_eval.py','misc/vp_simple_astra_compare.py','misc/vp_ending_screen_run.py']
    before={p:sha(ROOT/p) for p in files};ledger_path=legacy.OUT/'ledger.json';ledger_before=sha(ledger_path)
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(tc),unittest.defaultTestLoader.loadTestsFromModule(ta),unittest.defaultTestLoader.loadTestsFromTestCase(IndependentPairedTest)])
    stream=textio.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    assert before=={p:sha(ROOT/p) for p in before};assert ledger_before==sha(ledger_path)
    receipt=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=result.wasSuccessful(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),source_hashes=before,live_ledger_before_sha256=ledger_before,live_ledger_after_sha256=sha(ledger_path),live_ledger_unchanged=True,paid_calls=0,model_responses_read=False,test_log=stream.getvalue(),reviewer_script_sha256=sha(Path(__file__)),execution_authorized=False,benchmark_ready=False)
    (OUT/'continuous64k-independent-review-tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(stream.getvalue());print(json.dumps({k:receipt[k] for k in ['passed','tests_run','failures','errors','live_ledger_unchanged']}))
    if not result.wasSuccessful():raise SystemExit(1)
if __name__=='__main__':main()
