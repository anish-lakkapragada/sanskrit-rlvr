"""Unpaid, source-led bhave controls; never load model answers or mutate policy."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import vidyut

from misc.vp_cartesian_task import entries_by_code, make_task, oracle_issue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/parallel-search-20261006/four_d/bhave-scope-review-01'
LAKARAS = ['Lat', 'Lit', 'Lut', 'Lrt', 'Lot', 'Lan', 'VidhiLin', 'AshirLin', 'Lun', 'Lrn']
CODES = ['01.0001', '01.0822', '01.1051', '02.0011', '02.0026']
# Direct examples in the cited grammatical commentaries; not model-selected.
EXAMPLES = [
    ('01.0001', 'Lit', 'baBUve', '1.3.13', 'Balamanorama'),
    ('01.0001', 'Lun', 'aBAvi', '3.1.66', 'Laghusiddhantakaumudi'),
    ('01.0822', 'Lat', 'hasyate', '3.4.69', 'Prathamavrtti'),
    ('01.1051', 'Lat', 'glAyate', '1.3.13', 'Kashika'),
    ('02.0011', 'Lat', 'Asyate', '3.4.69', 'Kashika'),
    ('02.0026', 'Lun', 'aSAyi', '3.1.66', 'Kashika'),
]


def main():
    target = OUT / 'controls.json'
    if target.exists():
        raise ValueError('Preserve previous source-control evidence')
    es = entries_by_code()
    controls = []
    indexed = {}
    for code in CODES:
        for lakara in LAKARAS:
            generated = {}
            for voice in ['Bhave', 'Karmani']:
                task = make_task(es[code], 'source_control', dict(
                    lakara=lakara, prayoga=voice, purusha='Prathama', vacana='Eka'))
                generated[voice] = dict(gold_slp1=task['gold_slp1'],
                    gold_devanagari=task['gold_devanagari'],
                    rule_3_1_66_present='3.1.66' in task['campaign']['trace_rule_ids'],
                    current_shared_scope_issue=oracle_issue(task))
            row = dict(code=code, citation=es[code].dhatu.aupadeshika, lakara=lakara,
                generated=generated,
                gold_sets_identical=generated['Bhave']['gold_slp1'] == generated['Karmani']['gold_slp1'])
            controls.append(row)
            indexed[code, lakara] = row
    direct = [dict(code=code, lakara=lakara, expected_slp1=gold,
        source_sutra=rule, commentary=commentary,
        bhave_contains_source_form=gold in indexed[code, lakara]['generated']['Bhave']['gold_slp1'])
        for code, lakara, gold, rule, commentary in EXAMPLES]
    report = dict(created_at=datetime.now(timezone.utc).isoformat(),
        vp_version=vidyut.__version__, generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        adapter_sha256=hashlib.sha256((ROOT/'misc/vp_cartesian_task.py').read_bytes()).hexdigest(),
        paid_calls=0, model_answers_read=False, shared_policy_modified=False,
        controls=controls, direct_source_examples=direct,
        summary=dict(paired_controls=len(controls),
            non_Lun_pairs=sum(r['lakara'] != 'Lun' for r in controls),
            non_Lun_identical=sum(r['lakara'] != 'Lun' and r['gold_sets_identical'] for r in controls),
            Lun_pairs=sum(r['lakara'] == 'Lun' for r in controls),
            Lun_identical=sum(r['lakara'] == 'Lun' and r['gold_sets_identical'] for r in controls)),
        limits=[
            'Karmani is an engine-comparison input, not a claim that these intransitive lexical uses license a personal passive.',
            'Five source-example families do not establish correctness or hardness of a broader Bhave pool.',
            'The source examples specify third-person singular impersonal agreement. No other person/number is proposed.',
            'Bhave/Lun is excluded from all proposed follow-up work. Existing paid pilot08 contains no Bhave and remains unchanged.',
            'Other tenses still require semantic scope and optional-variant checks; surface equivalence is not independent grammar certification.'
        ], benchmark_ready=False)
    OUT.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report['summary']))


if __name__ == '__main__':
    main()
