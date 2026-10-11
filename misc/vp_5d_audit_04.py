"""Itemwise review of already exposed development answers; never selects questions."""
from __future__ import annotations
import json
from collections import Counter
from misc.vp_5d_audit_03 import ROOT, OUT, BASE, SOURCES, current_issue
from misc.vp_5d_pilot import atomic_json, now, sha
from misc.vp_5d_calibration_analysis_02 import summarize
from misc.vp_cartesian_task import make_task, entry_scope_issue
from misc import vp_campaign_candidates as old

# Indices are immutable raw-result indices, not future selection labels.
GROUPS = [
 ([3,17,20,32,42,53,56,71,82,98,120,133,141,145,210,216,238,239,259,278,284,297,306,312,319,328,331,412,419,435,456,459,467,468,473,477],
  'extra_aorist_reduplication','no_redup',
  'The existing intensive reduplication blocks another causal-aorist reduplication. The answer adds an extra syllable before that retained stem.'),
 ([2,52,240,243,397], 'unlicensed_guna_after_intensive_deletion','guna_block',
  'Suffix-conditioned deletion of intensive ya does not license the added guna in the answer. The retained root vowel is protected in this construction.'),
 ([136,162,293], 'unlicensed_vrddhi_after_intensive_deletion','vrddhi_block',
  'The answer newly lengthens the root a after intensive deletion; the relevant deleted-vowel effect blocks this strengthening.'),
 ([9,299], 'missing_intensive_luk_guna','guna',
  'Independent intensive-luk does not have the same guna-blocking effect as suffix-conditioned ya deletion. The answer omits regular causal guna.'),
 ([18,137,153,344,469], 'nasal_reduplicative_augment','nasal',
  'The nasal-final root takes the nasal augment under 7.4.85. A plain long vowel or r-series augment does not replace this nasal treatment.'),
 ([22,221], 'missing_conditional_future_marker','future',
  'The requested conditional Lrn retains the future marker; the answer instead has an aorist-like ending without that marker.'),
 ([23,296], 'missing_aorist_shortening','shortening',
  'The causal aorist shortens the root vowel. The answer retains the long vowel.'),
 ([33,298], 'rit_shortening_exception','rit',
  'The citation is r-it. Rule 7.4.2 blocks the usual causal-aorist penultimate-vowel shortening; the answer shortens it.'),
 ([128,356], 'missing_r_series_augment','r_augment',
  'The r-penultimate intensive-luk stem retains one of the r/ri/rI augment alternatives. A plain long-vowel reduplicative syllable is not an accepted alternative.'),
 ([201,395], 'missing_nasal_deletion','nasal_loss',
  'The non-idit nasal penultimate is deleted under 6.4.24 in the intensive formation. The answer retains that nasal.'),
 ([226,264,460], 'nested_long_r_order','long_r',
  'Rule 7.1.100 gives short ir. After intensive ya deletion, the following causal vowel does not provide the consonantal context required by 8.2.77 for lengthening; the answer has Ir.'),
 ([338,362], 'missing_reduplicative_palatalization','palatal',
  'The reduplicative consonant undergoes the regular palatal replacement under 7.4.62; the answer retains the unmodified consonant.'),
]
SPECIAL = {
 160:('lexical_s_exception','lexical_s','The lexical zvazk exception to 6.1.64 preserves initial z. The answer dentalizes the reduplicative portion.'),
 219:('samprasarana_luk_scope','svap_luk','The answer uses the ordinary yaN samprasarana stem in a yaNluk recipe. Component controls distinguish sozupya/sozupi from sAsvap/sAsvApi; independent luk does not retain this suffix-conditioned effect.'),
 222:('incorrect_intensive_reduplicative_vowel','intensive_vowel','The answer replaces the intensive long-a reduplicative syllable with e without an applicable condition.'),
 233:('invented_puk_and_wrong_vowel','causal_vowel','The intensive-luk stem of blI forms causal beblAya; the aorist shortens its penultimate A. The answer instead inserts p and i, confusing the A-final puK environment with this I-final entry.'),
 250:('extra_reduplication_and_missing_guna','no_redup','The answer both adds another reduplication to the inherited intensive stem and omits causal guna in the independent-luk construction.'),
 272:('unresolved_stim_lexical_variant','stim','The submitted oracle has dental s and the answer has retroflex z. The wider stim lexical-variant question is unresolved; preserve this raw disagreement and report an outcome-independent family sensitivity. This family is not a certified hardness lead.'),
 290:('extra_reduplication_and_missing_future_marker','future','The answer adds another reduplication and lacks the future marker of the requested Lrn.'),
 374:('mit_shortening','mit','The am-final mit treatment shortens the causal penultimate a. The answer retains A in the passive.'),
 416:('extra_reduplication_and_missing_guna','no_redup','The answer adds reduplication and retains i where independent intensive-luk plus causative permits guna to e.'),
 428:('extra_reduplication_with_unresolved_stim_family','no_redup','The answer adds fresh reduplication. This same family also has an unresolved lexical s/z variant question, so both family members remain in the sensitivity report.'),
 449:('quarantined_svakka_dentalization','lexical_s','Nyasa explicitly exempts zvakka from the dentalization of 6.1.64, but the submitted oracle applies it. Policy11 quarantines both matching family members irrespective of correctness. The answer also adds reduplication; it is not relabeled correct.'),
 452:('missing_future_marker_and_long_r_order','future','The answer lacks the conditional future marker and retains Ir instead of the short ir produced by the reviewed nested ordering.'),
}
SOURCES.update({
 'future':[BASE+'3/3.3.139.htm', BASE+'3/3.1.33.htm'],
 'rit':[BASE+'7/7.4.2.htm'],
 'nasal_loss':[BASE+'6/6.4.24.htm'],
 'palatal':[BASE+'7/7.4.62.htm'],
 'svap_luk':[BASE+'6/6.1.19.htm',BASE+'1/1.1.63.htm'],
 'intensive_vowel':[BASE+'7/7.4.83.htm'],
 'causal_vowel':[BASE+'7/7.2.115.htm',BASE+'6/6.1.78.htm',BASE+'7/7.4.1.htm',BASE+'7/7.3.36.htm'],
 'stim':[],
})

def main():
    source=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-04/results.json'
    rows=json.loads(source.read_text()); es={e.code:e for e in old.load_entries()}
    manual=dict(SPECIAL)
    for indices,category,key,note in GROUPS:
        for i in indices:
            assert i not in manual
            manual[i]=(category,key,note)
    wrong={i for i,r in enumerate(rows) if r['status']=='completed' and not r['is_correct']}
    assert set(manual)==wrong, (sorted(wrong-set(manual)),sorted(set(manual)-wrong))
    reviews=[]; refusals=[]; kept=[];excluded=[]
    for i,r in enumerate(rows):
        t=r['task']; code=t['dhatu']['code']; issue=current_issue(t,es)
        if issue: excluded.append({'id':t['id'],'code':code,'reason':issue,'correct':r['is_correct'],'status':r['status']})
        else: kept.append(r)
        if i in manual:
            category,key,note=manual[i]
            regen=make_task(es[code],'development',t['morphology'],t['derivation']['recipe_id'],t['derivation']['sanadi'],prompt_version=t['prompt_version'])
            assert regen['gold_slp1']==t['gold_slp1']
            reviews.append({'raw_index':i,'id':t['id'],'code':code,'recipe':t['derivation']['recipe_id'],'morphology':t['morphology'],
                'answer':r['answer'],'gold_slp1':t['gold_slp1'],'category':category,'review':note,'sources':SOURCES[key],
                'trace_rules':t['campaign']['trace_rule_ids'],'scope_issue':issue,'regeneration_passed':True,'gold_changed':False,
                'evidence_level':'Primary rule composition and component controls; not independent printed attestation of every complete rare form.'})
        if r['status']=='refused':
            m=r['raw_batch_result']['result']['message']
            note=('No visible linguistic reasoning is available in this refusal.' if code=='01.0371' else
              'The visible discussion considers causal guna, r-it shortening exceptions, and intensive-luk ordering; it does not expressly reject the requested recipe.')
            refusals.append({'id':t['id'],'code':code,'recipe':t['derivation']['recipe_id'],'morphology':t['morphology'],
                'provider_stop_reason':m.get('stop_reason'),'provider_stop_details':m.get('stop_details'),
                'linguistic_review':note,'explicit_recipe_invalidity_objection_found':False,
                'scope_issue':issue,'truncated':r['truncated'],
                'treatment':'Retain in all-request denominator; completion conditioning is reported separately and cannot create target qualification.'})
    assert len(reviews)==78 and len(refusals)==2
    k=sum(bool(r['is_correct']) for r in kept if r['status']=='completed');n=len(kept);missing=sum(r['status']!='completed' for r in kept)
    report={'created_at':now(),'policy':'oracle-policy-11','raw_source_sha256':sha(source),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
      'raw':summarize(rows),'current_scope':summarize(kept),'excluded':excluded,'reviews':reviews,'refusal_reviews':refusals,
      'eligible_wrong_categories':dict(Counter(r['category'] for r in reviews if not r['scope_issue'])),
      'missing_response_bounds':[k/n,(k+missing)/n],
      'stim_family_sensitivity':{'predicate':'code04.0137, all outcomes and coordinates','status':'Unresolved source question, not a shared exclusion',
         'without_family':summarize([r for r in kept if r['task']['dhatu']['code']!='04.0137'])},
      'limitations':['No answer was corrected or relabeled; all raw tasks and scores are preserved.',
        'This review does not independently attest every rare full form or settle the unresolved stim lexical question.',
        'Raw disagreement mechanisms can suggest broad grammatical hypotheses; they cannot be used to select the same failed questions for a new panel.',
        'Two-question-family dependence does not establish dependence under four or more forms or repeated aorists per family.'],
      'benchmark_ready':False,'heldout_answers_read':False,'paid_calls':0}
    atomic_json(OUT/'pilot-04.disagreement-review.json',report)
    print(json.dumps({k:report[k] for k in ['current_scope','eligible_wrong_categories','missing_response_bounds','stim_family_sensitivity']},indent=2))

if __name__=='__main__': main()
