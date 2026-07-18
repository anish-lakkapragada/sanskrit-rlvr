import Sanskrit.Phonology
import Sanskrit.Nouns

/-!
# Verbal morphology

Present tense (laṭ), both voices, for thematic verbs (classes 1/4/6/10 —
conjugated from their present stem) plus the two indispensable irregulars
as 'to be' and kṛ 'to do'. Persons follow the English convention
(third = Sanskrit prathama-puruṣa).
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

/-- as 'to be' (root class 2, athematic). -/
def asForm : Person → Number → String
  | third,  sg => "asti"  | third,  du => "staH"  | third,  pl => "santi"
  | second, sg => "asi"   | second, du => "sTaH"  | second, pl => "sTa"
  | first,  sg => "asmi"  | first,  du => "svaH"  | first,  pl => "smaH"

/-- kṛ 'to do' (class 8). -/
def kfForm : Person → Number → String
  | third,  sg => "karoti"  | third,  du => "kurutaH"  | third,  pl => "kurvanti"
  | second, sg => "karozi"  | second, du => "kuruTaH"  | second, pl => "kuruTa"
  | first,  sg => "karomi"  | first,  du => "kurvaH"   | first,  pl => "kurmaH"

/-- Conjugate: `stem` is the thematic present stem (ends in a), or the
special markers "as" / "kf" for the irregulars. -/
def conjugate (stem : String) (pada : Pada) (p : Person) (n : Number) : String :=
  if stem == "as" then asForm p n
  else if stem == "kf" then kfForm p n
  else natva ((stem.dropEnd 1).toString ++ thematicEnding pada p n)

end Sanskrit
