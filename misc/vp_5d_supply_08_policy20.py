"""Unpaid aggregate availability/allocation witnesses for two grammar proposals.

No question IDs, prompts, forms, or final membership are generated.
"""
import json,random
from collections import Counter,defaultdict
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_5d_candidate_4800_p18 import ProgressFlow
from misc.vp_5d_release_feasibility import Dinic
from misc.vp_5d_history_18 import history
from misc.vp_5d_pilot import SPLIT
from misc import vp_campaign_candidates as old

P=OUT/'pilot-08-proposal-policy20';PN=[(pu,va) for pu in ['Prathama','Madhyama','Uttama'] for va in ['Eka','Dvi','Bahu']]
def read(p):return json.loads(p.read_text())

def dev_rows():
    supply=read(OUT/'development-confirmation-policy20.supply.json');used,hf,ha=history();es={old.family(e):e for e in old.load_entries()};rows=[]
    recipes=read(OUT/'pilot-07/revision-01/plan.json')['recipe_operations']
    for row in supply['rows']:
        e=es[row['family']];masks={}
        for c,m in row['eligible_before_novelty_masks'].items():
            rec,la,vo=c.split('|');new=0
            for i,(pu,va) in enumerate(PN):
                if m&(1<<i) and (e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(recipes[rec]),la,vo,pu,va) not in used:new|=1<<i
            if new:masks[c]=new
        rows.append(dict(family=row['family'],gana=row['gana'],eligible_person_number_masks=masks))
    return rows,dict(source_sha256=sha(OUT/'development-confirmation-policy20.supply.json'),historical_inputs=ha,eligible_novel_tuples=sum(m.bit_count() for r in rows for m in r['eligible_person_number_masks'].values()),eligible_families=sum(bool(r['eligible_person_number_masks']) for r in rows),all_prior07_tuples_excluded=True)

def allocate(rows,plan,n,scope,name):
    scale=n/2400;target={c:round(q*scale) for c,q in plan['cell_counts'].items()};classes={c:round(q*scale) for c,q in plan['gana_counts'].items()};assert sum(target.values())==sum(classes.values())==n
    cap,lcap=(8,5) if n<=4800 else (10,6);rng=random.Random('vp-five-d-pilot08-aggregate-witness:'+name+':'+scope+':'+str(n));rr=sorted(rows,key=lambda r:r['family']);rng.shuffle(rr)
    net=ProgressFlow();edges=[];medium=n*cap*cap+1;large=n*(medium+cap*cap)+1
    for g in sorted(classes):net.edge('s',('g',g),classes[g])
    for i,row in enumerate(rr):
        net.edge(('g',row['gana']),('f',i),1)
        for j in range(2,cap+1):net.edge(('g',row['gana']),('f',i),1,large+2*j-1)
        masks=row['eligible_person_number_masks'];las=sorted({c.split('|')[1] for c in masks});rng.shuffle(las)
        for la in las:
            net.edge(('f',i),('fl',i,la),1)
            for k in range(2,(lcap if la=='Lun' else 1)+1):net.edge(('f',i),('fl',i,la),1,medium)
        cc=sorted(masks);rng.shuffle(cc)
        for c in cc:edges.append((i,c,net.edge(('fl',i,c.split('|')[1]),('c',c),min(cap,masks[c].bit_count()))))
    for c in sorted(target):net.edge(('c',c),'t',target[c])
    flow,cost=net.flow('s','t',n)
    if flow<n:return dict(feasible=False,flow=flow,n=n,scope=scope)
    occ=defaultdict(Counter)
    for i,c,e in edges:
        if e[3]-e[1]:occ[i][c]+=e[3]-e[1]
    loads=Counter(sum(x.values()) for x in occ.values());g=len(occ);lf=sum(any('|Lun|' in c for c in x) for x in occ.values());repeat=sum(q for c,q in target.items() if '|Lun|' in c)-lf;ssq=sum(k*k*v for k,v in loads.items());assert cost==large*(n-g)+medium*repeat+ssq-g
    # A separate integral matching checks exact balanced PN without selecting or saving tasks.
    pn=Dinic();pnedge=[]
    for i,cc in occ.items():
        for c,q in cc.items():
            node=('fc',i,c);pn.edge('s',node,q)
            for bit in range(9):
                if rr[i]['eligible_person_number_masks'][c]&(1<<bit):pnedge.append(pn.edge(node,('fp',i,bit),1))
        for bit in range(9):pn.edge(('fp',i,bit),('pn',bit),1 if cap<=9 else cap)
    base=n//9;extra=n%9;extra_bits={0,4,8} if extra==3 else {1,2,3,5,6,7} if extra==6 else set()
    for bit in range(9):pn.edge(('pn',bit),'t',base+int(bit in extra_bits))
    pnflow=pn.flow('s','t');assert pnflow==n,'Exact balanced fresh-PN matching failed'
    pairs=Counter();lh=Counter();sanh=Counter();cross=Counter()
    for cc in occ.values():
        slots=[c for c,q in cc.items() for _ in range(q)];lh[sum('|Lun|' in c for c in slots)]+=1;sanh[sum(c.startswith('desiderative|') for c in slots)]+=1
        for i,c in enumerate(slots):
            for d in slots[i+1:]:pairs[tuple(sorted((c,d)))]+=1;cross[tuple(sorted((c.split('|')[0],d.split('|')[0])))]+=1
    return dict(feasible=True,n=n,scope=scope,cell_counts=target,gana_counts=classes,distinct_families=g,family_cap=cap,aorist_per_family_cap=lcap,maximum_each_other_lakara=1,family_load_histogram=dict(loads),aorist_load_histogram=dict(lh),san_load_histogram=dict(sanh),distinct_aorist_families=lf,repeated_aorist_questions_beyond_one_per_family=repeat,sum_squared_family_loads=ssq,family_pair_correlation_multiplier=ssq/n-1,objective=[g,repeat,ssq],exact_balanced_PN_matching_passed=True,unique_PN_per_family=cap<=9,unordered_within_family_cell_pair_counts=[dict(cell_a=a,cell_b=b,pairs=q) for (a,b),q in sorted(pairs.items())],unordered_within_family_recipe_pair_counts=[dict(recipe_a=a,recipe_b=b,pairs=q) for (a,b),q in sorted(cross.items())],family_gana_counts=dict(Counter(rr[i]['gana'] for i in occ)),task_membership_generated=False,only_aggregate_witness=True)

def main():
    assert sha(ROOT/'misc/vp_cartesian_task.py')=='a7908917f2f5a711a29d116ce314467d807c8418581644b6ece27423c6753d08'
    dev,da=dev_rows();test=read(OUT/'pilot-06.scale-supply-policy20.json')['rows'];atomic_json(P/'fresh-development-supply-summary.json',da)
    summary={}
    for name in ['san20_lun45_fullcoverage']:
        plan=read(P/(name+'.quota-proposal.json'));summary[name]={}
        for scope,rows,n in [('development',dev,2400),('test',test,4800)]:
            status('Checking revised-mixture supply',f'Input-only aggregate allocation for {name}: {n} {scope} forms, exact joint/class margins, same coverage/repetition/load priorities. No prompts or final membership generated.')
            result=allocate(rows,plan,n,scope,name);summary[name][scope]=result;atomic_json(P/(name+f'.{scope}-N{n}.allocation.json'),result)
            print(json.dumps(dict(variant=name,scope=scope,**{k:result.get(k) for k in ['feasible','n','distinct_families','objective','family_pair_correlation_multiplier','exact_balanced_PN_matching_passed']})),flush=True)
    atomic_json(P/'allocation-summary.json',dict(created_at=now(),policy='oracle-policy-20',adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),variants=summary,no_task_membership_generated=True,no_answers_used_for_allocation=True,paid_calls=0))

if __name__=='__main__':main()
