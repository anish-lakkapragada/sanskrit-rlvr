"""Read-only export integrity checks; writes one additive receipt in this directory."""
from pathlib import Path
from collections import Counter
import datetime, hashlib, json
OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p/'misc/vp_cartesian_task.py').is_file())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
manifest = read(OUT/'manifest.json')
for name,h in manifest['files'].items(): assert sha(OUT/name)==h,name
for path,h in manifest['dependencies'].items(): assert sha(ROOT/path)==h,path
for path,h in manifest['inherited_source_dependencies'].items(): assert sha(ROOT/path)==h,path
tasks=read(OUT/'tasks.json');prompts=read(OUT/'public-prompts.json')
public=[json.loads(line) for line in (OUT/'public-tasks.jsonl').read_text().splitlines()]
gold=[json.loads(line) for line in (OUT/'canonical-gold.jsonl').read_text().splitlines()]
rows=read(OUT/'curriculum-metadata.json');source=read(OUT.parent/'curriculum-1400-metadata.json')
assert rows==source and len(tasks)==len(public)==len(gold)==len(prompts)==len(rows)==1400
for pos,(t,p,g,q,r) in enumerate(zip(tasks,public,gold,prompts,rows)):
    assert t['id']==p['id']==g['id']==q['id']==r['id']
    assert p['position']==g['position']==q['position']==r['position']==pos
    assert p['block']==q['block']==r['block']==pos//25
    assert set(p)=={'id','position','block','split','task_type','prompt_version','dhatu','morphology','prompt'}
    assert p['split']=='rl_train' and p['task_type']=='cartesian_4d'
    assert p['dhatu']==t['dhatu'] and p['morphology']==t['morphology']
    assert p['prompt']==q['prompt'] and 'Sanskrit verbal root' in p['prompt']
    assert hashlib.sha256(p['prompt'].encode()).hexdigest()==r['prompt_sha256']
    assert g['gold_slp1']==t['gold_slp1'] and g['gold_devanagari']==t['gold_devanagari']
    assert g['canonical_gold_variants']==len(t['gold_slp1'])
    assert g['canonical_gold_slp1_sha256']==r['canonical_gold_slp1_sha256']
    assert set(t['morphology'])=={'lakara','prayoga','purusha','vacana'} and 'derivation' not in t
for block in range(56):
    assert Counter(r['cell'] for r in rows[25*block:25*(block+1)])=={'short_adanta_non_aorist':13,'other_adanta_aorist':2,'broad_non_curadi':10}
plan_path=ROOT/'benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/execution-plan.json'
protected=read(plan_path)['dependencies']
assert not any((ROOT/p).resolve().is_relative_to(OUT) for p in protected)
for p,h in protected.items(): assert sha(ROOT/p)==h,p
audit=read(OUT/'materialization-audit.json')
for p,h in audit['preserved_original_file_hashes'].items(): assert sha(ROOT/p)==h,p
receipt={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':True,
 'n':1400,'original_metadata_and_order_unchanged':True,'public_gold_jsonl_roundtrip_and_alignment':True,
 'public_field_allowlist_passed':True,'all56_blocks_preserved':True,
 'all_frozen_paid_dependency_hashes_match':len(protected),'all_original_strict_file_hashes_match':True,
 'manifest_sha256':sha(OUT/'manifest.json'),'verification_script_sha256':sha(Path(__file__)),
 'model_outputs_read':False,'provider_calls':0,'training_started':False,
 'scope':'Export integrity check; regeneration/source/disjointness checks are in materialization-audit.json. No independent linguistic certification claimed.'}
target=OUT/'verification-receipt.json'
assert not target.exists(),'Preserve existing verification receipt'
target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
