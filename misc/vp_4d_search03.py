#!/usr/bin/env python3
"""Offline development research for fresh 4D hypotheses; no paid calls."""
from collections import Counter,defaultdict
from pathlib import Path
import datetime,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from misc.vp_4d_pilot import OUT,HISTORY,write,now,sha,load_entries,name,family
from misc.vp_cartesian_task import entry_scope_issue
from vidyut.prakriya import Vyakarana,Pada,Lakara,Prayoga,Purusha,Vacana
RUN_ID='overnight-search-03'
VEDIC_JUHOTYADI={f'03.{n:04d}' for n in range(15,27)}-{'03.0017'}

def status(phase,message):
 write(OUT/'status.json',dict(track='four_d',run_id=RUN_ID,state='running',updated_at=now(),phase=phase,message=message,benchmark_ready=False))
 with (OUT/'progress.md').open('a') as f:f.write(f'\n- {now()}: {phase}: {message}\n')

def lexical_base(e,vy):
 ps=vy.derive(Pada.Tinanta(dhatu=e.dhatu,lakara=Lakara.Lat,prayoga=Prayoga.Kartari,purusha=Purusha.Prathama,vacana=Vacana.Eka))
 if not ps:return None
 # Examine only initial lexical it-deletion metadata, never output forms.
 first=ps[0].history[0].result[0]
 for h in ps[0].history[1:]:
  if len(h.result)!=1:break
  if h.code=='1.3.9':return h.result[0]
 return first.replace('\\','').replace('^','')

def census():
 status('New lexical-mechanism census','Counting same-gana accent/anubandha contrasts using only dictionary identities and initial marker deletion, with no model-output filter.')
 es=[e for e in load_entries() if not entry_scope_issue(e) and e.code not in VEDIC_JUHOTYADI]
 splits=json.load(open(HISTORY/'family-split.json'))['families'];vy=Vyakarana();groups=defaultdict(list)
 for e in es:
  base=lexical_base(e,vy)
  if base:groups[base,name(e.dhatu.gana)].append(e)
 contrasts=[]
 for (base,gana),xs in groups.items():
  if len({e.dhatu.aupadeshika for e in xs})<=1:continue
  contrasts.append(dict(base=base,gana=gana,entries=[dict(code=e.code,aupadeshika=e.dhatu.aupadeshika,artha=e.artha,family=family(e),split=splits[family(e)]['split']) for e in xs]))
 out=dict(created_at=now(),method='Same gana and initial phonemic dhatu after it deletion; different fully visible citation strings. Never compare final output forms.',groups=contrasts)
 out['counts']={spl:dict(families=len({e['family'] for g in contrasts for e in g['entries'] if e['split']==spl}),ganas=dict(Counter(g['gana'] for g in contrasts for e in {e['family']:e for e in g['entries'] if e['split']==spl}.values()))) for spl in ['development','test','rl_train']}
 write(OUT/'search-03.marker-census.json',out)
 print(json.dumps(out['counts'],indent=2))
 for g in contrasts:
  dev=[e for e in g['entries'] if e['split']=='development']
  if dev:print(g['base'],g['gana'],[(e['code'],e['aupadeshika'],e['artha']) for e in dev])
if __name__=='__main__':census()
