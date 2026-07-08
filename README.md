# How determined is the Śivasūtra ordering? The forced/free map, in Lean 4

**Result.** Pāṇini's Śivasūtras arrange all the sounds of Sanskrit in 14 lines
so that every class his grammar needs is a contiguous stretch (a *pratyāhāra*).
A live scholarly dispute asks *how much of that ordering is actually determined*
by the class system: **Kiparsky** argues economy makes Pāṇini's order essentially
unique; **Staal** and **Cardona** hold that independent phonetic principles must
be doing real work; and the questions are ancient — Kātyāyana and Patañjali
already debated the order of the sounds in *ha ya va ra Ṭ*. This branch settles
the checkable core with a kernel-verified **forced/free map**: for each of the
**29 adjacent transpositions of two sounds within a line**, whether the 43
attested classes survive the swap.

- **11 junctures are FORCED** — `a‑i, i‑u, h‑y, y‑v, v‑r, ñ‑m, m‑ṅ, jh‑bh,
  j‑b, ph‑ch, th‑c`. Each proof exhibits a witness class and an exhaustive
  kernel search over **all 588 candidate (sound, marker) encodings** of the
  swapped alphabet, confirming the class becomes unnameable. In particular the
  `h‑y`, `y‑v`, `v‑r` verdicts fully pin Patañjali's *ha ya va ra* question.
- **18 junctures are FREE** — `ṛ‑ḷ, e‑o, ai‑au, ṅ‑ṇ, ṇ‑n, gh‑ḍh, ḍh‑dh, b‑g,
  g‑ḍ, ḍ‑d, kh‑ph, ch‑ṭh, ṭh‑th, c‑ṭ, ṭ‑t, k‑p, ś‑ṣ, ṣ‑s`. Each proof
  exhibits, for every one of the 43 classes, an explicit surviving pratyāhāra
  of the swapped alphabet (re-spelled where the swap renames one — e.g. after
  swapping `e‑o`, the vowel class `eṄ` survives as "oṄ").

So **the class system determines the within-line order at 11 of 29 junctures
and leaves 18 to phonetics or tradition** — a quantitative middle verdict:
more freedom than Kiparsky's uniqueness suggests (even `e‑o` and `ai‑au` are
pure convention), far less than arbitrary (every attested class boundary is
rigid).

All `sorry`-free; axioms `propext`, `Classical.choice`, `Quot.sound`.

**Start here:** open [`README.html`](README.html) in a browser — an interactive
explainer for readers with no Sanskrit background where you can *perform each
swap yourself* and watch the grammar survive or break, exactly as the kernel
checked it.

## Layout

| File | Role |
|---|---|
| `panini/Panini/Ordering.lean` | **the result**: the 29 swap theorems (11 forced, 18 free) |
| `panini/Panini/Basic.lean`, `Pratyahara.lean` | the model: sounds, markers, pratyāhāras, strict semantics |
| `panini/Panini/Interval.lean`, `Markers.lean`, `Optimality.lean`, `Necessity.lean` | infrastructure (the 43 attested classes live in `Optimality.lean`; those files' own theorems are showcased on the `result/shivasutra-optimality` and `result/marker-irredundancy` branches) |

## Build

```sh
cd panini
lake exe cache get   # download prebuilt Mathlib
lake build
```
