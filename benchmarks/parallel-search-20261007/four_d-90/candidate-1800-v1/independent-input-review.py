"""Independent additive input review; never opens model-response files."""
from pathlib import Path
from collections import Counter
import copy, datetime, hashlib, json, sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=Path(__file__).resolve().parent;BASE=OUT.parent
from misc.vp_4d_pilot import load_entries, family, HISTORY
from misc.vp_cartesian_task import validate_task, entry_scope_issue, oracle_issue
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_4d_pilot04 import COORDS,LAS,LOCAL_CODES,local_issue
from finetune.prompts import slp1_to_devanagari

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def fam(t):return t['dhatu']['aupadeshika']+'|'+t['dhatu']['gana']
def key(t):return (t['dhatu']['aupadeshika'],t['dhatu']['gana'],*(t['morphology'][k] for k in COORDS))
def main():
    frozen=[p for p in OUT.rglob('*') if p.is_file() and not p.name.startswith('independent-') and '__pycache__' not in str(p)]
    before={str(p.relative_to(ROOT)):sha(p) for p in frozen}
    ts=read(OUT/'tasks.json');pp=read(OUT/'public-prompts.json');m=read(OUT/'manifest.json');pol=read(OUT/'source-policy.json');old=read(BASE/'candidate-1250-v2/tasks.json')
    for name in ['tasks','public-prompts','source-policy','membership-audit','supply']:
        assert sha(OUT/(name+'.json'))==m[name.replace('-','_')+'_sha256']
    for rel,h in m['dependencies'].items():assert sha(ROOT/rel)==h,rel
    paths=sorted((ROOT/'benchmarks/iterative-goal-20261006/jobs').glob('*/tasks.json'))+sorted((HISTORY/'jobs').glob('*/tasks.json'))+[ROOT/'benchmarks/full-tasks.json',*sorted(HISTORY.glob('discovery-??.json'))]
    assert {str(p.relative_to(ROOT)):sha(p) for p in paths}==m['inputs']
    assert (OUT/'source-policy.json').read_bytes()==(BASE/'candidate-1250-v2/source-policy.json').read_bytes()
    assert pol['previous_holds']==read(BASE/'test-source-hold-predeclaration.json')
    assert pol['clarification_sha256']==sha(BASE/'reading-clarification.json')
    es={e.code:e for e in load_entries()};assign=read(HISTORY/'family-split.json')['families']
    prior=set();registered=set();rows=0
    for p in paths:
        for outer in read(p):
            for t in outer.get('forms',[outer]):
                rows+=1;d=t.get('dhatu',{});op=t.get('derivation',{})
                if '/jobs/' in str(p):
                    if 'aupadeshika' in d:registered.add(fam(t))
                    registered.update(x['aupadeshika']+'|'+x['gana'] for x in d.get('members',[]));registered.update(t.get('campaign',{}).get('root_families',[]))
                if 'aupadeshika' in d and set(t.get('morphology',{}))==set(COORDS) and not any(op.get(k) for k in ('sanadi','prefixes','pada')) and not d.get('pada'):prior.add(key(t))
    assert len(ts)==len(pp)==len({t['id'] for t in ts})==len({key(t) for t in ts})==len({p['prompt'] for p in pp})==1800
    tm={t['id']:t for t in ts};assert all(tm[t['id']]==t for t in old)
    oldids={t['id'] for t in old};added=[t for t in ts if t['id'] not in oldids]
    predicates=pol['previous_holds']['predicates']+[pol['additional_exclusion']]
    for t,p in zip(ts,pp):
        e=es[t['dhatu']['code']];validate_task(t,e,'test')
        assert not entry_scope_issue(e) and not oracle_issue(t) and not local_issue(t) and e.code not in LOCAL_CODES
        assert t['task_type']=='cartesian_4d' and t['prompt_version']=='cartesian-4d-v1' and set(t['morphology'])==set(COORDS) and 'derivation' not in t
        assert t['morphology']['prayoga']=='Kartari' and assign[fam(t)]['split']=='test' and t['campaign']['split']=='test'
        assert fam(t) not in registered and key(t) not in prior
        cell=t['campaign']['sampling_cell']['label'];a=t['dhatu']['aupadeshika'];g=t['dhatu']['gana'];la=t['morphology']['lakara']
        is_short=g=='Curadi' and a.endswith('a') and len(a[:-1])>1 and a[-3] in 'aiufx' and a[-2] not in 'aAiIuUfFxXeEoO'
        assert (cell=='short_adanta_non_aorist' and is_short and la!='Lun') or (cell=='other_adanta_aorist' and g=='Curadi' and a.endswith('a') and not is_short and la=='Lun') or (cell=='broad_non_curadi' and g!='Curadi')
        assert not any(t['dhatu']['code']==h['code'] and h['lakara'] in ('all',la) and ('sampling_cell' not in h or h['sampling_cell']==cell) for h in predicates)
        assert p=={'id':t['id'],'prompt':render(t)} and hashlib.sha256(p['prompt'].encode()).hexdigest()==t['campaign']['prompt_sha256']
        altered=copy.deepcopy(t);altered['gold_slp1']=['PRIVATE'];altered['gold_devanagari']=['PRIVATE'];altered['campaign']={'private':'PRIVATE'};altered['dhatu']['code']='PRIVATE';altered['aliases_devanagari']=['PRIVATE']
        assert render(altered)==p['prompt']
    fc=Counter(fam(t) for t in ts);composition=Counter(t['campaign']['sampling_cell']['label'] for t in ts)
    assert dict(composition)==m['composition']=={'short_adanta_non_aorist':936,'other_adanta_aorist':144,'broad_non_curadi':720}
    assert len(fc)==m['families']==755 and max(fc.values())==m['max_questions_per_family']==67
    assert {str(k):v for k,v in Counter(fc.values()).items()}==m['family_size_histogram']
    dist={k:dict(Counter(t['morphology'][k] for t in ts)) for k in COORDS};dist['gana']=dict(Counter(t['dhatu']['gana'] for t in ts));assert dist==m['distribution']
    percell={}
    for c,n in composition.items():
        sub=[t for t in ts if t['campaign']['sampling_cell']['label']==c];cf=Counter(fam(t) for t in sub)
        assert set(Counter(t['morphology']['purusha'] for t in sub).values())=={n//3} and set(Counter(t['morphology']['vacana'] for t in sub).values())=={n//3}
        expectedlas=([x for x in LAS if x!='Lun'] if c=='short_adanta_non_aorist' else ['Lun'] if c=='other_adanta_aorist' else LAS)
        assert dict(Counter(t['morphology']['lakara'] for t in sub))=={la:n//len(expectedlas) for la in expectedlas}
        assert set(cf)=={fam(t) for t in old if t['campaign']['sampling_cell']['label']==c} if c!='broad_non_curadi' else len(cf)==720
        percell[c]={'n':n,'families':len(cf),'family_loads':dict(Counter(cf.values()))}
    rl=read(BASE/'rl-supply/strict-citation-option/training-inventory-metadata.json')
    assert not set(fc)&{r['family'] for r in rl}
    assert not {t['dhatu']['aupadeshika'] for t in ts}&{r['aupadeshika'] for r in rl}
    assert not {slp1_to_devanagari(t['dhatu']['aupadeshika']) for t in ts}&{slp1_to_devanagari(r['aupadeshika']) for r in rl}
    assert not {key(t) for t in ts}&{(r['aupadeshika'],r['gana'],*(r[k] for k in COORDS)) for r in rl}
    assert not {t['campaign']['prompt_sha256'] for t in ts}&{r['prompt_sha256'] for r in rl}
    assert before=={p:sha(ROOT/p) for p in before}
    out=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=True,mechanical_review_passed=True,blockers=[],tasks_sha256=sha(OUT/'tasks.json'),manifest_sha256=sha(OUT/'manifest.json'),public_prompts_sha256=sha(OUT/'public-prompts.json'),source_policy_sha256=sha(OUT/'source-policy.json'),n=1800,all1800_full_canonical_regeneration=True,exact1250_full_objects_retained=True,added_objects=len(added),added_by_cell=dict(Counter(t['campaign']['sampling_cell']['label'] for t in added)),added_by_class=dict(Counter(t['dhatu']['gana'] for t in added)),families=len(fc),family_size_histogram=dict(Counter(fc.values())),cell_counts=percell,distribution=dist,all_public_prompts_exact_and_private_fields_isolated=True,history={'files':len(paths),'records':rows,'ordinary_unique_tuples':len(prior),'registered_families':len(registered),'tuple_overlap':0,'registered_family_overlap':0,'all_file_hashes_match':True},strict_rl={'rows':len(rl),'families':len({r['family'] for r in rl}),'family_raw_citation_rendered_citation_tuple_prompt_overlaps':0},scope='Independent mechanical/source-policy consistency review; not complete philological certification.',limitations=['The 52% hard component uses only14 families, each66–67 times; independent-family sub1pp precision is not established.','All220 additional broad families are Bhvadi; all10 classes are retained, not newly expanded.','Earlier legacy analysis inspected the dictionary before master split; no never-inspected lexical-root claim.','Source exclusions and finite accepted spelling rules remain bounded; every usable unrecognized answer requires independent source adjudication before linguistic errors or advancement.','Old task campaign sampling_cell.n values preserve old provenance; current manifest declares aggregate936/144/720.'],generator_read_only_review=True,allocation_reoptimization_performed=False,protected_files_unchanged=True,protected_hashes=before,reviewer_script_sha256=sha(Path(__file__)),model_outputs_read=False,paid_calls=0,benchmark_ready=False,evaluation_authorized=False)
    (OUT/'independent-input-review.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:out[k] for k in ['passed','n','families','added_by_cell','added_by_class','history','strict_rl']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
