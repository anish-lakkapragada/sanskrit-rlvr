"""Reproduce source-given finite sanadi examples without model calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import vp_campaign_candidates as old
from misc.vp_cartesian_task import make_task
from misc.vp_5d_pilot import OUT, atomic_json, now, sha

BASE = 'https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/'
WHITNEY = 'https://en.wikisource.org/wiki/Sanskrit_Grammar_(Whitney)/Chapter_XIV'
CONTROLS = [
    ('08.0010', ['Ric'], 'Kartari', 'Prathama', 'kArayati', BASE + '3/3.1.26.htm', 'Causative example in the Kashika.'),
    ('08.0010', ['san'], 'Kartari', 'Prathama', 'cikIrzati', BASE + '3/3.1.7.htm', 'Desiderative example in the Kashika.'),
    ('01.1151', ['yaN'], 'Kartari', 'Prathama', 'pApacyate', BASE + '3/3.1.22.htm', 'Intensive example in the Kashika.'),
    ('01.1164', ['yaNluk'], 'Kartari', 'Prathama', 'vAvadIti', BASE + '2/2.4.74.htm', 'Classical finite intensive-luk example in the Kashika.'),
    ('02.0059', ['yaN', 'Ric'], 'Kartari', 'Uttama', 'vevidayAmi', WHITNEY + '#1025', 'Intensive-to-causative example; accents normalized away.'),
    ('02.0059', ['yaN', 'Ric', 'san'], 'Kartari', 'Uttama', 'vevidayizAmi', WHITNEY + '#1025', 'Intensive-to-causative-to-desiderative example; accents normalized away.'),
    ('01.1047', ['Ric'], 'Karmani', 'Prathama', 'DAryate', WHITNEY + '#1052', 'Causative passive example; accents normalized away.'),
    ('01.1047', ['Ric', 'san'], 'Kartari', 'Prathama', 'diDArayizati', WHITNEY + '#1052', 'Causative-desiderative supporting control outside the six-value pilot menu.'),
]


def main():
    es = {e.code: e for e in old.load_entries()}
    records = []
    for code, ops, voice, person, expected, source, note in CONTROLS:
        task = make_task(es[code], 'source_control', {'lakara': 'Lat', 'prayoga': voice,
            'purusha': person, 'vacana': 'Eka'}, recipe_id='source_control', sanadi=ops)
        gold = task['gold_slp1'] if task else []
        records.append({'code': code, 'aupadeshika': es[code].dhatu.aupadeshika,
            'sanadi': ops, 'morphology': task['morphology'], 'source_expected_slp1': expected,
            'vp_variants': gold, 'source_example_found': expected in gold, 'source': source, 'note': note})
    result = {'created_at': now(), 'vp_version': task['campaign']['vp_version'],
        'script_sha256': sha(Path(__file__)), 'checks': records,
        'passed': all(r['source_example_found'] for r in records),
        'limits': ['Source examples check selected expected forms, not all engine alternatives.',
                   'The 120 pilot gold sets require systematic-disagreement review before release.',
                   'Source controls are separate from model-evaluated pilot membership.']}
    atomic_json(OUT / 'pilot-01.source-checks.json', result)
    print(json.dumps({'passed': result['passed'], 'checks': len(records),
        'failures': [r for r in records if not r['source_example_found']]}, ensure_ascii=False))
    assert result['passed']


if __name__ == '__main__':
    main()
