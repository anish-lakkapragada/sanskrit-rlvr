"""Secondary family-load balancing for the frozen pilot03 grammar distribution."""
from __future__ import annotations
import json
import math
from collections import Counter
from misc.vp_5d_scale_03 import OUT,WEIGHTS,GANAS,MinCost,apportion,sha,now,atomic_json,status


def balanced(rows,n,cap,strict):
    quotas=apportion(WEIGHTS,n);gq=apportion(GANAS,n) if strict else None
    net=MinCost();source='source';sink='sink';edges={};family_ganas={}
    if gq:
        for g,q in gq.items():net.edge(source,('g',g),q)
    # Lexicographic objective: first maximize distinct families, then minimize sum(load^2).
    # A single repeat-family penalty exceeds the entire possible quadratic secondary cost.
    penalty=n*cap*cap+1
    for i,row in enumerate(rows):
        fn=('f',i);start=('g',row['gana']) if gq else source;family_ganas[i]=row['gana']
        edges[i]=[net.edge(start,fn,1,0)]+[net.edge(start,fn,1,penalty+2*j-1) for j in range(2,cap+1)]
        for c,mask in row['eligible_person_number_masks'].items():
            if c in quotas:net.edge(fn,('c',c),min(cap,mask.bit_count()))
    for c,q in quotas.items():net.edge(('c',c),sink,q)
    maximum,_=net.flow(source,sink,n);assert maximum==n
    loads=Counter();gana=Counter()
    for i,ee in edges.items():
        load=sum(e[3]-e[1] for e in ee)
        if load:loads[load]+=1;gana[family_ganas[i]]+=load
    factor=sum(k*k*v for k,v in loads.items())/n-1
    assert all(mask==511 for row in rows for mask in row['eligible_person_number_masks'].values()) and cap<=9
    return {'n':n,'family_cap':cap,'class_weights':'pilot03' if strict else 'relaxed',
        'distinct_families':sum(loads.values()),'family_load_histogram':dict(loads),'gana_counts':dict(gana),
        'maximum_gana_fraction':max(gana.values())/n,'family_pair_correlation_multiplier':factor,
        'se_pp_at79_by_assumed_intraclass_correlation':{str(rho):100*math.sqrt(.79*.21/n*(1+factor*rho)) for rho in [0,.05,.1,.2,.3,.5,1]},
        'largest_rho_compatible_with_se_below1pp':(.0001*n/(.79*.21)-1)/factor,
        'balanced_person_number_supply':True,
        'person_number_balance_proof':'Each nonempty family/recipe/tense/voice cell has all9 options and contributes at most4 tasks. Consecutive cyclic assignment across cell groups gives global PN counts differing by at most1 with no duplicate tuple.',
        'no_final_membership_exported':True}


def main():
    source=OUT/'pilot-03.scale-supply.json';data=json.loads(source.read_text());out=[]
    for n in [1660,2000,2400]:
        for strict in [True,False]:
            cap=3 if n==1660 or (n==2000 and not strict) else 4
            status('Balancing repeated families',f'Optimizing {n:,} questions with family cap {cap} and '+('fixed' if strict else 'relaxed')+' class weights; maximizing distinct families first, then reducing uneven loads.')
            row=balanced(data['rows'],n,cap,strict);out.append(row)
            print(json.dumps(row),flush=True)
    atomic_json(OUT/'pilot-03.balanced-scale-analysis.json',{'created_at':now(),
        'supply_sha256':sha(source),'script_sha256':sha(__import__('pathlib').Path(__file__)),
        'objective':'Lexicographically maximize distinct families then minimize sum of squared family loads under frozen recipe/tense/voice weights.',
        'designs':out,'precision_caveat':'Constant79% Bernoulli variance with a common assumed within-family correlation; these are design sensitivities, not measured cluster SE or a guarantee.',
        'no_heldout_model_answers_read':True,'no_final_membership_selected':True})


if __name__=='__main__':main()
