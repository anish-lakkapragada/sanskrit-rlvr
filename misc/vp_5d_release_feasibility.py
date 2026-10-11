"""Offline aggregate supply census; never selects a final benchmark."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import heapq
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_5d_pilot import OUT, RECIPES, LAKARAS, GANAS, EXCLUDED_RULES, SPLIT, lexical_checks, now, atomic_json, sha, slots
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Vacana, Sanadi, Vyakarana
import vidyut

RUN = 'release-feasibility-01'
PASSIVE_LAKARAS = {'Lat', 'Lan', 'Lot', 'VidhiLin', 'Lut', 'Lrt'}
CAUSAL = {'causative', 'causative_of_intensive', 'desiderative_of_causative_of_intensive'}
PN = list(itertools.product(['Prathama', 'Madhyama', 'Uttama'], ['Eka', 'Dvi', 'Bahu']))


def status(phase, message):
    atomic_json(OUT/'status.json', {'track':'five_d', 'run_id':RUN, 'updated_at':now(),
        'state':'running', 'phase':phase, 'message':message, 'benchmark_ready':False})
    with (OUT/'progress.md').open('a') as f:
        f.write(f'- {now()}: {message}\n')


def cell(recipe, lakara, prayoga):
    return '|'.join((recipe, lakara, prayoga))


def census():
    path = OUT/(RUN+'.supply.json')
    if path.exists():
        raise RuntimeError('Preserve the existing census; use the summarize command')
    start = time.monotonic()
    split = json.loads(SPLIT.read_text())['families']
    es = {}
    for e in old.load_entries():
        if split[old.family(e)]['split'] == 'test':
            es.setdefault(old.family(e), e)
    v = Vyakarana()
    bases = {f:sorted({p.text for p in v.derive(e.dhatu)}) for f,e in es.items()}
    rows, rejection, variants = [], Counter(), Counter()
    attempted, accepted = 0, 0
    for index,(family,e) in enumerate(es.items(),1):
        eligible = {}
        for recipe,spec in RECIPES.items():
            why = lexical_checks(e, recipe, bases)
            if why:
                rejection['family_recipe:'+why] += 1
                continue
            d = e.dhatu.with_sanadi([getattr(Sanadi,x) for x in spec['sanadi']])
            for la in LAKARAS:
                voices = ['Kartari'] + (['Karmani'] if recipe in CAUSAL and la in PASSIVE_LAKARAS else [])
                for voice in voices:
                    mask = 0
                    for bit,(pu,va) in enumerate(PN):
                        attempted += 1
                        ps = v.derive(Pada.Tinanta(dhatu=d, lakara=getattr(Lakara,la),
                            prayoga=getattr(Prayoga,voice), purusha=getattr(Purusha,pu),
                            vacana=getattr(Vacana,va)))
                        if not ps:
                            rejection['tuple:empty_engine_derivation'] += 1
                            continue
                        gold = {p.text for p in ps}
                        if len(gold)>64:
                            rejection['tuple:more_than_64_variants'] += 1
                            continue
                        if len(spec['sanadi'])>1 and any(h.code in EXCLUDED_RULES and old.name(h.source)=='Ashtadhyayi' for p in ps for h in p.history):
                            rejection['tuple:unresolved_nested_rule_context'] += 1
                            continue
                        if voice=='Karmani' and la in {'Lut','Lrt'} and {'6.4.62','6.4.92'} <= {h.code for p in ps for h in p.history if old.name(h.source)=='Ashtadhyayi'}:
                            rejection['tuple:unresolved_optional_cinvat_lengthening'] += 1
                            continue
                        mask |= 1<<bit
                        accepted += 1
                        variants[len(gold)] += 1
                    if mask:
                        eligible[cell(recipe,la,voice)] = mask
        rows.append({'family':family, 'gana':old.name(e.dhatu.gana), 'eligible_person_number_masks':eligible})
        if index%50==0:
            status('Enumerating grammatical supply', f'Assessed {index} of {len(es)} master test families; {accepted:,} valid tuples counted. Only aggregate availability is retained, with no gold forms or final membership.')
            print(json.dumps({'families':index,'accepted':accepted,'seconds':round(time.monotonic()-start,1)}),flush=True)
    data = {'created_at':now(),'run_id':RUN,'vp_version':vidyut.__version__,
        'family_split_sha256':sha(SPLIT),'dictionary_sha256':sha(old.TSV),
        'generator_sha256':sha(Path(__file__)),'master_test_families':len(es),
        'family_gana':dict(Counter(r['gana'] for r in rows)),
        'attempted_tuples_after_lexical_filters':attempted,'accepted_tuples':accepted,
        'rejections':dict(rejection),'variant_count_histogram':dict(variants),
        'person_number_bit_order':PN,'rows':rows,
        'scope':'Full master test pool; all six menu recipes, ten classical lakaras and nine person-number pairs; active throughout, passive only causal recipes in six declared lakaras.',
        'no_final_membership':True,'no_gold_forms_retained':True,'no_model_results_read':True,
        'elapsed_seconds':time.monotonic()-start}
    atomic_json(path,data)
    summarize()


class Dinic:
    def __init__(self):
        self.adj=defaultdict(list)
    def edge(self,u,v,c):
        a=[v,c,None,c];b=[u,0,a,0];a[2]=b
        self.adj[u].append(a);self.adj[v].append(b)
        return a
    def flow(self,s,t):
        total=0
        while True:
            depth={s:0};q=deque([s])
            while q:
                u=q.popleft()
                for v,c,_,_ in self.adj[u]:
                    if c and v not in depth:depth[v]=depth[u]+1;q.append(v)
            if t not in depth:return total
            it=defaultdict(int)
            def dfs(u,pushed):
                if u==t:return pushed
                while it[u]<len(self.adj[u]):
                    e=self.adj[u][it[u]];v,c,rev,_=e
                    if c and depth.get(v)==depth[u]+1:
                        f=dfs(v,min(pushed,c))
                        if f:e[1]-=f;rev[1]+=f;return f
                    it[u]+=1
                return 0
            while True:
                f=dfs(s,10**9)
                if not f:break
                total+=f


class MinCost:
    def __init__(self):
        self.adj=defaultdict(list)
    def edge(self,u,v,cap,cost=0):
        a=[v,cap,None,cap,cost];b=[u,0,a,0,-cost];a[2]=b
        self.adj[u].append(a);self.adj[v].append(b)
        return a
    def flow(self,s,t,limit):
        potential=defaultdict(int);flow=cost=serial=0
        while flow<limit:
            dist={s:0};parent={};heap=[(0,serial,s)];serial+=1
            while heap:
                du,_,u=heapq.heappop(heap)
                if du!=dist[u]:continue
                for e in self.adj[u]:
                    v,cap,_,_,c=e
                    if not cap:continue
                    nd=du+c+potential[u]-potential[v]
                    if nd<dist.get(v,math.inf):
                        dist[v]=nd;parent[v]=(u,e)
                        heapq.heappush(heap,(nd,serial,v));serial+=1
            if t not in dist:break
            for node,d in dist.items():potential[node]+=d
            aug=limit-flow;node=t
            while node!=s:
                prev,e=parent[node];aug=min(aug,e[1]);node=prev
            node=t
            while node!=s:
                prev,e=parent[node];e[1]-=aug;e[2][1]+=aug;cost+=aug*e[4];node=prev
            flow+=aug
        return flow,cost


def apportion(weights,n):
    total=sum(weights.values());out={k:(v*n)//total for k,v in weights.items()}
    for k in sorted(weights,key=lambda k:(-(weights[k]*n%total),k))[:n-sum(out.values())]:out[k]+=1
    return out


def capacity_check(rows,n,cap,gana_weights=None):
    weights=Counter(cell(s['recipe'],s['morphology']['lakara'],s['morphology']['prayoga']) for s in slots())
    quotas=apportion(weights,n)
    gq=apportion(gana_weights,n) if gana_weights else None
    net=Dinic();source='source';sink='sink';family_edges={};gana_of={}
    if gq:
        for g,q in gq.items():net.edge(source,('g',g),q)
    # Reorder families across classes, so a relaxed witness is not driven by Dhatupatha ordering.
    ordered=sorted(rows,key=lambda r:hashlib.sha256(('feasibility-only:'+r['family']).encode()).hexdigest())
    for index,row in enumerate(ordered):
        fn=('f',index);gana_of[fn]=row['gana']
        family_edges[fn]=net.edge(('g',row['gana']) if gq else source,fn,cap)
        for c,mask in row['eligible_person_number_masks'].items():
            if c in quotas:net.edge(fn,('c',c),min(mask.bit_count(),cap))
    for c,q in quotas.items():net.edge(('c',c),sink,q)
    maximum=net.flow(source,sink)
    loads=Counter(e[3]-e[1] for e in family_edges.values() if e[3]-e[1])
    actual_gana=Counter()
    for fn,e in family_edges.items():actual_gana[gana_of[fn]]+=e[3]-e[1]
    return {'n':n,'max_per_family':cap,'fixed_pilot_gana_weights':bool(gq),
        'maximum_allocatable':maximum,'feasible':maximum==n,
        'family_load_histogram_in_discarded_capacity_witness':dict(loads),
        'families_in_discarded_capacity_witness':sum(loads.values()),
        'gana_counts_in_discarded_capacity_witness':dict(actual_gana),
        'max_gana_fraction_in_capacity_witness':max(actual_gana.values())/maximum if maximum else None,
        'cell_quotas':quotas,'gana_quotas':gq,
        'scope':'Capacity witness only. No task IDs, person-number choices, gold forms or family membership are exported. Joint person/number balance is not proven by this flow.'}


def diversity_check(rows,n,cap,gana_weights=None,label='relaxed_gana'):
    weights=Counter(cell(s['recipe'],s['morphology']['lakara'],s['morphology']['prayoga']) for s in slots())
    quotas=apportion(weights,n);gq=apportion(gana_weights,n) if gana_weights else None
    net=MinCost();source='source';sink='sink';family_edges={};gana_of={};cell_edges=[]
    if gq:
        for g,q in gq.items():net.edge(source,('g',g),q)
    ordered=sorted(rows,key=lambda r:hashlib.sha256(('diversity-only:'+r['family']).encode()).hexdigest())
    for index,row in enumerate(ordered):
        fn=('f',index);gana_of[fn]=row['gana'];gn=('g',row['gana']) if gq else source
        family_edges[fn]=[net.edge(gn,fn,1,0),net.edge(gn,fn,cap-1,1)]
        for c,mask in row['eligible_person_number_masks'].items():
            if c in quotas:cell_edges.append(net.edge(fn,('c',c),min(mask.bit_count(),cap)))
    for c,q in quotas.items():net.edge(('c',c),sink,q)
    maximum,cost=net.flow(source,sink,n)
    loads=Counter();actual_gana=Counter()
    for fn,edges in family_edges.items():
        load=sum(e[3]-e[1] for e in edges)
        if load:loads[load]+=1;actual_gana[gana_of[fn]]+=load
    # Every surviving cell in this census has all nine person-number combinations.
    # Group each family/cell's <=8 chosen questions consecutively, then cycle PN.
    # This proves global PN balance without persisting any final task choices.
    assert all(mask==511 for row in rows for mask in row['eligible_person_number_masks'].values())
    pair_counts=Counter();index=0
    for e in cell_edges:
        count=e[3]-e[1]
        assert count<=9
        for k in range(count):pair_counts['/'.join(PN[(index+k)%9])]+=1
        index+=count
    assert index==maximum and max(pair_counts.values())-min(pair_counts.values())<=1
    return {'n':n,'max_per_family':cap,'quota_mode':label,'maximum_allocatable':maximum,
        'feasible':maximum==n,'maximum_distinct_families':maximum-cost,
        'family_load_histogram':dict(loads),'gana_counts':dict(actual_gana),
        'max_gana_fraction':max(actual_gana.values())/maximum,
        'cell_quotas':quotas,'gana_quotas':gq,'balanced_person_number_counts':dict(pair_counts),
        'family_pair_correlation_multiplier':sum(k*k*v for k,v in loads.items())/maximum-1,
        'no_membership_exported':True,'optimization':'Minimize repeat-family units at the specified cap and quotas; equivalent to maximize distinct families. Availability witnesses are discarded.'}


def summarize(reviewed=False):
    source_path=OUT/(RUN+('.reviewed-supply.json' if reviewed else '.supply.json'))
    data=json.loads(source_path.read_text());rows=data['rows']
    cells=defaultdict(lambda:{'families':0,'tuples':0,'all_nine_person_number_families':0,'gana_families':Counter()})
    recipes=defaultdict(lambda:{'families':set(),'tuples':0,'gana_families':defaultdict(set)})
    for r in rows:
        for c,mask in r['eligible_person_number_masks'].items():
            d=cells[c];d['families']+=1;d['tuples']+=mask.bit_count();d['all_nine_person_number_families']+=mask==511;d['gana_families'][r['gana']]+=1
            recipe=c.split('|')[0];d=recipes[recipe];d['families'].add(r['family']);d['tuples']+=mask.bit_count();d['gana_families'][r['gana']].add(r['family'])
    recipe_summary={r:{'families':len(v['families']),'tuples':v['tuples'],'gana_families':{g:len(f) for g,f in v['gana_families'].items()}} for r,v in recipes.items()}
    status('Checking release-size constraints','Completed the grammatical supply census. Testing recipe, tense and class quota feasibility under explicit family caps; no final membership is being selected.')
    checks=[]
    for n in [1000,1601]:
        for strict in [True,False]:
            for cap in [1,2,3,4,5,6,7,8]:
                result=capacity_check(rows,n,cap,GANAS if strict else None);checks.append(result)
                if result['feasible']:break
    diversity=[]
    adjusted_gana={'Bhvadi':828,'Adadi':80,'Juhotyadi':28,'Divadi':174,'Svadi':28,
        'Tudadi':162,'Rudhadi':25,'Tanadi':9,'Kryadi':63,'Curadi':204}
    for n in [1000,1601]:
        for weights,cap,label in [(GANAS,5 if n==1000 else 8,'exact_pilot_gana'),
                                   (None,2,'relaxed_gana'),(adjusted_gana,2,'supply_adjusted_gana')]:
            status('Optimizing family breadth',f'Testing a {n:,}-question capacity design with {label.replace("_"," ")} and a limit of {cap} questions per family; final membership remains unset.')
            diversity.append(diversity_check(rows,n,cap,weights,label))
    precision=[]
    for n in [1000,1601,2001,2501]:
        # Optimistic variance design effect for balanced use of every eligible family.
        used=min(n,data.get('eligible_master_test_families',data['master_test_families']));lo,extra=divmod(n,used)
        factor=((used-extra)*lo*lo+extra*(lo+1)*(lo+1))/n-1
        precision.append({'n':n,'iid_se_at_80_percent':math.sqrt(.8*.2/n),
            'optimistic_balanced_family_count':used,'pair_correlation_multiplier':factor,
            'illustrative_se_by_within_family_correlation':{str(rho):math.sqrt(.16/n*(1+factor*rho)) for rho in [0,.05,.1,.2,.5,1]}})
    summary={'created_at':now(),'run_id':RUN,'state':'offline_supply_assessed','benchmark_ready':False,
        'scope':data['scope'],'vp_version':data['vp_version'],'master_test_families':data['master_test_families'],
        'family_gana':data['family_gana'],'accepted_tuples':data['accepted_tuples'],
        'attempted_tuples_after_lexical_filters':data['attempted_tuples_after_lexical_filters'],
        'rejections':data['rejections'],'recipes':recipe_summary,'cells':dict(cells),'capacity_checks':checks,
        'diversity_optimized_checks':diversity,'precision_sensitivity':precision,'pilot_results_used':False,
        'prospective_rule_exclusion':data.get('prospective_rule_exclusion'),
        'removed_tuples':data.get('removed_tuples',0),
        'hidden_modifier_exclusion':data.get('hidden_modifier_exclusion'),
        'eligible_master_test_families':data.get('eligible_master_test_families',data['master_test_families']),
        'eligible_family_gana':data.get('eligible_family_gana',data['family_gana']),
        'total_removed_tuples':data.get('total_removed_tuples',0),
        'inputs':{'family_split_sha256':data['family_split_sha256'],'dictionary_sha256':data['dictionary_sha256'],
                  'census_sha256':sha(source_path),'analysis_script_sha256':sha(Path(__file__))},
        'limitations':['Availability is VP plus declared construction filters, not independent certification of every gold variant.',
            'All accepted family/recipe/tense/voice cells have all nine person-number options. Grouped cyclic assignment proves balanced person-number supply with no membership fixed.',
            'No final distribution or membership has been frozen; old test suballocation is unchanged.',
            'Within-family correlations are illustrative sensitivity assumptions, not measured model statistics.',
            'No held-out model answers were inspected and no paid calls were made.']}
    atomic_json(OUT/(RUN+('.reviewed-analysis.json' if reviewed else '.json')),summary)
    print(json.dumps({'accepted_tuples':summary['accepted_tuples'],'recipes':recipe_summary,
        'capacity':[{k:x[k] for k in ['n','max_per_family','fixed_pilot_gana_weights','maximum_allocatable','feasible','families_in_discarded_capacity_witness']} for x in checks]},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['census','summarize','summarize-reviewed']);a=p.parse_args()
    census() if a.command=='census' else summarize(a.command=='summarize-reviewed')
