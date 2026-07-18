/-!
# Transliteration

IAST (what humans and the language model read/write) to SLP1 (what the
grammar computes over). Longest-match-first over IAST graphemes; input is
assumed NFC-normalized (the caller's job).
-/

namespace Sanskrit

/-- IAST graphemes → SLP1, two-character graphemes first. -/
private def digraphs : List (String × Char) :=
  [("ai", 'E'), ("au", 'O'),
   ("kh", 'K'), ("gh", 'G'), ("ch", 'C'), ("jh", 'J'),
   ("ṭh", 'W'), ("ḍh", 'Q'), ("th", 'T'), ("dh", 'D'),
   ("ph", 'P'), ("bh", 'B')]

private def monographs : List (Char × Char) :=
  [('a', 'a'), ('ā', 'A'), ('i', 'i'), ('ī', 'I'), ('u', 'u'), ('ū', 'U'),
   ('ṛ', 'f'), ('ṝ', 'F'), ('ḷ', 'x'), ('e', 'e'), ('o', 'o'),
   ('ṃ', 'M'), ('ḥ', 'H'), ('\'', '\''),
   ('k', 'k'), ('g', 'g'), ('ṅ', 'N'),
   ('c', 'c'), ('j', 'j'), ('ñ', 'Y'),
   ('ṭ', 'w'), ('ḍ', 'q'), ('ṇ', 'R'),
   ('t', 't'), ('d', 'd'), ('n', 'n'),
   ('p', 'p'), ('b', 'b'), ('m', 'm'),
   ('y', 'y'), ('r', 'r'), ('l', 'l'), ('v', 'v'),
   ('ś', 'S'), ('ṣ', 'z'), ('s', 's'), ('h', 'h')]

private def matchDigraph (c₁ c₂ : Char) : Option Char :=
  digraphs.lookup (String.ofList [c₁, c₂])

private def go : List Char → List Char
  | [] => []
  | c₁ :: c₂ :: rest =>
    match matchDigraph c₁ c₂ with
    | some s => s :: go rest
    | none =>
      match monographs.lookup c₁ with
      | some s => s :: go (c₂ :: rest)
      | none => c₁ :: go (c₂ :: rest)   -- unknown char: passed through, will fail lookup
  | [c] =>
    match monographs.lookup c with
    | some s => [s]
    | none => [c]

/-- IAST → SLP1 for a single word (no spaces). -/
def toSLP1 (iast : String) : String :=
  String.ofList (go iast.toList)

/-- SLP1 → IAST (for exporting human-readable forms). -/
def toIAST (slp : String) : String :=
  slp.toList.foldl (init := "") fun acc c =>
    let s := match c with
      | 'A' => "ā" | 'I' => "ī" | 'U' => "ū" | 'f' => "ṛ" | 'F' => "ṝ"
      | 'x' => "ḷ" | 'E' => "ai" | 'O' => "au" | 'M' => "ṃ" | 'H' => "ḥ"
      | 'K' => "kh" | 'G' => "gh" | 'N' => "ṅ" | 'C' => "ch" | 'J' => "jh"
      | 'Y' => "ñ" | 'w' => "ṭ" | 'W' => "ṭh" | 'q' => "ḍ" | 'Q' => "ḍh"
      | 'R' => "ṇ" | 'T' => "th" | 'D' => "dh" | 'P' => "ph" | 'B' => "bh"
      | 'S' => "ś" | 'z' => "ṣ" | other => other.toString
    acc ++ s

end Sanskrit
