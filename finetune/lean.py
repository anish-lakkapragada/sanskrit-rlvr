"""Bridge to the Lean checker — the only judge in this project.

Every linguistic decision lives in lean/; this module just shells out to the
compiled binaries and caches. `check()` returns the full JSON diagnostics of
one sentence; `lexicon()` parses the exported form table (the single source
of truth for data generation), keyed by vocabulary tier.
"""

import json
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_BIN = ROOT / "lean" / ".lake" / "build" / "bin" / "check"
EXPORT_BIN = ROOT / "lean" / ".lake" / "build" / "bin" / "export"


@lru_cache(maxsize=200_000)
def check(sentence: str, constraints: tuple[str, ...] = ()) -> dict:
    """One judgment: {'grammatical', 'components', 'constraints', 'lemmas',
    'tokens'} straight from `lean/Check.lean --json`."""
    r = subprocess.run([CHECK_BIN, "--json", sentence, *constraints],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"grammatical": False, "components": {}, "constraints":
                [False] * len(constraints), "lemmas": [], "tokens": []}


@lru_cache(maxsize=1)
def lexicon() -> dict:
    """{'core': {'noun': {lemma: {...}}, ...}, 'heldout': {...}} from
    `lean/Export.lean` (TSV, one line per inflected form)."""
    out = subprocess.run([EXPORT_BIN], capture_output=True, text=True).stdout
    lex = {"core": {"noun": {}, "adj": {}, "verb": {}, "ind": {}},
           "heldout": {"noun": {}, "adj": {}, "verb": {}, "ind": {}}}
    for line in out.splitlines():
        kind, lemma, extra, gloss, slot1, slot2, form, tier = line.split("\t")
        e = lex[tier][kind].setdefault(lemma, {"gloss": gloss, "extra": extra,
                                               "forms": {}})
        key = (extra, slot1, slot2) if kind == "adj" else (slot1, slot2)
        e["forms"].setdefault(key, []).append(form)
    return lex
