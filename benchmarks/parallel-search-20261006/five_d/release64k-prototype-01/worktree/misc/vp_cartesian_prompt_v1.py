"""Versioned 4D/5D prompts: exactly four coordinates, optionally sanadi."""
from finetune.prompts import render_vp_task
from misc.vp_compositional import OPERATIONS


def render(task):
    prompt = render_vp_task(task, 'v2/vp_task_eval.txt')
    if task['task_type'] == 'cartesian_4d':
        return prompt
    if task['task_type'] != 'cartesian_5d':
        raise ValueError('Unknown Cartesian task type')
    operations = task['derivation']['sanadi']
    recipe = ', followed by '.join(OPERATIONS[x] for x in operations) or 'none (ordinary conjugation)'
    addition = f'Sanskrit verb formation (sanadi; apply in the listed order): {recipe}\n\n'
    return prompt.replace('Required form:\n', addition + 'Required form:\n')
