"""Offline input/trace controls for the independent cross-track source review."""
import json, hashlib, datetime
from pathlib import Path
from misc.vp_campaign_candidates import load_entries
from vidyut.prakriya import Vyakarana, Pada, Sanadi, Lakara, Prayoga, Purusha, Vacana
P=Path('benchmarks/parallel-search-20261006')
OUT=P/'four_d/cross-track-source-review-01'
CAND=P/'five_d/candidate-4800/revision-01/tasks.json'
entries={e.code:e for e in load_entries()}
a=json.loads(CAND.read_text())
novel=json.loads((P/'five_d/candidate-4800/coordinator-novel-rule-screen.json').read_text())['novel_rule_task_counts']
ts=[t for t in a if t['derivation']['sanadi']==['san'] and set(t['campaign']['trace_rule_ids'])&set(novel)]
codes=sorted({t['dhatu']['code'] for t in ts})
v=Vyakarana()
def trace(ps):
 return [{'text':p.text,'history':[{'rule':h.code,'result':list(h.result)} for h in p.history]} for p in ps]
controls=[]
for code in codes:
 e=entries[code]; d=e.dhatu.with_sanadi([Sanadi.san])
 row={'code':code,'citation':e.dhatu.aupadeshika,'gana':repr(e.dhatu.gana),'artha':e.artha,'stem':trace(v.derive(d)),'finite':[]}
 for lak in [Lakara.Lat,Lakara.Lit,Lakara.Lrt,Lakara.Lun]:
  ps=v.derive(Pada.Tinanta(d,Prayoga.Kartari,lak,Purusha.Prathama,Vacana.Eka))
  row['finite'].append({'lakara':repr(lak),'traces':trace(ps)})
 controls.append(row)
actual=[]
for t in ts:
 m=t['morphology']; d=entries[t['dhatu']['code']].dhatu.with_sanadi([Sanadi.san])
 ps=v.derive(Pada.Tinanta(d,getattr(Prayoga,m['prayoga']),getattr(Lakara,m['lakara']),getattr(Purusha,m['purusha']),getattr(Vacana,m['vacana'])))
 actual.append({'task':t,'vp_traces':trace(ps),'regenerated_matches':sorted({p.text for p in ps})==t['gold_slp1']})
out={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_path':str(CAND),'sha256':hashlib.sha256(CAND.read_bytes()).hexdigest(),'model_answers_read':False,'codes':codes,'actual_candidate_inputs':actual,'controls':controls}
(OUT/'lexical-san-controls.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('candidate_inputs',len(actual),'roots',len(codes),'all_matches',all(t['regenerated_matches'] for t in actual))
for r in controls:
 print(r['code'],r['citation'],'stem',sorted({x['text'] for x in r['stem']}))
 for f in r['finite']:print(' ',f['lakara'],sorted({x['text'] for x in f['traces']}))
