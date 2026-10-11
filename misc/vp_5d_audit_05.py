"""Review every exposed Opus05 disagreement without modifying frozen rows."""
from __future__ import annotations
import json,re
from collections import Counter
from misc.vp_5d_audit_03 import ROOT,OUT,BASE,SOURCES,current_issue
from misc.vp_5d_audit_04 import SOURCES as MORE_SOURCES
from misc.vp_5d_pilot import atomic_json,now,sha
from misc.vp_5d_calibration_analysis_02 import summarize
from misc.vp_cartesian_task import make_task,entry_scope_issue
from misc import vp_campaign_candidates as old
from vidyut.prakriya import Vyakarana

GROUPS=[
([3,6,16,19,41,51,52,53,57,59,82,84,87,94,100,129,132,194,218,245,255,267,271,281,292,298,304,313,316,324,326,336,371,372,376,380,384,386,391,393,404,405,419,420,430,432,437,456,459,465,469,478],
 'extra_aorist_reduplication','no_redup','The answer adds a new causal-aorist reduplicative syllable to a stem that already has intensive reduplication. The anabhyasa restriction blocks that extra syllable.'),
([17,378],'lexical_s_exception','lexical_s','The explicit zvazk exception to6.1.64 preserves z; the answer incorrectly dentalizes the reduplicative stem.'),
([175,363,464],'luk_rit_source_question','rit','VP retains the original r-it shortening prohibition after independent yaNluk. The model shortens the vowel. The newly reviewed anubandha paribhasa creates a source-grounded oracle concern; this is not certified as a model error pending shared scope review.'),
([55,408],'mit_shortening_context','mit','The answer has a long root vowel and VP shortens under6.4.92. Distinguish am-final Sram, which can meet the broad phonological mit prescription anew, from non-am lexical pras, whose inherited gana-mit status is a pending source issue after yaNluk.'),
([54,369],'incorrect_intensive_reduplicative_vowel','intensive_vowel','The answer substitutes e for the long-a intensive reduplicative vowel without an applicable condition.'),
([103,237,389],'missing_conditional_future_marker','future','The requested Lrn conditional retains the future marker; the answer gives an aorist-like form without that marker.'),
([117,181,283],'missing_aorist_shortening','shortening','The causal aorist shortens the root vowel; the answer retains e or long I/U instead of the required short vowel.'),
([134,205,395,447],'missing_reduplicative_palatalization','palatal','The reduplicative velar consonant must undergo7.4.62 palatalization. The answer retains the original velar, including N instead of Y for the nasal.'),
([135,151,250],'r_series_augment','r_series','The r-penultimate intensive takes the specified rI augment (with additional alternatives only in the independent-luk context). The answer replaces it by a plain long-vowel reduplication; row135 also loses the lexical z.'),
([179,280],'nasal_reduplicative_augment','nasal','The nasal-final root has the7.4.85 nasal augment, not the r-series augment used by the answer.'),
([220,424],'unlicensed_guna_after_intensive_deletion','guna_block','The answer adds guna despite the blocking effect of suffix-conditioned intensive deletion. The protected root vowel remains r.'),
]
SPECIAL={
 27:('missing_rit_shortening_exception','rit','The ordinary yaN→Ric recipe retains the original r-it shortening restriction; the answer incorrectly shortens A. This is distinct from the pending independent-yaNluk transfer issue.'),
 28:('missing_causal_stem_segment','causal','The answer drops the causal aya segment before periphrastic-perfect Am. Its intensive stem and auxiliary otherwise align.'),
 99:('nested_long_r_order','long_r','The reviewed7.1.100/ya-deletion/8.2.77 ordering retains short ir. The answer has long Ir without the required following consonant.'),
 111:('extra_reduplication_and_luk_rit_question','no_redup','The answer adds another reduplication. Its shortening also intersects the pending r-it transfer concern after yaNluk, so do not certify the full accepted union without that source review.'),
 169:('missing_vowel_final_intensive_segment','hal','The root is vowel-final:6.4.49 does not delete its intensive ya. The causal/perfect stem retains the extra ya/aya structure omitted by the answer.'),
 176:('unlicensed_reduplicative_stop_substitution','sibilant','The answer turns initial S into c in reduplication. The relevant deaspiration/palatalization rules do not license that replacement; S remains S.'),
 279:('extra_reduplication_and_missing_shortening','shortening','The answer adds reduplication and retains long I in the causal aorist where shortening gives i.'),
 302:('extra_reduplication_and_missing_rit_exception','rit','The answer adds reduplication and shortens o. This ordinary-yaN recipe retains the r-it shortening exception; the new independent-luk question does not apply.'),
 370:('quarantined_svid_dictionary_accent','svid','The installed Divadi citation lacks the source anudatta and creates set forms. Primary Kashika gives the anit root and svettA; policy12 quarantines this exact entry. The model answer is not substituted into gold or relabeled.'),
 422:('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The answer lengthens root a to A despite the relevant blocking effect after intensive deletion.'),
}
SOURCES.update(MORE_SOURCES)
SOURCES.update(causal=[BASE+'3/3.1.26.htm',BASE+'6/6.1.78.htm'],r_series=[BASE+'7/7.4.90.htm',BASE+'7/7.4.91.htm'],sibilant=[BASE+'7/7.4.62.htm',BASE+'8/8.4.54.htm'],svid=['https://sa.wikisource.org/wiki/काशिका/सप्तमोऽध्यायः/द्वितीयः_पादः'])

def main():
    source=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-05/results.json';rs=json.loads(source.read_text());es={e.code:e for e in old.load_entries()}
    v=Vyakarana();bases={c:sorted({p.text for p in v.derive(e.dhatu)}) for c,e in es.items()};manual=dict(SPECIAL)
    for ix,category,key,note in GROUPS:
        for i in ix:assert i not in manual;manual[i]=(category,key,note)
    wrong={i for i,r in enumerate(rs) if r['status']=='completed' and not r['is_correct']};assert set(manual)==wrong,(sorted(wrong-set(manual)),sorted(set(manual)-wrong))
    reviews=[];kept=[];excluded=[];refusals=[];pending=[]
    for i,r in enumerate(rs):
        t=r['task'];code=t['dhatu']['code'];issue=current_issue(t,es);ops=t['derivation']['sanadi'];tr=set(t['campaign']['trace_rule_ids']);concerns=[]
        if 'yaNluk' in ops and 'Ric' in ops[ops.index('yaNluk')+1:]:
            if '7.4.2' in tr and re.search(r'f~[\\^]*$',es[code].dhatu.aupadeshika):concerns.append('r_it_shortening_block_after_luk')
            if '6.4.92' in tr and not all(x.endswith('am') for x in bases[code]):concerns.append('non_am_lexical_mit_after_luk')
        if concerns:pending.append({'id':t['id'],'code':code,'concerns':concerns,'correct':r['is_correct'],'status':r['status'],'shared_scope_issue':issue})
        if issue:excluded.append({'id':t['id'],'code':code,'reason':issue,'correct':r['is_correct'],'status':r['status']})
        else:kept.append(r)
        if i in manual:
            category,key,note=manual[i];regen=None if entry_scope_issue(es[code]) else make_task(es[code],'development',t['morphology'],t['derivation']['recipe_id'],ops,prompt_version=t['prompt_version'])
            if regen:assert regen['gold_slp1']==t['gold_slp1']
            reviews.append({'raw_index':i,'id':t['id'],'code':code,'recipe':t['derivation']['recipe_id'],'morphology':t['morphology'],'answer':r['answer'],'original_gold_slp1':t['gold_slp1'],'category':category,'review':note,'sources':SOURCES[key],'scope_issue':issue,'additional_luk_source_concerns':concerns,'trace_rules':t['campaign']['trace_rule_ids'],'regeneration_passed':True if regen else None,'gold_changed':False,'evidence_level':'Primary rule composition and component controls, not independent printed attestation of each full rare form.'})
        if r['status']=='refused':
            m=r['raw_batch_result']['result']['message'];refusals.append({'id':t['id'],'code':code,'provider_stop_reason':m.get('stop_reason'),'provider_stop_details':m.get('stop_details'),'scope_issue':issue,'linguistic_review':'No visible reasoning.' if code=='01.0371' else 'The discussion checks nasal deletion versus independent-luk retention, then causal aorist reduplication. It does not expressly reject the recipe.','explicit_recipe_invalidity_objection_found':False,'treatment':'Retain in all-request denominator unless an independent source predicate excludes the input.'})
    assert len(reviews)==88 and len(refusals)==2
    k=sum(bool(r['is_correct']) for r in kept if r['status']=='completed');n=len(kept);miss=sum(r['status']!='completed' for r in kept);pendingids={x['id'] for x in pending}
    out={'created_at':now(),'source_sha256':sha(source),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),'raw':summarize(rs),'current_scope':summarize(kept),'missing_response_bounds':[k/n,(k+miss)/n],'excluded':excluded,'reviews':reviews,'refusal_reviews':refusals,'luk_source_predicate_rows':pending,'sensitivity_without_luk_source_predicate_rows':summarize([r for r in kept if r['task']['id'] not in pendingids]),'eligible_error_categories':dict(Counter(x['category'] for x in reviews if not x['scope_issue'])),'limitations':['Earlier raw answers and gold remain immutable; no model answer is relabeled correct.','The marker/mit artifact proposes narrow source-driven gates; actual shared scope is identified per row and by adapter hash.','No final task membership or held-out model answers were read.','Complete rare forms are not all independently printed; source-uncertainty holds take priority over difficulty calibration.'],'benchmark_ready':False,'paid_calls':0}
    atomic_json(OUT/'pilot-05.disagreement-review.json',out);print(json.dumps({k:out[k] for k in ['current_scope','missing_response_bounds','sensitivity_without_luk_source_predicate_rows','eligible_error_categories']},indent=2))

if __name__=='__main__':main()
