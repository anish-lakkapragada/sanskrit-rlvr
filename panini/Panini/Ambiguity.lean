import Panini.Necessity

/-!
# The doubled Ṇ: Patañjali's "was there a dearth of symbols?"

As actually recited, the Śivasūtras use the *same* marker letter `Ṇ` to close
both line 1 (*a i u Ṇ*) and line 6 (*la Ṇ*). Kātyāyana and Patañjali already
asked why Pāṇini re-used a marker instead of picking a fresh one — Patañjali's
jab: was there a shortage of letters? The re-use makes some pratyāhāras
genuinely **ambiguous**: `aṆ` can run to the first Ṇ ({a, i, u}) or to the
second (the vowels plus *h y v r l*), and — as the tradition and the modern
literature both record — **the Aṣṭādhyāyī uses both readings** (the long one in
1.1.69, the short one elsewhere; likewise `iṆ` in 8.3.57 needs the long
reading).

Our main model dodges this by giving the two Ṇs distinct tokens (`N1`, `N2`).
This file models the recitation faithfully — one token — and proves that the
ambiguity is real and *irreducible*:

* `ambiguous_pratyaharas_card` — exactly **3** well-formed pratyāhāras of the
  recited Śivasūtras are ambiguous: `aṆ`, `iṆ`, `uṆ` (their near and far
  readings differ; every other pratyāhāra means the same under both).
* `nearest_convention_fails` — reading every pratyāhāra to the **nearest**
  following Ṇ (the default convention), the attested class `aṆ₂` (needed by
  8.4.57, and the reading 1.1.69 requires of `aṆ`) has **no encoding at all**.
* `farthest_convention_fails` — reading to the **farthest** Ṇ instead, the
  class `aṆ₁` = {a, i, u} (the reading of `aṆ` everywhere else) dies.
* `both_readings_attested` — under the single-token recitation, `aṆ` denotes
  `aṆ₁` on the near reading and `aṆ₂` on the far reading, and `iṆ` denotes
  `iṆ₂` on the far reading: Pāṇini's own usage requires **both**.
* `mixed_reading_covers` — allowing each pratyāhāra to choose its reading
  (which is what the grammar in fact does, rule by rule), all 43 attested
  classes are served.

Together: **no uniform convention for the doubled Ṇ is consistent with the
Aṣṭādhyāyī's usage; the re-use is only resolvable rule-by-rule.** That is the
formal content of Patañjali's complaint — the economy of one saved marker
letter is purchased with context-dependence in the metalanguage.
-/

set_option maxRecDepth 65536

namespace Panini

open Sound Marker

/-- The Śivasūtras **as recited**: line 6 closed by the *same* token `Ṇ` as
line 1 (we re-use the constructor `N1` for it). -/
def shivasutrasR : SAlphabet :=
  shivasutras.map (fun i => if i = Item.mark Marker.N2 then Item.mark Marker.N1 else i)

/-- The recited list still has 14 marker *occurrences* (13 distinct letters). -/
theorem numMarkers_shivasutrasR : shivasutrasR.numMarkers = 14 := by decide

/-! ## The far reading

`pratyahara` (Basic.lean) reads to the *nearest* following occurrence of the
marker token. The competing convention reads to the *farthest*. -/

/-- The item-segment of the far reading: from the first occurrence of `s` up to
(but excluding) the **last** occurrence of the token `m`. -/
def praFarItems (A : SAlphabet) (s : Sound) (m : Marker) : List Item :=
  (((A.dropWhile (fun i => decide (i ≠ Item.snd s))).reverse.dropWhile
      (fun i => decide (i ≠ Item.mark m))).reverse).dropLast

/-- The far reading of a pratyāhāra. -/
def pratyaharaF (A : SAlphabet) (s : Sound) (m : Marker) : Class :=
  ((praFarItems A s m).filterMap Item.toSound).toFinset

/-- Strict encoding under the far reading. -/
def EncodesF (A : SAlphabet) (C : Class) : Prop :=
  ∃ s m, Terminates A s m ∧ pratyaharaF A s m = C

instance (A : SAlphabet) (C : Class) : Decidable (EncodesF A C) :=
  inferInstanceAs (Decidable (∃ s m, Terminates A s m ∧ pratyaharaF A s m = C))

/-! ## The ambiguity is exactly {aṆ, iṆ, uṆ} -/

/-- **Exactly three pratyāhāras are ambiguous.** Among all well-formed
(sound, marker) pairs of the recited Śivasūtras, precisely `(a, Ṇ)`, `(i, Ṇ)`
and `(u, Ṇ)` denote different classes under the near and far readings — only
the sounds of line 1 see both Ṇs ahead of them. -/
theorem ambiguous_pratyaharas_card :
    (Finset.univ.filter (fun p : Sound × Marker =>
      Terminates shivasutrasR p.1 p.2 ∧
      pratyahara shivasutrasR p.1 p.2 ≠ pratyaharaF shivasutrasR p.1 p.2)).card
    = 3 := by decide +kernel

/-- And they are the expected three. -/
theorem ambiguous_pratyaharas :
    (Finset.univ.filter (fun p : Sound × Marker =>
      Terminates shivasutrasR p.1 p.2 ∧
      pratyahara shivasutrasR p.1 p.2 ≠ pratyaharaF shivasutrasR p.1 p.2))
    = {(a, .N1), (i, .N1), (u, .N1)} := by decide +kernel

/-! ## Neither uniform convention works -/

/-- Under the **nearest** convention, the attested class `aṆ₂` (the reading of
`aṆ` that 1.1.69 requires) is not encodable at all: `a` is the first sound, so
only pratyāhāras `(a, m)` can contain it, and none denotes `aṆ₂`. -/
theorem nearest_convention_fails :
    ¬ ∀ C ∈ paniniClasses, EncodesT shivasutrasR C := by
  intro hall
  have h := hall aN2 (by simp [paniniClasses])
  exact (by decide +kernel : ¬ EncodesT shivasutrasR aN2) h

/-- Under the **farthest** convention, the class `aṆ₁` = {a, i, u} (the reading
of `aṆ` everywhere outside 1.1.69) dies instead. -/
theorem farthest_convention_fails :
    ¬ ∀ C ∈ paniniClasses, EncodesF shivasutrasR C := by
  intro hall
  have h := hall aN1 (by simp [paniniClasses])
  exact (by decide +kernel : ¬ EncodesF shivasutrasR aN1) h

/-! ## Both readings are used — and together they suffice -/

/-- The doubled Ṇ carries genuine double duty: near-`aṆ` is `aṆ₁`, far-`aṆ` is
`aṆ₂`, and far-`iṆ` is `iṆ₂` — the readings the Aṣṭādhyāyī's rules demand. -/
theorem both_readings_attested :
    pratyahara shivasutrasR a .N1 = aN1 ∧
    pratyaharaF shivasutrasR a .N1 = aN2 ∧
    pratyaharaF shivasutrasR i .N1 = iN2 ∧
    pratyahara shivasutrasR y .N1 = yaN2 := by decide +kernel

/-- Allowing each pratyāhāra to pick its reading — as the grammar does, rule by
rule — every attested class is served by the recited Śivasūtras. -/
theorem mixed_reading_covers :
    ∀ C ∈ paniniClasses, EncodesT shivasutrasR C ∨ EncodesF shivasutrasR C := by
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact Or.inl ⟨a, .N1, by decide, by decide⟩
  · exact Or.inl ⟨a, .K, by decide, by decide⟩
  · exact Or.inl ⟨a, .C, by decide, by decide⟩
  · exact Or.inl ⟨a, .T1, by decide, by decide⟩
  · exact Or.inr ⟨a, .N1, by decide, by decide⟩
  · exact Or.inl ⟨a, .M, by decide, by decide⟩
  · exact Or.inl ⟨a, .Sx, by decide, by decide⟩
  · exact Or.inl ⟨a, .L, by decide, by decide⟩
  · exact Or.inl ⟨i, .K, by decide, by decide⟩
  · exact Or.inl ⟨i, .C, by decide, by decide⟩
  · exact Or.inr ⟨i, .N1, by decide, by decide⟩
  · exact Or.inl ⟨u, .K, by decide, by decide⟩
  · exact Or.inl ⟨e, .Ng, by decide, by decide⟩
  · exact Or.inl ⟨e, .C, by decide, by decide⟩
  · exact Or.inl ⟨ai, .C, by decide, by decide⟩
  · exact Or.inl ⟨h, .L, by decide, by decide⟩
  · exact Or.inl ⟨h, .Sx, by decide, by decide⟩
  · exact Or.inl ⟨y, .R, by decide, by decide⟩
  · exact Or.inl ⟨y, .Y, by decide, by decide⟩
  · exact Or.inl ⟨y, .Ny, by decide, by decide⟩
  · exact Or.inl ⟨y, .M, by decide, by decide⟩
  · exact Or.inl ⟨y, .N1, by decide, by decide⟩
  · exact Or.inl ⟨v, .L, by decide, by decide⟩
  · exact Or.inl ⟨v, .Sx, by decide, by decide⟩
  · exact Or.inl ⟨r, .L, by decide, by decide⟩
  · exact Or.inl ⟨nya, .M, by decide, by decide⟩
  · exact Or.inl ⟨ma, .Y, by decide, by decide⟩
  · exact Or.inl ⟨nga, .M, by decide, by decide⟩
  · exact Or.inl ⟨jha, .L, by decide, by decide⟩
  · exact Or.inl ⟨jha, .R, by decide, by decide⟩
  · exact Or.inl ⟨jha, .Y, by decide, by decide⟩
  · exact Or.inl ⟨jha, .Sx, by decide, by decide⟩
  · exact Or.inl ⟨jha, .Sh, by decide, by decide⟩
  · exact Or.inl ⟨bha, .Sh, by decide, by decide⟩
  · exact Or.inl ⟨ja, .Sx, by decide, by decide⟩
  · exact Or.inl ⟨ba, .Sx, by decide, by decide⟩
  · exact Or.inl ⟨kha, .R, by decide, by decide⟩
  · exact Or.inl ⟨kha, .Y, by decide, by decide⟩
  · exact Or.inl ⟨cha, .V, by decide, by decide⟩
  · exact Or.inl ⟨ca, .Y, by decide, by decide⟩
  · exact Or.inl ⟨ca, .R, by decide, by decide⟩
  · exact Or.inl ⟨sha, .L, by decide, by decide⟩
  · exact Or.inl ⟨sha, .R, by decide, by decide⟩

end Panini
