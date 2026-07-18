import Sanskrit.Lexicon
import Sanskrit.Sandhi
import Sanskrit.Translit

/-!
# Sentence grammar

The judgment this whole library exists for:

    Grammatical "rāmo grāmaṃ gacchati"

A sentence (IAST, space-separated words, sandhi applied or not) is
grammatical when every word is a real inflected form, there is exactly one
finite verb, the subject agrees with it in person and number, adjectives
agree with a noun in gender/case/number, and a transitive verb has an
accusative object. `Grammatical` is decidable, so the check is a proof:

    example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide
-/

namespace Sanskrit

/-- One grammatical reading of a surface word. -/
structure Analysis where
  lemma?  : String
  pos     : String              -- "noun" | "adj" | "pron" | "verb" | "ind"
  gender  : Option Gender := none
  case?   : Option Case  := none
  number  : Option Number := none
  person  : Option Person := none
  trans   : Bool := false
  deriving Repr, DecidableEq

def allCases : List Case := [.nom, .acc, .ins, .dat, .abl, .gen, .loc, .voc]
def allNumbers : List Number := [.sg, .du, .pl]
def allPersons : List Person := [.third, .second, .first]

/-- Analyses of `w` as a form of noun `e`. -/
def nounAnalyses (e : NounEntry) (w : String) : List Analysis :=
  allCases.flatMap fun c => allNumbers.flatMap fun n =>
    if (decline e.stem e.cls c n).contains w then
      [{ lemma? := e.stem, pos := "noun", gender := some e.cls.gender,
         case? := some c, number := some n, person := some .third }]
    else []

/-- Analyses of `w` as adjective `e`, in each gender. -/
def adjAnalyses (e : AdjEntry) (w : String) : List Analysis :=
  let inClass (stem : String) (sc : StemClass) (g : Gender) : List Analysis :=
    allCases.flatMap fun c => allNumbers.flatMap fun n =>
      if (decline stem sc c n).contains w then
        [{ lemma? := e.stem, pos := "adj", gender := some g,
           case? := some c, number := some n }]
      else []
  inClass e.stem .a_m .m ++ inClass e.stem .a_n .n ++ inClass e.femStem e.femCls .f

/-- Analyses of `w` as a finite present form of verb `e`. -/
def verbAnalyses (e : VerbEntry) (w : String) : List Analysis :=
  allPersons.flatMap fun p => allNumbers.flatMap fun n =>
    if conjugate e.stem e.pada p n == w then
      [{ lemma? := e.lemma, pos := "verb", number := some n,
         person := some p, trans := e.trans }]
    else []

/-- The pronouns tad (that/he/she/it), aham (I), tvam (you) — suppletive,
so simply enumerated: (form, gender?, case, number, person). -/
def pronounForms : List (String × Option Gender × Case × Number × Person) :=
  -- tad masculine
  [("saH", some .m, .nom, .sg, .third), ("tO", some .m, .nom, .du, .third),
   ("te", some .m, .nom, .pl, .third),
   ("tam", some .m, .acc, .sg, .third), ("tAn", some .m, .acc, .pl, .third),
   ("tena", some .m, .ins, .sg, .third), ("tasya", some .m, .gen, .sg, .third),
   ("tasmin", some .m, .loc, .sg, .third), ("tezAm", some .m, .gen, .pl, .third),
   -- tad feminine
   ("sA", some .f, .nom, .sg, .third), ("tAH", some .f, .nom, .pl, .third),
   ("tAm", some .f, .acc, .sg, .third), ("tayA", some .f, .ins, .sg, .third),
   ("tasyAH", some .f, .gen, .sg, .third),
   -- tad neuter
   ("tat", some .n, .nom, .sg, .third), ("tat", some .n, .acc, .sg, .third),
   ("tAni", some .n, .nom, .pl, .third), ("tAni", some .n, .acc, .pl, .third),
   -- aham / tvam (genderless)
   ("aham", none, .nom, .sg, .first), ("vayam", none, .nom, .pl, .first),
   ("mAm", none, .acc, .sg, .first), ("mayA", none, .ins, .sg, .first),
   ("mama", none, .gen, .sg, .first),
   ("tvam", none, .nom, .sg, .second), ("yUyam", none, .nom, .pl, .second),
   ("tvAm", none, .acc, .sg, .second), ("tava", none, .gen, .sg, .second)]

def pronounAnalyses (w : String) : List Analysis :=
  pronounForms.flatMap fun (f, g, c, n, p) =>
    if f == w then
      [{ lemma? := f, pos := "pron", gender := g, case? := some c,
         number := some n, person := some p }]
    else []

/-- Every reading of one pausa word. -/
def wordAnalyses (w : String) : List Analysis :=
  nouns.flatMap (nounAnalyses · w)
  ++ adjectives.flatMap (adjAnalyses · w)
  ++ verbs.flatMap (verbAnalyses · w)
  ++ pronounAnalyses w
  ++ indeclinables.flatMap fun (f, _) =>
       if f == w then [{ lemma? := f, pos := "ind" }] else []

/-- Analyses of a surface token: union over its pausa restorations. -/
def tokenAnalyses (w : String) (next? : Option Char) : List Analysis :=
  ((pausaCandidates (restoreInitial w) next?).flatMap wordAnalyses).eraseDups

/-- Split an IAST sentence into SLP1 tokens and analyze each
(each token sees the next token's first sound, for sandhi undoing). -/
def analyzeSentence (iast : String) : List (List Analysis) :=
  let toks := ((iast.splitOn " ").map toSLP1).filter (·.length > 0)
  let restored := toks.map restoreInitial
  toks.zipIdx.map fun (t, i) =>
    let next? := match restored[i + 1]? with
                 | some nxt => if nxt.isEmpty then none else some nxt.front
                 | none => none
    tokenAnalyses t next?

-- The five component judgments -------------------------------------------

/-- Every word has at least one reading. -/
def wordsOk (an : List (List Analysis)) : Bool :=
  an.all (!·.isEmpty)

private def isVerbal (as' : List Analysis) : Bool :=
  as'.any (·.pos == "verb")

private def onlyVerbal (as' : List Analysis) : Bool :=
  !as'.isEmpty && as'.all (·.pos == "verb")

/-- Exactly one finite verb (a token whose only readings are verbal),
or a single ambiguous verbal token. -/
def oneVerb (an : List (List Analysis)) : Bool :=
  let definite := an.filter onlyVerbal
  let possible := an.filter isVerbal
  definite.length == 1 || (definite.isEmpty && possible.length == 1)

/-- Some nominative reading agrees with some verb reading in person and
number; 1st/2nd-person verbs may drop their subject (gacchāmi = 'I go'). -/
def subjectAgrees (an : List (List Analysis)) : Bool :=
  let verbs := (an.filter onlyVerbal).flatten.filter (·.pos == "verb")
  let verbs := if verbs.isEmpty then an.flatten.filter (·.pos == "verb") else verbs
  let noms := an.flatten.filter fun a =>
    a.pos != "verb" && a.case? == some .nom
  verbs.any (fun v => noms.any fun s =>
    v.person == s.person && v.number == s.number)
  || (verbs.any (fun v => v.person == some .first || v.person == some .second)
      && !noms.any (fun s => s.pos == "pron"
           && (s.person == some .first || s.person == some .second)))

/-- Every unambiguous adjective agrees with some noun/pronoun in
gender, case, and number. -/
def adjectivesAgree (an : List (List Analysis)) : Bool :=
  an.all fun as' =>
    if !as'.isEmpty && as'.all (·.pos == "adj") then
      as'.any fun a => an.any fun bs => bs.any fun b =>
        (b.pos == "noun" || b.pos == "pron")
        && (b.gender == a.gender || b.gender == none)
        && b.case? == a.case? && b.number == a.number
    else true

/-- A transitive verb needs an accusative somewhere (intransitives pass). -/
def objectOk (an : List (List Analysis)) : Bool :=
  let verbs := an.flatten.filter (·.pos == "verb")
  verbs.isEmpty
  || verbs.any (fun v => !v.trans)
  || an.flatten.any fun a => a.pos != "verb" && a.case? == some .acc

/-- All five judgments as a record (the reward reads these). -/
structure Report where
  words     : Bool
  verb      : Bool
  subject   : Bool
  adjective : Bool
  object    : Bool
  lemmas    : List String     -- every lemma seen (for content checks)
  deriving Repr

def report (iast : String) : Report :=
  let an := analyzeSentence iast
  { words := wordsOk an, verb := oneVerb an, subject := subjectAgrees an,
    adjective := adjectivesAgree an, object := objectOk an,
    lemmas := (an.flatten.map (·.lemma?)).eraseDups }

/-- The whole judgment as one Bool (what the compiled checker runs). -/
def grammaticalB (iast : String) : Bool :=
  let r := report iast
  r.words && r.verb && r.subject && r.adjective && r.object

/-- **The judgment.** A sentence of Sanskrit is grammatical iff this
proposition holds — and it is decidable, so Lean can check it:

    example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide
-/
def Grammatical (iast : String) : Prop :=
  grammaticalB iast = true

instance (s : String) : Decidable (Grammatical s) :=
  inferInstanceAs (Decidable (grammaticalB s = true))

end Sanskrit
