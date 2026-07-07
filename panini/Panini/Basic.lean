import Mathlib.Data.Finset.Basic
import Mathlib.Data.Fintype.Basic
import Mathlib.Tactic

/-!
# The Śivasūtras, formalized

This file models Pāṇini's `Māheśvara` / `Śivasūtras` — the 14 lines that list every
sound of Sanskrit, each terminated by a single *marker* letter (an `anubandha`).
From this ordering Pāṇini builds `pratyāhāra`s: two-letter abbreviations naming a
contiguous run of sounds, used throughout the Aṣṭādhyāyī to say "any vowel", "any
consonant", "any voiced stop", and so on.

This is **Rung ①** of the build path: model the object, and (in `Pratyahara.lean`)
prove the abbreviations denote exactly the sets the tradition says they do.

Modeling choices:
* The 42 distinct sounds of the Śivasūtras become constructors of `Sound`.
* Each of the 14 lines ends in a *distinct* marker (`Marker`). Traditionally two
  lines end in `Ṇ` and the reader disambiguates by "nearest following marker"; we
  give each line its own marker token (`N1`, `N2`) which is a faithful and simpler
  encoding, since each marker then occurs exactly once.
* `h` is the one sound that appears **twice** (lines 5 and 14) — the crux of the
  optimality story in `Optimality.lean`.
-/

namespace Panini

/-- The 42 distinct sounds (`varṇa`) enumerated by the Śivasūtras. The *ordering*
lives in `shivasutras` below, not in this declaration. -/
inductive Sound where
  -- 9 vowels (a i u ṛ ḷ e o ai au)
  | a | i | u | rvoc | lvoc | e | o | ai | au
  -- the aspirate h
  | h
  -- 4 semivowels (y v r l)
  | y | v | r | l
  -- 5 nasals (ñ m ṅ ṇ n)
  | nya | ma | nga | nretro | na
  -- 5 voiced aspirated stops (jh bh gh ḍh dh)
  | jha | bha | gha | ddha | dha
  -- 5 voiced unaspirated stops (j b g ḍ d)
  | ja | ba | ga | dda | da
  -- 10 voiceless stops (kh ph ch ṭh th c ṭ t k p)
  | kha | pha | cha | ttha | tha | ca | tta | ta | ka | pa
  -- 3 sibilants (ś ṣ s)
  | sha | ssa | sa
  deriving DecidableEq, Fintype, Repr

/-- The 14 `anubandha` markers, one per Śivasūtra line, in textual order.
`N1` ends line 1 (`aiuṆ`); `N2` ends line 6 (`laṆ`); etc. -/
inductive Marker where
  | N1 | K | Ng | C | T1 | N2 | M | Ny | Sh | Sx | V | Y | R | L
  deriving DecidableEq, Fintype, Repr

/-- An entry in an S-alphabet is either a sound or a marker. -/
inductive Item where
  | snd : Sound → Item
  | mark : Marker → Item
  deriving DecidableEq, Repr

/-- Project the sound out of an item (markers project to `none`). -/
def Item.toSound : Item → Option Sound
  | .snd s => some s
  | .mark _ => none

/-- An **S-alphabet** is a linear arrangement of sounds interleaved with markers. -/
abbrev SAlphabet := List Item

/-- A **natural class** is just a finite set of sounds. -/
abbrev Class := Finset Sound

/-- Pāṇini's actual ordering: the 14 Śivasūtras flattened into one list.

```
1.  a i u              Ṇ
2.  ṛ ḷ                K
3.  e o                Ṅ
4.  ai au              C
5.  h y v r            Ṭ
6.  l                  Ṇ
7.  ñ m ṅ ṇ n          M
8.  jh bh              Ñ
9.  gh ḍh dh           Ṣ
10. j b g ḍ d          Ś
11. kh ph ch ṭh th c ṭ t   V
12. k p                Y
13. ś ṣ s              R
14. h                  L
```
-/
def shivasutras : SAlphabet :=
  open Sound Marker in
  [ .snd a, .snd i, .snd u, .mark N1,
    .snd rvoc, .snd lvoc, .mark K,
    .snd e, .snd o, .mark Ng,
    .snd ai, .snd au, .mark C,
    .snd h, .snd y, .snd v, .snd r, .mark T1,
    .snd l, .mark N2,
    .snd nya, .snd ma, .snd nga, .snd nretro, .snd na, .mark M,
    .snd jha, .snd bha, .mark Ny,
    .snd gha, .snd ddha, .snd dha, .mark Sh,
    .snd ja, .snd ba, .snd ga, .snd dda, .snd da, .mark Sx,
    .snd kha, .snd pha, .snd cha, .snd ttha, .snd tha, .snd ca, .snd tta, .snd ta, .mark V,
    .snd ka, .snd pa, .mark Y,
    .snd sha, .snd ssa, .snd sa, .mark R,
    .snd h, .mark L ]

/-- The 9 vowels, as a predicate. -/
def Sound.isVowel : Sound → Bool
  | .a | .i | .u | .rvoc | .lvoc | .e | .o | .ai | .au => true
  | _ => false

/-- The **pratyāhāra** named by "sound `s` + marker `m`": every sound from the first
occurrence of `s` up to (but not including) the first `m` after it. This is the
interval-reading device that makes the whole alphabet pay off. -/
def pratyahara (A : SAlphabet) (s : Sound) (m : Marker) : Class :=
  (((A.dropWhile (fun i => decide (i ≠ Item.snd s))).takeWhile
      (fun i => decide (i ≠ Item.mark m))).filterMap Item.toSound).toFinset

end Panini
