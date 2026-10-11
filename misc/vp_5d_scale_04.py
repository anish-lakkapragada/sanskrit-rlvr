"""Policy08 supply census and family-load sensitivity; no model results or release membership."""
from __future__ import annotations
import json
import time
from collections import Counter,defaultdict
from misc.vp_5d_prepare_04 import OUT,ROOT,RECIPES,status,atomic_json,now,sha
from misc.vp_5d_prepare_03 import lexical_issue,task_for
from misc.vp_5d_pilot import SPLIT
from misc import vp_campaign_candidates as old
from misc.vp_cartesian_task import oracle_issue
from misc.vp_5d_scale_03 import PN
from vidyut.prakriya import Vyakarana,Pada,Sanadi,Lakara,Prayoga,Purusha,Vacana

def main():
    path=OUT/'pilot-04.scale-supply.json'
    if path.exists():raise RuntimeError('Preserve policy08 census')
    p=json.loads((OUT/'pilot-04.plan.json').read_text());assignment=json.loads(SPLIT.read_text())['families'];es={};rl={}
    for e in old.load_entries():
        split=assignment[old.family(e)]['split']
        if split=='test':es.setdefault(old.family(e),e)
        elif split=='rl_train':rl.setdefault(old.family(e),e)
    v=Vyakarana();bases={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in es.items()}
    rows=[];reject=Counter();accepted=attempted=0;start=time.monotonic()
    for ix,(family,e) in enumerate(es.items(),1):
        masks={}
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
                    probe={'dhatu':{'code':e.code},'morphology':dict(lakara=la,prayoga=voice,purusha=pu,vacana=va),'campaign':{'trace_rule_ids':list(rules)},'derivation':{'sanadi':ops}}
                    issue=oracle_issue(probe)
                    if issue:reject['tuple:'+issue]+=1;continue
                    mask|=1<<bit;accepted+=1
                if mask:masks[cell]=mask
        rows.append({'family':family,'gana':old.name(e.dhatu.gana),'eligible_person_number_masks':masks})
        if ix%100==0:
            status('Updating policy08 supply census',f'Assessed {ix}/1000 reserved test families for input availability only; {accepted:,} eligible tuples so far. No test model answers or final membership read or selected.')
            print(json.dumps({'families':ix,'accepted':accepted,'elapsed_seconds':round(time.monotonic()-start,1)}),flush=True)
    rb={f:sorted({x.text for x in v.derive(e.dhatu)}) for f,e in rl.items()}
    rlc={r:sum(task_for(e,r,dict(lakara='Lat',prayoga='Kartari',purusha='Prathama',vacana='Eka'),rb,'rl_train')[0] is not None for e in rl.values()) for r in RECIPES}
    summary={}
    for r in RECIPES:
        rr=[row for row in rows if any(c.startswith(r+'|') for c in row['eligible_person_number_masks'])]
        summary[r]={'families':len(rr),'tuples':sum(m.bit_count() for row in rr for c,m in row['eligible_person_number_masks'].items() if c.startswith(r+'|')),'gana_families':dict(Counter(row['gana'] for row in rr))}
    data={'created_at':now(),'policy':'oracle-policy-08','rows':rows,'recipe_supply':summary,'attempted_tuples':attempted,'accepted_tuples':accepted,
      'rejections':dict(reject),'rl_training':{'reserved_families':len(rl),'eligible_families_in_present_active_probe':rlc},
      'family_split_sha256':sha(SPLIT),'dictionary_sha256':sha(old.TSV),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
      'no_model_results_read':True,'no_gold_forms_retained':True,'no_final_membership_selected':True}
    atomic_json(path,data)
    # Reuse reviewed flow implementation with only explicitly changed weights.
    import misc.vp_5d_scale_03 as cap
    import misc.vp_5d_balance_03 as bal
    cap.WEIGHTS=Counter(p['cell_counts']);cap.GANAS=p['gana_counts'];bal.WEIGHTS=cap.WEIGHTS;bal.GANAS=cap.GANAS
    designs=[];checks=[]
    for n in [1660,2000,2400]:
        for strict in [True,False]:
            for limit in range(1,7):
                result=cap.capacity(rows,n,limit,strict);checks.append(result)
                if result['feasible']:
                    result=bal.balanced(rows,n,limit,strict);result['class_weights']='pilot04' if strict else 'relaxed';designs.append(result);break
    analysis={'created_at':now(),'supply_sha256':sha(path),'policy':'oracle-policy-08','recipe_supply':summary,'accepted_tuples':accepted,'rl_training':data['rl_training'],
      'capacity_checks':checks,'balanced_designs':designs,
      'precision_caveat':'Assumed constant79% Bernoulli variance and common within-family correlation. These are sensitivity calculations, not measured cluster SE; 480 development questions cannot prove sub1pp release precision.',
      'all_person_number_masks_full':all(m==511 for row in rows for m in row['eligible_person_number_masks'].values()),
      'no_final_membership_selected':True,'no_model_results_read':True}
    atomic_json(OUT/'pilot-04.scale-analysis.json',analysis);print(json.dumps({'supply':summary,'designs':designs},indent=2))

if __name__=='__main__':main()
