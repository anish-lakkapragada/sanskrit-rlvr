"""Input-only policy21 N4800 feasibility witness; no final task membership.

Reads historical TASK inputs only. Never opens a provider result or answer file.
"""
from copy import deepcopy
from collections import Counter
from pathlib import Path
import json
from misc.vp_5d_prepare_04 import ROOT,OUT,sha,now,atomic_json,status
from misc.vp_5d_supply_08_policy20 import allocate,PN
from misc.vp_5d_history_18 import history
from misc.vp_5d_prepare_03 import SOURCE_ROOTS
from misc.vp_5d_prepare_05 import UNRESOLVED
from misc.vp_5d_pilot import SPLIT
from misc.vp_cartesian_task import entry_scope_issue
from misc import vp_campaign_candidates as old
P=OUT/'pilot-08-scale-policy21';NAME='san20_lun45_fullcoverage';EXPECTED='f5bfab6f3fc27b7c83bbd6987bede73501592a9568fda32a0371bd8e23b7febd'
def read(p):return json.loads(p.read_text())
def main():
 assert not P.exists(),'Preserve prior witness';assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 source=OUT/'pilot-06.scale-supply-policy21.json';sup=read(source);assert sup['shared_adapter_sha256']==EXPECTED
 assert sup['family_split_sha256']==sha(SPLIT) and sup['dictionary_sha256']==sha(old.TSV)
 baseplan=OUT/'pilot-08/revision-02/plan.json';plan=read(baseplan);assert plan['oracle_policy']=='oracle-policy-21';assert plan['recipe_counts']=={'causative_of_intensive':1344,'causative_of_intensive_luk':576,'desiderative':480}
 assignment=read(SPLIT)['families'];es={}
 for e in old.load_entries():es.setdefault(old.family(e),e)
 used,exposed,ha=history();rows=deepcopy(sup['rows']);held=set(SOURCE_ROOTS)|set(UNRESOLVED);overlaps=[];eligible_before=sum(bool(r['eligible_person_number_masks']) for r in rows)
 assert len(rows)==1000
 for row in rows:
  f=row['family'];e=es[f];assert assignment[f]['split']=='test'
  if row['eligible_person_number_masks']:assert e.code not in held and not entry_scope_issue(e)
  for cell,mask in list(row['eligible_person_number_masks'].items()):
   recipe,la,vo=cell.split('|');keep=0
   for i,(pu,va) in enumerate(PN):
    if not mask&(1<<i):continue
    sig=(e.dhatu.aupadeshika,old.name(e.dhatu.gana),tuple(plan['recipe_operations'][recipe]),la,vo,pu,va)
    if sig in used:overlaps.append(dict(family=f,cell=cell,person=pu,number=va))
    else:keep|=1<<i
   if keep:row['eligible_person_number_masks'][cell]=keep
   else:del row['eligible_person_number_masks'][cell]
 eligible={r['family'] for r in rows if r['eligible_person_number_masks']};assert len(eligible)==971 and not overlaps and not(eligible&exposed)
 update=read(OUT/'policy21-supply-mask-update.json');removed=next(x['removed'] for x in update['reports'] if x['scope']=='test');assert sum(x['removed_tuples'] for x in removed)==54
 byfamily={r['family']:r for r in rows}
 for x in removed:assert not(byfamily[x['family']]['eligible_person_number_masks'].get(x['cell'],0)&x['removed_mask'])
 P.mkdir();novelty=dict(created_at=now(),history_snapshot=ha,scope='All task/component INPUT files in both campaign ledgers, including the registered pilot08 inputs. No results or model answers opened.',eligible_master_test_families_before=eligible_before,eligible_master_test_families_after=len(eligible),eligible_tuple_count=sum(m.bit_count() for r in rows for m in r['eligible_person_number_masks'].values()),historical_tuple_overlap_count=0,new_campaign_family_overlap_count=0,source_control_and_unresolved_entries_excluded=True,RL_family_overlap=0,source_policy21_removed_masks_verified=removed,legacy_caveat='Legacy6687analysis inspected all dictionaryfamilies, including later reservedtestfamilies. This input-novelty check and newcampaign separation are not globally unseen lexicalroot claims.',final_membership_generated=False,paid_calls=0)
 atomic_json(P/'supply-and-novelty-audit.json',novelty)
 status('Checking policy21 test feasibility','Allocating an unpaid 4,800-slot witness from 971 eligible test families. Same grammar/class quotas and original coverage/repetition/load priorities; no model outputs or final membership.')
 result=allocate(rows,plan,4800,'test',NAME);assert result['feasible'] and result['distinct_families']==len(eligible);assert result['exact_balanced_PN_matching_passed']
 assert result['cell_counts']=={c:2*n for c,n in plan['cell_counts'].items()} and result['gana_counts']=={c:2*n for c,n in plan['gana_counts'].items()}
 result.update(created_at=now(),policy='oracle-policy-21',adapter_sha256=EXPECTED,source_supply_sha256=sha(source),source_plan_sha256=sha(baseplan),seed='vp-five-d-pilot08-aggregate-witness:'+NAME+':test:4800',source_control_codes_excluded=sorted(SOURCE_ROOTS),unresolved_prospective_exclusions=UNRESOLVED,no_model_answers_read=True,no_paid_calls=True,final_n=None,final_n_approved=False,final_membership_approved=False)
 atomic_json(P/'N4800.allocation.json',result)
 predecessor=OUT/'pilot-08-proposal-policy20/san20_lun45_fullcoverage.test-N4800.allocation.json';prior=read(predecessor)
 metrics=['distinct_families','distinct_aorist_families','repeated_aorist_questions_beyond_one_per_family','sum_squared_family_loads','family_pair_correlation_multiplier','family_cap','aorist_per_family_cap','maximum_each_other_lakara']
 changes={k:dict(previous=prior[k],current=result[k],delta=result[k]-prior[k]) for k in metrics}
 loads={k:dict(previous=prior[k],current=result[k]) for k in ['family_load_histogram','aorist_load_histogram','family_gana_counts']}
 def pairs(w):return {(x['cell_a'],x['cell_b']):x['pairs'] for x in w['unordered_within_family_cell_pair_counts']}
 a,b=pairs(prior),pairs(result);pd=[dict(cell_a=c,cell_b=d,previous=a.get((c,d),0),current=b.get((c,d),0),delta=b.get((c,d),0)-a.get((c,d),0)) for c,d in sorted(set(a)|set(b)) if a.get((c,d),0)!=b.get((c,d),0)]
 ll=Counter()
 for x in result['unordered_within_family_cell_pair_counts']:
  c,d=x['cell_a'].split('|'),x['cell_b'].split('|')
  if c[1]==d[1]=='Lun':ll['|'.join(sorted([c[0],d[0]]))]+=x['pairs']
 change=dict(created_at=now(),previous_witness_sha256=sha(predecessor),current_witness_sha256=sha(P/'N4800.allocation.json'),same_seed_and_priority_objective=True,exact_joint_and_class_quotas_unchanged=True,source_supply_removed_tuples=54,source_supply_removed_families=0,metrics=changes,histograms=loads,changed_within_family_cell_pair_counts=pd,repeated_Lun_recipe_pair_counts=dict(ll),comparison='Re-running the same seeded input-only flow after narrowing six Curadi san-Lun masks can change tie allocation and cell-pair structure even if primary optimum stays the same. No outcomes influence these choices.',feasibility_conclusion='A source-clean fixed4800 candidate can be constructed from this certified mask supply with all971eligible families and balanced PN, contingent on unchanged scope and a final complete regeneration/novelty audit. No final candidate membership or authorization is produced here.',unresolved_release_conditions=['All8pilot08jobs settle before any aggregate review.','Confirmation accuracy/response bounds and independent validity review support advancement.','Paired64kAstra completion/cost/covariance informs funding and both-model precision.','Coordinator freezes finalN/protocol/funding before any held-out answers; fixed4800is not approved by feasibility.'],paid_calls=0,model_outputs_read=False)
 atomic_json(P/'comparison-to-policy20.json',change)
 manifest=dict(created_at=now(),status='unpaid_input_only_feasibility_witness',n_scenario=4800,final_n=None,final_membership_generated=False,benchmark_ready=False,files={f:dict(sha256=sha(P/f),bytes=(P/f).stat().st_size) for f in ['supply-and-novelty-audit.json','N4800.allocation.json','comparison-to-policy20.json']},sources={str(p):sha(p) for p in [Path(__file__),ROOT/'misc/vp_5d_supply_08_policy20.py',ROOT/'misc/vp_5d_candidate_4800_p18.py',ROOT/'misc/vp_5d_release_feasibility.py',source,baseplan,OUT/'policy21-supply-mask-update.json',OUT.parent/'oracle-policy-21.json',ROOT/'misc/vp_cartesian_task.py',SPLIT,old.TSV]},paid_calls=0,no_model_results_read=True)
 atomic_json(P/'manifest.json',manifest)
 assert sha(ROOT/'misc/vp_cartesian_task.py')==EXPECTED
 print(json.dumps(dict(output=str(P),feasible=True,families=result['distinct_families'],objective=result['objective'],load_histogram=result['family_load_histogram'],aorist_histogram=result['aorist_load_histogram'],metric_deltas=changes,changed_pair_cells=len(pd),LL_recipe_pairs=dict(ll),manifest_sha256=sha(P/'manifest.json')),indent=2))
 status('Policy21 test witness complete','Input-only 4,800-slot allocation is feasible under current source scope with all 971 eligible test families and exact balanced PN. Final N, candidate membership, precision and funding remain unapproved.')
if __name__=='__main__':main()
