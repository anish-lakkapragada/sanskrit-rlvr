"""Aggregate-only alternative-N witnesses; never reads model results or selects tasks."""
from copy import deepcopy
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path
import hashlib,json,math
from misc.vp_5d_prepare_04 import ROOT,OUT,sha,now,atomic_json,status
from misc.vp_5d_supply_08_policy20 import allocate,PN
from misc.vp_5d_release_feasibility import Dinic
from misc.vp_5d_history_18 import history
from misc.vp_5d_prepare_03 import SOURCE_ROOTS
from misc.vp_5d_prepare_05 import UNRESOLVED
from misc.vp_5d_pilot import SPLIT
from misc.vp_cartesian_task import entry_scope_issue
from misc import vp_campaign_candidates as old
P=OUT/'pilot-08-scale-options-policy21'
POLICY='f5bfab6f3fc27b7c83bbd6987bede73501592a9568fda32a0371bd8e23b7febd'
NAME='san20_lun45_fullcoverage'
ROUNDSEED='vp-five-d-pilot08-scale-options-policy21-v1'
def read(p):return json.loads(Path(p).read_text())
def tie(n,tag):return hashlib.sha256(f'{ROUNDSEED}:{n}:{tag}'.encode()).hexdigest()
def rounding(plan,n):
    ideals={c:Fraction(q*n,2400) for c,q in plan['cell_counts'].items()}
    floors={c:int(q) for c,q in ideals.items()};quota=dict(floors)
    row_ideal=Counter();col_ideal=Counter();row_floor=Counter();col_floor=Counter()
    for c,q in ideals.items():
        r,la,vo=c.split('|');row_ideal[(r,vo)]+=q;col_ideal[la]+=q;row_floor[(r,vo)]+=floors[c];col_floor[la]+=floors[c]
    assert all(x.denominator==1 for x in [*row_ideal.values(),*col_ideal.values()])
    net=Dinic();edges={}
    for r,q in sorted(row_ideal.items()):net.edge('s',('r',r),int(q)-row_floor[r])
    for c in sorted(ideals,key=lambda c:(tie(n,'joint:'+c),c)):
        if ideals[c].denominator>1:
            r,la,vo=c.split('|');edges[c]=net.edge(('r',(r,vo)),('l',la),1)
    for la,q in sorted(col_ideal.items()):net.edge(('l',la),'t',int(q)-col_floor[la])
    assert net.flow('s','t')==n-sum(floors.values())
    for c,e in edges.items():quota[c]+=e[3]-e[1]
    gi={g:Fraction(q*n,2400) for g,q in plan['gana_counts'].items()};gq={g:int(x) for g,x in gi.items()}
    for g in sorted(gi,key=lambda g:(-(gi[g]-gq[g]),tie(n,'class:'+g),g))[:n-sum(gq.values())]:gq[g]+=1
    def detail(ideal,actual):return {k:dict(ideal_exact=str(v),rounded=actual[k],delta_exact=str(Fraction(actual[k])-v),delta_percentage_points=float((Fraction(actual[k])-v)*100/n)) for k,v in sorted(ideal.items())}
    ra=Counter();ca=Counter()
    for c,q in quota.items():r,la,vo=c.split('|');ra[(r,vo)]+=q;ca[la]+=q
    assert ra==row_ideal and ca==col_ideal and sum(gq.values())==sum(quota.values())==n
    return quota,gq,dict(n=n,rounding_seed=ROUNDSEED,joint_method='Floor every rational scaled cell; allocate the remaining units by integral recipe×voice-to-lakara flow over fractional cells, with SHA256-seeded edge order. Preserve all exact recipe×voice and all ten tense totals. Every cell remains floor or ceiling of its ideal; at these N every fractional cell is exactly one half.',class_method='Hamilton largest remainder, with SHA256-seeded tie order, independent of model outcomes.',joint_cells=detail(ideals,quota),class_cells=detail(gi,gq),recipe_voice_totals={r+'|'+v:int(q) for (r,v),q in sorted(ra.items())},lakara_totals=dict(ca),maximum_joint_absolute_rounding_error=float(max(abs(Fraction(quota[c])-q) for c,q in ideals.items())),maximum_class_absolute_rounding_error=float(max(abs(Fraction(gq[g])-q) for g,q in gi.items())),total_joint_absolute_rounding_error=float(sum(abs(Fraction(quota[c])-q) for c,q in ideals.items())),total_class_absolute_rounding_error=float(sum(abs(Fraction(gq[g])-q) for g,q in gi.items())))
def pair_summary(a):
    counts=Counter();repeated=Counter();by_rec=defaultdict(Counter)
    for x in a['unordered_within_family_cell_pair_counts']:
        c,d=x['cell_a'].split('|'),x['cell_b'].split('|');kind='Lun_Lun' if c[1]==d[1]=='Lun' else 'mixed_Lun_nonLun' if 'Lun' in [c[1],d[1]] else 'nonLun_nonLun';counts[kind]+=x['pairs'];by_rec[kind]['|'.join(sorted([c[0],d[0]]))]+=x['pairs']
        if c[1]==d[1]:repeated[c[1]]+=x['pairs']
    assert sum(counts.values())==(a['sum_squared_family_loads']-a['n'])//2
    assert set(repeated)<={'Lun'}
    return dict(total_unordered_pairs=sum(counts.values()),by_tense_block=dict(counts),by_tense_block_recipe_pair={k:dict(v) for k,v in by_rec.items()},same_lakara_pairs=dict(repeated),number_nonzero_cell_pairs=len(a['unordered_within_family_cell_pair_counts']))
def main():
    assert not P.exists(),'Preserve previous artifacts';assert sha(ROOT/'misc/vp_cartesian_task.py')==POLICY
    supply=OUT/'pilot-06.scale-supply-policy21.json';src=read(supply);planpath=OUT/'pilot-08/revision-02/plan.json';plan=read(planpath)
    assert src['shared_adapter_sha256']==POLICY and src['family_split_sha256']==sha(SPLIT) and src['dictionary_sha256']==sha(old.TSV)
    used,exposed,ha=history();rows=deepcopy(src['rows']);es={}
    for e in old.load_entries():es.setdefault(old.family(e),e)
    fs=read(SPLIT)['families'];overlap=0;held=set(SOURCE_ROOTS)|set(UNRESOLVED)
    for row in rows:
        f=row['family'];e=es[f];assert fs[f]['split']=='test'
        if row['eligible_person_number_masks']:assert not entry_scope_issue(e) and e.code not in held
        for c,m in list(row['eligible_person_number_masks'].items()):
            rec,la,vo=c.split('|');keep=0
            for i,(pu,va) in enumerate(PN):
                if not(m&(1<<i)):continue
                sig=(e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(plan['recipe_operations'][rec]),la,vo,pu,va)
                if sig in used:overlap+=1
                else:keep|=1<<i
            if keep:row['eligible_person_number_masks'][c]=keep
            else:del row['eligible_person_number_masks'][c]
    eligible={r['family'] for r in rows if r['eligible_person_number_masks']};assert len(eligible)==971 and not (eligible&exposed) and overlap==0
    availability=Counter(r['gana'] for r in rows if r['eligible_person_number_masks'])
    P.mkdir();atomic_json(P/'supply-audit.json',dict(created_at=now(),source_supply_sha256=sha(supply),eligible_families=len(eligible),eligible_by_class=dict(availability),eligible_exact_tuples=sum(m.bit_count() for r in rows for m in r['eligible_person_number_masks'].values()),history_snapshot=ha,historical_exact_tuple_overlap=0,new_campaign_family_overlap=0,source_controls_and_unresolved_entries_excluded=True,RL_disjoint=True,legacy_caveat='Legacy 6687 analysis inspected all dictionary families. Current campaign separation and exact tuple novelty are not globally unseen-root claims.',model_outputs_read=False))
    summaries=[]
    for n in [3000,3600,4200]:
        quota,gq,rounding_note=rounding(plan,n);atomic_json(P/f'N{n}.rounding.json',rounding_note)
        # The frozen allocation helper scales a 2400-unit plan. Supply a temporary
        # normalized equivalent and assert exact integer restoration; no shared edit.
        bridge=dict(cell_counts={c:q*2400/n for c,q in quota.items()},gana_counts={g:q*2400/n for g,q in gq.items()})
        assert {c:round(q*n/2400) for c,q in bridge['cell_counts'].items()}==quota
        status('Checking alternative N allocation',f'Input-only allocation of {n:,} slots, exact recipe/voice/tense totals and deterministic joint/class rounding. Maximum family coverage, then fewer repeated tenses, then balanced loads; no results or final membership.')
        a=allocate(rows,bridge,n,'test',NAME);assert a['feasible'] and a['cell_counts']==quota and a['gana_counts']==gq
        a.update(created_at=now(),policy='oracle-policy-21',adapter_sha256=POLICY,allocation_seed=f'vp-five-d-pilot08-aggregate-witness:{NAME}:test:{n}',objective_order=['maximum families','minimum repeated lakaras','minimum squared family loads'],class_only_family_upper_bound=sum(min(availability[g],gq[g]) for g in gq),eligible_families=len(eligible),rounding_file=f'N{n}.rounding.json',source_supply_sha256=sha(supply),source_plan_sha256=sha(planpath),final_n=None,final_membership_generated=False,model_outputs_read=False,paid_calls=0)
        a['pair_summary']=pair_summary(a);a['uncovered_families_by_class']={g:availability[g]-a['family_gana_counts'].get(g,0) for g in sorted(availability)}
        a['conditional_common_rho_sensitivity']={str(p):{str(rho):100*math.sqrt(p*(1-p)/n*(1+a['family_pair_correlation_multiplier']*rho)) for rho in [0,.05,.1,.2,.3]} for p in [.8,.7,.5]}
        a['precision_caveat']='Hypothetical equal-variance/common-correlation formula only. No empirical accuracy, missing-response, joint-cell covariance or pilot08 outcome is used. Actual iid and family sandwich SE must both pass for both models; changing N/root composition changes the estimand and information.'
        atomic_json(P/f'N{n}.allocation.json',a)
        summary={k:a[k] for k in ['n','feasible','distinct_families','class_only_family_upper_bound','family_gana_counts','family_load_histogram','aorist_load_histogram','distinct_aorist_families','repeated_aorist_questions_beyond_one_per_family','sum_squared_family_loads','family_pair_correlation_multiplier','pair_summary','uncovered_families_by_class']};summaries.append(summary);print(json.dumps(summary),flush=True)
    prior=OUT/'pilot-08-scale-policy21/N4800.allocation.json';a=read(prior);a['pair_summary']=pair_summary(a)
    summaries.append({k:a[k] for k in ['n','feasible','distinct_families','family_gana_counts','family_load_histogram','aorist_load_histogram','distinct_aorist_families','repeated_aorist_questions_beyond_one_per_family','sum_squared_family_loads','family_pair_correlation_multiplier','pair_summary']})
    atomic_json(P/'summary.json',dict(created_at=now(),status='aggregate_options_only_no_N_selected',options=summaries,existing_N4800_path=str(prior),existing_N4800_sha256=sha(prior),no_final_membership_generated=True,no_model_outputs_read=True,paid_calls=0))
    sources=[Path(__file__),ROOT/'misc/vp_5d_supply_08_policy20.py',ROOT/'misc/vp_5d_candidate_4800_p18.py',ROOT/'misc/vp_5d_release_feasibility.py',ROOT/'misc/vp_5d_history_18.py',supply,planpath,ROOT/'misc/vp_cartesian_task.py',OUT.parent/'oracle-policy-21.json',SPLIT,old.TSV,prior]
    atomic_json(P/'manifest.json',dict(created_at=now(),status='unpaid_aggregate_feasibility_options',files={p.name:sha(p) for p in sorted(P.glob('*.json'))},sources={str(p):sha(p) for p in sources},final_n=None,final_membership_generated=False,shared_code_changed=False,paid_calls=0,no_model_outputs_read=True))
    assert sha(ROOT/'misc/vp_cartesian_task.py')==POLICY
    status('Alternative N witnesses ready','Aggregate policy 21 witnesses for 3,000, 3,600 and 4,200 slots are feasible with fixed recipe/voice/tense proportions, documented rounding and full pair-count tables. Existing 4,800 witness remains unchanged; no N or membership is chosen.')
if __name__=='__main__':main()
