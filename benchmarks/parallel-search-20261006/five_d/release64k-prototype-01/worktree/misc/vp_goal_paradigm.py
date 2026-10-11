"""Small paradigm creation tasks, preserving per-form and all-forms metrics."""
import copy
import hashlib
import json
import random
import unicodedata
from collections import Counter
from pathlib import Path

from finetune.prompts import extract_answer
from misc import vp_compositional as g, oai_batch_eval as io
from misc.vp_finite_pada import task_for
from misc.vp_compositional_prompt_v4 import render as render_form
from misc.vp_paradigm_prompt_v1 import render
from vidyut.prakriya import Lakara, Purusha, Vacana


def make_task(forms, kind='finite_paradigm', prompt_version=None):
    if len(forms) not in {2, 4}:
        raise ValueError("Only the reviewed two/four-form format is enabled")
    first = forms[0]
    if kind not in {'finite_paradigm', 'finite_contrast'}:
        raise ValueError('Unknown multi-form task kind')
    for t in forms:
        if t['dhatu'] != first['dhatu'] or t['derivation']['prefixes'] != first['derivation']['prefixes']:
            raise ValueError("Multi-form tasks must share a root and prefixes")
        if kind == 'finite_paradigm' and t['derivation'] != first['derivation']:
            raise ValueError('A paradigm must share the same derivation')
        if t['morphology']['dhatu_pada'] != 'Parasmaipada':
            raise ValueError("Prompt specifies Parasmaipada")
    if kind == 'finite_paradigm' and len({t['morphology']['lakara'] for t in forms}) != len(forms):
        raise ValueError("Each requested tense must be distinct")
    if kind == 'finite_contrast' and len({tuple(t['derivation']['sanadi']) for t in forms}) != len(forms):
        raise ValueError('Each contrast row must use a different operation chain')
    identity = [t['id'] for t in forms]
    prefix = 'paradigm-' if kind == 'finite_paradigm' else 'contrast-'
    tid = prefix + hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    campaign = {k: copy.deepcopy(first['campaign'][k]) for k in ('root_family', 'split', 'vp_version')}
    campaign.update(construction=f"{prefix[:-1]}_{len(forms)}", base_construction=first['campaign']['construction'],
                    trace_rule_ids=sorted({r for t in forms for r in t['campaign']['trace_rule_ids']}),
                    minimum_trace_steps=sum(t['campaign']['minimum_trace_steps'] for t in forms),
                    selection_reason='Fresh score-independent paradigm; all requested forms must be correct')
    task = {'id':tid, 'task_type':kind, 'dhatu':copy.deepcopy(first['dhatu']),
            'derivation':copy.deepcopy(first['derivation']),
            'morphology':{'prayoga':'Kartari', 'dhatu_pada':'Parasmaipada'},
            'forms':copy.deepcopy(forms), 'gold_devanagari':[], 'gold_slp1':[],
            'prompt_version':'paradigm-v1', 'campaign':campaign}
    renderer = render
    if kind == 'finite_contrast':
        from misc.vp_contrast_prompt_v1 import render as renderer
        task['prompt_version'] = 'contrast-v1'
        task['derivation'] = {'prefixes':copy.deepcopy(first['derivation']['prefixes']),
                             'sanadi':[], 'order':'innermost_to_outermost', 'operations_vary_by_row':True}
        campaign['base_construction'] = 'varies_by_row'
        campaign['selection_reason'] = 'Fresh score-independent contrast set; all requested forms must be correct'
    if prompt_version is not None and prompt_version != task['prompt_version']:
        if kind == 'finite_paradigm' and prompt_version == 'paradigm-v2-sanskrit':
            from misc.vp_paradigm_prompt_v2 import render as renderer
        elif kind == 'finite_contrast' and prompt_version == 'contrast-v2-sanskrit':
            from misc.vp_contrast_prompt_v2 import render as renderer
        elif kind == 'finite_paradigm' and prompt_version == 'paradigm-v3-dhatu':
            from misc.vp_paradigm_prompt_v3 import render as renderer
        elif kind == 'finite_contrast' and prompt_version == 'contrast-v3-dhatu':
            from misc.vp_contrast_prompt_v3 import render as renderer
        elif kind == 'finite_paradigm' and prompt_version == 'paradigm-v4-lines':
            from misc.vp_paradigm_prompt_v4 import render as renderer
        elif kind == 'finite_contrast' and prompt_version == 'contrast-v4-lines':
            from misc.vp_contrast_prompt_v4 import render as renderer
        elif ((kind == 'finite_paradigm' and prompt_version == 'paradigm-v5-fields') or
              (kind == 'finite_contrast' and prompt_version == 'contrast-v5-fields')):
            from misc.vp_multiform_prompt_v5 import render as renderer
        else:
            raise ValueError('Prompt version does not match the multi-form task kind')
        task['prompt_version'] = prompt_version
    campaign['prompt_sha256'] = hashlib.sha256(renderer(task).encode()).hexdigest()
    return task


def grade(task, output):
    """Parse a single JSON answer without accepting duplicate/extra keys."""
    answer = extract_answer(output)
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError('Duplicate row key')
            obj[k] = v
        return obj
    try:
        if task.get('prompt_version') in {'paradigm-v4-lines','contrast-v4-lines',
                                         'paradigm-v5-fields','contrast-v5-fields','bundle-v1','bundle-v2-sanskrit'}:
            lines = [line.strip() for line in answer.splitlines() if line.strip()] if answer else []
            values = {str(i+1):line for i,line in enumerate(lines)}
        else:
            values = json.loads(answer, object_pairs_hook=unique) if answer else None
        valid = (isinstance(values, dict) and set(values) == {str(i+1) for i in range(len(task['forms']))}
                 and all(isinstance(v, str) and v.strip() for v in values.values()))
    except (ValueError, TypeError):
        values, valid = None, False
    norm = lambda s: unicodedata.normalize('NFC', s.strip())
    per_form = [bool(valid and norm(values[str(i+1)]) in {norm(gold) for gold in t['gold_devanagari']})
                for i, t in enumerate(task['forms'])]
    return {'format_valid':bool(valid), 'form_correct':per_form,
            'correct_forms':sum(per_form), 'n_forms':len(per_form),
            'is_correct':bool(valid and all(per_form)), 'answers':values if valid else None}


def validate_task(task, split, **kwargs):
    from misc.vp_goal_validate import validate
    validate(task['forms'], split, **kwargs)
    expected = make_task(task['forms'], task['task_type'], task['prompt_version'])
    for key in ('id','task_type','dhatu','derivation','morphology','gold_devanagari','gold_slp1','prompt_version'):
        if task[key] != expected[key]:
            raise ValueError('Paradigm metadata differs: ' + key)
    for key, value in expected['campaign'].items():
        if task['campaign'].get(key) != value:
            raise ValueError('Paradigm campaign metadata differs: ' + key)
    for t in task['forms']:
        if t['campaign']['root_family'] != task['campaign']['root_family']:
            raise ValueError('Mixed root families')
    if task['task_type'] == 'finite_contrast':
        cell = task['campaign']['sampling_cell']
        if len(cell['rows']) != len(task['forms']):
            raise ValueError('Contrast size differs from declared cell')
        for spec, form in zip(cell['rows'], task['forms']):
            if (spec['construction'] != form['campaign']['construction'] or
                spec['lakara'] != form['morphology']['lakara'] or
                set(form['campaign']['trace_rule_ids']) & set(spec.get('exclude_rules', []))):
                raise ValueError('Contrast row differs from declared cell')


def generate(label, cells, split='development', seed=20261018, max_per_family=2, allowed_families=None):
    from misc import vp_goal as c
    path = c.OUT / (label + '.json')
    if path.exists():
        raise ValueError('Panel already exists')
    assignments = io.read_json(c.HISTORY/'family-split.json')['families']
    allowed = {f for f, a in assignments.items() if a['split'] == split}
    if allowed_families is not None:
        if not set(allowed_families) <= allowed:
            raise ValueError('Requested family allocation crosses the immutable split')
        allowed &= set(allowed_families)
    elif split == 'test':
        allowed &= set(io.read_json(c.OUT/'test-family-reserve.json')['initial_release_families'])
    entries = {}
    for entry in g.old.load_entries():
        f = g.old.family(entry)
        if f in allowed:
            entries.setdefault(f, entry)
    used = set()
    for job in c.load()['jobs'].values():
        for t in io.read_json(c.OUT/'jobs'/job['id']/'tasks.json'):
            used.update(x['id'] for x in t.get('forms', [t]))
    for manifest in c.OUT.glob('*.sampling.json'):
        for t in io.read_json(c.OUT/io.read_json(manifest)['filename']):
            used.update(x['id'] for x in t.get('forms', [t]))
    rng, tasks, per_family = random.Random(seed), [], Counter()
    for cell in cells:
        n = 0
        for cycle in range(12):
            ordered = list(entries.items()); rng.shuffle(ordered)
            for family, entry in ordered:
                if per_family[family] >= max_per_family or g.old.name(entry.dhatu.gana) in cell.get('exclude_ganas', []):
                    continue
                prefixes = rng.choice(cell['prefixes'])
                forms = []
                for la in cell['lakaras']:
                    t = task_for(entry, split, cell['construction'], prefixes,
                                 (getattr(Lakara, la), rng.choice(Purusha.choices()), rng.choice(Vacana.choices())),
                                 'Parasmaipada')
                    if not t or t['id'] in used or set(t['campaign']['trace_rule_ids']) & set(cell.get('exclude_rules', [])):
                        break
                    t['campaign']['prompt_sha256'] = hashlib.sha256(render_form(t).encode()).hexdigest()
                    t['campaign']['sampling_cell'] = cell
                    forms.append(t)
                if len(forms) != len(cell['lakaras']):
                    continue
                task = make_task(forms)
                task['campaign'].update(panel=label, sampling_cell=cell)
                tasks.append(task); per_family[family] += 1; n += 1
                used.update(t['id'] for t in forms)
                if n == cell['n']:
                    break
            if n == cell['n']:
                break
        if n != cell['n']:
            raise ValueError(f'Insufficient paradigm supply: {n}')
    io.atomic_json(path, tasks)
    io.atomic_json(c.OUT/(label+'.sampling.json'), {
        'created_at':io.now(), 'filename':path.name, 'n':len(tasks), 'cells':cells, 'split':split,
        'seed':seed, 'root_families':len(per_family), 'max_per_family':max(per_family.values()),
        'task_digest':c.digest(tasks), 'generator_sha256':io.sha256(Path(__file__)),
        'selection':'Shuffled root visits; no response-based item filtering. No component task previously submitted.'})
    return tasks
