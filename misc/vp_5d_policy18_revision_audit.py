"""Policy18 immutable revisions: source delta, quota/seed identity and pre-exposure lineage."""
import json
from collections import Counter
from pathlib import Path
from misc.vp_5d_prepare_04 import OUT,ROOT,now,sha,atomic_json,status
from misc.vp_5d_candidate_nested_audit import traces
from misc.vp_5d_history_18 import history
from misc.vp_5d_novelty_04 import normalized
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue

def read(p):return json.loads(p.read_text())
def contexts(ts):return Counter((t['derivation']['recipe_id'],r) for t in ts for r in t['campaign']['trace_rule_ids'])

def main():
    prior_paths=[OUT/'candidate-4800/revision-03/tasks.json',OUT/'pilot-07/tasks.json']
    snapshot=read(OUT/'pilot-07/exposure-and-novelty-audit.json')['historical_input_snapshot']
    prior_paths += [Path(p['path']) for p in snapshot['task_files'] if '/opus-five-d-pilot-' in p['path']]
    allprior=[t for path in prior_paths for t in read(path)]
    prior_contexts=contexts(allprior);prior_rules={r for rec,r in prior_contexts}
    es=entries_by_code();used,hf,ha=history();outputs=[]
    for label,oldp,newp,planname,expected_excluded in [
      ('candidate04',OUT/'candidate-4800/revision-03',OUT/'candidate-4800/revision-04','sampling-plan.json',1),
      ('pilot07-r1',OUT/'pilot-07',OUT/'pilot-07/revision-01','plan.json',2)]:
        old=read(oldp/'tasks.json');new=read(newp/'tasks.json');op=read(oldp/planname);np=read(newp/planname)
        om={t['id']:t for t in old};nm={t['id']:t for t in new};shared=set(om)&set(nm)
        excluded=[]
        for t in old:
            why=entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)
            if why:excluded.append(dict(id=t['id'],code=t['dhatu']['code'],operations=t['derivation']['sanadi'],morphology=t['morphology'],reason=why))
        assert len(excluded)==expected_excluded and not(set(x['id'] for x in excluded)&set(nm))
        for tid in shared:
            for key in ['dhatu','morphology','derivation','gold_slp1','gold_devanagari','prompt_version']:assert om[tid][key]==nm[tid][key]
            assert om[tid]['campaign']['prompt_sha256']==nm[tid]['campaign']['prompt_sha256']
        for key in ['recipe_counts','cell_counts','gana_counts','lakara_counts','prayoga_counts','person_counts','number_counts','person_number_counts','seed','maximum_tasks_per_family','maximum_Lun_per_family','maximum_each_other_lakara_per_family']:
            assert op[key]==np[key],key
        nowctx=contexts(new);relative_contexts=set(nowctx)-set(contexts(old));newctx=set(nowctx)-set(prior_contexts)
        controls=[]
        for t in new:
            hits=[r for r in t['campaign']['trace_rule_ids'] if (t['derivation']['recipe_id'],r) in newctx]
            if hits:controls.append(dict(id=t['id'],code=t['dhatu']['code'],operations=t['derivation']['sanadi'],morphology=t['morphology'],new_context_rules=hits,derivations=traces(t['dhatu']['code'],t['derivation']['sanadi'],t['morphology'])))
        overlaps=[t['id'] for t in new if normalized(t)[0] in used];assert not overlaps
        if label=='candidate04':assert not ({t['campaign']['root_family'] for t in new}&hf)
        report=dict(created_at=now(),panel=label,policy='oracle-policy-18',policy_sha256=sha(OUT.parent/'oracle-policy-18.json'),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),
          previous_tasks_sha256=sha(oldp/'tasks.json'),revised_tasks_sha256=sha(newp/'tasks.json'),previous_n=len(old),revised_n=len(new),
          shared_question_ids=len(shared),new_question_ids=len(set(nm)-set(om)),removed_question_ids=len(set(om)-set(nm)),
          all_shared_grammar_gold_prompt_unchanged=True,all_global_quotas_caps_seed_unchanged=True,old_inputs_excluded_by_policy18=excluded,
          new_rule_ids_against_all_prior_reviewed_inputs=sorted({r for rec,r in nowctx}-prior_rules),
          new_recipe_rule_contexts_against_all_prior_reviewed_inputs=[dict(recipe=rec,rule=r,n=nowctx[rec,r]) for rec,r in sorted(newctx)],
          new_contexts_relative_to_immediate_predecessor=[dict(recipe=rec,rule=r,n=nowctx[rec,r]) for rec,r in sorted(relative_contexts)],
          new_context_controls=controls,reviewed_input_sources=[dict(path=str(path),sha256=sha(path)) for path in prior_paths],
          historical_tuple_overlap=overlaps,history=ha,
          explicit_unsubmitted_predecessor_overlap=len(shared) if label=='pilot07-r1' else None,
          source_scope='All current-policy gates and source/unresolved holds checked before any provider answers. Newly covered contexts are listed for bounded independent review, not declared universally valid.',
          legacy_caveat='Legacy6687 analysis inspected all dictionary families. New campaign exact-input novelty and family separation do not establish never-exposed lexical roots.',
          paid_calls=0,final_model_answers_read=False,final_membership_approved=False,benchmark_ready=False)
        atomic_json(newp/'revision-source-delta-audit.json',report)
        outputs.append({k:report[k] for k in ['panel','shared_question_ids','new_question_ids','new_rule_ids_against_all_prior_reviewed_inputs','new_recipe_rule_contexts_against_all_prior_reviewed_inputs']})
    print(json.dumps(outputs,indent=2))
    status('Policy18 revisions audited','Both immutable revisions retain all quotas, seeds and shared question forms; input history and newly covered source contexts checked without model answers. No provider calls or final evaluation approval.')

if __name__=='__main__':main()
