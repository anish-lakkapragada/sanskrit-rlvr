"""Every paid revision01 Opus disagreement and missing response; no score changes."""
from __future__ import annotations
import json
from collections import Counter
from misc.vp_5d_prepare_04 import OUT,ROOT,atomic_json,now,sha,status
from misc.vp_5d_audit_05 import SOURCES,BASE
from misc.vp_5d_audit_03 import current_issue
from misc.vp_5d_metrics import summarize,completed
from misc.vp_cartesian_task import make_task,entry_scope_issue
from misc import vp_campaign_candidates as old
SOURCES.update(paa=[BASE+'7/7.4.4.htm'],shas=[BASE+'6/6.4.34.htm',BASE+'7/7.4.82.htm'],aug_sandhi=[BASE+'6/6.4.72.htm',BASE+'6/6.1.90.htm'],nasal_delete=[BASE+'6/6.4.24.htm'],tuk=[BASE+'6/6.1.73.htm'],vocalic_l=[BASE+'8/8.2.18.htm'],vrasc=[BASE+'7/7.4.90.htm',BASE+'6/6.1.16.htm'])
GROUPS=[
([9,122,373],'missing_reduplicative_palatalization','palatal','The reduplicative velar must palatalize under7.4.62; the model keeps k. The special Bhvadi ku exception does not apply to Tudadi ku06.0136.'),
([31,409,452],'missing_rit_shortening_exception','rit','Ordinary yaN→Ric retains the original r-it shortening exception; the answer shortens the root vowel. This is not independent yaNluk, for which policy13 quarantines marker transfer.'),
([86,131,399],'unlicensed_guna_after_intensive_deletion','guna_block','The model strengthens a root vowel whose guna is blocked after suffix-conditioned intensive deletion.'),
([93,436],'incorrect_intensive_reduplicative_vowel','intensive_vowel','The intensive reduplicative vowel here is long A; the answer substitutes e.'),
([106,257],'missing_lexical_s_restoration','lexical_s','Initial lexical z is first dentalized and then restored under8.3.59 after the preceding vowel. The answer retains dental s in the root; this is not the zvazk exception.'),
([156,278,471],'missing_conditional_future_marker','future','The requested Lrn conditional retains the future marker; the answer gives an aorist-like form without it. Some answers additionally repeat reduplication.'),
([254,284],'missing_aorist_shortening','shortening','Causal-aorist shortening applies; the answer retains e or long I rather than the short root vowel.'),
([143,364,489],'nasal_reduplicative_augment','nasal','The nasal-final root has a nasal reduplicative augment. The answer incorrectly uses the r-series augment; row143 also strengthens the root vowel.'),
]
SPECIAL={
35:('wrong_intensive_retention_and_shortening','hal','The consonant-final intensive ya is deleted before Ric, and the root U shortens in this causal aorist. The answer retains both ya and long U.'),
65:('extra_reduplication_and_lateral_r_augment','r_series','The answer adds fresh reduplication and uses an unlicensed lateralized r-series syllable. The accepted kalp aorist variants do not contain vocalic l and are outside the separate scorer-coverage concern.'),
181:('missing_shas_weak_stem_before_reduplication','shas','Karmani k-it conditioning changes SAs to Sis under6.4.34 before intensive reduplication;7.4.82 then gives Se. The answer incorrectly retains a SAS reduplication. The trace independently places6.4.34 before6.1.9.'),
190:('missing_am_final_mit_shortening','mit','Am-final Sram satisfies the independently attested phonological mit prescription even after yaNluk. The answer retains A where6.4.92 shortens it.'),
228:('lexical_s_exception','lexical_s','Primary6.1.64 explicitly preserves the initial z of zvazk. The answer incorrectly dentalizes the intensive stem.'),
231:('missing_augment_vrddhi_sandhi','aug_sandhi','The augment before initial u gives au under the at-sandhi rule. The answer has A instead of O.'),
239:('unlicensed_strengthening_of_vowel_final_intensive','guna_block','The ordinary intensive retains its long-I plus ya sequence before causal/future morphology. The model replaces I by A as if directly causativizing the simple root.'),
241:('missing_r_augment_and_root_retroflexion','r_series','The intensive stem requires rI augmentation and the lexical retroflex consonant treatment. The answer substitutes a plain long-A reduplication and dental st.'),
273:('extra_reduplication_with_named_shas_exception','no_redup','The answer adds another reduplicative syllable. Shas is expressly named in7.4.2, distinct from the quarantined inherited r-it-marker branch.'),
309:('perfect_auxiliary_inflection','auxiliary','The answer omits r from second-dual perfect cakraTuH; the preceding causal intensive periphrastic stem agrees.'),
314:('missing_root_nasal_deletion','nasal_delete','Ordinary yaN is not independent luk. Root-nasal deletion6.4.24 applies; the answer incorrectly retains the nasal.'),
324:('missing_paa_causal_aorist_special_rule','paa','Rule7.4.4 deletes the root upadha and gives long I in the abhyasa in the causal aorist. Nyasa expressly exempts independent yaNluk via stip designation, but this task uses ordinary yaN, not yaNluk. The model preserves pepIy rather than applying the special late rule. This is rule-composition evidence, not a separately printed full nested form.'),
376:('wrong_r_augment_and_unlicensed_nasal','r_series','The answer uses a long-A intensive syllable, inserts an unsupported root nasal, and omits the licensed causal strengthening and nati of the accepted luk forms.'),
384:('vocalic_l_scorer_coverage','vocalic_l','The answer uses traditional klr typography for vocalic l, while the fixed gold/scorer uses k followed by the vocalic-l sign. Primary8.2.18 uses the traditional spelling. This is an accepted-alias coverage concern, not a certified grammatical model error; see source-addendum01.'),
459:('extra_reduplication_and_wrong_nasal_stem','nasal','The model adds fresh reduplication and uses the r-series instead of the nasal augment; it also omits the licensed root strengthening in the luk-derived causative.'),
492:('missing_causal_stem_segment','causal','The answer drops the causal aya segment before periphrastic-perfect Am.'),
494:('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The answer lengthens root a despite blocking after ordinary intensive deletion.'),
501:('extra_reduplication_and_missing_tuk','tuk','The model adds a fresh cu syllable and omits the cch cluster licensed by tuk treatment of ch. The accepted form retains the original intensive reduplication.'),
537:('missing_causal_guna_after_luk','causal','Independent yaNluk allows ordinary causal strengthening of root r to ar. The answer retains r.'),
543:('extra_reduplication_and_wrong_r_augment','r_series','The answer adds fresh reduplication, loses the r-series augment and dentalizes the retained root z.'),
551:('incorrect_intensive_reduplicative_vowel','intensive_vowel','The intensive of knu uses o in reduplication; the model substitutes e.'),
557:('missing_extended_r_augment','r_series','The model rejects rI because r is not penultimate before the nasal. Primary7.4.90 varttika explicitly extends the rule from r-upadha to r-containing roots, resolving that objection. It uses a plain long-A syllable instead.'),
577:('vrasc_luk_stem_source_contradiction','vrasc','Primary7.4.90 explicitly prints varIvfScIti for bare yaNluk, whereas the engine gives vAvraScIti/vAvrazwi. The nested passive inherits the disputed stem. Quarantine uncertainty rather than relabeling the answer; source-addendum01 preserves the contradictory control.'),
}

def main():
 p=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-06/results.json';rs=json.loads(p.read_text());es={e.code:e for e in old.load_entries()};manual=dict(SPECIAL)
 pure=json.loads((OUT/'pilot-06.error-review-working.json').read_text())['pure_extra_candidates']
 for i in pure:manual[i]=('extra_aorist_reduplication','no_redup','The answer adds a new causal-aorist reduplicative syllable before an already intensive-reduplicated stem. The anabhyasa restriction blocks that extra reduplication. Removing only that extra initial segment recovers an accepted gold form.')
 for indices,category,key,note in GROUPS:
  for i in indices:assert i not in manual;manual[i]=(category,key,note)
 wrong={i for i,r in enumerate(rs) if completed(r) and not r['is_correct']};assert set(manual)==wrong,(sorted(wrong-set(manual)),sorted(set(manual)-wrong));assert len(wrong)==118
 reviews=[];kept=[];excluded=[];missing=[]
 for i,r in enumerate(rs):
  t=r['task'];code=t['dhatu']['code'];issue=current_issue(t,es)
  if issue:excluded.append(dict(id=t['id'],index=i,code=code,reason=issue,correct=r['is_correct'],status=r['status']))
  else:kept.append(r)
  if i in manual:
   category,key,note=manual[i];regen=None if entry_scope_issue(es[code]) else make_task(es[code],'development',t['morphology'],t['derivation']['recipe_id'],t['derivation']['sanadi'],prompt_version=t['prompt_version'])
   if regen:assert regen['gold_slp1']==t['gold_slp1']
   reviews.append(dict(raw_index=i,id=t['id'],code=code,recipe=t['derivation']['recipe_id'],morphology=t['morphology'],answer=r['answer'],original_gold_slp1=t['gold_slp1'],category=category,review=note,sources=SOURCES[key],scope_issue=issue,regeneration_passed=bool(regen),gold_changed=False,evidence_level='Primary rule composition and controls; not independently printed attestation of every complete rare form.'))
  if not completed(r):
   m=r['raw_batch_result']['result']['message'];txt='\n'.join(b.get('thinking',b.get('text','')) for b in m.get('content',[]));note='No visible derivation; provider cyber-safety refusal is not linguistic invalidity evidence.'
   if i==597:note='Visible reasoning disputes rI because r is not penultimate before a nasal. The explicit r-tvat varttika at7.4.90 extends beyond the penultimate condition, resolving that linguistic objection. Other discussion concerns nasal deletion and existing reduplication, not recipe rejection.'
   if i==276:note='The reasoning reached the token limit while debating nested reduplication and strengthening. No parsed answer; no source-supported recipe-invalidity objection. Treat as missing, not a certified grammatical error.'
   missing.append(dict(raw_index=i,id=t['id'],code=code,status=r['status'],truncated=r['truncated'],answer=r['answer'],provider_stop_reason=m.get('stop_reason'),provider_stop_details=m.get('stop_details'),visible_reasoning_chars=len(txt),linguistic_review=note,source=BASE+'7/7.4.90.htm' if i==597 else None,scope_issue=issue,treatment='Retain all-request denominator; exclude from usable denominator; report missing-response bounds.'))
 assert len(missing)==4
 pending={384,577};out=dict(created_at=now(),task_sha256=sha(OUT/'pilot-06.revision-01.tasks.json'),source_sha256=sha(p),shared_adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),raw=summarize(rs),current_scope=summarize(kept),reviews=reviews,missing_response_reviews=missing,excluded=excluded,pending_source_or_scorer_reviews=[r for r in reviews if r['raw_index'] in pending and not r['scope_issue']],eligible_error_categories=dict(Counter(x['category'] for x in reviews if not x['scope_issue'])),raw_records_changed=False,model_answers_relabelled=False,paid_calls=0,benchmark_ready=False,limitations=['Current source scope is applied to every outcome, not only disagreements.','Passing the development numerical screen is not final qualification. Independent final membership and both-model precision remain unresolved.','The component-source audit supports rule composition; a separate authoritative full-form reference is unavailable for every rare form.'])
 atomic_json(OUT/'pilot-06.disagreement-review.json',out);print(json.dumps({k:out[k] for k in ['current_scope','eligible_error_categories']},indent=2));status('All Opus06 disagreements reviewed','All118 usable disagreements and four missing responses have item audits and unchanged-gold regeneration. Two narrow source/scorer issues await coordinator policy; the remaining errors are predominantly extra causal-aorist reduplication. No final membership selected.')
if __name__=='__main__':main()
