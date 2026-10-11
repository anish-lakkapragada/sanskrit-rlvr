"""Prepare/count exact final requests. Never creates model generations or jobs."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
from misc import vp_continuous64k as run, vp_goal as legacy, oai_batch_eval as io

ROOT=legacy.ROOT
CANDIDATE=ROOT/'benchmarks/parallel-search-20261007/four_d-90/candidate-1800-v1'
OUT=ROOT/'benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01'


def prepare():
    tasks=io.read_json(CANDIDATE/'tasks.json')
    review=io.read_json(CANDIDATE/'independent-input-review.json')
    if not review['passed'] or review['tasks_sha256']!=io.sha256(CANDIDATE/'tasks.json'):
        raise ValueError('Input review is not current')
    from misc.vp_goal_validate import validate
    validate(tasks,'test')
    requests={p:[run.request_for(t,p,i) for i,t in enumerate(tasks)] for p in run.HARD_CAPS}
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'requests.json'
    if path.exists():
        if io.read_json(path)!=requests:raise ValueError('Prepared exact requests changed')
    else:io.atomic_json(path,requests)
    return tasks,requests


def count_inputs():
    _,requests=prepare();path=OUT/'input-counts.json'
    saved=io.read_json(path) if path.exists() else {}
    for provider,items in requests.items():
        digest=legacy.digest(items)
        if provider in saved and saved[provider]['requests_digest']!=digest:
            raise ValueError('Counts belong to different exact requests')
        entry=saved.setdefault(provider,dict(requests_digest=digest,counts={}))
        missing=[i for i in range(len(items)) if str(i) not in entry['counts']]
        if not missing:continue
        client=legacy.client_for(provider)
        def count(index):
            body=items[index]
            if provider=='Anthropic':
                result=client.messages.count_tokens(model=body['model'],messages=body['messages'],
                    thinking=body['thinking'],tools=[],tool_choice={'type':'none'})
                n=result.input_tokens
            else:
                import httpx
                result=client.post('/responses/input_tokens',cast_to=httpx.Response,
                    body={k:body[k] for k in ('model','input','tools','tool_choice','reasoning')}).json()
                n=result['input_tokens']
            if type(n) is not int or not 0<n<=1300:raise ValueError('Input allowance exceeded')
            return str(index),n
        pool=ThreadPoolExecutor(max_workers=12)
        try:
            futures=[pool.submit(count,i) for i in missing]
            for future in as_completed(futures):
                index,n=future.result();entry['counts'][index]=n
                if len(entry['counts'])%100==0:
                    io.atomic_json(path,saved)
                    print(f'{provider}: {len(entry["counts"])}/{len(items)} input estimates; no generation',flush=True)
        except Exception as exc:
            io.atomic_json(path,saved)
            io.atomic_json(OUT/'input-count-error.json',io.error_details(exc,client))
            raise RuntimeError('Input counting stopped; partial estimates saved; no generation requests') from None
        finally:
            pool.shutdown(wait=True,cancel_futures=True)
        entry.update(counted_at=io.now(),maximum=max(entry['counts'].values()))
        io.atomic_json(path,saved)
    return saved


def draft_plan():
    tasks,requests=prepare()
    counts=io.read_json(OUT/'input-counts.json')
    for p,items in requests.items():
        if counts[p]['requests_digest']!=legacy.digest(items) or len(counts[p]['counts'])!=len(items):
            raise ValueError('Complete exact provider counts required')
    candidate=io.read_json(CANDIDATE/'manifest.json')
    paths={
        'tasks_path':CANDIDATE/'tasks.json','public_prompts_path':CANDIDATE/'public-prompts.json',
        'candidate_manifest_path':CANDIDATE/'manifest.json','input_review_path':CANDIDATE/'independent-input-review.json',
        'source_policy_path':CANDIDATE/'source-policy.json','scoring_adoption_path':CANDIDATE/'scoring-adoption.json',
        'scorer_path':CANDIDATE/'spelling-policy-proposal/scorer.py',
        'scoring_review_path':CANDIDATE/'spelling-policy-proposal/independent-review.json',
        'alias_policy_path':CANDIDATE/'spelling-policy-proposal/alias-policy.json',
        'spelling_rules_path':CANDIDATE.parent/'ending-screen-01/alias_policy.py',
        'paired_analyzer_path':ROOT/'misc/vp_continuous64k_analyze.py',
        'requests_path':OUT/'requests.json','input_counts_path':OUT/'input-counts.json'}
    files=set(paths.values())|{ROOT/name for name in candidate['dependencies']}
    files.update(ROOT/name for name in [
        'misc/vp_continuous64k.py','misc/vp_continuous64k_prepare.py',
        'misc/vp_goal.py','misc/vp_goal_validate.py','misc/vp_cartesian_task.py',
        'misc/vp_cartesian_prompt_v1.py','misc/oai_batch_eval.py','misc/ant_batch_eval.py',
        'misc/vp_simple_astra_compare.py','misc/vp_ending_screen_run.py',
        'misc/vp_simple_search_analyze.py','misc/vp_cartesian_final_analyze.py',
        'misc/vp_cartesian_analyze.py','misc/vp_goal_stats.py','misc/vp_cartesian_visibility.py',
        'finetune/prompts.py','prompts/v2/vp_task_eval.txt',
        'benchmarks/creation-campaign-20261006/family-split.json'])
    state=legacy.load()
    p=dict(schema=run.VERSION,phase=run.PHASE,split='test',run_id='original4d-final1800-64k-01',
        created_at=io.now(),n=len(tasks),effort='xhigh',max_output_tokens=65536,
        provider_caps_micro=run.HARD_CAPS,rates_micro_per_token={p:list(v) for p,v in run.RATES.items()},
        pool_caps_micro={'Anthropic':100_000_000,'OpenAI':225_000_000},
        concurrency={'Anthropic':16,'OpenAI':16},protected_allocation=legacy.protected_allocations(state),
        fixed_task_ids=[t['id'] for t in tasks],tasks_digest=legacy.digest(tasks),
        request_digests={p:[legacy.digest(x) for x in rows] for p,rows in requests.items()},
        dependencies={str(path.relative_to(ROOT)):io.sha256(path) for path in sorted(files)},
        **{k:str(v.relative_to(ROOT)) for k,v in paths.items()},
        rationale='Evaluate the complete independent original4D candidate using the grammar mixture validated on both development references. The full1800 cohort is fixed; no outcome-driven subset, retries or changes.',
        sample_size='1800 projects iidSE below1pp across80–90%; family-generalization precision remains unproven and is measured separately. Evaluation is not a waiver of the earlier precision requirement.',
        protocol_revision='This whole fixed>=500 paired cohort replaces legacy1000-core/extension execution mechanics for the latest single-benchmark goal, retaining64k and test-family validation. No test tasks are registered as development.',
        accounting='Only settled usage plus full outstanding/unknown maxima may consume each pool. Both pools fit current unprotected headroom; preserve existing final reserves. Complete1800 execution is conditional on realized usage, never correctness.',
        analysis='No score before both fixed1800 cohorts have terminal validated receipts. Preserve canonical/whitelist scores and independently adjudicate every unrecognized usable answer; symmetric corrections and full denominators.',
        benchmark_ready=False)
    for provider in run.HARD_CAPS:
        if legacy.committed(state,provider)+legacy.protected_remaining(state,provider)+p['pool_caps_micro'][provider]>run.HARD_CAPS[provider]:
            raise ValueError('Proposed pool cannot fit current protected lifetime headroom')
    path=OUT/'execution-plan.json'
    if path.exists():raise ValueError('Preserve the existing draft/freeze; version amendments separately')
    io.atomic_json(path,p)
    run.inspect_manifest(OUT,require_review=False)
    print({'draft_ready':True,'paid_calls':0,'ledger_mutated':False,'n':p['n']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','count','draft'])
    command=parser.parse_args().command
    if command=='prepare':print({'prepared':len(prepare()[0]),'paid_calls':0})
    elif command=='count':count_inputs()
    else:draft_plan()
