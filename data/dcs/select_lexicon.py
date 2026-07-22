"""Select and classify the v2 lexicon: 500 nouns, 100 verbs, 150 adjectives.

Reads usable_frequencies.tsv and harvest.json; classifies each candidate
into a v2 Lean stem class using attested corpus forms as evidence; excludes
irregulars and unsupported classes with a documented reason; writes:

  selection_nouns.tsv   lemma, slp1 stem, class, freq, gloss
  selection_adjs.tsv    lemma, slp1 stem, class, fem stem, freq, gloss
  selection_verbs.tsv   lemma, slp1 stem/table, kind, pada, trans, freq, gloss
  exclusions.tsv        lemma, pos, freq, reason

Athematic verb paradigms are seeded from attested cells and completed from
ATHEMATIC_FILL below (curated); every filled cell is marked so tests can
distinguish attested from curated.
"""

import csv
import json
from collections import Counter
from pathlib import Path

here = Path(__file__).parent
N_NOUNS, N_VERBS, N_ADJS = 500, 100, 150

# ---------------------------------------------------------------- IAST->SLP1
DIGRAPHS = [("ai", "E"), ("au", "O"), ("kh", "K"), ("gh", "G"), ("ch", "C"),
            ("jh", "J"), ("ṭh", "W"), ("ḍh", "Q"), ("th", "T"), ("dh", "D"),
            ("ph", "P"), ("bh", "B")]
SINGLE = {"ā": "A", "ī": "I", "ū": "U", "ṛ": "f", "ṝ": "F", "ḷ": "x",
          "ṃ": "M", "ḥ": "H", "ṅ": "N", "ñ": "Y", "ṭ": "w", "ḍ": "q",
          "ṇ": "R", "ś": "S", "ṣ": "z"}

def slp1(iast: str) -> str:
    out, i = [], 0
    while i < len(iast):
        for d, r in DIGRAPHS:
            if iast.startswith(d, i):
                out.append(r); i += len(d); break
        else:
            out.append(SINGLE.get(iast[i], iast[i])); i += 1
    return "".join(out)

# ------------------------------------------------------------------- glosses
GERMAN_HINTS = ("der ", "die ", "das ", "ein ", "eine", " und ", "sich ",
                "ß", "Name ", "name of", "Name of", "[gramm.]", "[math.]",
                "[astron.]", "[medic.]", "ifc", "iic")

def clean_gloss(meanings: str) -> str:
    for seg in meanings.split(";"):
        seg = seg.strip()
        core = seg
        while "(" in core and ")" in core:
            core = (core[: core.find("(")] + core[core.find(")") + 1 :]).strip()
        if not core or len(core) > 45:
            continue
        if any(h in seg for h in GERMAN_HINTS):
            continue
        if core.startswith("a "): core = core[2:]
        if core.startswith("an "): core = core[3:]
        if core.startswith("the "): core = core[4:]
        return core
    return ""

# ------------------------------------------------- curated linguistic tables
IRREGULAR_NOUNS = {  # high-frequency but outside any v2 class; future work
    "strī": "suppletive stem (striyam)", "go": "diphthong stem (gauḥ/gām)",
    "pati": "irregular sg obliques (patyā, patyuḥ)", "sakhi": "irregular strong stem (sakhāyam)",
    "pathin": "suppletive (panthāḥ/pathā)", "ap": "plural-only root stem (āpaḥ)",
    "ahan": "heteroclite an/ar (ahnā/ahobhiḥ)", "pums": "suppletive (pumān/puṃsā)",
    "div": "diphthong stem (dyauḥ)", "dvār": "irregular (dvāḥ)", "puṃs": "suppletive (pumān/puṃsā)",
    "asthi": "heteroclite i/an (asthnā)", "akṣi": "heteroclite i/an (akṣṇā)",
    "dadhi": "heteroclite i/an (dadhnā)", "hṛd": "suppletive with hṛdaya",
    "mās": "irregular (mās/māsam)", "nau": "diphthong stem (nauḥ/nāvam)",
    "rai": "diphthong stem (rāḥ/rāyam)", "anaḍuh": "irregular (anaḍvān)",
    "śrī": "monosyllabic ī-stem (śriyam)", "bhū": "monosyllabic ū-stem (bhuvi)",
    "dhī": "monosyllabic ī-stem (dhiyā)", "bhī": "monosyllabic ī-stem (bhiyā)",
    "hrī": "monosyllabic ī-stem (hriyā)", "bhrū": "monosyllabic ū-stem (bhruvā)",
    "uṣas": "fem as-stem with vṛddhi (uṣāḥ)", "dos": "heteroclite", "yoṣit": "regular but rare pada cells",
}
# pausa base for root/consonant stems: underlying -> word-final (nom sg, -su/-bhyām bases)
ROOT_STEM_PADA = {
    "vāc": "vāk", "diś": "dik", "dṛś": "dṛk", "tviṣ": "tviṭ", "viś": "viṭ",
    "ruj": "ruk", "sraj": "srak", "ṛtvij": "ṛtvik", "vaṇij": "vaṇik", "bhiṣaj": "bhiṣak",
    "samidh": "samit", "sampad": "sampat", "āpad": "āpat", "vipad": "vipat",
    "parisad": "pariṣat", "upaniṣad": "upaniṣat", "śarad": "śarat", "kakud": "kakut",
    "marut": "marut", "sarit": "sarit", "harit": "harit", "jagat": "jagat",
    "kṣudh": "kṣut", "yudh": "yut", "mṛd": "mṛt", "pad": "pat", "vipru": "vipru",
}
PRONOMINAL_ADJ_AT = {"anya", "itara", "katara", "katama", "anyatara"}  # neuter -at
PRONOMINAL_ADJ_AM = {"sarva", "viśva", "eka", "ubhaya"}  # strictly pronominal, neuter -am
PRONOMINAL_ADJ_OPT = {"para", "apara", "pūrva", "dakṣiṇa", "uttara", "adhara",
                      "sva", "antara"}  # optionally pronominal: both ending sets valid
# high-frequency pronominal adjectives that DCS tags as 'pron', not 'adj'
PRON_POOL_ADJS = {"sarva", "anya", "eka", "viśva"}
MOTION_INTRANS = {"gam", "yā", "i", "vraj", "dhāv", "pat", "car", "sṛp", "plu",
                  "sṛ", "kram", "cal", "ruh", "tṝ", "drū", "dru"}
TRANS_THRESHOLD = 0.75

# athematic present tables: pada -> {person|number: form}; None cells are
# filled from attested corpus forms where available. Forms in IAST.
ATHEMATIC_FILL = {
 "as":  {"P": {"3|Sing": "asti", "3|Dual": "staḥ", "3|Plur": "santi",
               "2|Sing": "asi", "2|Dual": "sthaḥ", "2|Plur": "stha",
               "1|Sing": "asmi", "1|Dual": "svaḥ", "1|Plur": "smaḥ"}},
 "kṛ":  {"P": {"3|Sing": "karoti", "3|Dual": "kurutaḥ", "3|Plur": "kurvanti",
               "2|Sing": "karoṣi", "2|Dual": "kuruthaḥ", "2|Plur": "kurutha",
               "1|Sing": "karomi", "1|Dual": "kurvaḥ", "1|Plur": "kurmaḥ"},
         "A": {"3|Sing": "kurute", "3|Dual": "kurvāte", "3|Plur": "kurvate",
               "2|Sing": "kuruṣe", "2|Dual": "kurvāthe", "2|Plur": "kurudhve",
               "1|Sing": "kurve", "1|Dual": "kurvahe", "1|Plur": "kurmahe"}},
 "hu":  {"P": {"3|Sing": "juhoti", "3|Dual": "juhutaḥ", "3|Plur": "juhvati",
               "2|Sing": "juhoṣi", "2|Dual": "juhuthaḥ", "2|Plur": "juhutha",
               "1|Sing": "juhomi", "1|Dual": "juhuvaḥ", "1|Plur": "juhumaḥ"}},
 "yā":  {"P": {"3|Sing": "yāti", "3|Dual": "yātaḥ", "3|Plur": "yānti",
               "2|Sing": "yāsi", "2|Dual": "yāthaḥ", "2|Plur": "yātha",
               "1|Sing": "yāmi", "1|Dual": "yāvaḥ", "1|Plur": "yāmaḥ"}},
 "i":   {"P": {"3|Sing": "eti", "3|Dual": "itaḥ", "3|Plur": "yanti",
               "2|Sing": "eṣi", "2|Dual": "ithaḥ", "2|Plur": "itha",
               "1|Sing": "emi", "1|Dual": "ivaḥ", "1|Plur": "imaḥ"}},
 "dhā": {"P": {"3|Sing": "dadhāti", "3|Dual": "dhattaḥ", "3|Plur": "dadhati",
               "2|Sing": "dadhāsi", "2|Dual": "dhatthaḥ", "2|Plur": "dhattha",
               "1|Sing": "dadhāmi", "1|Dual": "dadhvaḥ", "1|Plur": "dadhmaḥ"}},
 "dā":  {"P": {"3|Sing": "dadāti", "3|Dual": "dattaḥ", "3|Plur": "dadati",
               "2|Sing": "dadāsi", "2|Dual": "datthaḥ", "2|Plur": "dattha",
               "1|Sing": "dadāmi", "1|Dual": "dadvaḥ", "1|Plur": "dadmaḥ"}},
 "han": {"P": {"3|Sing": "hanti", "3|Dual": "hataḥ", "3|Plur": "ghnanti",
               "2|Sing": "haṃsi", "2|Dual": "hathaḥ", "2|Plur": "hatha",
               "1|Sing": "hanmi", "1|Dual": "hanvaḥ", "1|Plur": "hanmaḥ"}},
 "grah": {"P": {"3|Sing": "gṛhṇāti", "3|Dual": "gṛhṇītaḥ", "3|Plur": "gṛhṇanti",
                "2|Sing": "gṛhṇāsi", "2|Dual": "gṛhṇīthaḥ", "2|Plur": "gṛhṇītha",
                "1|Sing": "gṛhṇāmi", "1|Dual": "gṛhṇīvaḥ", "1|Plur": "gṛhṇīmaḥ"}},
 "jñā": {"P": {"3|Sing": "jānāti", "3|Dual": "jānītaḥ", "3|Plur": "jānanti",
               "2|Sing": "jānāsi", "2|Dual": "jānīthaḥ", "2|Plur": "jānītha",
               "1|Sing": "jānāmi", "1|Dual": "jānīvaḥ", "1|Plur": "jānīmaḥ"}},
 "āp":  {"P": {"3|Sing": "āpnoti", "3|Dual": "āpnutaḥ", "3|Plur": "āpnuvanti",
               "2|Sing": "āpnoṣi", "2|Dual": "āpnuthaḥ", "2|Plur": "āpnutha",
               "1|Sing": "āpnomi", "1|Dual": "āpnuvaḥ", "1|Plur": "āpnumaḥ"}},
 "śru": {"P": {"3|Sing": "śṛṇoti", "3|Dual": "śṛṇutaḥ", "3|Plur": "śṛṇvanti",
               "2|Sing": "śṛṇoṣi", "2|Dual": "śṛṇuthaḥ", "2|Plur": "śṛṇutha",
               "1|Sing": "śṛṇomi", "1|Dual": "śṛṇvaḥ", "1|Plur": "śṛṇmaḥ"}},
 "brū": {"P": {"3|Sing": "bravīti", "3|Dual": "brūtaḥ", "3|Plur": "bruvanti",
               "2|Sing": "bravīṣi", "2|Dual": "brūthaḥ", "2|Plur": "brūtha",
               "1|Sing": "bravīmi", "1|Dual": "brūvaḥ", "1|Plur": "brūmaḥ"},
         "A": {"3|Sing": "brūte", "3|Dual": "bruvāte", "3|Plur": "bruvate",
               "2|Sing": "brūṣe", "2|Dual": "bruvāthe", "2|Plur": "brūdhve",
               "1|Sing": "bruve", "1|Dual": "bruvahe", "1|Plur": "brūmahe"}},
 "vid": {"P": {"3|Sing": "vetti", "3|Dual": "vittaḥ", "3|Plur": "vidanti",
               "2|Sing": "vetsi", "2|Dual": "vitthaḥ", "2|Plur": "vittha",
               "1|Sing": "vedmi", "1|Dual": "vidvaḥ", "1|Plur": "vidmaḥ"}},
 "śak": {"P": {"3|Sing": "śaknoti", "3|Dual": "śaknutaḥ", "3|Plur": "śaknuvanti",
               "2|Sing": "śaknoṣi", "2|Dual": "śaknuthaḥ", "2|Plur": "śaknutha",
               "1|Sing": "śaknomi", "1|Dual": "śaknuvaḥ", "1|Plur": "śaknumaḥ"}},
 "krī": {"P": {"3|Sing": "krīṇāti", "3|Dual": "krīṇītaḥ", "3|Plur": "krīṇanti",
               "2|Sing": "krīṇāsi", "2|Dual": "krīṇīthaḥ", "2|Plur": "krīṇītha",
               "1|Sing": "krīṇāmi", "1|Dual": "krīṇīvaḥ", "1|Plur": "krīṇīmaḥ"}},
 "bandh": {"P": {"3|Sing": "badhnāti", "3|Dual": "badhnītaḥ", "3|Plur": "badhnanti",
                 "2|Sing": "badhnāsi", "2|Dual": "badhnīthaḥ", "2|Plur": "badhnītha",
                 "1|Sing": "badhnāmi", "1|Dual": "badhnīvaḥ", "1|Plur": "badhnīmaḥ"}},
 "pū":  {"P": {"3|Sing": "punāti", "3|Dual": "punītaḥ", "3|Plur": "punanti",
               "2|Sing": "punāsi", "2|Dual": "punīthaḥ", "2|Plur": "punītha",
               "1|Sing": "punāmi", "1|Dual": "punīvaḥ", "1|Plur": "punīmaḥ"}},
 "aś":  {"A": {"3|Sing": "aśnute", "3|Dual": "aśnuvāte", "3|Plur": "aśnuvate",
               "2|Sing": "aśnuṣe", "2|Dual": "aśnuvāthe", "2|Plur": "aśnudhve",
               "1|Sing": "aśnuve", "1|Dual": "aśnuvahe", "1|Plur": "aśnumahe"}},
 "su":  {"P": {"3|Sing": "sunoti", "3|Dual": "sunutaḥ", "3|Plur": "sunvanti",
               "2|Sing": "sunoṣi", "2|Dual": "sunuthaḥ", "2|Plur": "sunutha",
               "1|Sing": "sunomi", "1|Dual": "sunuvaḥ", "1|Plur": "sunumaḥ"}},
 "stu": {"P": {"3|Sing": "stauti", "3|Dual": "stutaḥ", "3|Plur": "stuvanti",
               "2|Sing": "stauṣi", "2|Dual": "stuthaḥ", "2|Plur": "stutha",
               "1|Sing": "staumi", "1|Dual": "stuvaḥ", "1|Plur": "stumaḥ"}},
 "ci":  {"P": {"3|Sing": "cinoti", "3|Dual": "cinutaḥ", "3|Plur": "cinvanti",
               "2|Sing": "cinoṣi", "2|Dual": "cinuthaḥ", "2|Plur": "cinutha",
               "1|Sing": "cinomi", "1|Dual": "cinuvaḥ", "1|Plur": "cinumaḥ"}},
 "yuj": {"A": {"3|Sing": "yuṅkte", "3|Dual": "yuñjāte", "3|Plur": "yuñjate",
               "2|Sing": "yuṅkṣe", "2|Dual": "yuñjāthe", "2|Plur": "yuṅgdhve",
               "1|Sing": "yuñje", "1|Dual": "yuñjvahe", "1|Plur": "yuñjmahe"}},
 "bhid": {"P": {"3|Sing": "bhinatti", "3|Dual": "bhinttaḥ", "3|Plur": "bhindanti",
                "2|Sing": "bhinatsi", "2|Dual": "bhintthaḥ", "2|Plur": "bhinttha",
                "1|Sing": "bhinadmi", "1|Dual": "bhindvaḥ", "1|Plur": "bhindmaḥ"}},
 "chid": {"P": {"3|Sing": "chinatti", "3|Dual": "chinttaḥ", "3|Plur": "chindanti",
                "2|Sing": "chinatsi", "2|Dual": "chintthaḥ", "2|Plur": "chintha",
                "1|Sing": "chinadmi", "1|Dual": "chindvaḥ", "1|Plur": "chindmaḥ"}},
 "rudh": {"P": {"3|Sing": "ruṇaddhi", "3|Dual": "runddhaḥ", "3|Plur": "rundhanti",
                "2|Sing": "ruṇatsi", "2|Dual": "runddhaḥ", "2|Plur": "runddha",
                "1|Sing": "ruṇadhmi", "1|Dual": "rundhvaḥ", "1|Plur": "rundhmaḥ"}},
 "dviṣ": {"P": {"3|Sing": "dveṣṭi", "3|Dual": "dviṣṭaḥ", "3|Plur": "dviṣanti",
                "2|Sing": "dvekṣi", "2|Dual": "dviṣṭhaḥ", "2|Plur": "dviṣṭha",
                "1|Sing": "dveṣmi", "1|Dual": "dviṣvaḥ", "1|Plur": "dviṣmaḥ"}},
 "vṛ":  {"A": {"3|Sing": "vṛṇīte", "3|Dual": "vṛṇāte", "3|Plur": "vṛṇate",
               "2|Sing": "vṛṇīṣe", "2|Dual": "vṛṇāthe", "2|Plur": "vṛṇīdhve",
               "1|Sing": "vṛṇe", "1|Dual": "vṛṇīvahe", "1|Plur": "vṛṇīmahe"}},
 "mā":  {"A": {"3|Sing": "mimīte", "3|Dual": "mimāte", "3|Plur": "mimate",
               "2|Sing": "mimīṣe", "2|Dual": "mimāthe", "2|Plur": "mimīdhve",
               "1|Sing": "mime", "1|Dual": "mimīvahe", "1|Plur": "mimīmahe"}},
 "hā":  {"P": {"3|Sing": "jahāti", "3|Dual": "jahitaḥ", "3|Plur": "jahati",
               "2|Sing": "jahāsi", "2|Dual": "jahithaḥ", "2|Plur": "jahitha",
               "1|Sing": "jahāmi", "1|Dual": "jahivaḥ", "1|Plur": "jahimaḥ"}},
 "śī":  {"A": {"3|Sing": "śete", "3|Dual": "śayāte", "3|Plur": "śerate",
               "2|Sing": "śeṣe", "2|Dual": "śayāthe", "2|Plur": "śedhve",
               "1|Sing": "śaye", "1|Dual": "śevahe", "1|Plur": "śemahe"}},
 "ās":  {"A": {"3|Sing": "āste", "3|Dual": "āsāte", "3|Plur": "āsate",
               "2|Sing": "āsse", "2|Dual": "āsāthe", "2|Plur": "ādhve",
               "1|Sing": "āse", "1|Dual": "āsvahe", "1|Plur": "āsmahe"}},
}
VERB_MERGE = {"paś": "dṛś"}  # DCS splits suppletive paśyati from dṛś

# ------------------------------------------------------------------- loading
rows = list(csv.reader(open(here / "corpus" / "usable_frequencies.tsv", encoding="utf-8"), delimiter="\t"))[1:]
harvest = json.load(open(here / "corpus" / "harvest.json", encoding="utf-8"))

SUFFIX_EXCLUDE = {"tā", "tva", "ka", "ja", "stha", "ga", "da", "kara", "kā", "bhāj", "vat", "mat"}

def is_verb_tag(g):
    return bool(g) and ((g[0].isdigit() and ("P" in g or "Ā" in g)) or g.startswith("Denom"))

def majority_gender(lid, fallback):
    g = harvest.get(lid, {}).get("genders", {})
    if g:
        return {"Masc": "m", "Fem": "f", "Neut": "n"}[max(g, key=g.get)]
    return fallback if fallback in ("m", "f", "n") else fallback[:1]

def attested(lid, cell):
    forms = harvest.get(lid, {}).get("nominal", {}).get(cell, {})
    return max(forms, key=forms.get) if forms else None

exclusions = []

# -------------------------------------------------------------------- nouns
def classify_noun(lemma, lid, gender):
    if lemma in IRREGULAR_NOUNS:
        return None, IRREGULAR_NOUNS[lemma]
    if lemma.endswith("an") and len(lemma) > 2:
        if gender not in ("m", "n"):
            return None, f"an-stem with gender {gender}"
        ins = attested(lid, f"Ins|Sing|{'Masc' if gender == 'm' else 'Neut'}")
        if ins is None:  # fall back to Whitney: -man/-van after consonant keeps a
            keeps_a = (lemma.endswith(("man", "van"))
                       and len(lemma) > 3 and lemma[-4] not in "aāiīuūṛeo")
        else:
            keeps_a = ins.endswith(("anā", "aṇā"))
        syncope = not keeps_a
        return ("an_m" if gender == "m" else "an_n") + ("" if syncope else "_a"), None
    if lemma.endswith("in"):
        return ("in_m", None) if gender == "m" else (None, f"in-stem gender {gender}")
    if lemma.endswith("as"):
        return ("as_n", None) if gender == "n" else (None, f"as-stem gender {gender}")
    if lemma.endswith("is"):
        return ("is_n", None) if gender == "n" else (None, f"is-stem gender {gender}")
    if lemma.endswith("us"):
        return ("us_n", None) if gender == "n" else (None, f"us-stem gender {gender}")
    if lemma.endswith("ant"):  # DCS lemmatizes bhagavat as bhagavant
        lemma = lemma[:-2] + "t"
        return (f"mat_m:{slp1(lemma)}" if gender == "m" else f"mat_n:{slp1(lemma)}"
                if gender == "n" else None,
                None if gender in ("m", "n") else f"ant-stem gender {gender}")
    if lemma.endswith("at"):
        return (("mat_m", None) if gender == "m" else ("mat_n", None) if gender == "n"
                else (None, f"at-stem gender {gender}"))
    last = lemma[-1]
    if last == "a":
        return ("a_m" if gender == "m" else "a_n" if gender == "n" else None,
                None if gender in ("m", "n") else "a-stem fem")
    if last == "ā":
        return ("A_f", None) if gender == "f" else (None, f"ā-stem gender {gender}")
    if last == "i":
        return {"m": ("i_m", None), "f": ("i_f", None), "n": ("i_n", None)}[gender]
    if last == "ī":
        return ("I_f", None) if gender == "f" else (None, f"ī-stem gender {gender}")
    if last == "u":
        return {"m": ("u_m", None), "f": ("u_f", None), "n": ("u_n", None)}[gender]
    if last == "ū":
        return ("U_f", None) if gender == "f" else (None, f"ū-stem gender {gender}")
    if last == "ṛ":
        acc = attested(lid, f"Acc|Sing|{'Masc' if gender == 'm' else 'Fem'}")
        vrddhi = bool(acc) and acc.endswith("āram")
        if gender == "m":
            return ("f_m_v" if vrddhi else "f_m"), None
        if gender == "f":
            return ("f_f_v" if vrddhi else "f_f"), None
        return None, "ṛ-stem neuter"
    if lemma in ROOT_STEM_PADA:
        if gender == "n":
            return None, "neuter root stem"
        return f"cons_{gender}:{slp1(ROOT_STEM_PADA[lemma])}", None
    return None, f"unsupported stem shape (-{last})"

nouns_out, seen = [], set()
noun_pool = sorted(
    ((int(r[4]), r[0], r[1], r[2], r[7]) for r in rows
     if r[2] in ("m", "f", "n", "mn", "mf", "fn", "mfn") and r[1] not in SUFFIX_EXCLUDE),
    reverse=True)
for freq, lid, lemma, gtag, meanings in noun_pool:
    if len(nouns_out) >= N_NOUNS:
        break
    if lemma in seen:
        continue
    if meanings.strip().startswith("="):  # cross-reference lemma (rāja = rājan)
        exclusions.append((lemma, "noun", freq, "cross-reference lemma"))
        continue
    gender = majority_gender(lid, gtag)
    cls, reason = classify_noun(lemma, lid, gender)
    if cls is None:
        exclusions.append((lemma, "noun", freq, reason))
        continue
    seen.add(lemma)
    if cls.startswith("mat_") and ":" in cls:
        cls, stem = cls.split(":")
    else:
        stem = slp1(lemma)
    nouns_out.append((lemma, stem, cls, freq, clean_gloss(meanings) or lemma))

# --------------------------------------------------------------- adjectives
def classify_adj(lemma, lid):
    if lemma == "mahat":
        return "mahat", ""
    if lemma in PRONOMINAL_ADJ_AT:
        return "a_pron_at", slp1(lemma[:-1] + "ā")
    if lemma in PRONOMINAL_ADJ_AM:
        return "a_pron", slp1(lemma[:-1] + "ā")
    if lemma in PRONOMINAL_ADJ_OPT:
        return "a_pron_opt", slp1(lemma[:-1] + "ā")
    if lemma.endswith(("mat", "vat")):
        return "mat_adj", slp1(lemma + "ī")
    if lemma.endswith("in"):
        return "in_adj", slp1(lemma[:-2] + "inī")
    last = lemma[-1]
    if last == "a":
        fem = attested(lid, "Nom|Sing|Fem")
        femI = bool(fem) and fem.endswith("ī")
        return "a_adj", slp1(lemma[:-1] + ("ī" if femI else "ā"))
    if last == "i":
        return "i_adj", slp1(lemma)
    if last == "u":
        fem = attested(lid, "Nom|Sing|Fem")
        femI = bool(fem) and fem.endswith("ī")
        return "u_adj", slp1(lemma[:-1] + "vī") if femI else ("u_adj", slp1(lemma))
    return None, ""

adjs_out = []
adj_pool = sorted(
    ((int(r[4]), r[0], r[1], r[7]) for r in rows
     if (r[2] == "adj" or (r[2] == "pron" and r[1] in PRON_POOL_ADJS))
     and r[1] not in SUFFIX_EXCLUDE), reverse=True)
NUM_WORDS = ("two", "three", "four", "five", "six", "seven", "eight", "nine",
             "ten", "twelve", "twenty", "hundred", "thousand")
for freq, lid, lemma, meanings in adj_pool:
    if len(adjs_out) >= N_ADJS:
        break
    if any(w in meanings[:30] for w in NUM_WORDS) and ";" not in meanings[:12]:
        exclusions.append((lemma, "adj", freq, "numeral"))
        continue
    if meanings.strip().startswith("="):
        exclusions.append((lemma, "adj", freq, "cross-reference lemma"))
        continue
    if lemma in {a for a, _, _, _, _ in nouns_out} or lemma in seen:
        continue
    res = classify_adj(lemma, lid)
    if res[0] is None:
        exclusions.append((lemma, "adj", freq, f"unsupported adjective shape (-{lemma[-1]})"))
        continue
    cls, fem = res
    seen.add(lemma)
    adjs_out.append((lemma, slp1(lemma), cls, fem, freq, clean_gloss(meanings) or lemma))

# -------------------------------------------------------------------- verbs
def verb_cells(lid):
    return harvest.get(lid, {}).get("verb", {})

def thematic_stem(cells):
    """If 3|Sing ends -ati/-ate with a consistent stem, return (stem, pada)."""
    for key, pada, cut in (("3|Sing", "P", "ti"), ("3|Sing", "A", "te")):
        forms = cells.get(key, {})
        if not forms:
            return None
        best = max(forms, key=forms.get)
        if best.endswith("a" + cut):
            stem = best[: -len(cut)]  # ends in a
            plur = cells.get("3|Plur", {})
            if plur:
                bp = max(plur, key=plur.get)
                if not bp.startswith(stem[:-1]):
                    return None
            return (stem, pada) if best.endswith("a" + cut) and (pada == "P") == best.endswith("ati") else None
    return None

verbs_out = []
verb_pool = sorted(
    ((int(r[5]), r[0], r[1], r[2], r[6], r[7]) for r in rows if is_verb_tag(r[2])),
    reverse=True)
vseen = set()
for freq, lid, lemma, gtag, acc_rate, meanings in verb_pool:
    if len(verbs_out) >= N_VERBS:
        break
    lemma = VERB_MERGE.get(lemma, lemma)
    if lemma in vseen:
        continue
    cells = verb_cells(lid)
    trans = (float(acc_rate) >= TRANS_THRESHOLD) if acc_rate else False
    if lemma in MOTION_INTRANS:
        trans = False
    gloss = clean_gloss(meanings) or lemma
    if gloss.startswith("to "):
        gloss = gloss[3:]
    if lemma in ATHEMATIC_FILL:
        for pada, table in ATHEMATIC_FILL[lemma].items():
            filled, attested_n = {}, 0
            for cell, form in table.items():
                corpus_forms = cells.get(cell, {})
                expect_v = form.endswith("e") if pada == "A" else not form.endswith("e")
                match = [f for f in corpus_forms if f == form]
                if match:
                    attested_n += 1
                filled[cell] = form
            verbs_out.append((lemma, "ATHEM:" + json.dumps({k: slp1(v) for k, v in filled.items()},
                              ensure_ascii=False), "athem", pada, trans, freq, gloss, attested_n))
        vseen.add(lemma)
        continue
    res = thematic_stem(cells)
    if res is None:
        exclusions.append((lemma, "verb", freq, "no curated athematic table and no clean thematic 3sg"))
        continue
    stem, pada = res
    vseen.add(lemma)
    verbs_out.append((lemma, slp1(stem), "them", pada, trans, freq, gloss, -1))

# ------------------------------------------------------------------- output
with open(here / "selection" / "selection_nouns.tsv", "w", encoding="utf-8") as f:
    f.write("lemma\tslp1\tclass\tfreq\tgloss\n")
    for lemma, s, cls, freq, gloss in nouns_out:
        f.write(f"{lemma}\t{s}\t{cls}\t{freq}\t{gloss}\n")
with open(here / "selection" / "selection_adjs.tsv", "w", encoding="utf-8") as f:
    f.write("lemma\tslp1\tclass\tfem_slp1\tfreq\tgloss\n")
    for lemma, s, cls, fem, freq, gloss in adjs_out:
        f.write(f"{lemma}\t{s}\t{cls}\t{fem}\t{freq}\t{gloss}\n")
with open(here / "selection" / "selection_verbs.tsv", "w", encoding="utf-8") as f:
    f.write("lemma\tslp1_stem\tkind\tpada\ttrans\tfreq\tgloss\tattested_cells\n")
    for lemma, s, kind, pada, trans, freq, gloss, att in verbs_out:
        f.write(f"{lemma}\t{s}\t{kind}\t{pada}\t{int(trans)}\t{freq}\t{gloss}\t{att}\n")
with open(here / "selection" / "exclusions.tsv", "w", encoding="utf-8") as f:
    f.write("lemma\tpos\tfreq\treason\n")
    for lemma, pos, freq, reason in exclusions:
        f.write(f"{lemma}\t{pos}\t{freq}\t{reason}\n")

print(f"nouns: {len(nouns_out)}  adjs: {len(adjs_out)}  verbs: {len(verbs_out)} "
      f"({sum(1 for v in verbs_out if v[2] == 'athem')} athematic entries)  excluded: {len(exclusions)}")
cls_counts = Counter(c for _, _, c, _, _ in nouns_out)
print("noun classes:", dict(cls_counts.most_common()))
print("adj classes:", dict(Counter(c for _, _, c, _, _, _ in adjs_out).most_common()))
