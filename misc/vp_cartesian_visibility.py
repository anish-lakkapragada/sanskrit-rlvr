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
