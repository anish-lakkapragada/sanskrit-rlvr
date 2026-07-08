# No anubandha is redundant: every Śivasūtra marker is load-bearing, in Lean 4

**Result.** Pāṇini's Śivasūtras use exactly 14 marker letters (*anubandhas*) and
exactly one duplicated sound (the second `h`). The Sanskrit tradition's famous
economy principle (*lāghava* — "grammarians rejoice over the saving of half a
mora as over the birth of a son") asserts that nothing in Pāṇini is redundant.
At the Śivasūtra level this is now a machine-checked theorem:

- **`no_marker_redundant`** — delete *any single one* of the 14 markers and some
  class the grammar actually uses loses its well-formed pratyāhāra. For each of
  the 14 truncated alphabets, the Lean kernel searches **all 588 candidate
  (sound, marker) encodings** and confirms none rescues the witness class
  (`Ṇ₁ ↦ aṆ`, `K ↦ aK`, `Ṅ ↦ eṄ`, `C ↦ aiC`, `Ṭ ↦ aṬ`, `Ṇ₂ ↦ yaṆ`, `M ↦ ñaM`,
  `Ñ ↦ yaÑ`, `Ṣ ↦ jhaṢ`, `Ś ↦ jhaŚ`, `V ↦ chaV`, `Y ↦ khaY`, `R ↦ śaR`,
  `L ↦ raL`).
- **`noH2_not_lax` / `noH2_not_strict`** — the duplicated `h` cannot be dropped
  either, under *any* reading of pratyāhāras: without it, `raL` (the consonants
  minus `y v`) is flatly unencodable.
- **`card_wellFormed_pratyaharas` / `card_singleton_pratyaharas`** —
  kernel-verified counts: the Śivasūtras admit exactly **304** well-formed
  pratyāhāras, **13** of them singletons (refining the occurrence-based counts
  305/14 in Petersen 2004, fn. 2).

All `sorry`-free; axioms `propext`, `Classical.choice`, `Quot.sound`.

**Start here:** open [`README.html`](README.html) in a browser — an interactive
explainer for readers with no Sanskrit background where you can *delete each
marker yourself* and watch which class breaks, and why.

## Layout

| File | Role |
|---|---|
| `panini/Panini/Necessity.lean` | **the result**: irredundancy theorems + counts |
| `panini/Panini/Basic.lean`, `Pratyahara.lean` | the model: sounds, markers, pratyāhāras, strict semantics |
| `panini/Panini/Interval.lean`, `Markers.lean`, `Optimality.lean` | infrastructure (the 43 attested classes live in `Optimality.lean`; its own theorems are showcased on the `result/shivasutra-optimality` branch) |

## Build

```sh
cd panini
lake exe cache get   # download prebuilt Mathlib
lake build
```
