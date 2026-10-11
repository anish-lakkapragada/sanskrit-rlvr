"""Assemble the bounded human/source review; never mutate scores or paid inputs."""
from pathlib import Path
import collections
import datetime
import hashlib
import json

from vidyut.lipi import Scheme, transliterate

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'pyproject.toml').exists())
OVERLAY = HERE.parent
BASE = OVERLAY.parent.parent
PACK = BASE / 'final1800-source-pack'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rel(path):
    return str(path.relative_to(ROOT))

def rule(n):
    return f'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/{n[0]}/{n}.htm'

def slp(s):
    return transliterate(s, Scheme.Devanagari, Scheme.Slp1)

queue_path = OVERLAY / 'independent-review/completed-review/Anthropic-source-adjudication-queue.json'
canonical_path = OVERLAY / 'results/Anthropic/canonical.json'
queue = json.loads(queue_path.read_text())
canonical = json.loads(canonical_path.read_text())
adoption_path = PACK / 'source-adjudication-adoption-02.json'
adoption = json.loads(adoption_path.read_text())
accepted_puk = {r['task_id']: r['additional_forms_devanagari'] for r in adoption['accepted_additions']}
reference = json.loads((PACK / 'reference-pack.json').read_text())
families = {x['family']: x for x in reference['family_records']}

groups = {}
short = {'Cada': ('CAd', 'Cad'), 'laja': ('lAj', 'laj'), 'kuha': ('koh', 'kuh'),
         'paWa': ('pAW', 'paW'), 'pada': ('pAd', 'pad')}
lexical = {
    'Cada': 'Kshiratarangini printed333 entry321 and Siddhantakaumudi1938 printed238 explicitly give छदयति for literal-final-a छद. Distinguish nasal-marker Cada~ and Cadi~ entries. The conflicting long-vowel Wikisource transcription is documented, not silently harmonized; the two inspected printed witnesses support the supplied literal-a reading.',
    'laja': 'Madhaviya printed573 (scan627) gives लजयति for literal-a लज and separately discusses laji readings. The supplied citation has neither the alternative nasal-i marker nor an added causative operation.',
    'kuha': 'Siddhantakaumudi1938 printed237 (scan241) and Dhatupradipa printed149 (scan160) give कुहयते in the intrinsic Atmanepada group; the latter also prints कुहयाञ्चक्रे.',
    'pada': 'Siddhantakaumudi1938 printed237 (scan241) gives पदयते and अपपदत and places the pada-to-garva group in Atmanepada.',
    'paWa': 'Siddhantakaumudi1938 printed236 (scan240) lists the aspirated literal-a पठ in the adanta group. पठय- is inferred by the same stated final-a-lopa/retained-position rule; an independently printed complete paTha paradigm was not inspected.'}
for stem, (wrong, good) in short.items():
    groups[f'short-{stem}'] = {
        'disposition': 'rejected', 'claim': 'Submitted strengthened stem is not licensed for the supplied literal-final-a dictionary root.',
        'lexical_evidence': lexical[stem],
        'derivation': ['Class-intrinsic nic follows the supplied ordinary Curadi root (3.1.25).',
            'Final lexical a is deleted before the ardhadhatuka suffix (6.4.48); its retained positional effect blocks the newly apparent upadha strengthening, as explicitly explained for kathadi in SK. The supplied initial stem vowel therefore remains unchanged.',
            'Selected present, imperfect, imperative, optative, future, conditional, periphrastic future/perfect and benedictive endings do not independently license the model\'s first-vowel strengthening. For Lit, the auxiliary changes while the lexical periphrastic stem retains this vowel.',
            'The separately licensed alternative replaces final-a lopa with final-a lengthening plus puK: its stem contains an added p. It does not license these p-less CAd/lAj/koh/pAW/pAd answers.'],
        'rule_ids': ['3.1.25', '6.4.48', '7.2.116', '7.3.86'],
        'source_urls': families[f'{stem}|Curadi']['primary_lexical_locators'] + [rule('6.4.48')],
        'source_pack_family': f'{stem}|Curadi',
        'evidence_level': 'explicit lexical controls plus general-rule inference; not all paradigms printed',
        'diagnostic_stem_substitution': {'from': wrong, 'to': good, 'purpose': 'descriptive mismatch localization only; never an acceptance alias'},
        'limit': 'Rejects the actual incompatible stem. Does not certify that every canonical or unsubmitted alternative form is linguistically exhaustive.'}

lun = {
    'anka': ('AYcik', 'AYcak', 'आञ्चकत्'),
    'anga': ('AYjig', 'AYjag', 'आञ्जगत्'),
    'anDa': ('AndiD', 'AndaD', 'आन्दधत्'),
    'ansa': ('AMsis', 'AMsas', None),
    'BAma': ('abIBam', 'abaBAm', 'अबभामत्'),
}
for stem, (wrong, good, witness) in lun.items():
    groups[f'lun-{stem}'] = {
        'disposition': 'rejected', 'claim': 'The proposed aorist applies san-like vowel changes to an aglopin literal-a stem.',
        'lexical_evidence': f'SK adanta lexical entry {stem}; ' + (f'direct printed aorist representative {witness}.' if witness else 'dental ansa is distinguished from palatal amsha; its exact aorist is general-rule inference, not a printed witness.'),
        'derivation': ['Curadi nic and caN aorist are selected (3.1.25,3.1.48); the lexical final-a has been deleted.',
            '7.4.93 explicitly limits san-like reduplicative changes to an-ag-lopa and gives अचकथत् as the excluded aglopin control. The i in the submitted reduplicative syllable is consequently unlicensed.',
            '7.4.2 independently blocks caN shortening for aglopin stems; this additionally rejects BAma→Bam. Appropriate person/number endings attach to the source-supported unchanged reduplicative stem; they cannot restore the forbidden vowel changes.'],
        'rule_ids': ['3.1.25', '3.1.48', '6.4.48', '7.4.2', '7.4.93'],
        'source_urls': families[f'{stem}|Curadi']['primary_lexical_locators'] + [rule('7.4.93'), rule('7.4.2')],
        'source_pack_family': f'{stem}|Curadi',
        'evidence_level': 'printed representative and general-rule derivation' if witness else 'lexical evidence plus general-rule derivation',
        'diagnostic_stem_substitution': {'from': wrong, 'to': good, 'purpose': 'localize the wrong vowel; not an acceptance alias'},
        'limit': 'No claim of exhaustive puK-aorist propagation. An unsubmitted possible p-bearing branch cannot license the actual p-less san-like stem.'}

broad = {
90: ('rejected', 'kutadi-perfect-guna', 'डिडेपिथ changes the i of the kutadi root डिप to e. Dhatupradipa scan121 places डिप in the kutadi section. 1.2.1 makes the non-nit/nit-exempt thal suffix ngit;1.1.5 blocks guna. डिडिपिथ follows. Ordinary non-kutadi perfect analogies do not override the specified class/entry.', ['1.2.1','1.1.5'], 'Dhatupradipa scan121 lexical placement; Kashika1.2.1 and1.1.5.'),
181: ('rejected', 'optative-person-ending', 'कुथ्नीत lacks the required Parasmaipada optative ya element and is not the second-person-plural ending. 3.4.103 adds yasut,7.2.79 deletes its s,3.4.101 changes tha to ta;6.4.113 gives the short-class weak stem kuthni. Together कुथ्नीयात is obtained. A possible middle reading would require its own second-person-plural ending, not the submitted -ta.', ['3.4.103','7.2.79','3.4.101','6.4.113'], 'Kashika commentaries on the listed rules; actual morphological coordinates.'),
229: ('unresolved', 'sr-aorist-commentary-scope', 'Kashika3.1.56 expressly names सृ गतौ and prints असरत्, supporting an ang stem which regularly yields असरन्. Madhaviya restricts this ang rule to Juhotyadi sr by association with sas. The supplied task says Bhvadi but specifies no commentary school. The bounded review cannot settle whether the broader Kashika wording licenses the exact Bhvadi entry; neither accept nor reject solely from VP.', ['3.1.56','7.4.16'], 'Kashika3.1.56 versus Madhaviya entry sR, reproduced at kosha.sanskrit.today/word/sa/sR; primary commentary conflict.'),
437: ('unresolved', 'jabh-lexical-pada-num', 'Dhatupradipa scan44 and Purusakara145 explicitly support जम्भते for jabh in gatravinama;7.1.61 licenses num in the relevant jabh before a vowel. The supplied jaBa~01.0150 lacks the accent/marker pattern of the separately listed middle entry. Whether this literal citation deliberately selects a different lexeme or exposes dictionary metadata loss is not resolved. Do not label this a proven model error.', ['7.1.61','1.3.12','1.3.78'], 'Dhatupradipa scan44; Purusakara145; Kashika7.1.61; original supplied marker-bearing citation.'),
481: ('unresolved', 'reb-lexical-pada', 'अरेबामहि uses a middle first-person-plural ending while the key is अरेबाम. Primary Dhatupradipa scan43 prints a rebu/rebu-type movement entry with रेबते, but this review has not established identity with supplied rebf~ (plavagatau), including its accent. The generic default-pada rule alone is insufficient to dismiss this lexical possibility.', ['1.3.12','1.3.78'], 'Dhatupradipa scan43 is an OCR lexical lead, not an independently established exact-entry identity.'),
495: ('unresolved', 'khund-lexical-pada', 'खुण्डिताध्वे selects middle while key खुण्डितास्थ selects Parasmaipada. Under the supplied unaccented Kuqi~ the latter is the mechanical default. An exact primary lexical source for this rare Kuqi/gativaiKalya entry and its permitted pada was not verified in this bounded review; no new answer is admitted, and no definitive linguistic-error claim is made.', ['1.3.12','1.3.78'], 'Supplied exact citation plus Kashika pada rules; exact lexical/source reading remains unverified.'),
566: ('unresolved', 'sal-rdit-aorist', 'असलताम् resembles an ang aorist or an imperfect; the key is the is-aorist असालिष्टाम्. The supplied zal-f~ ends in vocalic r, not the vocalic l marker of lRdit; generic lRdit aorist reasoning therefore does not license it. The exact rare zalf lexical reading and any independent ang option were not independently located, so the bounded disposition stays unresolved.', ['3.1.43','3.1.44','3.1.55'], 'Literal-marker distinction and generic aorist rules; exact lexical enumeration remains a gap.'),
764: ('rejected', 'ish-meaning-pada', 'ईषेथाः is middle. Dhatupradipa scan59 explicitly gives ईष उञ्छे→ईषति; the separately listed movement/harming/giving ईष→ईषते is on scan56. The supplied meaning selects the first entry. By1.3.78 its second-person-singular optative is ईषेः, not a middle ending.', ['1.3.78','3.4.103','7.2.79'], 'Primary Dhatupradipa distinct lexical entries, scans59 and56; generic Parasmaipada optative rules.'),
949: ('rejected', 'dyai-ay-length', 'The supplied root ends in ai. 6.1.78 maps ai to ay with LONG a (आय्) before the a-stem vowel, giving द्याय-. The submitted द्ययाम incorrectly shortens that stem; the first-person-plural imperative does not supply a rule for that shortening.', ['6.1.78'], 'Kashika6.1.78 explicitly gives ordered e/o/ai/au→ay/av/ay(long)/av(long); Dhatupradipa scan76 prints द्यायति.'),
992: ('rejected', 'rinv-natva', 'रिरिन्व retains dental n. The supplied idit root adds num and the same-word earlier r triggers natva across the permitted vowel/v interveners under8.4.1–2, giving रिरिण्व. The frozen optional-gemination policy cannot change n to n retroflex or remove the required natva.', ['8.4.1','8.4.2'], 'Kashika8.4.1–2 plus literal idit root and actual perfect form.'),
1025: ('rejected', 'durv-lengthening', 'दुर्वतः retains short u before the root-internal rv cluster. 8.2.78 extends the r/v lengthening to the root-internal position and directly illustrates urvi/dhurvi; the analogous supplied durvi requires दूर्वतः. Dhatupradipa scan53 also prints दूर्वति.', ['8.2.78'], 'Kashika8.2.78; primary lexical representative in Dhatupradipa scan53.'),
1104: ('rejected', 'cell-lexical-geminate', 'चेलानि deletes one lexical l from the supplied cella citation. Primary Dhatupradipa scans51–52 separately list cela and cella and print चेल्लति. Optional deletion8.4.64 requires a preceding consonant; the first l here follows e, so it does not license cell→cel. Adding an optional third l then deleting it likewise never licenses a singleton.', ['8.4.64','8.4.65'], 'Primary separate lexical entries in Dhatupradipa51–52 and Kashika8.4.64–65.'),
1186: ('unresolved', 'kand-lexical-accent-pada', 'कण्डिष्ये uses middle. Dhatupradipa scan37 explicitly gives kadi made→कण्डते, supporting a middle lexical reading; supplied kaqi~01.0418 lacks an anudatta marker and VP produces only Parasmaipada. The visible prompt includes citation markers and meaning but no chosen edition. Exact-entry/accent reconciliation is needed before accepting or rejecting कण्डिष्ये.', ['1.3.12','1.3.78'], 'Dhatupradipa scan37 and primary Dhatupatha middle-section entry; possible task-source marker ambiguity.'),
1686: ('rejected', 'mr-labial-u', 'मीर्यास्म uses i where the specified long-vocalic-r root after labial m requires u by7.1.102;8.2.77 supplies its long vowel before ry. The benedictive is therefore मूर्यास्म. This is an obligatory labial-conditioned vowel change, not optional spelling.', ['7.1.102','8.2.77'], 'Kashika7.1.102 and8.2.77 plus supplied mF citation.'),
}
for index,(disposition,key,note,ids,source) in broad.items():
    groups[key] = {'disposition': disposition, 'claim': note, 'rule_ids': ids,
        'source_urls': [rule(n) for n in ids], 'evidence_level': source,
        'limit': 'Bounded examination of this submitted answer; unsubmitted variants and complete accepted unions are not certified.'}
groups['sr-aorist-commentary-scope']['source_urls'].append('https://kosha.sanskrit.today/word/sa/sR')
groups['jabh-lexical-pada-num']['source_urls'].append('https://sa.wikisource.org/wiki/दैवम्_(पुरुषकारव्याख्यासमेतम्)')

rows=[]
for q in queue:
    t=q['task'];stem=t['dhatu']['aupadeshika'];ans=slp(q['answer'])
    if stem in short:
        group='short-'+stem
    elif stem in lun:
        group='lun-'+stem
    else:
        group=broad[q['index']][1]
    g=groups[group]
    r={'task_id':q['task_id'],'index':q['index'],'answer_devanagari':q['answer'],
       'answer_slp1':ans,'dhatu':t['dhatu'],'morphology':t['morphology'],
       'canonical_forms_devanagari':q['canonical_forms_devanagari'],
       'canonical_gold_preserved':True,'predeclared_alias_match':q['answer'] in q['predeclared_aliases_devanagari'],
       'adopted_puk_addition_match':q['answer'] in accepted_puk.get(q['task_id'],[]),
       'disposition':g['disposition'],'evidence_group':group,'rule_ids':g['rule_ids'],
       'source_urls':g['source_urls'],'receipt_sha256':q['receipt_sha256'],
       'case_limit':g['limit']}
    if 'diagnostic_stem_substitution' in g:
        sub=g['diagnostic_stem_substitution'];z=ans.replace(sub['from'],sub['to'])
        r['wrong_stem_present']=sub['from'] in ans
        r['diagnostic_only_corrected_stem_slp1']=z
        r['diagnostic_only_after_stem_change_matches_canonical']=z in t['gold_slp1']
        assert r['wrong_stem_present']
    if q['index']==1075:
        r['additional_error']='The perfect auxiliary also has cakravahe instead of canonical cakrvahe (SLP1 cakfvahe); rejection already follows independently from koh instead of kuh.'
    rows.append(r)

refusals=[]
for r in canonical:
    if r['status']!='refused':continue
    msg=r['raw_batch_result']['result']['message']
    prompt=r['request']['params']['messages'][0]['content']
    refusals.append({'task_id':r['task_id'],'index':r['task_index'],'dhatu':r['task']['dhatu'],
        'morphology':r['task']['morphology'],'output_text':r['output_text'],'answer':r['answer'],
        'stop_reason':msg['stop_reason'],'provider_stop_details':msg.get('stop_details'),
        'explicit_sanskrit_verbal_root_prompt':'Sanskrit verbal root (dhatu' in prompt,
        'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
        'returned_summary_present':bool(r.get('thinking_text')),
        'returned_summary_topic':'Sanskrit grammar' if r.get('thinking_text') else None,
        'disposition':'provider_cyber_filter_false_positive_nonanswer',
        'interpretation':'The provider explicitly labels the rejection cyber, while the task is Sanskrit conjugation. The specific triggering token or policy feature cannot be inferred; no claim that English root alone caused it.',
        'scoring':'Preserve fixed1800 denominator and raw refusal. Not a submitted linguistic error; no retry or replacement.'})

counts=collections.Counter(x['disposition'] for x in rows)
assert len(rows)==214 and len({r['task_id'] for r in rows})==214
assert len(refusals)==5 and all(r['provider_stop_details']['category']=='cyber' for r in refusals)
assert counts=={'rejected':208,'unresolved':6}
assert sum(r['evidence_group'].startswith('short-') for r in rows)==187
assert not any(r['adopted_puk_addition_match'] or r['predeclared_alias_match'] for r in rows)
assert sum(r.get('diagnostic_only_after_stem_change_matches_canonical',False) for r in rows if r['evidence_group'].startswith('short-'))==186

inputs=[queue_path,canonical_path,PACK/'reference-pack.json',PACK/'source-adjudication-adoption-02.json',
    PACK/'puk-extension-supplement/supplement.json',BASE/'reading-clarification.json',
    BASE/'candidate-1800-v1/tasks.json',BASE/'candidate-1800-v1/public-prompts.json',
    BASE/'candidate-1800-v1/source-policy.json',
    ROOT/'benchmarks/parallel-search-20261006/four_d/source-03/dhatupradipa-clean.txt',
    ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01/independent-source-cache/1.2.1.html',
    HERE/'Anthropic-sources/index.json']
inputs += sorted((HERE/'Anthropic-sources').glob('*.html'))
result={'schema':'bounded-source-adjudication-v1','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'provider':'Anthropic','source_review_scope':'All214 unrecognized usable answers and all5 refusals; no sample of successful answers newly certified.',
    'all_queue_rows_individually_mapped':True,'raw_scores_unchanged':True,'counts':dict(counts),
    'refusal_counts':{'total':5,'provider_explicit_cyber_category':5,'with_returned_grammar_summary':4},
    'source_corrections_accepted':0,'source_unresolved_indices':[r['index'] for r in rows if r['disposition']=='unresolved'],
    'group_counts':dict(collections.Counter(r['evidence_group'] for r in rows)),
    'concentration':{'all_noncorrect':219,'Cada_and_laja_errors':128,'Cada_and_laja_fraction_of_noncorrect':128/219,
        'five_short_stem_families_errors':187,'five_short_stem_fraction_of_noncorrect':187/219,
        'warning':'The755-family coverage does not imply uniformly distributed difficulty; two lexical families account for most observed errors.'},
    'score_accounting':{'canonical_correct':1581,'n':1800,'canonical_accuracy':1581/1800,
        'source_sensitivity_if_all_six_unresolved_credited':1587/1800,
        'source_and_refusal_sensitivity_if_all_six_plus_five_credited':1592/1800,
        'conservative_short_stem_only_upper_bound':{'upheld_errors':187,'all_other_cases_credited':1613,'n':1800,'accuracy':1613/1800,
            'meaning':'Conditional source-uncertainty bound from187 independently supported wrong stems, even crediting every other usable mismatch and refusal. Not a new certified score.'},
        'limits':'No precision qualification: family dependence is large (~4.95 percentage-point family SE in the run analysis). This review does not validate all successful keys or remove source uncertainty.'},
    'evidence_groups':groups,'rows':rows,'refusals':refusals,
    'source_access_limitations':['New Jainqq scan retrieval attempts for Dhatupradipa37/44/52/59/121 returned HTTP403. Existing cached primary-book OCR is used explicitly as lexical navigation/transcription evidence; no claim of new visual verification of those pages.',
        'Earlier visually inspected hard-family SK/Madhaviya/Kshiratarangini controls are reused with their recorded limitations.',
        'No blanket grammatical-school exclusion. Broad exact-entry or commentary-scope conflicts remain unresolved.',
        'A complete derivation from explicit general rules can reject an incompatible submitted form without certifying an exhaustive gold union.'],
    'inputs':{rel(p):sha(p) for p in inputs},'provider_calls':0,'ledger_changes':0,'frozen_files_changed':False,
    'training_started':False,'review_complete_as_bounded_row_accounting':True,'full_linguistic_certification':False}
(HERE/'Anthropic-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'counts':dict(counts),'rows':len(rows),'refusals':len(refusals),'sha256':sha(HERE/'Anthropic-review.json')},indent=2))
