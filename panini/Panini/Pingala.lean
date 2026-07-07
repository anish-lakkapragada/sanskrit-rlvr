import Mathlib.Data.Nat.Fib.Basic
import Mathlib.Data.Fintype.Pi
import Mathlib.Tactic

/-!
# Piṅgala's prosody: the mātrā-meters are counted by the Fibonacci numbers

Sanskrit prosody (*chandas*), codified in Piṅgala's *Chandaḥśāstra* (c. 3rd–2nd
century BCE), analyses verse as sequences of light and heavy syllables: a
**laghu** (l) lasts one mora (*mātrā*), a **guru** (g) two. For *mātrā-vṛtta*
meters — fixed total duration, free syllable count — the combinatorial question
is: *how many patterns realize a total of n mātrās?* The answer, given by
Virahāṅka (c. 7th century) and elaborated by Gopāla and Hemacandra (c. 1150),
is the Fibonacci sequence, half a millennium before Fibonacci's *Liber Abaci*
(1202): a pattern of n mātrās ends either in a laghu (leaving n−1) or a guru
(leaving n−2), so the counts obey `V(n) = V(n−1) + V(n−2)`.

This file mechanizes the *combinatorial* statement, not just the recurrence:

* `patterns n` — Virahāṅka's enumeration of the weight-`n` patterns.
* `mem_patterns` — it is sound and complete: a pattern appears in `patterns n`
  **iff** its weight is `n`.
* `nodup_patterns` — no pattern is listed twice.
* `length_patterns` / `card_matra_patterns` — the count is `fib (n + 1)`:
  **the set of all laghu/guru sequences of total weight `n` has exactly
  `Nat.fib (n+1)` elements.**

As a companion, `card_varna_patterns` records Piṅgala's other famous count: the
*varṇa-vṛtta* meters of a fixed **syllable count** `n` number `2^n` — the
content of his *prastāra* enumeration, whose l/g expansions are a binary
numeral system two millennia before Leibniz.
-/

namespace Pingala

/-- A syllable of Sanskrit prosody: **laghu** (light, one mātrā) or **guru**
(heavy, two mātrās). -/
inductive Syllable where
  | laghu
  | guru
  deriving DecidableEq, Fintype, Repr

open Syllable

/-- The duration of a syllable in mātrās (morae). -/
def Syllable.matras : Syllable → ℕ
  | laghu => 1
  | guru => 2

/-- The total duration of a pattern, in mātrās. -/
def weight (p : List Syllable) : ℕ := (p.map Syllable.matras).sum

@[simp] theorem weight_nil : weight [] = 0 := rfl

@[simp] theorem weight_cons (s : Syllable) (p : List Syllable) :
    weight (s :: p) = s.matras + weight p := by
  simp [weight]

/-- Only the empty pattern has weight zero (every syllable lasts ≥ 1 mātrā). -/
theorem weight_eq_zero_iff {p : List Syllable} : weight p = 0 ↔ p = [] := by
  cases p with
  | nil => simp
  | cons s q => cases s <;> simp [Syllable.matras]

/-- **Virahāṅka's enumeration** of the mātrā-patterns of total weight `n`: a
weight-`n` pattern starts with a laghu followed by a weight-`(n−1)` pattern, or
a guru followed by a weight-`(n−2)` pattern. -/
def patterns : ℕ → List (List Syllable)
  | 0 => [[]]
  | 1 => [[laghu]]
  | (n + 2) => (patterns (n + 1)).map (laghu :: ·) ++ (patterns n).map (guru :: ·)

/-- Soundness: everything enumerated has the right weight. -/
theorem weight_of_mem_patterns : ∀ {n : ℕ} {p : List Syllable},
    p ∈ patterns n → weight p = n := by
  intro n
  induction n using patterns.induct with
  | case1 =>
    intro p hp
    simp [patterns] at hp
    simp [hp]
  | case2 =>
    intro p hp
    simp [patterns] at hp
    simp [hp, Syllable.matras]
  | case3 n ih1 ih2 =>
    intro p hp
    simp only [patterns, List.mem_append, List.mem_map] at hp
    rcases hp with ⟨q, hq, rfl⟩ | ⟨q, hq, rfl⟩
    · rw [weight_cons, ih1 hq]
      simp only [Syllable.matras]
      omega
    · rw [weight_cons, ih2 hq]
      simp only [Syllable.matras]
      omega

/-- Completeness: every pattern of weight `n` is enumerated. -/
theorem mem_patterns_of_weight : ∀ (p : List Syllable) {n : ℕ},
    weight p = n → p ∈ patterns n := by
  intro p
  induction p with
  | nil =>
    intro n hn
    simp at hn
    subst hn
    simp [patterns]
  | cons s q ih =>
    intro n hn
    rw [weight_cons] at hn
    cases s with
    | laghu =>
      have h1 : weight q + 1 = n := by
        simp only [Syllable.matras] at hn
        omega
      cases n with
      | zero => omega
      | succ m =>
        have hq : weight q = m := by omega
        cases m with
        | zero =>
          have hnil : q = [] := weight_eq_zero_iff.mp hq
          subst hnil
          simp [patterns]
        | succ k =>
          simp only [patterns, List.mem_append, List.mem_map]
          exact Or.inl ⟨q, ih hq, rfl⟩
    | guru =>
      have h1 : weight q + 2 = n := by
        simp only [Syllable.matras] at hn
        omega
      cases n with
      | zero => omega
      | succ m =>
        cases m with
        | zero => omega
        | succ k =>
          have hq : weight q = k := by omega
          simp only [patterns, List.mem_append, List.mem_map]
          exact Or.inr ⟨q, ih hq, rfl⟩

/-- The two are one: `patterns n` enumerates *exactly* the weight-`n` patterns. -/
theorem mem_patterns {n : ℕ} {p : List Syllable} :
    p ∈ patterns n ↔ weight p = n :=
  ⟨weight_of_mem_patterns, mem_patterns_of_weight p⟩

/-- No pattern is enumerated twice. -/
theorem nodup_patterns : ∀ n : ℕ, (patterns n).Nodup := by
  intro n
  induction n using patterns.induct with
  | case1 => simp [patterns]
  | case2 => simp [patterns]
  | case3 n ih1 ih2 =>
    simp only [patterns]
    refine List.Nodup.append ?_ ?_ ?_
    · exact ih1.map (fun a b h => by simpa using h)
    · exact ih2.map (fun a b h => by simpa using h)
    · intro p hp hq
      simp only [List.mem_map] at hp hq
      obtain ⟨_, -, rfl⟩ := hp
      obtain ⟨_, -, h⟩ := hq
      simp at h

/-- **The Virahāṅka–Hemacandra theorem, count form**: the mātrā-patterns of
total weight `n` number `fib (n + 1)`. -/
theorem length_patterns : ∀ n : ℕ, (patterns n).length = Nat.fib (n + 1) := by
  intro n
  induction n using patterns.induct with
  | case1 => rfl
  | case2 => rfl
  | case3 n ih1 ih2 =>
    have h := Nat.fib_add_two (n := n + 1)
    simp only [patterns, List.length_append, List.length_map, ih1, ih2]
    have e2 : n + 2 + 1 = n + 1 + 2 := rfl
    have e1 : n + 1 + 1 = n + 2 := rfl
    rw [e2, h, e1]
    omega

/-- **The Virahāṅka–Hemacandra theorem, set form**: the *set* of laghu/guru
sequences of total weight `n` has exactly `fib (n + 1)` elements. -/
theorem card_matra_patterns (n : ℕ) :
    ((patterns n).toFinset).card = Nat.fib (n + 1) := by
  rw [List.toFinset_card_of_nodup (nodup_patterns n), length_patterns]

/-- The Finset counted above is precisely `{p | weight p = n}`. -/
theorem mem_toFinset_patterns {n : ℕ} {p : List Syllable} :
    p ∈ (patterns n).toFinset ↔ weight p = n := by
  rw [List.mem_toFinset, mem_patterns]

/-- **Piṅgala's prastāra count**: the varṇa-vṛtta patterns of a fixed
*syllable count* `n` number `2 ^ n`. -/
theorem card_varna_patterns (n : ℕ) :
    Fintype.card (Fin n → Syllable) = 2 ^ n := by
  have h : Fintype.card Syllable = 2 := by decide
  simp [h]

end Pingala
