"""Offline staging for a fixed 4D/5D evaluation; never selects items or pays APIs.

The caller supplies an ordered task set and a sampling plan chosen before test
answers. This tool validates their inputs and emits an authorization fragment
for coordinator review. It does not install the runner's release gate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io, vp_goal as runner
from misc.vp_goal_validate import RENDERERS, validate

PHASES = {'four_d': ('bench_final', 'bench_extension'),
          'five_d': ('hard_final', 'hard_extension')}


def phase_pair(track, protocol='legacy16k-v1'):
    if protocol == 'legacy16k-v1':
        return PHASES[track]
    if protocol == 'common64k-v1' and track == 'five_d':
        return ('hard_final_64k', 'hard_extension_64k')
    raise ValueError('Unknown track or release protocol')


def transport_stages(tasks, track, protocol='legacy16k-v1', stage_sizes=None, extension_chunk=500):
    core, extension = phase_pair(track, protocol)
    boundary = min(1000, len(tasks))
    if stage_sizes is None:
        stage_sizes = [boundary] + [min(extension_chunk, len(tasks)-i)
                                   for i in range(boundary, len(tasks), extension_chunk)]
    if (not stage_sizes or any(type(n) is not int or n <= 0 for n in stage_sizes)
            or sum(stage_sizes) != len(tasks)):
        raise ValueError('Positive fixed stage sizes must exactly sum to N')
    stages, start = [], 0
    for size in stage_sizes:
        stop = start + size
        if start < boundary < stop:
            raise ValueError('Payment chunk crosses the 1000-question core boundary')
        stages.append({'phase': core if start < boundary else extension,
                       'tasks': tasks[start:stop]})
        start = stop
    return stages


def audit_partition(tasks, stages, track, protocol='legacy16k-v1'):
    """Require an exact ordered partition, including identical task metadata."""
    core, extension = phase_pair(track, protocol)
    if not tasks or len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError('Full membership must be nonempty and unique')
    flattened = []
    core_count = 0
    saw_extension = False
    for stage in stages:
        if not stage['tasks']:
            raise ValueError('Empty stage')
        phase = stage['phase']
        if phase == core:
            if saw_extension:
                raise ValueError('Core stages must precede extensions')
            core_count += len(stage['tasks'])
        elif phase == extension:
            saw_extension = True
        else:
            raise ValueError('Wrong track or phase')
        flattened.extend(stage['tasks'])
    if core_count != min(1000, len(tasks)):
        raise ValueError('Exactly the first 1000 tasks must use the core phase')
    if runner.digest(flattened) != runner.digest(tasks):
        raise ValueError('Stages must exactly partition ordered full membership')
    if len(tasks) - core_count > 5000:
        raise ValueError('Extension exceeds the existing runner allowance')
    return {'n': len(tasks), 'core_n': core_count,
            'extension_n': len(tasks) - core_count, 'stage_count': len(stages),
            'exact_ordered_partition': True}


def freeze(tasks_path, plan_path, output, track, extension_chunk=500, *, protocol='legacy16k-v1', stage_sizes=None):
    """Write a new, auditable candidate freeze. No model outputs are read."""
    tasks_path, plan_path, output = map(Path, (tasks_path, plan_path, output))
    if output.exists():
        raise ValueError('Release directory exists; use a new version')
    if track not in PHASES or not 1 <= extension_chunk <= 1000:
        raise ValueError('Unknown track or invalid extension chunk')
    source_hash, plan_hash = io.sha256(tasks_path), io.sha256(plan_path)
    tasks, plan = io.read_json(tasks_path), io.read_json(plan_path)
    if not 500 <= len(tasks) <= 6000:
        raise ValueError('Fixed release must contain 500–6000 unique tasks')
    if plan.get('track') != track or plan.get('fixed_n') != len(tasks):
        raise ValueError('Sampling plan must declare this track and exact fixed_n')
    if plan.get('point_accuracy_target') != [0.79, 0.81]:
        raise ValueError('Sampling plan must preserve the current accuracy target')
    if plan.get('precision_standard_error_lt') != 0.01:
        raise ValueError('Sampling plan must preserve the precision requirement')
    expected_type = 'cartesian_4d' if track == 'four_d' else 'cartesian_5d'
    if any(t.get('task_type') != expected_type for t in tasks):
        raise ValueError('Mixed or expanded task dimensions')
    if len({t['prompt_version'] for t in tasks}) != 1:
        raise ValueError('A release must use a single frozen prompt version')
    current = io.read_json(ROOT / 'benchmarks/parallel-search-20261006/plan.json')
    policy_path = ROOT / 'benchmarks/parallel-search-20261006' / current['oracle_policy']
    policy = io.read_json(policy_path)
    if policy.get('adapter_sha256', policy.get('generator_sha256')) != io.sha256(ROOT / 'misc/vp_cartesian_task.py'):
        raise ValueError('Current scope policy does not fingerprint the loaded generator')
    audit = validate(tasks, 'test')
    core, extension = phase_pair(track, protocol)
    protocols = {phase: {'effort': runner.PHASES[phase][0],
                         'max_output_tokens': runner.PHASES[phase][1]}
                 for phase in (core, extension)}
    if protocols[core] != protocols[extension]:
        raise ValueError('Core and extension reference protocols must match')
    stages = transport_stages(tasks, track, protocol, stage_sizes, extension_chunk)
    partition = audit_partition(tasks, stages, track, protocol)
    if io.sha256(tasks_path) != source_hash or io.sha256(plan_path) != plan_hash:
        raise ValueError('Source tasks or sampling plan changed during validation')
    output.mkdir(parents=True)
    io.atomic_json(output / 'tasks.json', tasks)
    io.atomic_json(output / 'sampling-plan.json', plan)
    records, authorization = [], {}
    for index, stage in enumerate(stages, 1):
        path = output / f'stage-{index:02d}.tasks.json'
        io.atomic_json(path, stage['tasks'])
        digest = runner.digest(stage['tasks'])
        records.append({'stage': index, 'phase': stage['phase'], 'n': len(stage['tasks']),
                        'path': path.name, 'sha256': io.sha256(path), 'tasks_digest': digest})
        authorization.setdefault(stage['phase'], []).append(digest)
    counts = {field: dict(Counter(t['morphology'][field] for t in tasks))
              for field in ('lakara', 'prayoga', 'purusha', 'vacana')}
    counts['gana'] = dict(Counter(t['dhatu']['gana'] for t in tasks))
    counts['recipe'] = dict(Counter(t['campaign']['construction'] for t in tasks))
    family_tenses = Counter((t['campaign']['root_family'], t['morphology']['lakara']) for t in tasks)
    manifest = {'created_at': io.now(), 'status': 'mechanically_audited_freeze_candidate',
                'track': track, 'protocol_version': protocol, 'fixed_n': len(tasks), 'benchmark_ready': False,
                'passed_mechanical_checks': True, 'audit': audit, 'partition': partition,
                'distributions': counts,
                'repeated_family_tense_pairs': sum(n > 1 for n in family_tenses.values()),
                'maximum_tasks_in_one_family_tense': max(family_tenses.values()),
                'source_tasks_path': str(tasks_path.resolve()),
                'source_tasks_sha256': source_hash,
                'source_sampling_plan_path': str(plan_path.resolve()),
                'source_sampling_plan_sha256': plan_hash,
                'frozen_tasks_sha256': io.sha256(output / 'tasks.json'),
                'frozen_sampling_plan_sha256': io.sha256(output / 'sampling-plan.json'),
                'oracle_policy_path': str(policy_path.relative_to(ROOT)),
                'oracle_policy_sha256': io.sha256(policy_path),
                'prompt_version': tasks[0]['prompt_version'],
                'prompt_renderer_sha256': io.sha256(Path(sys.modules[
                    RENDERERS[tasks[0]['prompt_version']].__module__].__file__)),
                'vp_versions': sorted({t['campaign']['vp_version'] for t in tasks}),
                'dependency_sha256': {str(p.relative_to(ROOT)): io.sha256(p) for p in (
                    Path(__file__), ROOT / 'misc/vp_cartesian_task.py',
                    ROOT / 'misc/vp_cartesian_release_run.py', ROOT / 'misc/vp_goal.py',
                    policy_path,
                    Path(sys.modules[RENDERERS[tasks[0]['prompt_version']].__module__].__file__),
                    ROOT / 'misc/vp_goal_validate.py', ROOT / 'misc/vp_goal_stats.py',
                    ROOT / 'misc/vp_cartesian_final_analyze.py',
                    ROOT / 'misc/vp_cartesian_release_protocol.py', ROOT / 'misc/vp_cartesian_visibility.py',
                    ROOT / 'misc/vp_cartesian_analyze.py', ROOT / 'misc/oai_batch_eval.py',
                    ROOT / 'misc/ant_batch_eval.py', ROOT / 'finetune/prompts.py',
                    ROOT / 'misc/benchmark_forward.py', ROOT / 'misc/vp_parallel_monitor.py',
                    ROOT / 'misc/vp_goal_analyze.py',
                    ROOT / 'misc/vp_sanskrit_prompt_v1.py',
                    ROOT / 'data/finetune/task-data/vidyut_dhatupatha_5.tsv',
                    runner.HISTORY / 'family-split.json')},
                'stages': records, 'authorized_by_phase': authorization,
                'reference_models': {p: v['model'] for p, v in runner.PROVIDERS.items()},
                'reference_protocol_by_phase': protocols,
                'execution': 'Use identical stage files for both references. Settle all 1000 core questions before extensions. Every stage remains subject to the shared maximum-cost budget gate. This tool makes no paid calls and does not install release-freeze.json.',
                'stopping': 'All fixed_n questions are primary. Transport staging never permits stopping based on final accuracy or SE. If funding or an external failure prevents completion, report an incomplete evaluation, not a precision-qualified benchmark.',
                'limits': 'Mechanical checks do not establish independent linguistic validity, sufficient diversity, target difficulty or precision. Coordinator must review the sampling rationale, source audit and prospective choice before authorizing execution.'}
    io.atomic_json(output / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tasks', type=Path)
    parser.add_argument('sampling_plan', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--track', choices=PHASES, required=True)
    parser.add_argument('--extension-chunk', type=int, default=500)
    parser.add_argument('--protocol', choices=['legacy16k-v1','common64k-v1'], default='legacy16k-v1')
    parser.add_argument('--stage-sizes', type=Path, help='JSON list of fixed positive stage sizes summing to N')
    args = parser.parse_args()
    result = freeze(args.tasks, args.sampling_plan, args.output, args.track, args.extension_chunk,
                    protocol=args.protocol, stage_sizes=io.read_json(args.stage_sizes) if args.stage_sizes else None)
    print({k: result[k] for k in ('track', 'fixed_n', 'status')})
