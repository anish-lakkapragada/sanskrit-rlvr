import Sanskrit.Phonology

/-!
# External sandhi (undoing)

Written Sanskrit fuses words at their boundaries (devaḥ + gacchati is
written devo gacchati). To recognize the words of a sentence we restore
the possible pausa (citation) forms of each surface word, given the first
sound of the following word. The list always contains the word itself.

Scope note: vowel-fusion sandhi merges two words into one written token;
like careful didactic prose, we accept unmerged (hiatus) spellings, and
handle the sandhi families that keep tokens separate: visarga, final m,
final t and d, doubled nn, and the saḥ special case.
-/

namespace Sanskrit

/-- Possible pausa forms of surface word `w` (SLP1), where `next?` is the
first char of the following word after avagraha restoration. -/
def pausaCandidates (w : String) (next? : Option Char) : List String :=
  if w.isEmpty then [w] else
  let body := (w.dropEnd 1).toString
  let last := w.back
  let nextVoiced := match next? with | some c => isVoiced c | none => false
  let nextVowel  := match next? with | some c => isVowel c  | none => false
  let base := [w]
  -- -o from -aḥ before voiced sounds (devo < devaḥ); lenient at sentence end
  let base := if last == 'o' && (next?.isNone || nextVoiced)
              then base ++ [body ++ "aH"] else base
  -- -ā from -āḥ before voiced (devā gacchanti < devāḥ)
  let base := if last == 'A' && nextVoiced then base ++ [w ++ "H"] else base
  -- bare -a from -aḥ before non-a vowels (deva icchati < devaḥ)
  let base := if last == 'a' && nextVowel && next? != some 'a'
              then base ++ [w ++ "H"] else base
  -- -r from -ḥ (munir gacchati < muniḥ)
  let base := if last == 'r' && nextVoiced && body.length ≥ 1 && isVowel body.back
              then base ++ [body ++ "H"] else base
  -- -ś/-s from -ḥ before unvoiced coronals (devāś ca, devas tatra)
  let base := if last == 'S' && (next? == some 'c' || next? == some 'C')
              then base ++ [body ++ "H"] else base
  let base := if last == 's' && (next? == some 't' || next? == some 'T')
              then base ++ [body ++ "H"] else base
  -- -ṃ from -m before consonants (grāmaṃ gacchati < grāmam); lenient at end
  let base := if last == 'M' && !nextVowel then base ++ [body ++ "m"] else base
  -- -d from -t before voiced (tad asti < tat)
  let base := if last == 'd' && nextVoiced then base ++ [body ++ "t"] else base
  -- voiced final stops from unvoiced before voiced (vāg asti < vāk)
  let base := if last == 'g' && nextVoiced then base ++ [body ++ "k"] else base
  let base := if last == 'q' && nextVoiced then base ++ [body ++ "w"] else base
  let base := if last == 'b' && nextVoiced then base ++ [body ++ "p"] else base
  -- final t assimilated to a following coronal (tac ca, taj jalam, tan na)
  let base := if last == 'c' && (next? == some 'c' || next? == some 'C')
              then base ++ [body ++ "t"] else base
  let base := if last == 'j' && next? == some 'j' then base ++ [body ++ "t"] else base
  let base := if last == 'l' && next? == some 'l' then base ++ [body ++ "t"] else base
  let base := if last == 'n' && next? == some 'n' then base ++ [body ++ "t"] else base
  -- -ṃś/-ṃs/-ṃṣ from -n before unvoiced coronals (bhavāṃś ca < bhavān)
  let base := if w.endsWith "MS" && (next? == some 'c' || next? == some 'C')
              then base ++ [(w.dropEnd 2).toString ++ "n"] else base
  let base := if w.endsWith "Ms" && (next? == some 't' || next? == some 'T')
              then base ++ [(w.dropEnd 2).toString ++ "n"] else base
  let base := if w.endsWith "Mz" && (next? == some 'w' || next? == some 'W')
              then base ++ [(w.dropEnd 2).toString ++ "n"] else base
  -- -nn from -n before vowels (āsann atra < āsan)
  let base := if w.endsWith "nn" && nextVowel then base ++ [body] else base
  -- saḥ drops its visarga before consonants: sa gacchati / so 'pi
  let base := if w == "sa" then base ++ ["saH"] else base
  let base := if w == "so" then base ++ ["saH"] else base
  base

/-- A word beginning with avagraha lost an initial a (devo 'pi < devaḥ api). -/
def restoreInitial (w : String) : String :=
  if w.startsWith "'" then "a" ++ w.drop 1 else w

end Sanskrit
