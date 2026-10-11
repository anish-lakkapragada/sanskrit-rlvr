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
    occupied=defaultdict(Counter)
    for i,c,e in ce:
        k=e[3]-e[1]
        if k:occupied[i][c]+=k
    pair_cells=Counter()
    for counts in occupied.values():
        cells=sorted(counts)
        for a,c in enumerate(cells):
            if counts[c]>1:pair_cells[(c,c)]+=counts[c]*(counts[c]-1)//2
            for d in cells[a+1:]:pair_cells[(c,d)]+=counts[c]*counts[d]
    o['cell_counts']=quota
    o['unordered_within_family_cell_pair_counts']=[{'cell_a':c,'cell_b':d,'pairs':k} for (c,d),k in sorted(pair_cells.items())]
    # All masks remain full; with family cap<=9 each occupied exact grammar
    # cell can receive unique PN pairs and globally cyclic balanced assignment.
    assert all(m==511 for row in rows for m in row['eligible_person_number_masks'].values()) and all(e[3]-e[1]<=9 for _,_,e in ce)
    o.update(distinct_families=sum(loads.values()),family_load_histogram=dict(loads),family_pair_correlation_multiplier=factor,
       aorist_family_load_histogram=dict(lloads),distinct_aorist_families=sum(lloads.values()),
       repeated_aorist_questions_beyond_one_per_family=sum((k-1)*v for k,v in lloads.items()),
       families_with_repeated_aorists=sum(v for k,v in lloads.items() if k>1),
       aorist_by_recipe={r:{'questions':sum(c.values()),'families':len(c),'load_histogram':dict(Counter(c.values()))} for r,c in pc.items()},
       se_pp_by_accuracy_and_assumed_rho={str(pr):{str(rho):100*math.sqrt(pr*(1-pr)/n*(1+factor*rho)) for rho in [0,.05,.1,.2,.3,.5]} for pr in [.8,.7,.65,.5]},
       largest_rho_for_sub1pp_by_accuracy={str(pr):(.0001*n/(pr*(1-pr))-1)/factor for pr in [.8,.7,.65,.5]},
       balanced_PN_supply=True,PN_proof='Every eligible exact family/recipe/tense/voice cell has nine PN options and carries at most nine assignments. Assign consecutive cyclic PN options within each occupied cell group, carrying the global counter between groups: each group stays unique and total PN counts differ by at most one.',
       objective='Maximize distinct families, then minimize repeated lakaras, then minimize sum of squared family loads; only Lun may repeat.',no_final_membership_exported=True)
    return o
