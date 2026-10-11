"""Source-restricted unadi exploration. No automatic model calls."""
import hashlib
import json
import subprocess
from pathlib import Path
from misc import vp_goal as c, vp_compositional as g, oai_batch_eval as io
from misc.vp_unadi_prompt_v1 import render

REV = '8da2f90bee3ce1c07505fa432fc3729e3f7e02ea'
BINARY = Path('/tmp/vp-samasa-oracle-target/debug/vp-unadi-oracle')


def derive(case):
    request = {k: case[k] for k in ['code','dhatu','gana','antargana','unadi']}
    result = subprocess.run([str(BINARY)], input=json.dumps(request)+'\n',
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise ValueError('Unadi oracle failed')
    rows = json.loads(result.stdout)['candidates']
    if len(rows) != 1:
        raise ValueError('Expected one supported unadi suffix')
    return rows[0]


def make_task(case, prompt_version='unadi-v1'):
    entry = {e.code:e for e in g.old.load_entries()}[case['code']]
    identity = [g.old.family(entry),case['unadi'],REV]
    result = derive(case)
    if result['stems'] != case['expected']:
        raise ValueError('Unadi differs from source example')
    if (entry.dhatu.aupadeshika != case['dhatu'] or g.old.name(entry.dhatu.gana) != case['gana']
        or (g.old.name(entry.dhatu.antargana) if entry.dhatu.antargana else None) != case['antargana']):
        raise ValueError('Unadi dhatu identity differs')
    task = {'id':'unadi-'+c.digest(identity)[:24], 'task_type':'unadi_creation',
            'prompt_version':prompt_version,
            'dhatu':{'code':entry.code,'aupadeshika':entry.dhatu.aupadeshika,
                     'gana':g.old.name(entry.dhatu.gana),'artha':entry.artha},
            'derivation':{'prefixes':[],'sanadi':[],'order':'innermost_to_outermost'},
            'morphology':{'unadi':case['unadi'],'unadi_aupadeshika':result['aupadeshika'],
                          'level':'pratipadika'},
            'gold_slp1':result['stems'],
            'gold_devanagari':[g.slp1_to_devanagari(x) for x in result['stems']],
            'campaign':{'root_family':g.old.family(entry),'split':'development',
                        'construction':'unadi_nominal_stem','source_example':case,
                        'vp_version':'Rust0.2.0@'+REV,
                        'oracle_source_sha256':io.sha256(c.ROOT/'misc/vp_unadi_oracle/src/main.rs'),
                        'oracle_lock_sha256':io.sha256(c.ROOT/'misc/vp_unadi_oracle/Cargo.lock'),
                        'oracle_binary_sha256':io.sha256(BINARY),
                        'selection_reason':'Documented unprefixed unadi stem example; not an unrestricted root/affix product.'}}
    for slp,deva in zip(task['gold_slp1'],task['gold_devanagari']):
        if g.transliterate(deva,g.Scheme.Devanagari,g.Scheme.Slp1) != slp:
            raise ValueError('Unadi transliteration mismatch')
    renderer = render
    if prompt_version == 'unadi-v2-sanskrit':
        from misc.vp_sanskrit_prompt_v1 import render as renderer
    elif prompt_version != 'unadi-v1':
        raise ValueError('Unknown unadi prompt')
    task['campaign']['prompt_sha256'] = hashlib.sha256(renderer(task).encode()).hexdigest()
    return task


def validate_task(task, split):
    if split != 'development':
        raise ValueError('Unadi release/train scope has not been reviewed')
    case = task['campaign']['source_example']
    whitelist = io.read_json(c.OUT/'unadi-source-check-01.json')['matches']
    if case not in whitelist:
        raise ValueError('Unadi outside documented source examples')
    expected = make_task(case, task['prompt_version'])
    for key,value in expected.items():
        if key == 'campaign':
            if any(task[key].get(k)!=v for k,v in value.items()):
                raise ValueError('Unadi metadata differs')
        elif task.get(key)!=value:
            raise ValueError('Unadi regenerated task differs: '+key)
