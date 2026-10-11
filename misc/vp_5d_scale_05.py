"""Aggregate fixed-distribution witnesses with explicit repeated-lakara costs."""
from __future__ import annotations
import json,math
from collections import Counter,defaultdict
from misc.vp_5d_prepare_04 import OUT,ROOT,status,atomic_json,now,sha
from misc.vp_5d_release_feasibility import MinCost,Dinic,apportion
from misc import vp_campaign_candidates as old

def witness(rows,p,n,cap,lcap,optimize):
    quota=apportion(p['cell_counts'],n);gq=apportion(p['gana_counts'],n)
    net=MinCost() if optimize else Dinic();fe={};le={};ce=[]
    medium=n*cap*cap+1;large=n*(medium+cap*cap)+1
    for g,q in gq.items():net.edge('s',('g',g),q)
    for i,row in enumerate(rows):
        f=('f',i);g=('g',row['gana'])
        fe[i]=([net.edge(g,f,1,0)]+[net.edge(g,f,1,large+2*j-1) for j in range(2,cap+1)]) if optimize else [net.edge(g,f,cap)]
        las=sorted({c.split('|')[1] for c in row['eligible_person_number_masks'] if c in quota})
        for la in las:
            lc=lcap if la=='Lun' else 1;fl=('fl',i,la)
            le[(i,la)]=([net.edge(f,fl,1,0)]+[net.edge(f,fl,1,medium) for j in range(2,lc+1)]) if optimize else [net.edge(f,fl,lc)]
        for c,mask in row['eligible_person_number_masks'].items():
            if c in quota:ce.append((i,c,net.edge(('fl',i,c.split('|')[1]),('c',c),min(cap,mask.bit_count()))))
    for c,q in quota.items():net.edge(('c',c),'t',q)
    flow=net.flow('s','t',n)[0] if optimize else net.flow('s','t')
    o={'n':n,'family_cap':cap,'aorist_per_family_cap':lcap,'non_aorist_same_lakara_per_family_cap':1,'feasible':flow==n,'maximum_allocatable':flow}
    if flow!=n:return o
    loads=Counter(sum(e[3]-e[1] for e in es) for es in fe.values());loads.pop(0,None)
    lloads=Counter(sum(e[3]-e[1] for e in es) for (i,la),es in le.items() if la=='Lun');lloads.pop(0,None)
    factor=sum(k*k*v for k,v in loads.items())/n-1
    pc=defaultdict(Counter)
    for i,c,e in ce:
        k=e[3]-e[1]
        if k and '|Lun|' in c:pc[c.split('|')[0]][i]+=k
    # All masks remain full; with family cap<=9 each occupied exact grammar
    # cell can receive unique PN pairs and globally cyclic balanced assignment.
    assert all(m==511 for row in rows for m in row['eligible_person_number_masks'].values()) and cap<=9
    o.update(distinct_families=sum(loads.values()),family_load_histogram=dict(loads),family_pair_correlation_multiplier=factor,
       aorist_family_load_histogram=dict(lloads),distinct_aorist_families=sum(lloads.values()),
       repeated_aorist_questions_beyond_one_per_family=sum((k-1)*v for k,v in lloads.items()),
       families_with_repeated_aorists=sum(v for k,v in lloads.items() if k>1),
       aorist_by_recipe={r:{'questions':sum(c.values()),'families':len(c),'load_histogram':dict(Counter(c.values()))} for r,c in pc.items()},
       se_pp_by_accuracy_and_assumed_rho={str(pr):{str(rho):100*math.sqrt(pr*(1-pr)/n*(1+factor*rho)) for rho in [0,.05,.1,.2,.3,.5]} for pr in [.8,.7,.65,.5]},
       largest_rho_for_sub1pp_by_accuracy={str(pr):(.0001*n/(pr*(1-pr))-1)/factor for pr in [.8,.7,.65,.5]},
       balanced_PN_supply=True,PN_proof=f'Every eligible exact grammar cell has nine PN options; the maximum family load is{cap}, so cyclic global assignment yields balanced PN counts and distinct tuples.',
       objective='Maximize distinct families, then minimize repeated lakaras, then minimize sum of squared family loads; only Lun may repeat.',no_final_membership_exported=True)
    return o

def main():
    source=OUT/'pilot-04.scale-supply.json';raw=json.loads(source.read_text());p=json.loads((OUT/'pilot-05.plan.json').read_text())
    hold_codes=set(p['unresolved_prospective_exclusions']);hold_families={old.family(e) for e in old.load_entries() if e.code in hold_codes}
    rows=[r for r in raw['rows'] if r['family'] not in hold_families]
    checks=[];designs=[]
    for n in [2400,2880,3360,3840]:
        found=None
        # Lexicographically minimize family cap, then aorist cap within that cap;
        # report the price rather than silently allowing repeated non-aorists.
        for cap in range(3,10):
            for lcap in range(1,cap+1):
                r=witness(rows,p,n,cap,lcap,False);checks.append(r)
                if r['feasible']:found=(cap,lcap);break
            if found:break
        if not found:raise RuntimeError('No constrained witness for '+str(n))
        status('Quantifying repeated-aorist release supply',f'Optimizing an aggregate {n:,}-question witness at family cap{found[0]}, aorist cap{found[1]}, and no repeated other tense. No final membership or model answers are selected.')
        r=witness(rows,p,n,*found,True);designs.append(r);print(json.dumps(r),flush=True)
    rsets={recipe:{r['family'] for r in rows if recipe+'|Lun|Kartari' in r['eligible_person_number_masks']} for recipe in p['recipe_counts']}
    out={'created_at':now(),'policy':'oracle-policy-11 plus prospective stim/urja source holds','supply_sha256':sha(source),'policy11_provenance_sha256':sha(OUT/'pilot-04.scale-policy11-addendum.json'),'candidate_plan_sha256':sha(OUT/'pilot-05.plan.json'),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
      'additional_test_families_held':sorted(hold_families&{r['family'] for r in raw['rows']}),
      'aorist_supply_by_recipe':{r:len(f) for r,f in rsets.items()},'nested_aorist_union_families':len(set.union(*(f for r,f in rsets.items() if r!='desiderative'))),
      'capacity_checks':checks,'balanced_designs':designs,
      'limitations':['These aggregate availability witnesses are not final membership and are not nested panels.',
        'SE sensitivities assume a common family correlation and constant Bernoulli variance, not measured final cluster SE. Check both references; Astra may have higher variance than Opus.',
        'The two-distinct-tense pilot dependence cannot be transferred to families with repeated aorists without evidence.',
        'Family means are exact dictionary citation plus gana, not etymological independence. Separate RL families remain reserved.'],
      'no_heldout_model_answers_read':True,'no_final_membership_selected':True,'benchmark_ready':False}
    atomic_json(OUT/'pilot-05.scale-analysis.json',out)

if __name__=='__main__':main()
