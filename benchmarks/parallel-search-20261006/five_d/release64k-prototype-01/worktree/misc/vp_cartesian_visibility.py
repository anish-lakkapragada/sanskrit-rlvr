"""Suppress interim scores for the fixed paired development experiment."""

PILOT08_JOBS = tuple(
    [f'opus-five-d-pilot-08-{i:02}' for i in range(1, 7)]
    + [f'astra-five-d-pilot-08-{i:02}' for i in range(1, 3)]
)


def pending_confirmation_ids(state):
    jobs = state.get('jobs', {})
    complete = all(jobs.get(key, {}).get('settled')
                   and jobs.get(key, {}).get('collected_at')
                   for key in PILOT08_JOBS)
    return set() if complete else set(PILOT08_JOBS)


def visible_release_job(state, job):
    """Remove score/completion metrics until both providers' full cohort settles.

    Raw ledger/results are preserved. Report/monitor consumers should use this
    adapter before displaying a bound final job. Missing/corrupt bindings hide.
    """
    from misc import vp_goal as runner
    from misc.vp_cartesian_release_protocol import read_binding, stage_jobs
    public = dict(job)
    if not job.get('release_manifest_path') and job['phase'] not in runner.FINAL_ALIASES:
        return public
    try:
        manifest = read_binding(job, runner.ROOT, runner.PHASES, runner.PROVIDERS)
        _, pending = stage_jobs(state, manifest, job['release_manifest_sha256'], runner.PROVIDERS)
        hidden = bool(pending)
    except (ValueError, KeyError, OSError, TypeError):
        hidden = True
    if hidden:
        for key in ('summary', 'completed_answers', 'completed_correct', 'accuracy', 'results'):
            public.pop(key, None)
        public['scores_embargoed'] = True
    return public
