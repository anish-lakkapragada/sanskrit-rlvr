# Pāṇini's Śivasūtras in Lean 4

A formalization of Pāṇini's **Śivasūtras** — the 14 lines that order every sound of
Sanskrit and let his grammar name natural classes ("any vowel", "any voiced stop")
as contiguous `pratyāhāra` abbreviations — and of **Petersen's optimality theorem**
about them (*A Mathematical Analysis of Pāṇini's Śivasūtras*, JoLLI 2004, Prop. 4.2).

This follows the build path laid out in [`../thinking/`](../thinking/): the first
mechanized result about any part of Pāṇini's grammar in a theorem prover.

## Layout

| File | Rung | Contents |
|------|------|----------|
| [`Panini/Basic.lean`](Panini/Basic.lean) | — | The model: `Sound` (42 varṇas), `Marker`, the 14 `shivasutras`, and the `pratyahara` interval function. |
| [`Panini/Pratyahara.lean`](Panini/Pratyahara.lean) | ① | The abbreviations denote what the tradition says: `aC = vowels`, `haL = consonants`, `aL = univ`, … — each closed by `decide`. Defines `Encodes` / `IsSAlphabet`. |
| [`Panini/Interval.lean`](Panini/Interval.lean) | ② (Moves 1–2) | All `sorry`-free: **Move 1** — a pratyāhāra is a contiguous infix of the sound sequence (`Encodes.exists_infix`); **Move 2** — three *positionally independent* sounds (Petersen's `K⁵`-triple shape, arbitrary-size witnessing classes) force a duplicated sound, proved by elementary convexity/betweenness instead of her graph-planarity argument (`one_le_duplications_of_independent_triple`). Also holds `cost` / `numMarkers` / `duplications`. |
| [`Panini/Markers.lean`](Panini/Markers.lean) | ② (Move 3) | All `sorry`-free: markers are **right edges**. A pratyāhāra interval ends at a definite position (`endPos`); two classes sharing that edge are ⊆-nested (`subset_or_subset_of_endPos_eq`); hence a ⊆-**antichain** of `k` encoded classes forces `k − 1` marker occurrences (`card_le_numMarkers_succ_of_antichain`), counted index-free via marker-headed suffixes (`markerTails`). |
| [`Panini/Optimality.lean`](Panini/Optimality.lean) | ② | Petersen Prop. 4.2 over the **full attested class family** (43 named pratyāhāras of the Aṣṭādhyāyī, each with its sūtra citation), the hypothesis-free duplication-optimality theorem, the antichain-derived marker bound, the lax-semantics refutation, and the strict theorems. |
| [`Panini/Necessity.lean`](Panini/Necessity.lean) | ③ | **No anubandha is redundant**: deleting any one of the 14 markers breaks the well-formed encoding of some attested class (`no_marker_redundant`, one kernel search over all rescue encodings per marker); the duplicated `h` of line 14 is necessary even laxly (`noH2_not_lax`). Kernel-verified pratyāhāra counts refining Petersen fn. 2: **304** well-formed pratyāhāras and **13** singletons under first-occurrence semantics. |
| [`Panini/Pingala.lean`](Panini/Pingala.lean) | ⓪ | Sanskrit prosody: **the mātrā-meters of total weight `n` number `fib (n+1)`** (Virahāṅka c. 700, Hemacandra c. 1150 — the "Fibonacci" numbers five centuries early), proved as a full combinatorial characterization (`mem_patterns`, `nodup_patterns`, `card_matra_patterns`), plus Piṅgala's `2^n` prastāra count for fixed syllable counts. |

## What is proved vs. open

Everything below is **machine-checked and `sorry`-free** (`lake build` is clean; the
key theorems depend only on `propext`, `Classical.choice`, `Quot.sound`).

**Proved (lax semantics — `Encodes`, marker optional):**
- `shivasutra_isSAlphabet` — Pāṇini's ordering encodes **all 43 attested
  pratyāhāras** (the real family, sourced from the standard enumeration and the
  `vidyut-prakriya` engine, each content replayed against the Śivasūtra text by
  `decide`) and lists every sound.
- `numMarkers_shivasutras = 14`, `duplications_shivasutras = 1`,
  `cost_shivasutras = 15`; `h_is_unique_duplicate` — `h` is Pāṇini's only repeat.
- All Rung ① pratyāhāra-denotation lemmas.
- **Move 1** (`Encodes.exists_infix`); **Move 2** in both the abstract pair form and
  the real convexity form (`false_of_independent_triple`,
  `one_le_duplications_of_independent_triple`).
- `one_le_duplications_for_panini` — **any rival S-alphabet must duplicate a
  sound**, witnessed by the attested classes `aṬ`, `yaṆ`, `raL` on Petersen's own
  triple `h, v, l`. Hypothesis-free.
- `shivasutra_duplication_optimal` — **Petersen's optimality criterion (1),
  complete**: her Def. 2.5 is lexicographic (fewest duplications first, then fewest
  markers), and the first component is now a theorem with no hypotheses.
- **Move 3** (`Markers.lean`): right-edge rigidity and the antichain ⇒ markers
  bound.
- `paniniAntichain` — an **11-antichain** of attested pratyāhāras
  (`aṆ₁, uK, eṄ, aiC, yaṆ, ñaM, jhaṢ, jaŚ, chaV, caR, śaL`), hence
  `ten_le_numMarkers` and `eleven_le_cost`.
- `lax_marker_bound_false` / `lax_cost_optimality_false` — **a machine-checked
  refutation**: for the lax reading, the tight 14-marker bound and full
  cost-optimality are *false*. Deleting Pāṇini's final `L` (`shivasutras_noL`)
  leaves a valid 13-marker, cost-14 alphabet, because a `takeWhile`-based
  pratyāhāra silently runs to the end of the list when its marker is absent.
  Attempting to prove the tight bound produced this counterexample instead.

**Proved (strict semantics — `EncodesT`, the it-marker must occur; the
traditional and Petersen-faithful reading):**
- `shivasutra_isSAlphabetT` — Pāṇini's alphabet is a **strict** S-alphabet; his
  final `h L` sūtra is exactly what strictness demands.
- `noL_not_strict` — the counterexample dies under strict semantics: without the
  final `L`, `raL` has no well-formed pratyāhāra. The kernel thus certifies that
  **the 14th Śivasūtra is load-bearing**.
- `shivasutra_duplication_optimal_strict` — duplication-minimality, hypothesis-free.
- `eleven_le_numMarkers` — the antichain bound without the lax `+1` slack: every
  strict rival carries **≥ 11 markers**.
- `twelve_le_cost` — unconditional: every strict rival costs **≥ 12** (vs. 15).
- `shivasutra_cost_optimal_of_marker_bound_strict` — full cost-optimality,
  conditional on the tight strict bound `14 ≤ numMarkers`.

**Proved (irredundancy and counting — `Necessity.lean`):**
- `no_marker_redundant` — **every one of the 14 anubandhas is individually
  load-bearing**: delete any single marker and some attested class loses its
  well-formed pratyāhāra. This is the economy principle (*lāghava*) as a theorem,
  at the Śivasūtra level: the kernel verifies, for each of the 14 truncated
  alphabets, that no rescue encoding exists among all 588 candidate pairs.
- `noH2_not_lax` / `noH2_not_strict` — Pāṇini's one duplicated sound (the second
  `h`) cannot be dropped, even under the lax semantics: `raL` becomes flatly
  unencodable. Together with `noL_not_strict`, the entire apparatus — 14 markers
  plus 1 duplication — is pointwise indispensable.
- `card_wellFormed_pratyaharas = 304`, `card_singleton_pratyaharas = 13` —
  kernel-verified counts, refining Petersen's occurrence-based 305/14 (fn. 2 of
  the 2004 paper): first-occurrence semantics merges her pair (h′, L) into
  (h, L) = `haL`.

**Proved (prosody — `Pingala.lean`):**
- `card_matra_patterns` — the laghu/guru patterns of total duration `n` mātrās
  number exactly `Nat.fib (n + 1)`: the Virahāṅka–Hemacandra ("Fibonacci")
  theorem, proved as a genuine combinatorial statement (sound + complete +
  duplicate-free enumeration, `mem_patterns` / `nodup_patterns`), not just the
  recurrence.
- `card_varna_patterns` — Piṅgala's prastāra count: `2^n` patterns of `n`
  syllables.

**Open (no `sorry` — one honest gap, diagnosed at the end of `Optimality.lean`):**
- The tight strict marker bound `14 ≤ numMarkers`. This is Petersen's
  **Satz 6.1.1** (*Zur Minimalität von Pāṇinis Śivasūtras*, Düsseldorf
  dissertation 2008, pp. 149–152 — the only rigorous source; the 2004 JoLLI paper
  calls the count "obvious"). Her proof: (1) the `h`-free class system needs 13
  markers — via her Chapter-5 theory of *runs through S-graphs* over plane Hasse
  diagrams of the concept lattice (our antichain method reaches 11 of these 13);
  (2) re-adding `h` forces one more marker, because `caR`/`śaR`/`śaL` jointly force
  `h` to *follow* `ś ṣ s` behind a fresh marker — precisely why the list ends
  `… ś ṣ s R h L`. Caveats: her bound is relative to duplication-minimal
  extensions, and her model starts a pratyāhāra at a chosen copy of a sound while
  ours uses the first copy — so the faithful mechanization target is the strict
  hypothesis above (possibly guarded by `duplications ≤ 1`), and mechanizing the
  run machinery is a self-contained project of its own.

Route (a) from the notes ("bound, then decide") is **not** viable: even after a
normal-form cap the candidate space is ~`42!` orderings, far beyond what `decide`
can reduce. The lower bound has to go through the structural argument above.

The optimality *statement* deliberately exposes `paniniClasses` (which classes
Pāṇini is assumed to need — now the attested list, not a sample), the cost
criterion, and the one remaining marker hypothesis explicitly, so the
Staal / Kiparsky / Petersen dispute over *what* "optimal" means stays a checkable
hypothesis rather than prose.

## Build

```sh
lake exe cache get   # download prebuilt Mathlib
lake build
```
