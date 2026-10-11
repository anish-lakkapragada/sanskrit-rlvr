"""Constrain a creation task to one explicit, engine-supported ending set."""
import hashlib
import json

from misc import vp_compositional as g
from misc.vp_compositional_prompt_v4 import render
from vidyut.prakriya import DhatuPada, Pada, Prayoga, Sanadi, Vyakarana
from vidyut.lipi import Scheme, transliterate


def task_for(entry, split, construction, prefixes, coordinates, dhatu_pada):
    # Reuse the established schema, then replace the oracle and identity with
    # those of the specified pada. An incompatible pada produces no task.
    task = g.task_for(entry, split, construction, prefixes, coordinates)
    if task is None:
        return None
    ops = g.CONSTRUCTIONS[construction]
    dhatu = entry.dhatu.with_sanadi([getattr(Sanadi, op) for op in ops]).with_prefixes(prefixes)
    la, pu, va = coordinates
    ps = Vyakarana().derive(Pada.Tinanta(dhatu=dhatu, lakara=la, prayoga=Prayoga.Kartari,
        purusha=pu, vacana=va, dhatu_pada=getattr(DhatuPada, dhatu_pada)))
    gold = sorted({p.text for p in ps})
    if not gold or len(gold) > 64:
        return None
    assert set(gold) <= set(task["gold_slp1"])
    devanagari = list(map(g.slp1_to_devanagari, gold))
    assert [transliterate(s, Scheme.Devanagari, Scheme.Slp1) for s in devanagari] == gold
    task["morphology"]["dhatu_pada"] = dhatu_pada
    identity = [task["campaign"]["root_family"], ops, prefixes, *map(g.old.name, coordinates), dhatu_pada]
    task["id"] = "finite-" + hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]
    task.update(gold_slp1=gold, gold_devanagari=devanagari, prompt_version="composition-v4-pada")
    task["campaign"].update(
        trace_rule_ids=sorted({h.code for p in ps for h in p.history if g.old.name(h.source) == "Ashtadhyayi"}),
        minimum_trace_steps=min(len(p.history) for p in ps), gold_variants=len(gold),
        prompt_sha256=hashlib.sha256(render(task).encode()).hexdigest())
    return task
