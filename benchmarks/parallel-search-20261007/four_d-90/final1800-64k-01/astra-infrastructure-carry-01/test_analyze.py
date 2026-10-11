"""Pure analysis-gate and missing-row sensitivity checks; no actual result reads."""
import copy
import contextlib
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('carry_analyzer',HERE/'analyze.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        for key,value in [('KNOWN',2),('FINAL_N',8)]:
            p=patch.object(a.carry,key,value);p.start();self.addCleanup(p.stop)
        self.jobs={p:dict(request_accounts={str(i):dict(state='settled') for i in range(8)}) for p in ['Anthropic','OpenAI']}
        self.jobs['OpenAI']['request_accounts']['2']['state']='reserved_unknown'
        self.progress={'Anthropic':dict(complete=True,admitted=8,terminal_usage=8),
                       'OpenAI':dict(complete=False,admitted=8,terminal_usage=7)}
        self.tasks=[dict(id=f't{i}',campaign=dict(root_family=f'f{i//2}'),dhatu=dict(gana='Curadi')) for i in range(8)]
        self.rows=[dict(task=t,is_correct=i%3!=0,status='completed',answer='fake',truncated=False)
                   for i,t in enumerate(self.tasks)]
        self.rows[2].update(is_correct=None,status='infrastructure_error',answer=None)

    def test_exact_final_metadata_gate_without_responses(self):
        self.assertTrue(a.ready(self.progress,self.jobs))
        for edit in [lambda p,j:p['OpenAI'].update(admitted=7),
                     lambda p,j:p['OpenAI'].update(terminal_usage=6),
                     lambda p,j:p['Anthropic'].update(complete=False),
                     lambda p,j:j['OpenAI']['request_accounts']['3'].update(state='reserved_unknown'),
                     lambda p,j:j['OpenAI'].update(infrastructure_carry_new_failure=[dict(index=3)]),
                     lambda p,j:j['OpenAI']['request_accounts'].pop('7')]:
            progress,jobs=copy.deepcopy(self.progress),copy.deepcopy(self.jobs);edit(progress,jobs)
            self.assertFalse(a.ready(progress,jobs))

    def test_both_imputations_preserve_raw_hole_and_genuine_usable_count(self):
        before=copy.deepcopy(self.rows);result=a.sensitivity(self.tasks,self.rows,repetitions=1000)
        low=result['missing_incorrect']['statistics'];high=result['missing_correct']['statistics']
        self.assertEqual(self.rows,before);self.assertIsNone(self.rows[2]['is_correct'])
        self.assertEqual(low['all_request']['n'],8);self.assertEqual(high['all_request']['n'],8)
        self.assertEqual(high['all_request']['accuracy']-low['all_request']['accuracy'],1/8)
        self.assertEqual(low['completed_answer'],high['completed_answer'])
        self.assertEqual(low['completed_answer']['n'],7)
        self.assertIsNotNone(high['all_request']['root_cluster_sandwich_standard_error'])
        self.assertIsNotNone(low['all_request']['iid_standard_error'])

    def test_upper_bound_and_both_precision_imputations_control_evidence(self):
        def stats(upper=.899,cluster=.009):
            row=dict(accuracy=.88,iid_standard_error=.007,root_cluster_sandwich_standard_error=cluster)
            return dict(missing_answer_accuracy_bounds=[.88,upper],all_request=row.copy(),completed_answer=row.copy())
        models={p:dict(statistics=stats()) for p in ['Anthropic','OpenAI']}
        imputed={k:dict(statistics=stats()) for k in ['missing_incorrect','missing_correct']}
        result=a.numerical(models,imputed)
        self.assertFalse(result['both_references_complete']);self.assertFalse(result['original_complete_gate_met'])
        self.assertTrue(result['both_below_90_with_all_missing_answer_upper_bounds'])
        models['OpenAI']['statistics']['missing_answer_accuracy_bounds'][1]=.900
        imputed['missing_correct']['statistics']['all_request']['root_cluster_sandwich_standard_error']=.01
        result=a.numerical(models,imputed)
        self.assertFalse(result['both_below_90_with_all_missing_answer_upper_bounds'])
        self.assertFalse(result['both_family_se_below_one_pp'])

    def test_analyze_does_not_load_receipts_or_scorer_before_gate(self):
        progress=copy.deepcopy(self.progress);progress['OpenAI']['admitted']=7
        guard=SimpleNamespace(state=lambda *args,**kw:self.jobs,
                              accounting=SimpleNamespace(snapshot=lambda:progress))
        with patch.object(a.carry.prior,'coordinator',return_value=contextlib.nullcontext()), \
             patch.object(a.original,'inspect_manifest',return_value=({},self.tasks,{})), \
             patch.object(a.carry,'Guard',return_value=guard), \
             patch.object(a,'check_review'),patch.object(a.legacy,'load',return_value={}), \
             patch.object(a.carry,'receipt_bindings') as receipts, \
             patch.object(a.io,'read_json',side_effect=AssertionError('Premature output read')), \
             patch.object(a.io,'atomic_json') as write:
            result=a.analyze(HERE.parent,HERE)
        self.assertEqual(result['state'],'waiting_for_all_attempts_and_settled_remaining_receipts')
        self.assertFalse(result['scores_visible']);receipts.assert_not_called();write.assert_not_called()

    def test_analysis_review_binds_exact_amendment_and_executed_code(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            for name in ['analyze.py','test_analyze.py','continue.py']:(path/name).write_bytes((HERE/name).read_bytes())
            guard=SimpleNamespace(plan_sha='originalplan',amendment_sha='actualcarry')
            review=dict(passed=True,analyzer_sha256=a.io.sha256(path/'analyze.py'),
                        tests_sha256=a.io.sha256(path/'test_analyze.py'),driver_sha256=a.io.sha256(path/'continue.py'),
                        execution_plan_sha256='originalplan',continuation_amendment_sha256='actualcarry')
            a.io.atomic_json(path/'analysis-review.json',review);a.check_review(path,guard)
            review['continuation_amendment_sha256']='other';a.io.atomic_json(path/'analysis-review.json',review)
            with self.assertRaisesRegex(ValueError,'analysis review'):a.check_review(path,guard)

    def test_full_synthetic_assembly_retains_explicit_hole_and_separate_outputs(self):
        tasks=copy.deepcopy(self.tasks)
        for i,t in enumerate(tasks):
            t.update(task_type='cartesian_4d',gold_slp1=['ka'],gold_devanagari=['क'],
                     morphology=dict(lakara='Lat',prayoga='Kartari',purusha='Prathama',vacana='Eka'))
            t['campaign']['root_family']=f'f{i}'
        plan=dict(run_id='synthetic',scorer_path='never-loaded',request_digests={'OpenAI':['digest']*8})
        requests={p:[dict(index=i) for i in range(8)] for p in ['Anthropic','OpenAI']}
        guard=SimpleNamespace(state=lambda *args,**kw:self.jobs,plan_sha='plan',amendment_sha='carry',
                              accounting=SimpleNamespace(snapshot=lambda:self.progress))
        class Scorer:
            def grade(self,text,task_id):
                return dict(alias_aware_correct=text=='<answer>क</answer>',requires_source_adjudication=False,answer='क' if text else None)
        loader=SimpleNamespace(exec_module=lambda module:setattr(module,'FiniteScorer',Scorer))
        reads=[];writes={}
        def read(path):
            path=Path(path);reads.append(path)
            if path.name=='execution.json':return dict(state='complete_attempted_pending_paired_analysis',scheduling_amendment_sha256='carry')
            if path.suffix=='.json' and path.name.endswith('.http.json'):
                self.assertNotEqual(str(path).split('/')[-2:] , ['OpenAI','00002.http.json'])
                if path.parent.name=='Anthropic':return dict(body=dict(stop_reason='end_turn',content=[dict(type='text',text='<answer>क</answer>')]))
                return dict(body=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text='<answer>क</answer>')])]))
            raise AssertionError('Unexpected read '+str(path))
        def write(path,value):writes[str(path)]=copy.deepcopy(value)
        bindings={'OpenAI':[dict(error_sha256='original502') for _ in range(8)],'Anthropic':[]}
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);overlay=directory/'carry';overlay.mkdir()
            with patch.object(a.carry.prior,'coordinator',return_value=contextlib.nullcontext()), \
                 patch.object(a.original,'inspect_manifest',return_value=(plan,tasks,requests)), \
                 patch.object(a.carry,'Guard',return_value=guard),patch.object(a,'check_review'), \
                 patch.object(a.legacy,'load',return_value={}),patch.object(a.carry,'receipt_bindings',return_value=bindings), \
                 patch.object(a.io,'read_json',side_effect=read),patch.object(a.io,'atomic_json',side_effect=write), \
                 patch.object(a.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=loader)), \
                 patch.object(a.importlib.util,'module_from_spec',return_value=SimpleNamespace()):
                value=a.analyze(directory,overlay)
            self.assertFalse(value['numerical']['both_references_complete'])
            self.assertEqual(value['primary']['OpenAI']['statistics']['all_request']['n'],8)
            self.assertEqual(value['primary']['OpenAI']['statistics']['completed_answer']['n'],7)
            self.assertEqual(value['primary']['OpenAI']['statistics']['infrastructure_only_accuracy_bounds'],[7/8,1])
            raw=next(v for k,v in writes.items() if k.endswith('/OpenAI/canonical.json'))
            self.assertIsNone(raw[2]['is_correct']);self.assertIsNone(raw[2]['raw_batch_result'])
            self.assertEqual(raw[2]['status'],'infrastructure_error')
            self.assertTrue(all(str(overlay.resolve()) in k for k in writes))
            self.assertNotIn(str(directory.resolve()/'analysis.json'),writes)
            self.assertFalse(value['numerical']['both_below_90_with_all_missing_answer_upper_bounds'])


if __name__=='__main__':unittest.main()
