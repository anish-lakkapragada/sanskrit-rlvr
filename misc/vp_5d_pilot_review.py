"""Read the authorized 5D development pilot only; no paid operations."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_5d_pilot import OUT,atomic_json,now,sha
from vidyut.prakriya import Lakara,Pada,Prayoga,Purusha,Vacana,Sanadi,Vyakarana

JOB=ROOT/'benchmarks/iterative-goal-20261006/jobs/opus-five-d-pilot-01'
BASE='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
SOURCE={
    'reduplication':[BASE+'6/6.1.8.htm',BASE+'6/6.1.11.htm'],
    'abhyasa_consonant':[BASE+'7/7.4.62.htm'],
    'nasal_augment':[BASE+'7/7.4.85.htm'],
    'r_augment':[BASE+'7/7.4.91.htm'],
    'mit_shortening':[BASE+'6/6.4.92.htm'],
    'nested_long_r_order':[BASE+'7/7.1.100.htm',BASE+'6/6.4.49.htm',BASE+'8/8.2.77.htm',BASE+'8/8.2.1.htm'],
    'intensive_y_loss':[BASE+'6/6.4.49.htm'],
    'passive_variants':[BASE+'6/6.4.62.htm'],
    'nested_vowel':['https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV#1025'],
    'adanta':[BASE+'6/6.4.48.htm'],
}
REVIEWS={
    '07.0023':('vowel_grade','intensive_y_loss','The intensive-luk aorist retains the ordinary guna result in the lexical root (ve-vij to ve-vej before the set aorist); the model retained i. Full trace records 7.3.86.','rule_supported_composition'),
    '01.0241':('extra_reduplication','reduplication','The model added pu before the already reduplicated intensive-causative aorist. The anabhyasa restriction forbids a second reduplication here.','rule_supported_model_error'),
    '09.0027':('nested_long_r_vowel','nested_long_r_order','VP changes long vocalic r to ir under 7.1.100, removes consonant-following ya under 6.4.49 before nic, and retains short i because the surviving following element is vocalic. Carrying long i from a completed intensive surface form would apply 8.2.77 prematurely; 8.2.1 supports the ordering. No direct printed example of this entire chain was found.','source_supported_ordering_inference_not_direct_example'),
    '01.0412':('lexical_consonant','abhyasa_consonant','The supplied dictionary root has retroflex d (SLP1 q). The model substituted dental d. This is a lexical identity error, independent of optional endings.','lexical_identity_error'),
    '08.0007':('abhyasa_augment','nasal_augment','The nasal-final root takes the nasal reduplicative augment under 7.4.85. The model used the rI augment for a different structural environment.','rule_supported_model_error'),
    '03.0020':('abhyasa_consonant','abhyasa_consonant','The initial k in the reduplicative syllable becomes c under 7.4.62.','rule_supported_model_error'),
    '01.0887':('mit_shortening','mit_shortening','The root is in the mit lexical context. Under 6.4.92, e shortens to i in the causal layer; the model preserved e. The same short vowel persists into the desiderative passive.','rule_supported_composition'),
    '06.0137':('abhyasa_consonant','abhyasa_consonant','This Tudadi ku is not the Bhvadi homonym to which the intensive exception applies. The regular reduplicative k-to-c change is retained.','rule_supported_lexical_scope'),
    '06.0141':('vowel_grade','intensive_y_loss','The requested intensive-luk future keeps the set future after a guna stem and resolves e+i as ay+i. The model used an unset shortened form. Full trace records 7.2.35 and 7.3.84.','rule_supported_composition'),
    '01.0837':('abhyasa_augment','r_augment','The vocalic-r medial intensive-luk admits ru/rI/ri augment variants under 7.4.91, not a bare long-a reduplicative syllable.','rule_supported_model_error'),
    '04.0026':('nested_long_r_vowel','nested_long_r_order','The same 7.1.100 / 6.4.49 / 8.2.77 ordering issue as 09.0027: VP has short ir before the causal-desiderative suffix. This is a rule-based inference, not an independently printed full-form example.','source_supported_ordering_inference_not_direct_example'),
    '06.0100':('extra_reduplication','reduplication','The model added pu before the existing intensive reduplication in the causal aorist.','rule_supported_model_error'),
    '02.0006':('nested_vowel','nested_vowel','The model strengthened lih to leh inside the already intensive stem. The nested-stem preservation is analogous to the directly documented vevidayami control. Passive future variants with and without the causal suffix are licensed under 6.4.62.','source_supported_analogy_not_direct_example'),
    '01.1136':('mit_shortening','passive_variants','An independent source audit found a missing optional long-vowel branch under 6.4.93 with Cinvat. The model lengthens while retaining causal aya, whereas the documented long-vowel branch deletes nic. This is not a demonstrated score correction, but the whole grammatical context is prospectively excluded pending oracle repair. See release-feasibility-01.passive-oracle-review.json.','oracle_incomplete_context_without_demonstrated_score_correction'),
    '10.0393':('adanta_lexical_base','adanta','The cited Curadi root is the a-final SvaWa entry, distinct from SvaWa~. The final a is not an anubandha here; its deletion prevents the model\'s assumed medial lengthening. The dictionary identity and trace support short a.','rule_supported_lexical_scope'),
    '02.0074':('extra_reduplication','reduplication','The model inserted a fresh desiderative reduplication before an already reduplicated intensive-causal stem.','rule_supported_model_error'),
    '09.0045':('extra_reduplication','reduplication','The model added vi before the existing intensive reduplication in the causal aorist.','rule_supported_model_error'),
}


def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [center-half,center+half]


def main():
    result_path=JOB/'results.json';rs=json.loads(result_path.read_text())
    es={e.code:e for e in old.load_entries()};v=Vyakarana();review=[];cells=defaultdict(Counter)
    for r in rs:
        t=r['task'];assert t['campaign']['split']=='development'
        cell=cells[t['derivation']['recipe_id']];cell['n']+=1;cell[r['status']]+=1;cell['correct']+=bool(r['is_correct'])
        if r['status']!='completed' or r['is_correct']:continue
        e=es[t['dhatu']['code']];m=t['morphology'];d=e.dhatu.with_sanadi([getattr(Sanadi,s) for s in t['derivation']['sanadi']])
        ps=v.derive(Pada.Tinanta(dhatu=d,lakara=getattr(Lakara,m['lakara']),prayoga=getattr(Prayoga,m['prayoga']),purusha=getattr(Purusha,m['purusha']),vacana=getattr(Vacana,m['vacana'])))
        assert sorted({p.text for p in ps})==t['gold_slp1']
        group,source,note,confidence=REVIEWS[e.code]
        relevant=[]
        for h in ps[0].history:
            if h.code.startswith(('6.4.','7.1.','7.2.','7.3.','7.4.','8.2.77')):
                relevant.append({'rule':h.code,'terms':list(h.result)})
        review.append({'task_id':t['id'],'code':e.code,'aupadeshika':e.dhatu.aupadeshika,
            'recipe':t['derivation']['recipe_id'],'morphology':m,'answer':r['answer'],
            'gold_devanagari':t['gold_devanagari'],'gold_slp1':t['gold_slp1'],
            'category':group,'sources':SOURCE[source],'review':note,'evidence_level':confidence,
            'relevant_trace_first_variant':relevant,'gold_changed':False})
    assert len(review)==17
    summary=json.loads((JOB/'summary.json').read_text())
    out={'created_at':now(),'experiment':'opus-five-d-pilot-01','reference':'Opus 5.5 xHigh / 16384',
        'n':120,'completed':115,'correct_completed':98,'completed_exact_accuracy':98/115,
        'all_request_accuracy':98/120,'refused':5,'truncated':0,'infrastructure_failures':0,
        'completed_iid_se':math.sqrt((98/115)*(17/115)/115),'completed_wilson_95':wilson(98,115),
        'cells':{k:dict(c,completed_exact_accuracy=c['correct']/c['completed']) for k,c in cells.items()},
        'error_categories':dict(Counter(x['category'] for x in review)),
        'reviews':review,'confirmed_oracle_corrections':0,'raw_scores_unchanged':True,
        'oracle_completeness_issue':{'source_audit':'release-feasibility-01.passive-oracle-review.json',
            'affected_pilot_code':'01.1136','score_change_demonstrated':False,'prospective_context_exclusion':True},
        'interpretation':'85.22% completed-answer accuracy is above the 79–81% target. The 81.67% all-request figure includes five refusals and must not be presented as grammatical accuracy.',
        'uncertainty':'120 distinct citation-plus-gana families limit within-pilot repetition, but the interval does not account for development-selection effects, missing-answer bias, shared linguistic patterns or run-to-run model variation.',
        'cautions':['Three full nested forms are supported by ordering/analogy rather than directly printed examples: jF, JF and lih. Keep these visible in final oracle review.',
            'Sources support rule applications but do not certify all engine alternatives.',
            'No pilot item is removed or relabeled based on its answer.'],
        'paid_cost_upper_usd_from_coordinator_record':summary['actual_cost_upper_micro']/1e6,
        'worker_paid_calls':0,'input_sha256':sha(result_path),'script_sha256':sha(Path(__file__))}
    atomic_json(OUT/'pilot-01.result-review.json',out)
    print(json.dumps({k:out[k] for k in ['completed_exact_accuracy','all_request_accuracy','error_categories','confirmed_oracle_corrections']},indent=2))


if __name__=='__main__':main()
