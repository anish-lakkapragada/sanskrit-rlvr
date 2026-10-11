"""Safely update policy20 mask census for the single new-san trace predicate."""
import json,time
from copy import deepcopy
from collections import Counter
from misc.vp_5d_prepare_04 import ROOT,OUT,sha,now,atomic_json,status
from misc.vp_cartesian_task import entries_by_code,oracle_issue
from vidyut.prakriya import Vyakarana,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana
from misc import vp_campaign_candidates as old
EXPECTED='f5bfab6f3fc27b7c83bbd6987bede73501592a9568fda32a0371bd8e23b7febd'
PN=[(p,v) for p in ['Prathama','Madhyama','Uttama'] for v in ['Eka','Dvi','Bahu']]
def read(p):return json.loads(p.read_text())
def main():
 assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED;es=entries_by_code();ef={}
 for e in old.load_entries():ef.setdefault(old.family(e),e)
 v=Vyakarana();reports=[];started=time.monotonic()
 for label,src,dest in [('development','development-confirmation-policy20.supply.json','development-confirmation-policy21.supply.json'),('test','pilot-06.scale-supply-policy20.json','pilot-06.scale-supply-policy21.json')]:
  prior=read(OUT/src)
  if (OUT/dest).exists():
   saved=read(OUT/dest);assert saved['policy']=='oracle-policy-21' and saved['prior_policy_source']['sha256']==sha(OUT/src)
   reports.append(dict(scope=label,source_sha256=sha(OUT/src),output_sha256=sha(OUT/dest),checked=saved['policy21_mask_update']['all_prior_eligible_san_tuples_rederived'],removed=saved['policy21_mask_update']['removed'],preserved_completed_scope=True));continue
  d=deepcopy(prior);removed=[];checked=0
  for row in d['rows']:
   masks=row.get('eligible_before_novelty_masks',row['eligible_person_number_masks']);entry=es[row['code']] if 'code' in row else ef[row['family']];dhatu=entry.dhatu.with_sanadi([Sanadi.san])
   for cell,mask in list(masks.items()):
    rec,la,vo=cell.split('|')
    if rec!='desiderative':continue
    badmask=0
    for bit,(pu,va) in enumerate(PN):
     if not mask&(1<<bit):continue
     checked+=1;ps=v.derive(Pada.Tinanta(dhatu=dhatu,lakara=getattr(Lakara,la),prayoga=getattr(Prayoga,vo),purusha=getattr(Purusha,pu),vacana=getattr(Vacana,va)))
     rules={h.code for p in ps for h in p.history if old.name(h.source)=='Ashtadhyayi'}
     if '7.4.7' in rules:badmask|=1<<bit
    if badmask:
     removed.append(dict(code=entry.code,family=row['family'],cell=cell,removed_mask=badmask,removed_tuples=badmask.bit_count()))
     for field in ['eligible_person_number_masks','eligible_before_novelty_masks']:
      if field in row and cell in row[field]:
       row[field][cell]&=~badmask
       if not row[field][cell]:del row[field][cell]
  d.update(created_at=now(),policy='oracle-policy-21',prior_policy_source=dict(path=str(OUT/src),sha256=sha(OUT/src)),policy21_mask_update=dict(single_new_predicate='operations exactly[san] and trace7.4.7',all_prior_eligible_san_tuples_rederived=checked,removed=removed,non_san_masks_unchanged=True,prior_shapes_and_scope_unchanged=True))
  if label=='development':
   d.update(adapter_sha256=EXPECTED,policy_sha256=sha(OUT.parent/'oracle-policy-21.json'),eligible_tuples=sum(m.bit_count() for r in d['rows'] for m in r['eligible_before_novelty_masks'].values()),novel_tuples=sum(m.bit_count() for r in d['rows'] for m in r['eligible_person_number_masks'].values()),eligible_families=sum(bool(r['eligible_person_number_masks']) for r in d['rows']))
   d['previous_tuple_overlap']=d['eligible_tuples']-d['novel_tuples']
  else:
   d.update(shared_adapter_sha256=EXPECTED,source_policy_sha256=sha(OUT.parent/'oracle-policy-21.json'),accepted_tuples=sum(m.bit_count() for r in d['rows'] for m in r['eligible_person_number_masks'].values()))
   for rec,info in d['recipe_supply'].items():
    rr=[r for r in d['rows'] if any(c.startswith(rec+'|') for c in r['eligible_person_number_masks'])];info.update(families=len(rr),tuples=sum(m.bit_count() for r in rr for c,m in r['eligible_person_number_masks'].items() if c.startswith(rec+'|')),gana_families=dict(Counter(r['gana'] for r in rr)))
  why='caN-conditioned r preservation applied inside a desiderative with outer sic';d['rejections'][why]=d['rejections'].get(why,0)+sum(x['removed_tuples'] for x in removed)
  atomic_json(OUT/dest,d);reports.append(dict(scope=label,source_sha256=sha(OUT/src),output_sha256=sha(OUT/dest),checked=checked,removed=removed));print(json.dumps(reports[-1]),flush=True)
 assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 atomic_json(OUT/'policy21-supply-mask-update.json',dict(created_at=now(),policy='oracle-policy-21',adapter_sha256=EXPECTED,reports=reports,seconds=time.monotonic()-started,method='Re-derive every previously eligible single-san tuple. Remove all-and-only newly quarantined7.4.7 traces. Retain non-san masks from hashed policy20 source; policy21 adds only this predicate.',no_answers_read=True,no_paid_calls=True))
if __name__=='__main__':main()
