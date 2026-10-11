"""Read-only development-result audit; writes isolated review artifacts only."""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path
from misc.vp_5d_pilot import OUT, atomic_json, now, sha
from misc.vp_5d_calibration_analysis_02 import summarize, SOURCES
from misc.vp_cartesian_task import entry_scope_issue, oracle_issue, make_task
from misc import vp_campaign_candidates as old

ROOT=Path(__file__).resolve().parents[1]
BASE='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
SOURCES.update({
 'shortening':[BASE+'7/7.4.1.htm',BASE+'1/1.1.48.htm'],
 'lexical_s':[BASE+'6/6.1.64.htm',BASE+'8/8.3.59.htm'],
 'r_augment':[BASE+'7/7.4.91.htm',BASE+'6/6.1.64.htm'],
 'auxiliary':[BASE+'7/7.1.91.htm'],
 'hal':[BASE+'6/6.4.49.htm'],
 'aspiration':[BASE+'8/8.4.54.htm'],
})
REVIEWS={
 '01.1079':('quarantined_puk','oracle','Intermediate dAdA ends in A; nested causative omits source-required puK. Quarantine across coordinates; no model-answer substitution.'),
 '01.0062':('extra_aorist_reduplication','no_redup','Already intensive-reduplicated stem does not take another causal-aorist reduplication.'),
 '06.0090':('missing_lexical_s_restoration','lexical_s','Initial citation z changes to s under 6.1.64 and is restored under 8.3.59 in this intensive context; the model retains dental s in the root.'),
 '02.0054':('vowel_final_intensive_ya_retention','hal','6.4.49 requires a consonant-final root. The vowel-final dA intensive retains ya, so ordinary simple-root puK is not licensed after dAdAya.'),
 '01.0693':('extra_aorist_reduplication','no_redup','The model adds a second reduplicative syllable to the intensive aorist.'),
 '01.0685':('lost_root_aspiration','aspiration','Deaspiration of the reduplicative syllable does not remove the original root Dh; the answer has d in the root.'),
 '06.0027':('unlicensed_guna_after_intensive_deletion','guna_block','The intensive-causal passive preserves root i, rather than strengthening it to e.'),
 '01.0363':('extra_aorist_reduplication','no_redup','The model adds a new causal-aorist reduplication to the existing intensive stem.'),
 '01.0852':('extra_aorist_reduplication','no_redup','The accepted set already includes the three r/ri/rI intensive-luk augment alternatives; the answer adds another reduplicative syllable.'),
 '04.0020':('extra_reduplication_and_missing_shortening','shortening','The answer adds a fresh reduplication and retains long I where causal-aorist shortening gives i.'),
 '08.0007':('nasal_reduplicative_augment','nasal','The nasal-final root takes nasal augment under 7.4.85, not the r augment. This family has earlier-panel errors; it is not independent broad-supply evidence.'),
 '04.0080':('unlicensed_guna_after_intensive_deletion','guna_block','The model strengthens root u to o; the intensive-deletion context blocks that guna.'),
 '01.0105':('lexical_s_exception','lexical_s','Kashika 6.1.64 explicitly exempts zvazk from the dental-s replacement; the model uses dental s where lexical z remains.'),
 '04.0130':('unlicensed_guna_after_intensive_deletion','guna_block','The model strengthens root u to o despite intensive-caused deletion.'),
 '06.0124':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The deleted intensive suffix does not license new penultimate a-vrddhi in the passive stem.'),
 '01.0868':('perfect_auxiliary_inflection','auxiliary','The answer omits r in the second-dual kR perfect auxiliary cakraTuH; the stem itself agrees.'),
 '01.0649':('missing_aorist_shortening','shortening','The causal-aorist environment shortens the root vowel; ec shortening gives i in this case.'),
 '01.1149':('semantic_lexical_san_quarantine','semantic','The input leaves the meaning branch unspecified, but the engine inserts lexical san 3.1.6 before the requested desiderative san; see semantic-san audit.'),
 '01.0206':('extra_reduplication_and_wrong_root_vowel','no_redup','The answer adds fresh causal reduplication and alters the retained intensive-luk stem vowel.'),
 '01.0186':('extra_aorist_reduplication','no_redup','The model adds an extra va to an already intensive-reduplicated stem.'),
 '01.0246':('extra_aorist_reduplication','no_redup','The model adds an extra da to the existing intensive reduplication.'),
 '04.0152':('missing_aorist_shortening','shortening','Root U shortens to u in this causal aorist; the answer retains U.'),
 '01.0751':('r_augment_and_lexical_s','r_augment','The intensive-luk r-penultimate root has ra/ri/rI augment choices. The answer substitutes a plain long-vowel reduplicative stem and dentalizes the retained lexical z.'),
 '01.0810':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','Root a remains short in this intensive-causal passive; the model gives A.'),
 '01.1158':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The future passive alternatives differ in causal-suffix treatment, but neither licenses root a-vrddhi.'),
 '01.0869':('extra_aorist_reduplication','no_redup','The model adds another pa before the existing intensive stem.'),
 '02.0007':('quarantined_caksh_substitution','oracle','Direct traditional controls disagree with VP added-sanadi caksh stems. The nested question is quarantined prospectively.'),
 '04.0142':('unlicensed_guna_after_intensive_deletion','guna_block','The model strengthens root R to ar despite the intensive-deletion blocking environment.'),
 '01.0552':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The model lengthens root a although intensive-suffix deletion preserves the relevant blocking effect.'),
 '01.0124':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The model introduces root A into the intensive-causal passive.'),
 '06.0164':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The model introduces root A into the intensive-causal passive.'),
 '05.0031':('vedic_scope_exclusion','vedic','Source-marked Vedic-only Svadi entry, excluded across all shapes by policy07. Its model error is not retained for calibration.'),
 '07.0013':('unlicensed_guna_after_intensive_deletion','guna_block','Root i stays i in the intensive-causal future passive; both source-audited causal-suffix variants are already accepted.'),
 '03.0009':('quarantined_puk','oracle','Intermediate jAhA ends in A; VP omits puK before causal nic. The model also adds reduplication, but gold uncertainty requires exclusion.'),
 '04.0007':('unlicensed_vrddhi_after_intensive_deletion','vrddhi_block','The model adds penultimate a-vrddhi in a suffix-conditioned intensive-deletion context.'),
}
REFUSAL_REVIEW={
 '05.0037':'The visible derivation discussion checks an R-final intensive; the lexical entry is independently Vedic-only and excluded by policy07.',
 '01.0131':'The visible discussion concerns ya deletion and sthAnivat vowel preservation, not an objection to recipe licensing.',
 '09.0021':'The visible discussion compares long-R ir/Ir ordering. The existing jF/JF component audit applies; no new recipe objection appears.',
 '06.0077':'The visible discussion concerns nasal deletion under 6.4.24 and the intensive reduplicative augment, not unsupported composition.',
 '06.0057':'The visible discussion considers nasal versus r augment and subsequent guna; the nasal-final 7.4.85 control remains applicable.',
 '01.0912':'The visible discussion checks mit status and inherited aorist reduplication; it does not reject the recipe.',
 '04.0032':'The discussion asks about mI9 versus mI4. This entry is mIN class4, excluded from the lexical list of 6.1.50; its nic strengthening is ordinary 7.2.115. No new validity issue.',
 '01.0477':'The visible discussion checks the nasal stem and sometimes conflates yaN with yaNluk; that is model uncertainty, not source evidence that the requested recipe is invalid.',
 '01.0782':'The discussion concerns blocked vrddhi after intensive deletion, with no expressed grammatical invalidity objection.',
 '01.0911':'The visible discussion contrasts yaN/yaNluk strengthening and sthAnivat, with no expressed licensing objection.',
}

def current_issue(t,es):
    return entry_scope_issue(es[t['dhatu']['code']]) or oracle_issue(t)

def main():
    es={e.code:e for e in old.load_entries()}
    job=ROOT/'benchmarks/iterative-goal-20261006/jobs'
    source=job/'opus-five-d-pilot-03/results.json'; rs=json.loads(source.read_text())
    excluded=[];kept=[];reviews=[];refusals=[]
    for r in rs:
        t=r['task'];code=t['dhatu']['code'];issue=current_issue(t,es)
        if issue:excluded.append({'id':t['id'],'code':code,'reason':issue,'status':r['status'],'correct':r['is_correct']})
        else:kept.append(r)
        if r['status']=='completed' and not r['is_correct']:
            category,key,note=REVIEWS[code]
            regen=None if entry_scope_issue(es[code]) else make_task(es[code],'development',t['morphology'],t['derivation']['recipe_id'],t['derivation']['sanadi'])
            if regen:assert regen['gold_slp1']==t['gold_slp1']
            sources=SOURCES.get(key,[])
            if key=='oracle':
                sources=[BASE+'7/7.3.36.htm'] if code!='02.0007' else ['https://samsaadhanii-concordance.vipran.in/dhatu/1508-cakRizf-vyakwAyAM_vAci-cakR1']
            if key=='vedic':sources=['https://jainqq.org/booktext/Kshir_Tarangini/002433']
            if key=='semantic':sources=[BASE+'3/3.1.5.htm',BASE+'3/3.1.6.htm']
            reviews.append({'id':t['id'],'code':code,'recipe':t['derivation']['recipe_id'],'morphology':t['morphology'],
                'model_answer':r['answer'],'gold_slp1':t['gold_slp1'],'category':category,'review':note,'sources':sources,
                'scope_issue':issue,'regeneration_passed':True if regen else None,'gold_changed':False,
                'evidence_level':'Rule-composition and component-source review; not exhaustive independent attestation of every complete rare form.'})
        if r['status']=='refused':
            message=r['raw_batch_result']['result']['message']
            refusals.append({'id':t['id'],'code':code,'recipe':t['derivation']['recipe_id'],'morphology':t['morphology'],
                'provider_stop_reason':message.get('stop_reason'),'provider_stop_details':message.get('stop_details'),
                'output_text':r['output_text'],'truncated':r['truncated'],'scope_issue':issue,
                'linguistic_review':REFUSAL_REVIEW[code],'explicit_recipe_invalidity_objection_found':False,
                'treatment':'Retain all-request denominator unless an independently established scope predicate excludes this input.'})
    assert len(reviews)==35 and len(refusals)==10
    groups=defaultdict(list)
    for r in kept:
        t=r['task'];m=t['morphology'];recipe=t['derivation']['recipe_id'];rules=set(t['campaign']['trace_rule_ids'])
        for dim,val in [('recipe',recipe),('lakara',m['lakara']),('voice',m['prayoga']),('gana',t['dhatu']['gana']),
          ('recipe_aorist',recipe+'|'+('aorist' if m['lakara']=='Lun' else 'other')),
          ('recipe_voice',recipe+'|'+m['prayoga']),('recipe_ya_deletion',recipe+'|'+str('6.4.49' in rules))]:groups[dim+'::'+val].append(r)
    report={'created_at':now(),'raw_source_sha256':sha(source),'shared_adapter_sha256':sha(ROOT/'misc/vp_cartesian_task.py'),
      'raw':summarize(rs),'current_scope':summarize(kept),'excluded':excluded,'reviews':reviews,'refusal_reviews':refusals,
      'groups':{k:summarize(v) for k,v in groups.items()},'remaining_wrong_categories':dict(Counter(r['category'] for r in reviews if not r['scope_issue'])),
      'limitations':['Completion-conditioned accuracy is not all-request accuracy. Refusals cannot be discarded to meet the target.',
        'All provider refusal metadata say cyber; the visible derivation discussions do not expressly reject the constructions. Wording causality needs the paired diagnostic.',
        'Development reweighting is adaptive and requires fresh confirmation. No final held-out answers were read.',
        'Semantic lexical-san scope review is separately recorded; use the current shared policy and preserve earlier raw scores.'],
      'raw_tasks_or_scores_changed':False,'benchmark_ready':False}
    atomic_json(OUT/'pilot-03.disagreement-review.json',report)
    # Identical original question set for both providers, with outcome-independent scope gates.
    op=json.loads((job/'opus-five-d-pilot-01/results.json').read_text());ast=json.loads((job/'astra-five-d-pilot-01-pair/results.json').read_text())
    om={r['task']['id']:r for r in op};pairs=[(om[r['task']['id']],r) for r in ast if not current_issue(r['task'],es)]
    joint=[(a,b) for a,b in pairs if a['status']=='completed' and b['status']=='completed']
    table=Counter(f'opus_{int(bool(a["is_correct"]))}_astra_{int(bool(b["is_correct"]))}' for a,b in joint)
    paired={'created_at':now(),'n_same_eligible_questions':len(pairs),'opus':summarize([a for a,b in pairs]),'astra':summarize([b for a,b in pairs]),
      'both_completed_n':len(joint),'both_completed_opus':summarize([a for a,b in joint]),'both_completed_astra':summarize([b for a,b in joint]),
      'both_completed_correctness_table':dict(table),'excluded_question_ids':[r['task']['id'] for r in ast if current_issue(r['task'],es)],
      'astra_truncations':sum(bool(b['truncated']) for a,b in pairs),
      'interpretation':'Opus remains the stronger tested reference on the same development inputs. Astra truncations remain separate from grammatical mistakes and require output-cap sensitivity before stronger capability claims.',
      'heldout_answers_read':False,'paid_calls':0}
    atomic_json(OUT/'pilot-01.paired-current-scope-analysis.json',paired)
    print(json.dumps({'current':report['current_scope'],'groups':{k:v for k,v in report['groups'].items() if k.startswith('recipe::')},'paired':paired},indent=2))

if __name__=='__main__':main()
