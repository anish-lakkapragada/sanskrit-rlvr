"""Targeted corruption of verified sentences, for post-edit and error-id tasks.

A corruption re-inflects exactly one word (or deletes a required object) of
a sentence known to be grammatical, producing a labeled minimal pair. The
non-negotiable step is verification: a candidate only counts if the Lean
checker actually rejects it — some plausible-looking corruptions (an oblique
case swap, a mismatched adjective that can read as a standalone nominal)
still parse, and must be discarded rather than mislabeled.

Sentences are token lists [{form, kind, lemma, slot}] where slot is
"case:num" (noun), "gender:case:num" (adj), "person:num" (verb), "" (ind /
pron) — the schema of data/dcs/corpus/mined_sentences.tsv; templated
sentences from tasks.py use the same shape.
"""

import random

from .lean import check, lexicon

CASES = ["nom", "acc", "ins", "dat", "abl", "gen", "loc"]
NUMS = ["sg", "du", "pl"]
PERSONS = ["3", "2", "1"]


def _sentence(tokens: list[dict]) -> str:
    return " ".join(t["form"] for t in tokens)


def _swap(tokens: list[dict], i: int, form: str) -> list[dict]:
    return [{**t, "form": form} if j == i else t for j, t in enumerate(tokens)]


def bare_lemma_specs(tokens: list[dict]) -> list[str]:
    """Constraint strings pinning every content word's lemma (pronoun forms
    are suppletive in the checker's analyses, so they are not pinned)."""
    return sorted({t["lemma"] for t in tokens if t["kind"] != "pron"})


def corruption_candidates(tokens: list[dict], rng: random.Random) -> list[dict]:
    """Unverified candidates: {tokens, sentence, bad_index, bad_surface, op}.
    bad_surface is None for deletions (error-id tasks need a nameable word).
    High-yield ops (agreement breaks) come first; oblique-case swaps and
    adjective-gender mismatches often still parse and mostly get filtered."""
    lex = lexicon()
    likely, unlikely = [], []

    def emit(pool, i, form, op, new_tokens=None):
        if form is not None and form == tokens[i]["form"]:
            return
        nt = new_tokens if new_tokens is not None else _swap(tokens, i, form)
        pool.append({"tokens": nt, "sentence": _sentence(nt), "bad_index": i,
                     "bad_surface": form, "op": op})

    for i, t in enumerate(tokens):
        if t["kind"] == "verb":
            p, n = t["slot"].split(":")
            for n2 in NUMS:
                if n2 != n:
                    for f in lex["verb"][t["lemma"]]["forms"].get((p, n2), [])[:1]:
                        emit(likely, i, f, "verb_number")
            for p2 in PERSONS:
                if p2 != p:
                    for f in lex["verb"][t["lemma"]]["forms"].get((p2, n), [])[:1]:
                        emit(likely, i, f, "verb_person")
        elif t["kind"] == "noun":
            c, n = t["slot"].split(":")
            for c2 in rng.sample(CASES, len(CASES)):
                if c2 != c:
                    for f in lex["noun"][t["lemma"]]["forms"].get((c2, n), [])[:1]:
                        # breaking nom/acc hits subject/object checks; swapping
                        # one oblique for another usually still parses
                        pool = likely if c in ("nom", "acc") else unlikely
                        emit(pool, i, f, "noun_case")
            for n2 in NUMS:
                if n2 != n:
                    for f in lex["noun"][t["lemma"]]["forms"].get((c, n2), [])[:1]:
                        pool = likely if c == "nom" else unlikely
                        emit(pool, i, f, "noun_number")
        elif t["kind"] == "adj":
            g, c, n = t["slot"].split(":")
            for g2 in ("m", "f", "n"):
                if g2 != g:
                    for f in lex["adj"][t["lemma"]]["forms"].get((g2, c, n), [])[:1]:
                        emit(unlikely, i, f, "adj_gender")

    # deleting the sole accusative of a transitive verb breaks the object check
    acc = [i for i, t in enumerate(tokens)
           if t["kind"] == "noun" and t["slot"].startswith("acc:")]
    has_trans = any(t["kind"] == "verb"
                    and lex["verb"][t["lemma"]]["extra"] == "t" for t in tokens)
    if has_trans and len(acc) == 1 and len(tokens) > 3:
        nt = [t for j, t in enumerate(tokens) if j != acc[0]]
        likely.append({"tokens": nt, "sentence": _sentence(nt),
                       "bad_index": acc[0], "bad_surface": None, "op": "drop_object"})

    rng.shuffle(likely)
    rng.shuffle(unlikely)
    return likely + unlikely


def verified_corruptions(tokens: list[dict], rng: random.Random, k: int = 1,
                         need_surface: bool = False) -> list[dict]:
    """Up to k corruptions the Lean checker actually rejects. With
    need_surface, only ops that leave a nameable wrong word (for error-id)."""
    out = []
    for cand in corruption_candidates(tokens, rng):
        if need_surface and cand["bad_surface"] is None:
            continue
        if not check(cand["sentence"])["grammatical"]:
            out.append(cand)
            if len(out) == k:
                break
    return out
