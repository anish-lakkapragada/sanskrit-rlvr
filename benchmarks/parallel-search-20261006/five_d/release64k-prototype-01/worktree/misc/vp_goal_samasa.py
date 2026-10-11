"""Audited prototype: one-word compounds of independently specified participants.

This uses a pinned Rust VP checkout because the installed Python API does not
expose samasa. No paid requests are made by this module.
"""
import hashlib
import json
import random
import subprocess
from collections import defaultdict
from pathlib import Path

from misc import vp_goal as c, vp_compositional as g, vp_compositional_deep as deep, oai_batch_eval as io
from misc.vp_samasa_prompt_v1 import render, CASES
from misc.vp_samasa_prompt_v2 import render as render_v2
from misc.vp_samasa_prompt_v3 import render as render_v3

RENDERERS = {'samasa-v1': render, 'samasa-v2-fields': render_v2, 'samasa-v3-fields': render_v3}

ENGINE_REV = '8da2f90bee3ce1c07505fa432fc3729e3f7e02ea'
ORACLE = Path('/tmp/vp-samasa-oracle-target/debug/vp-samasa-oracle')
ALLOWED = {'ric_san_ric_san','ric_san_ric_san_ric_san'}


def provenance():
    return {'engine_git_revision':ENGINE_REV, 'rust_crate_version':'0.2.0',
            'binary_sha256':io.sha256(ORACLE),
            'source_sha256':io.sha256(c.ROOT/'misc/vp_samasa_oracle/src/main.rs'),
            'cargo_lock_sha256':io.sha256(c.ROOT/'misc/vp_samasa_oracle/Cargo.lock')}


def oracle_many(requests):
    result = subprocess.run([str(ORACLE)],input=''.join(json.dumps(r)+'\n' for r in requests),
                            capture_output=True,text=True,timeout=180)
    if result.returncode:
        raise ValueError('Compound oracle failed: '+result.stderr[-1000:])
    rows = [json.loads(x) for x in result.stdout.splitlines()]
    if len(rows)!=len(requests):
        raise ValueError('Missing oracle responses')
    return rows


def member(entry, construction):
    if construction not in ALLOWED or g.old.name(entry.dhatu.gana)=='Curadi':
        raise ValueError('Unreviewed compound construction')
    return {'dhatu':{'code':entry.code,'aupadeshika':entry.dhatu.aupadeshika,
                     'gana':g.old.name(entry.dhatu.gana),'artha':entry.artha,
                     'antargana':g.old.name(entry.dhatu.antargana) if entry.dhatu.antargana else None},
            'root_family':g.old.family(entry),'sanadi':deep.CONSTRUCTIONS[construction],
            'prefixes':[],'krt':'Satf'}


def request(members, case, mode=None):
    return {'mode':mode,'items':[{'dhatu':m['dhatu']['aupadeshika'],'gana':m['dhatu']['gana'],
            'antargana':m['dhatu']['antargana'],'sanadi':m['sanadi'],'prefixes':[], 'krt':'Satf'} for m in members],
            'samasa_type':'Dvandva','vibhakti':case,'vacana':'Dvi' if len(members)==2 else 'Bahu'}


def prosody(text):
    positions=[i for i,x in enumerate(text) if x in 'aAiIuUfFxXeEoO']
    return tuple(2 if text[i] in 'AIUFXeEoO' or
                 (positions[k+1]-i-1 if k+1<len(positions) else len(text)-i-1)>=2 else 1
                 for k,i in enumerate(positions))


def make_task(members, split, construction, case, result=None, prompt_version='samasa-v1'):
    if len(members) not in {2,4} or case not in CASES:
        raise ValueError('Unsupported compound size or case')
    if len({m['root_family'] for m in members})!=len(members):
        raise ValueError('Participants must use distinct dhatu families')
    result = result or oracle_many([request(members,case)])[0]
    shapes = [{prosody(s) for s in detail['stems']} for detail in result['members']]
    # Equal syllable weights avoid ordering conflicts under 2.2.34; all are
    # consonant-final Satf stems, so ghi/ajadyadanta priority does not arise.
    if len(shapes)!=len(members) or any(len(shape)!=1 for shape in shapes) or any(shape!=shapes[0] for shape in shapes):
        raise ValueError('Compound constituent ordering has not been reviewed')
    gold=sorted(set(result['forms']))
    if not gold or len(gold)>64:
        raise ValueError('Empty or excessive compound variants')
    families=[m['root_family'] for m in members]
    identity=[members,case,'Pum','Dvi' if len(members)==2 else 'Bahu',ENGINE_REV]
    tid='samasa-'+c.digest(identity)[:24]
    task={'id':tid,'task_type':'samasa_creation','prompt_version':prompt_version,'members':members,
          'dhatu':{'members':[m['dhatu'] for m in members]},
          'derivation':{'prefixes':[],'sanadi':[],'order':'innermost_to_outermost','operations_vary_by_member':True},
          'morphology':{'samasa_type':'Dvandva','linga':'Pum','vibhakti':case,'vacana':identity[3]},
          'gold_slp1':gold,'gold_devanagari':[g.slp1_to_devanagari(x) for x in gold],
          'campaign':{'split':split,'root_family':'cohort-'+c.digest(sorted(families))[:24],
                      'root_families':families,'construction':f'samasa_{len(members)}_{construction}',
                      'base_construction':construction,'member_prosody':list(next(iter(shapes[0]))),
                      'member_stems':[d['stems'] for d in result['members']],
                      'vp_version':'Rust0.2.0@'+ENGINE_REV,'oracle':provenance(),
                      'selection_reason':'Score-independent sampling of equal-prosody participants; explicit coordinative semantics.'}}
    for form in gold:
        if g.transliterate(g.slp1_to_devanagari(form),g.Scheme.Devanagari,g.Scheme.Slp1)!=form:
            raise ValueError('Compound transliteration does not round trip')
    task['campaign']['prompt_sha256']=hashlib.sha256(RENDERERS[prompt_version](task).encode()).hexdigest()
    return task


def validate_task(task,split,allowed_families=None):
    assignments=io.read_json(c.HISTORY/'family-split.json')['families']
    entries={e.code:e for e in g.old.load_entries()}
    construction=task['campaign']['base_construction']
    for m in task['members']:
        expected=member(entries[m['dhatu']['code']],construction)
        if m!=expected or assignments[m['root_family']]['split']!=split:
            raise ValueError('Compound member identity or split mismatch')
        if allowed_families is not None and m['root_family'] not in allowed_families:
            raise ValueError('Compound member outside frozen allocation')
    expected=make_task(task['members'],split,construction,task['morphology']['vibhakti'],
                       prompt_version=task['prompt_version'])
    for key,value in expected.items():
        if key=='campaign':
            if any(task[key].get(k)!=v for k,v in value.items()):
                raise ValueError('Compound campaign metadata changed')
        elif task.get(key)!=value:
            raise ValueError('Compound regenerated data differs: '+key)


def generate(label, per_cell=16, seed=20261026):
    path=c.OUT/(label+'.json')
    if path.exists():
        raise ValueError('Compound panel already exists')
    assignments=io.read_json(c.HISTORY/'family-split.json')['families']
    entries={}
    for e in g.old.load_entries():
        family=g.old.family(e)
        if assignments[family]['split']=='development' and g.old.name(e.dhatu.gana)!='Curadi':
            entries.setdefault(family,e)
    rng=random.Random(seed);tasks=[];used=set()
    for construction in sorted(ALLOWED):
        candidates=[member(e,construction) for e in entries.values()]
        details=oracle_many([request([m],'Trtiya','members') for m in candidates])
        groups=defaultdict(list)
        for m,detail in zip(candidates,details):
            shapes={prosody(s) for s in detail['members'][0]['stems']}
            if len(shapes)==1:
                groups[next(iter(shapes))].append(m)
        for size in [2,4]:
            for i in range(per_cell):
                pools=[[m for m in group if m['root_family'] not in used] for group in groups.values()]
                pools=[pool for pool in pools if len(pool)>=size]
                if not pools:
                    raise ValueError('Insufficient disjoint equal-prosody cohorts')
                chosen=rng.sample(rng.choice(pools),size)
                task=make_task(chosen,'development',construction,rng.choice(list(CASES)))
                task['campaign']['panel']=label
                tasks.append(task);used.update(m['root_family'] for m in chosen)
    io.atomic_json(path,tasks)
    io.atomic_json(c.OUT/(label+'.sampling.json'),{'created_at':io.now(),'filename':path.name,'n':len(tasks),
       'seed':seed,'split':'development','root_families':len(used),'task_digest':c.digest(tasks),
       'oracle':provenance(),'selection':'Uniform feasible prosody-group draw,then uniform participant draw; no scores. Every dhatu family appears in at most one task in this development panel.'})
    return tasks
