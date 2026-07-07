import Panini.Pratyahara

/-!
# Route (b) infrastructure: "encoding = interval", and "crossings force duplication"

This file is the reusable combinatorial engine behind Petersen's optimality result,
following the plan in the Part III note (`thinking/sanskrit-lean-scoring-targets.html`,
§6.5). It develops the two structural facts an optimality lower bound rests on, and
proves them `sorry`-free:

* **Move 1 — encoding = interval.** A pratyāhāra `pratyahara A s m` denotes the
  `toFinset` of a *contiguous infix* of `A`'s sound sequence (`praLits_infix`,
  `Encodes.exists_infix`). Naming a class as a pratyāhāra means laying its members
  out as a consecutive block.

* **Move 2 — crossings force duplication.** In a repetition-free layout, three
  *distinct* sounds cannot be pairwise adjacent (`no_pairwise_adj_triple`: you cannot
  draw a triangle on a path). Hence an alphabet that must encode a "crossing triangle"
  of two-element classes `{x,y}`, `{y,z}`, `{x,z}` is forced to repeat a sound
  (`one_le_duplications_of_triangle`). This is the abstract form of *why Pāṇini repeats
  `h`*.

The triangle here is the minimal obstruction to the *consecutive-ones property*. It is
genuine, reusable infrastructure; instantiating it on Pāṇini's actual (larger) classes
is the remaining linguistic input, discussed in `Optimality.lean`.
-/

-- These proofs use single-letter names (`a`, `y`, `v`, …) that collide with the
-- constructors of `Sound`; the collision is harmless here.
set_option linter.constructorNameAsVariable false

open List
namespace Panini

/-! ## The cost function (Petersen Def. 2.5)

These live here (rather than in `Optimality.lean`) because the lower-bound
infrastructure below refers to them. -/

/-- The sounds of an S-alphabet, in order, dropping the markers. -/
def SAlphabet.sounds (A : SAlphabet) : List Sound := A.filterMap Item.toSound

/-- The number of markers used. -/
def SAlphabet.numMarkers (A : SAlphabet) : Nat :=
  (A.filter (fun i => match i with | .mark _ => true | .snd _ => false)).length

/-- The number of *duplicated* sound-slots: total sound occurrences minus the number
of distinct sounds present. A sound appearing `k` times costs `k - 1` here. -/
def SAlphabet.duplications (A : SAlphabet) : Nat :=
  A.sounds.length - A.sounds.toFinset.card

/-- Petersen's cost: markers used, plus duplicated sounds. This is the quantity the
optimal S-alphabet minimizes — **not** overall length. -/
def cost (A : SAlphabet) : Nat := A.numMarkers + A.duplications

/-! ## Move 1: a pratyāhāra is a contiguous infix of the sound sequence -/

/-- The raw list of sounds a pratyāhāra collects, *before* `toFinset`. -/
def praLits (A : SAlphabet) (s : Sound) (m : Marker) : List Sound :=
  ((A.dropWhile (fun i => decide (i ≠ Item.snd s))).takeWhile
      (fun i => decide (i ≠ Item.mark m))).filterMap Item.toSound

@[simp] theorem pratyahara_eq_toFinset (A : SAlphabet) (s : Sound) (m : Marker) :
    pratyahara A s m = (praLits A s m).toFinset := rfl

/-- **Move 1.** The sounds named by any pratyāhāra form a contiguous infix of the
alphabet's sound sequence: naming a class *is* laying it out as an interval. -/
theorem praLits_infix (A : SAlphabet) (s : Sound) (m : Marker) :
    (praLits A s m) <:+: A.sounds := by
  unfold praLits SAlphabet.sounds
  have hinf : ((A.dropWhile (fun i => decide (i ≠ Item.snd s))).takeWhile
      (fun i => decide (i ≠ Item.mark m))) <:+: A :=
    (List.takeWhile_prefix _).isInfix.trans (List.dropWhile_suffix _).isInfix
  obtain ⟨pre, suf, h⟩ := hinf
  refine ⟨pre.filterMap Item.toSound, suf.filterMap Item.toSound, ?_⟩
  conv_rhs => rw [← h]
  simp [List.filterMap_append]

/-- Packaged for `Encodes`: an encoded class is the `toFinset` of a contiguous infix
of the sound sequence. -/
theorem Encodes.exists_infix {A : SAlphabet} {C : Class} (h : Encodes A C) :
    ∃ L : List Sound, L <:+: A.sounds ∧ L.toFinset = C := by
  obtain ⟨s, m, hsm⟩ := h
  exact ⟨praLits A s m, praLits_infix A s m, hsm⟩

/-! ## Abstract list combinatorics -/

section Abstract
variable {α : Type*} [BEq α] [LawfulBEq α]

/-- In a `Nodup` list, a length-2 infix `[a,b]` sits at consecutive indices:
`b` immediately follows `a`. -/
theorem idxOf_succ_of_infix {W : List α} (hW : W.Nodup) {a b : α}
    (h : [a, b] <:+: W) : W.idxOf a + 1 = W.idxOf b := by
  obtain ⟨p, q, hpq⟩ := h
  have hW' : W = p ++ (a :: b :: q) := by simpa using hpq.symm
  subst hW'
  rw [List.nodup_append] at hW
  obtain ⟨-, hnd2, hdis⟩ := hW
  have hap : a ∉ p := fun ha => hdis a ha a (by simp) rfl
  have hbp : b ∉ p := fun hb => hdis b hb b (by simp) rfl
  have hab : a ≠ b := by
    rw [List.nodup_cons] at hnd2
    exact fun h => hnd2.1 (by simp [h])
  rw [List.idxOf_append_of_notMem hap, List.idxOf_append_of_notMem hbp,
      List.idxOf_cons_eq _ rfl, List.idxOf_cons_ne _ hab, List.idxOf_cons_eq _ rfl]

/-- `idxOf` is injective on members (it returns the unique first index). -/
theorem idxOf_inj {W : List α} {a b : α} (ha : a ∈ W) (hb : b ∈ W)
    (h : W.idxOf a = W.idxOf b) : a = b := by
  have := List.getElem_idxOf (List.idxOf_lt_length_of_mem ha)
  rw [← this, ← List.getElem_idxOf (List.idxOf_lt_length_of_mem hb)]
  simp [h]

/-- Adjacency in a list: the two elements occur as a length-2 infix, either order. -/
def Adj (W : List α) (a b : α) : Prop := [a, b] <:+: W ∨ [b, a] <:+: W

/-- **The obstruction (Move 2).** In a `Nodup` list, three *distinct* elements cannot
be pairwise adjacent — a triangle cannot be drawn on a path. -/
theorem no_pairwise_adj_triple {W : List α} (hW : W.Nodup) {x y z : α}
    (hxy : x ≠ y) (hyz : y ≠ z) (hxz : x ≠ z)
    (hx : x ∈ W) (hy : y ∈ W) (hz : z ∈ W)
    (axy : Adj W x y) (ayz : Adj W y z) (axz : Adj W x z) : False := by
  have dxy : W.idxOf x ≠ W.idxOf y := fun h => hxy (idxOf_inj hx hy h)
  have dyz : W.idxOf y ≠ W.idxOf z := fun h => hyz (idxOf_inj hy hz h)
  have dxz : W.idxOf x ≠ W.idxOf z := fun h => hxz (idxOf_inj hx hz h)
  have e (a b : α) : Adj W a b → W.idxOf a + 1 = W.idxOf b ∨ W.idxOf b + 1 = W.idxOf a :=
    fun h => h.elim (fun i => Or.inl (idxOf_succ_of_infix hW i))
                    (fun i => Or.inr (idxOf_succ_of_infix hW i))
  rcases e _ _ axy with h1 | h1 <;> rcases e _ _ ayz with h2 | h2 <;>
    rcases e _ _ axz with h3 | h3 <;> omega

/-! ### Move 2, generalized: convexity

The pairwise "crossing triangle" obstruction above needs literal 2-element classes
`{x,y}`, `{y,z}`, `{x,z}` — a shape that never occurs among Pāṇini's *actual*
pratyāhāras (his classes are large intervals, not bare pairs). The real forcing
argument (Petersen 2004, §4.2, Fig. 5–6: "the class memberships of h, v and l are
independent of each other") only needs, for each pair drawn from three sounds, *some*
encoded class containing that pair while excluding the third sound — which is exactly
what happens for Pāṇini's `h`, `v`, `l` (see `Optimality.lean`). The underlying fact is
elementary **convexity**, not adjacency: an interval containing two points contains
everything positioned between them. -/

/-- `q` sits (in either direction) between `p` and `r` in the index order of `W`. -/
def IdxBetween (W : List α) (p q r : α) : Prop :=
  (W.idxOf p < W.idxOf q ∧ W.idxOf q < W.idxOf r) ∨
  (W.idxOf r < W.idxOf q ∧ W.idxOf q < W.idxOf p)

/-- **Convexity.** If `L` is a contiguous infix of a `Nodup` list `W`, `p, r ∈ L`, and
`q ∈ W` sits between `p` and `r` in `W`'s index order, then `q ∈ L` too. -/
theorem mem_of_idxBetween {W L : List α} (hW : W.Nodup) (hL : L <:+: W)
    {p q r : α} (hp : p ∈ L) (hr : r ∈ L) (hq : q ∈ W) (hb : IdxBetween W p q r) :
    q ∈ L := by
  obtain ⟨pre, suf, heq⟩ := hL
  have hWeq : W = pre ++ L ++ suf := heq.symm
  rw [hWeq] at hW hq hb
  rw [List.nodup_append, List.nodup_append] at hW
  obtain ⟨⟨-, -, hdisPreL⟩, -, hdisPLSuf⟩ := hW
  have hpBound : pre.length ≤ (pre ++ L ++ suf).idxOf p ∧
      (pre ++ L ++ suf).idxOf p < pre.length + L.length := by
    have h1 : (pre ++ L ++ suf).idxOf p = (pre ++ L).idxOf p :=
      List.idxOf_append_of_mem (List.mem_append.mpr (Or.inr hp))
    have h2 : (pre ++ L).idxOf p = pre.length + L.idxOf p :=
      List.idxOf_append_of_notMem (fun h => hdisPreL p h p hp rfl)
    have h3 : L.idxOf p < L.length := List.idxOf_lt_length_of_mem hp
    omega
  have hrBound : pre.length ≤ (pre ++ L ++ suf).idxOf r ∧
      (pre ++ L ++ suf).idxOf r < pre.length + L.length := by
    have h1 : (pre ++ L ++ suf).idxOf r = (pre ++ L).idxOf r :=
      List.idxOf_append_of_mem (List.mem_append.mpr (Or.inr hr))
    have h2 : (pre ++ L).idxOf r = pre.length + L.idxOf r :=
      List.idxOf_append_of_notMem (fun h => hdisPreL r h r hr rfl)
    have h3 : L.idxOf r < L.length := List.idxOf_lt_length_of_mem hr
    omega
  rcases List.mem_append.mp hq with hq' | hqsuf
  · rcases List.mem_append.mp hq' with hqpre | hqL
    · exfalso
      have hqEq : (pre ++ L ++ suf).idxOf q = pre.idxOf q := by
        rw [List.idxOf_append_of_mem (List.mem_append.mpr (Or.inl hqpre))]
        exact List.idxOf_append_of_mem hqpre
      have hqlt : pre.idxOf q < pre.length := List.idxOf_lt_length_of_mem hqpre
      unfold IdxBetween at hb
      omega
    · exact hqL
  · exfalso
    have hqnotPreL : q ∉ pre ++ L := fun h => hdisPLSuf q h q hqsuf rfl
    have hqEq : (pre ++ L ++ suf).idxOf q = (pre ++ L).length + suf.idxOf q :=
      List.idxOf_append_of_notMem hqnotPreL
    unfold IdxBetween at hb
    simp only [List.length_append] at hqEq
    omega

/-- Positions of distinct members of a `Nodup` list are distinct. -/
theorem idxOf_ne_of_ne {W : List α} {a b : α} (ha : a ∈ W) (hb : b ∈ W) (hab : a ≠ b) :
    W.idxOf a ≠ W.idxOf b := fun h => hab (idxOf_inj ha hb h)

/-- **The general obstruction.** Suppose three sounds `x, y, z` are *positionally
independent*: for each pair, some contiguous infix of `W` contains that pair while
excluding the third element. Then no such configuration is realizable in a `Nodup`
list — one of the three infixes is always forced (by convexity) to contain the very
element it was supposed to exclude. This is the general, adjacency-free form of the
"three independent elements force a crossing" fact (Petersen's `K⁵`-triple), proved by
elementary betweenness rather than graph planarity. -/
theorem false_of_independent_triple {W : List α} (hW : W.Nodup)
    {x y z : α} {L1 L2 L3 : List α}
    (hx : x ∈ W) (hy : y ∈ W) (hz : z ∈ W)
    (hL1 : L1 <:+: W) (hxL1 : x ∈ L1) (hyL1 : y ∈ L1) (hzL1 : z ∉ L1)
    (hL2 : L2 <:+: W) (hyL2 : y ∈ L2) (hzL2 : z ∈ L2) (hxL2 : x ∉ L2)
    (hL3 : L3 <:+: W) (hxL3 : x ∈ L3) (hzL3 : z ∈ L3) (hyL3 : y ∉ L3) :
    False := by
  have hxy : x ≠ y := fun h => hxL2 (h ▸ hyL2)
  have hyz : y ≠ z := fun h => hyL3 (h ▸ hzL3)
  have hxz : x ≠ z := fun h => hzL1 (h ▸ hxL1)
  have dxy := idxOf_ne_of_ne hx hy hxy
  have dyz := idxOf_ne_of_ne hy hz hyz
  have dxz := idxOf_ne_of_ne hx hz hxz
  have htri : IdxBetween W x y z ∨ IdxBetween W y x z ∨ IdxBetween W x z y := by
    unfold IdxBetween; omega
  rcases htri with hb | hb | hb
  · exact hyL3 (mem_of_idxBetween hW hL3 hxL3 hzL3 hy hb)
  · exact hxL2 (mem_of_idxBetween hW hL2 hyL2 hzL2 hx hb)
  · exact hzL1 (mem_of_idxBetween hW hL1 hxL1 hyL1 hz hb)

end Abstract

/-! ## From `duplications = 0` to `Nodup`, and the duplication lower bound -/

/-- No duplicated sound-slot means the sound sequence is genuinely repetition-free. -/
theorem nodup_of_duplications_eq_zero {A : SAlphabet} (h : A.duplications = 0) :
    A.sounds.Nodup := by
  unfold SAlphabet.duplications at h
  have hle : A.sounds.toFinset.card ≤ A.sounds.length := List.toFinset_card_le _
  have heq : A.sounds.toFinset.card = A.sounds.length := by omega
  rw [List.card_toFinset] at heq
  have : A.sounds.dedup = A.sounds := (List.dedup_sublist _).eq_of_length heq
  exact List.dedup_eq_self.mp this

/-- If the sound sequence has no duplicates and `A` encodes the pair `{x,y}`
(`x ≠ y`), then `x` and `y` are adjacent in the sound sequence. -/
theorem adj_of_encodes_pair {A : SAlphabet} (hnd : A.sounds.Nodup) {x y : Sound}
    (hxy : x ≠ y) (h : Encodes A {x, y}) : Adj A.sounds x y := by
  obtain ⟨L, hinf, hLC⟩ := h.exists_infix
  have hLnd : L.Nodup := hinf.sublist.nodup hnd
  have hlen : L.length = 2 := by
    have hc : L.toFinset.card = L.length := by
      rw [List.card_toFinset, List.dedup_eq_self.mpr hLnd]
    rw [← hc, hLC, Finset.card_insert_of_notMem (by simp [hxy]), Finset.card_singleton]
  obtain ⟨c, d, rfl⟩ := List.length_eq_two.mp hlen
  have hset : ({c, d} : Finset Sound) = {x, y} := by simpa using hLC
  have hcx : c ∈ ({x, y} : Finset Sound) := hset ▸ (by simp)
  have hdx : d ∈ ({x, y} : Finset Sound) := hset ▸ (by simp)
  have hcd : c ≠ d := by
    simp only [List.nodup_cons, List.mem_singleton, List.not_mem_nil, List.nodup_nil] at hLnd
    tauto
  simp only [Finset.mem_insert, Finset.mem_singleton] at hcx hdx
  rcases hcx with rfl | rfl <;> rcases hdx with rfl | rfl
  · exact absurd rfl hcd          -- c = x = d, impossible
  · exact Or.inl hinf             -- c = x, d = y  ⇒  [x,y] infix
  · exact Or.inr hinf             -- c = y, d = x  ⇒  [y,x] infix
  · exact absurd rfl hcd          -- c = y = d, impossible

/-- **Duplication lower bound (Move 2), the packaged theorem.** If `A` encodes three
classes forming a crossing triangle `{x,y}`, `{y,z}`, `{x,z}` on distinct sounds, then
`A` must repeat a sound: `1 ≤ A.duplications`. This is the abstract statement of *why
an optimal S-alphabet duplicates a sound at all.* -/
theorem one_le_duplications_of_triangle {A : SAlphabet} {x y z : Sound}
    (hxy : x ≠ y) (hyz : y ≠ z) (hxz : x ≠ z)
    (exy : Encodes A {x, y}) (eyz : Encodes A {y, z}) (exz : Encodes A {x, z}) :
    1 ≤ A.duplications := by
  by_contra hlt
  have hz0 : A.duplications = 0 := by omega
  have hnd : A.sounds.Nodup := nodup_of_duplications_eq_zero hz0
  have mem : ∀ {a : Sound} {C : Class}, a ∈ C → Encodes A C → a ∈ A.sounds := by
    intro a C ha h
    obtain ⟨L, hinf, hLC⟩ := h.exists_infix
    exact hinf.sublist.subset (List.mem_toFinset.mp (by rw [hLC]; exact ha))
  exact no_pairwise_adj_triple hnd hxy hyz hxz
    (mem (by simp) exy) (mem (by simp) eyz) (mem (by simp) exz)
    (adj_of_encodes_pair hnd hxy exy) (adj_of_encodes_pair hnd hyz eyz)
    (adj_of_encodes_pair hnd hxz exz)

/-- **Duplication lower bound (Move 2), the real form.** Suppose three sounds `x, y,
z` are *positionally independent* w.r.t. the classes `A` encodes: some encoded class
contains `x, y` but not `z`; some encoded class contains `y, z` but not `x`; some
encoded class contains `x, z` but not `y`. Then `A` must repeat a sound.

Unlike `one_le_duplications_of_triangle`, this needs no 2-element classes — `C1, C2,
C3` can be arbitrarily large. This is exactly the shape of Petersen's claim that "the
class memberships of `h`, `v` and `l` are independent of each other" (2004, Fig. 5–6),
and it is what actually holds of Pāṇini's real pratyāhāras (see `Optimality.lean`). -/
theorem one_le_duplications_of_independent_triple {A : SAlphabet} {x y z : Sound}
    {C1 C2 C3 : Class}
    (e1 : Encodes A C1) (hx1 : x ∈ C1) (hy1 : y ∈ C1) (hz1 : z ∉ C1)
    (e2 : Encodes A C2) (hy2 : y ∈ C2) (hz2 : z ∈ C2) (hx2 : x ∉ C2)
    (e3 : Encodes A C3) (hx3 : x ∈ C3) (hz3 : z ∈ C3) (hy3 : y ∉ C3) :
    1 ≤ A.duplications := by
  by_contra hlt
  have hz0 : A.duplications = 0 := by omega
  have hnd : A.sounds.Nodup := nodup_of_duplications_eq_zero hz0
  obtain ⟨L1, hL1inf, hL1eq⟩ := e1.exists_infix
  obtain ⟨L2, hL2inf, hL2eq⟩ := e2.exists_infix
  obtain ⟨L3, hL3inf, hL3eq⟩ := e3.exists_infix
  have mem : ∀ {a : Sound} {L : List Sound} {C : Class}, L.toFinset = C → a ∈ C → a ∈ L :=
    fun {a L C} hLC ha => List.mem_toFinset.mp (hLC.symm ▸ ha)
  have notMem : ∀ {a : Sound} {L : List Sound} {C : Class}, L.toFinset = C → a ∉ C → a ∉ L :=
    fun {a L C} hLC ha hmem => ha (hLC ▸ List.mem_toFinset.mpr hmem)
  have memW : ∀ {a : Sound} {L : List Sound} {C : Class},
      L <:+: A.sounds → L.toFinset = C → a ∈ C → a ∈ A.sounds :=
    fun {a L C} hinf hLC ha => hinf.subset (mem hLC ha)
  exact false_of_independent_triple hnd
    (memW hL1inf hL1eq hx1) (memW hL1inf hL1eq hy1) (memW hL3inf hL3eq hz3)
    hL1inf (mem hL1eq hx1) (mem hL1eq hy1) (notMem hL1eq hz1)
    hL2inf (mem hL2eq hy2) (mem hL2eq hz2) (notMem hL2eq hx2)
    hL3inf (mem hL3eq hx3) (mem hL3eq hz3) (notMem hL3eq hy3)

end Panini
