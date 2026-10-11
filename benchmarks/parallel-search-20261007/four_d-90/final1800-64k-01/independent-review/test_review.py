"""Synthetic smoke checks only: never invoke the reviewer on the live run."""
from pathlib import Path
import copy,importlib.util,io,json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('independent_final_review',HERE/'review.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from misc import oai_batch_eval as oai, ant_batch_eval as ant
from misc.vp_cartesian_final_analyze import panel_statistics

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.item={'canonical_forms_devanagari':['भवति'],'aliases_devanagari':['भवत्ति']}
        self.plan={'n':1800};self.progress={p:dict(complete=True,fixed_n=1800,admitted=1800,terminal_usage=1800,operational_failure=None) for p in m.execution.HARD_CAPS}
    def test_incomplete_usage_does_not_open_primary_analysis(self):
        self.progress['OpenAI']['terminal_usage']=1799
        with patch.object(m,'analysis_header',side_effect=AssertionError('No analysis access')):
            with self.assertRaisesRegex(ValueError,'Both complete'):m.require_read_permission(Path('/unused'),self.plan,'sha',self.progress)
    def test_operational_failure_does_not_open_analysis(self):
        self.progress['Anthropic']['operational_failure']={'error':'unknown'}
        with patch.object(m,'analysis_header',side_effect=AssertionError('No analysis access')):
            with self.assertRaises(ValueError):m.require_read_permission(Path('/unused'),self.plan,'sha',self.progress)
    def test_missing_complete_primary_analysis_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):m.require_read_permission(Path(tmp),self.plan,'sha',self.progress)
    def test_wrong_analysis_state_stops_before_answer_payload(self):
        text='{\n"updated_at":"now",\n"state":"waiting",\n"answer_payload":"NEVER_READ"}'
        stream=io.StringIO(text);stream.close=lambda:None
        with patch.object(Path,'open',return_value=stream):
            with self.assertRaisesRegex(ValueError,'not complete'):m.analysis_header(Path('unused'))
        self.assertLess(stream.tell(),text.index('answer_payload'))
    def test_complete_header_reads_only_four_metadata_values(self):
        text=json.dumps(dict(updated_at='now',state='complete_pending_independent_source_adjudication',execution_plan_sha256='sha',n=1800,answer_payload='NEVER_READ'))
        stream=io.StringIO(text);stream.close=lambda:None
        with patch.object(Path,'open',return_value=stream):header=m.analysis_header(Path('unused'))
        self.assertEqual(header['n'],1800);self.assertLess(stream.tell(),text.index('answer_payload'))
        with patch.object(m,'analysis_header',return_value=header):m.require_read_permission(Path('unused'),self.plan,'sha',self.progress)
    def test_complete_analysis_for_other_cohort_refuses(self):
        with patch.object(m,'analysis_header',return_value={'n':1800,'execution_plan_sha256':'wrong'}):
            with self.assertRaisesRegex(ValueError,'another cohort'):m.require_read_permission(Path('unused'),self.plan,'sha',self.progress)
    def test_independent_parser_matches_frozen_assemblers_on_synthetic_cases(self):
        textcases=['<answer>भवति</answer>','<answer>भवत्ति</answer>','<answer>अज्ञातम्</answer>','भवति','<answer></answer>','<answer>भवति</answer><answer>अज्ञातम्</answer>']
        for provider in ['Anthropic','OpenAI']:
            for text in textcases:
                for status in ['complete','truncated','refused','failed']:
                    if provider=='Anthropic' and status=='failed':continue
                    task={'id':'fake','gold_devanagari':['भवति']}
                    row={'task':task,'status':'prepared','answer':None,'answer_normalized':None,'is_correct':None,'truncated':False,'refusals':[]}
                    if provider=='Anthropic':
                        body={'content':[{'type':'thinking','thinking':'<answer>भवति</answer>'},{'type':'text','text':text}],
                              'stop_reason':{'complete':'end_turn','truncated':'max_tokens','refused':'refusal'}[status]}
                        saved=ant.apply_result(row,{'result':{'type':'succeeded','message':body}},'fixture')
                    else:
                        content=[{'type':'output_text','text':text}]
                        if status=='refused':content.append({'type':'refusal','refusal':'fixture refusal'})
                        body={'status':{'complete':'completed','truncated':'incomplete','refused':'completed','failed':'failed'}[status],
                            'output':[{'type':'reasoning','summary':[{'type':'summary_text','text':'<answer>भवति</answer>'}]},{'type':'message','content':content}]}
                        if status=='truncated':body['incomplete_details']={'reason':'max_output_tokens'}
                        saved=oai.apply_result(row,{'response':{'status_code':200,'body':body}},'fixture')
                    graded=m.grade_response(provider,body,self.item)
                    for k in ['status','output_text','answer','answer_normalized','truncated','refusals']:
                        self.assertEqual(graded[k],saved[k],(provider,status,text,k))
                    self.assertIs(graded['canonical_correct'],saved['is_correct'])
                    self.assertEqual(graded['usable'],saved['status']=='completed' and saved['answer'] is not None and not saved['truncated'])
                    if status=='complete' and text==textcases[1]:
                        self.assertFalse(graded['canonical_correct']);self.assertTrue(graded['finite_correct'])
                    if status=='complete' and text==textcases[2]:
                        self.assertTrue(graded['finite_spelling_grade']['requires_source_adjudication'])
    def test_statistics_include_zero_usable_families_and_match_analytic_core(self):
        rows=[];tasks=[];saved=[]
        values=[('a',True,True),('a',False,True),('b',False,False),('c',None,False)]
        for i,(family,correct,usable) in enumerate(values):
            task={'id':str(i),'campaign':{'root_family':family},'dhatu':{'gana':'Bhvadi'}};tasks.append(task)
            status='completed' if usable else ('refused' if correct is not None else 'api_error')
            rows.append(dict(family=family,status=status,truncated=False,usable=usable,finite_correct=correct))
            saved.append(dict(task=task,status=status,answer='x' if usable else None,truncated=False,is_correct=correct))
        actual=m.statistics(rows,'finite_correct');expected=panel_statistics(tasks,saved,repetitions=1000)
        for k,v in actual.items():
            if k in ['all_request','completed_answer']:
                for field,value in v.items():self.assertFalse(m.different(value,expected[k].get(field)),(k,field))
            else:self.assertFalse(m.different(v,expected[k]),k)
        self.assertEqual(actual['root_families'],3);self.assertEqual(actual['completed_answer']['n'],2)
    def test_all_nonusable_statistics_have_defined_bounds(self):
        rows=[dict(family=f,status='refused',truncated=False,usable=False,finite_correct=False) for f in ['a','b']]
        s=m.statistics(rows,'finite_correct');self.assertEqual(s['missing_answer_accuracy_bounds'],[0,1]);self.assertIsNone(s['completed_answer']['accuracy'])

if __name__=='__main__':unittest.main(verbosity=2)
