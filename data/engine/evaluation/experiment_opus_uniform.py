"""Budgeted wording experiments, always rooted in the original v2 templates.

All four families use the same variant. Only `run` makes model requests.
The $5 ceiling reserves the full 128k output maximum before each request;
therefore only one request may run at a time and some budget may remain unused.
"""

import argparse
from collections import Counter
from copy import deepcopy
import difflib
import fcntl
import importlib
import json
import os
from pathlib import Path
import random
import string
import sys
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.evaluation import experiment_opus_wording as common

opus, base = common.opus, common.base
FOLDER = ROOT / 'data/benchmark/experiments/opus55-uniform-v2'
FAMILIES = ('tinanta', 'krdanta', 'taddhitanta', 'subanta')
BUDGET = 5.0
MAX_REQUESTS = 600
HARD = 'taddhitanta:loqana:basic:Napumsaka:TAl'
TINANTA = '06.0035:Lan:Kartari:Uttama:Bahu'
VARIANTS = ('original', 'no_role', 'shared_question', 'shared_exercise', 'shared_sentences')
LEAD = {
    'tinanta': 'conjugated verb form (tinanta)',
    'krdanta': 'primary verbal derivative (krdanta)',
    'taddhitanta': 'nominal derivative (taddhitanta)',
    'subanta': 'inflected nominal form (subanta)',
}
RULES = {
    'tinanta': 'Use the supplied Dhatupatha citation, including anubandha markers, verb class, traditional meaning, and any verbal prefixes. Apply the specified tense or mood, voice, person, and number.',
    'krdanta': 'Use the supplied Dhatupatha citation, including anubandha markers, verb class, traditional meaning, and any verbal prefixes. Apply the specified primary suffix and any participle coordinates. For a noun or adjective, give the uninflected stem without case or number endings. For an indeclinable, give the complete form.',
    'taddhitanta': 'Use the supplied nominal base with its stated grammatical interpretation. Apply the specified taddhita affix in any meaning licensed for that affix. Give the derived nominal stem or complete indeclinable without case or number endings.',
    'subanta': 'Use the supplied nominal stem with the specified gender, case, and number. Give the complete standalone noun or adjective form. When a feminine stem is supplied, use that stem rather than reconstructing it from a masculine headword.',
}


def fields(text):
    return sorted(f for _, f, _, _ in string.Formatter().parse(text) if f)


def transform(text, family, variant):
    if variant == 'original':
        return text
    if variant == 'no_role':
        return text.removeprefix('You are an expert in Sanskrit grammar (vyakarana).\n\n')
    intro, data = text.split('=== Your task ===', 1)
    answer = 'Write ONLY the final form' + intro.split('Write ONLY the final form', 1)[1].rstrip()
    if variant == 'shared_question':
        lead = f'What is the Sanskrit {LEAD[family]} specified below?'
    elif variant in ('shared_exercise', 'shared_sentences'):
        lead = f'Complete this Sanskrit grammar exercise: form the {LEAD[family]} specified below.'
    else:
        raise ValueError(variant)
    if variant == 'shared_sentences':
        lines = []
        for line in data.strip().splitlines():
            # Optional renderer-generated blocks remain literal and intact.
            if ': ' in line:
                label, value = line.removeprefix('- ').split(': ', 1)
                lines.append(f'The {label} is {value}.')
            else:
                lines.append(line)
        data = '\n\n' + '\n'.join(lines) + '\n'
    return lead + '\n\n' + RULES[family] + '\n\n' + answer + '\n\n=== Your task ===' + data


def render(template, family, task):
    module = importlib.import_module(f'data.engine.{family}.common')
    with patch.object(module, 'template_text', return_value=template):
        return module.render_task(task)


def reserve(prompt, manifest):
    # UTF-8 byte upper estimate plus framing allowance. No caching is requested.
    rates = manifest['pricing']['rates_usd_per_million_tokens']
    return ((len(prompt.encode('utf-8')) + 1024) * max(rates['uncached_input'], rates['cache_write_input'])
            + opus.REQUEST_DEFAULTS['max_tokens'] * rates['output']) / 1e6


def can_admit(spent, unknown_reserve, next_reserve):
    return spent + unknown_reserve + next_reserve <= BUDGET


def read_json(path):
    return json.loads(path.read_text())


def recover(folder, manifest, cases):
    journal = base.Journal(folder / 'journals/requests.jsonl')
    starts, records = {}, {}
    for event in journal.read():
        key = event['task_id']
        if event['event'] == 'started':
            if key in starts:
                raise RuntimeError('Duplicate request start')
            starts[key] = event
        elif event['event'] in ('response', 'error'):
            if key not in starts or key in records:
                raise RuntimeError('Unmatched terminal event')
            p = starts[key]['plan']
            row = opus.result_row(event, cases[p['case_id']]['task'], manifest)
            records[key] = {**{k: p[k] for k in ('request_key', 'case_id', 'family', 'phase', 'variant')}, **row}
        else:
            raise RuntimeError('Unknown journal event')
    if len(starts) > MAX_REQUESTS or set(starts) != records.keys():
        raise RuntimeError('Request cap exceeded or unresolved start; never resubmit automatically')
    return journal, starts, records


def load(folder):
    m, cases = read_json(folder / 'manifest.json'), read_json(folder / 'cases.json')
    if m['budget_usd'] != BUDGET or m['request_defaults'] != opus.REQUEST_DEFAULTS:
        raise RuntimeError('Settings changed')
    if common.sha(cases) != m['cases_sha256']:
        raise RuntimeError('Cases changed')
    for entry in [m['script'], *m['dependencies']]:
        base.verify_descriptor(entry)
    for entry in m['source_tasks']:
        for name in ('dataset', 'sampling_manifest', 'prompt_template', 'renderer'):
            base.verify_descriptor(entry[name])
    return m, cases, *recover(folder, m, cases)


def summarize(records):
    rows = list(records.values())
    return {'total': common.metrics(rows), 'stages': {
        phase: {'variants': {v: common.metrics([r for r in rows if r['phase'] == phase and r['variant'] == v])
                            for v in sorted({r['variant'] for r in rows if r['phase'] == phase})},
                'families': {f: common.metrics([r for r in rows if r['phase'] == phase and r['family'] == f]) for f in FAMILIES}}
        for phase in sorted({r['phase'] for r in rows})}}


def prepare(folder):
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError('Experiment already exists; cannot reset budget')
    source, tasks, prompts, _ = opus.load_inputs()
    originals = {f: (ROOT / f'data/engine/prompts/v2/vp_{f}.txt').read_text() for f in FAMILIES}
    results = {f: {r['task_id']: r for r in read_json(opus.RUN / f'{f}.json')} for f in FAMILIES}
    prior = set()
    for name in ('opus55-cyber-wording', 'opus55-cyber-wording-round2', 'opus55-cyber-wording-round3'):
        for c in read_json(folder.parent / name / 'cases.json'):
            prior.add((c['family'], c['task']['id']))
    cases = {}
    for f in FAMILIES:
        for task_id, task in tasks[f].items():
            cid = f'{f}/{task_id}'
            cases[cid] = {'case_id': cid, 'family': f, 'task': task,
                          'original_prompt': prompts[f, task_id],
                          'original_status': results[f][task_id]['status'],
                          'used_in_prior_experiment': (f, task_id) in prior}
    rng = random.Random(69)
    def cid(f, t):
        return f'{f}/{t}'
    def sample(f, n, refused=False, exclude=()):
        available = sorted(k for k, r in results[f].items() if cid(f, k) not in exclude
                           and r['status'] == ('refused' if refused else 'completed'))
        return [cid(f, t) for t in rng.sample(available, n)]
    discovery = [cid('taddhitanta', HARD)] * 3 + [
        cid('taddhitanta', 'taddhitanta:selaga:basic:Pum:Sas'),
        cid('taddhitanta', 'taddhitanta:AntrikI:nyap:Stri:kan'), cid('tinanta', TINANTA)]
    discovery += sample('tinanta', 2, True, discovery) + sample('krdanta', 3, True) + sample('subanta', 1)
    assert len(discovery) == 12
    used = set(discovery)
    validation = []
    for f in FAMILIES:
        fresh = sorted(k for k, c in cases.items() if c['family'] == f and k not in used
                       and not c['used_in_prior_experiment'] and c['original_status'] in ('completed', 'refused'))
        flagged = [k for k in fresh if cases[k]['original_status'] == 'refused']
        picked = rng.sample(flagged, min(10, len(flagged)))
        normal = [k for k in fresh if cases[k]['original_status'] == 'completed']
        picked += rng.sample(normal, 20 - len(picked))
        validation += picked
        used.update(picked)
    confirmation = []
    for f in FAMILIES:
        available = sorted(k for k, c in cases.items() if c['family'] == f and k not in used
                           and not c['used_in_prior_experiment'] and c['original_status'] in ('completed', 'refused'))
        chosen = rng.sample(available, 20)
        confirmation += chosen
        used.update(chosen)
    # Additional repeated challenges are kept separate from fresh-task rates.
    challenge = [cid('taddhitanta', HARD)] * 10 + [cid('tinanta', TINANTA)] * 5
    challenge += [k for k in discovery if cases[k]['family'] == 'krdanta'][:2] * 2 + [discovery[-1]]
    assert len(challenge) == 20
    folder.mkdir(parents=True)
    (folder / 'journals').mkdir()
    candidate_dir = common.FOLDER / 'candidate-templates'
    before = folder / 'candidate-templates-before'
    before.mkdir()
    for p in candidate_dir.iterdir():
        if p.is_file():
            base.atomic_write(before / p.name, p.read_text())
    m = {'experiment': 'opus55-uniform-v2', 'created_at': base.now(), 'status': 'prepared',
         'budget_usd': BUDGET, 'request_safety_cap': MAX_REQUESTS, 'submitted_requests': 0,
         'request_defaults': deepcopy(opus.REQUEST_DEFAULTS), 'pricing': source['pricing'],
         'source_tasks': source['tasks'], 'original_templates': originals,
         'cases_sha256': common.sha(cases), 'script': opus.descriptor(Path(__file__)),
         'dependencies': [opus.descriptor(Path(common.__file__)), opus.descriptor(Path(opus.__file__)),
                          opus.descriptor(Path(base.__file__)), source['scoring']['implementation']],
         'stages': {}, 'sampling_seed': 69,
         'prospective_cases': {'discovery': discovery, 'validation': validation,
                               'confirmation': confirmation, 'challenge': challenge},
         'budget_policy': 'Sequential requests; reserve full 128000 output tokens plus conservative input allowance before every admission. Unknown costs retain reservation and pause. A strict $5 ceiling can leave roughly $2.6 unspent because no smaller output cap is imposed.',
         'selection_policy': 'Use one variant across all four families. Prefer zero observed refusals, then strict accuracy, then fewer edits from original v2. Inspect results before freezing the next stage; preserve any adaptive amendments.',
         'scope': 'Small targeted wording study, not a population refusal estimate. Validation is fresh but enriched with previously refused tasks; confirmation is sampled from remaining benchmark tasks; repeated challenge calls are reported separately.',
         'preservation': 'Keep all inputs and answer format; no tools, fallbacks, automatic retries, answer leakage, or production prompt/benchmark changes.'}
    # Keep only prospectively selected tasks, not a duplicate of the whole benchmark.
    included = set(discovery + validation + confirmation + challenge)
    cases = {k: v for k, v in cases.items() if k in included}
    m['cases_sha256'] = common.sha(cases)
    common.write_json(folder / 'cases.json', cases)
    common.write_json(folder / 'manifest.json', m)
    common.write_json(folder / 'results.json', [])
    add_stage(folder, 'discovery', VARIANTS, discovery)
    return {'discovery_requests': 60, 'budget_usd': BUDGET, 'prospective_validation': 80, 'prospective_confirmation': 80, 'challenge': 20}


def add_stage(folder, name, variants, selected_cases=None, reason=None, template_overrides=None):
    with (folder / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, cases, _, starts, records = load(folder)
        if name in m['stages']:
            raise RuntimeError('Stage already frozen')
        ids = selected_cases if selected_cases is not None else m['prospective_cases'][name]
        templates = {v: template_overrides[v] if template_overrides and v in template_overrides else
                     {f: transform(m['original_templates'][f], f, v) for f in FAMILIES} for v in variants}
        for v, family_templates in templates.items():
            for f, t in family_templates.items():
                if fields(t) != fields(m['original_templates'][f]):
                    raise RuntimeError('Template placeholders changed')
        plan = []
        for i, cid in enumerate(ids):
            c = cases[cid]
            for v in variants:
                plan.append({'request_key': f'{name}:{i:03}:{v}', 'case_id': cid, 'family': c['family'],
                             'task_id': c['task']['id'], 'phase': name, 'variant': v,
                             'prompt': render(templates[v][c['family']], c['family'], c['task'])})
        random.Random(69 + len(m['stages'])).shuffle(plan)
        if len(starts) + len(plan) > MAX_REQUESTS:
            raise RuntimeError('Request safety cap')
        m['stages'][name] = {'created_at': base.now(), 'status': 'prepared', 'plan_sha256': common.sha(plan),
                             'templates': templates, 'requests': len(plan), 'reason': reason}
        common.write_json(folder / f'{name}-plan.json', plan)
        common.write_json(folder / 'manifest.json', m)
        return {'stage': name, 'requests': len(plan), 'variants': list(variants)}


def run(folder, stage):
    with (folder / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, cases, journal, starts, records = load(folder)
        config = m['stages'][stage]
        plan = read_json(folder / f'{stage}-plan.json')
        if common.sha(plan) != config['plan_sha256']:
            raise RuntimeError('Plan changed')
        for p in plan:
            k = p['request_key']
            if k in starts and starts[k]['request'] != opus.request_body(p['prompt']):
                raise RuntimeError('Request changed')
        if any(r['cost_usd'] is None or r['status'] not in ('completed', 'refused') for r in records.values()):
            raise RuntimeError('Inspect errors before continuing')
        key = os.environ.get('ANTHROPIC_API_KEY') or opus.dotenv_values(ROOT / '.env').get('ANTHROPIC_API_KEY')
        if not key:
            raise RuntimeError('Missing Anthropic key')
        m['status'] = 'running'
        config['status'] = 'running'
        stop = None
        def checkpoint():
            summary = summarize(records)
            m.update(submitted_requests=len(starts), updated_at=base.now(), stopped_reason=stop,
                     known_cost_usd=summary['total']['known_cost_usd'])
            common.write_json(folder / 'results.json', sorted(records.values(), key=lambda r: r['request_key']))
            common.write_json(folder / 'summary.json', summary)
            common.write_json(folder / 'manifest.json', m)
        checkpoint()
        with opus.httpx.Client(timeout=opus.httpx.Timeout(1800, connect=30), follow_redirects=False,
                               transport=opus.httpx.HTTPTransport(retries=0)) as client:
            for p in plan:
                k = p['request_key']
                if k in starts:
                    continue
                spent = sum(r['cost_usd'] or 0 for r in records.values())
                reserved = reserve(p['prompt'], m)
                if len(starts) >= MAX_REQUESTS or not can_admit(spent, 0, reserved):
                    stop = 'Budget guard: insufficient dollars to reserve one full-output request'
                    break
                body, client_id = opus.request_body(p['prompt']), str(uuid.uuid4())
                marker = {'event': 'started', 'task_id': k, 'attempt_number': 1, 'timestamp': base.now(),
                          'client_request_id': client_id, 'plan': p, 'request': body, 'reserved_usd': reserved}
                journal.append(marker)
                starts[k] = marker
                checkpoint()
                event = opus.execute(client, m, k, body, client_id, journal, key)
                row = opus.result_row(event, cases[p['case_id']]['task'], m)
                records[k] = {**{x: p[x] for x in ('request_key', 'case_id', 'family', 'phase', 'variant')}, **row}
                if row['status'] not in ('completed', 'refused') or row['cost_usd'] is None:
                    stop = f'Inspect {k}: {row["status"]}; retain full cost reservation'
                elif row['cost_usd'] > reserved:
                    stop = 'Cost exceeded reservation'
                checkpoint()
                print(base.compact({'stage': stage, 'settled': len(records), 'last': k, 'status': row['status'],
                                    'correct': row['correct'], 'cost_usd': m['known_cost_usd'], 'stop': stop}), flush=True)
                if stop:
                    break
        config['status'] = 'completed' if all(p['request_key'] in records for p in plan) else 'paused'
        m['status'] = stage + '_complete' if config['status'] == 'completed' else 'paused'
        checkpoint()
        return {'status': m['status'], 'total': summarize(records)['total'], 'stage': summarize(records)['stages'].get(stage)}


def verify(folder, selected=None, install=False):
    with (folder / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        m, cases, journal, starts, records = load(folder)
        if sorted(records.values(), key=lambda r: r['request_key']) != read_json(folder / 'results.json'):
            raise RuntimeError('Replay mismatch')
        if summarize(records) != read_json(folder / 'summary.json'):
            raise RuntimeError('Summary mismatch')
        validator = opus.Draft202012Validator(opus.schema())
        extras = {'request_key', 'case_id', 'family', 'phase', 'variant'}
        for r in records.values():
            validator.validate([{k: v for k, v in r.items() if k not in extras}])
        running_cost = 0
        for key, start in starts.items():
            p = start['plan']
            stage = m['stages'][p['phase']]
            plan = read_json(folder / f'{p["phase"]}-plan.json')
            if common.sha(plan) != stage['plan_sha256'] or p not in plan:
                raise RuntimeError('Plan mismatch')
            expected = render(stage['templates'][p['variant']][p['family']], p['family'], cases[p['case_id']]['task'])
            if expected != p['prompt'] or start['request'] != opus.request_body(expected):
                raise RuntimeError('Prompt/request mismatch')
            if not can_admit(running_cost, 0, start['reserved_usd']):
                raise RuntimeError('Admission exceeded budget')
            running_cost += records[key]['cost_usd'] if records[key]['cost_usd'] is not None else start['reserved_usd']
        if running_cost > BUDGET:
            raise RuntimeError('Budget exceeded')
        result = {'verified_at': base.now(), 'requests': len(records), 'total': summarize(records)['total'],
                  'cost_including_unknown_reserves_usd': round(running_cost, 10), 'budget_usd': BUDGET,
                  'exact_hydration_and_request_settings_verified': True, 'schema_and_journal_replay_verified': True,
                  'production_templates_unchanged': True}
        if selected:
            tested = [s['templates'][selected] for s in m['stages'].values() if selected in s['templates']]
            if not tested or any(t != tested[0] for t in tested):
                raise RuntimeError('Selected variant missing or changed across stages')
            templates = tested[0]
            matching = [r for k, r in records.items() if starts[k]['request']['messages'][0]['content'] == render(templates[r['family']], r['family'], cases[r['case_id']]['task'])]
            result.update(selected_variant=selected, matching_final_templates=common.metrics(matching),
                          matching_by_family={f: common.metrics([r for r in matching if r['family'] == f]) for f in FAMILIES},
                          matching_by_stage={s: common.metrics([r for r in matching if r['phase'] == s]) for s in m['stages']})
            if install:
                target = common.FOLDER / 'candidate-templates'
                (folder / 'candidate-templates-after').mkdir(exist_ok=True)
                # Check every destination before replacing any of them.
                for f, template in templates.items():
                    current = target / f'vp_{f}.txt'
                    before = (folder / 'candidate-templates-before' / current.name).read_text()
                    if current.read_text() not in (before, template):
                        raise RuntimeError('Candidate changed externally')
                for f, template in templates.items():
                    current = target / f'vp_{f}.txt'
                    before = (folder / 'candidate-templates-before' / current.name).read_text()
                    if current.read_text() not in (before, template):
                        raise RuntimeError('Candidate changed externally')
                    base.atomic_write(folder / 'candidate-templates-after' / current.name, template)
                    base.atomic_write(current, template)
                provenance = {'updated_at': base.now(), 'experiment': str(folder.relative_to(ROOT)),
                              'variant': selected, 'all_four_use_same_variant': True,
                              'files': {f: opus.descriptor(target / f'vp_{f}.txt') for f in FAMILIES},
                              'results': result, 'caveat': 'Finite observed refusal counts do not establish zero future refusal probability.'}
                common.write_json(target / 'provenance.json', provenance)
                result['candidate_files'] = provenance['files']
        common.write_json(folder / 'verification.json', result)
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'stage', 'run', 'verify'))
    parser.add_argument('--folder', type=Path, default=FOLDER)
    parser.add_argument('--stage')
    parser.add_argument('--variants', nargs='+')
    parser.add_argument('--selected')
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        output = prepare(args.folder)
    elif args.action == 'stage':
        output = add_stage(args.folder, args.stage, args.variants)
    elif args.action == 'run':
        output = run(args.folder, args.stage)
    else:
        output = verify(args.folder, args.selected, args.install)
    print(json.dumps(output, ensure_ascii=False, indent=2))
