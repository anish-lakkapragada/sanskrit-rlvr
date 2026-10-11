"""Adversarial release migration tests; synthetic inputs, never provider APIs."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
from misc import vp_goal as runner, oai_batch_eval as io
from misc import vp_cartesian_release as release
from misc import vp_cartesian_release_run as execution
from misc import vp_cartesian_final_analyze as analysis
from misc.vp_cartesian_release_protocol import release_binding, require_complete_cohort, stage_jobs
from misc.vp_cartesian_visibility import visible_release_job
from misc.test_vp_goal import state,job

TAPER=[200]*5+[200]*10+[100]*10+[50]*10+[10]*25+[5]*10
GOLDEN=json.loads((runner.ROOT/'misc/testdata/release64k-legacy-requests.json').read_text())

def tasks(n):
    """Deliberately invalid synthetic grammar rows: validation is mocked for freeze tests."""
    return [dict(copy.deepcopy(GOLDEN['task']),id=f'synthetic-{i}',gold_slp1=['synthetic'],
                 gold_devanagari=['synthetic'],campaign=dict(root_family=f'unit-{i//3}',
                 construction='synthetic_unit_fixture',vp_version='unit')) for i in range(n)]

def freeze_fixture(root,n=1200,sizes=None,protocol='common64k-v1'):
    source=root/'source.json';plan=root/'plan.json';out=root/'release'
    ts=tasks(n);io.atomic_json(source,ts)
    io.atomic_json(plan,dict(track='five_d',fixed_n=n,point_accuracy_target=[.79,.81],precision_standard_error_lt=.01))
    with patch.object(release,'validate',return_value={'fixture_only':True}):
        manifest=release.freeze(source,plan,out,'five_d',protocol=protocol,
            stage_sizes=sizes or ([200]*5+[n-1000] if n>1000 else [n]))
    return out,manifest,ts

def cohort(directory,manifest,*,complete=True):
    binding=release_binding(directory/'manifest.json');s=state()
    for provider in runner.PROVIDERS:
        for i,stage in enumerate(manifest['stages']):
            key=f'{provider.lower()}-{i}'
            j=dict(id=key,provider=provider,phase=stage['phase'],n=stage['n'],
                   tasks_digest=stage['tasks_digest'],attempted_at='intent',batch_id='fixture-batch',
                   reservation_micro=stage['n']*10,settled=complete,
                   collected_at='receipt' if complete else None,actual_cost_upper_micro=1,**binding)
            s['jobs'][key]=j
    return s

class LegacyAndAccountingTests(unittest.TestCase):
    def test_every_legacy_request_is_byte_identical(self):
        for phase,spec in GOLDEN['phases'].items():
            self.assertEqual(json.loads(json.dumps(runner.PHASES[phase])),spec)
            for provider in runner.PROVIDERS:
                self.assertEqual(runner.digest(runner.request(GOLDEN['task'],provider,phase,0)),GOLDEN['request_sha256'][provider][phase])

    def test_new_aliases_only_change_cap_and_share_allowances(self):
        for provider in runner.PROVIDERS:
            old=runner.request(GOLDEN['task'],provider,'hard_final',0)
            new=runner.request(GOLDEN['task'],provider,'hard_final_64k',0)
            if provider=='Anthropic':old['params']['max_tokens']=65536
            else:old['body']['max_output_tokens']=65536
            self.assertEqual(old,new)
        for canonical,alias,limit in [('hard_final','hard_final_64k',1000),('hard_extension','hard_extension_64k',5000)]:
            for old_phase in (canonical,alias):
                for new_phase in (canonical,alias):
                    s=state();j=job(phase=old_phase,n=limit-1);j.update(attempted_at='old',settled=True,actual_cost_upper_micro=1);s['jobs']['old']=j
                    if 'extension' in new_phase:
                        core=job(phase=runner.EXTENSIONS[new_phase],n=1000);core.update(attempted_at='core',settled=True,collected_at='receipt',actual_cost_upper_micro=1);s['jobs']['core']=core
                    # Isolate allowance arithmetic; binding/barrier are tested with real files below.
                    with patch.object(runner,'verify_release_binding',return_value=None):
                        runner.budget_gate(s,job(phase=new_phase,n=1))
                        with self.assertRaisesRegex(ValueError,'Phase allowance'):
                            runner.budget_gate(s,job(phase=new_phase,n=2))

    def test_canonical_protection_counts_new_alias_once(self):
        s=state();before=runner.protected_remaining(s,'OpenAI')
        j=job('OpenAI','hard_final_64k',200);j['attempted_at']='intent';s['jobs']['new']=j
        self.assertEqual(before-runner.protected_remaining(s,'OpenAI'),200*(1500*5+16384*25))
        self.assertEqual(runner.PROTECTED,{'hard_final','bench_final','cap_check'})

    def test_funding_taper_uses_maximums_not_expected_savings(self):
        s=state();s['historical_spend_micro']['OpenAI']=727478150
        with patch.object(runner,'verify_release_binding',return_value=None),patch.object(runner,'protected_remaining',return_value=0):
            with self.assertRaisesRegex(ValueError,'Cumulative'):
                runner.budget_gate(s,job('OpenAI','hard_final_64k',1000))
            self.assertEqual(runner.budget_gate(s,job('OpenAI','hard_final_64k',200)),329180000)
            s['historical_spend_micro']['OpenAI']=1990000000
            self.assertEqual(runner.budget_gate(s,job('OpenAI','hard_final_64k',5)),8229500)
            with self.assertRaisesRegex(ValueError,'Cumulative'):
                runner.budget_gate(s,job('OpenAI','hard_final_64k',10))
        self.assertEqual(runner.PROVIDERS['OpenAI']['cap_micro'],2000000000)

    def test_replay_aliases_unknown_posts_and_paired_provider(self):
        s=state();j=job(phase='hard_final',n=1);j.update(id='old',attempted_at='unknown');s['jobs']['old']=j
        with patch.object(io,'read_json',return_value=[{'id':'same'}]):
            with self.assertRaisesRegex(ValueError,'already attempted'):
                runner.prevent_repeated_final_questions(s,job(phase='hard_final_64k'),[{'id':'same'}])
            runner.prevent_repeated_final_questions(s,job('OpenAI','hard_final_64k'),[{'id':'same'}])
            runner.prevent_repeated_final_questions(s,job(phase='cap_check'),[{'id':'same'}])

class TransportTests(unittest.TestCase):
    def test_fixed_4800_taper_and_boundary(self):
        ts=tasks(4800);stages=release.transport_stages(ts,'five_d','common64k-v1',TAPER)
        p=release.audit_partition(ts,stages,'five_d','common64k-v1')
        self.assertEqual((p['core_n'],p['extension_n'],p['stage_count']),(1000,3800,70))
        with self.assertRaisesRegex(ValueError,'crosses'):
            release.transport_stages(ts,'five_d','common64k-v1',[600,600,3600])
        for sizes in ([1000,3799],[1000,3800,0],[True,4799],[1000,-1,3801]):
            with self.assertRaises(ValueError):release.transport_stages(ts,'five_d','common64k-v1',sizes)
        stages[5]['phase']='hard_extension'
        with self.assertRaisesRegex(ValueError,'Wrong track'):
            release.audit_partition(ts,stages,'five_d','common64k-v1')

    def test_legacy_default_stages_remain_same(self):
        stages=release.transport_stages(tasks(2400),'five_d')
        self.assertEqual([len(s['tasks']) for s in stages],[1000,500,500,400])
        self.assertEqual(stages[0]['phase'],'hard_final')

class BoundReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.directory,self.manifest,self.tasks=freeze_fixture(self.root)
        self.state=cohort(self.directory,self.manifest)
        stage=self.manifest['stages'][-1]
        self.new=dict(job('Anthropic','hard_extension_64k',stage['n']),id='new-extension',tasks_digest=stage['tasks_digest'],**release_binding(self.directory/'manifest.json'))
        # The extension under test has not been attempted yet.
        self.state['jobs'].pop('anthropic-5')

    def test_exact_core_barrier_missing_uncollected_wrong_release_wrong_protocol(self):
        runner.budget_gate(self.state,self.new)
        for field,value in [('settled',False),('collected_at',None),('release_manifest_sha256','other'),('phase','hard_final'),('n',199)]:
            s=copy.deepcopy(self.state);s['jobs']['anthropic-0'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):runner.budget_gate(s,self.new)
        s=copy.deepcopy(self.state);s['jobs'].pop('anthropic-4')
        with self.assertRaisesRegex(ValueError,'Collect and settle'):runner.budget_gate(s,self.new)
        # Provider-specific barrier: unready counterpart does not allow/deny this provider's core proof.
        self.state['jobs']['openai-0']['settled']=False
        runner.budget_gate(self.state,self.new)

    def test_duplicate_core_stage_and_duplicate_attempt_fail(self):
        m=copy.deepcopy(self.manifest);m['stages'][1]=m['stages'][0]
        with self.assertRaisesRegex(ValueError,'distinct'):
            stage_jobs(self.state,m,self.new['release_manifest_sha256'],runner.PROVIDERS)
        self.state['jobs']['duplicate']=dict(self.state['jobs']['anthropic-0'],id='duplicate')
        with self.assertRaisesRegex(ValueError,'attempted twice'):runner.budget_gate(self.state,self.new)

    def test_missing_binding_and_changed_manifest_fail(self):
        j=dict(self.new);j.pop('release_manifest_path')
        with self.assertRaisesRegex(ValueError,'requires an exact release binding'):runner.budget_gate(self.state,j)
        m=dict(self.manifest,fixed_n=1199);io.atomic_json(self.directory/'manifest.json',m)
        with self.assertRaisesRegex(ValueError,'manifest changed'):runner.budget_gate(self.state,self.new)

    def test_dependency_tamper_is_checked_before_count_client(self):
        m=copy.deepcopy(self.manifest);m['dependency_sha256']['misc/vp_goal_stats.py']='not-the-hash'
        io.atomic_json(self.directory/'manifest.json',m);j=dict(self.new,**release_binding(self.directory/'manifest.json'))
        with patch.object(runner,'load',return_value={'jobs':{'new':j}}),patch.object(runner,'verify_job',return_value=([],[])),patch.object(runner,'client_for') as client:
            with self.assertRaisesRegex(ValueError,'dependency changed'):runner.count_inputs('new')
            client.assert_not_called()

    def test_authorization_is_for_exact_manifest_not_just_stage(self):
        out=self.root/'runner';out.mkdir();gate=dict(passed=True,authorized_by_phase=self.manifest['authorized_by_phase'],authorized_release_manifest_sha256=['wrong'])
        io.atomic_json(out/'release-freeze.json',gate)
        with patch.object(runner,'OUT',out):
            with self.assertRaisesRegex(ValueError,'Exact frozen release manifest'):runner.verify_release_binding(self.new,authorized=True)
            gate['authorized_release_manifest_sha256']=[self.new['release_manifest_sha256']];io.atomic_json(out/'release-freeze.json',gate)
            runner.verify_release_binding(self.new,authorized=True)

    def test_partial_visibility_removes_scores_without_mutating_raw(self):
        j=self.state['jobs']['anthropic-0'];j.update(summary={'accuracy':.8},completed_answers=200,completed_correct=160)
        visible=visible_release_job(self.state,j)
        self.assertTrue(visible['scores_embargoed']);self.assertNotIn('summary',visible);self.assertNotIn('completed_correct',visible)
        self.assertEqual(j['summary'],{'accuracy':.8})
        full=cohort(self.directory,self.manifest);full['jobs']['anthropic-0'].update(summary={'accuracy':.8})
        self.assertEqual(visible_release_job(full,full['jobs']['anthropic-0'])['summary'],{'accuracy':.8})

    def test_analyzer_reads_zero_result_files_until_both_cohorts_complete(self):
        original=io.read_json;opened=[]
        def read(path):
            if Path(path).name=='results.json':opened.append(str(path));raise AssertionError('Premature result read')
            return original(path)
        with patch.object(runner,'load',return_value=self.state),patch.object(io,'read_json',side_effect=read):
            with self.assertRaisesRegex(ValueError,'Full fixed release cohort'):analysis.analyze(self.directory)
        self.assertEqual(opened,[])

    def test_complete_cohort_uses_full_N_and_unchanged_statistics(self):
        full=cohort(self.directory,self.manifest);out=self.root/'runner'
        for j in full['jobs'].values():
            stage=next(s for s in self.manifest['stages'] if s['tasks_digest']==j['tasks_digest'])
            ts=io.read_json(self.directory/stage['path'])
            rows=[dict(task=t,status='completed',answer='synthetic',truncated=False,is_correct=(int(t['id'].split('-')[-1])%5!=0)) for t in ts]
            io.atomic_json(out/'jobs'/j['id']/'results.json',rows)
        original=analysis.panel_statistics
        with patch.object(runner,'load',return_value=full),patch.object(runner,'OUT',out),patch.object(analysis,'panel_statistics',side_effect=lambda t,r:original(t,r,repetitions=1000)):
            result=analysis.analyze(self.directory)
        self.assertEqual(result['status'],'complete_numerical_analysis')
        self.assertEqual({m['all_request']['n'] for m in result['models'].values()},{1200})
        self.assertEqual({m['all_request']['accuracy'] for m in result['models'].values()},{.8})
        self.assertFalse(result['benchmark_ready'])

    def test_durable_intent_precedes_fake_client_failure_and_cannot_retry(self):
        out=self.root/'runner';history=self.root/'history'
        stage=self.manifest['stages'][0];ts=io.read_json(self.directory/stage['path'])
        j=dict(job('Anthropic',stage['phase'],stage['n']),id='durable',
               tasks_digest=stage['tasks_digest'],**release_binding(self.directory/'manifest.json'))
        requests=[runner.request(t,'Anthropic',j['phase'],i) for i,t in enumerate(ts)]
        j['requests_digest']=runner.digest(requests)
        s=state();s.update(maximum_counted_input=1300,additional_renderers={
            'vp_cartesian_prompt_v3.py':io.sha256(runner.ROOT/'misc/vp_cartesian_prompt_v3.py')})
        s['jobs']['durable']=j;snapshots=[]
        io.atomic_json(out/'jobs/durable/input-counts.json',dict(requests_digest=j['requests_digest'],counts={r['custom_id']:100 for r in requests}))
        io.atomic_json(history/'family-split.json',dict(families={t['campaign']['root_family']:{'split':'test'} for t in ts}))
        io.atomic_json(out/'release-freeze.json',dict(passed=True,
            authorized_release_manifest_sha256=[j['release_manifest_sha256']],authorized_by_phase=self.manifest['authorized_by_phase']))
        def fake_client(provider):
            self.assertEqual(len(snapshots),1)
            saved=snapshots[0]['jobs']['durable']
            self.assertEqual(saved['status'],'submission_unknown')
            self.assertTrue(saved['attempted_at']);self.assertEqual(saved['reservation_micro'],131672000)
            raise RuntimeError('Synthetic client initialization failure; no provider instantiated')
        with patch.object(runner,'OUT',out),patch.object(runner,'HISTORY',history),patch.object(runner,'load',return_value=s),patch.object(runner,'save',side_effect=lambda value:snapshots.append(copy.deepcopy(value))),patch.object(runner,'verify_job',return_value=(ts,requests)),patch('misc.vp_goal_validate.validate',return_value={}),patch.object(runner,'client_for',side_effect=fake_client) as client:
            with self.assertRaisesRegex(RuntimeError,'Synthetic client'):runner.submit('durable')
            with self.assertRaisesRegex(ValueError,'never replay'):runner.submit('durable')
            self.assertEqual(client.call_count,1)
        self.assertFalse(j.get('settled',False));self.assertEqual(j['reservation_micro'],131672000)

    def test_executor_lock_rejects_a_second_controller_before_inspection(self):
        import fcntl
        with (self.directory/'execution.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(execution,'inspect') as inspect:
                with self.assertRaises(BlockingIOError):execution.execute(self.directory,'duplicate',.01)
                inspect.assert_not_called()

    def test_mixed_protocol_manifest_rejected_before_submission(self):
        m=copy.deepcopy(self.manifest)
        m['reference_protocol_by_phase']['hard_final']={'effort':'xhigh','max_output_tokens':16384}
        io.atomic_json(self.directory/'manifest.json',m)
        j=dict(self.new,**release_binding(self.directory/'manifest.json'))
        with self.assertRaisesRegex(ValueError,'mixed or missing'):runner.budget_gate(self.state,j)

    def test_executor_rechecks_after_count_before_submit(self):
        out=self.root/'runner';out.mkdir();stage=self.manifest['stages'][0]
        item=dict(id='unit-job',provider='Anthropic',phase=stage['phase'],n=stage['n'],tasks_digest=stage['tasks_digest'],path=str(self.directory/stage['path']))
        prepared=dict(job(n=200),id='unit-job');calls=[]
        def inspect(*args,**kwargs):
            calls.append('inspect')
            if len(calls)==3:raise ValueError('Frozen release dependency changed')
            return self.manifest,[item]
        with patch.object(execution,'inspect',side_effect=inspect),patch.object(runner,'load',return_value=state()),patch.object(runner,'prepare',return_value=prepared),patch.object(execution,'decision',return_value='submit'),patch.object(runner,'count_inputs') as count,patch.object(runner,'submit') as submit:
            with self.assertRaisesRegex(ValueError,'dependency changed'):execution.execute(self.directory,'unit',.01)
            count.assert_called_once();submit.assert_not_called()

class ConsumerAndResumeTests(unittest.TestCase):
    setUp=BoundReleaseTests.setUp

    def consumer_state(self,complete):
        s=cohort(self.directory,self.manifest)
        s.update(authorization=copy.deepcopy(runner.PROVIDERS),phase_policy=json.loads(json.dumps(runner.PHASES)),updated_at='fixture')
        renamed={}
        for key,j in s['jobs'].items():
            j.update(id=key.replace('-', '-five-d-',1),status='completed',summary={'accuracy':.75},completed_answers=j['n'],completed_correct=int(.75*j['n']))
            renamed[j['id']]=j
        s['jobs']=renamed
        if not complete:
            s['jobs']['openai-five-d-5'].update(settled=False,collected_at=None)
        return s

    def test_report_withholds_partial_final_scores_and_releases_complete_cohort(self):
        from misc import benchmark_forward as report
        root=self.root/'report';directory=root/'benchmarks/iterative-goal-20261006'
        io.atomic_json(directory/'plan.json',{})
        for complete in (False,True):
            with self.subTest(complete=complete):
                s=self.consumer_state(complete);original=copy.deepcopy(s)
                io.atomic_json(directory/'ledger.json',s)
                result=report.iterative_goal_execution(root)
                self.assertEqual(len(result['jobs']),12)
                for row in result['jobs']:
                    self.assertEqual(row['summary'],{'accuracy':.75} if complete else None)
                    self.assertEqual(row['completed_correct'],150 if complete else None)
                    self.assertEqual(bool(row['scores_embargoed']),not complete)
                self.assertEqual(s,original)
                self.assertEqual({x['cap_usd'] for x in result['providers']},{1000,2000})

    def test_report_legacy_detail_route_does_not_bypass_bound_release_embargo(self):
        from misc import benchmark_forward as report
        root=self.root/'detail-report';directory=root/'benchmarks/iterative-goal-20261006'
        s=self.consumer_state(False);j=s['jobs'].pop('anthropic-five-d-0')
        j['id']='opus-composition-01';s['jobs'][j['id']]=j
        io.atomic_json(directory/'plan.json',{});io.atomic_json(directory/'ledger.json',s)
        io.atomic_json(directory/'jobs'/j['id']/'results.json',[{'sentinel':'must not be read'}])
        original=Path.read_text
        def read(path,*args,**kwargs):
            if path.name=='results.json':raise AssertionError('Premature detail-route result read')
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read):result=report.iterative_goal_execution(root)
        self.assertEqual(result['cells'],{})
        self.assertIsNone(next(x for x in result['jobs'] if x['id']==j['id'])['summary'])

    def test_monitor_masks_scores_and_cached_scope_metrics_but_keeps_costs(self):
        from misc import vp_parallel_monitor as monitor
        out=self.root/'monitor';ledger=out/'ledger.json'
        for complete in (False,True):
            s=self.consumer_state(complete)
            def read(path,default=None):
                if path==ledger:return copy.deepcopy(s)
                if path==out/'development-results.json':
                    return {'experiments':{key:{'within_current_scope':{'accuracy':.75},'excluded':[1]} for key in s['jobs']}}
                return {} if default is None else default
            with self.subTest(complete=complete),patch.object(monitor,'OUT',out),patch.object(monitor,'LEDGER',ledger),patch.object(monitor,'read',side_effect=read):
                result=monitor.snapshot()
            rows=next(t for t in result['tracks'] if t['track']=='five_d')['evaluations']
            self.assertEqual(len(rows),12)
            for row in rows:
                self.assertEqual(row['summary'],{'accuracy':.75} if complete else None)
                self.assertEqual(row['within_current_scope'],{'accuracy':.75} if complete else None)
                self.assertEqual(row['excluded_by_current_scope'],1 if complete else 0)
                self.assertEqual(row['scores_embargoed'],not complete)
                self.assertIn('cost_usd',row)
            self.assertEqual(result['budgets']['OpenAI']['cap'],2000)

    def test_generic_development_analyzer_never_reads_final_rows(self):
        from misc import vp_goal_analyze as generic
        s=self.consumer_state(False)
        legacy=dict(next(iter(s['jobs'].values())),id='legacy',phase='hard_final')
        legacy.pop('release_manifest_path');legacy.pop('release_manifest_sha256');s['jobs']['legacy']=legacy
        # A bound release record is also excluded if its phase is malformed as development.
        s['jobs']['malformed']=dict(next(iter(s['jobs'].values())),id='malformed',phase='confirm')
        with patch.object(runner,'load',return_value=s),patch.object(io,'read_json',side_effect=AssertionError('Forbidden final result read')) as read,patch.object(io,'atomic_json'),patch('builtins.print'):
            result=generic.analyze()
        read.assert_not_called();self.assertEqual(result['experiments'],{})

    def test_legacy_unbound_prepared_job_resumes_without_rebinding(self):
        directory,manifest,ts=freeze_fixture(self.root/'legacy',protocol='legacy16k-v1')
        stage=manifest['stages'][0]
        item=dict(id='legacy-stage',provider='Anthropic',phase=stage['phase'],n=stage['n'],tasks_digest=stage['tasks_digest'],path=str(directory/stage['path']),**release_binding(directory/'manifest.json'))
        old=dict(job('Anthropic',stage['phase'],stage['n']),id='legacy-stage',tasks_digest=stage['tasks_digest'])
        s=state();s['jobs'][old['id']]=old
        with patch.object(execution,'inspect',return_value=(manifest,[item])),patch.object(runner,'load',return_value=s),patch.object(execution,'decision',return_value='submit'),patch.object(runner,'prepare') as prepare,patch.object(runner,'count_inputs',side_effect=RuntimeError('Reached existing legacy stage count')) as count,patch.object(runner,'submit') as submit:
            with self.assertRaisesRegex(RuntimeError,'Reached existing legacy'):execution.execute(directory,'legacy',.01)
        prepare.assert_not_called();count.assert_called_once_with('legacy-stage');submit.assert_not_called()
        self.assertNotIn('release_manifest_sha256',old)

    def test_common64k_resume_requires_binding_and_legacy_bound_resume_requires_identity(self):
        item=dict(id='unit',provider='Anthropic',phase='hard_final_64k',n=200,tasks_digest='digest',release_manifest_path='path',release_manifest_sha256='sha')
        old={k:v for k,v in item.items() if not k.startswith('release_manifest')}
        with self.assertRaisesRegex(ValueError,'release binding'):
            execution.verify_existing_stage(old,item,{'protocol_version':'common64k-v1'})
        item['phase']=old['phase']='hard_final'
        execution.verify_existing_stage(old,item,{'protocol_version':'legacy16k-v1'})
        old.update(release_manifest_path='path',release_manifest_sha256='wrong')
        with self.assertRaisesRegex(ValueError,'release binding'):
            execution.verify_existing_stage(old,item,{'protocol_version':'legacy16k-v1'})

class WholeTaperCompletionTests(unittest.TestCase):
    def test_all_140_jobs_required_and_unknown_last_post_blocks(self):
        stages=release.transport_stages(tasks(4800),'five_d','common64k-v1',TAPER)
        m=dict(protocol_version='common64k-v1',stages=[dict(phase=s['phase'],n=len(s['tasks']),tasks_digest=runner.digest(s['tasks'])) for s in stages]);s=state()
        for provider in runner.PROVIDERS:
            for i,stage in enumerate(m['stages']):
                key=f'{provider}-{i}';s['jobs'][key]=dict(stage,id=key,provider=provider,attempted_at='intent',settled=True,collected_at='receipt',release_manifest_sha256='frozen')
        self.assertEqual(sum(map(len,require_complete_cohort(s,m,'frozen',runner.PROVIDERS).values())),140)
        last=s['jobs']['OpenAI-69'];last.update(settled=False,collected_at=None)
        with self.assertRaisesRegex(ValueError,'Full fixed release cohort'):require_complete_cohort(s,m,'frozen',runner.PROVIDERS)
        last.update(settled=True,collected_at='receipt',release_manifest_sha256='another')
        with self.assertRaisesRegex(ValueError,'different release'):require_complete_cohort(s,m,'frozen',runner.PROVIDERS)

if __name__=='__main__':unittest.main()
