import Sanskrit.Phonology

/-!
# Nominal morphology

Declension for the seven vowel-stem classes that dominate classical prose:
masculine/neuter a-stems, feminine ā-stems, masculine/feminine i-stems,
masculine u-stems, feminine ī-stems — 8 cases × 3 numbers, with the ṇatva
rule applied to every generated form. Endings replace the stem-final vowel.
A cell may hold accepted variants (mati dat. sg. mataye/matyai).
-/

namespace Sanskrit

inductive Case | nom | acc | ins | dat | abl | gen | loc | voc
  deriving DecidableEq, Repr

inductive Number | sg | du | pl
  deriving DecidableEq, Repr

inductive Gender | m | f | n
  deriving DecidableEq, Repr

inductive StemClass | a_m | a_n | A_f | i_m | i_f | u_m | I_f
  deriving DecidableEq, Repr

open Case Number

/-- The masculine a-stem row (deva), which the neuter also borrows. -/
private def aMasc : Case → Number → List String
  | nom, sg => ["aH"]   | nom, du => ["O"]      | nom, pl => ["AH"]
  | acc, sg => ["am"]   | acc, du => ["O"]      | acc, pl => ["An"]
  | ins, sg => ["ena"]  | ins, du => ["AByAm"]  | ins, pl => ["EH"]
  | dat, sg => ["Aya"]  | dat, du => ["AByAm"]  | dat, pl => ["eByaH"]
  | abl, sg => ["At"]   | abl, du => ["AByAm"]  | abl, pl => ["eByaH"]
  | gen, sg => ["asya"] | gen, du => ["ayoH"]   | gen, pl => ["AnAm"]
  | loc, sg => ["e"]    | loc, du => ["ayoH"]   | loc, pl => ["ezu"]
  | voc, sg => ["a"]    | voc, du => ["O"]      | voc, pl => ["AH"]

/-- The masculine i-stem row (agni), which the feminine mostly borrows. -/
private def iMasc : Case → Number → List String
  | nom, sg => ["iH"]   | nom, du => ["I"]      | nom, pl => ["ayaH"]
  | acc, sg => ["im"]   | acc, du => ["I"]      | acc, pl => ["In"]
  | ins, sg => ["inA"]  | ins, du => ["iByAm"]  | ins, pl => ["iBiH"]
  | dat, sg => ["aye"]  | dat, du => ["iByAm"]  | dat, pl => ["iByaH"]
  | abl, sg => ["eH"]   | abl, du => ["iByAm"]  | abl, pl => ["iByaH"]
  | gen, sg => ["eH"]   | gen, du => ["yoH"]    | gen, pl => ["InAm"]
  | loc, sg => ["O"]    | loc, du => ["yoH"]    | loc, pl => ["izu"]
  | voc, sg => ["e"]    | voc, du => ["I"]      | voc, pl => ["ayaH"]

/-- Endings (SLP1) that replace the stem-final vowel; variants listed. -/
def endings : StemClass → Case → Number → List String
  | .a_m, c, n => aMasc c n

  | .a_n, nom, sg => ["am"]   | .a_n, nom, du => ["e"]      | .a_n, nom, pl => ["Ani"]
  | .a_n, acc, sg => ["am"]   | .a_n, acc, du => ["e"]      | .a_n, acc, pl => ["Ani"]
  | .a_n, voc, sg => ["a"]    | .a_n, voc, du => ["e"]      | .a_n, voc, pl => ["Ani"]
  | .a_n, c, n => aMasc c n   -- all other cells match the masculine

  | .A_f, nom, sg => ["A"]    | .A_f, nom, du => ["e"]      | .A_f, nom, pl => ["AH"]
  | .A_f, acc, sg => ["Am"]   | .A_f, acc, du => ["e"]      | .A_f, acc, pl => ["AH"]
  | .A_f, ins, sg => ["ayA"]  | .A_f, ins, du => ["AByAm"]  | .A_f, ins, pl => ["ABiH"]
  | .A_f, dat, sg => ["AyE"]  | .A_f, dat, du => ["AByAm"]  | .A_f, dat, pl => ["AByaH"]
  | .A_f, abl, sg => ["AyAH"] | .A_f, abl, du => ["AByAm"]  | .A_f, abl, pl => ["AByaH"]
  | .A_f, gen, sg => ["AyAH"] | .A_f, gen, du => ["ayoH"]   | .A_f, gen, pl => ["AnAm"]
  | .A_f, loc, sg => ["AyAm"] | .A_f, loc, du => ["ayoH"]   | .A_f, loc, pl => ["Asu"]
  | .A_f, voc, sg => ["e"]    | .A_f, voc, du => ["e"]      | .A_f, voc, pl => ["AH"]

  | .i_m, c, n => iMasc c n

  | .i_f, acc, pl => ["IH"]
  | .i_f, ins, sg => ["yA"]
  | .i_f, dat, sg => ["aye", "yE"]
  | .i_f, abl, sg => ["eH", "yAH"]
  | .i_f, gen, sg => ["eH", "yAH"]
  | .i_f, loc, sg => ["O", "yAm"]
  | .i_f, c, n => iMasc c n   -- otherwise like the masculine i-stem

  | .u_m, nom, sg => ["uH"]   | .u_m, nom, du => ["U"]      | .u_m, nom, pl => ["avaH"]
  | .u_m, acc, sg => ["um"]   | .u_m, acc, du => ["U"]      | .u_m, acc, pl => ["Un"]
  | .u_m, ins, sg => ["unA"]  | .u_m, ins, du => ["uByAm"]  | .u_m, ins, pl => ["uBiH"]
  | .u_m, dat, sg => ["ave"]  | .u_m, dat, du => ["uByAm"]  | .u_m, dat, pl => ["uByaH"]
  | .u_m, abl, sg => ["oH"]   | .u_m, abl, du => ["uByAm"]  | .u_m, abl, pl => ["uByaH"]
  | .u_m, gen, sg => ["oH"]   | .u_m, gen, du => ["voH"]    | .u_m, gen, pl => ["UnAm"]
  | .u_m, loc, sg => ["O"]    | .u_m, loc, du => ["voH"]    | .u_m, loc, pl => ["uzu"]
  | .u_m, voc, sg => ["o"]    | .u_m, voc, du => ["U"]      | .u_m, voc, pl => ["avaH"]

  | .I_f, nom, sg => ["I"]    | .I_f, nom, du => ["yO"]     | .I_f, nom, pl => ["yaH"]
  | .I_f, acc, sg => ["Im"]   | .I_f, acc, du => ["yO"]     | .I_f, acc, pl => ["IH"]
  | .I_f, ins, sg => ["yA"]   | .I_f, ins, du => ["IByAm"]  | .I_f, ins, pl => ["IBiH"]
  | .I_f, dat, sg => ["yE"]   | .I_f, dat, du => ["IByAm"]  | .I_f, dat, pl => ["IByaH"]
  | .I_f, abl, sg => ["yAH"]  | .I_f, abl, du => ["IByAm"]  | .I_f, abl, pl => ["IByaH"]
  | .I_f, gen, sg => ["yAH"]  | .I_f, gen, du => ["yoH"]    | .I_f, gen, pl => ["InAm"]
  | .I_f, loc, sg => ["yAm"]  | .I_f, loc, du => ["yoH"]    | .I_f, loc, pl => ["Izu"]
  | .I_f, voc, sg => ["i"]    | .I_f, voc, du => ["yO"]     | .I_f, voc, pl => ["yaH"]

/-- Decline an SLP1 stem: drop its final vowel, attach each ending, retroflex. -/
def decline (stem : String) (sc : StemClass) (c : Case) (n : Number) : List String :=
  (endings sc c n).map fun e => natva ((stem.dropEnd 1).toString ++ e)

/-- The gender a stem class inflects. -/
def StemClass.gender : StemClass → Gender
  | .a_m | .i_m | .u_m => .m
  | .A_f | .i_f | .I_f => .f
  | .a_n => .n

end Sanskrit
