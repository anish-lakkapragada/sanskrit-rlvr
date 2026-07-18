import Sanskrit

/-!
The checker CLI — the single entry point the fine-tuning framework calls.

    check [--json] <sentence in IAST> [constraint ...]

Constraints: `lemma:case:number` (a nominal), `verb:lemma:person:number`
(a finite verb), or bare `lemma` (any reading). Handles sentences of any
length; k ca-coordinated clauses are licensed by k−1 ca particles.

Default output is one human-readable line; `--json` emits full diagnostics
(component judgments, constraint bits, per-token analyses). Exit code 0 iff
grammatical. Same definitions the kernel-checked theorems use.
-/

open Sanskrit

def parseCase : String → Option Case
  | "nom" => some .nom | "acc" => some .acc | "ins" => some .ins
  | "dat" => some .dat | "abl" => some .abl | "gen" => some .gen
  | "loc" => some .loc | "voc" => some .voc | _ => none

def parseNumber : String → Option Number
  | "sg" => some .sg | "du" => some .du | "pl" => some .pl | _ => none

def parsePerson : String → Option Person
  | "3" => some .third | "2" => some .second | "1" => some .first | _ => none

/-- Does any word of the sentence realize the constraint? -/
def satisfies (an : List (List Analysis)) (spec : String) : Bool :=
  match spec.splitOn ":" with
  | ["verb", l, p, n] =>
    match parsePerson p, parseNumber n with
    | some p', some n' => an.flatten.any fun a =>
        a.pos == "verb" && a.lemma? == toSLP1 l
        && a.person == some p' && a.number == some n'
    | _, _ => false
  | [l, c, n] =>
    match parseCase c, parseNumber n with
    | some c', some n' => an.flatten.any fun a =>
        a.lemma? == toSLP1 l && a.case? == some c' && a.number == some n'
    | _, _ => false
  | [l] => an.flatten.any (·.lemma? == toSLP1 l)
  | _ => false

-- JSON emission (strings here are IAST/ASCII; no escaping needed beyond quotes)
def jstr (s : String) : String := "\"" ++ s ++ "\""
def jbool (b : Bool) : String := if b then "true" else "false"
def jarr (xs : List String) : String := "[" ++ ",".intercalate xs ++ "]"

def caseTag : Case → String
  | .nom => "nom" | .acc => "acc" | .ins => "ins" | .dat => "dat"
  | .abl => "abl" | .gen => "gen" | .loc => "loc" | .voc => "voc"

def numTag : Number → String
  | .sg => "sg" | .du => "du" | .pl => "pl"

def personTag : Person → String
  | .third => "3" | .second => "2" | .first => "1"

def genderTag : Gender → String
  | .m => "m" | .f => "f" | .n => "n"

def analysisJson (a : Analysis) : String :=
  let opt (k : String) (v : Option String) :=
    match v with | some s => [jstr k ++ ":" ++ jstr s] | none => []
  "{" ++ ",".intercalate (
    [jstr "lemma" ++ ":" ++ jstr (toIAST a.lemma?),
     jstr "pos" ++ ":" ++ jstr a.pos]
    ++ opt "gender" (a.gender.map genderTag)
    ++ opt "case" (a.case?.map caseTag)
    ++ opt "number" (a.number.map numTag)
    ++ opt "person" (a.person.map personTag)) ++ "}"

def main (args : List String) : IO UInt32 := do
  let (json, args) := match args with
    | "--json" :: rest => (true, rest)
    | _ => (false, args)
  match args with
  | [] => IO.println "usage: check [--json] <sentence> [constraint ...]"; return 2
  | sentence :: specs =>
    let r := report sentence
    let an := analyzeSentence sentence
    let good := r.words && r.verb && r.subject && r.adjective && r.object
    if json then
      let comps := "{" ++ ",".intercalate [
        jstr "words" ++ ":" ++ jbool r.words,
        jstr "clauses" ++ ":" ++ jbool r.verb,
        jstr "subject" ++ ":" ++ jbool r.subject,
        jstr "adjective" ++ ":" ++ jbool r.adjective,
        jstr "object" ++ ":" ++ jbool r.object] ++ "}"
      let toks := ((sentence.splitOn " ").filter (!·.isEmpty)).zipIdx.map
        fun (t, i) =>
          "{" ++ jstr "surface" ++ ":" ++ jstr t ++ ","
              ++ jstr "analyses" ++ ":"
              ++ jarr ((an[i]?.getD []).map analysisJson) ++ "}"
      IO.println ("{" ++ ",".intercalate [
        jstr "grammatical" ++ ":" ++ jbool good,
        jstr "components" ++ ":" ++ comps,
        jstr "constraints" ++ ":" ++ jarr (specs.map (jbool ∘ satisfies an)),
        jstr "lemmas" ++ ":" ++ jarr (r.lemmas.map (jstr ∘ toIAST)),
        jstr "tokens" ++ ":" ++ jarr toks] ++ "}")
    else
      let b := fun (x : Bool) => if x then "1" else "0"
      let reqs := ",".intercalate (specs.map fun s => b (satisfies an s))
      IO.println s!"words={b r.words} clauses={b r.verb} subject={b r.subject} \
adjective={b r.adjective} object={b r.object} reqs={reqs} \
lemmas={",".intercalate (r.lemmas.map toIAST)}"
    return if good then 0 else 1
