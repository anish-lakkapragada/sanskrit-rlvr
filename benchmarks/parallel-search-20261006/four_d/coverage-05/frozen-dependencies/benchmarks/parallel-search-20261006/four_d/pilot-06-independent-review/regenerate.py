"""Independent input/source audit only; never opens any provider result file."""
from pathlib import Path
import sys,json,hashlib,argparse
from datetime import datetime,timezone
from collections import Counter
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from misc.vp_cartesian_task import entries_by_code,validate_task,make_task,oracle_issue
from misc.vp_goal_validate import validate
from vidyut.prakriya import Vyakarana,Pada,DhatuPada,Lakara,Prayoga,Purusha,Vacana
OUT=Path(__file__).resolve().parent
V=Vyakarana(); E=entries_by_code()
FOCUS={'1.2.4','1.1.5','1.3.12','1.3.72','1.3.78','3.1.78','3.1.81','3.1.82','3.4.92','6.4.34','6.4.107','6.4.111','6.4.112','6.4.113','6.4.116','7.3.84','7.3.86'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def paths(t,pada=None):
 m=t['morphology'];kw={k:getattr(c,m[k]) for k,c in [('lakara',Lakara),('prayoga',Prayoga),('purusha',Purusha),('vacana',Vacana)]}
 return V.derive(Pada.Tinanta(dhatu=E[t['dhatu']['code']].dhatu,**kw,dhatu_pada=pada))
def audit(t):
 e=E[t['dhatu']['code']];validate_task(t,e,'development')
 ps=paths(t); fixed={p.name:sorted({x.text for x in paths(t,p)}) for p in [DhatuPada.Parasmaipada,DhatuPada.Atmanepada]}
 assert set(t['gold_slp1'])==set(fixed['Parasmaipada'])|set(fixed['Atmanepada'])
 return dict(id=t['id'],dhatu=t['dhatu'],morphology=t['morphology'],gold=t['gold_slp1'],pada_specific_forms=fixed,pada_union_matches=True,paths=[dict(form=p.text,has_pit_rule=any(h.code=='3.4.92' for h in p.history),rules=sorted({h.code for h in p.history}),focus_steps=[dict(index=i,rule=h.code,before=list(p.history[i-1].result) if i else [],after=list(h.result)) for i,h in enumerate(p.history) if h.code in FOCUS]) for p in ps])
def main():
 pa=argparse.ArgumentParser();pa.add_argument('--panel',type=Path);a=pa.parse_args()
 source=ROOT/'benchmarks/parallel-search-20261006/four_d/coverage-05/athematic-development-controls.json'
 pairs=json.loads(source.read_text());out=[]
 for pair in pairs:
  x={k:audit(pair[k]) for k in ['target','present']};x['branch']=pair['branch']
  assert all(p['has_pit_rule'] for p in x['target']['paths'])
  assert all(not p['has_pit_rule'] for p in x['present']['paths'])
  assert all(not ({'6.4.111','6.4.113','6.4.116','6.4.34','6.4.107'} & set(p['rules'])) for p in x['target']['paths'])
  out.append(x)
 report=dict(created_at=datetime.now(timezone.utc).isoformat(),policy='oracle-policy-21',source_pairs_sha256=sha(source),script_sha256=sha(__file__),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),pairs=out,summary=dict(n_pairs=len(out),n_tasks=2*len(out),families=len({x['target']['dhatu']['code'] for x in out}),all_target_derivations_have_3_4_92=True,all_present_derivations_lack_3_4_92=True,all_target_derivations_lack_listed_weak_changes=True,all_union_checks_pass=True),no_model_results_read=True,no_paid_calls=True)
 (OUT/'supply-derivation-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 # Negative person controls: same six-class roots, third-person dual imperative.
 codes=['02.0006','03.0005','03.0009','05.0005','07.0007','08.0002','09.0014','09.0008']
 neg=[]
 for code in codes:
  t=make_task(E[code],'development',dict(lakara='Lot',prayoga='Kartari',purusha='Prathama',vacana='Dvi'))
  x=audit(t);assert all(not z['has_pit_rule'] for z in x['paths']);neg.append(x)
 (OUT/'negative-person-controls.json').write_text(json.dumps(neg,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report['summary']))
 if a.panel:
  tasks=json.loads(a.panel.read_text());validate(tasks,'development');z=[audit(t) for t in tasks]
  counts=Counter(t['morphology']['lakara'] for t in tasks)
  assert len(tasks)==96 and counts=={'Lot':48,'Lat':16,'Lan':16,'VidhiLin':16}
  by={}
  for t in tasks:by.setdefault(t['campaign']['root_family'],[]).append(t)
  assert len(by)==48 and all(len(v)==2 for v in by.values())
  for ts in by.values():
   assert len({t['dhatu']['code'] for t in ts})==1
   assert len({(t['morphology']['prayoga'],t['morphology']['purusha'],t['morphology']['vacana']) for t in ts})==1
   assert sum(t['morphology']['lakara']=='Lot' for t in ts)==1
  result=dict(created_at=datetime.now(timezone.utc).isoformat(),panel_path=str(a.panel),panel_sha256=sha(a.panel),n=96,families=48,lakara_counts=dict(counts),regeneration_and_validator_pass=True,pada_union_pass=True,pair_contract_pass=True,audit=z,no_model_results_read=True,no_paid_calls=True)
  (OUT/'panel-regeneration-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Panel passed',result['panel_sha256'])
if __name__=='__main__':main()
