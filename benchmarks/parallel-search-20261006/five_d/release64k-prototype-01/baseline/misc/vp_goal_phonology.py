"""Explicit lexical phonology predicates for development-led construction sampling."""
from vidyut.prakriya import Vyakarana


def lexical_bases(dhatu):
    return tuple(sorted({p.text for p in Vyakarana().derive(dhatu)}))


def matches(entry, predicate):
    if predicate is None:
        return True
    if predicate != 'sibilant_initial':
        raise ValueError('Unreviewed phonological sampling predicate')
    bases = lexical_bases(entry.dhatu)
    return bool(bases) and all(base and base[0] in 'sSz' for base in bases)
