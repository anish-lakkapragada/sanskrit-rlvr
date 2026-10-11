"""Input/oracle-only novel nested-rule controls. No model response files read."""
import json,concurrent.futures
from pathlib import Path
import requests
from html.parser import HTMLParser
class TextParser(HTMLParser):
 def __init__(self): super().__init__();self.parts=[]
 def handle_data(self,data): self.parts.append(data)
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_cartesian_task import GRAMMAR,entries_by_code,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana
B=OUT/'candidate-4800'
A=B/'nested-source-review-01';A.mkdir(exist_ok=True)
def derive(code,ops,m):
 e=entries_by_code()[code];d=e.dhatu.with_sanadi([getattr(Sanadi,x) for x in ops])
 return GRAMMAR.derive(Pada.Tinanta(dhatu=d,**{k:getattr({'lakara':Lakara,'prayoga':Prayoga,'purusha':Purusha,'vacana':Vacana}[k],v) for k,v in m.items()}))
def traces(code,ops,m):
 return [dict(text=p.text,history=[dict(rule=h.code,source=str(h.source),terms=list(h.result)) for h in p.history]) for p in derive(code,ops,m)]
def fetch(r):
 u=f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{r.split(".")[0]}/{r}.htm';q=requests.get(u,timeout=25);
 if q.status_code!=200:return dict(rule=r,url=u,http_status=q.status_code,cached=False,review_source='Browser primary-source retrieval; see rule review')
 q.encoding='utf-8';(A/f'{r}.html').write_text(q.text);parser=TextParser();parser.feed(q.text);s=' '.join(x.strip() for x in parser.parts if x.strip());(A/f'{r}.txt').write_text(s);return dict(rule=r,url=u,html_sha256=sha(A/f'{r}.html'),text_sha256=sha(A/f'{r}.txt'))
def main():
 ts=json.loads((B/'tasks.json').read_text());screen=json.loads((B/'coordinator-novel-rule-screen.json').read_text());rs={r:[t for t in ts if len(t['derivation']['sanadi'])>1 and r in t['campaign']['trace_rule_ids']] for r in screen['novel_rule_task_counts']};rs={r:t for r,t in rs.items() if t}
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:sources=list(pool.map(fetch,rs))
 out={}
 for r,rows in rs.items():
  seen=set();samples=[];transitions=[]
  for t in rows:
   key=(t['dhatu']['code'],tuple(t['derivation']['sanadi']),t['morphology']['lakara'],t['morphology']['prayoga'])
   if key in seen:continue
   seen.add(key);ps=traces(key[0],list(key[1]),t['morphology']);samples.append(dict(id=t['id'],dhatu=t['dhatu'],morphology=t['morphology'],operations=list(key[1]),derivations=ps))
   for p in ps:
    for i,h in enumerate(p['history']):
     if h['rule']==r:
      z=dict(code=key[0],operations=list(key[1]),lakara=key[2],voice=key[3],step=i,before=p['history'][i-1]['terms'] if i else [],after=h['terms'],ric_steps=[j for j,x in enumerate(p['history']) if x['rule']=='3.1.26'],luk_steps=[j for j,x in enumerate(p['history']) if x['rule']=='2.4.74'])
      if z not in transitions:transitions.append(z)
  out[r]=dict(candidate_count=len(rows),candidate_ids=[t['id'] for t in rows],source=next(s for s in sources if s['rule']==r),samples=samples,transitions=transitions)
 atomic_json(A/'trace-audit.json',dict(created_at=now(),generator_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),candidate_source_sha256=sha(B/'tasks.json'),scope='All23 newly covered nested rules; oracle traces only, no model answers.',rules=out))
 print(json.dumps({r:dict(n=x['candidate_count'],unique_transitions=len(x['transitions']),examples=x['transitions'][:2]) for r,x in out.items()},ensure_ascii=False,indent=2))
 status('source-audit','Cached primary commentary and saved input-only traces for all 23 newly covered nested rules. Candidate revision 02 remains unpublished while narrow source issues are resolved.')
if __name__=='__main__':main()
