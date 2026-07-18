import Sanskrit

/-!
The reward-loop entry point:

    check <sentence in IAST> [lemma:case:number ...]

prints the five component judgments, the lemmas found, and — for each
optional constraint — whether some word realizes that lemma in that case
and number (how translation tasks verify who does what to whom). Exits 0
iff grammatical. Same definitions the theorems use, compiled for speed.
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

/-- Does any word of the sentence realize the constraint?
`lemma:case:number` (a nominal), `verb:lemma:person:number` (a finite
verb), or bare `lemma` (any reading). -/
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

def main (args : List String) : IO UInt32 := do
  match args with
  | [] => IO.println "usage: check <sentence> [lemma:case:number ...]"; return 2
  | sentence :: specs =>
    let r := report sentence
    let an := analyzeSentence sentence
    let b := fun (x : Bool) => if x then "1" else "0"
    let reqs := ",".intercalate (specs.map fun s => b (satisfies an s))
    IO.println s!"words={b r.words} verb={b r.verb} subject={b r.subject} \
adjective={b r.adjective} object={b r.object} reqs={reqs} \
lemmas={",".intercalate (r.lemmas.map toIAST)}"
    return if r.words && r.verb && r.subject && r.adjective && r.object then 0 else 1
