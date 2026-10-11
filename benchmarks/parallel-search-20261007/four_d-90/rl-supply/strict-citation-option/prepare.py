"""Prospective stricter train-only metadata; original audit stays unchanged."""
import hashlib
import json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from misc.vp_cartesian_task import entries_by_code,make_task,validate_task,oracle_issue
from misc.vp_campaign_candidates import family
from misc.vp_4d_pilot04 import LAS,COORDS,local_issue

ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;BASE=OUT.parent
SEED='rl-52-8-40-supply-20261007-v1'
CELLS=['short_adanta_non_aorist','other_adanta_aorist','broad_non_curadi']
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
rank=lambda x:hashlib.sha256((SEED+':'+str(x)).encode()).hexdigest()
def save(n,o):(OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def stats(rs):
    fc=Counter(r['family'] for r in rs)
    return dict(public_tuples=len(rs),families=len(fc),distinct_family_coordinates=len({(r['family'],*(r[k] for k in COORDS)) for r in rs}),
        family_capacity=dict(sorted(fc.items())),class_counts=dict(Counter(r['gana'] for r in rs)),
        families_by_class=dict(Counter({r['family']:r['gana'] for r in rs}.values())),
        tense_counts=dict(Counter(r['lakara'] for r in rs)),person_counts=dict(Counter(r['purusha'] for r in rs)),number_counts=dict(Counter(r['vacana'] for r in rs)))

original_paths=[BASE/n for n in ['training-inventory-metadata.json','curriculum-1400-metadata.json',
    'curriculum-manifest.json','supply-audit.json','audit_supply.py','verification-receipt.json','README.md']]
original_hashes={str(p.relative_to(ROOT)):sha(p) for p in original_paths}
master_path=ROOT/'benchmarks/creation-campaign-20261006/family-split.json'
master_hash=sha(master_path);master=read(master_path)['families']
blocked=defaultdict(list)
for f,d in master.items():
    if d['split'] in {'development','test'}:
        blocked[f.rsplit('|',1)[0]].append(dict(family=f,split=d['split'],codes=d['codes']))
original=read(BASE/'training-inventory-metadata.json')
kept=[r for r in original if r['aupadeshika'] not in blocked]
removed=[r for r in original if r['aupadeshika'] in blocked]
for r in kept:
    assert master[r['family']]['split']=='rl_train'
    assert r['aupadeshika']==r['family'].rsplit('|',1)[0]
assert not {r['aupadeshika'] for r in kept}&set(blocked)
save('training-inventory-metadata.json',kept)
excluded=[]
for f in sorted({r['family'] for r in removed}):
    rs=[r for r in removed if r['family']==f];citation=rs[0]['aupadeshika']
    excluded.append(dict(train_family=f,citation=citation,codes=sorted({r['code'] for r in rs}),
        removed_public_tuples=len(rs),cells=dict(Counter(r['cell'] for r in rs)),
        master_development_test_matches=sorted(blocked[citation],key=lambda x:x['family'])))
save('excluded-family-audit.json',excluded)
main={c:stats([r for r in kept if r['cell']==c]) for c in CELLS}
blocks=min(main[c]['public_tuples']//n for c,n in zip(CELLS,[13,2,10]));assert blocks>=56
blocks=56;quotas=dict(zip(CELLS,[728,112,560]));ordered={}
for cell in CELLS:
    pool=[r for r in kept if r['cell']==cell];picked=[]
    fc=Counter();fl=Counter();pc=Counter();vc=Counter();lc=Counter();gc=Counter()
    for step in range(quotas[cell]):
        la=LAS[step%len(LAS)] if cell==CELLS[2] else None
        options=[r for r in pool if la is None or r['lakara']==la];assert options
        r=min(options,key=lambda r:(fc[r['family']],fl[(r['family'],r['lakara'])],lc[r['lakara']],gc[r['gana']],pc[r['purusha']]+vc[r['vacana']],rank(r['id'])))
        picked.append(r);pool.remove(r);fc[r['family']]+=1;fl[(r['family'],r['lakara'])]+=1
        pc[r['purusha']]+=1;vc[r['vacana']]+=1;lc[r['lakara']]+=1;gc[r['gana']]+=1
    ordered[cell]=picked
curriculum=[]
for b in range(blocks):
    part=[(c,r) for c,n in zip(CELLS,[13,2,10]) for r in ordered[c][b*n:(b+1)*n]]
    for c,r in sorted(part,key=lambda cr:rank(f'block{b}:{cr[1]["id"]}')):
        curriculum.append(dict(position=len(curriculum),block=b,**r))
assert len(curriculum)==len({r['id'] for r in curriculum})==1400
assert Counter(r['cell'] for r in curriculum)==quotas
assert {r['family'] for r in curriculum}=={r['family'] for r in kept}
assert not {r['aupadeshika'] for r in curriculum}&set(blocked)
es=entries_by_code();holds=read(BASE.parent/'test-source-hold-predeclaration.json')['predicates']
for r in curriculum:
    assert master[r['family']]['split']=='rl_train' and family(es[r['code']])==r['family']
    t=make_task(es[r['code']],'rl_train',{k:r[k] for k in COORDS});validate_task(t,es[r['code']],'rl_train')
    assert not local_issue(t) and not oracle_issue(t)
    assert not any(r['code']==p['code'] and p['lakara'] in {'all',r['lakara']} for p in holds)
    assert digest(t['gold_slp1'])==r['canonical_gold_slp1_sha256'] and t['campaign']['prompt_sha256']==r['prompt_sha256']
save('curriculum-1400-metadata.json',curriculum)
fc=Counter(r['family'] for r in curriculum)
assert sha(master_path)==master_hash
assert all(sha(ROOT/p)==h for p,h in original_hashes.items())
audit=dict(created_at=datetime.now(timezone.utc).isoformat(),status='prospective_training_option_not_executed',
    additional_input_filter='Exclude any RL entry whose exact raw citation occurs anywhere in master development/test inventory, ignoring class. Apply before sampling, without reassignment or outcome information.',
    original_scope_unchanged=True,main_source_scope='Policy21 + pilot04 local holds + three source predicates, inherited exactly from main inventory.',
    master_development_test_raw_citations=len(blocked),original=stats(original),remaining=stats(kept),remaining_components=main,
    removed=dict(public_tuples=len(removed),families=len(excluded),raw_citations=len({r['aupadeshika'] for r in removed}),by_cell=dict(Counter(r['cell'] for r in removed))),
    raw_citation_overlap_with_any_master_development_test=0,declared_family_overlap_with_development_test=0,
    all_short_and_other_adanta_families_retained=all({r['family'] for r in kept if r['cell']==c}=={r['family'] for r in original if r['cell']==c} for c in CELLS[:2]),
    curriculum=dict(n=1400,blocks=56,quotas=quotas,seed=SEED,ordering_algorithm='Same input-only family/tense/class/PN load algorithm and seed as original, rerun on the restricted pool; 13/2/10 each25.',
        families=len(fc),max_family_load=max(fc.values()),family_load_sumsq=sum(v*v for v in fc.values()),
        all_remaining_families_covered=True,all_regenerated=1400,statistics=stats(curriculum),
        per_cell={c:stats([r for r in curriculum if r['cell']==c]) for c in CELLS}),
    limitations=['Closes exact raw-citation overlap only; no claim to merge synonymous roots, different anubandha/accent spellings or semantically related lexemes.',
        'No proof of entirely unseen Sanskrit lexical knowledge in any pretrained model.',
        'Nine hard-short families still limit lexical transfer coverage. More forms and replay do not add families.',
        'Same mechanical/source-review and accepted-spelling limitations as main inventory. No gold export or training-ready reward claim.'],
    preserved_original_hashes=original_hashes,master_split_path=str(master_path.relative_to(ROOT)),master_split_sha256=master_hash,
    source_dependencies=read(BASE/'curriculum-manifest.json')['source_dependencies'],model_output_files_read=[],api_calls=0,
    training_started=False,split_changes=False,test_candidate_changes=False)
save('supply-audit.json',audit)
save('curriculum-manifest.json',dict(created_at=audit['created_at'],kind='Strict-citation-disjoint RL metadata option; no training authorization',n=1400,families=len(fc),split='rl_train',component_weights=[.52,.08,.40],
    files={str((OUT/n).relative_to(ROOT)):sha(OUT/n) for n in ['training-inventory-metadata.json','curriculum-1400-metadata.json','excluded-family-audit.json','supply-audit.json','prepare.py']},
    master_split_path=str(master_path.relative_to(ROOT)),master_split_sha256=master_hash,source_dependencies=audit['source_dependencies'],
    original_manifest_path=str((BASE/'curriculum-manifest.json').relative_to(ROOT)),original_manifest_sha256=sha(BASE/'curriculum-manifest.json'),
    runtime_guard='At export, check every exact citation against all current master development/test citations AND each family/code against rl_train; fail on hash changes.',
    gold_export_created=False,training_started=False,provider_calls=0))
print(json.dumps(dict(remaining={c:{k:d[k] for k in ['public_tuples','families','distinct_family_coordinates']} for c,d in main.items()},removed=audit['removed'],curriculum=dict(n=1400,families=len(fc),max_family_load=max(fc.values()),family_load_sumsq=sum(v*v for v in fc.values())),all_original_files_unchanged=True),indent=2))
