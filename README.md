# Pāṇini in Lean 4 — five machine-checked results, rated by controversy

This repository is the first mechanization of any part of Pāṇini's Sanskrit grammar in
a theorem prover. It formalizes the **Śivasūtras** — the 14 lines that order the sounds
of Sanskrit so any needed sound-class can be named by a two-letter *pratyāhāra* — plus
the 43 classes the Aṣṭādhyāyī actually uses, and proves five families of theorems about
them (all `sorry`-free; axioms `propext`, `Classical.choice`, `Quot.sound`; the heavy
combinatorics replayed by the Lean kernel via `decide`).

**Start here:** open [`README.html`](README.html) in a browser — the full illustrated
summary of every result, each with a **controversy rating** and links to the primary
sources. Each result also lives on its own showcase branch with an interactive explainer.

## The five results

| Branch | Result | Controversy |
|---|---|---|
| [`result/pingala-fibonacci`](https://github.com/anish-lakkapragada/sanskrit/tree/result/pingala-fibonacci) | Sanskrit prosody's light/heavy patterns of duration *n* number exactly `fib (n+1)` — the Fibonacci numbers, five centuries before Fibonacci (Virahāṅka c. 700 CE; Hemacandra c. 1150). Proved as a sound, complete, duplicate-free enumeration. | **1/5 — settled.** Math and history undisputed ([Singh 1985](https://doi.org/10.1016/0315-0860(85)90021-7)). |
| [`result/marker-irredundancy`](https://github.com/anish-lakkapragada/sanskrit/tree/result/marker-irredundancy) | No Śivasūtra marker is redundant (delete any of the 14 and an attested class dies — 588-encoding kernel search each), nor is the duplicated `h`. Kernel counts: exactly **304** well-formed pratyāhāras, **13** singletons. | **2/5 — mild.** Confirms the tradition's *lāghava*, but the counts correct [Petersen 2004](https://doi.org/10.1007/s10849-004-2117-7), fn. 2 (305/14, occurrence-counted). |
| [`result/doubled-n-ambiguity`](https://github.com/anish-lakkapragada/sanskrit/tree/result/doubled-n-ambiguity) | Modeling the recitation faithfully (one Ṇ token closing both line 1 and line 6), exactly **3** pratyāhāras are ambiguous; the uniform nearest-Ṇ and farthest-Ṇ conventions each break an attested class; Pāṇini's usage needs **both** readings — Patañjali's "dearth of letters" complaint as a theorem. | **3/5 — interpretive.** The verdict hangs on the single-token model; most formal treatments individuate the two Ṇ's by position, dissolving the ambiguity by fiat ([Cardona 1969](https://www.jstor.org/stable/1005972)). |
| [`result/ordering-forced-free`](https://github.com/anish-lakkapragada/sanskrit/tree/result/ordering-forced-free) | Of the 29 adjacent within-line transpositions, **11 are forced** by the class system (incl. Patañjali's *ha ya va ra* question) and **18 are free** (even *e-o* and *ai-au*) — a quantitative middle verdict in a live dispute. | **4/5 — live dispute.** Takes a position between [Kiparsky's](https://web.stanford.edu/~kiparsky/Papers/siva-t.pdf) uniqueness claim and [Staal](https://www.semanticscholar.org/paper/4cb5106d40d5cea71a8dfd0978c345bba11bfccf)/[Cardona's](https://www.jstor.org/stable/1005972) phonetic-principles view; both camps can contest the framing. |
| [`result/shivasutra-optimality`](https://github.com/anish-lakkapragada/sanskrit/tree/result/shivasutra-optimality) | Petersen's optimality theorem mechanized: duplication optimality **complete and hypothesis-free**; every strict rival has ≥ 11 markers and cost ≥ 12; full cost-optimality conditional on the unmechanized Satz 6.1.1. Plus `lax_marker_bound_false`: under the naive marker-optional semantics, a **13-marker rival beats Pāṇini** — kernel-checked. | **5/5 — against the literature.** The refutation contradicts the natural reading of a claim [Petersen 2004](https://doi.org/10.1007/s10849-004-2117-7) calls "obvious" (proved only in the [2008 dissertation](https://docserv.uni-duesseldorf.de/servlets/DocumentServlet?id=15491), under assumptions); the strict-semantics rescue and the conditional headline are both contestable. |

The scale: **1** settled · **2** corrects a published detail · **3** verdict depends on a
contestable modeling choice · **4** takes sides in an active scholarly controversy ·
**5** machine-checked result against the natural reading of a published claim.

A shared caution: the kernel makes each *theorem* indisputable **given the model**; every
controversy above lives in the gap between Pāṇini's Sanskrit and the Lean formalization
(the 43-class list, strict vs. lax semantics, the single-token Ṇ). Each branch's README
documents its gap.

## Layout (on `main`)

| File | Contents |
|---|---|
| `panini/Panini/Basic.lean` | `Sound` (42 varṇas), `Marker`, the Śivasūtras, `pratyahara` |
| `panini/Panini/Pratyahara.lean` | denotation checks; lax (`Encodes`) and strict (`EncodesT`) semantics |
| `panini/Panini/Interval.lean` | encoding = interval; positional independence forces duplication |
| `panini/Panini/Markers.lean` | markers are right edges; antichains force markers |
| `panini/Panini/Optimality.lean` | the 43 attested classes; optimality, refutation, strict theorems |
| `panini/Panini/Necessity.lean` | marker irredundancy + kernel-verified counts |
| `panini/Panini/Ordering.lean` | the 29 swap theorems (11 forced, 18 free) |
| `panini/Panini/Ambiguity.lean` | the doubled-Ṇ model and its five theorems |
| `panini/Panini/Pingala.lean` | the Virahāṅka–Hemacandra (Fibonacci) theorem |

`formalization/shivasutra-optimality` is the historical development branch of the first
result; the five `result/*` branches are showcases, each with its own interactive
`README.html`.

## Build

```sh
cd panini
lake exe cache get   # download prebuilt Mathlib
lake build           # replays every proof through the Lean kernel
```

## Primary sources

- Wiebke Petersen, ["A Mathematical Analysis of Pāṇini's Śivasūtras"](https://doi.org/10.1007/s10849-004-2117-7), *J. of Logic, Language and Information* 13 (2004) 471–489 ([open PDF](https://user.phil-fak.uni-duesseldorf.de/~petersen/paper/petersen_jolli_proof.pdf))
- Wiebke Petersen, [*Zur Minimalität von Pāṇinis Śivasūtras*](https://docserv.uni-duesseldorf.de/servlets/DocumentServlet?id=15491), dissertation, Düsseldorf 2008 ([open PDF](https://d-nb.info/1007126175/34))
- Paul Kiparsky, ["Economy and the Construction of the Śivasūtras"](https://web.stanford.edu/~kiparsky/Papers/siva-t.pdf), in *Pāṇinian Studies* (Ann Arbor, 1991)
- J. F. Staal, ["A Method of Linguistic Description: The Order of Consonants According to Pāṇini"](https://www.semanticscholar.org/paper/4cb5106d40d5cea71a8dfd0978c345bba11bfccf), *Language* 38.1 (1962) 1–10
- George Cardona, ["Studies in Indian Grammarians I: The Method of Description Reflected in the Śivasūtras"](https://www.jstor.org/stable/1005972), *Trans. Am. Philos. Soc.* 59.1 (1969) 3–48
- Parmanand Singh, ["The So-called Fibonacci Numbers in Ancient and Medieval India"](https://doi.org/10.1016/0315-0860(85)90021-7), *Historia Mathematica* 12 (1985) 229–244 ([open PDF](https://www.cs.umd.edu/~gasarch/BLOGPAPERS/fibfibs.pdf))
