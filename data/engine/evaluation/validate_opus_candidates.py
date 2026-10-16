"""Fresh, budgeted validation of the frozen uniform candidate templates.

No prompt tuning, automatic retries, or result replacement. CLI preparation is
offline; only `run` calls the provider. Output allowance is an explicit setting.
"""
import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
import fcntl
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import experiment_opus_uniform as prior

opus, base, common = prior.opus, prior.base, prior.common
FOLDER = ROOT / 'data/benchmark/experiments/opus55-uniform-validation'
FAMILIES = prior.FAMILIES
TARGET_SPEND = 2.0
PER_FAMILY = 100


def body(prompt, manifest, max_tokens=None):
    request = {**deepcopy(manifest['request_defaults']), 'messages': [{'role': 'user', 'content': prompt}]}
    if max_tokens is not None:
        request['max_tokens'] = max_tokens
    return request


def reservation(prompt, manifest, max_tokens=None):
    rates = manifest['pricing']['rates_usd_per_million_tokens']
    return ((len(prompt.encode()) + 1024) * max(rates['uncached_input'], rates['cache_write_input'])
            + (max_tokens if max_tokens is not None else manifest['request_defaults']['max_tokens']) * rates['output']) / 1e6


def affordable_request(prompt, manifest, remaining):
    """Use the largest output allowance that fits the remaining dollar budget."""
    maximum = manifest['request_defaults']['max_tokens']
    if manifest.get('output_budget_policy') == 'remaining_dollars':
        rate = manifest['pricing']['rates_usd_per_million_tokens']['output'] / 1e6
        input_reserve = reservation(prompt, manifest, 0)
        maximum = min(maximum, math.floor((remaining - input_reserve - 1e-9) / rate))
    if maximum < 1:
        return None, 0
    return body(prompt, manifest, maximum), reservation(prompt, manifest, maximum)


def admission(spent, committed, pending_reserve, budget, target=TARGET_SPEND):
    return spent < target and spent + committed + pending_reserve <= budget


def wilson(successes, n):
    if not n:
        return None
    z = 1.959963984540054
    p = successes / n
    denominator = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denominator
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return [max(0, centre-radius), min(1, centre+radius)]


def metrics(rows):
    stat = common.metrics(rows)
    n = stat['requests']
    stat.update(accuracy=stat['correct']/n if n else None,
                strict_accuracy=stat['strict_correct']/n if n else None,
                accuracy_wilson_95=wilson(stat['strict_correct'], n),
                refusal_wilson_95=wilson(stat['refusals'], n),
                truncated=sum((r.get('error') or {}).get('stop_reason') == 'max_tokens' for r in rows),
                max_output_tokens=max(((r.get('usage') or {}).get('output_tokens', 0) for r in rows), default=0),
                min_requested_output_allowance=min((r['max_tokens'] for r in rows), default=None),
                max_requested_output_allowance=max((r['max_tokens'] for r in rows), default=None))
    if n and stat['refusals'] == 0:
        stat['zero_refusal_one_sided_95_upper'] = 1 - .05**(1/n)
    return stat


def summarize(records):
    rows = list(records.values())
    return {'total': metrics(rows), 'families': {f: metrics([r for r in rows if r['family'] == f]) for f in FAMILIES}}


def prior_cases():
    seen, descriptors = set(), []
    for name in ('opus55-cyber-wording', 'opus55-cyber-wording-round2',
                 'opus55-cyber-wording-round3', 'opus55-uniform-v2'):
        path = FOLDER.parent / name / 'cases.json'
        data = prior.read_json(path)
        rows = data.values() if isinstance(data, dict) else data
        seen.update((c['family'], c['task']['id']) for c in rows)
        descriptors.append(opus.descriptor(path))
    return seen, descriptors


def sample(tasks, excluded, per_family=PER_FAMILY):
    rng = random.Random(69)
    chosen = {f: rng.sample(sorted(k for k in tasks[f] if (f, k) not in excluded), per_family) for f in FAMILIES}
    order = []
    for i in range(per_family):
        families = list(FAMILIES)
        rng.shuffle(families)
        order.extend((f, chosen[f][i]) for f in families)
    return order


def prepare(folder, max_tokens, budget, rationale):
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError('Existing validation; never reset spending history')
    if (max_tokens, budget) not in ((16000, 2.0), (128000, 3.0), (128000, 5.0)):
        raise RuntimeError('Use an explicitly selected budget/output configuration')
    source, tasks, _, _ = opus.load_inputs()
    excluded, sources = prior_cases()
    provenance = prior.read_json(common.FOLDER / 'candidate-templates/provenance.json')
    assert provenance['variant'] == 'table_rules_first'
    for descriptor in provenance['files'].values():
        base.verify_descriptor(descriptor)
    templates = {f: (ROOT / provenance['files'][f]['path']).read_text() for f in FAMILIES}
    plan = []
    for i, (f, task_id) in enumerate(sample(tasks, excluded)):
        task = tasks[f][task_id]
        plan.append({'request_key': f'{i:04}:{f}:{task_id}', 'family': f, 'task': task,
                     'prompt': prior.render(templates[f], f, task)})
    settings = deepcopy(opus.REQUEST_DEFAULTS)
    settings['max_tokens'] = max_tokens
    folder.mkdir(parents=True)
    (folder / 'journals').mkdir()
    (folder / 'templates').mkdir()
    for f, text in templates.items():
        base.atomic_write(folder / 'templates' / f'vp_{f}.txt', text)
    manifest = {'experiment': 'opus55-uniform-validation', 'created_at': base.now(), 'status': 'prepared',
                'budget_usd': budget, 'target_spend_usd': TARGET_SPEND, 'submitted_requests': 0,
                'request_defaults': settings, 'configuration_rationale': rationale,
                'output_budget_policy': 'remaining_dollars' if budget == 3.0 else 'fixed',
                'pricing': source['pricing'], 'source_tasks': source['tasks'],
                'template_sources': provenance['files'], 'template_text': templates,
                'exclusion_sources': sources, 'excluded_tasks': len(excluded),
                'sampling': {'seed': 69, 'planned_per_family': PER_FAMILY, 'planned_requests': len(plan),
                             'method': 'Uniform sample without replacement from each 5000-task benchmark, excluding every task reserved in all prior wording experiments. Interleaved family order keeps a budget-limited prefix approximately balanced. No selection by previous correctness or refusal status.'},
                'plan_sha256': common.sha(plan), 'script': opus.descriptor(Path(__file__)),
                'dependencies': [opus.descriptor(Path(prior.__file__)), opus.descriptor(Path(common.__file__)),
                                 opus.descriptor(Path(opus.__file__)), opus.descriptor(Path(base.__file__)), source['scoring']['implementation']],
                'budget_policy': 'Before each request, reserve its full actual output allowance and a conservative input estimate. In remaining_dollars mode, send sequentially and choose the largest allowance (up to 128000) fitting the remaining ceiling; stop around the $2 target, leaving roughly $1 headroom. Retain full reserves for unknown costs. No retries. Fixed mode uses its configured allowance unchanged.',
                'evaluation': 'Exact accepted-answer membership; strict accuracy additionally requires precisely one answer block and no outside text. All requested tasks enter accuracy denominators, including refusals, incomplete responses and infrastructure failures.',
                'scope': 'Frozen-template validation; never edit templates in response to these results. Fresh means unused in prompt experiments, not unseen in the original full benchmark. Report family-specific rates and intervals; zero observed refusals does not establish a zero population rate.'}
    common.write_json(folder / 'plan.json', plan)
    common.write_json(folder / 'manifest.json', manifest)
    common.write_json(folder / 'results.json', [])
    return {'requests_planned': len(plan), 'per_family': PER_FAMILY, 'max_tokens': max_tokens,
            'budget_usd': budget, 'target_spend_usd': TARGET_SPEND}


def recover(folder, manifest, plan):
    journal = base.Journal(folder / 'journals/requests.jsonl')
    mapping = {p['request_key']: p for p in plan}
    starts, records, sequence = {}, {}, []
    for event in journal.read():
        k = event['task_id']
        if k not in mapping:
            raise RuntimeError('Unknown request')
        p = mapping[k]
        if event['event'] == 'started':
            allowance = event['request'].get('max_tokens')
            if (k in starts or type(allowance) is not int or not 0 < allowance <= manifest['request_defaults']['max_tokens']
                    or event['request'] != body(p['prompt'], manifest, allowance)):
                raise RuntimeError('Duplicate or modified request')
            starts[k] = event
        elif event['event'] in ('response', 'error'):
            if k not in starts or k in records:
                raise RuntimeError('Unmatched terminal event')
            records[k] = {'request_key': k, 'family': p['family'], 'max_tokens': starts[k]['request']['max_tokens'],
                          **opus.result_row(event, p['task'], manifest)}
        else:
            raise RuntimeError('Unexpected event')
        sequence.append(event)
    return journal, starts, records, sequence


def load(folder):
    manifest, plan = prior.read_json(folder / 'manifest.json'), prior.read_json(folder / 'plan.json')
    if common.sha(plan) != manifest['plan_sha256']:
        raise RuntimeError('Plan changed')
    expected = deepcopy(opus.REQUEST_DEFAULTS)
    expected['max_tokens'] = manifest['request_defaults']['max_tokens']
    if manifest['request_defaults'] != expected or (expected['max_tokens'], manifest['budget_usd']) not in ((16000, 2.0), (128000, 3.0), (128000, 5.0)):
        raise RuntimeError('Settings changed')
    if manifest['output_budget_policy'] != ('remaining_dollars' if manifest['budget_usd'] == 3.0 else 'fixed'):
        raise RuntimeError('Output budget policy changed')
    for d in [manifest['script'], *manifest['dependencies'], *manifest['template_sources'].values(), *manifest['exclusion_sources']]:
        base.verify_descriptor(d)
    for task in manifest['source_tasks']:
        for name in ('dataset', 'sampling_manifest', 'prompt_template', 'renderer'):
            base.verify_descriptor(task[name])
    return manifest, plan, *recover(folder, manifest, plan)


def run(folder):
    with (folder / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, plan, journal, starts, records, _ = load(folder)
        if set(starts) != records.keys():
            raise RuntimeError('Unresolved start blocks resume; never resubmit')
        if any(r['cost_usd'] is None for r in records.values()):
            raise RuntimeError('Unknown-cost attempt needs inspection')
        pending = [p for p in plan if p['request_key'] not in starts]
        key = os.environ.get('ANTHROPIC_API_KEY') or opus.dotenv_values(ROOT / '.env').get('ANTHROPIC_API_KEY')
        if not key:
            raise RuntimeError('Missing Anthropic key')
        stop, futures, cursor = None, {}, 0
        m.update(status='running', started_at=m.get('started_at') or base.now())
        last_print = 0
        def checkpoint(force=False):
            nonlocal last_print
            summary = summarize(records)
            unknown = sum(starts[k]['reserved_usd'] for k, r in records.items() if r['cost_usd'] is None)
            m.update(updated_at=base.now(), submitted_requests=len(starts), stopped_reason=stop,
                     known_cost_usd=summary['total']['known_cost_usd'], unknown_cost_reserve_usd=unknown)
            common.write_json(folder / 'results.json', [records[p['request_key']] for p in plan if p['request_key'] in records])
            common.write_json(folder / 'summary.json', summary)
            common.write_json(folder / 'manifest.json', m)
            if force or time.monotonic() - last_print > 20:
                print(base.compact({'at': base.now(), 'submitted': len(starts), 'settled': len(records),
                                    'in_flight': len(futures), 'cost_usd': m['known_cost_usd'],
                                    'refusals': summary['total']['refusals'], 'correct': summary['total']['strict_correct'], 'stop': stop}), flush=True)
                last_print = time.monotonic()
        checkpoint(True)
        concurrency = 1 if m['output_budget_policy'] == 'remaining_dollars' else 4
        with opus.httpx.Client(timeout=opus.httpx.Timeout(1800, connect=30), follow_redirects=False,
                               transport=opus.httpx.HTTPTransport(retries=0)) as client, ThreadPoolExecutor(max_workers=concurrency) as pool:
            while cursor < len(pending) or futures:
                spent = sum(r['cost_usd'] or 0 for r in records.values())
                while stop is None and cursor < len(pending) and len(futures) < concurrency:
                    p = pending[cursor]
                    committed = sum(value[1] for value in futures.values())
                    request, reserved = affordable_request(p['prompt'], m, m['budget_usd'] - spent - committed)
                    if request is None or not admission(spent, committed, reserved, m['budget_usd'], m['target_spend_usd']):
                        if not futures:
                            stop = 'Target reached' if spent >= m['target_spend_usd'] else 'Budget cannot reserve another full configured response'
                        break
                    k, client_id = p['request_key'], str(uuid.uuid4())
                    marker = {'event': 'started', 'task_id': k, 'attempt_number': 1, 'timestamp': base.now(),
                              'client_request_id': client_id, 'request': request, 'reserved_usd': reserved}
                    journal.append(marker)
                    starts[k] = marker
                    futures[pool.submit(opus.execute, client, m, k, request, client_id, journal, key)] = (p, reserved)
                    cursor += 1
                checkpoint()
                if not futures:
                    break
                done, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                for future in done:
                    p, reserved = futures.pop(future)
                    row = opus.result_row(future.result(), p['task'], m)
                    records[p['request_key']] = {'request_key': p['request_key'], 'family': p['family'],
                                                  'max_tokens': starts[p['request_key']]['request']['max_tokens'], **row}
                    if row['cost_usd'] is None or row['status'] in ('api_error', 'transport_error', 'unknown'):
                        stop = 'Infrastructure/unknown-cost result; stop admissions and preserve reservation'
                    elif row['cost_usd'] > reserved:
                        stop = 'Provider charge exceeded reservation'
                checkpoint()
        m.update(status='finished', finished_at=base.now())
        checkpoint(True)
        return summarize(records)


def verify(folder):
    with (folder / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, plan, journal, starts, records, sequence = load(folder)
        if m['status'] != 'finished' or set(starts) != records.keys():
            raise RuntimeError('Requests not settled')
        expected = [records[p['request_key']] for p in plan if p['request_key'] in records]
        if expected != prior.read_json(folder / 'results.json') or summarize(records) != prior.read_json(folder / 'summary.json'):
            raise RuntimeError('Journal replay mismatch')
        validator = opus.Draft202012Validator(opus.schema())
        validator.validate([{k: v for k, v in r.items() if k not in ('request_key', 'family', 'max_tokens')} for r in expected])
        mapping = {p['request_key']: p for p in plan}
        excluded, _ = prior_cases()
        assert len(mapping) == 4*PER_FAMILY and len({(p['family'], p['task']['id']) for p in plan}) == len(plan)
        assert not excluded.intersection((p['family'], p['task']['id']) for p in plan)
        for p in plan:
            assert p['prompt'] == prior.render(m['template_text'][p['family']], p['family'], p['task'])
        assert list(starts) == [p['request_key'] for p in plan[:len(starts)]]
        active, spent, unknown = {}, 0, 0
        for event in sequence:
            k = event['task_id']
            if event['event'] == 'started':
                if m['output_budget_policy'] == 'remaining_dollars':
                    assert not active
                expected_body, reserve = affordable_request(mapping[k]['prompt'], m, m['budget_usd']-spent-sum(active.values())-unknown)
                assert event['request'] == expected_body
                assert event['reserved_usd'] == reserve
                assert admission(spent, sum(active.values())+unknown, reserve, m['budget_usd'], m['target_spend_usd'])
                active[k] = reserve
            else:
                reserve = active.pop(k)
                cost = records[k]['cost_usd']
                if cost is None:
                    unknown += reserve
                else:
                    assert cost <= reserve
                    spent += cost
        assert not active and spent + unknown <= m['budget_usd']
        result = {'verified_at': base.now(), 'requests': len(records), 'cost_usd': round(spent, 10),
                  'unknown_cost_reserve_usd': unknown, 'budget_usd': m['budget_usd'],
                  'fresh_sample_no_duplicates': True, 'all_hydrated_prompts_verified': True,
                  'all_request_settings_verified': True, 'budget_admissions_replayed': True,
                  'schema_and_results_replayed': True, 'templates_and_production_sources_unchanged': True,
                  'summary': summarize(records)}
        journal.archive()
        # Reading the compressed log must reproduce exactly the same outcomes.
        assert recover(folder, m, plan)[2] == records
        common.write_json(folder / 'verification.json', result)
        report = ['FROZEN OPUS CANDIDATE VALIDATION', '',
                  f'Model: claude-opus-5-5, adaptive thinking, xhigh; maximum output allowance={m["request_defaults"]["max_tokens"]}.',
                  'No model tools, Internet, fallback, automatic retries, or prompt tuning.',
                  f'Estimated usage-based cost: ${spent:.6f}; unknown-cost reserve: ${unknown:.6f}; budget ceiling: ${m["budget_usd"]:.2f}.',
                  f'Stopping reason: {m["stopped_reason"] or "All planned requests settled"}.',
                  '', 'Family       Requests Correct Strict-correct Refusals Truncated']
        for family, stat in result['summary']['families'].items():
            report.append(f'{family:12} {stat["requests"]:8} {stat["correct"]:7} {stat["strict_correct"]:14} {stat["refusals"]:8} {stat["truncated"]:9}')
        stat = result['summary']['total']
        report += [f'TOTAL        {stat["requests"]:8} {stat["correct"]:7} {stat["strict_correct"]:14} {stat["refusals"]:8} {stat["truncated"]:9}', '',
                   f'Actual requested output allowances: {stat["min_requested_output_allowance"]}–{stat["max_requested_output_allowance"]} tokens. Largest observed output: {stat["max_output_tokens"]} tokens.',
                   'This run enforces a remaining-dollar output ceiling when necessary; it is not an identical-output-limit replication of the earlier fixed-128000 runs. xHigh effort and the prompt templates remain unchanged.',
                   'Seed 69, sampling without replacement, approximately equal family counts. Every reserved task from every earlier wording experiment was excluded, including unused plans.',
                   'Tasks come from the existing 5000-per-family benchmark; previous correctness/refusal outcomes were not used in sample selection. This is validation on tasks fresh to prompt experiments, not tasks unseen in the original benchmark.',
                   'Budget admissions retain the full configured output reserve, so actual spending can stop below the target. Every admitted request is retained and included in accuracy denominators.',
                   'Accuracy and refusal Wilson 95% intervals are in summary.json. A zero observed refusal count does not prove a zero population rate.',
                   f'Output setting: {m["configuration_rationale"]}',
                   'All prompts, responses, accepted answers, model settings, token usage, costs, and failure details are preserved in plan.json, manifest.json, results.json, and journals/requests.jsonl.gz.']
        common.write_json(folder / 'summary.json', result['summary'])
        base.atomic_write(folder / 'report.txt', '\n'.join(report)+'\n')
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run', 'verify'))
    parser.add_argument('--folder', type=Path, default=FOLDER)
    parser.add_argument('--max-tokens', type=int)
    parser.add_argument('--budget', type=float)
    parser.add_argument('--rationale')
    args = parser.parse_args()
    if args.action == 'prepare':
        if not args.rationale:
            parser.error('Record the budget/output configuration rationale')
        output = prepare(args.folder, args.max_tokens, args.budget, args.rationale)
    else:
        output = run(args.folder) if args.action == 'run' else verify(args.folder)
    print(json.dumps(output, ensure_ascii=False, indent=2))
