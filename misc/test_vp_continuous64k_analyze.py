import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from misc import vp_continuous64k_analyze as a
from misc import oai_batch_eval as io


class AnalyzerTests(unittest.TestCase):
    def test_incomplete_partner_does_not_read_answers_or_load_scorer(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);io.atomic_json(p/'execution-plan.json',{})
            progress={'Anthropic':{'complete':True},'OpenAI':{'complete':False}}
            with patch.object(a.execution,'inspect_manifest',return_value=({},[],{})), \
                 patch.object(a.execution.Accounting,'snapshot',return_value=progress), \
                 patch.object(a.execution.Accounting,'__init__',return_value=None), \
                 patch.object(a.io,'read_json',side_effect=AssertionError('Must not read answer files')), \
                 patch.object(a.importlib.util,'spec_from_file_location',side_effect=AssertionError('Must not load grader')):
                result=a.analyze(p)
            self.assertFalse(result['scores_visible'])
            self.assertFalse(result['benchmark_ready'])

    def test_unrecognized_usable_answers_require_review_without_overwriting_canonical(self):
        class Scorer:
            def grade(self,text,task_id):
                return dict(answer=text,alias_aware_correct=text=='licensed',requires_source_adjudication=text!='licensed')
        rows=[dict(task={'id':'one'},status='completed',answer='licensed',output_text='licensed',is_correct=False,truncated=False),
              dict(task={'id':'two'},status='completed',answer='unlisted',output_text='unlisted',is_correct=False,truncated=False),
              dict(task={'id':'three'},status='failed',answer=None,output_text='',is_correct=None,truncated=False)]
        scored,changes,pending=a.spelling_rows(rows,Scorer())
        self.assertFalse(rows[0]['is_correct']);self.assertTrue(scored[0]['is_correct'])
        self.assertEqual(len(changes),1)
        self.assertEqual([r['task_id'] for r in pending],['two'])
        self.assertIsNone(scored[2]['is_correct'])

    def test_iid_precision_does_not_stand_in_for_family_precision(self):
        st=dict(all_results_present=True,missing_answer_accuracy_bounds=[.85,.85],
            all_request=dict(accuracy=.85,iid_standard_error=.008,root_cluster_sandwich_standard_error=.03),
            completed_answer=dict(accuracy=.85,iid_standard_error=.008,root_cluster_sandwich_standard_error=.03))
        result=a.numerical_assessment({p:{'statistics':st} for p in ['Anthropic','OpenAI']})
        self.assertTrue(result['both_below_90_before_source_adjudication'])
        self.assertTrue(result['both_iid_se_below_one_pp'])
        self.assertFalse(result['both_family_se_below_one_pp'])
        self.assertFalse(result['benchmark_ready'])


if __name__=='__main__':unittest.main()
