"""Policy19 full supply census and family-load sensitivity; no model results or release membership."""
from __future__ import annotations
import json
import time
from collections import Counter,defaultdict
from misc.vp_5d_prepare_04 import OUT,ROOT,RECIPES,status,atomic_json,now,sha
from misc.vp_5d_prepare_03 import lexical_issue,task_for,SOURCE_ROOTS
from misc.vp_5d_prepare_05 import UNRESOLVED
from misc.vp_5d_pilot import SPLIT
from misc import vp_campaign_candidates as old
from misc.vp_cartesian_task import oracle_issue
from misc.vp_5d_scale_03 import PN
from vidyut.prakriya import Vyakarana,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana

def main():
    path=OUT/'pilot-06.scale-supply-policy19.json'
    if path.exists():raise RuntimeError('Preserve policy19 census')
    assert sha(ROOT/'misc/vp_cartesian_task.py')=='f04e9fa535784bd0318d6a5bef38ccf024c240c444af0f1c771221e94262f838'
    p=json.loads((OUT/'pilot-06.revision-01.plan.json').read_text());assignment=json.loads(SPLIT.read_text())['families'];es={};rl={}
    for e in old.load_entries():
        split=assignment[old.family(e)]['split']
        if split=='test':es.setdefault(old.family(e),e)
        elif split=='rl_train':rl.setdefault(old.family(e),e)
    v=Vyakarana();bases={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in es.items()}
    rows=[];reject=Counter();accepted=attempted=0;start=time.monotonic()
    for ix,(family,e) in enumerate(es.items(),1):
        masks={}
        if e.code in SOURCE_ROOTS or e.code in UNRESOLVED:
            rows.append({'family':family,'gana':old.name(e.dhatu.gana),'eligible_person_number_masks':{}});reject['prospective_source_hold']+=1;continue
        for recipe,ops in RECIPES.items():
            issue=lexical_issue(e,recipe,bases)
            if issue:reject['family_recipe:'+issue]+=1;continue
            d=e.dhatu.with_sanadi([getattr(Sanadi,x) for x in ops])
            for cell in p['cell_counts']:
                rec,la,voice=cell.split('|')
                if rec!=recipe:continue
                mask=0
                for bit,(pu,va) in enumerate(PN):
                    attempted+=1;ps=v.derive(Pada.Tinanta(dhatu=d,lakara=getattr(Lakara,la),prayoga=getattr(Prayoga,voice),purusha=getattr(Purusha,pu),vacana=getattr(Vacana,va)))
                    if not ps:reject['empty_engine_derivation']+=1;continue
                    if len({x.text for x in ps})>64:reject['more_than64variants']+=1;continue
                    rules={h.code for x in ps for h in x.history if old.name(h.source)=='Ashtadhyayi'}
                    probe={'dhatu':{'code':e.code},'morphology':dict(lakara=la,prayoga=voice,purusha=pu,vacana=va),'campaign':{'trace_rule_ids':list(rules)},'derivation':{'sanadi':ops},'gold_slp1':sorted({x.text for x in ps})}
                    issue=oracle_issue(probe)
                    if issue:reject['tuple:'+issue]+=1;continue
                    mask|=1<<bit;accepted+=1
                if mask:masks[cell]=mask
        rows.append({'family':family,'gana':old.name(e.dhatu.gana),'eligible_person_number_masks':masks})
        if ix%100==0:
            status('Updating policy19 supply census',f'Assessed {ix}/1000 reserved test families for input availability only; {accepted:,} eligible tuples so far. No model answers read and no final membership approved.')
            print(json.dumps({'families':ix,'accepted':accepted,'elapsed_seconds':round(time.monotonic()-start,1)}),flush=True)
    rb={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in rl.items()}
    rlc={r:sum(task_for(e,r,dict(lakara='Lat',prayoga='Kartari',purusha='Prathama',vacana='Eka'),rb,'rl_train')[0] is not None for e in rl.values()) for r in RECIPES}
    summary={}
    for r in RECIPES:
        rr=[row for row in rows if any(c.startswith(r+'|') for c in row['eligible_person_number_masks'])]
        summary[r]={'families':len(rr),'tuples':sum(m.bit_count() for row in rr for c,m in row['eligible_person_number_masks'].items() if c.startswith(r+'|')),'gana_families':dict(Counter(row['gana'] for row in rr))}
    data={'created_at':now(),'policy':'oracle-policy-19','rows':rows,'recipe_supply':summary,'attempted_tuples':attempted,'accepted_tuples':accepted,
      'rejections':dict(reject),'rl_training':{'reserved_families':len(rl),'eligible_families_in_present_active_probe':rlc},
      'family_split_sha256':sha(SPLIT),'dictionary_sha256':sha(old.TSV),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
      'prospective_source_holds':UNRESOLVED,'source_control_codes_excluded':sorted(SOURCE_ROOTS),'no_model_results_read':True,'no_gold_forms_retained':True,'no_final_membership_approved':True,'census_only_no_membership_selected_in_this_step':True,'source_policy_sha256':sha(OUT.parent/'oracle-policy-19.json')}
    assert sha(ROOT/'misc/vp_cartesian_task.py')=='f04e9fa535784bd0318d6a5bef38ccf024c240c444af0f1c771221e94262f838'
    atomic_json(path,data)
    print(json.dumps({"accepted_tuples":accepted,"recipe_supply":summary,"rl":data["rl_training"]},indent=2))

if __name__=="__main__":main()
