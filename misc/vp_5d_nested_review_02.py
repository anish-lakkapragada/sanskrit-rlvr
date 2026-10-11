"""Expand independent rule evidence for the three nested vowel disagreements."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_5d_pilot import OUT,atomic_json,now,sha
from misc.vp_5d_prepare_02 import status
from vidyut.prakriya import Vyakarana,Sanadi,Pada,Lakara,Prayoga,Purusha,Vacana

BASE='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
SOURCES={
 '1.1.4':'https://sanskritdocuments.org/~sanskrit/learning_tools/sarvanisutrani/1.1.4.htm',
 '1.1.56':BASE+'1/1.1.57.htm',
 '1.1.57':BASE+'1/1.1.58.htm',
 '6.4.48':BASE+'6/6.4.48.htm','6.4.49':BASE+'6/6.4.49.htm',
 '7.1.100':BASE+'7/7.1.100.htm','8.2.77':BASE+'8/8.2.77.htm',
 '8.2.1':BASE+'8/8.2.1.htm',
 'jF_derivative_paradigm':'https://kosha.sanskrit.today/word/sa/जेजिरितव्यम्',
 'nested_direct_examples':'https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV#1025'}


def main():
    es={e.code:e for e in old.load_entries()};v=Vyakarana()
    tasks={t['dhatu']['code']:t for t in json.loads((OUT/'pilot-01.tasks.json').read_text())}
    records=[]
    for code in ['09.0027','04.0026','02.0006']:
        t=tasks[code];e=es[code];controls=[]
        for ops,la in [(['yaN'],'Lat'),(['yaN'],'Lut'),(['yaN','Ric'],'Lat'),(['yaN','Ric','san'],'Lat')]:
            ps=v.derive(Pada.Tinanta(dhatu=e.dhatu.with_sanadi([getattr(Sanadi,s) for s in ops]),
                lakara=getattr(Lakara,la),prayoga=Prayoga.Kartari,purusha=Purusha.Prathama,vacana=Vacana.Eka))
            controls.append({'sanadi':ops,'lakara':la,'prayoga':'Kartari','purusha':'Prathama','vacana':'Eka',
                'engine_forms':sorted({p.text for p in ps}),
                'relevant_trace_first_variant':[{'rule':h.code,'terms':list(h.result)} for h in ps[0].history
                    if h.code in {'1.1.4','1.1.5','6.4.48','6.4.49','7.1.100','7.3.84','7.3.86','8.2.77'}],
                'evidence_level':'Engine reproduction, not independent source certification.'})
        if code in {'09.0027','04.0026'}:
            argument=[
                '7.1.100 replaces final long vocalic r by i with r retention; the base has ir before the intensive ya.',
                'In the simple present intensive, the following y supplies the consonantal environment for 8.2.77, producing long i.',
                'Before added causal nic, 6.4.49 and 6.4.48 delete intensive ya. The surviving next element is vocalic, so 8.2.77 no longer has its consonantal condition.',
                'The original vowel deletion does not recreate an erased consonant. Rules 1.1.56/57 restrict substitution retention, while 8.2.1 prevents treating a completed tripadi surface form as a new unconditioned stem.',
                'No extra guna may be introduced merely after ya deletion: 1.1.4 and the related substitution-retention analysis block the otherwise expected vowel strengthening.',
                'The Kridantarupamala transcription independently has short-i jF intensive derivatives jejiritA and jejirizyamARa against present jejIryamARa. These are derivative-paradigm corroboration, not direct examples of the full requested triple finite form.']
            sources=['7.1.100','6.4.49','6.4.48','1.1.4','1.1.56','1.1.57','8.2.77','8.2.1','jF_derivative_paradigm']
            conclusion='Retain the original short-i key. The disputed long-i feature is not supported by the surviving phonological environment. Full nested forms remain rule-composition evidence; JF also uses cross-root generalization of the explicit rule.'
        else:
            argument=[
                'The intensive stem is lelihya; its internal lexical i is unchanged.',
                'Adding causal nic deletes intensive ya under 6.4.49/48.',
                '1.1.4 explicitly prevents the guna/vrddhi otherwise occasioned by an ardhadhatuka suffix when that same suffix causes loss of part of the dhatu. Intensive ya deletion is the relevant construction.',
                'The alternative analysis using vowel-deletion retention under 1.1.56 also prevents treating lih as a newly exposed unconditioned light penultimate vowel.',
                'Whitney directly prints vevidayAmi and vevidayizAmi, independently showing the same non-strengthening pattern in nested intensive derivation.',
                'Thus leleh in the model answer is unsupported; causal-suffix variants in the passive future are a separate matter. The lih trace does not have the combined Cinvat/mit quarantine condition.']
            sources=['1.1.4','1.1.56','6.4.48','6.4.49','nested_direct_examples']
            conclusion='Retain the original lih vowel. The narrow vowel disagreement now has explicit rule support rather than analogy alone. The complete passive future remains composed from documented operations, not directly attested as a whole.'
        records.append({'task_id':t['id'],'dhatu_code':code,'aupadeshika':e.dhatu.aupadeshika,
            'morphology':t['morphology'],'sanadi':t['derivation']['sanadi'],'original_gold_slp1':t['gold_slp1'],
            'argument':argument,'sources':{k:SOURCES[k] for k in sources},'component_controls':controls,
            'disposition':'retain_with_rule_composition_evidence','conclusion':conclusion,
            'full_requested_form_direct_example_found':False,'gold_changed':False,'new_exclusion':None})
    audit={'created_at':now(),'run_id':'pilot-preparation-02','vp_version':'0.4.0',
        'issue':'Three nested vowel disagreements from Opus development pilot01','reviews':records,
        'source_identity_note':'The SanskritDocuments archive filenames 1.1.57.htm and 1.1.58.htm contain the displayed texts of rules 1.1.56 and 1.1.57 respectively; citations are keyed to the actual text, not assumed filename numbering.',
        'evidence_boundary':'The narrow disputed vowel features are supported by explicit traditional rules and component corroboration. No claim is made that every accepted variant of each complete nested finite form appears verbatim in a source.',
        'unresolved_oracle_exclusions':['The adopted optional Cinvat/mit passive-future branch remains excluded, not repaired.','All pre-existing nested trace exclusions and shared lexical/semantic exclusions remain active.'],
        'new_quarantines':[],'raw_scores_changed':False,'script_sha256':sha(Path(__file__))}
    atomic_json(OUT/'pilot-02.nested-source-review.json',audit)
    prose='''# Nested source review for pilot 02

The three outstanding disagreements have been reviewed at the disputed vowel, with no gold or score changes. They remain in the audited paired subset. No additional quarantine follows from this review; the existing rule and scope exclusions remain active.

For jF and JF, 7.1.100 supplies ir. Simple intensive present forms acquire long i before y under 8.2.77. Added causal nic deletes ya under 6.4.49/48, leaving a vowel rather than the required following consonant. The short-i nested result therefore has explicit rule support. A printed Kridantarupamala paradigm also contrasts jF intensive present jejIryamARa with nonpresent jejirizyamARa and derivative jejiritA. This corroborates the component alternation, not the entire triple finite form; JF uses the general rule across another root. [7.1.100](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.1.100.htm), [6.4.49](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/6/6.4.49.htm), [8.2.77](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.77.htm), [Kridantarupamala transcription](https://kosha.sanskrit.today/word/sa/जेजिरितव्यम्).

For lih, the earlier analogy is strengthened by rule 1.1.4: the ardhadhatuka suffix that causes intensive-stem deletion cannot thereby introduce the blocked guna. The retained vowel in lelihay- is consistent with the directly documented veviday- construction. The complete requested passive future remains a composition inference, not a directly printed example. [Kashika and Nyasa on 1.1.4](https://sanskritdocuments.org/~sanskrit/learning_tools/sarvanisutrani/1.1.4.htm), [Whitney §1025](https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV#1025).

The order of operations matters: carrying a finished intensive surface form unchanged into the next operation is not a valid substitute for the full derivation. The substitution-retention rules and tripadi ordering constrain that reasoning. Some archive filenames are offset: the displayed 1.1.56 and 1.1.57 texts are at files 1.1.57.htm and 1.1.58.htm. [Displayed 1.1.56](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.1.57.htm), [displayed 1.1.57](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.1.58.htm), [8.2.1](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/8/8.2.1.htm).

The optional Cinvat/mit passive-future issue remains independently unresolved and excluded. This review resolves the narrow vowel objections; it is not blanket certification of every rare nested gold alternative. Machine-readable component derivations, source labels and unchanged original task IDs are in `pilot-02.nested-source-review.json`.
'''
    (OUT/'pilot-02.nested-source-review.md').write_text(prose)
    status('Nested vowel review complete','The three narrow vowel disagreements have explicit rule support; full forms remain labeled as composition inference. Original keys stay unchanged, and adopted oracle exclusions remain active.')
    print(json.dumps({'reviewed':len(records),'new_quarantines':[],'gold_changes':0}))


if __name__=='__main__':main()
