import Panini.Interval
import Mathlib.Data.List.TakeWhile

/-!
# Route (b) Move 3: markers are right-endpoints

This file supplies the third structural move of the optimality argument — the part
that lower-bounds `numMarkers` — at the level of generality we can make fully
rigorous without Petersen's boundary-graph/planarity machinery.

**The idea.** A pratyāhāra interval `pratyahara A s m` runs from the first occurrence
of the sound `s` up to the first occurrence of the marker `m` after it. Its right
edge is therefore a specific *position* in the raw alphabet list — either a genuine
marker occurrence, or the end of the list if `m` never appears (`endPos`). The
crucial rigidity fact is:

> **Two classes realized with the same right edge are ⊆-comparable**
> (`subset_or_subset_of_endPos_eq`): both intervals end at the same position, so one
> is a positional suffix of the other, hence one class's sounds are a subset of the
> other's.

Contrapositive: pairwise ⊆-*incomparable* classes (an **antichain**) need pairwise
*distinct* right edges. Each right edge except possibly one (the end of the list) is
a genuine marker occurrence, and distinct positions give distinct occurrences. Hence
(`card_le_numMarkers_succ_of_antichain`):

> an antichain of `k` encodable classes forces `k - 1 ≤ numMarkers`.

This is a Dilworth-flavoured bound: what a single marker occurrence can serve is (at
most) a nested chain, so the marker count is at least the width of the class family.
It is *weaker* than Petersen's tight count (her boundary-graph runs also force
markers between nested classes when the traversal direction flips — that is the part
that would need genuine graph-planarity infrastructure), but it is fully rigorous,
self-contained, and — instantiated with a real 11-antichain of attested pratyāhāras
in `Optimality.lean` — it turns the marker half of the lower bound from a bare
hypothesis into `10 ≤ numMarkers`, proved.

The counting device (`markerTails`): a marker occurrence is identified with the
suffix of the alphabet starting at it, so "number of marker occurrences" becomes the
cardinality of a `Finset` of suffixes — no index bookkeeping, and
`(markerTails A).card = A.numMarkers` falls to an easy induction.
-/

open List

namespace Panini

/-! ## The raw interval and its edges -/

/-- The raw item-segment a pratyāhāra reads: from the first occurrence of `s`
(inclusive) up to the first following occurrence of the marker `m` (exclusive).
`praLits` is its sound-projection, `pratyahara` the `Finset` of those sounds. -/
def praItems (A : SAlphabet) (s : Sound) (m : Marker) : List Item :=
  (A.dropWhile (fun i => decide (i ≠ Item.snd s))).takeWhile
    (fun i => decide (i ≠ Item.mark m))

theorem praLits_eq_filterMap (A : SAlphabet) (s : Sound) (m : Marker) :
    praLits A s m = (praItems A s m).filterMap Item.toSound := rfl

/-- Number of items strictly before the interval (everything before the first `s`). -/
def startLen (A : SAlphabet) (s : Sound) : Nat :=
  (A.takeWhile (fun i => decide (i ≠ Item.snd s))).length

/-- One-past-the-end position of the interval: the position of the terminating
marker occurrence, or `A.length` if the marker never occurs after `s`. -/
def endPos (A : SAlphabet) (s : Sound) (m : Marker) : Nat :=
  startLen A s + (praItems A s m).length

/-! ## Two small `takeWhile`/`dropWhile` facts

Mathlib relates `takeWhile`/`dropWhile` to each other (`takeWhile_append_dropWhile`)
but not, in the form we need, to `take`/`drop` at the split point. -/

section TakeDropWhile
variable {α : Type*} (p : α → Bool)

theorem dropWhile_eq_drop (l : List α) :
    l.dropWhile p = l.drop (l.takeWhile p).length := by
  induction l with
  | nil => rfl
  | cons a l ih =>
    by_cases h : p a
    · simp [h, ih]
    · simp [h]

theorem takeWhile_eq_take (l : List α) :
    l.takeWhile p = l.take (l.takeWhile p).length := by
  induction l with
  | nil => rfl
  | cons a l ih =>
    by_cases h : p a
    · simp only [List.takeWhile_cons, h]
      simpa using ih
    · simp [h]

end TakeDropWhile

/-! ## The interval, cut out of the alphabet by position -/

/-- The raw interval is literally the slice of `A` between `startLen` and `endPos`. -/
theorem praItems_eq_drop_take (A : SAlphabet) (s : Sound) (m : Marker) :
    praItems A s m = (A.take (endPos A s m)).drop (startLen A s) := by
  unfold endPos startLen
  rw [← List.take_drop, ← dropWhile_eq_drop]
  exact takeWhile_eq_take _ _

theorem endPos_le_length (A : SAlphabet) (s : Sound) (m : Marker) :
    endPos A s m ≤ A.length := by
  unfold endPos startLen
  have h1 : (praItems A s m).length
      ≤ (A.dropWhile (fun i => decide (i ≠ Item.snd s))).length :=
    (List.takeWhile_sublist _).length_le
  have h2 : (A.takeWhile (fun i => decide (i ≠ Item.snd s))).length
      + (A.dropWhile (fun i => decide (i ≠ Item.snd s))).length = A.length := by
    rw [← List.length_append, List.takeWhile_append_dropWhile]
  omega

/-- What lies at (and after) the right edge: dropping `endPos` items lands exactly on
the terminating-marker search, so the suffix starts with `m` whenever it is nonempty. -/
theorem drop_endPos (A : SAlphabet) (s : Sound) (m : Marker) :
    A.drop (endPos A s m) =
      (A.dropWhile (fun i => decide (i ≠ Item.snd s))).dropWhile
        (fun i => decide (i ≠ Item.mark m)) := by
  unfold endPos startLen praItems
  rw [← List.drop_drop, ← dropWhile_eq_drop, ← dropWhile_eq_drop]

/-! ## Rigidity: a shared right edge forces nesting -/

/-- If two pratyāhāras of `A` end at the same position and the first starts no later
than the second, the second's interval is a suffix of the first's — so its class is
contained in the first's. -/
theorem pratyahara_subset_of_endPos_eq {A : SAlphabet} {s₁ s₂ : Sound}
    {m₁ m₂ : Marker} (hp : endPos A s₁ m₁ = endPos A s₂ m₂)
    (hle : startLen A s₁ ≤ startLen A s₂) :
    pratyahara A s₂ m₂ ⊆ pratyahara A s₁ m₁ := by
  have ha : startLen A s₁ + (startLen A s₂ - startLen A s₁) = startLen A s₂ := by omega
  have key : praItems A s₂ m₂
      = (praItems A s₁ m₁).drop (startLen A s₂ - startLen A s₁) := by
    rw [praItems_eq_drop_take A s₂ m₂, praItems_eq_drop_take A s₁ m₁,
      List.drop_drop, ha, hp]
  intro x hx
  rw [pratyahara_eq_toFinset, List.mem_toFinset] at hx ⊢
  have hsub : praLits A s₂ m₂ <+ praLits A s₁ m₁ := by
    rw [praLits_eq_filterMap, praLits_eq_filterMap, key]
    exact (List.drop_sublist _ _).filterMap _
  exact hsub.subset hx

/-- **Rigidity.** Two pratyāhāras of `A` ending at the same position denote
⊆-comparable classes. -/
theorem subset_or_subset_of_endPos_eq {A : SAlphabet} {s₁ s₂ : Sound}
    {m₁ m₂ : Marker} (hp : endPos A s₁ m₁ = endPos A s₂ m₂) :
    pratyahara A s₁ m₁ ⊆ pratyahara A s₂ m₂ ∨
      pratyahara A s₂ m₂ ⊆ pratyahara A s₁ m₁ := by
  rcases le_total (startLen A s₁) (startLen A s₂) with hle | hle
  · exact Or.inr (pratyahara_subset_of_endPos_eq hp hle)
  · exact Or.inl (pratyahara_subset_of_endPos_eq hp.symm hle)

/-! ## Counting marker occurrences as marker-headed suffixes -/

/-- Does the list start with a marker? -/
def headIsMark : List Item → Bool
  | Item.mark _ :: _ => true
  | _ => false

/-- The marker occurrences of `A`, each identified with the suffix of `A` that starts
at it. Distinct occurrences give distinct (different-length) suffixes, so this is a
faithful, index-free representation of "the set of marker occurrences." -/
def markerTails (A : SAlphabet) : Finset (List Item) :=
  (A.tails.filter headIsMark).toFinset

theorem nodup_tails {α : Type*} (l : List α) : l.tails.Nodup := by
  induction l with
  | nil => simp
  | cons a l ih =>
    rw [List.tails_cons]
    refine List.nodup_cons.mpr ⟨fun hmem => ?_, ih⟩
    have hle := ((List.mem_tails _ _).mp hmem).length_le
    simp at hle

theorem length_filter_tails (A : SAlphabet) :
    (A.tails.filter headIsMark).length = A.numMarkers := by
  induction A with
  | nil => rfl
  | cons x A ih =>
    unfold SAlphabet.numMarkers at ih ⊢
    rw [List.tails_cons, List.filter_cons, List.filter_cons]
    cases x <;> simp [headIsMark, ih]

/-- There are exactly `numMarkers` marker-headed suffixes. -/
theorem card_markerTails (A : SAlphabet) : (markerTails A).card = A.numMarkers := by
  rw [markerTails, List.toFinset_card_of_nodup ((nodup_tails A).filter _)]
  exact length_filter_tails A

/-- A nonempty suffix cut at a pratyāhāra's right edge starts with its marker. -/
theorem headIsMark_drop_endPos {A : SAlphabet} {s : Sound} {m : Marker}
    (h : A.drop (endPos A s m) ≠ []) :
    headIsMark (A.drop (endPos A s m)) = true := by
  rw [drop_endPos] at h ⊢
  have hhead := List.head_dropWhile_not (fun i => decide (i ≠ Item.mark m)) h
  have hm : ((A.dropWhile (fun i => decide (i ≠ Item.snd s))).dropWhile
      (fun i => decide (i ≠ Item.mark m))).head h = Item.mark m := by
    simpa using hhead
  rw [← List.cons_head_tail h, hm]
  rfl

/-! ## The packaged lower bound -/

/-- **Move 3, the packaged theorem.** If `A` encodes every class of a family `𝒜`
that is a ⊆-**antichain** (no class contains another), then `A` carries at least
`𝒜.card - 1` markers.

Each class's interval ends either at a marker occurrence or at the very end of the
alphabet; by rigidity (`subset_or_subset_of_endPos_eq`) no two classes of an
antichain can share an edge, and only one edge can be the alphabet's end — so at
least `𝒜.card - 1` distinct marker occurrences exist. -/
theorem card_le_numMarkers_succ_of_antichain {A : SAlphabet} {𝒜 : Finset Class}
    (henc : ∀ C ∈ 𝒜, Encodes A C)
    (hanti : ∀ C ∈ 𝒜, ∀ D ∈ 𝒜, C ⊆ D → C = D) :
    𝒜.card ≤ A.numMarkers + 1 := by
  classical
  have henc' : ∀ C ∈ 𝒜, ∃ sm : Sound × Marker, pratyahara A sm.1 sm.2 = C := by
    intro C hC
    obtain ⟨s, m, hsm⟩ := henc C hC
    exact ⟨(s, m), hsm⟩
  choose sm hsm using henc'
  -- Send each class to the suffix of `A` starting at its interval's right edge.
  let F : Class → List Item := fun C =>
    if h : C ∈ 𝒜 then A.drop (endPos A (sm C h).1 (sm C h).2) else []
  have hF : ∀ (C) (hC : C ∈ 𝒜), F C = A.drop (endPos A (sm C hC).1 (sm C hC).2) := by
    intro C hC
    simp only [F, dif_pos hC]
  have hmaps : Set.MapsTo F ↑𝒜 ↑(insert ([] : List Item) (markerTails A)) := by
    intro C hC'
    have hC : C ∈ 𝒜 := Finset.mem_coe.mp hC'
    rw [Finset.mem_coe, hF C hC]
    by_cases hne : A.drop (endPos A (sm C hC).1 (sm C hC).2) = []
    · rw [hne]
      exact Finset.mem_insert_self _ _
    · refine Finset.mem_insert_of_mem ?_
      rw [markerTails, List.mem_toFinset, List.mem_filter]
      exact ⟨(List.mem_tails _ _).mpr (List.drop_suffix _ _),
        headIsMark_drop_endPos hne⟩
  have hinj : Set.InjOn F ↑𝒜 := by
    intro C hC' D hD' hFeq
    have hC : C ∈ 𝒜 := Finset.mem_coe.mp hC'
    have hD : D ∈ 𝒜 := Finset.mem_coe.mp hD'
    rw [hF C hC, hF D hD] at hFeq
    have hlen := congrArg List.length hFeq
    rw [List.length_drop, List.length_drop] at hlen
    have hpC := endPos_le_length A (sm C hC).1 (sm C hC).2
    have hpD := endPos_le_length A (sm D hD).1 (sm D hD).2
    have hpe : endPos A (sm C hC).1 (sm C hC).2
        = endPos A (sm D hD).1 (sm D hD).2 := by omega
    rcases subset_or_subset_of_endPos_eq hpe with hsub | hsub
    · rw [hsm C hC, hsm D hD] at hsub
      exact hanti C hC D hD hsub
    · rw [hsm C hC, hsm D hD] at hsub
      exact (hanti D hD C hC hsub).symm
  calc 𝒜.card ≤ (insert ([] : List Item) (markerTails A)).card :=
        Finset.card_le_card_of_injOn F hmaps hinj
    _ ≤ (markerTails A).card + 1 := Finset.card_insert_le _ _
    _ = A.numMarkers + 1 := by rw [card_markerTails]

/-! ## The strict bound: no `+1` slack

Under the lax `Encodes`, one class per alphabet can be realized as an unterminated
suffix (its "edge" is the end of the list, not a marker) — hence the `+ 1` above.
Under the strict `EncodesT` every interval genuinely ends at a marker occurrence, so
an antichain of `k` classes forces `k` markers outright. -/

/-- A well-formed pratyāhāra's right edge is a genuine position: `endPos` lands
strictly inside the alphabet (on the terminating marker occurrence). -/
theorem endPos_lt_length_of_terminates {A : SAlphabet} {s : Sound} {m : Marker}
    (h : Terminates A s m) : endPos A s m < A.length := by
  have hne : (A.dropWhile (fun i => decide (i ≠ Item.snd s))).dropWhile
      (fun i => decide (i ≠ Item.mark m)) ≠ [] := by
    intro hnil
    rw [List.dropWhile_eq_nil_iff] at hnil
    have := hnil _ h
    simp at this
  have hdrop : A.drop (endPos A s m) ≠ [] := by
    rw [drop_endPos]
    exact hne
  by_contra hle
  exact hdrop (List.drop_eq_nil_of_le (by omega))

/-- **Move 3, strict form.** If `A` *strictly* encodes every class of a
⊆-antichain `𝒜`, then `A` carries at least `𝒜.card` markers: every class's
interval ends at a genuine marker occurrence, and rigidity
(`subset_or_subset_of_endPos_eq`) keeps the occurrences of incomparable classes
pairwise distinct. -/
theorem card_le_numMarkers_of_antichainT {A : SAlphabet} {𝒜 : Finset Class}
    (henc : ∀ C ∈ 𝒜, EncodesT A C)
    (hanti : ∀ C ∈ 𝒜, ∀ D ∈ 𝒜, C ⊆ D → C = D) :
    𝒜.card ≤ A.numMarkers := by
  classical
  have henc' : ∀ C ∈ 𝒜, ∃ sm : Sound × Marker,
      Terminates A sm.1 sm.2 ∧ pratyahara A sm.1 sm.2 = C := by
    intro C hC
    obtain ⟨s, m, hterm, hsm⟩ := henc C hC
    exact ⟨(s, m), hterm, hsm⟩
  choose sm hterm hsm using henc'
  let F : Class → List Item := fun C =>
    if h : C ∈ 𝒜 then A.drop (endPos A (sm C h).1 (sm C h).2) else []
  have hF : ∀ (C) (hC : C ∈ 𝒜), F C = A.drop (endPos A (sm C hC).1 (sm C hC).2) := by
    intro C hC
    simp only [F, dif_pos hC]
  have hne : ∀ (C) (hC : C ∈ 𝒜), F C ≠ [] := by
    intro C hC
    rw [hF C hC]
    have := endPos_lt_length_of_terminates (hterm C hC)
    intro hnil
    have := congrArg List.length hnil
    rw [List.length_drop] at this
    simp at this
    omega
  have hmaps : Set.MapsTo F ↑𝒜 ↑(markerTails A) := by
    intro C hC'
    have hC : C ∈ 𝒜 := Finset.mem_coe.mp hC'
    rw [Finset.mem_coe, markerTails, List.mem_toFinset, List.mem_filter, hF C hC]
    refine ⟨(List.mem_tails _ _).mpr (List.drop_suffix _ _), ?_⟩
    have := hne C hC
    rw [hF C hC] at this
    exact headIsMark_drop_endPos this
  have hinj : Set.InjOn F ↑𝒜 := by
    intro C hC' D hD' hFeq
    have hC : C ∈ 𝒜 := Finset.mem_coe.mp hC'
    have hD : D ∈ 𝒜 := Finset.mem_coe.mp hD'
    rw [hF C hC, hF D hD] at hFeq
    have hlen := congrArg List.length hFeq
    rw [List.length_drop, List.length_drop] at hlen
    have hpC := endPos_le_length A (sm C hC).1 (sm C hC).2
    have hpD := endPos_le_length A (sm D hD).1 (sm D hD).2
    have hpe : endPos A (sm C hC).1 (sm C hC).2
        = endPos A (sm D hD).1 (sm D hD).2 := by omega
    rcases subset_or_subset_of_endPos_eq hpe with hsub | hsub
    · rw [hsm C hC, hsm D hD] at hsub
      exact hanti C hC D hD hsub
    · rw [hsm C hC, hsm D hD] at hsub
      exact (hanti D hD C hC hsub).symm
  calc 𝒜.card ≤ (markerTails A).card := Finset.card_le_card_of_injOn F hmaps hinj
    _ = A.numMarkers := card_markerTails A

end Panini
