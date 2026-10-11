"""Synthetic-only tests. Never load an actual response or completed analysis."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('source_adjusted_tested', HERE / 'score.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def task(i):
    return dict(id=f't{i}', task_type='cartesian_4d', dhatu=dict(code=f'01.{i:04d}', aupadeshika='BU', gana='Bhvadi', artha='sattAyAm'),
        morphology=dict(lakara='Lat', prayoga='Kartari', purusha='Prathama', vacana=['Eka','Dvi','Bahu'][i % 3]),
        gold_slp1=['Bavati'], gold_devanagari=['भवति'], campaign=dict(root_family=f'f{i}',
            split='test', construction='ordinary_conjugation', prompt_sha256=f'prompt{i}', sampling_cell=dict(label='cell')))


def row(i, answer='कथापयति', correct=False, status='completed'):
    return dict(task=task(i), task_index=i, answer=answer, answer_normalized=answer,
        output_text=f'<answer>{answer}</answer>' if answer else None, is_correct=correct,
        status=status, truncated=False, refusals=[], raw_batch_result=dict(immutable='raw'))


def policy():
    return dict(accepted={('t0', 'कथापयति'): ['base']}, rejected={}, unresolved={}, evidence=[])


def addition(t, form='कथापयति'):
    return dict(task_id=t['id'], dhatu=t['dhatu'], morphology=t['morphology'],
        prompt_sha256=t['campaign']['prompt_sha256'], additional_forms_devanagari=[form])


class SourceLayerTests(unittest.TestCase):
    def test_exact_symmetric_and_raw_preservation(self):
        original=[row(0), row(1, 'काथयति'), row(2, 'भवति', True)]
        snapshot=copy.deepcopy(original)
        a, changes, pending, decisions=s.adjust_rows(original, policy())
        b, *_=s.adjust_rows(copy.deepcopy(original), policy())
        self.assertEqual(a,b)
        self.assertEqual(original,snapshot)
        self.assertEqual([r['is_correct'] for r in a],[True,False,True])
        self.assertEqual(len(changes),1)
        self.assertEqual([r['task_id'] for r in pending],['t1'])
        self.assertEqual(decisions[0]['disposition'],'accepted_exact_source_form')
        for before,after in zip(original,a):
            for key in before:
                if key!='is_correct':self.assertEqual(before[key],after[key])

    def test_no_cross_task_or_p_less_rescue(self):
        rows=[row(1),row(0,'कथायति'),row(2,'कथापयति')]
        adjusted,changed,queue,_=s.adjust_rows(rows,policy())
        self.assertEqual(changed,[])
        self.assertEqual(len(queue),3)
        self.assertFalse(any(r['is_correct'] for r in adjusted))

    def test_missing_refusal_truncation_denominators_unchanged(self):
        rows=[row(0,None,None,'infrastructure_error'),row(1,None,False,'refused'),row(2,'कथापयति',False,'incomplete')]
        rows[2]['truncated']=True
        p=policy();p['accepted'][('t2','कथापयति')]=['source']
        adjusted,changes,queue,_=s.adjust_rows(rows,p)
        self.assertIsNone(adjusted[0]['is_correct'])
        self.assertTrue(adjusted[2]['is_correct']) # Same extracted-answer contract as frozen finite grading.
        self.assertEqual([s.usable(r) for r in adjusted],[False]*3)
        self.assertEqual(queue,[])
        self.assertEqual([r['status'] for r in adjusted],[r['status'] for r in rows])

    def test_nfc_only_matching(self):
        p=policy();p['accepted']={('t0',s.normalize('क़')):['s']}
        adjusted,*_=s.adjust_rows([row(0,'क़')],p)
        self.assertTrue(adjusted[0]['is_correct'])
        adjusted,*_=s.adjust_rows([row(0,'क')],p)
        self.assertFalse(adjusted[0]['is_correct'])

    def test_reviewed_rejection_resolves_queue_without_task_drop(self):
        p=policy();p['rejected'][('t1','काथयति')]=['review']
        adjusted,changes,pending,decisions=s.adjust_rows([row(1,'काथयति')],p)
        self.assertEqual((len(adjusted),changes,pending),(1,[],[]))
        self.assertFalse(adjusted[0]['is_correct'])
        self.assertEqual(decisions[0]['disposition'],'source_rejected_exact_form')
        with self.assertRaises(ValueError):s.adjust_rows([row(1,'काथयति',True)],p)

    def test_exact_identity_guard(self):
        t=task(0);item=addition(t)
        self.assertEqual(s.identity(item,{'t0':t}),'t0')
        for field in ('dhatu','morphology','prompt_sha256'):
            wrong=copy.deepcopy(item);wrong[field]='different'
            with self.assertRaises(ValueError):s.identity(wrong,{'t0':t})

    def test_review_header_stops_before_scores(self):
        base=dict(created_at='synthetic',passed=True,mechanical_review_only=True,n_per_provider=1800,
            provider_responses=3599,explicit_infrastructure_missing=1,missing_index=837,models='DO_NOT_READ')
        text=json.dumps(base)
        stream=io.StringIO(text)
        @contextlib.contextmanager
        def opened(*a,**kw):yield stream
        with patch.object(Path,'open',opened):
            h=s.review_header(Path('synthetic'))
        self.assertEqual(h['missing_index'],837)
        self.assertLess(stream.tell(),text.index('models'))
        base['passed']=False;text=json.dumps(base);stream=io.StringIO(text)
        with patch.object(Path,'open',opened),self.assertRaises(ValueError):s.review_header(Path('synthetic'))
        self.assertLess(stream.tell(),text.index('mechanical_review_only'))

    def test_run_cannot_load_results_before_permission(self):
        fake=SimpleNamespace(carry=SimpleNamespace(prior=SimpleNamespace(coordinator=lambda _:contextlib.nullcontext())))
        with patch.object(s,'verify_tool',return_value={}),patch.object(s,'module',return_value=fake),\
             patch.object(s,'permission',side_effect=ValueError('blocked')),\
             patch.object(s,'read',side_effect=AssertionError('result read before gate')),\
             patch.object(s,'compute',side_effect=AssertionError('scoring before gate')):
            with self.assertRaisesRegex(ValueError,'blocked'):s.run()

    def test_metadata_failure_cannot_read_review_or_results(self):
        guard=SimpleNamespace(amendment_sha='amend',plan_sha='plan',accounting=SimpleNamespace(snapshot=lambda:{}),state=lambda *a,**kw:{})
        primary=SimpleNamespace(carry=SimpleNamespace(Guard=lambda *a:guard),
            original=SimpleNamespace(inspect_manifest=lambda _:({},[],{})),check_review=lambda *a:None,
            legacy=SimpleNamespace(load=lambda:{}))
        independent=SimpleNamespace(require_read_permission=lambda *a:(_ for _ in ()).throw(ValueError('not complete')))
        with patch.object(s,'sha',return_value='plan'),patch.object(s,'review_header',side_effect=AssertionError('too early')),\
             patch.object(s,'read',side_effect=AssertionError('too early')):
            with self.assertRaisesRegex(ValueError,'not complete'):
                s.permission(dict(execution_plan_sha256='plan',continuation_amendment_sha256='amend'),primary,independent)

    def test_base_and_extension_bindings(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);tasks=[task(i) for i in range(19)]
            def save(name,value):
                f=root/name;f.write_text(json.dumps(value));return f
            base=dict(execution_plan_sha256='plan',candidate_tasks_sha256='tasks',public_prompts_sha256='prompts',
                continuation_amendment_sha256='amend',status='adopted_exact_additions_for_separate_source_adjudicated_scoring',
                accepted_additions=[addition(t) for t in tasks])
            bp=save('base.json',base);tool=save('tool-manifest.json',{})
            pin=dict(adoption_path=str(bp),adoption_sha256=s.sha(bp),execution_plan_sha256='plan',tasks_sha256='tasks',
                public_prompts_sha256='prompts',continuation_amendment_sha256='amend')
            source=save('source.json',{'primary':'evidence'})
            rejected=addition(tasks[0]);rejected['forms_devanagari']=['काथयति']
            doc=dict(schema='exact-task-source-dispositions-v1',status='adopted',execution_plan_sha256='plan',candidate_tasks_sha256='tasks',
                symmetric_across_providers=True,source_dependencies={str(source):s.sha(source)},rejected_answers=[rejected])
            dp=save('disposition.json',doc)
            rp=save('review.json',dict(passed=True,dispositions_sha256=s.sha(dp),execution_plan_sha256='plan',candidate_tasks_sha256='tasks'))
            extension=dict(schema='reviewed-source-extensions-v1',tool_manifest_sha256=s.sha(tool),execution_plan_sha256='plan',
                candidate_tasks_sha256='tasks',dispositions=[dict(path=str(dp),sha256=s.sha(dp),review_path=str(rp),review_sha256=s.sha(rp))])
            ep=save('extensions.json',extension)
            with patch.object(s,'HERE',root),patch.object(s,'ROOT',root):
                result=s.build_policy(pin,tasks,ep)
                self.assertEqual(len(result['accepted']),19)
                self.assertIn(('t0','काथयति'),result['rejected'])
                rp.write_text(rp.read_text().replace('true','false'))
                with self.assertRaises(ValueError):s.build_policy(pin,tasks,ep)

    def test_real_statistical_helpers_on_synthetic_rows(self):
        # Only import source functions; never call real analyze/permission/ledger.
        import sys
        sys.path.insert(0,str(s.ROOT))
        primary=s.module('synthetic_source_primary',s.OVERLAY/'analyze.py')
        a=[row(0),row(1,'भवति',True),row(2,'असिद्धम्',False)]
        o=copy.deepcopy(a);o[1]=row(1,None,None,'infrastructure_error')
        before=copy.deepcopy({'Anthropic':a,'OpenAI':o})
        with patch.object(s,'MISSING',1),patch.object(primary.carry,'KNOWN',1):
            report,adjusted=s.compute([task(i) for i in range(3)],before,policy(),primary)
        self.assertEqual(report['models']['Anthropic']['statistics']['all_request']['correct'],2)
        self.assertEqual(report['models']['OpenAI']['statistics']['completed_answer']['n'],2)
        self.assertEqual(report['models']['OpenAI']['statistics']['unscored_results'],1)
        variants=report['infrastructure_sensitivity']['source']
        self.assertEqual(variants['missing_correct']['statistics']['all_request']['correct'],2)
        self.assertEqual(variants['missing_incorrect']['statistics']['all_request']['correct'],1)
        self.assertEqual(variants['missing_correct']['statistics']['completed_answer']['n'],2)
        self.assertIsNone(adjusted['OpenAI'][1]['is_correct'])
        self.assertIsNone(before['OpenAI'][1]['is_correct'])
        self.assertFalse(report['benchmark_ready'])

    def test_synthetic_end_to_end_output_and_no_overwrite(self):
        import sys
        sys.path.insert(0,str(s.ROOT))
        primary=s.module('synthetic_source_primary_e2e',s.OVERLAY/'analyze.py')
        with tempfile.TemporaryDirectory() as td:
            run=Path(td).resolve();overlay=run/'carry';here=overlay/'source';here.mkdir(parents=True)
            (here/'tool-manifest.json').write_text('{}')
            tasks=[task(i) for i in range(3)]
            a=[row(0),row(1,'भवति',True),row(2,'असिद्धम्',False)]
            o=copy.deepcopy(a);o[1]=row(1,None,None,'infrastructure_error')
            hashes={}
            for provider,rows in [('Anthropic',a),('OpenAI',o)]:
                d=overlay/'results'/provider;d.mkdir(parents=True)
                for filename in ['canonical.json','predeclared-spelling.json']:
                    path=d/filename;path.write_text(json.dumps(rows,ensure_ascii=False))
                    hashes[str(path.relative_to(run))]=s.sha(path)
            review_path=overlay/'fake-review.json';review_path.write_text('{}')
            review=dict(primary_analysis_sha256='synthetic',result_fingerprints=hashes)
            pin=dict(execution_plan_sha256='synthetic',continuation_amendment_sha256='synthetic')
            with patch.object(s,'RUN',run),patch.object(s,'OVERLAY',overlay),patch.object(s,'HERE',here),\
                 patch.object(s,'N',3),patch.object(s,'MISSING',1),patch.object(primary.carry,'KNOWN',1),\
                 patch.object(s,'verify_tool',return_value=pin),patch.object(s,'module',return_value=primary),\
                 patch.object(primary.carry.prior,'coordinator',return_value=contextlib.nullcontext()),\
                 patch.object(s,'permission',return_value=({},tasks,review,review_path)),\
                 patch.object(s,'build_policy',return_value=policy()):
                result=s.run();out=Path(result['output'])
                assembled=s.read(out/'analysis.json')
                self.assertEqual(assembled['n_per_provider'],3)
                self.assertEqual(assembled['models']['Anthropic']['statistics']['all_request']['correct'],2)
                self.assertIsNone(s.read(out/'OpenAI-source-adjusted.json')[1]['is_correct'])
                self.assertTrue(all(s.sha(run/p)==h for p,h in hashes.items()))
                with self.assertRaisesRegex(ValueError,'Preserve prior source-layer output'):s.run()


if __name__=='__main__':
    unittest.main()
