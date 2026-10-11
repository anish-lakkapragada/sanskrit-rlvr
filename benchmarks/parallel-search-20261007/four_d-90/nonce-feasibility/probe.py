"""Six offline API examples only; never creates benchmark tasks or split members."""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import vidyut
import vidyut.vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import Dhatu, Gana, Lakara, Pada, Prayoga, Purusha, Vacana, Vyakarana
from misc.vp_cartesian_task import entries_by_code, entry_scope_issue


OUT = Path(__file__).resolve().parent
SPECS = [
    ('dictionary-control-bhu', 'BU', 'Bhvadi', 'dictionary control'),
    ('unlisted-bhu-class', 'BU', 'Divadi', 'attested citation assigned an unlisted class'),
    ('dictionary-control-kala', 'kala', 'Curadi', 'dictionary short-a control'),
    ('invented-short-a', 'gavapa', 'Curadi', 'invented citation absent from this inventory'),
    ('invented-marked-a', 'gavapa~', 'Curadi', 'same spelling with explicit nasal it marker'),
    ('invented-marked-a-bhvadi', 'gavapa~', 'Bhvadi', 'same marked citation assigned another class'),
]
MORPHOLOGY = dict(lakara='Lat', prayoga='Kartari', purusha='Prathama', vacana='Eka')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    entries = entries_by_code()
    inventory = [dict(code=e.code, citation=e.dhatu.aupadeshika,
                      gana=e.dhatu.gana.name, meaning=e.artha, intrinsic=repr(e.dhatu))
                 for e in entries.values()]
    grammar = Vyakarana(log_steps=True, is_chandasi=False, use_svaras=False, nlp_mode=False)
    examples = []
    for label, citation, gana, description in SPECS:
        root = Dhatu.mula(citation, getattr(Gana, gana))
        assert root.antargana is None and not root.prefixes and not root.sanadi
        forms = grammar.derive(Pada.Tinanta(root, Prayoga.Kartari, Lakara.Lat,
                                           Purusha.Prathama, Vacana.Eka))
        full_union = sorted({p.text for p in forms})
        assert full_union
        exact = [e for e in entries.values()
                 if e.dhatu.aupadeshika == citation and e.dhatu.gana.name == gana]
        raw = [e.code for e in entries.values() if e.dhatu.aupadeshika == citation]
        assert bool(exact) == label.startswith('dictionary-control')
        if citation.startswith('gavap'):
            assert not raw
            assert not any(e.dhatu.aupadeshika.translate(str.maketrans('', '', '~^\\'))
                           == 'gavapa' for e in entries.values())
        dev = [transliterate(x, Scheme.Slp1, Scheme.Devanagari) for x in full_union]
        assert all(transliterate(d, Scheme.Devanagari, Scheme.Slp1) == s
                   for d, s in zip(dev, full_union))
        examples.append(dict(
            id=label, description=description,
            input=dict(aupadeshika_slp1=citation,
                       aupadeshika_devanagari=transliterate(citation, Scheme.Slp1, Scheme.Devanagari),
                       gana=gana, morphology=MORPHOLOGY),
            omitted_choices=dict(antargana=None, prefixes=[], sanadi=[], dhatu_pada=None),
            exact_dictionary_codes=[e.code for e in exact],
            same_raw_citation_any_class_codes=raw,
            dictionary_controls_scope_issues=[entry_scope_issue(e) for e in exact],
            meaning_received_by_mula=False,
            all_engine_forms_slp1=full_union, all_engine_forms_devanagari=dev,
            traces=[dict(output=p.text, steps=[dict(source=h.source.name, rule=h.code,
                                                   result=[str(x) for x in h.result])
                                              for h in p.history]) for p in forms],
            classical_licensing='dictionary control' if exact else 'not certified; formal engine extrapolation',
        ))
    assert len(examples) == 6
    payload = dict(
        purpose='Bounded hypothetical-root feasibility, not benchmark membership or authorization',
        provider_calls=0, model_outputs_read=0, dictionary_entries=len(entries),
        inventory_sha256=hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest(),
        vidyut_version=vidyut.__version__,
        native_binary=dict(path=vidyut.vidyut.__file__, sha256=digest(vidyut.vidyut.__file__)),
        helper_sha256=digest(__file__),
        shared_adapter_sha256=digest('misc/vp_cartesian_task.py'),
        mula_signature=str(inspect.signature(Dhatu.mula)),
        mula_docstring=Dhatu.mula.__doc__,
        examples=examples,
        limitations=[
            'Absence is checked against 2,229 installed dictionary entries, not all Sanskrit literature.',
            'Only Lat Kartari third-person singular is probed; no claim about other coordinates.',
            'Engine trace 1.3.1 records its input assumption, not independent lexical attestation.',
            'Full engine unions are preserved; linguistic and spelling completeness is not certified.',
            'No task IDs, dictionary codes, meanings, splits, or synthetic benchmark families are fabricated.',
        ],
    )
    (OUT / 'examples.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'examples': len(examples), 'dictionary_entries': len(entries),
                      'outputs': {e['id']: e['all_engine_forms_devanagari'] for e in examples}},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
