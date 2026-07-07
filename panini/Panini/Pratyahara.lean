import Panini.Basic

/-!
# Rung ①: the pratyāhāra machinery is correct

Before anything *deep* can be said about the Śivasūtras, we must check that the
abbreviations actually denote the sets every grammar says they do: `aC` is the
vowels, `haL` is the consonants, and so on.

These are not theorems you prove by hand — they are *computations* the Lean kernel
runs. Everything is finite and `DecidableEq`, so each equality closes by `decide`.
This is the satisfying first commit, and it validates the data structure the
optimality theorem (`Optimality.lean`) is built on.
-/

namespace Panini

open Sound Marker

/-- The consonants: everything that is not one of the 9 vowels (33 sounds,
including the two occurrences-worth of `h`). -/
def consonants : Class := Finset.univ.filter (fun s => ¬ s.isVowel)

/-! ## The headline abbreviations -/

/-- `aC` (a … C) denotes exactly the nine vowels. This is Pāṇini's way of writing
"any vowel". -/
example : pratyahara shivasutras .a .C = {a, i, u, rvoc, lvoc, e, o, ai, au} := by decide

/-- `haL` (h … L) denotes exactly the consonants — Pāṇini's "any consonant". -/
example : pratyahara shivasutras .h .L = consonants := by decide

/-- `aL` (a … L) denotes *every* sound. -/
example : pratyahara shivasutras .a .L = Finset.univ := by decide

/-! ## A few more, to exercise the machinery -/

/-- `aṆ` (a … first Ṇ) = the three short simple vowels `a i u`. -/
example : pratyahara shivasutras .a .N1 = {a, i, u} := by decide

/-- `aK` (a … K) = the simple vowels `a i u ṛ ḷ`. -/
example : pratyahara shivasutras .a .K = {a, i, u, rvoc, lvoc} := by decide

/-- `iK` (i … K) = `i u ṛ ḷ` — the simple vowels other than `a`. -/
example : pratyahara shivasutras .i .K = {i, u, rvoc, lvoc} := by decide

/-- `eṄ` (e … Ṅ) = the guṇa vowels `e o`. -/
example : pratyahara shivasutras .e .Ng = {e, o} := by decide

/-- `yaṆ` (y … second Ṇ) = the four semivowels `y v r l`. -/
example : pratyahara shivasutras .y .N2 = {y, v, r, l} := by decide

/-- `yaM` (y … M) = semivowels together with the nasals. -/
example : pratyahara shivasutras .y .M = {y, v, r, l, nya, ma, nga, nretro, na} := by decide

/-- `jhaŚ` (jh … Ś) = the ten voiced stops. -/
example : pratyahara shivasutras .jha .Sx
    = {jha, bha, gha, ddha, dha, ja, ba, ga, dda, da} := by decide

/-- `śaR` (ś … R) = the three sibilants. -/
example : pratyahara shivasutras .sha .R = {sha, ssa, sa} := by decide

/-! ## What it means to *encode* a class -/

/-- An S-alphabet **encodes** a class when some pratyāhāra denotes it exactly.

⚠️ This is the *lax* reading: `pratyahara` is `takeWhile`-based, so when the marker
`m` never occurs after `s` the "interval" silently runs to the end of the list. The
lax reading admits marker-dropping rivals the tradition would reject (see
`shivasutras_noL` in `Optimality.lean`); `EncodesT` below is the faithful reading. -/
def Encodes (A : SAlphabet) (C : Class) : Prop := ∃ s m, pratyahara A s m = C

/-- `A` is an **S-alphabet for a family `𝒞`** when it encodes every class in `𝒞`
and every sound appears in it at least once. (Lax reading — see `IsSAlphabetT`.) -/
def IsSAlphabet (A : SAlphabet) (𝒞 : Finset Class) : Prop :=
  (∀ C ∈ 𝒞, Encodes A C) ∧ (∀ s : Sound, Item.snd s ∈ A)

/-- Sanity check: `Encodes` is decidable, so witnessed encodings close by `decide`. -/
example : Encodes shivasutras consonants := ⟨.h, .L, by decide⟩

/-! ## The strict (traditional) reading: the anubandha must exist

A pratyāhāra is a sound **plus its it-marker**; the tradition reads `haL` as "h up
to the marker L", which presupposes an occurrence of `L`. Pāṇini's 14th and final
Śivasūtra — the lone `h L` — exists precisely to close `haL`, `aL`, `śaL`, `vaL`,
`raL`, `jhaL`. Under the lax `Encodes` one may simply delete that final `L` and
lose nothing (`Optimality.lean` proves this, and with it that the traditional
marker-count claims are *false* for the lax reading); `Terminates` restores the
missing well-formedness condition. -/

/-- The pratyāhāra `(s, m)` is **well-formed** in `A`: the marker `m` actually
occurs after the first occurrence of `s`, so the `takeWhile` in `pratyahara` really
is cut off by `m` rather than falling off the end of the list. -/
def Terminates (A : SAlphabet) (s : Sound) (m : Marker) : Prop :=
  Item.mark m ∈ A.dropWhile (fun i => decide (i ≠ Item.snd s))

instance (A : SAlphabet) (s : Sound) (m : Marker) : Decidable (Terminates A s m) :=
  inferInstanceAs (Decidable (_ ∈ _))

/-- Strict encoding: some **well-formed** pratyāhāra denotes the class exactly. -/
def EncodesT (A : SAlphabet) (C : Class) : Prop :=
  ∃ s m, Terminates A s m ∧ pratyahara A s m = C

instance (A : SAlphabet) (C : Class) : Decidable (EncodesT A C) :=
  inferInstanceAs (Decidable (∃ s m, Terminates A s m ∧ pratyahara A s m = C))

theorem EncodesT.encodes {A : SAlphabet} {C : Class} (h : EncodesT A C) :
    Encodes A C := by
  obtain ⟨s, m, -, hsm⟩ := h
  exact ⟨s, m, hsm⟩

/-- `A` is a **strict S-alphabet for `𝒞`**: every class has a well-formed
pratyāhāra, and every sound occurs. This is the faithful counterpart of Petersen's
S-alphabets, where a pratyāhāra `aM` always names an existing marker `M`. -/
def IsSAlphabetT (A : SAlphabet) (𝒞 : Finset Class) : Prop :=
  (∀ C ∈ 𝒞, EncodesT A C) ∧ (∀ s : Sound, Item.snd s ∈ A)

theorem IsSAlphabetT.isSAlphabet {A : SAlphabet} {𝒞 : Finset Class}
    (h : IsSAlphabetT A 𝒞) : IsSAlphabet A 𝒞 :=
  ⟨fun C hC => (h.1 C hC).encodes, h.2⟩

end Panini
