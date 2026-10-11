"""Offline split-assets proof; no generation, training, registry or ledger writes."""
import hashlib,json
from pathlib import Path
from misc.vp_goal_dataset import export
from misc.vp_goal_validate import RENDERERS,validate
COORDS={'lakara','prayoga','purusha','vacana'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path):return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
def write_rows(path,values):Path(path).write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in values))
def public_input(task,menu):
    if set(task['morphology'])!=COORDS:raise ValueError('Exactly four inflection coordinates')
    result={'dhatu':{k:task['dhatu'][k] for k in ['aupadeshika','gana','artha']},'morphology':task['morphology']}
    if task['task_type']=='cartesian_5d':
        d=task['derivation'];recipe=d['recipe_id']
        if recipe not in menu or d['sanadi']!=menu[recipe]:raise ValueError('Outside the exact finite recipe menu')
        if d['prefixes'] or d['order']!='innermost_to_outermost':raise ValueError('Hidden prefix or changed order')
        result['sanadi_recipe']=recipe
    elif task['task_type']!='cartesian_4d' or 'derivation' in task:raise ValueError('Only ordinary 4D or menu 5D')
    return result

def package(source,output,menu,split='development'):
    output=Path(output)
    if output.exists():raise ValueError('Preserve versioned exports')
    tasks=json.loads(Path(source).read_text());validate(tasks,split)
    for task in tasks:public_input(task,menu)
    (output/'private').mkdir(parents=True)
    # Retain current exporter as the explicit baseline, under the private tree.
    export(Path(source),output/'private/combined-baseline.jsonl',split)
    combined=rows(output/'private/combined-baseline.jsonl')
    public=[{'id':r['id'],'input':public_input(r['task'],menu),'prompt':r['prompt'],'messages':r['messages']} for r in combined]
    keys=[{'id':r['id'],'gold_devanagari':r['gold_devanagari']} for r in combined]
    audit=[{'id':r['id'],'task':r['task']} for r in combined]
    write_rows(output/'prompts.jsonl',public);write_rows(output/'private/answer-key.jsonl',keys);write_rows(output/'private/audit.jsonl',audit)
    (output/'recipe-menu.json').write_text(json.dumps(menu,ensure_ascii=False,indent=2)+'\n')
    names=['prompts.jsonl','recipe-menu.json','private/answer-key.jsonl','private/audit.jsonl']
    manifest={'schema':'cartesian-separated-assets-demo-v1','status':'development_only_contract_fixture','split':split,'n':len(tasks),'files':{n:sha(output/n) for n in names},'model_input':'messages only; prompt is its equivalent text','reward':'binary exact accepted-variant union; no thinking bonus','no_training':True,'not_final_membership':True}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def verified_records(manifest_path,expected_split):
    manifest_path=Path(manifest_path);directory=manifest_path.parent;manifest=json.loads(manifest_path.read_text())
    if manifest['split']!=expected_split:raise ValueError('Export split differs from requested use')
    for name,value in manifest['files'].items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path)!=value:raise ValueError('Bundle fingerprint changed')
    public=rows(directory/'prompts.jsonl');keys=rows(directory/'private/answer-key.jsonl');audit=rows(directory/'private/audit.jsonl')
    ids=[r['id'] for r in public]
    if len(ids)!=manifest['n'] or len(ids)!=len(set(ids)) or any([r['id'] for r in rr]!=ids for rr in [keys,audit]):raise ValueError('Exact ordered membership required')
    tasks=[r['task'] for r in audit];validate(tasks,expected_split)
    menu=json.loads((directory/'recipe-menu.json').read_text())
    for pub,key,task in zip(public,keys,tasks):
        prompt=RENDERERS[task['prompt_version']](task)
        if pub!={'id':task['id'],'input':public_input(task,menu),'prompt':prompt,'messages':[{'role':'user','content':prompt}]}:raise ValueError('Public input changed or private fields leaked')
        if key!={'id':task['id'],'gold_devanagari':task['gold_devanagari']}:raise ValueError('Full accepted union changed')
    return public,keys
