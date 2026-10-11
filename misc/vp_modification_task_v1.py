"""Input-only inverse dictionary audit and strict modification validation."""
from functools import lru_cache
from pathlib import Path
from collections import defaultdict
import hashlib,json,re
from misc.vp_cartesian_task import make_task,entries_by_code,entry_scope_issue,oracle_issue,COORDINATES,GRAMMAR,Pada,Lakara,Prayoga,Purusha,Vacana
from finetune.prompts import slp1_to_devanagari
from misc.vp_campaign_candidates import family
from misc.vp_modification_prompt_v1 import render
ROOT=Path(__file__).resolve().parents[1]
POLICY=ROOT/'benchmarks/parallel-search-20261006/oracle-policy-21.json'
DICT=ROOT/'data/finetune/task-data/vidyut_dhatupatha_5.tsv'
SPLIT=ROOT/'benchmarks/creation-campaign-20261006/family-split.json'
UNRESOLVED={'04.0137','10.0023'}
SPELLING=re.compile('[aAiIuUfFxXeEoO]rC')
FIELDS=('lakara','prayoga','purusha','vacana')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def signature(m):return tuple(m[k] for k in FIELDS)
def public_key(form,m):return json.dumps([form,*signature(m)],ensure_ascii=False,separators=(',',':'))
@lru_cache(maxsize=1)
def assignments():return json.loads(SPLIT.read_text())['families']
@lru_cache(maxsize=1)
def inventory():
    return {c:e for c,e in entries_by_code().items() if not entry_scope_issue(e) and c not in UNRESOLVED}
@lru_cache(maxsize=None)
def ordinary(code,morph):
    e=inventory().get(code)
    if e is None:return None
    t=make_task(e,assignments()[family(e)]['split'],dict(zip(FIELDS,morph)),prompt_version='cartesian-4d-v3-sanskrit')
    if not t or oracle_issue(t) or any(SPELLING.search(x) for x in t['gold_slp1']):return None
    return t
@lru_cache(maxsize=None)
def inverse(morph):
    result=defaultdict(list)
    for code in inventory():
        task=ordinary(code,morph)
        if task:
            for word in task['gold_devanagari']:result[word].append(code)
    return {word:sorted(codes) for word,codes in result.items()}
@lru_cache(maxsize=None)
def shadow_inverse(morph):
    """Do not manufacture uniqueness by deleting excluded dictionary analyses."""
    result=defaultdict(list)
    enums=[Lakara,Prayoga,Purusha,Vacana]
    fields={k:getattr(enum,value) for k,enum,value in zip(FIELDS,enums,morph)}
    for code,e in entries_by_code().items():
        paths=GRAMMAR.derive(Pada.Tinanta(dhatu=e.dhatu,**fields))
        for form in {slp1_to_devanagari(p.text) for p in paths}:
            result[form].append(code)
    return {word:sorted(codes) for word,codes in result.items()}
def analyses(word,source):return inverse(signature(source)).get(word,[])
def task_id(public):
    raw=json.dumps(public,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    return 'modify-'+hashlib.sha256(raw.encode()).hexdigest()[:24]
def validate_task(task,split,allowed_families=None):
    if task['task_type']!='modification' or task['prompt_version']!='modification-v1':raise ValueError('Wrong modification schema')
    source=task['source_morphology'];target=task['target_morphology'];word=task['source_form_devanagari']
    if set(source)!=COORDINATES or set(target)!=COORDINATES:raise ValueError('Exactly four source and target coordinates')
    if source['lakara']==target['lakara'] or any(source[k]!=target[k] for k in FIELDS[1:]):raise ValueError('Only lakara must change')
    evidence=task['modification_audit']
    for path,value in evidence['dependencies'].items():
        if sha(ROOT/path)!=value:raise ValueError('Modification audit dependency changed: '+path)
    codes=analyses(word,source)
    if shadow_inverse(signature(source)).get(word,[])!=codes:raise ValueError('Excluded or uncertain colliding source analysis')
    if not codes or codes!=evidence['candidate_codes']:raise ValueError('Inverse dictionary candidates changed')
    fams={family(inventory()[c]) for c in codes}
    if len(fams)!=1 or fams!={task['campaign']['root_family']}:raise ValueError('Public source key has ambiguous families')
    if task['campaign']['split']!=split or any(assignments()[f]['split']!=split for f in fams):raise ValueError('Root-family split violation')
    if allowed_families is not None and not fams<=set(allowed_families):raise ValueError('Family not allowed')
    targets=[ordinary(c,signature(target)) for c in codes]
    if any(t is None for t in targets):raise ValueError('An inverse analysis has an uncertified target')
    unions={tuple(t['gold_slp1']) for t in targets}
    if len(unions)!=1:raise ValueError('Inverse analyses disagree on full target union')
    origin=next((t for t in targets if t['dhatu']==task['dhatu']),None)
    if origin is None or task['morphology']!=target:raise ValueError('Private target provenance changed')
    for k in ['gold_slp1','gold_devanagari']:
        if task[k]!=origin[k]:raise ValueError('Full target union changed')
    if word in task['gold_devanagari']:raise ValueError('Surface identity-copy question')
    public={k:task[k] for k in ['source_form_devanagari','source_morphology','target_morphology']}
    if task['id']!=task_id(public):raise ValueError('Public task identity changed')
    if hashlib.sha256(render(task).encode()).hexdigest()!=task['campaign']['prompt_sha256']:raise ValueError('Public prompt changed')
    if evidence['source_key']!=public_key(word,source):raise ValueError('Collision key changed')
    return True
