"""Independent offline export audit; no provider, training or final-answer access."""
from pathlib import Path
from collections import Counter
import copy,datetime,hashlib,json,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT));OUT=Path(__file__).resolve().parent;BASE=OUT.parents[2]
from misc.vp_cartesian_task import entries_by_code,validate_task,entry_scope_issue,oracle_issue
from misc.vp_cartesian_prompt_v1 import render
from misc.vp_4d_pilot04 import COORDS,local_issue
from finetune.prompts import slp1_to_devanagari

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(t):return (t['dhatu']['aupadeshika'],t['dhatu']['gana'],*(t['morphology'][k] for k in COORDS))
def family(t):return t['dhatu']['aupadeshika']+'|'+t['dhatu']['gana']
def main():
    plan=read(BASE/'final1800-64k-01/execution-plan.json');protected=plan['dependencies']
    assert len(protected)==44 and all(sha(ROOT/p)==h for p,h in protected.items())
    preserved={str(p.relative_to(ROOT)):sha(p) for p in OUT.rglob('*') if p.is_file() and not p.name.startswith('independent-') and '__pycache__' not in str(p)}
    m=read(OUT/'manifest.json')
    for n,h in m['files'].items():assert sha(OUT/n)==h,n
    for group in ['dependencies','inherited_source_dependencies']:
        for p,h in m[group].items():assert sha(ROOT/p)==h,p
    ts=read(OUT/'tasks.json');metadata=read(OUT/'curriculum-metadata.json');pp=read(OUT/'public-prompts.json')
    public=[json.loads(x) for x in (OUT/'public-tasks.jsonl').read_text().splitlines()];gold=[json.loads(x) for x in (OUT/'canonical-gold.jsonl').read_text().splitlines()]
    inventory={r['id']:r for r in read(OUT.parent/'training-inventory-metadata.json')}
    assert (OUT/'curriculum-metadata.json').read_bytes()==(OUT.parent/'curriculum-1400-metadata.json').read_bytes()
    assert (OUT/'source-policy.json').read_bytes()==(BASE/'candidate-1800-v1/source-policy.json').read_bytes()
    assert len(ts)==len(metadata)==len(pp)==len(public)==len(gold)==len({t['id'] for t in ts})==len({key(t) for t in ts})==1400
    master=read(ROOT/'benchmarks/creation-campaign-20261006/family-split.json')['families'];es=entries_by_code()
    blocked={f.rsplit('|',1)[0] for f,v in master.items() if v['split'] in ('test','development')};blocked_deva={slp1_to_devanagari(x) for x in blocked}
    pol=read(OUT/'source-policy.json');holds=pol['previous_holds']['predicates']+[pol['additional_exclusion']]
    def check_no_reward_fields(obj):
        if isinstance(obj,dict):
            assert not any(k.startswith('gold') or k.startswith('trace') or k in {'campaign','aliases_devanagari','aliases_slp1','canonical_gold_variants','canonical_gold_slp1_sha256'} for k in obj)
            for x in obj.values():check_no_reward_fields(x)
        elif isinstance(obj,list):
            for x in obj:check_no_reward_fields(x)
    for i,(t,r,p,g,q) in enumerate(zip(ts,metadata,public,gold,pp)):
        assert t['id']==r['id']==p['id']==g['id']==q['id']
        assert {k:v for k,v in r.items() if k not in {'position','block'}}==inventory[r['id']]
        assert r['position']==p['position']==g['position']==q['position']==i and r['block']==p['block']==q['block']==i//25
        e=es[r['code']];validate_task(t,e,'rl_train')
        assert not entry_scope_issue(e) and not oracle_issue(t) and not local_issue(t)
        assert t['campaign']['split']==r['split']==master[family(t)]['split']=='rl_train'
        assert t['campaign']['root_family']==r['family']==family(t)
        assert t['task_type']=='cartesian_4d' and t['prompt_version']=='cartesian-4d-v1' and 'derivation' not in t and set(t['morphology'])==set(COORDS)
        assert t['morphology']['prayoga']=='Kartari' and not any(k in t['dhatu'] for k in ['pada','prefixes','sanadi'])
        assert t['dhatu']['aupadeshika'] not in blocked and slp1_to_devanagari(t['dhatu']['aupadeshika']) not in blocked_deva
        assert not any(r['code']==h['code'] and h['lakara'] in ('all',r['lakara']) and ('sampling_cell' not in h or h['sampling_cell']==r['cell']) for h in holds)
        assert t['gold_slp1']==g['gold_slp1'] and t['gold_devanagari']==g['gold_devanagari']==[slp1_to_devanagari(s) for s in t['gold_slp1']]
        assert digest(t['gold_slp1'])==g['canonical_gold_slp1_sha256']==r['canonical_gold_slp1_sha256']
        assert len(t['gold_slp1'])==g['canonical_gold_variants']==r['canonical_gold_variants']
        assert set(p)=={'id','position','block','split','task_type','prompt_version','dhatu','morphology','prompt'}
        check_no_reward_fields(p);assert p['dhatu']==t['dhatu'] and p['morphology']==t['morphology']
        assert p['prompt']==q['prompt']==render(t) and hashlib.sha256(p['prompt'].encode()).hexdigest()==r['prompt_sha256']==t['campaign']['prompt_sha256']
        private=copy.deepcopy(t);private.update(gold_slp1=['PRIVATE'],gold_devanagari=['PRIVATE'],campaign={'private':'PRIVATE'},aliases_devanagari=['PRIVATE']);private['dhatu']['code']='PRIVATE'
        assert render(private)==p['prompt']
    components=Counter(r['cell'] for r in metadata);assert dict(components)==m['component_counts']=={'short_adanta_non_aorist':728,'other_adanta_aorist':112,'broad_non_curadi':560}
    for b in range(56):assert Counter(r['cell'] for r in metadata[b*25:(b+1)*25])=={'short_adanta_non_aorist':13,'other_adanta_aorist':2,'broad_non_curadi':10}
    final=read(BASE/'candidate-1800-v1/tasks.json');finalpp=read(BASE/'candidate-1800-v1/public-prompts.json')
    overlap={'family':len({family(t) for t in ts}&{family(t) for t in final}),'raw_citation':len({t['dhatu']['aupadeshika'] for t in ts}&{t['dhatu']['aupadeshika'] for t in final}),'rendered_citation':len({slp1_to_devanagari(t['dhatu']['aupadeshika']) for t in ts}&{slp1_to_devanagari(t['dhatu']['aupadeshika']) for t in final}),'tuple':len({key(t) for t in ts}&{key(t) for t in final}),'prompt':len({p['prompt'] for p in public}&{p['prompt'] for p in finalpp})}
    assert not any(overlap.values());assert len({p['prompt'] for p in public})==1400
    assert all(sha(ROOT/p)==h for p,h in protected.items()) and all(sha(ROOT/p)==h for p,h in preserved.items())
    assert not (OUT/'scoring-adoption.json').exists() and not (OUT/'spelling-policy-proposal/scoring-adoption.json').exists()
    fc=Counter(family(t) for t in ts)
    result={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'blockers':[],'scope':'Independent mechanical export, source-policy consistency and input-separation review; not exhaustive Sanskrit certification or training authorization.','n':1400,'families':len(fc),'tasks_sha256':sha(OUT/'tasks.json'),'manifest_sha256':sha(OUT/'manifest.json'),'public_tasks_sha256':sha(OUT/'public-tasks.jsonl'),'canonical_gold_sha256':sha(OUT/'canonical-gold.jsonl'),'curriculum_metadata_sha256':sha(OUT/'curriculum-metadata.json'),'source_policy_sha256':sha(OUT/'source-policy.json'),'all_ids_order_positions_and56_blocks_preserved':True,'all1400_canonical_unions_regenerated_and_metadata_hash_matched':True,'canonical_task_form_count':sum(len(t['gold_slp1']) for t in ts),'public_field_allowlist_and_recursive_no_gold_trace':True,'private_gold_campaign_alias_and_code_mutation_does_not_change_any_prompt':True,'all_master_rl_train':True,'all_master_dev_test_raw_and_rendered_citation_overlap':0,'final1800_input_overlap':overlap,'component_counts':dict(components),'component_families':{c:len({r['family'] for r in metadata if r['cell']==c}) for c in components},'max_family_load':max(fc.values()),'spelling_policy_adopted':False,'spelling_review_separate':True,'protected_paid_dependencies_unchanged':len(protected),'protected_hashes':protected,'export_files_unchanged':preserved,'script_sha256':sha(Path(__file__)),'limitations':['Give only the public record prompt to the learner; dictionary code and curriculum positions remain audit metadata, not extra model input.','Canonical reward must accept every union member; first-form-only matching is invalid.','The proposed finite alias scorer is not an autonomous binary RL reward for unknown usable outputs: its pending-source state needs explicit handling before training.','Nine hard training families and exact-citation disjointness do not establish broad semantic/stem or pretraining independence.'],'training_started':False,'paid_calls':0,'final_responses_read':False,'live_ledger_read_or_written':False}
    (OUT/'independent-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','n','families','canonical_task_form_count','component_counts','component_families','final1800_input_overlap','protected_paid_dependencies_unchanged']},indent=2))
if __name__=='__main__':main()
