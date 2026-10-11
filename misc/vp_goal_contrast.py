"""Fresh contrast sets: one root, different derived stems and tense systems."""
import hashlib
import random
from collections import Counter
from pathlib import Path

from misc import vp_goal as c, vp_compositional as g, vp_compositional_deep as deep, oai_batch_eval as io
from misc.vp_finite_pada import task_for
from misc.vp_goal_paradigm import make_task
from misc.vp_compositional_prompt_v4 import render as render_form
from vidyut.prakriya import Lakara, Purusha, Vacana


def generate(label, cells, seed=20261020, max_per_family=1):
    path = c.OUT / (label+'.json')
    if path.exists():
        raise ValueError('Panel already frozen')
    assignments = io.read_json(c.HISTORY/'family-split.json')['families']
    entries = {}
    for e in g.old.load_entries():
        f = g.old.family(e)
        if assignments[f]['split'] == 'development':
            entries.setdefault(f, e)
    used = set()
    for manifest in c.OUT.glob('*.sampling.json'):
        for t in io.read_json(c.OUT/io.read_json(manifest)['filename']):
            used.update(x['id'] for x in t.get('forms', [t]))
    for job in c.load()['jobs'].values():
        for t in io.read_json(c.OUT/'jobs'/job['id']/'tasks.json'):
            used.update(x['id'] for x in t.get('forms', [t]))
    rng, tasks, counts = random.Random(seed), [], Counter()
    for cell in cells:
        n = 0
        for cycle in range(15):
            order = list(entries.items()); rng.shuffle(order)
            for family, e in order:
                if counts[family] >= max_per_family or g.old.name(e.dhatu.gana) in cell['exclude_ganas']:
                    continue
                prefixes = rng.choice(cell['prefixes'])
                person, number = rng.choice(Purusha.choices()), rng.choice(Vacana.choices())
                forms = []
                for i, row in enumerate(cell['rows']):
                    construction = row['construction']
                    factory = deep.task_for if construction in deep.CONSTRUCTIONS else task_for
                    form = factory(e, 'development', construction, prefixes,
                                   (getattr(Lakara,row['lakara']),person,number), 'Parasmaipada')
                    if not form or form['id'] in used or set(form['campaign']['trace_rule_ids']) & set(row.get('exclude_rules', [])):
                        break
                    form['campaign']['sampling_cell'] = {
                        'label':f"{cell['label']}, row {i+1}", 'construction':construction,
                        'lakaras':[row['lakara']], 'dhatu_padas':['Parasmaipada'],
                        'prefixes':cell['prefixes'], 'exclude_ganas':cell['exclude_ganas'],
                        'exclude_rules':row.get('exclude_rules', [])}
                    form['campaign']['prompt_sha256'] = hashlib.sha256(render_form(form).encode()).hexdigest()
                    forms.append(form)
                if len(forms) != len(cell['rows']):
                    continue
                task = make_task(forms, 'finite_contrast')
                task['campaign'].update(panel=label, sampling_cell=cell)
                tasks.append(task); counts[family] += 1; n += 1
                used.update(f['id'] for f in forms)
                if n == cell['n']:
                    break
            if n == cell['n']:
                break
        if n != cell['n']:
            raise ValueError(f'Insufficient valid contrast supply: {n}')
    io.atomic_json(path,tasks)
    io.atomic_json(c.OUT/(label+'.sampling.json'),{
        'created_at':io.now(),'filename':path.name,'n':len(tasks),'cells':cells,'split':'development',
        'seed':seed,'root_families':len(counts),'max_per_family':max(counts.values()),
        'task_digest':c.digest(tasks),'generator_sha256':io.sha256(Path(__file__)),
        'selection':'Shuffled development root visits; all component forms fresh; no model-score selection.'})
    return tasks
