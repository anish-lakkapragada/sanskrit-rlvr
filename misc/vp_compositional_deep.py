"""Finite creation with reviewed alternating causative/desiderative chains.

Derived stems receive dhatu status (3.1.32). Causative and desiderative
operations can therefore be applied in their respective semantic contexts.
The restriction against a desiderative directly on an iccha-san stem (3.1.7
commentary) rules out san+san; each repeated san here follows a fresh nic.
These are formal grammar tasks, not assertions of textual attestation.
"""
import hashlib
import json

import vidyut
from vidyut.lipi import Scheme, transliterate
from vidyut.prakriya import DhatuPada, Pada, Prayoga, Sanadi, Vyakarana
from misc import vp_compositional as g
from misc.vp_goal_grammar import validate_prefixes

CONSTRUCTIONS = {
    "san_ric_san": ["san", "Ric", "san"],
    "ric_san_ric_san": ["Ric", "san", "Ric", "san"],
    "yan_ric_san_ric_san": ["yaN", "Ric", "san", "Ric", "san"],
    "ric_san_ric_san_ric_san": ["Ric", "san", "Ric", "san", "Ric", "san"],
}


def task_for(entry, split, construction, prefixes, coordinates, dhatu_pada=None):
    validate_prefixes(prefixes)
    ops = CONSTRUCTIONS[construction]
    assert all(a != "san" or b != "san" for a, b in zip(ops, ops[1:]))
    assert "yaN" not in ops[1:]
    dhatu = entry.dhatu.with_sanadi([getattr(Sanadi, op) for op in ops]).with_prefixes(prefixes)
    la, pu, va = coordinates
    ps = Vyakarana().derive(Pada.Tinanta(dhatu=dhatu, lakara=la, prayoga=Prayoga.Kartari,
        purusha=pu, vacana=va, dhatu_pada=getattr(DhatuPada, dhatu_pada) if dhatu_pada else None))
    gold = sorted({p.text for p in ps})
    if not gold or len(gold) > 64:
        return None
    devanagari = list(map(g.slp1_to_devanagari, gold))
    assert [transliterate(s, Scheme.Devanagari, Scheme.Slp1) for s in devanagari] == gold
    la, pu, va = map(g.old.name, coordinates)
    identity = [g.old.family(entry), ops, prefixes, la, pu, va]
    if dhatu_pada:
        identity.append(dhatu_pada)
    tid = ("finite-" if dhatu_pada else "comp-") + hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    morphology = {"lakara": la, "prayoga": "Kartari", "purusha": pu, "vacana": va}
    if dhatu_pada:
        morphology["dhatu_pada"] = dhatu_pada
    return {"id": tid, "dhatu": {"code": entry.code, "aupadeshika": entry.dhatu.aupadeshika,
                "gana": g.old.name(entry.dhatu.gana), "artha": entry.artha},
            "morphology": morphology,
            "derivation": {"sanadi": ops, "prefixes": prefixes, "order": "innermost_to_outermost"},
            "gold_slp1": gold, "gold_devanagari": devanagari,
            "prompt_version": "composition-v4-pada" if dhatu_pada else "composition-v3-fields",
            "campaign": {"root_family": g.old.family(entry), "split": split, "construction": construction,
                "trace_rule_ids": sorted({h.code for p in ps for h in p.history if g.old.name(h.source) == "Ashtadhyayi"}),
                "minimum_trace_steps": min(len(p.history) for p in ps), "gold_variants": len(gold),
                "vp_version": vidyut.__version__, "selection_reason": "score-independent draw from a specified operation chain",
                "audit_status": "engine_and_roundtrip_verified; formal construction review recorded separately"}}
