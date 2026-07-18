import Sanskrit

/-!
`export` prints the whole lexicon with every inflected form as TSV, IAST —
the single source of truth the data generator reads. One line per form:

    kind  lemma(IAST)  extra  gloss  slot1  slot2  form(IAST)  tier

where `tier` is `core` (may appear in training data) or `heldout`
(evaluation-only vocabulary; the generalization benchmark).
-/

open Sanskrit

def caseName : Case → String
  | .nom => "nom" | .acc => "acc" | .ins => "ins" | .dat => "dat"
  | .abl => "abl" | .gen => "gen" | .loc => "loc" | .voc => "voc"

def numName : Number → String
  | .sg => "sg" | .du => "du" | .pl => "pl"

def personName : Person → String
  | .third => "3" | .second => "2" | .first => "1"

def genderName : Gender → String
  | .m => "m" | .f => "f" | .n => "n"

def emitNouns (entries : List NounEntry) (tier : String) : IO Unit := do
  for e in entries do
    for c in allCases do
      for n in allNumbers do
        for f in decline e.stem e.cls c n do
          IO.println s!"noun\t{toIAST e.stem}\t{genderName e.cls.gender}\t\
{e.gloss}\t{caseName c}\t{numName n}\t{toIAST f}\t{tier}"

def emitAdjs (entries : List AdjEntry) (tier : String) : IO Unit := do
  for e in entries do
    for (stem, sc, g) in [(e.stem, .a_m, Gender.m), (e.stem, .a_n, .n),
                          (e.femStem, e.femCls, .f)] do
      for c in allCases do
        for n in allNumbers do
          for f in decline stem sc c n do
            IO.println s!"adj\t{toIAST e.stem}\t{genderName g}\t{e.gloss}\t\
{caseName c}\t{numName n}\t{toIAST f}\t{tier}"

def emitVerbs (entries : List VerbEntry) (tier : String) : IO Unit := do
  for e in entries do
    for p in allPersons do
      for n in allNumbers do
        IO.println s!"verb\t{toIAST e.lemma}\t{if e.trans then "t" else "i"}\t\
{e.gloss}\t{personName p}\t{numName n}\t{toIAST (conjugate e.stem e.pada p n)}\t{tier}"

def main : IO Unit := do
  emitNouns nouns "core"
  emitNouns nounsHeldout "heldout"
  emitAdjs adjectives "core"
  emitAdjs adjectivesHeldout "heldout"
  emitVerbs verbs "core"
  emitVerbs verbsHeldout "heldout"
  for (f, gloss) in indeclinables do
    IO.println s!"ind\t{toIAST f}\t-\t{gloss}\t-\t-\t{toIAST f}\tcore"
