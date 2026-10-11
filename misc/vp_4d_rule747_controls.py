"""Recheck frozen caN/SAN source controls without rewriting their artifacts."""
import json
from pathlib import Path

from misc.vp_cartesian_task import GRAMMAR, entries_by_code
from vidyut.prakriya import Lakara, Pada, Prayoga, Purusha, Sanadi, Vacana

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'benchmarks/parallel-search-20261006/four_d/subset08-review/revision-01/rule747-positive-negative-controls.json'


def main():
    controls = json.loads(PATH.read_text())
    for c in controls:
        e = entries_by_code()[c['code']]
        dhatu = e.dhatu.with_sanadi([getattr(Sanadi, op) for op in c['ops']])
        rs = GRAMMAR.derive(Pada.Tinanta(dhatu=dhatu, lakara=getattr(Lakara, c['tense']),
            prayoga=Prayoga.Kartari, purusha=Purusha.Prathama, vacana=Vacana.Eka))
        derived = [dict(text=r.text, history=[dict(rule=h.code, terms=list(h.result)) for h in r.history]) for r in rs]
        assert derived == c['derivations']
        assert sorted({r.text for r in rs}) == c['forms']
        rbranches = [r for r in rs if any(h.code == '7.4.7' for h in r.history)]
        if c['tense'] != 'Lun':
            assert not rbranches
        elif not c['ops']:
            assert rbranches
            assert all(any('caN' in h.result for h in r.history) for r in rbranches)
        else:
            assert c['ops'] == ['san'] and rbranches
            assert not any('caN' in h.result for r in rs for h in r.history)
            assert all(any(h.code == '3.1.44' for h in r.history) for r in rs)
    print(f'{len(controls)} frozen controls exactly reproduced; caN present in ordinary7.4.7 branches and absent in san7.4.7 branches.')


if __name__ == '__main__':
    main()
