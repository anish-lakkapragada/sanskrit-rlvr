import Sanskrit.Phonology

/-!
# Nominal morphology

Declension for the stem classes of classical prose. v2 extends the seven
vowel-stem classes of v1 (masculine/neuter a-stems, feminine ā-stems,
masculine/feminine i-stems, masculine u-stems, feminine ī-stems) with:

* the remaining vowel classes — neuter i/u-stems (vāri, madhu), feminine
  u/ū-stems (dhenu, vadhū);
* ṛ-stems, guṇa (pitṛ → pitaram) and vṛddhi (kartṛ → kartāram) grades,
  both genders;
* the big consonant families — an-stems with and without weak-stem
  syncope (rājan → rājñā vs ātman → ātmanā), in-stems (yogin), neuter
  s-stems (manas/havis/cakṣus), mat/vat-stems (bhagavat, with the mahat
  vṛddhi special), and root stems (vāc, diś — the entry supplies the
  word-final pada base, the engine derives its voiced counterpart);
* pronominal a-stem endings (sarva, anya; strict, -at neuter, and
  optional variants) used by pronominal adjectives.

Endings for vowel classes replace the stem-final vowel; consonantal
classes build on the full stem. The ṇatva rule is applied to every
generated form, and a cell may hold accepted variants (mataye/matyai).
-/

namespace Sanskrit

inductive Case | nom | acc | ins | dat | abl | gen | loc | voc
  deriving DecidableEq, Repr

inductive Number | sg | du | pl
  deriving DecidableEq, Repr

inductive Gender | m | f | n
  deriving DecidableEq, Repr

inductive StemClass
  | a_m | a_n | A_f | i_m | i_f | i_n | u_m | u_f | u_n | I_f | U_f
  | f_m | f_m_v | f_f | f_f_v
  | an_m | an_m_a | an_n | an_n_a
  | in_m | in_n | as_n | is_n | us_n | mat_m | mat_n
  | cons_m | cons_f
  | pron_m | pron_n | pron_n_at | pron_f
  | pron_opt_m | pron_opt_n | pron_opt_f
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

/-- The neuter a-stem row (vana). -/
private def aNeut : Case → Number → List String
  | nom, sg => ["am"]   | nom, du => ["e"]      | nom, pl => ["Ani"]
  | acc, sg => ["am"]   | acc, du => ["e"]      | acc, pl => ["Ani"]
  | voc, sg => ["a"]    | voc, du => ["e"]      | voc, pl => ["Ani"]
  | c, n => aMasc c n

/-- The feminine ā-stem row (senā). -/
private def AFem : Case → Number → List String
  | nom, sg => ["A"]    | nom, du => ["e"]      | nom, pl => ["AH"]
  | acc, sg => ["Am"]   | acc, du => ["e"]      | acc, pl => ["AH"]
  | ins, sg => ["ayA"]  | ins, du => ["AByAm"]  | ins, pl => ["ABiH"]
  | dat, sg => ["AyE"]  | dat, du => ["AByAm"]  | dat, pl => ["AByaH"]
  | abl, sg => ["AyAH"] | abl, du => ["AByAm"]  | abl, pl => ["AByaH"]
  | gen, sg => ["AyAH"] | gen, du => ["ayoH"]   | gen, pl => ["AnAm"]
  | loc, sg => ["AyAm"] | loc, du => ["ayoH"]   | loc, pl => ["Asu"]
  | voc, sg => ["e"]    | voc, du => ["e"]      | voc, pl => ["AH"]

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

/-- Pronominal a-stem endings, masculine (sarva → sarve, sarvasmai). -/
private def pronMasc : Case → Number → List String
  | nom, sg => ["aH"]    | nom, du => ["O"]      | nom, pl => ["e"]
  | acc, sg => ["am"]    | acc, du => ["O"]      | acc, pl => ["An"]
  | ins, sg => ["ena"]   | ins, du => ["AByAm"]  | ins, pl => ["EH"]
  | dat, sg => ["asmE"]  | dat, du => ["AByAm"]  | dat, pl => ["eByaH"]
  | abl, sg => ["asmAt"] | abl, du => ["AByAm"]  | abl, pl => ["eByaH"]
  | gen, sg => ["asya"]  | gen, du => ["ayoH"]   | gen, pl => ["ezAm"]
  | loc, sg => ["asmin"] | loc, du => ["ayoH"]   | loc, pl => ["ezu"]
  | voc, sg => ["a"]     | voc, du => ["O"]      | voc, pl => ["e"]

/-- Pronominal endings, neuter: -am (sarva) or -at (anya) in nom/acc sg. -/
private def pronNeut (at' : Bool) : Case → Number → List String
  | nom, sg => [if at' then "at" else "am"]
  | acc, sg => [if at' then "at" else "am"]
  | voc, sg => [if at' then "at" else "a"]
  | nom, du => ["e"]   | acc, du => ["e"]   | voc, du => ["e"]
  | nom, pl => ["Ani"] | acc, pl => ["Ani"] | voc, pl => ["Ani"]
  | c, n => pronMasc c n

/-- Pronominal endings, feminine, on the -ā stem (sarvā → sarvasyai). -/
private def pronFem : Case → Number → List String
  | nom, sg => ["A"]      | nom, du => ["e"]     | nom, pl => ["AH"]
  | acc, sg => ["Am"]     | acc, du => ["e"]     | acc, pl => ["AH"]
  | ins, sg => ["ayA"]    | ins, du => ["AByAm"] | ins, pl => ["ABiH"]
  | dat, sg => ["asyE"]   | dat, du => ["AByAm"] | dat, pl => ["AByaH"]
  | abl, sg => ["asyAH"]  | abl, du => ["AByAm"] | abl, pl => ["AByaH"]
  | gen, sg => ["asyAH"]  | gen, du => ["ayoH"]  | gen, pl => ["AsAm"]
  | loc, sg => ["asyAm"]  | loc, du => ["ayoH"]  | loc, pl => ["Asu"]
  | voc, sg => ["e"]      | voc, du => ["e"]     | voc, pl => ["AH"]

/-- Endings (SLP1) that replace the stem-final vowel; variants listed. -/
def endings : StemClass → Case → Number → List String
  | .a_m, c, n => aMasc c n
  | .a_n, c, n => aNeut c n
  | .A_f, c, n => AFem c n
  | .i_m, c, n => iMasc c n

  | .i_f, acc, pl => ["IH"]
  | .i_f, ins, sg => ["yA"]
  | .i_f, dat, sg => ["aye", "yE"]
  | .i_f, abl, sg => ["eH", "yAH"]
  | .i_f, gen, sg => ["eH", "yAH"]
  | .i_f, loc, sg => ["O", "yAm"]
  | .i_f, c, n => iMasc c n   -- otherwise like the masculine i-stem

  | .i_n, nom, sg => ["i"]    | .i_n, nom, du => ["inI"]    | .i_n, nom, pl => ["Ini"]
  | .i_n, acc, sg => ["i"]    | .i_n, acc, du => ["inI"]    | .i_n, acc, pl => ["Ini"]
  | .i_n, ins, sg => ["inA"]  | .i_n, ins, du => ["iByAm"]  | .i_n, ins, pl => ["iBiH"]
  | .i_n, dat, sg => ["ine"]  | .i_n, dat, du => ["iByAm"]  | .i_n, dat, pl => ["iByaH"]
  | .i_n, abl, sg => ["inaH"] | .i_n, abl, du => ["iByAm"]  | .i_n, abl, pl => ["iByaH"]
  | .i_n, gen, sg => ["inaH"] | .i_n, gen, du => ["inoH"]   | .i_n, gen, pl => ["InAm"]
  | .i_n, loc, sg => ["ini"]  | .i_n, loc, du => ["inoH"]   | .i_n, loc, pl => ["izu"]
  | .i_n, voc, sg => ["i", "e"] | .i_n, voc, du => ["inI"]  | .i_n, voc, pl => ["Ini"]

  | .u_m, nom, sg => ["uH"]   | .u_m, nom, du => ["U"]      | .u_m, nom, pl => ["avaH"]
  | .u_m, acc, sg => ["um"]   | .u_m, acc, du => ["U"]      | .u_m, acc, pl => ["Un"]
  | .u_m, ins, sg => ["unA"]  | .u_m, ins, du => ["uByAm"]  | .u_m, ins, pl => ["uBiH"]
  | .u_m, dat, sg => ["ave"]  | .u_m, dat, du => ["uByAm"]  | .u_m, dat, pl => ["uByaH"]
  | .u_m, abl, sg => ["oH"]   | .u_m, abl, du => ["uByAm"]  | .u_m, abl, pl => ["uByaH"]
  | .u_m, gen, sg => ["oH"]   | .u_m, gen, du => ["voH"]    | .u_m, gen, pl => ["UnAm"]
  | .u_m, loc, sg => ["O"]    | .u_m, loc, du => ["voH"]    | .u_m, loc, pl => ["uzu"]
  | .u_m, voc, sg => ["o"]    | .u_m, voc, du => ["U"]      | .u_m, voc, pl => ["avaH"]

  | .u_f, nom, sg => ["uH"]   | .u_f, nom, du => ["U"]      | .u_f, nom, pl => ["avaH"]
  | .u_f, acc, sg => ["um"]   | .u_f, acc, du => ["U"]      | .u_f, acc, pl => ["UH"]
  | .u_f, ins, sg => ["vA"]   | .u_f, ins, du => ["uByAm"]  | .u_f, ins, pl => ["uBiH"]
  | .u_f, dat, sg => ["ave", "vE"] | .u_f, dat, du => ["uByAm"] | .u_f, dat, pl => ["uByaH"]
  | .u_f, abl, sg => ["oH", "vAH"] | .u_f, abl, du => ["uByAm"] | .u_f, abl, pl => ["uByaH"]
  | .u_f, gen, sg => ["oH", "vAH"] | .u_f, gen, du => ["voH"]   | .u_f, gen, pl => ["UnAm"]
  | .u_f, loc, sg => ["O", "vAm"]  | .u_f, loc, du => ["voH"]   | .u_f, loc, pl => ["uzu"]
  | .u_f, voc, sg => ["o"]    | .u_f, voc, du => ["U"]      | .u_f, voc, pl => ["avaH"]

  | .u_n, nom, sg => ["u"]    | .u_n, nom, du => ["unI"]    | .u_n, nom, pl => ["Uni"]
  | .u_n, acc, sg => ["u"]    | .u_n, acc, du => ["unI"]    | .u_n, acc, pl => ["Uni"]
  | .u_n, ins, sg => ["unA"]  | .u_n, ins, du => ["uByAm"]  | .u_n, ins, pl => ["uBiH"]
  | .u_n, dat, sg => ["une"]  | .u_n, dat, du => ["uByAm"]  | .u_n, dat, pl => ["uByaH"]
  | .u_n, abl, sg => ["unaH"] | .u_n, abl, du => ["uByAm"]  | .u_n, abl, pl => ["uByaH"]
  | .u_n, gen, sg => ["unaH"] | .u_n, gen, du => ["unoH"]   | .u_n, gen, pl => ["UnAm"]
  | .u_n, loc, sg => ["uni"]  | .u_n, loc, du => ["unoH"]   | .u_n, loc, pl => ["uzu"]
  | .u_n, voc, sg => ["u", "o"] | .u_n, voc, du => ["unI"]  | .u_n, voc, pl => ["Uni"]

  | .I_f, nom, sg => ["I"]    | .I_f, nom, du => ["yO"]     | .I_f, nom, pl => ["yaH"]
  | .I_f, acc, sg => ["Im"]   | .I_f, acc, du => ["yO"]     | .I_f, acc, pl => ["IH"]
  | .I_f, ins, sg => ["yA"]   | .I_f, ins, du => ["IByAm"]  | .I_f, ins, pl => ["IBiH"]
  | .I_f, dat, sg => ["yE"]   | .I_f, dat, du => ["IByAm"]  | .I_f, dat, pl => ["IByaH"]
  | .I_f, abl, sg => ["yAH"]  | .I_f, abl, du => ["IByAm"]  | .I_f, abl, pl => ["IByaH"]
  | .I_f, gen, sg => ["yAH"]  | .I_f, gen, du => ["yoH"]    | .I_f, gen, pl => ["InAm"]
  | .I_f, loc, sg => ["yAm"]  | .I_f, loc, du => ["yoH"]    | .I_f, loc, pl => ["Izu"]
  | .I_f, voc, sg => ["i"]    | .I_f, voc, du => ["yO"]     | .I_f, voc, pl => ["yaH"]

  | .U_f, nom, sg => ["UH"]   | .U_f, nom, du => ["vO"]     | .U_f, nom, pl => ["vaH"]
  | .U_f, acc, sg => ["Um"]   | .U_f, acc, du => ["vO"]     | .U_f, acc, pl => ["UH"]
  | .U_f, ins, sg => ["vA"]   | .U_f, ins, du => ["UByAm"]  | .U_f, ins, pl => ["UBiH"]
  | .U_f, dat, sg => ["vE"]   | .U_f, dat, du => ["UByAm"]  | .U_f, dat, pl => ["UByaH"]
  | .U_f, abl, sg => ["vAH"]  | .U_f, abl, du => ["UByAm"]  | .U_f, abl, pl => ["UByaH"]
  | .U_f, gen, sg => ["vAH"]  | .U_f, gen, du => ["voH"]    | .U_f, gen, pl => ["UnAm"]
  | .U_f, loc, sg => ["vAm"]  | .U_f, loc, du => ["voH"]    | .U_f, loc, pl => ["Uzu"]
  | .U_f, voc, sg => ["u"]    | .U_f, voc, du => ["vO"]     | .U_f, voc, pl => ["vaH"]

  | .pron_m, c, n => pronMasc c n
  | .pron_n, c, n => pronNeut false c n
  | .pron_n_at, c, n => pronNeut true c n
  | .pron_f, c, n => pronFem c n
  -- optionally pronominal (pūrva, uttara …): both ending sets are classical
  | .pron_opt_m, c, n => pronMasc c n ++ aMasc c n
  | .pron_opt_n, c, n => pronNeut false c n ++ aNeut c n
  | .pron_opt_f, c, n => pronFem c n ++ AFem c n

  -- consonantal classes are declined by dedicated functions in `decline`
  | _, _, _ => []

/-- ṛ-stems: pitṛ (guṇa, pitaram), kartṛ (vṛddhi, kartāram); feminines
take accusative plural -ṝḥ. Base = stem without the final ṛ. -/
private def declineR (stem : String) (vrddhi fem : Bool) : Case → Number → List String :=
  let b := (stem.dropEnd 1).toString
  let ar := if vrddhi then "Ar" else "ar"   -- the strong syllable
  fun c n => match c, n with
  | nom, sg => [b ++ "A"]        | nom, du => [b ++ ar ++ "O"] | nom, pl => [b ++ ar ++ "aH"]
  | acc, sg => [b ++ ar ++ "am"] | acc, du => [b ++ ar ++ "O"]
  | acc, pl => [b ++ (if fem then "FH" else "Fn")]
  | ins, sg => [b ++ "rA"]  | ins, du => [b ++ "fByAm"] | ins, pl => [b ++ "fBiH"]
  | dat, sg => [b ++ "re"]  | dat, du => [b ++ "fByAm"] | dat, pl => [b ++ "fByaH"]
  | abl, sg => [b ++ "uH"]  | abl, du => [b ++ "fByAm"] | abl, pl => [b ++ "fByaH"]
  | gen, sg => [b ++ "uH"]  | gen, du => [b ++ "roH"]
  | gen, pl => if stem == "nf" then [b ++ "FnAm", b ++ "fnAm"]   -- nṝṇām/nṛṇām
               else [b ++ "FnAm"]
  | loc, sg => [b ++ "ari"] | loc, du => [b ++ "roH"]   | loc, pl => [b ++ "fzu"]
  | voc, sg => [b ++ "ar"]  | voc, du => [b ++ ar ++ "O"] | voc, pl => [b ++ ar ++ "aH"]

/-- an-stems: rājan (weak rājñ-), ātman (weak ātman-: -man and -van after
a consonant keep their a), and their neuters karman, nāman. -/
private def declineAn (stem : String) (keepA neut : Bool) : Case → Number → List String :=
  let b := (stem.dropEnd 2).toString                    -- rAj, Atm, karm, nAm
  let weak := if keepA then stem
              else if b.back == 'j' then b ++ "Y"       -- rājñ-
              else b ++ "n"                             -- nāmn-, pūṣṇ- (ṇatva)
  let pada := b ++ "a"                                  -- rāja-bhyām
  let locSg := if keepA then [stem ++ "i"] else [weak ++ "i", stem ++ "i"]
  fun c n => match neut, c, n with
  | true, nom, sg => [pada]         | true, acc, sg => [pada]
  | true, nom, du => [weak ++ "I"]  | true, acc, du => [weak ++ "I"]
  | true, nom, pl => [b ++ "Ani"]   | true, acc, pl => [b ++ "Ani"]
  | true, voc, sg => [stem, pada]   | true, voc, du => [weak ++ "I"]
  | true, voc, pl => [b ++ "Ani"]
  | false, nom, sg => [b ++ "A"]    | false, nom, du => [b ++ "AnO"]
  | false, nom, pl => [b ++ "AnaH"]
  | false, acc, sg => [b ++ "Anam"] | false, acc, du => [b ++ "AnO"]
  | false, acc, pl => [weak ++ "aH"]
  | false, voc, sg => [stem]        | false, voc, du => [b ++ "AnO"]
  | false, voc, pl => [b ++ "AnaH"]
  | _, ins, sg => [weak ++ "A"]  | _, ins, du => [pada ++ "ByAm"] | _, ins, pl => [pada ++ "BiH"]
  | _, dat, sg => [weak ++ "e"]  | _, dat, du => [pada ++ "ByAm"] | _, dat, pl => [pada ++ "ByaH"]
  | _, abl, sg => [weak ++ "aH"] | _, abl, du => [pada ++ "ByAm"] | _, abl, pl => [pada ++ "ByaH"]
  | _, gen, sg => [weak ++ "aH"] | _, gen, du => [weak ++ "oH"]   | _, gen, pl => [weak ++ "Am"]
  | _, loc, sg => locSg          | _, loc, du => [weak ++ "oH"]   | _, loc, pl => [pada ++ "su"]

/-- in-stems: yogin → yogī, yoginam, yogibhiḥ; neuter bali, balinī, balīni. -/
private def declineIn (stem : String) (neut : Bool) : Case → Number → List String :=
  let ib := (stem.dropEnd 1).toString                   -- yogi
  let long := (ib.dropEnd 1).toString ++ "I"            -- yogI
  fun c n => match neut, c, n with
  | true, nom, sg => [ib]           | true, acc, sg => [ib]
  | true, nom, du => [stem ++ "I"]  | true, acc, du => [stem ++ "I"]
  | true, nom, pl => [(ib.dropEnd 1).toString ++ "Ini"]
  | true, acc, pl => [(ib.dropEnd 1).toString ++ "Ini"]
  | true, voc, sg => [ib]           | true, voc, du => [stem ++ "I"]
  | true, voc, pl => [(ib.dropEnd 1).toString ++ "Ini"]
  | false, nom, sg => [long]        | false, nom, du => [stem ++ "O"]
  | false, nom, pl => [stem ++ "aH"]
  | false, acc, sg => [stem ++ "am"] | false, acc, du => [stem ++ "O"]
  | false, acc, pl => [stem ++ "aH"]
  | false, voc, sg => [stem]        | false, voc, du => [stem ++ "O"]
  | false, voc, pl => [stem ++ "aH"]
  | _, ins, sg => [stem ++ "A"]  | _, ins, du => [ib ++ "ByAm"] | _, ins, pl => [ib ++ "BiH"]
  | _, dat, sg => [stem ++ "e"]  | _, dat, du => [ib ++ "ByAm"] | _, dat, pl => [ib ++ "ByaH"]
  | _, abl, sg => [stem ++ "aH"] | _, abl, du => [ib ++ "ByAm"] | _, abl, pl => [ib ++ "ByaH"]
  | _, gen, sg => [stem ++ "aH"] | _, gen, du => [stem ++ "oH"] | _, gen, pl => [stem ++ "Am"]
  | _, loc, sg => [stem ++ "i"]  | _, loc, du => [stem ++ "oH"] | _, loc, pl => [ib ++ "zu"]

/-- Neuter s-stems: manas, havis, cakṣus (nom manaḥ, pl manāṃsi,
pada mano-bhiḥ / havir-bhiḥ). `v` is the class vowel a/i/u. -/
private def declineS (stem : String) (v : Char) : Case → Number → List String :=
  let b := (stem.dropEnd 2).toString                    -- man, hav, cakz
  let vs := String.ofList [v]
  let sib := if v == 'a' then "s" else "z"              -- havizA, manasA
  let core := b ++ vs ++ sib                            -- manas, haviz
  let longPl := b ++ (if v == 'a' then "AMsi" else if v == 'i' then "IMzi" else "UMzi")
  let padaB := if v == 'a' then b ++ "o" else b ++ vs ++ "r"   -- mano-, havir-
  let visarga := b ++ vs ++ "H"
  let locPl := b ++ vs ++ "H" ++ (if v == 'a' then "su" else "zu")
  fun c n => match c, n with
  | nom, sg => [visarga] | nom, du => [core ++ "I"] | nom, pl => [longPl]
  | acc, sg => [visarga] | acc, du => [core ++ "I"] | acc, pl => [longPl]
  | voc, sg => [visarga] | voc, du => [core ++ "I"] | voc, pl => [longPl]
  | ins, sg => [core ++ "A"]  | ins, du => [padaB ++ "ByAm"] | ins, pl => [padaB ++ "BiH"]
  | dat, sg => [core ++ "e"]  | dat, du => [padaB ++ "ByAm"] | dat, pl => [padaB ++ "ByaH"]
  | abl, sg => [core ++ "aH"] | abl, du => [padaB ++ "ByAm"] | abl, pl => [padaB ++ "ByaH"]
  | gen, sg => [core ++ "aH"] | gen, du => [core ++ "oH"]    | gen, pl => [core ++ "Am"]
  | loc, sg => [core ++ "i"]  | loc, du => [core ++ "oH"]    | loc, pl => [locPl]

/-- mat/vat-stems: bhagavat → bhagavān, bhagavantam, bhagavadbhiḥ; the
neuter jagat → jaganti; mahat strengthens with vṛddhi (mahāntam). -/
private def declineMat (stem : String) (neut : Bool) : Case → Number → List String :=
  let b := (stem.dropEnd 1).toString                    -- Bagava, maha
  let strong := if stem == "mahat" then "mahAnt" else b ++ "nt"
  let pada := b ++ "d"
  let nomSg := (b.dropEnd 1).toString ++ "An"           -- BagavAn, mahAn
  let vocSg := (b.dropEnd 1).toString ++ "an"
  fun c n => match neut, c, n with
  | true, nom, sg => [stem]          | true, acc, sg => [stem] | true, voc, sg => [stem]
  | true, nom, du => [stem ++ "I"]   | true, acc, du => [stem ++ "I"]
  | true, voc, du => [stem ++ "I"]
  | true, nom, pl => [strong ++ "i"] | true, acc, pl => [strong ++ "i"]
  | true, voc, pl => [strong ++ "i"]
  | false, nom, sg => [nomSg]        | false, nom, du => [strong ++ "O"]
  | false, nom, pl => [strong ++ "aH"]
  | false, acc, sg => [strong ++ "am"] | false, acc, du => [strong ++ "O"]
  | false, acc, pl => [stem ++ "aH"]
  | false, voc, sg => [vocSg]        | false, voc, du => [strong ++ "O"]
  | false, voc, pl => [strong ++ "aH"]
  | _, ins, sg => [stem ++ "A"]  | _, ins, du => [pada ++ "ByAm"] | _, ins, pl => [pada ++ "BiH"]
  | _, dat, sg => [stem ++ "e"]  | _, dat, du => [pada ++ "ByAm"] | _, dat, pl => [pada ++ "ByaH"]
  | _, abl, sg => [stem ++ "aH"] | _, abl, du => [pada ++ "ByAm"] | _, abl, pl => [pada ++ "ByaH"]
  | _, gen, sg => [stem ++ "aH"] | _, gen, du => [stem ++ "oH"]   | _, gen, pl => [stem ++ "Am"]
  | _, loc, sg => [stem ++ "i"]  | _, loc, du => [stem ++ "oH"]   | _, loc, pl => [stem ++ "su"]

/-- Root stems: vāc, diś, marut. The entry supplies the word-final (pada)
base — vāk, dik — whose voiced counterpart is derived (vāgbhiḥ). -/
private def declineCons (stem pada : String) : Case → Number → List String :=
  let padaV := (pada.dropEnd 1).toString.push (voiceFinal pada.back)
  let locPl := pada ++ (if pada.back == 'k' then "zu" else "su")   -- vākṣu, marutsu
  fun c n => match c, n with
  | nom, sg => [pada]         | nom, du => [stem ++ "O"] | nom, pl => [stem ++ "aH"]
  | acc, sg => [stem ++ "am"] | acc, du => [stem ++ "O"] | acc, pl => [stem ++ "aH"]
  | voc, sg => [pada]         | voc, du => [stem ++ "O"] | voc, pl => [stem ++ "aH"]
  | ins, sg => [stem ++ "A"]  | ins, du => [padaV ++ "ByAm"] | ins, pl => [padaV ++ "BiH"]
  | dat, sg => [stem ++ "e"]  | dat, du => [padaV ++ "ByAm"] | dat, pl => [padaV ++ "ByaH"]
  | abl, sg => [stem ++ "aH"] | abl, du => [padaV ++ "ByAm"] | abl, pl => [padaV ++ "ByaH"]
  | gen, sg => [stem ++ "aH"] | gen, du => [stem ++ "oH"]    | gen, pl => [stem ++ "Am"]
  | loc, sg => [stem ++ "i"]  | loc, du => [stem ++ "oH"]    | loc, pl => [locPl]

/-- Decline an SLP1 stem. Vowel and pronominal classes replace the final
vowel with table endings; consonantal classes build on the full stem.
`pada` is the word-final base of a root stem (vāc → vāk), unused otherwise.
Every form passes through the ṇatva rule. -/
def decline (stem : String) (sc : StemClass) (c : Case) (n : Number)
    (pada : String := "") : List String :=
  let raw := match sc with
    | .f_m   => declineR stem false false c n
    | .f_m_v => declineR stem true  false c n
    | .f_f   => declineR stem false true  c n
    | .f_f_v => declineR stem true  true  c n
    | .an_m   => declineAn stem false false c n
    | .an_m_a => declineAn stem true  false c n
    | .an_n   => declineAn stem false true  c n
    | .an_n_a => declineAn stem true  true  c n
    | .in_m => declineIn stem false c n
    | .in_n => declineIn stem true  c n
    | .as_n => declineS stem 'a' c n
    | .is_n => declineS stem 'i' c n
    | .us_n => declineS stem 'u' c n
    | .mat_m => declineMat stem false c n
    | .mat_n => declineMat stem true  c n
    | .cons_m => declineCons stem pada c n
    | .cons_f => declineCons stem pada c n
    | _ => (endings sc c n).map fun e => (stem.dropEnd 1).toString ++ e
  (raw.map natva).eraseDups

/-- The gender a stem class inflects. -/
def StemClass.gender : StemClass → Gender
  | .a_m | .i_m | .u_m | .f_m | .f_m_v | .an_m | .an_m_a
  | .in_m | .mat_m | .cons_m | .pron_m | .pron_opt_m => .m
  | .a_n | .i_n | .u_n | .an_n | .an_n_a | .in_n | .as_n | .is_n | .us_n
  | .mat_n | .pron_n | .pron_n_at | .pron_opt_n => .n
  | _ => .f

end Sanskrit
