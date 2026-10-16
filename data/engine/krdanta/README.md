# Kṛdanta generation and prompt rendering

This directory builds [full.json](../../datasets/krdanta/full.json) from the
pinned root TSV using `vidyut==0.4.0`. Its exhaustive grid is all 2,229 roots
and the 14 reviewed suffixes in `common.SUFFIXES`. Full-dataset generation uses
no model calls, random samples, or extra prefix/sanādi combinations.

From the repository root:

```bash
uv run --python 3.11 data/engine/krdanta/generate.py
uv run --python 3.11 data/engine/krdanta/verify.py --rederive
uv run --python 3.11 data/engine/krdanta/test_krdanta.py
uv run --python 3.11 data/engine/krdanta/render.py krdanta:08.0010:kta
```

Existing exports are protected. Use `generate.py --overwrite` to regenerate
in place, or `--output /path/to/new-export` to generate another copy. Pass the
same `--output` to `verify.py`. Rendering accepts `--dataset /path/to/full.json`.
`uv` manages the pinned script dependency without a project environment.

| File | Responsibility |
| --- | --- |
| [common.py](common.py) | Source validation, suffix scope/glosses, engine requests, prompt rendering, prompt-conflict detection |
| [generate.py](generate.py) | Enumerate every scoped request, filter, write `full.json` and `manifest.json` |
| [export_benchmark.py](export_benchmark.py) | Sample 5,000 tasks in proportion to suffix populations, seed 69; retain original rows and all accepted answers |
| [verify.py](verify.py) | Check every record and exclusion; optionally rederive all 31,206 candidate requests |
| [render.py](render.py) | Select a JSON record by ID and print its hydrated prompt without gold answers |
| [test_krdanta.py](test_krdanta.py) | Regression cases for stems, alternatives, prefixes, participle conditions, hidden metadata, citation rendering, and overwrite protection |

Generation uses `Vyakarana.derive(Pratipadika.krdanta(entry.dhatu, Krt))`.
There is no `Pada.Subanta` step. `Data.load_dhatu_entries()` preserves the
entry's subclass and built-in prefixes. The engine is classical, unaccented,
and outside NLP mode. Present participle requests use the Python API's fixed
`Lat`/`Kartari` defaults, which are stored and shown explicitly.

The [official Python API](https://vidyut.readthedocs.io/en/latest/prakriya.html#basic-methods)
explains direct stem derivation. The exact
[0.4.0 source archive](https://files.pythonhosted.org/packages/69/b5/6876b3f807ac38812c6e29eb43738d28a6a21c2aed456486e654997efcdd/vidyut-0.4.0.tar.gz)
was used to check `bindings-python/src/prakriya/args.rs`,
`vidyut-prakriya/src/args/krt.rs`, `vidyut-prakriya/src/ashtadhyayi.rs`, and
`vidyut-prakriya/src/krt/basic.rs`. Its checksum is in `common.py` and the
manifest; generation itself needs no source download.

Nonempty derivations are necessary but not sufficient for inclusion. The
export also enforces the reviewed suffix scope, lossless gold rendering,
visible lexical prefixes and participle defaults, and equal gold sets for
identical rendered questions. Every excluded candidate ID has a reason in
the manifest. Engine exceptions abort the build instead of becoming silently
omitted tasks. The [dataset README](../../datasets/krdanta/README.md) gives
counts, scope, record examples, and the limits of these fairness checks.

Files are built in a temporary directory; the complete array is published
before its manifest. Neither contains timestamps or machine-specific paths.
A verification run with `--rederive` checks retained and excluded candidates
with engine history logging enabled, whereas generation disables it. Prompt
hashes pin both the template and every hydrated prompt in record order.

## Benchmark subset

[export_benchmark.py](export_benchmark.py) samples 5,000 tasks without replacement
from the filtered full dataset, using seed **69**. Each suffix gets its share
of the source population, with integer quotas allocated by largest remainder.
Sampling within a suffix is uniform; the final output order is shuffled.

```bash
python3 data/engine/krdanta/export_benchmark.py
```

The output is [data/benchmark/krdanta/krdanta.json](../../benchmark/krdanta/krdanta.json).
Its companion [manifest](../../benchmark/krdanta/krdanta.manifest.json) records
the allocation, seed, per-suffix counts, hashes, and source row indices. The
export preserves each selected source object and its complete answer sets.
