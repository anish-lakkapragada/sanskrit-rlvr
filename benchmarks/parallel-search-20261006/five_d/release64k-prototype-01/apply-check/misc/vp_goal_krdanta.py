"""Reviewed verbal derivation followed by nominal inflection; no model calls."""
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Krt, Linga, Pada, Pratipadika, Sanadi, Vacana, Vibhakti, Vyakarana
from misc import vp_compositional as g, vp_compositional_deep as deep, oai_batch_eval as io
from misc.vp_goal_grammar import validate_prefixes
from misc.vp_krdanta_prompt_v1 import render, KRT_LABELS

CONSTRUCTIONS = {**g.CONSTRUCTIONS, **deep.CONSTRUCTIONS}
OBLIQUE_CASES = ['Dvitiya','Trtiya','Caturthi','Panchami','Sasthi','Saptami']


def task_for(entry, split, construction, prefixes, krt, linga, vibhakti, vacana):
    validate_prefixes(prefixes)
    if krt not in KRT_LABELS:
        raise ValueError('Unreviewed krt suffix')
    if krt == 'Satf' and vibhakti not in OBLIQUE_CASES:
        raise ValueError('Present participle pilot excludes nominative and vocative context')
    ops = CONSTRUCTIONS[construction]
    dhatu = entry.dhatu.with_sanadi([getattr(Sanadi,x) for x in ops]).with_prefixes(prefixes)
    pratipadika = Pratipadika.krdanta(dhatu, getattr(Krt,krt))
    ps = Vyakarana().derive(Pada.Subanta(pratipadika,getattr(Linga,linga),getattr(Vibhakti,vibhakti),getattr(Vacana,vacana)))
    gold = sorted({p.text for p in ps})
    if not gold or len(gold)>64:
        return None
    deva = list(map(g.slp1_to_devanagari,gold))
    assert [transliterate(x,Scheme.Devanagari,Scheme.Slp1) for x in deva] == gold
    identity = [g.old.family(entry),ops,prefixes,krt,linga,vibhakti,vacana]
    task = {'id':'krdanta-'+hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24],
        'task_type':'krdanta_creation', 'prompt_version':'krdanta-v1',
        'dhatu':{'code':entry.code,'aupadeshika':entry.dhatu.aupadeshika,'gana':g.old.name(entry.dhatu.gana),'artha':entry.artha},
        'derivation':{'sanadi':ops,'prefixes':prefixes,'order':'innermost_to_outermost'},
        'morphology':{'krt':krt,'krt_artha':'Kartari','linga':linga,'vibhakti':vibhakti,'vacana':vacana},
        'gold_slp1':gold,'gold_devanagari':deva,
        'campaign':{'root_family':g.old.family(entry),'split':split,'construction':construction,
            'trace_rule_ids':sorted({h.code for p in ps for h in p.history if g.old.name(h.source)=='Ashtadhyayi'}),
            'minimum_trace_steps':min(len(p.history) for p in ps),'gold_variants':len(gold),'vp_version':vidyut.__version__,
            'selection_reason':'Score-independent derived-root and krt combination with nominal coordinates',
            'audit_status':'Engine and transliteration verified; independent reference checks recorded separately'}}
    task['campaign']['prompt_sha256'] = hashlib.sha256(render(task).encode()).hexdigest()
    return task


def validate_task(task, entry, split):
    m,d,meta = task['morphology'],task['derivation'],task['campaign']
    expected = task_for(entry,split,meta['construction'],d['prefixes'],m['krt'],m['linga'],m['vibhakti'],m['vacana'])
    if expected is None:
        raise ValueError('No engine derivation for requested krdanta')
    for key in ('id','task_type','prompt_version','dhatu','derivation','morphology','gold_slp1','gold_devanagari'):
        if task[key] != expected[key]:
            raise ValueError('Regenerated krdanta disagrees: '+key)
    for key in ('root_family','split','trace_rule_ids','minimum_trace_steps','gold_variants','vp_version','prompt_sha256'):
        if meta[key] != expected['campaign'][key]:
            raise ValueError('Krdanta metadata disagrees: '+key)
    cell = meta.get('sampling_cell',{})
    if cell.get('construction',meta['construction']) != meta['construction']:
        raise ValueError('Krdanta construction differs from sampling cell')
    if task['dhatu']['gana'] in cell.get('exclude_ganas',[]) or set(meta['trace_rule_ids']) & set(cell.get('exclude_rules',[])):
        raise ValueError('Krdanta violates declared exclusions')
    for field,value in [('krts',m['krt']),('lingas',m['linga']),('vibhaktis',m['vibhakti']),('vacanas',m['vacana']),('prefixes',d['prefixes'])]:
        if field in cell and value not in cell[field]:
            raise ValueError('Krdanta violates sampling field: '+field)


def generate(label,cells,split='development',seed=20261021,max_per_family=2):
    from misc import vp_goal as c
    path = c.OUT/(label+'.json')
    if path.exists():
        raise ValueError('Panel already frozen')
    for cell in cells:
        for prefixes in cell['prefixes']:
            validate_prefixes(prefixes)
    assignment = io.read_json(c.HISTORY/'family-split.json')['families']
    allowed = {f for f,a in assignment.items() if a['split']==split}
    if split=='test':
        allowed &= set(io.read_json(c.OUT/'test-family-reserve.json')['initial_release_families'])
    entries = {}
    for e in g.old.load_entries():
        if g.old.family(e) in allowed:
            entries.setdefault(g.old.family(e),e)
    used = set()
    for manifest in c.OUT.glob('*.sampling.json'):
        used.update(t['id'] for t in io.read_json(c.OUT/io.read_json(manifest)['filename']))
    for job in c.load()['jobs'].values():
        used.update(t['id'] for t in io.read_json(c.OUT/'jobs'/job['id']/'tasks.json'))
    rng, tasks, counts = random.Random(seed),[],Counter()
    for cell in cells:
        n = 0
        for cycle in range(15):
            roots = list(entries.items());rng.shuffle(roots)
            for family,entry in roots:
                if counts[family]>=max_per_family or g.old.name(entry.dhatu.gana) in cell.get('exclude_ganas',[]):
                    continue
                task = task_for(entry,split,cell['construction'],rng.choice(cell['prefixes']),rng.choice(cell['krts']),
                    rng.choice(cell.get('lingas',['Pum','Stri','Napumsaka'])),
                    rng.choice(cell.get('vibhaktis',OBLIQUE_CASES)),rng.choice(cell.get('vacanas',['Eka','Dvi','Bahu'])))
                if not task or task['id'] in used or set(task['campaign']['trace_rule_ids']) & set(cell.get('exclude_rules',[])):
                    continue
                task['campaign'].update(panel=label,sampling_cell=cell)
                tasks.append(task);used.add(task['id']);counts[family]+=1;n+=1
                if n==cell['n']:
                    break
            if n==cell['n']:
                break
        if n!=cell['n']:
            raise ValueError(f'Insufficient krdanta supply: {n}/{cell["n"]}')
    io.atomic_json(path,tasks)
    io.atomic_json(c.OUT/(label+'.sampling.json'),{'created_at':io.now(),'filename':path.name,'n':len(tasks),'split':split,
        'seed':seed,'cells':cells,'root_families':len(counts),'max_per_family':max(counts.values()),'task_digest':c.digest(tasks),
        'generator_sha256':io.sha256(Path(__file__)), 'selection':'Shuffled root visits and random grammatical coordinates; no model-score selection.'})
    return tasks
