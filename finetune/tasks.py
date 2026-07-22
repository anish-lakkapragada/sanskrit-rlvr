"""Task generation from the Lean lexicon and the mined corpus — the data/ writer.

Six machine-checkable task families over the fragment:
  qa         inflect one form — noun, adjective, or verb (exact-match)
  cloze      restore a blanked word in a sentence, given its lemma
             (exact-match against every accepted form of that cell)
  error_id   name the one misinflected word in a sentence — or answer
             sādhu 'correct' when there is nothing wrong (exact-match)
  post_edit  fix a minimally corrupted sentence (graded: the checker's
             all-or-nothing verdict × lemma preservation × length damping)
  translate  templated English sentence, no vocabulary hints; verified
             structurally (right lemmas in the right cases, by Lean)
  compose    one sentence using 4-5 required words (grammar by Lean,
             coverage by constraint bits)

Sentence-shaped tasks draw from two sources: templated sentences built from
the lexicon, and real corpus sentences mined from the DCS
(data/dcs/corpus/mined_sentences.tsv). Real sentences carry a train/eval
split assigned by text hash at mining time; every task derived from a
sentence inherits that split, so no real sentence straddles the boundary.
Template semantics (which nouns pluralize, which sit in the locative) come
from corpus statistics (data/dcs/corpus/noun_traits.json), not hand lists.

`python -m finetune.tasks` regenerates everything under data/in_fragment/;
`--self-test` re-reads the written files and asserts the grading contract.
Every reference answer and every corruption is verified through the Lean
checker at generation time. data/out_of_fragment/ is written by
data/dcs/make_oof_cloze.py, not here.
"""

import argparse
import json
import random
from pathlib import Path

from .corrupt import bare_lemma_specs, verified_corruptions
from .lean import ROOT, check, lexicon
from .reward import SYSTEM, reward

DCS = ROOT / "data" / "dcs" / "corpus"

CASE_NAMES = {"nom": "nominative", "acc": "accusative", "ins": "instrumental",
              "dat": "dative", "abl": "ablative", "gen": "genitive",
              "loc": "locative", "voc": "vocative"}
NUM_NAMES = {"sg": "singular", "du": "dual", "pl": "plural"}
PERSON_NAMES = {"3": "third", "2": "second", "1": "first"}
GENDER_NAMES = {"m": "masculine", "f": "feminine", "n": "neuter"}

_IRREGULAR_PLURAL = {"man": "men", "wife": "wives", "child": "children",
                     "foot": "feet", "tooth": "teeth", "goose": "geese"}


def _plural(g):
    if g in _IRREGULAR_PLURAL:
        return _IRREGULAR_PLURAL[g]
    if g.endswith("y") and g[-2] not in "aeiou":
        return g[:-1] + "ies"
    if g.endswith(("s", "sh", "ch", "x")):
        return g + "es"
    return g + "s"


def _v3sg(g):
    if g.endswith(("s", "sh", "ch", "x", "o")):
        return g + "es"
    if g.endswith("y") and g[-2] not in "aeiou":
        return g[:-1] + "ies"
    return g + "s"


# --- pools -------------------------------------------------------------------

def build_pools() -> dict:
    lex = lexicon()
    traits = json.load(open(DCS / "noun_traits.json", encoding="utf-8"))
    mined = {"train": [], "eval": []}
    with open(DCS / "mined_sentences.tsv", encoding="utf-8") as fh:
        for line in fh.read().splitlines()[1:]:
            sent_id, split, source, sentence, tokens_json = line.split("\t")
            mined[split].append({"sent_id": sent_id, "source": source,
                                 "sentence": sentence,
                                 "tokens": json.loads(tokens_json)})
    nouns = list(lex["noun"].items())
    verbs = list(lex["verb"].items())
    return {
        "lex": lex, "traits": traits, "mined": mined,
        "nouns": nouns,
        "adjs": list(lex["adj"].items()),
        "verbs": verbs,
        # copular as/bhū make degenerate templated sentences; keep them for qa
        "sent_verbs": [(l, e) for l, e in verbs if l not in ("as", "bhū")],
        "give_verbs": [(l, e) for l, e in verbs
                       if e["extra"] == "t" and e["gloss"] in ("give", "offer")],
        "pron_adjs": [(l, e) for l, e in lex["adj"].items()
                      if l in ("sarva", "eka")],
    }


def _tr(P, lemma):
    return P["traits"].get(lemma, {})


def _num_for(P, rng, lemma, p_pl=0.4):
    return "pl" if (_tr(P, lemma).get("plural_ok") and rng.random() < p_pl) else "sg"


# --- templated sentence source (for post_edit / error_id / cloze) -------------

def simple_sentence(P, rng):
    """A small verified sentence with full token provenance, mirroring the
    mined-sentence schema. Returns (tokens, sentence) or None."""
    for _ in range(12):
        vl, v = rng.choice(P["sent_verbs"])
        sl, s = rng.choice(P["nouns"])
        sn = _num_for(P, rng, sl, 0.35)
        subj_forms = s["forms"].get(("nom", sn))
        vf = v["forms"].get(("3", sn))
        if not subj_forms or not vf:
            continue
        tokens = []
        if rng.random() < 0.35:
            al, a = rng.choice(P["adjs"])
            af = a["forms"].get((s["extra"], "nom", sn))
            if af:
                tokens.append({"form": af[0], "kind": "adj", "lemma": al,
                               "slot": f"{s['extra']}:nom:{sn}"})
        tokens.append({"form": subj_forms[0], "kind": "noun", "lemma": sl,
                       "slot": f"nom:{sn}"})
        if v["extra"] == "t":
            pool = [x for x in P["nouns"] if x[0] != sl and _tr(P, x[0]).get("acc_ok")]
            if not pool:
                continue
            ol, o = rng.choice(pool)
            on = _num_for(P, rng, ol, 0.3)
            tokens.append({"form": o["forms"][("acc", on)][0], "kind": "noun",
                           "lemma": ol, "slot": f"acc:{on}"})
        elif rng.random() < 0.4:
            pool = [x for x in P["nouns"] if x[0] != sl and _tr(P, x[0]).get("loc_ok")]
            if pool:
                ll, le = rng.choice(pool)
                tokens.append({"form": le["forms"][("loc", "sg")][0], "kind": "noun",
                               "lemma": ll, "slot": "loc:sg"})
        tokens.append({"form": vf[0], "kind": "verb", "lemma": vl, "slot": f"3:{sn}"})
        sentence = " ".join(t["form"] for t in tokens)
        if check(sentence)["grammatical"]:
            return tokens, sentence
    return None


# --- family builders (each returns a task dict or None) -----------------------

def gen_qa(P, rng):
    r = rng.random()
    if r < 0.4:
        lemma, e = rng.choice(P["nouns"])
        c, n = rng.choice(list(CASE_NAMES)), rng.choice(list(NUM_NAMES))
        gold = e["forms"].get((c, n))
        if not gold:
            return None
        q = (f"What is the {CASE_NAMES[c]} {NUM_NAMES[n]} of the "
             f"Sanskrit noun {lemma} ('{e['gloss']}')?")
    elif r < 0.75:
        lemma, e = rng.choice(P["verbs"])
        p, n = rng.choice(list(PERSON_NAMES)), rng.choice(list(NUM_NAMES))
        gold = e["forms"].get((p, n))
        if not gold:
            return None
        q = (f"What is the present tense, {PERSON_NAMES[p]} person "
             f"{NUM_NAMES[n]} of the Sanskrit verb {lemma} "
             f"('to {e['gloss']}')?")
    else:
        lemma, e = rng.choice(P["adjs"])
        g = rng.choice("mfn")
        c, n = rng.choice(list(CASE_NAMES)), rng.choice(list(NUM_NAMES))
        gold = e["forms"].get((g, c, n))
        if not gold:
            return None
        q = (f"What is the {GENDER_NAMES[g]} {CASE_NAMES[c]} {NUM_NAMES[n]} of "
             f"the Sanskrit adjective {lemma} ('{e['gloss']}')?")
    return {"type": "qa", "prompt": q, "gold": gold, "specs": [],
            "reference": gold[0]}


def _verified(task):
    """Sentence families only leave the generator if their reference answer
    earns the full reward — the grading contract, enforced at the source."""
    ok = reward({"type": task["type"], "gold": task["gold"],
                 "specs": task["specs"], "cap": task.get("cap")},
                f"<ans>{task['reference']}</ans>")
    return task if ok["reward"] == 1.0 else None


def gen_translate(P, rng):
    kind = rng.choices(
        ["sv", "svo", "loc", "saha", "gen", "dat", "pron", "coord", "neg"],
        weights=[10, 20, 12, 10, 12, 8, 10, 10, 8])[0]
    vl, v = rng.choice(P["sent_verbs"])
    trans = v["extra"] == "t"
    sl, s = rng.choice(P["nouns"])
    sn = _num_for(P, rng, sl)
    if ("nom", sn) not in s["forms"] or ("3", sn) not in v["forms"]:
        return None
    subj_sa, verb_sa = s["forms"][("nom", sn)][0], v["forms"][("3", sn)][0]
    subj_en = s["gloss"] if sn == "sg" else _plural(s["gloss"])
    verb_en = _v3sg(v["gloss"]) if sn == "sg" else v["gloss"]
    specs = [f"{sl}:nom:{sn}", f"verb:{vl}:3:{sn}"]
    parts, ref = None, None

    def obj_pick():
        pool = [x for x in P["nouns"] if x[0] != sl and _tr(P, x[0]).get("acc_ok")]
        ol, o = rng.choice(pool)
        on = _num_for(P, rng, ol, 0.3)
        return ol, o, on

    if kind in ("sv", "svo"):
        if kind == "svo" and not trans:
            return None
        if kind == "sv" and trans:
            return None
        adj_sa = ""
        if rng.random() < 0.45:
            al, a = rng.choice(P["adjs"])
            af = a["forms"].get((s["extra"], "nom", sn))
            if af:
                adj_sa = af[0] + " "
                specs.append(al)
                subj_en = f"{a['gloss']} {subj_en}"
        if trans:
            ol, o, on = obj_pick()
            specs.append(f"{ol}:acc:{on}")
            o_en = o["gloss"] if on == "sg" else _plural(o["gloss"])
            parts = f"The {subj_en} {verb_en} the {o_en}."
            ref = f"{adj_sa}{subj_sa} {o['forms'][('acc', on)][0]} {verb_sa}"
        else:
            parts = f"The {subj_en} {verb_en}."
            ref = f"{adj_sa}{subj_sa} {verb_sa}"
    elif kind == "loc":
        if trans:
            return None
        pool = [x for x in P["nouns"] if x[0] != sl and _tr(P, x[0]).get("loc_ok")]
        if not pool:
            return None
        ll, le = rng.choice(pool)
        specs.append(f"{ll}:loc:sg")
        parts = f"The {subj_en} {verb_en} in the {le['gloss']}."
        ref = f"{subj_sa} {le['forms'][('loc', 'sg')][0]} {verb_sa}"
    elif kind == "saha":
        if trans:
            return None
        pool = [x for x in P["nouns"] if x[0] != sl and _tr(P, x[0]).get("ins_ok")]
        if not pool:
            return None
        cl, ce = rng.choice(pool)
        specs += [f"{cl}:ins:sg", "saha"]
        parts = f"The {subj_en} {verb_en} with the {ce['gloss']}."
        ref = f"{ce['forms'][('ins', 'sg')][0]} saha {subj_sa} {verb_sa}"
    elif kind == "gen":
        pool = [x for x in P["nouns"] if x[0] != sl and _tr(P, x[0]).get("gen_ok")]
        if not pool:
            return None
        gl, ge = rng.choice(pool)
        specs.append(f"{gl}:gen:sg")
        if trans:
            ol, o, on = obj_pick()
            specs.append(f"{ol}:acc:{on}")
            o_en = o["gloss"] if on == "sg" else _plural(o["gloss"])
            parts = f"The {ge['gloss']}'s {subj_en} {verb_en} the {o_en}."
            ref = (f"{ge['forms'][('gen', 'sg')][0]} {subj_sa} "
                   f"{o['forms'][('acc', on)][0]} {verb_sa}")
        else:
            parts = f"The {ge['gloss']}'s {subj_en} {verb_en}."
            ref = f"{ge['forms'][('gen', 'sg')][0]} {subj_sa} {verb_sa}"
    elif kind == "dat":
        if not P["give_verbs"]:
            return None
        vl, v = rng.choice(P["give_verbs"])
        if ("3", "sg") not in v["forms"]:
            return None
        sl, s = rng.choice(P["nouns"])
        if ("nom", "sg") not in s["forms"]:
            return None
        ol, o, on = obj_pick()
        pool = [x for x in P["nouns"]
                if x[0] not in (sl, ol) and _tr(P, x[0]).get("dat_ok")]
        if not pool:
            return None
        rl, re_ = rng.choice(pool)
        specs = [f"{sl}:nom:sg", f"verb:{vl}:3:sg", f"{ol}:acc:{on}",
                 f"{rl}:dat:sg"]
        o_en = o["gloss"] if on == "sg" else _plural(o["gloss"])
        parts = (f"The {s['gloss']} {_v3sg(v['gloss'])} the {o_en} "
                 f"to the {re_['gloss']}.")
        ref = (f"{s['forms'][('nom', 'sg')][0]} {re_['forms'][('dat', 'sg')][0]} "
               f"{o['forms'][('acc', on)][0]} {v['forms'][('3', 'sg')][0]}")
    elif kind == "pron":
        if trans or not P["pron_adjs"]:
            return None
        al, a = rng.choice(P["pron_adjs"])
        pn = "pl" if al == "sarva" else "sg"
        if not _tr(P, sl).get("plural_ok") and pn == "pl":
            return None
        af = a["forms"].get((s["extra"], "nom", pn))
        vf = v["forms"].get(("3", pn))
        sf = s["forms"].get(("nom", pn))
        if not (af and vf and sf):
            return None
        specs = [f"{sl}:nom:{pn}", al, f"verb:{vl}:3:{pn}"]
        en_subj = _plural(s["gloss"]) if pn == "pl" else s["gloss"]
        en_v = v["gloss"] if pn == "pl" else _v3sg(v["gloss"])
        parts = (f"All the {en_subj} {en_v}." if al == "sarva"
                 else f"One {en_subj} {en_v}.")
        ref = f"{af[0]} {sf[0]} {vf[0]}"
    elif kind == "coord":
        conj_en, conj_sa = rng.choice([("and", "ca"), ("or", "vā"), ("but", "tu")])
        clauses, en_parts, sa_parts = [], [], []
        n_cl = 3 if (conj_sa == "ca" and rng.random() < 0.25) else 2
        used = set()
        for ci in range(n_cl):
            cvl, cv = rng.choice([x for x in P["sent_verbs"]
                                  if x[1]["extra"] != "t"])
            cnl, cn = rng.choice([x for x in P["nouns"] if x[0] not in used])
            used.add(cnl)
            cnum = _num_for(P, rng, cnl, 0.3)
            if ("nom", cnum) not in cn["forms"] or ("3", cnum) not in cv["forms"]:
                return None
            clauses.append((cnl, cn, cnum, cvl, cv))
        for ci, (cnl, cn, cnum, cvl, cv) in enumerate(clauses):
            en_s = cn["gloss"] if cnum == "sg" else _plural(cn["gloss"])
            en_v = _v3sg(cv["gloss"]) if cnum == "sg" else cv["gloss"]
            en_parts.append(f"the {en_s} {en_v}")
            sa = f"{cn['forms'][('nom', cnum)][0]}"
            if ci > 0:
                sa += f" {conj_sa}"
            sa += f" {cv['forms'][('3', cnum)][0]}"
            sa_parts.append(sa)
            specs_c = [f"{cnl}:nom:{cnum}", f"verb:{cvl}:3:{cnum}"]
            if ci == 0:
                specs = specs_c
            else:
                specs += specs_c
        specs.append(conj_sa)
        joiner = f" {conj_en} "
        parts = (en_parts[0].capitalize()[0] + en_parts[0][1:]).join([""])  # placeholder
        parts = "T" + (joiner.join(en_parts))[1:] + "."
        parts = parts[0].upper() + parts[1:]
        ref = " ".join(sa_parts)
    elif kind == "neg":
        if trans:
            return None
        specs.append("na")
        en_v = v["gloss"]
        parts = (f"The {subj_en} does not {en_v}." if sn == "sg"
                 else f"The {subj_en} do not {en_v}.")
        ref = f"{subj_sa} na {verb_sa}"
    if not parts or not ref:
        return None
    return _verified({
        "type": "translate", "specs": specs, "gold": [], "reference": ref,
        "cap": len(ref.split()) + 3,
        "prompt": f'Translate into Sanskrit (one sentence): "{parts}"'})


def gen_compose(P, rng):
    five = rng.random() < 0.3
    if five:
        (v1l, v1), (v2l, v2) = rng.sample(
            [x for x in P["sent_verbs"] if x[1]["extra"] != "t"], 2)
        (n1l, n1), (n2l, n2) = rng.sample(P["nouns"], 2)
        if any(("nom", "sg") not in n["forms"] for n in (n1, n2)) or \
           any(("3", "sg") not in v["forms"] for v in (v1, v2)):
            return None
        words = [(v1l, f"to {v1['gloss']}"), (n1l, n1["gloss"]),
                 (v2l, f"to {v2['gloss']}"), (n2l, n2["gloss"]), ("ca", "and")]
        specs = [v1l, n1l, v2l, n2l, "ca"]
        ref = (f"{n1['forms'][('nom', 'sg')][0]} {v1['forms'][('3', 'sg')][0]} "
               f"{n2['forms'][('nom', 'sg')][0]} ca {v2['forms'][('3', 'sg')][0]}")
        cap = 13
    else:
        vl, v = rng.choice(P["sent_verbs"])
        n1l, e1 = rng.choice(P["nouns"])
        n2l, e2 = rng.choice([x for x in P["nouns"] if x[0] != n1l])
        al, a = rng.choice(P["adjs"])
        obj = ("acc", "sg") if v["extra"] == "t" else ("loc", "sg")
        af = a["forms"].get((e1["extra"], "nom", "sg"))
        if not af or ("nom", "sg") not in e1["forms"] or obj not in e2["forms"] \
                or ("3", "sg") not in v["forms"]:
            return None
        words = [(vl, f"to {v['gloss']}"), (n1l, e1["gloss"]),
                 (n2l, e2["gloss"]), (al, a["gloss"])]
        specs = [vl, n1l, n2l, al]
        ref = (f"{af[0]} {e1['forms'][('nom', 'sg')][0]} "
               f"{e2['forms'][obj][0]} {v['forms'][('3', 'sg')][0]}")
        cap = 12
    rng.shuffle(words)
    wl = ", ".join(f"{w} ('{g}')" for w, g in words)
    return _verified({
        "type": "compose", "specs": specs, "gold": [], "reference": ref,
        "cap": cap,
        "prompt": ("Write one grammatically correct Sanskrit sentence "
                   f"using all of these words (inflect as needed): {wl}.")})


def _source_sentence(P, rng, pools_key, real: bool):
    """A (tokens, sentence, gloss-lookup) sentence source: a mined real
    sentence from the requested split, or a fresh templated one."""
    if real:
        m = rng.choice(P["mined"][pools_key])
        return m["tokens"], m["sentence"]
    made = simple_sentence(P, rng)
    return made if made else (None, None)


def _gloss(P, kind, lemma):
    return P["lex"][kind][lemma]["gloss"]


def gen_cloze(P, rng, split, real):
    tokens, _ = _source_sentence(P, rng, split, real)
    if not tokens:
        return None
    maskable = [i for i, t in enumerate(tokens)
                if t["kind"] in ("noun", "adj", "verb")
                and sum(1 for u in tokens if u["form"] == t["form"]) == 1]
    if not maskable:
        return None
    i = rng.choice(maskable)
    t = tokens[i]
    cell = tuple(t["slot"].split(":"))
    gold = P["lex"][t["kind"]][t["lemma"]]["forms"].get(cell, [])
    if t["form"] not in gold:
        return None
    blanked = " ".join("____" if j == i else u["form"]
                       for j, u in enumerate(tokens))
    kind_en = {"noun": "noun", "adj": "adjective", "verb": "verb"}[t["kind"]]
    return {"type": "cloze",
            "prompt": (f'Complete the Sanskrit sentence "{blanked}" by replacing '
                       f"____ with the correct form of the {kind_en} {t['lemma']} "
                       f"('{_gloss(P, t['kind'], t['lemma'])}'). "
                       "Output only that word."),
            "gold": gold, "specs": [], "reference": t["form"]}


def gen_post_edit(P, rng, split, real):
    tokens, sentence = _source_sentence(P, rng, split, real)
    if not tokens:
        return None
    cs = verified_corruptions(tokens, rng, k=1)
    if not cs:
        return None
    task = {"type": "post_edit",
            "prompt": ("The following Sanskrit sentence contains exactly one "
                       f'grammatical error: "{cs[0]["sentence"]}". Output the '
                       "corrected sentence, changing as little as possible."),
            "gold": [sentence], "specs": bare_lemma_specs(tokens),
            "reference": sentence, "cap": len(tokens) + 2,
            "corrupted": cs[0]["sentence"]}
    v = _verified(task)
    if v is None:
        return None
    # the design-review guarantee: echoing the corruption back scores ~0
    echo = reward({"type": "post_edit", "gold": task["gold"],
                   "specs": task["specs"], "cap": task["cap"]},
                  f"<ans>{cs[0]['sentence']}</ans>")
    return v if echo["task"] < 0.2 else None


def gen_error_id(P, rng, split, real, clean):
    tokens, sentence = _source_sentence(P, rng, split, real)
    if not tokens:
        return None
    if clean:
        shown, gold = sentence, ["sādhu"]
    else:
        cs = verified_corruptions(tokens, rng, k=1, need_surface=True)
        if not cs:
            return None
        shown, gold = cs[0]["sentence"], [cs[0]["bad_surface"]]
    return {"type": "error_id",
            "prompt": (f'The Sanskrit sentence "{shown}" may contain one '
                       "incorrectly inflected word. Output that word exactly "
                       "as it appears — or output sādhu if the sentence is "
                       "already correct."),
            "gold": gold, "specs": [], "reference": gold[0]}


# --- the data/ writer ---------------------------------------------------------

# per-file family quotas; real_* = how many draw from mined real sentences
MIXTURE = {
    "eval":       {"qa": 40, "cloze": 40, "error_id": 30, "post_edit": 50,
                   "translate": 50, "compose": 40,
                   "real": {"cloze": 25, "post_edit": 30, "error_id": 10}},
    "sft_valid":  {"qa": 10, "cloze": 8, "error_id": 8, "post_edit": 12,
                   "translate": 16, "compose": 10, "real": {}},
    "grpo_valid": {"qa": 10, "cloze": 8, "error_id": 8, "post_edit": 12,
                   "translate": 16, "compose": 10, "real": {}},
    "sft_train":  {"qa": 300, "cloze": 250, "error_id": 250, "post_edit": 400,
                   "translate": 500, "compose": 300,
                   "real": {"cloze": 120, "post_edit": 200, "error_id": 130}},
    "grpo_train": {"qa": 300, "cloze": 250, "error_id": 250, "post_edit": 400,
                   "translate": 500, "compose": 300,
                   "real": {"cloze": 120, "post_edit": 200, "error_id": 130}},
}
SPLIT_OF = {"eval": "eval", "sft_valid": "train", "grpo_valid": "train",
            "sft_train": "train", "grpo_train": "train"}
CLEAN_ERROR_ID_SHARE = 0.33   # error_id rows with nothing wrong (gold sādhu)


def make_file(name: str, P: dict, seen: set) -> list[dict]:
    quotas = MIXTURE[name]
    split = SPLIT_OF[name]
    rng = random.Random(f"sanskrit-v2:{name}")
    tasks = []

    def fill(family, n, gen, max_tries=60):
        made, tries = 0, 0
        while made < n and tries < n * max_tries:
            tries += 1
            t = gen()
            if t is None or t["prompt"] in seen:
                continue
            seen.add(t["prompt"])
            t.pop("corrupted", None)
            tasks.append(t)
            made += 1
        if made < n:
            print(f"  {name}/{family}: short {n - made} after {tries} tries")

    real_q = quotas["real"]
    for fam in ("qa", "translate", "compose", "cloze", "post_edit", "error_id"):
        n, r = quotas[fam], real_q.get(fam, 0)
        if fam == "qa":
            fill(fam, n, lambda: gen_qa(P, rng))
        elif fam == "translate":
            fill(fam, n, lambda: gen_translate(P, rng))
        elif fam == "compose":
            fill(fam, n, lambda: gen_compose(P, rng))
        elif fam == "cloze":
            fill(f"{fam}-real", r, lambda: gen_cloze(P, rng, split, True))
            fill(fam, n - r, lambda: gen_cloze(P, rng, split, False))
        elif fam == "post_edit":
            fill(f"{fam}-real", r, lambda: gen_post_edit(P, rng, split, True))
            fill(fam, n - r, lambda: gen_post_edit(P, rng, split, False))
        elif fam == "error_id":
            n_clean = round(n * CLEAN_ERROR_ID_SHARE)
            r_clean = min(r, n_clean)
            fill(f"{fam}-real", r_clean,
                 lambda: gen_error_id(P, rng, split, True, True))
            fill(f"{fam}-real", r - r_clean,
                 lambda: gen_error_id(P, rng, split, True, False))
            fill(f"{fam}-clean", n_clean - r_clean,
                 lambda: gen_error_id(P, rng, split, False, True))
            fill(fam, n - r - (n_clean - r_clean),
                 lambda: gen_error_id(P, rng, split, False, False))
    rng.shuffle(tasks)
    return tasks


def _spec_json(t):
    # the whole grading contract rides in this opaque string: Lean-judged
    # rewards use gold/specs/cap, the chrF++ control reward uses reference
    spec = {"type": t["type"], "gold": t["gold"],
            "specs": t["specs"], "reference": t["reference"]}
    if t.get("cap"):
        spec["cap"] = t["cap"]
    return json.dumps(spec, ensure_ascii=False)


def _write(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{path.relative_to(ROOT)}: {len(rows)}")


def eval_row(t, i, judge):
    row = {"id": f"e{i}", "type": t["type"], "prompt": t["prompt"],
           "system": SYSTEM, "judge": judge, "gold": t["gold"],
           "specs": t["specs"], "reference": t["reference"]}
    if t.get("cap"):
        row["cap"] = t["cap"]
    return row


def sft_row(t):
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": t["prompt"]},
        {"role": "assistant", "content": f"<ans>{t['reference']}</ans>"}]}


def grpo_row(t):
    return {"prompt": t["prompt"], "system": SYSTEM, "type": t["type"],
            "answer": _spec_json(t)}


def main(self_test: bool = False):
    P = build_pools()
    seen: set[str] = set()
    files = {name: make_file(name, P, seen) for name in MIXTURE}
    _write(ROOT / "data/in_fragment/sft/train.jsonl",
           [sft_row(t) for t in files["sft_train"]])
    _write(ROOT / "data/in_fragment/sft/valid.jsonl",
           [sft_row(t) for t in files["sft_valid"]])
    _write(ROOT / "data/in_fragment/grpo/train.jsonl",
           [grpo_row(t) for t in files["grpo_train"]])
    _write(ROOT / "data/in_fragment/grpo/valid.jsonl",
           [grpo_row(t) for t in files["grpo_valid"]])
    _write(ROOT / "data/in_fragment/eval.jsonl",
           [eval_row(t, i, "lean+chrf") for i, t in enumerate(files["eval"])])
    if self_test:
        run_self_test()


def run_self_test():
    """Re-read the written files and assert the grading contract."""
    from .common import read_jsonl
    eval_rows = read_jsonl(ROOT / "data/in_fragment/eval.jsonl")
    grpo = read_jsonl(ROOT / "data/in_fragment/grpo/train.jsonl")
    sft = read_jsonl(ROOT / "data/in_fragment/sft/train.jsonl")
    prompts = [r["prompt"] for r in eval_rows] + [r["prompt"] for r in grpo] \
        + [r["messages"][1]["content"] for r in sft]
    assert len(prompts) == len(set(prompts)), "duplicate prompts across files"
    rng = random.Random(0)
    checked = 0
    for r in eval_rows + rng.sample(grpo, 200):
        if "answer" in r:
            spec = json.loads(r["answer"])
            ref = spec["reference"]
        else:
            spec = {"type": r["type"], "gold": r["gold"], "specs": r["specs"],
                    "cap": r.get("cap")}
            ref = r["reference"]
        got = reward(spec, f"<ans>{ref}</ans>")
        assert got["reward"] == 1.0, (r.get("id"), spec, got)
        checked += 1
    types = sorted({r["type"] for r in eval_rows})
    print(f"self-test OK: {checked} gold answers score 1.0; "
          f"{len(prompts)} unique prompts; eval families: {types}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    main(self_test=args.self_test)
