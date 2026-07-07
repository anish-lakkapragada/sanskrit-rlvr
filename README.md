# The Śivasūtra optimality theorem (Petersen 2004/2008), in Lean 4

**Result.** Pāṇini's Śivasūtras — the 14 lines that order the sounds of Sanskrit
so his grammar can name any needed sound-class as a two-letter contiguous
abbreviation (*pratyāhāra*) — are an **optimal** arrangement: fewest duplicated
sounds first, fewest markers second (Petersen, *A Mathematical Analysis of
Pāṇini's Śivasūtras*, JoLLI 2004; dissertation, Düsseldorf 2008). This is the
first mechanization of any part of Pāṇini's grammar in a theorem prover.

**What is proved** (all `sorry`-free; axioms `propext`, `Classical.choice`,
`Quot.sound`):

| Theorem | Statement |
|---|---|
| `shivasutra_isSAlphabet(T)` | Pāṇini's list encodes **all 43 attested pratyāhāras** (each replayed by `decide`), laxly and strictly |
| `numMarkers_shivasutras` … | his cost: 14 markers + 1 duplication (only `h`) = 15 |
| `one_le_duplications_for_panini` | **duplication is forced**: any rival must repeat a sound (convexity obstruction on the triple `h, v, l` via the attested classes `aṬ`, `yaṆ`, `raL`) |
| `shivasutra_duplication_optimal(_strict)` | **Petersen's criterion 1, complete**: no rival duplicates less — hypothesis-free |
| `eleven_le_numMarkers` | every strict rival carries **≥ 11 markers** (right-edge rigidity + an 11-antichain of attested classes) |
| `twelve_le_cost` | every strict rival costs **≥ 12**, vs. Pāṇini's 15 |
| `lax_marker_bound_false` | a machine-checked **refutation**: under the naive marker-optional semantics, deleting the final `L` gives a valid 13-marker rival — so that semantics is the wrong arena, and the strict one (`EncodesT`) is used throughout |
| `shivasutra_cost_optimal_of_marker_bound_strict` | full cost-optimality, conditional on the one remaining unmechanized step: the tight bound `14 ≤ numMarkers` (Petersen's Satz 6.1.1, diagnosed at the end of `Optimality.lean`) |

**Start here:** open [`README.html`](README.html) in a browser — an interactive
explainer for readers with no Sanskrit background, including a clickable
pratyāhāra explorer over the real Śivasūtras.

## Layout

| File | Contents |
|---|---|
| `panini/Panini/Basic.lean` | `Sound` (42 varṇas), `Marker`, the Śivasūtras, `pratyahara` |
| `panini/Panini/Pratyahara.lean` | denotation checks; lax (`Encodes`) and strict (`EncodesT`) semantics |
| `panini/Panini/Interval.lean` | encoding = interval; positional independence forces duplication |
| `panini/Panini/Markers.lean` | markers are right edges; antichains force markers |
| `panini/Panini/Optimality.lean` | the 43 attested classes; the optimality, refutation, and strict theorems |

## Build

```sh
cd panini
lake exe cache get   # download prebuilt Mathlib
lake build
```
