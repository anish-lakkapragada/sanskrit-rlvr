"""Train-only input census/curriculum metadata. No model-result or API reads."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import re

from misc.vp_cartesian_task import entries_by_code, entry_scope_issue, oracle_issue, make_task, validate_task
from misc.vp_campaign_candidates import family, name
from misc.vp_4d_pilot04 import LOCAL_CODES, local_issue, LAS, COORDS
from misc.vp_4d_pilot05 import short
from misc.vp_4d_pilot import identity
from misc.vp_cartesian_prompt_v1 import render

ROOT=Path.cwd()
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
SEED='rl-52-8-40-supply-20261007-v1'
CELLS=['short_adanta_non_aorist','other_adanta_aorist','broad_non_curadi']
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
rank=lambda x:hashlib.sha256((SEED+':'+str(x)).encode()).hexdigest()
def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def stat(rows):
    fc=Counter(r['family'] for r in rows)
    return dict(public_tuples=len(rows),families=len(fc),
        distinct_family_coordinates=len({(r['family'],*(r[k] for k in COORDS)) for r in rows}),
        families_by_class=dict(Counter({r['family']:r['gana'] for r in rows}.values())),
        family_capacity=dict(sorted(fc.items())),
        capacity_at_family_caps={str(n):sum(min(n,v) for v in fc.values()) for n in [1,3,8,9,18,40,81,90]},
        by_tense=dict(Counter(r['lakara'] for r in rows)),by_person=dict(Counter(r['purusha'] for r in rows)),
        by_number=dict(Counter(r['vacana'] for r in rows)),by_class=dict(Counter(r['gana'] for r in rows)))

split_path=ROOT/'benchmarks/creation-campaign-20261006/family-split.json'
split_blob=read(split_path);assign=split_blob['families']
families_by_split={s:{f for f,d in assign.items() if d['split']==s} for s in ['rl_train','development','test']}
assert not any(families_by_split[a]&families_by_split[b] for a,b in [('rl_train','test'),('rl_train','development'),('test','development')])
holds_path=BASE/'test-source-hold-predeclaration.json';holds=read(holds_path)['predicates']
def held(code,la):return any(code==p['code'] and p['lakara'] in {'all',la} for p in holds)
es=entries_by_code();by_public={};entry_holds=[];reject=Counter();derived=0
for code,e in sorted(es.items()):
    f=family(e)
    if f not in families_by_split['rl_train']:continue
    g=name(e.dhatu.gana);adanta=g=='Curadi' and e.dhatu.aupadeshika.endswith('a')
    issue=entry_scope_issue(e) or ('pilot04 local entry hold' if code in LOCAL_CODES else None)
    if issue:
        entry_holds.append(dict(code=code,family=f,reason=issue));continue
    if g=='Curadi' and not adanta:continue
    cell='broad_non_curadi' if g!='Curadi' else ('short_adanta_non_aorist' if short(e) else 'other_adanta_aorist')
    lakaras=LAS if cell=='broad_non_curadi' else [x for x in LAS if x!='Lun'] if cell==CELLS[0] else ['Lun']
    for la in lakaras:
        for pu in ['Prathama','Madhyama','Uttama']:
            for va in ['Eka','Dvi','Bahu']:
                if held(code,la):reject['additional_source_hold']+=1;continue
                m=dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va)
                t=make_task(e,'rl_train',m);derived+=1
                if not t:reject['no_engine_form']+=1;continue
                issue=oracle_issue(t) or ('pilot04 local tuple hold' if local_issue(t) else None)
                if issue:reject[issue]+=1;continue
                pub=identity(t);prompt_hash=hashlib.sha256(render(t).encode()).hexdigest()
                gold_hash=digest(t['gold_slp1'])
                if pub in by_public:
                    prev=by_public[pub]
                    assert prev['canonical_gold_slp1_sha256']==gold_hash and prev['prompt_sha256']==prompt_hash
                    prev['equivalent_codes'].append(code);continue
                by_public[pub]=dict(id=t['id'],code=code,equivalent_codes=[code],family=f,split='rl_train',gana=g,
                    aupadeshika=e.dhatu.aupadeshika,artha=e.artha,cell=cell,**m,
                    canonical_gold_variants=len(t['gold_slp1']),canonical_gold_slp1_sha256=gold_hash,
                    prompt_sha256=prompt_hash,
                    stricter_vowel_rC_spelling_hold=any(re.search('[aAiIuUfFxXeEoO]rC',v) for v in t['gold_slp1']))
rows=sorted(by_public.values(),key=lambda x:(x['cell'],rank(x['id'])))
assert len(rows)==len({r['id'] for r in rows})==len({r['prompt_sha256'] for r in rows})
assert {r['family'] for r in rows}<=families_by_split['rl_train']
save('training-inventory-metadata.json',rows)
main={c:stat([r for r in rows if r['cell']==c]) for c in CELLS}
strict={c:stat([r for r in rows if r['cell']==c and not r['stricter_vowel_rC_spelling_hold']]) for c in CELLS}

# Compare only input metadata, never results. Family exclusion is stronger than
# code identity and covers all dictionary synonyms and every coordinate.
comparators=[BASE/'tasks.json',BASE/'candidate-1250-source-filtered/tasks.json']
comparison=[]
cross_class_diagnostics=[]
train_families={r['family'] for r in rows};train_public=set(by_public)
for p in comparators:
    ts=read(p);fs={t['campaign']['root_family'] for t in ts}
    f_overlap=train_families&fs;pub_overlap=train_public&{identity(t) for t in ts}
    assert not f_overlap and not pub_overlap
    comparison.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),tasks=len(ts),families=len(fs),
        family_overlap=0,public_tuple_overlap=0))
    common={r['aupadeshika'] for r in rows}&{t['dhatu']['aupadeshika'] for t in ts}
    detailed=[]
    for citation in sorted(common):
        rr=[r for r in rows if r['aupadeshika']==citation]
        tt=[t for t in ts if t['dhatu']['aupadeshika']==citation]
        assert not {r['gana'] for r in rr}&{t['dhatu']['gana'] for t in tt}
        detailed.append(dict(exact_citation=citation,train_families=sorted({r['family'] for r in rr}),
            comparator_families=sorted({t['campaign']['root_family'] for t in tt}),
            train_codes=sorted({r['code'] for r in rr}),comparator_codes=sorted({t['dhatu']['code'] for t in tt}),
            train_public_tuples=len(rr),comparator_tasks=len(tt)))
    cross_class_diagnostics.append(dict(comparator_path=str(p.relative_to(ROOT)),
        definition='Exact raw Dhatupatha citation with class ignored; no marker stripping, phonological stem merging or semantic-equivalence inference.',
        shared_citations=len(common),train_families=len({f for x in detailed for f in x['train_families']}),
        comparator_families=len({f for x in detailed for f in x['comparator_families']}),
        train_public_tuples=sum(x['train_public_tuples'] for x in detailed),
        comparator_tasks=sum(x['comparator_tasks'] for x in detailed),details=detailed))

history=[ROOT/'benchmarks/full-tasks.json']
for campaign in ['creation-campaign-20261006','iterative-goal-20261006']:
    history+=sorted((ROOT/'benchmarks'/campaign/'jobs').glob('*/tasks.json'))
legacy_families=set();legacy_tuples=set();modern_families=set();modern_tuples=set();history_skip=Counter()
for p in history:
    legacy=p.name=='full-tasks.json'
    for top in read(p):
        for t in top.get('forms',[top]):
            if not isinstance(t,dict) or 'dhatu' not in t:continue
            d=t['dhatu']
            if not isinstance(d,dict) or 'gana' not in d or not ('aupadeshika' in d or 'upadesha' in d):
                history_skip['non_dictionary_root_task']+=1;continue
            f=d.get('aupadeshika',d.get('upadesha','UNKNOWN'))+'|'+d['gana']
            (legacy_families if legacy else modern_families).add(f)
            if set(t.get('morphology',{}))!=set(COORDS):continue
            if any(t.get('derivation',{}).get(k) for k in ['sanadi','prefixes']):continue
            if any(o.get(k) for o in [t,d,t['morphology']] for k in ['pada','dhatu_pada','prefixes','sanadi']):continue
            if 'aupadeshika' not in d or 'artha' not in d:continue
            (legacy_tuples if legacy else modern_tuples).add(identity(t))

# Exact13:2:10 blocks preserve52/8/40. Select without replacement. Coverage and
# balanced family loads precede tense/person/number balance; no model outcomes.
blocks=min(main[c]['public_tuples']//n for c,n in zip(CELLS,[13,2,10]))
target={c:blocks*n for c,n in zip(CELLS,[13,2,10])}
ordered={}
for cell in CELLS:
    pool=[r for r in rows if r['cell']==cell];picked=[]
    fc=Counter();fl=Counter();pc=Counter();vc=Counter();lc=Counter();gc=Counter()
    for step in range(target[cell]):
        # Broad rounds cover all ten tenses, while taking new families first
        # wherever this exact tense remains available.
        la=LAS[step%len(LAS)] if cell==CELLS[2] else None
        options=[r for r in pool if la is None or r['lakara']==la]
        assert options
        chosen=min(options,key=lambda r:(fc[r['family']],fl[(r['family'],r['lakara'])],
            lc[r['lakara']],gc[r['gana']],pc[r['purusha']]+vc[r['vacana']],rank(r['id'])))
        picked.append(chosen);pool.remove(chosen)
        fc[chosen['family']]+=1;fl[(chosen['family'],chosen['lakara'])]+=1
        pc[chosen['purusha']]+=1;vc[chosen['vacana']]+=1;lc[chosen['lakara']]+=1;gc[chosen['gana']]+=1
    ordered[cell]=picked
curriculum=[]
for b in range(blocks):
    part=[(c,r) for c,n in zip(CELLS,[13,2,10]) for r in ordered[c][b*n:(b+1)*n]]
    for c,r in sorted(part,key=lambda cr:rank(f'block{b}:{cr[1]["id"]}')):
        curriculum.append(dict(position=len(curriculum),block=b,**r))
assert len(curriculum)==len({r['id'] for r in curriculum})==blocks*25
assert Counter(r['cell'] for r in curriculum)==target
assert {r['family'] for r in curriculum}<=families_by_split['rl_train']
for r in curriculum:
    e=es[r['code']];t=make_task(e,'rl_train',{k:r[k] for k in COORDS})
    validate_task(t,e,'rl_train')
    assert t['id']==r['id'] and digest(t['gold_slp1'])==r['canonical_gold_slp1_sha256']
    assert not local_issue(t) and not held(r['code'],r['lakara'])
save('curriculum-1400-metadata.json',curriculum)
for comparison_row in cross_class_diagnostics:
    for d in comparison_row['details']:
        d['curriculum_tasks']=sum(r['aupadeshika']==d['exact_citation'] for r in curriculum)
    comparison_row['curriculum_tasks']=sum(d['curriculum_tasks'] for d in comparison_row['details'])
cs={c:stat([r for r in curriculum if r['cell']==c]) for c in CELLS}
loads=Counter(r['family'] for r in curriculum)
frozen_source_paths=[split_path,holds_path,ROOT/'misc/vp_cartesian_task.py',ROOT/'misc/vp_cartesian_prompt_v1.py',
    ROOT/'misc/vp_4d_pilot04.py',ROOT/'misc/vp_4d_pilot05.py',ROOT/'misc/vp_4d_candidate_prepare.py',
    ROOT/'misc/vp_campaign_candidates.py',ROOT/'finetune/prompts.py',ROOT/'prompts/v2/vp_task_eval.txt',
    ROOT/'data/finetune/task-data/vidyut_dhatupatha_5.tsv',
    ROOT/'benchmarks/parallel-search-20261006/oracle-policy-21.json']
out=dict(created_at=datetime.now(timezone.utc).isoformat(),scope='Input-only RL-training-family supply; same source scope as candidate1250; no training, evaluation, model output, split or ledger mutation.',
    main_scope=dict(shared_policy=21,pilot04_local_holds=sorted(LOCAL_CODES),additional_source_predicates=holds,
        extra_spelling_filter_applied=False,relation_to_candidate='Exact same scope predicates as candidate-1250-source-filtered. Additional source predicates affect test entries only; none of those codes is in RL.'),
    master_split_counts={s:len(f) for s,f in families_by_split.items()},main_supply=main,combined_main=stat(rows),
    stricter_spelling_sensitivity=dict(predicate='Any canonical gold contains vowel followed by rC (SLP1 C=ch); not applied to main scope or curriculum.',supply=strict,removed_metadata=[r for r in rows if r['stricter_vowel_rC_spelling_hold']]),
    dictionary_derivations=derived,entry_holds=entry_holds,tuple_rejections=dict(reject),
    duplicate_public_code_rows_collapsed=sum(len(r['equivalent_codes'])-1 for r in rows),
    split_guard=dict(rl_development_overlap=0,rl_test_overlap=0,all_main_families_authorized_rl=True,comparators=comparison),
    exact_citation_class_ignored_diagnostic=dict(assignment_changed=False,counts=cross_class_diagnostics,
        interpretation='Declared families (exact citation plus class) are disjoint. Equal citations in different classes can cross splits; this does not establish entirely unseen Sanskrit lexemes. No speculative stem or sense grouping is applied.'),
    historical_input_exposure=dict(files=len(history),non_dictionary_task_rows_skipped=dict(history_skip),legacy_family_overlap=len(train_families&legacy_families),legacy_exact_public_tuple_overlap=len(train_public&legacy_tuples),modern_job_family_overlap=len(train_families&modern_families),modern_exact_public_tuple_overlap=len(train_public&modern_tuples),master_warning=split_blob['prior_exposure'],training_checkpoint_status=split_blob['training_status'],history_files={str(p.relative_to(ROOT)):sha(p) for p in history}),
    curriculum=dict(seed=SEED,n=len(curriculum),blocks=blocks,per_block={c:n for c,n in zip(CELLS,[13,2,10])},exact_weights=[.52,.08,.40],selection='Deterministic input hashes; minimize family load then within-family tense repeats then marginal tense/class/PN loads. Broad cell cycles all10tense labels. No replacement within this pass.',families=len(loads),max_family_load=max(loads.values()),family_load_sumsq=sum(v*v for v in loads.values()),cells=cs,all_stats=stat(curriculum),all_regenerated=len(curriculum),unused_by_cell={c:main[c]['public_tuples']-target[c] for c in CELLS},scope_identical_to_main=True,not_executed=True),
    family_repetition_limits=dict(short_families=main[CELLS[0]]['families'],short_family_tense_slots=len({(r['family'],r['lakara']) for r in rows if r['cell']==CELLS[0]}),one_per_short_family_tense_exact_mix_n_max=25*(len({(r['family'],r['lakara']) for r in rows if r['cell']==CELLS[0]})//13),unique_public_tuple_exact_mix_n_max=25*blocks,interpretation='More persons/numbers or replayed epochs do not add root families or independent mechanisms.'),
    source_limits=['RL roots/forms mechanically derived and filtered; no new independent full-paradigm or spelling certification.','The96ending-screen alias whitelist is task-specific and is not automatically transferred to this inventory.','The manifest identifies train-only metadata, not training-ready rewards or authorization to finetune. Existing checkpoints are not certified split-clean.','If a fresh learner is trained, all SFT/RL/evaluation-selection stages must preserve the master family boundary; dev/test prompts and gold must not enter training assets.'],
    dependencies={str(p.relative_to(ROOT)):sha(p) for p in frozen_source_paths},outcome_files_read=[],provider_calls=0,training_started=False,split_mutated=False,benchmark_ready=False)
save('supply-audit.json',out)
save('curriculum-manifest.json',dict(created_at=out['created_at'],kind='Deterministic train-only curriculum metadata; no training or final benchmark authorization',split='rl_train',seed=SEED,n=len(curriculum),component_weights=[.52,.08,.40],
    tasks_metadata_path=str((OUT/'curriculum-1400-metadata.json').relative_to(ROOT)),tasks_metadata_sha256=sha(OUT/'curriculum-1400-metadata.json'),
    inventory_metadata_path=str((OUT/'training-inventory-metadata.json').relative_to(ROOT)),inventory_metadata_sha256=sha(OUT/'training-inventory-metadata.json'),
    supply_audit_sha256=sha(OUT/'supply-audit.json'),generator_sha256=sha(Path(__file__)),master_split_path=str(split_path.relative_to(ROOT)),master_split_sha256=sha(split_path),
    candidate_comparators=comparison,source_dependencies=out['dependencies'],family_overlap_with_development_or_test=0,
    loader_requirement='Revalidate split for EVERY code/equivalent-code/family and regenerate gold/prompt before export. Public prompt files must be separated from private keys/trace metadata. No result records consumed.',training_status='metadata_prepared_not_trained',gold_or_prompt_export_created=False,paid_calls=0))
print(json.dumps(dict(main={c:{k:d[k] for k in ['public_tuples','families','distinct_family_coordinates']} for c,d in main.items()},strict={c:{k:d[k] for k in ['public_tuples','families']} for c,d in strict.items()},curriculum=dict(n=len(curriculum),families=len(loads),max_load=max(loads.values()),all_regenerated=len(curriculum)),history={k:v for k,v in out['historical_input_exposure'].items() if k!='history_files'}),indent=2))
