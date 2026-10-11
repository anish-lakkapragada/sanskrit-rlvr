"""Describe the enriched wording diagnostic without treating it as a benchmark."""
from misc import vp_goal as runner, oai_batch_eval as io
from misc.vp_cartesian_analyze import metric

OUT = runner.ROOT / 'benchmarks/parallel-search-20261006/prompt-probe-01'


def analyze():
    plan = io.read_json(OUT / 'plan.json')
    refused_ids = set(plan['historically_refused_ids'])
    state = runner.load()
    arms = {}
    for version in ['v1', 'v2-verb', 'v3-sanskrit']:
        job_id = 'opus-cartesian-wording-01-' + version
        job = state['jobs'].get(job_id)
        if not job:
            continue
        arm = {'job_id': job_id, 'status': job['status'], 'n': job['n']}
        if job.get('collected_at'):
            path = runner.OUT / 'jobs' / job_id / 'results.json'
            rows = io.read_json(path)
            arm.update(overall=metric(rows),
                       previously_refused=metric([r for r in rows if r['task_id'] in refused_ids]),
                       random_completed_controls=metric([r for r in rows if r['task_id'] not in refused_ids]),
                       results_sha256=io.sha256(path), cost_usd=job['actual_cost_upper_micro'] / 1e6)
        arms[version] = arm
    result = {'updated_at': io.now(), 'arms': arms, 'unique_grammar_questions': 36,
              'limits': 'Same questions across arms, deliberately enriched for nine historical refusals. '
                        'These are diagnostic scores, not population benchmark accuracy or new independent tasks. '
                        'The fully Sanskrit arm was added after the first two arms showed seven refusals each.'}
    io.atomic_json(OUT / 'results.json', result)
    return result


if __name__ == '__main__':
    print(analyze())
