"""Unpaid development novelty/supply census. Does not select task membership."""
import json,time
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,RECIPES,atomic_json,now,sha,status
from misc.vp_5d_prepare_03 import SOURCE_ROOTS,lexical_issue
from misc.vp_5d_prepare_05 import UNRESOLVED,history
from misc.vp_5d_pilot import SPLIT
from misc.vp_5d_scale_03 import PN
from misc import vp_campaign_candidates as old
from misc.vp_cartesian_task import oracle_issue
from vidyut.prakriya import Vyakarana,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana
EXPECTED='86a9e2dce069a8fdb64c8c8e359120d499a60c4d4d5e1f926f0b51199f4474a5'
def main():
 out=OUT/'development-confirmation-policy17.supply.json';assert not out.exists();assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 assignment=json.loads(SPLIT.read_text())['families'];es={}
 for e in old.load_entries():
  if assignment[old.family(e)]['split']=='development':es.setdefault(old.family(e),e)
 used,hf,ha=history();v=Vyakarana();bases={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in es.items()};plan=json.loads((OUT/'pilot-06.revision-01.plan.json').read_text());rows=[];reject=Counter();eligible=novel=0;start=time.monotonic()
 for ix,(f,e) in enumerate(es.items(),1):
  masks={};allmasks={}
  if e.code not in set(SOURCE_ROOTS)|set(UNRESOLVED):
   for rec,ops in RECIPES.items():
    why=lexical_issue(e,rec,bases)
    if why:reject[why]+=1;continue
    d=e.dhatu.with_sanadi([getattr(Sanadi,x) for x in ops])
    for c in plan['cell_counts']:
     r,la,vo=c.split('|')
     if r!=rec:continue
     mask=allmask=0
     for bit,(pu,va) in enumerate(PN):
      ps=v.derive(Pada.Tinanta(dhatu=d,lakara=getattr(Lakara,la),prayoga=getattr(Prayoga,vo),purusha=getattr(Purusha,pu),vacana=getattr(Vacana,va)))
      if not ps or len({x.text for x in ps})>64:continue
      probe=dict(dhatu={'code':e.code},morphology=dict(lakara=la,prayoga=vo,purusha=pu,vacana=va),campaign={'trace_rule_ids':list({h.code for x in ps for h in x.history if old.name(h.source)=='Ashtadhyayi'})},derivation={'sanadi':ops},gold_slp1=sorted({x.text for x in ps}))
      why=oracle_issue(probe)
      if why:reject[why]+=1;continue
      allmask|=1<<bit;eligible+=1
      if (e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(ops),la,vo,pu,va) not in used:mask|=1<<bit;novel+=1
     if mask:masks[c]=mask
     if allmask:allmasks[c]=allmask
  rows.append(dict(family=f,code=e.code,gana=old.name(e.dhatu.gana),previously_exposed=f in hf,eligible_person_number_masks=masks,eligible_before_novelty_masks=allmasks))
  if ix%100==0:print(json.dumps(dict(families=ix,novel=novel,seconds=round(time.monotonic()-start,1))),flush=True)
 assert len(es)==700 and sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 data=dict(created_at=now(),policy='oracle-policy-17',adapter_sha256=EXPECTED,policy_sha256=sha(OUT.parent/'oracle-policy-17.json'),master_development_families=len(es),unexposed_family_count=len(set(es)-hf),unexposed_families=sorted(set(es)-hf),eligible_families=sum(bool(r['eligible_person_number_masks']) for r in rows),eligible_tuples=eligible,novel_tuples=novel,previous_tuple_overlap=eligible-novel,rows=rows,rejections=dict(reject),historical_inputs=ha,source_controls_excluded=sorted(SOURCE_ROOTS),unresolved_excluded=UNRESOLVED,no_model_results_read=True,no_paid_calls=True,no_task_membership_selected=True)
 atomic_json(out,data);print(json.dumps({k:data[k] for k in ['master_development_families','unexposed_family_count','eligible_families','eligible_tuples','novel_tuples','previous_tuple_overlap']},indent=2))
if __name__=='__main__':main()
