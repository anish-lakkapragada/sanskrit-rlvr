import Panini.Optimality

/-!
# No anubandha is redundant: every marker of the Śivasūtras is load-bearing

The tradition's celebrated economy principle (*lāghava* — "grammarians rejoice
over the saving of half a mora as over the birth of a son") asserts that nothing
in Pāṇini's system is redundant. At the level of the whole grammar that claim is
too vague to be a theorem; at the level of the Śivasūtras it is a precise,
checkable statement, and this file proves it:

* **Every one of the 14 markers is individually necessary**
  (`no_marker_redundant`): delete any single anubandha and some attested
  pratyāhāra class loses its well-formed encoding. Each case is witnessed by a
  concrete class and discharged by `decide` — the kernel searches all 588
  candidate (sound, marker) pairs of the truncated alphabet and finds none that
  both terminates and denotes the class.
* **The duplicated `h` of line 14 is necessary even under the lax semantics**
  (`noH2_not_lax`): delete the second `h` and `raL` (consonants minus `y v`,
  8.2.18 *kṛpo ro laḥ* family) is not encodable at all — not merely not
  *well-formedly* encodable. This sharpens `one_le_duplications_for_panini`
  (some sound must repeat) to the pointwise statement that Pāṇini's own repeat
  cannot be dropped.

Together with `noL_not_strict` (`Optimality.lean`) this gives the complete
irredundancy picture for the Śivasūtras' apparatus: the 14 markers and the one
duplication are each individually indispensable for the 43 attested classes.

## Kernel-verified counts (Petersen 2004, fn. 2, made precise)

Petersen counts 305 pratyāhāra-forming pairs "segment followed by an anubandha",
of which 14 denote singletons. Her count is over segment *occurrences*; under our
first-occurrence semantics the pair (h, L) formed at the *second* `h` coincides
with the one formed at the first, so the counts shift by exactly that one pair:

* `card_wellFormed_pratyaharas` — **304** well-formed (sound, marker) pairs.
* `card_singleton_pratyaharas` — **13** of them denote singleton classes: her
  14th singleton is (h₂, L) = {h}, which for us is (h, L) = `haL`, the whole
  consonant class.

These are not deep, but they are exactly the kind of numerical folklore that a
kernel can pin down — including the subtle dependence on how one reads a
pratyāhāra whose start sound occurs twice.
-/

set_option maxRecDepth 65536

namespace Panini

open Sound Marker

/-- `A` with every occurrence of the marker `m` deleted. -/
def removeMarker (A : SAlphabet) (m : Marker) : SAlphabet :=
  A.filter (fun i => decide (i ≠ Item.mark m))

/-- If one attested class has no well-formed pratyāhāra, the alphabet is not a
strict S-alphabet for the family. -/
theorem not_SAlphabetT_of_witness {A : SAlphabet} {C : Class}
    (hC : C ∈ paniniClasses) (h : ¬ EncodesT A C) :
    ¬ IsSAlphabetT A paniniClasses :=
  fun hA => h (hA.1 C hC)

/-- **No anubandha is redundant.** Deleting any single one of the 14 markers
from the Śivasūtras destroys the well-formed encoding of some attested class.
The witness classes, marker by marker:
`Ṇ₁ ↦ aṆ₁`, `K ↦ aK`, `Ṅ ↦ eṄ`, `C ↦ aiC`, `Ṭ ↦ aṬ`, `Ṇ₂ ↦ yaṆ`, `M ↦ ñaM`,
`Ñ ↦ yaÑ`, `Ṣ ↦ jhaṢ`, `Ś ↦ jhaŚ`, `V ↦ chaV`, `Y ↦ khaY`, `R ↦ śaR`,
`L ↦ raL`. -/
theorem no_marker_redundant :
    ∀ m : Marker, ¬ IsSAlphabetT (removeMarker shivasutras m) paniniClasses := by
  intro m
  cases m with
  | N1 => exact not_SAlphabetT_of_witness (C := aN1) (by decide +kernel) (by decide +kernel)
  | K => exact not_SAlphabetT_of_witness (C := aK) (by decide +kernel) (by decide +kernel)
  | Ng => exact not_SAlphabetT_of_witness (C := eNg) (by decide +kernel) (by decide +kernel)
  | C => exact not_SAlphabetT_of_witness (C := aiC) (by decide +kernel) (by decide +kernel)
  | T1 => exact not_SAlphabetT_of_witness (C := aT1) (by decide +kernel) (by decide +kernel)
  | N2 => exact not_SAlphabetT_of_witness (C := yaN2) (by decide +kernel) (by decide +kernel)
  | M => exact not_SAlphabetT_of_witness (C := nyaM) (by decide +kernel) (by decide +kernel)
  | Ny => exact not_SAlphabetT_of_witness (C := yaNy) (by decide +kernel) (by decide +kernel)
  | Sh => exact not_SAlphabetT_of_witness (C := jhaSh) (by decide +kernel) (by decide +kernel)
  | Sx => exact not_SAlphabetT_of_witness (C := jhaSx) (by decide +kernel) (by decide +kernel)
  | V => exact not_SAlphabetT_of_witness (C := chaV) (by decide +kernel) (by decide +kernel)
  | Y => exact not_SAlphabetT_of_witness (C := khaY) (by decide +kernel) (by decide +kernel)
  | R => exact not_SAlphabetT_of_witness (C := shaR) (by decide +kernel) (by decide +kernel)
  | L => exact not_SAlphabetT_of_witness (C := raL) (by decide +kernel) (by decide +kernel)

/-! ## The duplicated `h` is load-bearing -/

/-- Pāṇini's alphabet with the *second* `h` (the sound of the 14th sūtra)
deleted: drop the trailing `h, L` and restore the `L`. -/
def shivasutras_noH2 : SAlphabet :=
  shivasutras.dropLast.dropLast ++ [Item.mark Marker.L]

theorem numMarkers_noH2 : shivasutras_noH2.numMarkers = 14 := by decide

theorem duplications_noH2 : shivasutras_noH2.duplications = 0 := by decide

/-- **The second `h` is necessary even laxly.** Without it, `raL` (consonants
minus `y v`) is not encodable by any pratyāhāra at all: the first `h` precedes
`y v r`, so every interval reaching `h` picks up `y` and `v` as well. Deleting
the duplication is therefore not an option — Pāṇini's one repeated sound cannot
be traded away no matter how the markers are read. -/
theorem noH2_not_lax : ¬ IsSAlphabet shivasutras_noH2 paniniClasses := by
  intro h
  have hraL := h.1 raL (by simp [paniniClasses])
  exact (by decide +kernel : ¬ Encodes shivasutras_noH2 raL) hraL

/-- A fortiori under the strict semantics. -/
theorem noH2_not_strict : ¬ IsSAlphabetT shivasutras_noH2 paniniClasses :=
  fun h => noH2_not_lax h.isSAlphabet

/-! ## Counting the pratyāhāras -/

/-- The well-formed pratyāhāra-forming pairs of the Śivasūtras: a sound `s` and
a marker `m` occurring after (the first occurrence of) `s`. -/
def wellFormedPairs : Finset (Sound × Marker) :=
  Finset.univ.filter (fun p => Terminates shivasutras p.1 p.2)

/-- **304 well-formed pratyāhāras.** Petersen's count of 305 (2004, fn. 2) is
over segment occurrences; the pair formed at the second `h` — her (h′, L) — is
the first-occurrence pair (h, L) for us, so exactly one pair merges. -/
theorem card_wellFormed_pratyaharas : wellFormedPairs.card = 304 := by decide

/-- **13 singleton pratyāhāras** — one fewer than Petersen's 14: her extra
singleton is (h′, L) = {h}, which under first-occurrence reading denotes `haL`,
the full consonant class, instead. -/
theorem card_singleton_pratyaharas :
    (wellFormedPairs.filter
      (fun p => (pratyahara shivasutras p.1 p.2).card = 1)).card = 13 := by decide

end Panini
