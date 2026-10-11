"""Metadata-only release identity, completion barriers and dependency checks."""
from pathlib import Path
from misc import oai_batch_eval as io

COMMON64_PHASES = {'hard_final_64k', 'hard_extension_64k'}

def release_binding(manifest_path):
    path = Path(manifest_path).resolve()
    return {'release_manifest_path': str(path),
            'release_manifest_sha256': io.sha256(path)}


def read_binding(job, root, phases, providers, *, dependencies=True):
    """Read frozen inputs/metadata only. Never read model results."""
    if not job.get('release_manifest_path'):
        if job['phase'] in COMMON64_PHASES:
            raise ValueError('Common64k final job requires an exact release binding')
        return None
    path = Path(job['release_manifest_path'])
    if io.sha256(path) != job.get('release_manifest_sha256'):
        raise ValueError('Frozen release manifest changed')
    manifest = io.read_json(path)
    if job['phase'] in COMMON64_PHASES:
        if (manifest.get('protocol_version') != 'common64k-v1' or manifest.get('track') != 'five_d'
                or set(manifest['reference_protocol_by_phase']) != COMMON64_PHASES
                or any(s['phase'] not in COMMON64_PHASES for s in manifest['stages'])):
            raise ValueError('Common64k release has a mixed or missing phase protocol')
    for phase, protocol in manifest['reference_protocol_by_phase'].items():
        if phase not in phases or protocol != {'effort': phases[phase][0], 'max_output_tokens': phases[phase][1]}:
            raise ValueError('Frozen release protocol changed')
    expected_protocol = {'effort': phases[job['phase']][0],
                         'max_output_tokens': phases[job['phase']][1]}
    if manifest['reference_protocol_by_phase'].get(job['phase']) != expected_protocol:
        raise ValueError('Job differs from frozen release protocol')
    if manifest['reference_models'] != {p: v['model'] for p, v in providers.items()}:
        raise ValueError('Frozen reference models changed')
    matches = [s for s in manifest['stages'] if s['phase'] == job['phase']
               and s['tasks_digest'] == job['tasks_digest'] and s['n'] == job['n']]
    if len(matches) != 1:
        raise ValueError('Job is not exactly one frozen release stage')
    if dependencies:
        for name, digest in manifest['dependency_sha256'].items():
            file = (Path(root) / name).resolve()
            if not file.is_relative_to(Path(root).resolve()) or io.sha256(file) != digest:
                raise ValueError('Frozen release dependency changed: ' + name)
        for name, digest in [('tasks.json', manifest['frozen_tasks_sha256']),
                             ('sampling-plan.json', manifest['frozen_sampling_plan_sha256'])]:
            if io.sha256(path.parent / name) != digest:
                raise ValueError('Frozen release input changed: ' + name)
        stage = matches[0]
        if io.sha256(path.parent / stage['path']) != stage['sha256']:
            raise ValueError('Frozen stage input changed')
        if io.sha256(Path(root) / manifest['oracle_policy_path']) != manifest['oracle_policy_sha256']:
            raise ValueError('Frozen oracle policy changed')
    return manifest


def stage_jobs(state, manifest, manifest_sha, providers):
    """Identify all attempted stage jobs, fail closed on duplicates/metadata drift."""
    selected, pending = {}, []
    binding_required = manifest.get('protocol_version') == 'common64k-v1'
    stage_keys = [(s['phase'], s['tasks_digest']) for s in manifest['stages']]
    if not stage_keys or len(stage_keys) != len(set(stage_keys)):
        raise ValueError('Frozen release stages must be nonempty and distinct')
    for provider in providers:
        selected[provider] = []
        for stage in manifest['stages']:
            matches = [j for j in state.get('jobs', {}).values()
                       if j['provider'] == provider and j['phase'] == stage['phase']
                       and j['tasks_digest'] == stage['tasks_digest'] and j.get('attempted_at')]
            if len(matches) > 1:
                raise ValueError('A primary final stage was attempted twice')
            if not matches:
                pending.append((provider, stage['tasks_digest']));continue
            job = matches[0]
            if 'n' in stage and job.get('n') != stage['n']:
                raise ValueError('Final stage count differs from its frozen manifest')
            if ((binding_required or job.get('release_manifest_sha256'))
                    and job.get('release_manifest_sha256') != manifest_sha):
                raise ValueError('Final stage belongs to a different release')
            if not job.get('settled') or not job.get('collected_at'):
                pending.append((provider, stage['tasks_digest']))
            selected[provider].append(job)
    return selected, pending


def require_complete_cohort(state, manifest, manifest_sha, providers):
    selected, pending = stage_jobs(state, manifest, manifest_sha, providers)
    if pending:
        raise ValueError('Full fixed release cohort must settle and collect before reading results')
    return selected


def require_settled_core(state, job, manifest, core_phase):
    """Every exact core stage of this release/protocol must settle, for this provider."""
    stages = [s for s in manifest['stages'] if s['phase'] == core_phase]
    if sum(s['n'] for s in stages) != 1000:
        raise ValueError('Collect and settle the core tier: exact 1000-question core required')
    core = dict(manifest, stages=stages)
    selected, pending = stage_jobs(state, core, job['release_manifest_sha256'], [job['provider']])
    if pending or sum(j['n'] for j in selected[job['provider']]) != 1000:
        raise ValueError('Collect and settle the core tier for the same release and protocol')
