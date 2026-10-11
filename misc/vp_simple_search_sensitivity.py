"""Additive paired sensitivity for the source hold identified before outcomes."""
from misc import vp_goal as runner, oai_batch_eval as io
from misc.vp_simple_search_analyze import OUT, describe, paired


def analyze():
    declaration = OUT / 'source-sensitivity-predeclaration.json'
    if not declaration.exists():
        return None
    spec = io.read_json(declaration)
    holdpath = runner.ROOT / spec['hold_path']
    if io.sha256(holdpath) != spec['hold_sha256']:
        raise ValueError('Source hold changed after supplementary declaration')
    holds = io.read_json(holdpath)
    state = runner.load()
    names = ['opus-modification-01', 'opus-modification-control-01']
    result = {'updated_at': io.now(), 'state': 'waiting_for_both_complete_arms',
              'hold_sha256': spec['hold_sha256'], 'held_pairs': len(holds['pairs']),
              'raw_membership_and_scores_unchanged': True, 'benchmark_ready': False}
    jobs = [state['jobs'][name] for name in names]
    if all(j.get('settled') and j.get('collected_at') for j in jobs):
        arms = []
        for job, role, hashkey in zip(jobs, ['modification_id', 'control_id'], ['tasks_sha256', 'controls_sha256']):
            path = runner.OUT / 'jobs' / job['id']
            tasks, _ = runner.verify_job(job)
            if io.sha256(path / 'tasks.json') != holds[hashkey]:
                # Job copies may differ in whitespace: check canonical contents as well.
                original = OUT / 'modification-01' / ('tasks.json' if role == 'modification_id' else 'controls.json')
                if io.sha256(original) != holds[hashkey] or io.read_json(original) != tasks:
                    raise ValueError('Sensitivity panel differs from reviewed inputs')
            rows = io.read_json(path / 'results.json')
            held = {p[role] for p in holds['pairs']}
            if not held <= {t['id'] for t in tasks}:
                raise ValueError('Held pair is missing')
            kept = [t for t in tasks if t['id'] not in held]
            retained = [r for r in rows if r['task']['id'] not in held]
            arms.append((describe(kept, retained), retained))
        result.update(state='complete_supplementary_sensitivity', modification=arms[0][0],
                      control=arms[1][0], paired=paired(arms[0][1], arms[1][1]))
    io.atomic_json(OUT / 'source-sensitivity.json', result)
    return result
