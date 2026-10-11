"""Classical-scope impact: input selection first; development score fields only."""
import json,datetime,hashlib
from pathlib import Path
from misc.vp_campaign_candidates import load_entries
P=Path('benchmarks/parallel-search-20261006');O=P/'four_d/cross-track-source-review-01'
a=json.load(open(P/'development-results.json'))
codes={'02.0071','02.0072','02.0073','02.0074'}
rows=[]
for d in sorted(Path('benchmarks/iterative-goal-20261006/jobs').iterdir()):
 if not any(s in d.name for s in ['four-d-pilot','five-d-pilot','five-d-cap']):continue
 p=d/'tasks.json'
 if not p.exists():continue
 ts=json.load(open(p));ex={x['id'] for x in a.get('experiments',{}).get(d.name,{}).get('excluded',[])}
 affected=[t for t in ts if t.get('dhatu',{}).get('code') in codes]
 current=[t for t in affected if t['id'] not in ex]
 row={'job':d.name,'input_path':str(p),'raw_n':len(ts),'affected_inputs':[{k:t[k] for k in ['id','dhatu','morphology']} for t in affected],'currently_eligible_affected_ids':[t['id'] for t in current]}
 # Only development pilot jobs, frozen proposed predicate precedes any score lookup.
 if current and d.name in a['experiments']:
  rr={r['task_id']:{k:r.get(k) for k in ['status','is_correct','truncated']} for r in json.load(open(d/'results.json'))}
  removed=[rr[t['id']] for t in current];b=a['experiments'][d.name]['within_current_scope']
  c=sum(bool(r['is_correct']) for r in removed);n=len(removed)
  done=[r for r in removed if r['status']=='completed']; dc=sum(bool(r['is_correct']) for r in done)
  row['removed_development_score_counts']={'n':n,'correct':c,'completed':len(done),'completed_correct':dc}
  row['prior_scope_counts']={k:b[k] for k in ['n','correct','completed','completed_correct']}
  row['hypothetical_after_only_this_scope_hold']={'n':b['n']-n,'correct':b['correct']-c,'completed':b['completed']-len(done),'completed_correct':b['completed_correct']-dc}
 rows.append(row)
candidates=[]
for p in sorted((P/'five_d/candidate-4800').rglob('tasks.json')):
 ts=json.load(open(p));affected=[t for t in ts if t['dhatu']['code'] in codes]
 candidates.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'n':len(ts),'affected_ids':[t['id'] for t in affected]})
out={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'predicate':{'exact_codes':sorted(codes),'all_coordinates':True,'all_recipes':True,'explicitly_preserve':['02.0075']},'shared_policy_mutated':False,'basis':'Declared classical Paninian finite-form scope','entries':[{'code':e.code,'aupadeshika':e.dhatu.aupadeshika,'gana':repr(e.dhatu.gana),'artha':e.artha} for e in load_entries() if e.code in codes|{'02.0075'}],
'sources':[{'url':'https://www.ashtadhyayi.com/bhashya/4?scroll=bhashya-11009','work':'Mahabhasya1.1.6','quote':'दीधीवेव्यौ छन्दसो विषयौ','finding':'Direct primary text confirms dIdhI/vevI Vedic scope.'},{'url':'https://ashtadhyayi.com/sutraani/lsk345','work':'Mahabhasya6.1.6','quote':'षसिवशी छान्दसौ','finding':'Confirms sas/vas Vedic characterization, subject to explicit classical exception below.'},{'url':'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.53.htm','work':'Balamanorama and Tattvabodhini','finding':'Names dIdhI,vevI,sas,sasti,vas as the five; says unrestricted classical paradigm enumeration is inappropriate; explicitly preserves classical uses of vas. There is textual disagreement whether sasti is a separate historical entry, but installed zasti~ exactly identifies the disputed Vedic entry and has no classical license here.'},{'url':'https://jainqq.org/booktext/Kshir_Tarangini/002433','work':'Kshiratarangini, printedp167–168','finding':'The earlier caution arose from p168 editorial acchandasatva wording. It conflicts with p167 footnote and the primary Mahabhasya text itself. It is not sufficient contrary evidence for a classical Paninian benchmark. Katant ra alternative tradition is noted separately, not silently imported into this contract.'}],
'interpretation':'Recommend exact71–74 scope hold with75 preserved. This supersedes the tentative unresolved classification in search-03.lexical-scope-scan.json; do not rewrite that historical artifact. Morphological single-san defects remain independently documented.',
'method':'Inspect input codes before any score fields. Only existing development results is_correct/status fields were extracted; no final model answers exist or were read. Counterfactual counts apply this scope hold alone against the shared development-results snapshot and leave raw files unchanged.',
'development_snapshot_updated_at':a['updated_at'],'jobs':rows,'candidate_versions':candidates}
(O/'classical-scope-proposal.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for r in rows:print(r['job'],len(r['affected_inputs']),r.get('hypothetical_after_only_this_scope_hold'))
