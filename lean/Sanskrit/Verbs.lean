import Sanskrit.Phonology
import Sanskrit.Nouns

/-!
# Verbal morphology

Present tense (laṭ), both voices. Thematic verbs (classes 1/4/6/10 and
denominatives) are conjugated from their present stem by the ending
tables below. Athematic verbs (root, reduplicating, nasal and nu/nā
classes: as, dā, dhā, hu, śru, kṛ …) carry their nine present forms as
an explicit table in the lexicon entry — enumerated like all suppletive
morphology, and validated cell-by-cell against corpus attestations.
Persons follow the English convention (third = Sanskrit prathama-puruṣa).
-/

namespace Sanskrit

inductive Person | third | second | first
  deriving DecidableEq, Repr

inductive Pada | P | A   -- parasmaipada (active) / ātmanepada (middle)
  deriving DecidableEq, Repr

open Person Number

/-- Thematic endings, replacing the stem-final a. -/
def thematicEnding : Pada → Person → Number → String
  | .P, third,  sg => "ati"  | .P, third,  du => "ataH"  | .P, third,  pl => "anti"
  | .P, second, sg => "asi"  | .P, second, du => "aTaH"  | .P, second, pl => "aTa"
  | .P, first,  sg => "Ami"  | .P, first,  du => "AvaH"  | .P, first,  pl => "AmaH"
  | .A, third,  sg => "ate"  | .A, third,  du => "ete"   | .A, third,  pl => "ante"
  | .A, second, sg => "ase"  | .A, second, du => "eTe"   | .A, second, pl => "aDve"
  | .A, first,  sg => "e"    | .A, first,  du => "Avahe" | .A, first,  pl => "Amahe"

/-- Conjugate a thematic present stem (ends in a), with ṇatva applied. -/
def conjugate (stem : String) (pada : Pada) (p : Person) (n : Number) : String :=
  natva ((stem.dropEnd 1).toString ++ thematicEnding pada p n)

/-- An athematic paradigm: the nine present-indicative cells. -/
abbrev AthematicTable := List (Person × Number × String)

/-- Look up person/number in an athematic table. -/
def athematicForm (t : AthematicTable) (p : Person) (n : Number) : Option String :=
  (t.find? fun (p', n', _) => p' == p && n' == n).map (·.2.2)

end Sanskrit
