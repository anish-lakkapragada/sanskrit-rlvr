"""Unpaid revision/source-rule delta audit; input/oracle only."""
import json
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha
from misc.vp_5d_candidate_nested_audit import traces
from misc.vp_cartesian_task import entries_by_code,entry_scope_issue,oracle_issue
B=OUT/'candidate-4800';D=B/'revision-03'
def read(p):return json.loads(p.read_text())
def main():
 old=read(B/'revision-01/tasks.json');new=read(D/'tasks.json');om={t['id']:t for t in old};nm={t['id']:t for t in new};shared=set(om)&set(nm);es=entries_by_code();excluded=[]
 for t in old:
  why=entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)
  if why:excluded.append(dict(id=t['id'],code=t['dhatu']['code'],operations=t['derivation']['sanadi'],morphology=t['morphology'],issue=why))
 assert len(excluded)==24 and not(set(x['id'] for x in excluded)&set(nm))
 for tid in shared:
  for key in ['dhatu','morphology','derivation','gold_slp1','gold_devanagari','prompt_version']:assert om[tid][key]==nm[tid][key]
  assert om[tid]['campaign']['prompt_sha256']==nm[tid]['campaign']['prompt_sha256']
 for name in ['recipe_counts','cell_counts','gana_counts','lakara_counts','prayoga_counts','person_counts','number_counts','person_number_counts','seed','maximum_tasks_per_family','maximum_Lun_per_family','maximum_each_other_lakara_per_family']:
  assert read(B/'revision-01/sampling-plan.json')[name]==read(D/'sampling-plan.json')[name],name
 contexts=lambda ts:Counter((t['derivation']['recipe_id'],r) for t in ts for r in t['campaign']['trace_rule_ids'])
 before=contexts(old);after=contexts(new);newctx=set(after)-set(before);removed=set(before)-set(after);newrules={r for rec,r in after}-{r for rec,r in before};controls=[]
 for t in new:
  if any((t['derivation']['recipe_id'],r) in newctx for r in t['campaign']['trace_rule_ids']):controls.append(dict(id=t['id'],dhatu=t['dhatu'],operations=t['derivation']['sanadi'],morphology=t['morphology'],new_context_rules=[r for r in t['campaign']['trace_rule_ids'] if (t['derivation']['recipe_id'],r) in newctx],derivations=traces(t['dhatu']['code'],t['derivation']['sanadi'],t['morphology'])))
 han=[x for x in controls if '7.3.32' in x['new_context_rules']];assert len(han)==1
 hs=dict(created_at=now(),rule='7.3.32',source='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.3.32.htm',brief_excerpt='हनः तकारोदेशो भवति ञिति, णिति प्रत्यये परतः चिण्णलौ वर्जयित्वा।',source_conditions='han final n→t before a ñit/ṇit dhātu suffix other than ciṇ/ṇal. Ric is such a suffix; nominal taddhita exclusions are not present.',trace_reading='First nontrivial step changes hAn/hān? to hAt after outer Ric; later7.3.32 entry is unchanged. The whole intensive reduplicative prefix is preserved. No source marker restriction of the original dhātu or extra anubandha inference is used.',conclusion='No concrete new oracle mismatch found in this bounded source check. Full rare nested form is not separately printed; no universal correctness claim.',controls=han,no_model_answers_read=True,paid_calls=0)
 # Record exact transition wording, avoiding a guessed intermediate.
 for c in han:
  for p in c['derivations']:
   p['rule_transitions']=[dict(step=i,before=p['history'][i-1]['terms'],after=h['terms']) for i,h in enumerate(p['history']) if h['rule']=='7.3.32']
 hs['trace_reading']='The first nontrivial7.3.32 step changes the final n of the already lengthened han root portion to t after outer Ric; subsequent7.3.32 entries are unchanged. Exact term arrays are preserved below.'
 atomic_json(D/'han-7.3.32-source-control.json',hs)
 delta=dict(created_at=now(),old_tasks_sha256=sha(B/'revision-01/tasks.json'),new_tasks_sha256=sha(D/'tasks.json'),policy='oracle-policy-17',prior_revision03_not_exposed_to_models=True,old_n=len(old),new_n=len(new),shared_question_ids=len(shared),new_question_ids=len(set(nm)-set(om)),removed_question_ids=len(set(om)-set(nm)),all_shared_grammar_gold_prompt_unchanged=True,all_global_quotas_caps_and_seed_unchanged=True,old_inputs_excluded_by_current_policy=excluded,new_rule_ids=sorted(newrules),new_recipe_rule_contexts=[dict(recipe=rec,rule=r,count=after[rec,r]) for rec,r in sorted(newctx)],removed_recipe_rule_contexts=[dict(recipe=rec,rule=r,count=before[rec,r]) for rec,r in sorted(removed)],new_context_controls=controls,review='Only new rule ID is7.3.32; see han-7.3.32-source-control.json. New recipe/context combinations are listed for coordinator comparison with prior reviewed rules; source-policy17 holds remain enforced on every task.',no_model_answers_read=True,no_paid_calls=True)
 atomic_json(D/'source-rule-delta-audit.json',delta)
 print(json.dumps({k:delta[k] for k in ['shared_question_ids','new_question_ids','removed_question_ids','new_rule_ids','new_recipe_rule_contexts']},indent=2))
if __name__=='__main__':main()
