"""Independent-root creation sets; each set is one all-forms-correct task."""
import copy
import hashlib
from misc.vp_bundle_prompt_v1 import render


def make_task(forms, prompt_version='bundle-v1'):
    from misc import vp_goal as c
    if len(forms) not in {2, 4}:
        raise ValueError('Only two/four-form creation sets are reviewed')
    families = [f['campaign']['root_family'] for f in forms]
    splits = {f['campaign']['split'] for f in forms}
    if len(set(families)) != len(forms) or len(splits) != 1:
        raise ValueError('Each form must have a distinct dhatu family in one split')
    if any(f.get('task_type') or f['prompt_version'] != 'composition-v4-pada' for f in forms):
        raise ValueError('Only individually audited finite forms with explicit pada are supported')
    task = {
        'id': 'bundle-' + c.digest([f['id'] for f in forms])[:24],
        'task_type': 'finite_bundle', 'prompt_version': prompt_version,
        'dhatu': {'members': [copy.deepcopy(f['dhatu']) for f in forms]},
        'derivation': {'prefixes': [], 'sanadi': [], 'order': 'innermost_to_outermost',
                       'operations_vary_by_row': True},
        'morphology': {'specifications_vary_by_row': True},
        'forms': copy.deepcopy(forms), 'gold_devanagari': [], 'gold_slp1': [],
        'campaign': {
            'split': next(iter(splits)), 'root_families': families,
            'root_family': 'cohort-' + c.digest(sorted(families))[:24],
            'construction': f'independent_creation_{len(forms)}',
            'base_construction': 'varies_by_row',
            'vp_version': forms[0]['campaign']['vp_version'],
            'selection_reason': 'Score-independent sets of distinct dhatus; headline requires every form correct; per-form accuracy reported separately.'}}
    renderer = render
    if prompt_version == 'bundle-v2-sanskrit':
        from misc.vp_sanskrit_prompt_v1 import render as renderer
    elif prompt_version != 'bundle-v1':
        raise ValueError('Unknown independent-creation prompt')
    task['campaign']['prompt_sha256'] = hashlib.sha256(renderer(task).encode()).hexdigest()
    return task


def validate_task(task, split, **kwargs):
    from misc.vp_goal_validate import validate
    validate(task['forms'], split, **kwargs)
    expected = make_task(task['forms'], task['prompt_version'])
    for key, value in expected.items():
        if key == 'campaign':
            if any(task[key].get(k) != v for k, v in value.items()):
                raise ValueError('Independent-creation metadata differs')
        elif task.get(key) != value:
            raise ValueError('Independent-creation data differs: ' + key)
