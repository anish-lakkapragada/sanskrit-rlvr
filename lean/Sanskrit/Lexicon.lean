import Sanskrit.Nouns
import Sanskrit.Verbs

/-!
# Lexicon

The vocabulary the formalization knows. Stems are SLP1; glosses drive the
English side of translation tasks. Adjectives carry an explicit feminine
stem class because a-stem adjectives split between -ā and -ī feminines.
-/

namespace Sanskrit

structure NounEntry where
  stem  : String
  cls   : StemClass
  gloss : String
  deriving Repr

structure AdjEntry where
  stem    : String      -- masculine a-stem; neuter declines a_n
  femStem : String
  femCls  : StemClass
  gloss   : String
  deriving Repr

structure VerbEntry where
  lemma : String        -- citation root
  stem  : String        -- thematic present stem, or "as"/"kf"
  pada  : Pada
  trans : Bool          -- takes an accusative object
  gloss : String        -- English infinitive without 'to'
  deriving Repr

def nouns : List NounEntry := [
  -- masculine a-stems
  ⟨"rAma",   .a_m, "Rāma"⟩,
  ⟨"deva",   .a_m, "god"⟩,      ⟨"nara",   .a_m, "man"⟩,
  ⟨"vIra",   .a_m, "hero"⟩,     ⟨"putra",  .a_m, "son"⟩,
  ⟨"bAla",   .a_m, "boy"⟩,      ⟨"nfpa",   .a_m, "king"⟩,
  ⟨"aSva",   .a_m, "horse"⟩,    ⟨"gaja",   .a_m, "elephant"⟩,
  ⟨"siMha",  .a_m, "lion"⟩,     ⟨"grAma",  .a_m, "village"⟩,
  ⟨"vfkza",  .a_m, "tree"⟩,     ⟨"candra", .a_m, "moon"⟩,
  ⟨"mArga",  .a_m, "road"⟩,     ⟨"Sizya",  .a_m, "pupil"⟩,
  ⟨"meGa",   .a_m, "cloud"⟩,    ⟨"dUta",   .a_m, "messenger"⟩,
  ⟨"kumAra", .a_m, "prince"⟩,   ⟨"vAnara", .a_m, "monkey"⟩,
  ⟨"sAgara", .a_m, "ocean"⟩,    ⟨"dIpa",   .a_m, "lamp"⟩,
  -- neuter a-stems
  ⟨"Pala",    .a_n, "fruit"⟩,   ⟨"vana",    .a_n, "forest"⟩,
  ⟨"jala",    .a_n, "water"⟩,   ⟨"pustaka", .a_n, "book"⟩,
  ⟨"kzetra",  .a_n, "field"⟩,   ⟨"gfha",    .a_n, "house"⟩,
  ⟨"puzpa",   .a_n, "flower"⟩,  ⟨"mitra",   .a_n, "friend"⟩,
  ⟨"jYAna",   .a_n, "knowledge"⟩, ⟨"satya", .a_n, "truth"⟩,
  ⟨"nagara",  .a_n, "city"⟩,    ⟨"ratna",  .a_n, "jewel"⟩,
  ⟨"patra",   .a_n, "leaf"⟩,    ⟨"yudDa",  .a_n, "battle"⟩,
  ⟨"vastra",  .a_n, "garment"⟩,
  -- feminine ā-stems
  ⟨"senA",  .A_f, "army"⟩,      ⟨"kanyA", .A_f, "girl"⟩,
  ⟨"mAlA",  .A_f, "garland"⟩,   ⟨"vidyA", .A_f, "learning"⟩,
  ⟨"kaTA",  .A_f, "story"⟩,     ⟨"BAzA",  .A_f, "language"⟩,
  ⟨"CAyA",  .A_f, "shadow"⟩,    ⟨"gaNgA", .A_f, "Ganges"⟩,
  ⟨"praBA", .A_f, "radiance"⟩,  ⟨"lIlA",  .A_f, "play"⟩,
  -- masculine i-stems
  ⟨"agni", .i_m, "fire"⟩,       ⟨"kavi", .i_m, "poet"⟩,
  ⟨"muni", .i_m, "sage"⟩,       ⟨"giri", .i_m, "mountain"⟩,
  ⟨"atiTi", .i_m, "guest"⟩,     ⟨"ari",  .i_m, "foe"⟩,
  ⟨"niDi", .i_m, "treasure"⟩,
  -- feminine i-stems
  ⟨"mati",   .i_f, "thought"⟩,  ⟨"Sakti", .i_f, "power"⟩,
  ⟨"SAnti",  .i_f, "peace"⟩,    ⟨"kIrti", .i_f, "fame"⟩,
  ⟨"gati",   .i_f, "motion"⟩,   ⟨"smfti", .i_f, "memory"⟩,
  -- masculine u-stems
  ⟨"guru",  .u_m, "teacher"⟩,   ⟨"paSu",  .u_m, "animal"⟩,
  ⟨"Satru", .u_m, "enemy"⟩,     ⟨"banDu", .u_m, "kinsman"⟩,
  ⟨"vAyu",  .u_m, "wind"⟩,      ⟨"SiSu",  .u_m, "child"⟩,
  -- feminine ī-stems
  ⟨"nadI",  .I_f, "river"⟩,     ⟨"devI",   .I_f, "goddess"⟩,
  ⟨"patnI", .I_f, "wife"⟩,      ⟨"pfTivI", .I_f, "earth"⟩,
  ⟨"kumArI", .I_f, "princess"⟩, ⟨"jananI", .I_f, "mother"⟩]

def adjectives : List AdjEntry := [
  ⟨"sundara", "sundarI", .I_f, "beautiful"⟩,
  ⟨"priya",   "priyA",   .A_f, "dear"⟩,
  ⟨"nava",    "navA",    .A_f, "new"⟩,
  ⟨"Sveta",   "SvetA",   .A_f, "white"⟩,
  ⟨"kfzRa",   "kfzRA",   .A_f, "black"⟩,
  ⟨"alpa",    "alpA",    .A_f, "small"⟩,
  ⟨"DIra",    "DIrA",    .A_f, "steadfast"⟩,
  ⟨"taruRa",  "taruRI",  .I_f, "young"⟩,
  ⟨"vfdDa",   "vfdDA",   .A_f, "old"⟩,
  ⟨"pApa",    "pApA",    .A_f, "wicked"⟩,
  ⟨"puRya",   "puRyA",   .A_f, "holy"⟩,
  ⟨"ugra",    "ugrA",    .A_f, "fierce"⟩,
  ⟨"ramya",   "ramyA",   .A_f, "delightful"⟩]

def verbs : List VerbEntry := [
  ⟨"BU",   "Bava",  .P, false, "become"⟩,
  ⟨"gam",  "gacCa", .P, false, "go"⟩,
  ⟨"paW",  "paWa",  .P, true,  "read"⟩,
  ⟨"vad",  "vada",  .P, true,  "speak"⟩,
  ⟨"dfS",  "paSya", .P, true,  "see"⟩,
  ⟨"nI",   "naya",  .P, true,  "lead"⟩,
  ⟨"smf",  "smara", .P, true,  "remember"⟩,
  ⟨"jIv",  "jIva",  .P, false, "live"⟩,
  ⟨"krIq", "krIqa", .P, false, "play"⟩,
  ⟨"pA",   "piba",  .P, true,  "drink"⟩,
  ⟨"KAd",  "KAda",  .P, true,  "eat"⟩,
  ⟨"liK",  "liKa",  .P, true,  "write"⟩,
  ⟨"rakz", "rakza", .P, true,  "protect"⟩,
  ⟨"DAv",  "DAva",  .P, false, "run"⟩,
  ⟨"as",   "as",    .P, false, "be"⟩,
  ⟨"kf",   "kf",    .P, true,  "do"⟩,
  ⟨"laB",  "laBa",  .A, true,  "obtain"⟩,
  ⟨"sev",  "seva",  .A, true,  "serve"⟩,
  ⟨"car",  "cara",  .P, false, "wander"⟩,
  ⟨"pat",  "pata",  .P, false, "fall"⟩,
  ⟨"yaj",  "yaja",  .P, true,  "worship"⟩,
  ⟨"Df",   "Dara",  .P, true,  "hold"⟩,
  ⟨"has",  "hasa",  .P, false, "laugh"⟩]

def indeclinables : List (String × String) := [
  ("ca", "and"), ("na", "not"), ("iti", "thus"), ("api", "also"),
  ("eva", "indeed"), ("atra", "here"), ("tatra", "there"),
  ("adya", "today"), ("sadA", "always"), ("tu", "but"), ("saha", "with")]

end Sanskrit
