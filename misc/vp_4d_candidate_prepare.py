"""Generate a source-filtered 1,250-question proposal; no provider or outcome reads."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import HISTORY,load_entries,family,name,identity,now,sha,write
from misc.vp_4d_pilot04 import COORDS,local_issue
from misc.vp_4d_pilot05 import short
from misc.vp_cartesian_task import make_task,validate_task,entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v1 import render

BASE=ROOT/'benchmarks/parallel-search-20261007/four_d-90'
OUT=BASE/'candidate-1250-source-filtered'
SEED='source-filtered-1250-20261007'
QUOTAS={'short_adanta_non_aorist':650,'other_adanta_aorist':100,'broad_non_curadi':500}


def rank(value):return hashlib.sha256((SEED+':'+value).encode()).hexdigest()


def main():
    if (OUT/'tasks.json').exists():raise RuntimeError('Preserve existing proposal; create a new version for changes')
    rows=json.loads((BASE/'scale-candidate-1250-metadata.json').read_text())
    holds=json.loads((BASE/'test-source-hold-predeclaration.json').read_text())
    assignments=json.loads((HISTORY/'family-split.json').read_text())['families']
    entries={e.code:e for e in load_entries()}
    input_paths=sorted((ROOT/'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json'))
    legacy=[ROOT/'benchmarks/full-tasks.json',*sorted(HISTORY.glob('discovery-??.json'))]
    seen=set();registered_families=set()
    for path in input_paths+legacy:
        for outer in json.loads(path.read_text()):
            for task in outer.get('forms',[outer]):
                if 'dhatu' not in task:continue
                if path in input_paths:
                    registered_families.add(task.get('campaign',{}).get('root_family') or
                                            task['dhatu']['aupadeshika']+'|'+task['dhatu']['gana'])
                if (set(task.get('morphology',{}))==set(COORDS) and
                    not task.get('derivation',{}).get('sanadi') and
                    not task.get('derivation',{}).get('prefixes')):seen.add(identity(task))

    def held(row):
        return any(row['code']==p['code'] and p['lakara'] in {'all',row['lakara']} for p in holds['predicates'])

    removed=[row for row in rows if held(row)]
    assert {row['id'] for row in removed}==set(holds['affected_proposed_ids'])
    chosen=[row for row in rows if not held(row)]
    assert all(row['cell']=='other_adanta_aorist' for row in removed)
    occupied={row['id'] for row in chosen}
    replacements=[]
    for e in entries.values():
        if (assignments[family(e)]['split']!='test' or name(e.dhatu.gana)!='Curadi' or
            not e.dhatu.aupadeshika.endswith('a') or short(e) or entry_scope_issue(e)):
            continue
        for pu in ['Prathama','Madhyama','Uttama']:
            for va in ['Eka','Dvi','Bahu']:
                m=dict(lakara='Lun',prayoga='Kartari',purusha=pu,vacana=va)
                row=dict(code=e.code,cell='other_adanta_aorist',family=family(e),**m)
                if held(row) or family(e) in registered_families:continue
                task=make_task(e,'test',m)
                if (not task or oracle_issue(task) or local_issue(task) or
                    identity(task) in seen or task['id'] in occupied):continue
                row.update(id=task['id'],gana='Curadi',split='test')
                replacements.append(row)
    loads=Counter(row['family'] for row in chosen if row['cell']=='other_adanta_aorist')
    persons=Counter(row['purusha'] for row in chosen if row['cell']=='other_adanta_aorist')
    numbers=Counter(row['vacana'] for row in chosen if row['cell']=='other_adanta_aorist')
    added=[]
    for _ in removed:
        row=min(replacements,key=lambda x:(loads[x['family']],persons[x['purusha']]+numbers[x['vacana']],rank(x['id'])))
        replacements.remove(row);added.append(row);chosen.append(row)
        loads[row['family']]+=1;persons[row['purusha']]+=1;numbers[row['vacana']]+=1
    assert len(chosen)==1250 and Counter(row['cell'] for row in chosen)==QUOTAS
    tasks=[]
    for row in chosen:
        e=entries[row['code']]
        task=make_task(e,'test',{k:row[k] for k in COORDS})
        validate_task(task,e,'test')
        assert task['id']==row['id'] and not entry_scope_issue(e) and not oracle_issue(task) and not local_issue(task)
        assert assignments[family(e)]['split']=='test' and family(e) not in registered_families
        assert not held(row) and identity(task) not in seen
        task['campaign'].update(panel='source-filtered-1250-proposal',seed=SEED,
            sampling_cell={'label':row['cell'],'n':QUOTAS[row['cell']]},
            selection={'method':'Preserve prior1250 metadata except uniform pre-outcome source holds; balance replacement families/person/number, then input-hash order.'})
        tasks.append(task)
    tasks.sort(key=lambda t:rank('order:'+t['id']))
    assert len({identity(t) for t in tasks})==len({render(t) for t in tasks})==len({t['id'] for t in tasks})==1250
    assert all(t['task_type']=='cartesian_4d' and set(t['morphology'])==set(COORDS) and 'derivation' not in t for t in tasks)
    write(OUT/'tasks.json',tasks)
    prompts=[{'id':t['id'],'prompt':render(t)} for t in tasks]
    write(OUT/'public-prompts.json',prompts)
    write(OUT/'replacement-audit.json',{'created_at':now(),'removed':removed,'added':added,
        'all_other_question_ids_preserved':True,'source_hold_predicates':holds['predicates'],
        'test_model_answers_read':False,'old_proposal_unchanged':True})
    counts={k:dict(Counter(t['morphology'][k] for t in tasks)) for k in COORDS}
    counts['gana']=dict(Counter(t['dhatu']['gana'] for t in tasks))
    family_load=Counter(t['campaign']['root_family'] for t in tasks)
    dependencies=[Path(__file__),ROOT/'misc/vp_cartesian_task.py',ROOT/'misc/vp_cartesian_prompt_v1.py',
        ROOT/'misc/vp_4d_pilot04.py',ROOT/'misc/vp_4d_pilot05.py',HISTORY/'family-split.json',
        BASE/'scale-candidate-1250-metadata.json',BASE/'test-source-hold-predeclaration.json']
    write(OUT/'manifest.json',{'created_at':now(),'status':'unscored_proposal_not_registered_for_evaluation',
        'n':1250,'families':len(family_load),'max_questions_per_family':max(family_load.values()),
        'composition':QUOTAS,'distribution':counts,'source_held_questions_replaced':len(removed),
        'source_held_codes':sorted({row['code'] for row in removed}),
        'tasks_sha256':sha(OUT/'tasks.json'),'public_prompts_sha256':sha(OUT/'public-prompts.json'),
        'mechanical_validation':{'regenerated':1250,'unique_questions_and_prompts':1250,
            'source_hold_violations':0,'current_registered_family_overlap':0,'prior_tuple_overlap':0,
            'original_four_coordinates':True,'added_operations_prefixes_or_selected_pada':False,
            'full_answer_unions_preserved':True},
        'exposure_limit':'Legacy analysis inspected all dictionary families before master split. Fresh tuple and current-campaign family disjointness do not establish never-inspected families.',
        'unresolved_before_final_freeze':['Strongest-reference same-panel development comparison pending',
            'Family-generalization SE below1pp unsupported by this small hard-family population',
            'Final question/variant source review incomplete;10.0108 classification and10.0481 edition clarification remain explicit',
            'Uses future test reserve families; release allocation and spending plan not registered'],
        'precision':'1,250 independent observations would have0.935pp SE at87.5%; that assumption does not establish family-generalization precision.',
        'selection_rationale':'Grammar-defined52/8/40 mixture motivated by development evidence, with prospective uniform source exclusions. No test outcome-based task selection.',
        'inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in input_paths+legacy],
        'dependencies':{str(p.relative_to(ROOT)):sha(p) for p in dependencies},
        'paid_calls':0,'split_changes':False,'test_model_answers_read':False,'benchmark_ready':False})
    print(json.dumps({'n':len(tasks),'families':len(family_load),'replacement_count':len(removed),'distribution':counts}))


if __name__=='__main__':main()
