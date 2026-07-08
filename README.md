# The doubled Ṇ: Patañjali's "dearth of letters" complaint as a theorem, in Lean 4

**Result.** As actually recited, Pāṇini's Śivasūtras close both line 1
(*a i u Ṇ*) and line 6 (*la Ṇ*) with the **same marker letter Ṇ** — the only
marker he re-uses. Kātyāyana and Patañjali (the *Mahābhāṣya*, c. 150 BCE)
already asked why: was there a *dearth of letters*? The re-use makes some
pratyāhāras genuinely ambiguous — `aṆ` can run to the first Ṇ ({a, i, u}) or
to the second (the vowels plus *h y v r l*) — and the tradition records that
the Aṣṭādhyāyī **uses both readings** (the long one in 1.1.69, the short one
elsewhere). This branch models the recitation faithfully (one Ṇ token) and
proves the ambiguity is real and **irreducible**:

- **`ambiguous_pratyaharas`** — among all 588 candidate (sound, marker) pairs,
  **exactly 3** well-formed pratyāhāras are ambiguous (near-reading ≠
  far-reading): `aṆ`, `iṆ`, `uṆ`. Every other pratyāhāra means the same thing
  under both conventions — kernel-checked.
- **`nearest_convention_fails`** — resolve every pratyāhāra to the *nearest*
  following Ṇ (the default convention), and the attested class `aṆ₂` (the
  reading rule 1.1.69 demands) has **no encoding at all**.
- **`farthest_convention_fails`** — resolve to the *farthest* Ṇ instead, and
  `aṆ₁` = {a, i, u} (the reading of `aṆ` everywhere else) dies instead.
- **`both_readings_attested`** — under the single-token recitation, `aṆ`
  denotes `aṆ₁` on the near reading and `aṆ₂` on the far reading, and `iṆ`
  (rule 8.3.57) needs the far reading: Pāṇini's own usage requires **both**.
- **`mixed_reading_covers`** — allowing each pratyāhāra to choose its reading
  rule by rule (which is what the grammar in fact does), **all 43 attested
  classes are served**.

Together: **no uniform convention for the doubled Ṇ is consistent with the
Aṣṭādhyāyī's usage; the re-use is only resolvable rule-by-rule.** That is the
formal content of Patañjali's complaint — the economy of one saved marker
letter is purchased with context-dependence in the metalanguage.

All `sorry`-free; axioms `propext`, `Classical.choice`, `Quot.sound`.

**Start here:** open [`README.html`](README.html) in a browser — an interactive
explainer for readers with no Sanskrit background where you can *read the
ambiguous pratyāhāras both ways yourself*, and watch each uniform convention
break the grammar.

## Layout

| File | Role |
|---|---|
| `panini/Panini/Ambiguity.lean` | **the result**: the recited (single-Ṇ) model, the far-reading semantics, and the five theorems above |
| `panini/Panini/Basic.lean`, `Pratyahara.lean` | the model: sounds, markers, pratyāhāras, strict semantics |
| `panini/Panini/Interval.lean`, `Markers.lean`, `Optimality.lean`, `Necessity.lean` | infrastructure (the 43 attested classes live in `Optimality.lean`; those files' own theorems are showcased on the `result/shivasutra-optimality` and `result/marker-irredundancy` branches) |

## Build

```sh
cd panini
lake exe cache get   # download prebuilt Mathlib
lake build
```
