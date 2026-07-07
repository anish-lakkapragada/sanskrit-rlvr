# The Virahāṅka–Hemacandra theorem, in Lean 4

**Result.** In Sanskrit prosody a light syllable (*laghu*) lasts one beat
(*mātrā*) and a heavy syllable (*guru*) two. The number of light/heavy patterns
whose total duration is `n` beats is exactly the Fibonacci number `fib (n + 1)`.

Indian prosodists knew this five centuries before Fibonacci: the recursion is
stated by Virahāṅka (c. 700 CE) and elaborated by Gopāla and Hemacandra
(c. 1150); the underlying enumeration goes back to Piṅgala's *Chandaḥśāstra*
(c. 3rd–2nd century BCE). Fibonacci's *Liber Abaci* is from 1202.

**What is mechanized** (`panini/Panini/Pingala.lean`, all `sorry`-free) is the
genuine combinatorial statement, not just the recurrence:

| Theorem | Statement |
|---|---|
| `patterns n` | Virahāṅka's enumeration of the weight-`n` patterns |
| `mem_patterns` | a pattern is enumerated **iff** its weight is `n` (sound + complete) |
| `nodup_patterns` | no pattern is enumerated twice |
| `length_patterns` / `card_matra_patterns` | **the set of weight-`n` patterns has exactly `Nat.fib (n+1)` elements** |
| `card_varna_patterns` | Piṅgala's *prastāra* count: `2^n` patterns of `n` syllables |

Axioms: `propext`, `Classical.choice`, `Quot.sound` (the characterization
`mem_patterns` needs only `propext`, `Quot.sound`).

**Start here:** open [`README.html`](README.html) in a browser — an interactive
explainer for readers with no Sanskrit (or Lean) background: generate the
patterns, hear them as rhythms, and watch the Fibonacci recursion appear.

## Build

```sh
cd panini
lake exe cache get   # download prebuilt Mathlib
lake build
```
