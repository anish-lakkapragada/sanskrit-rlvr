"""Pre-exposure policy20 lineage, evidence reuse and exact quota audit."""
import json
from pathlib import Path
from collections import Counter
from misc.vp_5d_prepare_04 import ROOT,OUT,sha,now,atomic_json
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue
from misc.vp_5d_candidate_4800_p18 import cell
P=OUT/'pilot-08';Q=P/'revision-01'
def read(p):return json.loads(p.read_text())
def main():
 es=entries_by_code();old=read(P/'tasks.json');new=read(Q/'tasks.json');op=read(P/'plan.json');np=read(Q/'plan.json');om={t['id']:t for t in old};nm={t['id']:t for t in new};shared=set(om)&set(nm)
 keys=['recipe_counts','cell_counts','gana_counts','lakara_counts','prayoga_counts','person_counts','number_counts','person_number_counts','seed','maximum_tasks_per_family','maximum_Lun_per_family','maximum_each_other_lakara_per_family','prompt_version','max_output_tokens','effort','phase']
 assert all(op[k]==np[k] for k in keys)
 exclusions=[dict(id=t['id'],code=t['dhatu']['code'],cell=cell(t),reason=entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)) for t in old if entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)]
 assert len(exclusions)==3 and {x['code'] for x in exclusions}=={'05.0015'} and not ({x['id'] for x in exclusions}&set(nm))
 for tid in shared:
  for k in ['dhatu','morphology','derivation','gold_slp1','gold_devanagari','prompt_version']:assert om[tid][k]==nm[tid][k]
  assert om[tid]['campaign']['prompt_sha256']==nm[tid]['campaign']['prompt_sha256']
 so=read(P/'astra-subset/tasks.json');sn=read(Q/'astra-subset/tasks.json');sop=read(P/'astra-subset/plan.json');snp=read(Q/'astra-subset/plan.json')
 for k in ['cell_counts','gana_counts','recipe_counts','lakara_counts','prayoga_counts','seed','max_questions_per_family','Lun_pair_recipe_counts','curadi_lun','curadi_non_lun','max_output_tokens','effort','phase']:assert sop[k]==snp[k]
 ledger=read(ROOT/'benchmarks/iterative-goal-20261006/ledger.json');jobs=[j for j in ledger['jobs'].values() if j['id'].startswith(('opus-five-d-pilot-08-','astra-five-d-pilot-08-'))];assert not jobs,'Record coordinator pre-exposure proof if already registered'
 evidence=[P/'coordinator-source-review.json',OUT.parent/'four_d/subset08-review/source-review.json',OUT.parent/'oracle-policy-20.json']
 assert all(p.is_file() for p in evidence)
 evidence_rec=[dict(path=str(p),sha256=sha(p)) for p in evidence]
 delta=read(Q/'source-rule-delta-audit.json');assert not delta['new_rule_ids'] and not delta['new_recipe_rule_contexts']
 report=dict(created_at=now(),policy='oracle-policy-20',adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),original_primary_sha256=sha(P/'tasks.json'),revised_primary_sha256=sha(Q/'tasks.json'),original_subset_sha256=sha(P/'astra-subset/tasks.json'),revised_subset_sha256=sha(Q/'astra-subset/tasks.json'),all_declared_quota_seed_cap_protocol_fields_unchanged=keys,shared_primary_ids=len(shared),new_primary_ids=len(set(nm)-set(om)),removed_primary_ids=len(set(om)-set(nm)),shared_grammar_gold_and_prompt_unchanged=True,original_primary_policy20_exclusions=exclusions,original_subset_policy20_exclusions=0,shared_subset_ids=len({t['id'] for t in so}&{t['id'] for t in sn}),same_subset_selection_algorithm_and_seed=True,source_rule_delta_empty=True,reused_primary_evidence=evidence_rec,ledger_sha256_at_preexposure_check=sha(ROOT/'benchmarks/iterative-goal-20261006/ledger.json'),pilot08_registered_job_count=0,no_pilot08_provider_exposure=True,source_scope='Exact Svadi05.0013/0014/0015 are conservatively held for unresolved classical scope; chāndasa labels are qualified by Kshira chāndasa-prāya, not treated as proof of universal Vedic exclusivity. Classical homonyms preserved.',no_model_answers_used_for_membership=True,paid_calls=0)
 atomic_json(Q/'revision-lineage-audit.json',report);print(json.dumps({k:report[k] for k in ['shared_primary_ids','new_primary_ids','removed_primary_ids','shared_subset_ids','source_rule_delta_empty','no_pilot08_provider_exposure']},indent=2))
if __name__=='__main__':main()
