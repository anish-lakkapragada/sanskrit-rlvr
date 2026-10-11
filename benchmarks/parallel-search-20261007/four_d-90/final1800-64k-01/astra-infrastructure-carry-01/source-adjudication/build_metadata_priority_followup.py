"""Bounded input-only source review. No response, ledger, or scoring reads."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from misc.vp_cartesian_task import GRAMMAR, entries_by_code
from misc.vp_4d_gap06_source_audit import paths
from vidyut.prakriya import Dhatu, DhatuPada, Lakara, Pada, Prayoga, Purusha, Vacana

ROOT = Path.cwd()
OUT = ROOT / 'benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/astra-infrastructure-carry-01/source-adjudication'
CANDIDATE = ROOT / 'benchmarks/parallel-search-20261007/four_d-90/candidate-1800-v1'
CODES = ['06.0168', '04.0094', '04.0095', '04.0096', '04.0121', '08.0008', '01.0922']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def derive(dhatu, morphology, pada=None):
    return GRAMMAR.derive(Pada.Tinanta(dhatu=dhatu,
        lakara=getattr(Lakara, morphology['lakara']),
        prayoga=getattr(Prayoga, morphology['prayoga']),
        purusha=getattr(Purusha, morphology['purusha']),
        vacana=getattr(Vacana, morphology['vacana']), dhatu_pada=pada))


def main():
    dest = OUT / 'metadata-priority-followup.json'
    assert not dest.exists(), 'Additive review; preserve an existing receipt.'
    tasks = json.loads((CANDIDATE / 'tasks.json').read_text())
    metadata = json.loads((OUT / 'input-metadata-audit.json').read_text())
    families = {f['dhatu']['code']: f for f in metadata['families']}
    entries = entries_by_code()
    rows = []
    for code in CODES:
        selected = [(i, t) for i, t in enumerate(tasks) if t['dhatu']['code'] == code]
        assert len(selected) == 1
        index, task = selected[0]
        e = entries[code]
        m = task['morphology']
        ps = derive(e.dhatu, m)
        forms = sorted({p.text for p in ps})
        assert forms == sorted(task['gold_slp1'])
        pd = {str(p): sorted({x.text for x in derive(e.dhatu, m, p)}) for p in DhatuPada.choices()}
        assert set(forms) == {f for fs in pd.values() for f in fs}
        r = dict(code=code, index=index, index_basis='zero-based, matching input-metadata-audit.json',
            ordinal_1based=index + 1, task_id=task['id'], dhatu=task['dhatu'],
            morphology=m, prompt_sha256=task['campaign']['prompt_sha256'],
            canonical_gold_slp1=forms, canonical_gold_devanagari=task['gold_devanagari'],
            regeneration_matches=True, explicit_pada_union=pd,
            input_metadata_flags=families[code]['diagnostic_flags'],
            derivations=paths(ps))
        if code in ['06.0168', '04.0094', '04.0095', '04.0096', '04.0121']:
            citation = e.dhatu.aupadeshika
            altered = citation.replace('\\', '') if '\\' in citation else citation.replace('pu', 'pu\\', 1)
            alt = derive(Dhatu.mula(altered, e.dhatu.gana), m)
            r['literal_citation_counterfactual'] = dict(aupadeshika=altered,
                gold_slp1=sorted({p.text for p in alt}), derivations=paths(alt),
                warning='Diagnostic only, not a certified alternate entry: literal citation changes can disable lexical rule matching. Source rules decide permitted variants.')
        if code == '01.0922':
            r['underlying_identity_controls'] = []
            for underlying in ['01.1067', '02.0048']:
                ce = entries[underlying]
                cp = derive(ce.dhatu, m)
                r['underlying_identity_controls'].append(dict(code=underlying,
                    aupadeshika=ce.dhatu.aupadeshika, gana=str(ce.dhatu.gana),
                    artha=ce.artha, morphology=m, gold_slp1=sorted({p.text for p in cp}),
                    derivations=paths(cp)))
        rows.append(r)
    dispositions = {
      '01.0922': dict(disposition='propose_exact_lexical_identity_hold', affected_selected_inputs=1,
        reason='The primary printed commentary makes śrā a common reference to Bhvadi śrai (after ā substitution) and Adadi śrā, not an autonomous Bhvadi ā-final entry. The selected imperfect differs between those originals.',
        proposed_predicate="dhatu.code == '01.0922'", source_ids=['sk1938-p196'],
        source_gold_effect='Placeholder aSrAm agrees with Adadi02.0048; Bhvadi01.1067 gives aSrAyam. Do not silently remap the public identity or accept a union of distinct roots.',
        uncertainty='A future explicit dictionary mapping can settle the contract; this review proposes a hold rather than declaring a replacement gold.'),
      '08.0008': dict(disposition='retain_selected_full_union', affected_selected_inputs=1,
        reason='SK Tanadi1471 expressly gives vanute/vavane and records Parasmaipada vanoti/vavana according to Candra. The P branch is licensed for this very root.',
        source_ids=['sk-tanadi1471'], source_gold_effect='Retain vanizIran and vanyAsuH. Exact 3pl benedictive endings are general-rule inference from the printed pada alternatives.',
        uncertainty='The P opinion is explicitly attributed to Candra. A future single-school protocol would need an independently declared scope, not a flat-tag exclusion after scoring.'),
      '06.0168': dict(disposition='retain_selected_perfect_union_accent_provenance_qualified', affected_selected_inputs=1,
        reason='SK1433 expressly records both set and anit traditions for vid labhe. The selected perfect permits it independently of the future/periphrastic-future contrast.',
        source_ids=['sk-tudadi1433','perfect-it'], source_gold_effect='vivediTa/vividize remain unchanged in the counterfactual engine check and follow the perfect rules.',
        uncertainty='Do not infer one universally correct citation accent from the flat inventory. Competing traditions are explicit; this review certifies the selected forms, not every tense in every recension.'),
      '04.0094': dict(disposition='retain_selected_full_union_accent_provenance_qualified', affected_selected_inputs=1,
        reason='Nyasa7.2.45 calls the other radhadi roots udatta while identifying trp/drp as anudatta; optional it still applies. Kashika directly prints drogdha/drodha/drohita.',
        source_ids=['radhadi7.2.45','sk-divadi1197'], source_gold_effect='All three selected Lut2sg forms are supported by the printed stems plus regular asi. Removing the literal accent in VP loses lexical exceptions and is not grammatical evidence to delete two answers.',
        uncertainty='The online Dhatupatha transcription has a conflicting radhadi accent rubric. A critical-edition accent reconciliation remains open; selected gold is unaffected under the explicit optional-it rule.'),
      '04.0095': dict(disposition='retain_selected_form_accent_provenance_qualified', affected_selected_inputs=1,
        reason='Nyasa7.2.45 provides positive udatta evidence; SK1198 directly prints muhyati.',
        source_ids=['radhadi7.2.45','sk-divadi1197'], source_gold_effect='Selected Lat3sg muhyati is printed and is unchanged by the diagnostic root-accent edit.',
        uncertainty='Radhadi accent-recension discrepancy remains; it does not alter this present-tense form.'),
      '04.0096': dict(disposition='retain_selected_form_accent_provenance_qualified', affected_selected_inputs=1,
        reason='Nyasa7.2.45 provides positive udatta evidence; SK1199 directly prints snuhyati.',
        source_ids=['radhadi7.2.45','sk-divadi1197'], source_gold_effect='Selected Lan1sg asnuhyam follows the printed present stem and regular imperfect ending; counterfactual accent edit has no effect.',
        uncertainty='Radhadi accent-recension discrepancy remains; it does not alter this imperfect form.'),
      '04.0121': dict(disposition='retain_selected_form_inventory_accent_tag_not_adopted', affected_selected_inputs=1,
        reason='Dhatupatha explicitly lists pus vibhaage04.0121 among the asu-prabhrti roots and closes that group as udatta/udatteta. It is distinct from anudatta pus pustau04.0079.',
        source_ids=['dhatupatha-pus'], source_gold_effect='Supports set apozizyatAm. The invented anudatta counterfactual yields apokzyatAm, which this review does not adopt.',
        uncertainty='This positive group evidence is a primary-text transcription, not an independently checked printed critical edition. The exact conditional dual is rule inference; SK omits this alternate lexical reading.'),
    }
    for r in rows:
        r['source_disposition'] = dispositions[r['code']]
    sources = [
      dict(id='sk1938-p196',url='https://jainqq.org/explore/002377/200',
        scan='jna-shuth-followup-sources/sk1938-p200.jpg',
        scan_sha256=sha(OUT/'jna-shuth-followup-sources/sk1938-p200.jpg'),
        image_url='https://s3.us-east-2.wasabisys.com/jainqq-hq/96bc756f71dff90876b661e65a9a035c88a7c769a78dc02d49449b127c34d86f.jpg',
        independently_visually_read=True, locator='Printed196, bottom ghaṭādi listing',
        excerpt='श्रा पाके । श्रै इति कृतात्वस्य श्रा इत्यादादिकस्य च सामान्येनानुकरणम्'),
      dict(id='sk-tanadi1471',url='https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌५१-६०',
        locator='Tanadi1471',excerpt='वनु । याचने । वनुते । ववने । चान्द्रमते परस्मैपदी । वनोति । ववान'),
      dict(id='sk-tudadi1433',url='https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌४१-५०',
        locator='Tudadi1433',excerpt='व्याघ्रभूत्यादिमते सेट्कोऽयम् । वेदिता । भाष्यादिमतेऽनिट्कः । वेत्ता'),
      dict(id='radhadi7.2.45',url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.45.htm',
        locator='Kashika and Nyasa7.2.45',excerpt='एषु तृप्यतिदृप्यत्योरनुदात्तत्वादिट्प्रतिषेधे प्राप्ते शेषाणामुदात्तत्वान्नित्यमिटि प्राप्ते विकल्पार्थं वचनम्'),
      dict(id='sk-divadi1197',url='https://sa.wikisource.org/wiki/सिद्धान्तकौमुदी/प्रकरण‌४१-५०',
        locator='Divadi1197-1199', evidence='Direct drohita/drogdha/drodha, muhyati and snuhyati forms.'),
      dict(id='perfect-it',url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.13.htm',
        secondary_rule_url='https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.2.61.htm',
        evidence='Perfect it restrictions; vid labhe is not in the anit perfect exception group.'),
      dict(id='dhatupatha-pus',url='https://thevyasa.in/dhatupatha/',
        locator='Divadi04.0106 asu through04.0161 grdhu; exact04.0121 pus and closing group rubric',
        excerpt='४.१२१ पुषँ च । ... इत्यसुँ॑प्रभृतय उ॒दात्ता॑ उ॒दात्ते॑तः ।',
        limitation='Primary text transcription. Its radhadi accent rubric conflicts with Nyasa and is not treated as a critical-edition resolution for those other roots.')
    ]
    obj = dict(schema='input-only-metadata-priority-source-followup-v1',
      created_at=datetime.now(timezone.utc).isoformat(), status='bounded_review_complete',
      scope=dict(selected_families=7,selected_inputs=7,total_selected_panel=1800,
        selection='Exact code flags from all755-family input-only metadata audit; no outcome filtering.',
        outcomes_read=False, paid_calls=False, shared_or_frozen_edits=False,
        canonical_gold_is_not_a_model_answer=True),
      input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [CANDIDATE/'tasks.json',
        CANDIDATE/'public-prompts.json',OUT/'input-metadata-audit.json',
        ROOT/'misc/vp_cartesian_task.py',Path(__file__)]},
      summary=dict(proposed_identity_hold_codes=['01.0922'],proposed_identity_hold_inputs=1,
        selected_inputs_with_no_proposed_gold_change=6,
        no_automatic_gold_aliases_or_shared_policy_edits=True,
        outcomes_and_canonical_success_counts='Not read or inferred; apply any adopted hold symmetrically to every provider and correctness status.'),
      sources=sources, cases=rows,
      limitations=['A bounded source audit is not a general certification of every paradigm for these roots.',
        'Four accent cases preserve selected gold while leaving citation-recension provenance qualified.',
        'Transcribed primary text and printed image evidence are distinguished explicitly.',
        'A broad metadata mismatch is not sufficient to replace a source-supported accepted union.'])
    dest.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(path=str(dest.relative_to(ROOT)),sha256=sha(dest),n=len(rows),
        hold=rows[-1]['task_id']),indent=2))


if __name__ == '__main__':
    main()
