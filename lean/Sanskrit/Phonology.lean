/-!
# Phonology

The sound inventory of Sanskrit, in SLP1 transliteration (one ASCII
character per phoneme), and the classifications the grammar needs:
vowels, voicing, and the retroflexion (ṇatva) rule that turns n into ṇ
after r/ṛ/ṝ/ṣ within a word.
-/

namespace Sanskrit

/-- SLP1 vowels: a A i I u U f(ṛ) F(ṝ) x(ḷ) e E(ai) o O(au). -/
def isVowel (c : Char) : Bool :=
  "aAiIuUfFxeEoO".contains c

/-- Voiced sounds (for visarga and final-consonant sandhi). -/
def isVoiced (c : Char) : Bool :=
  isVowel c || "gGjJqQdDbBNYRnmyrlvh".contains c

/-- The voiced counterpart of a word-final stop (vāk → vāg-bhiḥ). -/
def voiceFinal : Char → Char
  | 'k' => 'g' | 'w' => 'q' | 't' => 'd' | 'p' => 'b' | c => c

/-- Sounds transparent to ṇatva: vowels, velars, labials, y v h ṃ. -/
private def natvaTransparent (c : Char) : Bool :=
  isVowel c || "kKgGNpPbBmyvhM".contains c

/-- Sounds that trigger ṇatva. -/
private def natvaTrigger (c : Char) : Bool :=
  "rfFz".contains c

/-- n retroflexes only before a vowel or n m y v (never word-finally). -/
private def natvaFollow (c : Char) : Bool :=
  isVowel c || "nmyv".contains c

private def natvaGo : List Char → Bool → List Char
  | [], _ => []
  | c :: rest, active =>
    if natvaTrigger c then c :: natvaGo rest true
    else if c == 'n' then
      match rest with
      | c' :: _ =>
        if active && natvaFollow c' then 'R' :: natvaGo rest false
        else 'n' :: natvaGo rest false
      | [] => ['n']
    else if natvaTransparent c then c :: natvaGo rest active
    else c :: natvaGo rest false

/-- Apply the ṇatva (n → ṇ) rule inside a word: rāma+inā → rāmeṇa. -/
def natva (w : String) : String :=
  String.ofList (natvaGo w.toList false)

end Sanskrit
