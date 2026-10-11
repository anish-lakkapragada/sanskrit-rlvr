"""Input-defined offline ending-interaction census; no held-out answers or APIs."""
import json,re,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue,make_task,GRAMMAR,Pada,Lakara,Prayoga,Purusha,Vacana
from misc.vp_campaign_candidates import family,name
from misc.vp_4d_coverage05 import LOCAL,SPECIAL_IT
ROOT=Path.cwd();OUT=ROOT/'benchmarks/parallel-search-20261007/four_d-90';SPL=ROOT/'benchmarks/creation-campaign-20261006/family-split.json';assign=json.loads(SPL.read_text())['families'];es=entries_by_code()
# Fixed before reading any additional development outcomes.
CELLS={
 'future_ending_lopa':dict(coords=[('Lut','Madhyama','Eka')],rules={'7.4.50'}),
 'secondary_plural_cluster':dict(coords=[(la,'Prathama','Bahu') for la in ['Lan','Lrn']],rules={'8.2.23','8.4.37'}),
 'ling_plural_jus':dict(coords=[(la,'Prathama','Bahu') for la in ['VidhiLin','AshirLin']],rules={'3.4.108'}),
 'sigmatic_aprkta_repair':dict(coords=[('Lun',pu,'Eka') for pu in ['Prathama','Madhyama']],rules={'7.3.96','8.2.28'})}
rows=[];examples=defaultdict(list);exclusions=Counter();derived=0
for code,e in sorted(es.items()):
 if entry_scope_issue(e) or code in LOCAL:continue
 if name(e.dhatu.gana)=='Curadi' and e.dhatu.aupadeshika.endswith('a'):continue
 for cell,cfg in CELLS.items():
  for la,pu,va in cfg['coords']:
   m=dict(lakara=la,prayoga='Kartari',purusha=pu,vacana=va);spl=assign[family(e)]['split'];t=make_task(e,spl,m);derived+=1
   if not t:continue
   if oracle_issue(t) or (code=='10.0412' and la=='Lun') or any(re.search('[aAiIuUfFxXeEoO]rC',g) for g in t['gold_slp1']):exclusions['policy_or_local_spelling']+=1;continue
   rs=set(t['campaign']['trace_rule_ids'])
   if '1.2.1' in rs or rs&{'8.3.78','8.3.79'} or (name(e.dhatu.gana)!='Curadi' and la in ['Lut','Lrt','Lrn'] and rs&SPECIAL_IT):continue
   if not cfg['rules']<=rs:continue
   ps=GRAMMAR.derive(Pada.Tinanta(dhatu=e.dhatu,lakara=getattr(Lakara,la),prayoga=Prayoga.Kartari,purusha=getattr(Purusha,pu),vacana=getattr(Vacana,va)))
   if not all(cfg['rules']<={h.code for h in p.history if name(h.source)=='Ashtadhyayi'} for p in ps):exclusions['easy_alternative_lacks_required_interaction']+=1;continue
   # Same grammatical interaction must cover all accepted derivation paths.
   r=dict(id=t['id'],code=code,family=family(e),gana=name(e.dhatu.gana),split=spl,cell=cell,**m,path_count=len(ps),gold_variants=len(t['gold_slp1']),rules=sorted(cfg['rules']))
   rows.append(r)
   if spl=='development' and len(examples[cell])<3:examples[cell].append(dict(code=code,citation=e.dhatu.aupadeshika,morphology=m,gold=t['gold_devanagari'],path_count=len(ps)))
# Only input metadata from every historical job; private held-out answers never opened.
exposed=set();sources=[]
paths=[ROOT/'benchmarks/full-tasks.json']
for campaign in ['creation-campaign-20261006','iterative-goal-20261006']:
 paths+=sorted((ROOT/'benchmarks'/campaign/'jobs').glob('*/tasks.json'))
for p in paths:
  for top in json.loads(p.read_text()):
   for t in top.get('forms',[top]):
    if not isinstance(t,dict) or 'dhatu' not in t or len(t.get('morphology',{}))!=4:continue
    if any(t.get('derivation',{}).get(k) for k in ['sanadi','prefixes']):continue
    if any(o.get(k) for o in [t,t['dhatu'],t['morphology']] for k in ['pada','dhatu_pada','prefixes','sanadi']):continue
    m=t['morphology']; exposed.add((str(t['dhatu'].get('aupadeshika',t['dhatu'].get('upadesha','UNKNOWN')))+'|'+str(t['dhatu'].get('gana')),*(m.get(k) for k in ['lakara','prayoga','purusha','vacana'])))
  sources.append(str(p.relative_to(ROOT)))
key=lambda r:(r['code'],r['lakara'],r['prayoga'],r['purusha'],r['vacana'])
for r in rows:r['prior_exact_input']=(r['family'],r['lakara'],r['prayoga'],r['purusha'],r['vacana']) in exposed
summ=lambda rr:dict(tuples=len(rr),families=len({r['family'] for r in rr}),family_classes=dict(Counter({r['family']:r['gana'] for r in rr}.values())),lakaras=dict(Counter(r['lakara'] for r in rr)),previous_exact=sum(r['prior_exact_input'] for r in rr))
summary={c:{spl:summ([r for r in rows if r['cell']==c and r['split']==spl]) for spl in ['development','test','rl_train']} for c in CELLS}
summary['union']={spl:summ([r for r in rows if r['split']==spl]) for spl in ['development','test','rl_train']}
summary['fresh_development']={c:summ([r for r in rows if r['split']=='development' and r['cell']==c and not r['prior_exact_input']]) for c in CELLS}
# All matching usable outcomes from prespecified completed ordinary4D development jobs.
bykey={key(r):r for r in rows if r['split']=='development'};history=defaultdict(lambda:dict(n=0,correct=0,families=set(),jobs=Counter()));reads=[]
jobnames=[f'opus-four-d-pilot-{i:02}' for i in range(1,9)]+[f'opus-fast-simple4d-{i:02}' for i in range(1,6)]+[f'opus-fast-control-{i:02}' for i in range(1,6)]
for jid in jobnames:
 p=ROOT/'benchmarks/iterative-goal-20261006/jobs'/jid/'results.json'
 if not p.exists():continue
 reads.append(str(p.relative_to(ROOT)))
 for result in json.loads(p.read_text()):
  t=result['task'];assert t['campaign']['split']=='development'
  m=t['morphology'];k=(t['dhatu']['code'],*(m[a] for a in ['lakara','prayoga','purusha','vacana']))
  if k not in bykey or result['status']!='completed' or result.get('truncated') or not result.get('answer'):continue
  rr=bykey[k];z=history[rr['cell']];z['n']+=1;z['correct']+=int(result['is_correct']);z['families'].add(rr['family']);z['jobs'][jid]+=1
history={c:dict(n=v['n'],correct=v['correct'],families=len(v['families']),jobs=dict(v['jobs'])) for c,v in history.items()}
meta=OUT/'broader-hypothesis-metadata.json';meta.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
out=dict(created_at=datetime.now(timezone.utc).isoformat(),kind='prospective hypothesis census; not frozen questions or authorization',predicate_cells={c:dict(coordinates=v['coords'],require_on_every_derivation_path=sorted(v['rules'])) for c,v in CELLS.items()},dictionary_entries=len(es),actual_derivations=derived,scope='Policy21, current local holds, Kartari, no added operations/prefix/pada, exclude all adanta Curadi/Kutadi/dhvam/specialized future-it and vowel-rC spelling uncertainty. Keep full gold unions. All-path condition prevents an easier accepted branch bypassing the intended rule.',counts=summary,exclusions=dict(exclusions),examples_development_only=dict(examples),prior_completed_development_coverage=history,outcome_files_read=reads,history_input_file_count=len(sources),metadata_path=str(meta.relative_to(ROOT)),metadata_sha256=hashlib.sha256(meta.read_bytes()).hexdigest(),adapter_sha256=hashlib.sha256((ROOT/'misc/vp_cartesian_task.py').read_bytes()).hexdigest(),family_split_sha256=hashlib.sha256(SPL.read_bytes()).hexdigest(),model_answer_selection=False,heldout_answers_read=False,paid_calls=0,benchmark_ready=False)
(OUT/'broader-hypothesis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=summary,prior=history,examples=dict(examples)),ensure_ascii=False,indent=2))
