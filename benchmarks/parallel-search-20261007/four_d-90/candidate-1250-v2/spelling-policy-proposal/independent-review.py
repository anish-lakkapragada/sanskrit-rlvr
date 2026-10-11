"""Additive, offline review; no model answers or rewrites of the proposal."""
from pathlib import Path
import collections, copy, datetime, hashlib, importlib.util, json, runpy, sys, tempfile
from unittest.mock import patch

ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent.parent/'ending-screen-01'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    protected=list(OUT.parent.glob('*.json'))+[p for p in OUT.iterdir() if p.is_file() and not p.name.startswith('independent-review')]
    before={str(p.relative_to(ROOT)):sha(p) for p in protected}
    ts=json.loads((OUT.parent/'tasks.json').read_text())
    pp=json.loads((OUT.parent/'public-prompts.json').read_text())
    policy=json.loads((OUT/'alias-policy.json').read_text())
    transfer=json.loads((OUT/'transfer-review.json').read_text())
    receipt=json.loads((OUT/'verification-receipt.json').read_text())
    assert sha(SOURCE/'alias_policy.py')=='95aa681cf454a6f71e63acc4fd34ff52ae9b9341a2a9e6c68050c0a073003825'
    assert sha(OUT.parent/'tasks.json')==policy['canonical_tasks_sha256']=='e7800eb7093a7531dbd92b6965fdbfc90a5260d506b78d698fa586cc7319a1e5'
    checks=collections.Counter()
    for rel,h in transfer['frozen_dependencies'].items():
        assert sha(ROOT/rel)==h,rel;checks['transfer_dependency_hashes']+=1
    for name,h in transfer['proposal_hashes'].items():
        assert sha(OUT/name)==h,name;checks['proposal_hashes']+=1
    for r in transfer['source_snapshots']:
        assert sha(ROOT/r['local_path'])==r['sha256'];checks['source_snapshot_hashes']+=1
    for f,h in receipt['hashes'].items():
        assert sha(OUT/f)==h;checks['saved_verification_hashes']+=1
    rules=module('review_original_finite_rules',SOURCE/'alias_policy.py')
    assert rules.build(ts)['items']==policy['items'];checks['exact_approved_builder_items']=len(ts)
    # Run the author's tests while intercepting its one receipt write.
    captured={}
    def capture(path,text,*args,**kwargs):
        assert path.resolve()==(OUT/'verification-receipt.json').resolve()
        captured['receipt']=json.loads(text);return len(text)
    with patch.object(Path,'write_text',capture):runpy.run_path(str(OUT/'verify.py'),run_name='__main__')
    assert captured['receipt']['checks_passed']
    checks.update(captured['receipt']['statistics'])
    from misc.vp_cartesian_prompt_v1 import render
    for t,p in zip(ts,pp):
        assert t['id']==p['id'] and render(t)==p['prompt']
        assert hashlib.sha256(p['prompt'].encode()).hexdigest()==t['campaign']['prompt_sha256']
        altered=copy.deepcopy(t)
        altered['gold_slp1']=['PRIVATE_ONLY_SENTINEL'];altered['gold_devanagari']=['PRIVATE_ONLY_SENTINEL']
        altered['campaign']={'private':'PRIVATE_ONLY_SENTINEL'}
        altered['dhatu']['code']='PRIVATE_ONLY_SENTINEL'
        altered['aliases_devanagari']=['PRIVATE_ONLY_SENTINEL']
        assert render(altered)==p['prompt'];checks['public_prompt_and_private_field_isolation']+=1
    sm=module('review_candidate_scorer',OUT/'scorer.py');scorer=sm.FiniteScorer()
    t=ts[0];valid=t['gold_devanagari'][0];tid=t['id']
    for text in [None,'',valid,'<answer></answer>','<answer>'+valid,
                 '<answer>'+valid+'</answer><answer>भवति</answer>']:
        r=scorer.grade(text,tid)
        assert r['status']=='unparsed' and not r['alias_aware_correct'];checks['malformed_answer_cases']=checks['malformed_answer_cases']+1
    r=scorer.grade('<answer>'+valid+' / भवति</answer>',tid)
    assert r['requires_source_adjudication'] and r['status']=='unrecognized_pending_source_review'
    checks['multiple_forms_in_one_tag_pending_review']=1
    assert scorer.grade('<answer> '+valid+' </answer>',tid)['canonical_correct'];checks['existing_whitespace_normalization']=1
    def fails():
        try:sm.FiniteScorer()
        except ValueError:return
        raise AssertionError('Changed input did not fail closed')
    # Only disposable copies are changed for tamper tests.
    with tempfile.TemporaryDirectory(prefix='independent-fixture-',dir=OUT) as td:
        target=Path(td);local=target/'policy';local.mkdir()
        taskpath=target/'tasks.json';aliaspath=local/'alias-policy.json'
        taskbytes=(OUT.parent/'tasks.json').read_bytes();aliasbytes=(OUT/'alias-policy.json').read_bytes()
        taskpath.write_bytes(taskbytes);aliaspath.write_bytes(aliasbytes);sm.OUT=local
        sm.FiniteScorer()
        aliaspath.write_bytes(aliasbytes+b' ');fails();checks['policy_hash_tamper_rejected']=1
        aliaspath.write_bytes(aliasbytes);taskpath.write_bytes(taskbytes+b' ');fails();checks['task_hash_tamper_rejected']=1
        taskpath.write_bytes(taskbytes);deps=sm.SOURCE_SHAS.copy();sm.SOURCE_SHAS['finetune/prompts.py']='0'*64
        fails();checks['extraction_dependency_tamper_rejected']=1;sm.SOURCE_SHAS=deps
    sm.OUT=OUT
    bytense={}
    for lakara in sorted({t['morphology']['lakara'] for t in ts}):
        pairs=[(t,i) for t,i in zip(ts,policy['items']) if t['morphology']['lakara']==lakara]
        bytense[lakara]=dict(tasks=len(pairs),canonical_forms=sum(len(t['gold_slp1']) for t,i in pairs),
            tasks_with_aliases=sum(bool(i['aliases_slp1']) for t,i in pairs),
            aliases=sum(len(i['aliases_slp1']) for t,i in pairs),
            unresolved_tasks=sum(bool(i['unresolved_contexts']) for t,i in pairs))
    periphrastic=[(t,i) for t,i in zip(ts,policy['items']) if '3.1.35' in t['campaign']['trace_rule_ids'] and t['morphology']['lakara']=='Lit']
    controls=json.loads((OUT/'controls.json').read_text())
    tm={t['id']:t for t in ts};im={i['task_id']:i for i in policy['items']}
    for c in controls:
        assert c['canonical_slp1'] in tm[c['id']]['gold_slp1']
        assert c['alias_slp1'] in im[c['id']]['aliases_slp1']
        assert c['proof'] in im[c['id']]['evidence'];checks['representative_control_membership']+=1
    assert len({c['gana'] for c in controls})==10 and len({c['morphology']['lakara'] for c in controls})==10
    assert before=={p:sha(ROOT/p) for p in before}
    report=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='independent modification/5D agent',
        decision='bounded_adoption_recommended_with_mandatory_source_adjudication',blockers=[],benchmark_ready=False,evaluation_authorized=False,
        checks=dict(checks),tense_coverage=bytense,
        periphrastic_perfect=dict(tasks=len(periphrastic),canonical_forms=sum(len(t['gold_slp1']) for t,i in periphrastic),
             tasks_with_aliases=sum(bool(i['aliases_slp1']) for t,i in periphrastic),aliases=sum(len(i['aliases_slp1']) for t,i in periphrastic),
             example=dict(id=periphrastic[0][0]['id'],canonical=periphrastic[0][0]['gold_slp1'],aliases=periphrastic[0][1]['aliases_slp1']),
             limitation='Generic phonological transfer on the joined canonical string; not exhaustive alternative segmentation, auxiliary, lexical or spelling certification.'),
        conditions=['Every parsed unrecognized usable answer needs independent source adjudication before a linguistic error or advancement claim.',
                    'Execution layer must separately classify refusal/truncation/unparsed responses; scorer does not infer transport usability.',
                    'Preserve canonical, predeclared-whitelist and later adjudicated scores, full membership and unresolved counts; any new correction must apply symmetrically.',
                    'Instantiate the hash-checking scorer under a frozen execution/analysis manifest; do not treat this proposal as an installed runner change.'],
        limitations=['53 tasks have explicitly flagged residual cluster contexts; this is not an exhaustive list of possible missing forms.',
                     'All surface unions are preserved but not every lexical paradigm is independently source-certified.',
                     'No periphrastic spelling segmentation alternatives or new phonological rules were added.'],
        source_reading=['8.4.46 postvocalic r/h context, excluding duplicated r/h','8.4.47 simple postvocalic cluster and pause','8.4.49 sibilant-before-vowel prohibition','8.4.53 and 8.4.55 first-copy deaspiration','8.4.56 singleton/doubled final stop alternatives'],
        model_outputs_read=False,paid_calls=0,protected_files_unchanged=True,protected_hashes=before,
        reviewer_script_sha256=sha(Path(__file__)))
    (OUT/'independent-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'decision':report['decision'],'checks':report['checks'],'periphrastic_perfect':report['periphrastic_perfect'],'tense_coverage':bytense},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
