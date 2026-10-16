# Taddhitanta generation and preliminary testing

The exporter now reads **only the filtered shared nominal inventory**:
[shared-nominal-stems.json](../files/shared-nominal-stems.json). It preserves
all 74,193 stem–gender inputs and attempts **all 175 VP affixes** for each:
12,983,775 candidate requests. No raw headwords are added back, and genders
are not merged. MWlexnorm remains the only lexical source.

The current full dataset contains 3,342,776 tasks and uses schema 2. All
12,983,775 candidates passed complete rederivation, with zero engine or
encoding errors. The verifier rejects the earlier schema-1 export. The
prompt samples and distribution report describe the current shared-input grid.

```bash
uv run --python 3.11 data/engine/taddhitanta/test_full.py
uv run --python 3.11 data/engine/nominal_stems/preflight.py
# Full regeneration is a separate, expensive step:
uv run --python 3.11 data/engine/taddhitanta/generate.py --output /path/to/new-export
uv run --python 3.11 data/engine/taddhitanta/verify.py --output /path/to/new-export --rederive
```

The bounded preflight checks 128 shared inputs against all 24 subanta cells
and all 175 taddhita affixes, repeats results with history logging, compares
serial and parallel batching, and runs upstream reference examples. Its
[report](../../datasets/nominal-preflight/report.json) records the exact code,
source, and engine patch. This sample checks adapter behavior; its nonempty
fraction is not an estimate of linguistic correctness.

## Resolved stem and source gender

Subanta still uses the Python VP 0.4.0 constructors for inflection. Taddhitanta
uses the same pinned release through a small Rust bridge with the explicit
[nominal input patch](nominal-input.patch). Cargo/Rust is therefore required
for the full taddhitanta exporter as well as the pilot. Builds stay in the
system temporary cache, use the checked-in Cargo lock, and record source,
patch, bridge, dependency, and patched-engine file hashes.

In VP 0.4.0, `nyap` stores the full stem spelling and feminine tags on a base
term, then appends an empty feminine suffix marker for inflection. The
original taddhita code selects that empty last term as its base. The patch
removes this marker only when the new, explicit nominal-input adapter is
used. It keeps the full spelling and nyap tags, and sets the source gender
on the base term. Subanta and the historical unpatched probe are unaffected.
No suffix rules or word-specific outputs are hardcoded.

The bridge requires source gender. It does **not** set the gender of the
resulting word: masculine `guru + tal` still gives `gurutA`. Gender-sensitive
rules such as 4.1.120–121 now see the input's feminine status, including a
feminine basic stem such as `lakzmI`. The known feminine reference failures
now yield `cUqAvat`, `mAyAvin`, and `samIna`.

A task ID is `taddhitanta:stem:constructor:source_gender:affix`. Records retain
the shared nominal ID and MW IDs. Prompts display the resolved spelling,
source gender, basic/nyap interpretation, and technical affix. They ask for
the derived stem or indeclinable, without case or number endings. Source
gender is carried inside the existing `{base_interpretation}` placeholder;
legacy records without a gender still render their original interpretation.

Meaning remains unrestricted (`artha: null`), and all 175 affixes are
attempted. VP still has two known explicit-meaning reference gaps:
`pfTu/mfdu + aR` with `TasyaBhava` yields no form. These are recorded in the
preflight rather than claimed fixed or relabeled as successful derivations.
The patch does not change VP's meaning rules.

## Export and verification

Nonempty, losslessly renderable results enter `full.json`; all empty or
invalid-encoding coordinates are audited. Engine errors abort publication.
An empty result means this engine request produced no form, not a linguistic
proof that the formation is impossible.

Generation and verification support `--workers 1–16` (default 4), build the
bridge once, process batches of 64 inputs, bound pending results, and preserve
deterministic ordering. Existing exports are protected unless `--overwrite`
is supplied. Files are staged and the completion manifest is published last.

| File | Responsibility |
| --- | --- |
| [common.py](common.py) | Shared inputs, all affixes, worker batches, prompt hydration |
| [adapter.py](adapter.py), [adapter.rs](adapter.rs) | Pinned compatibility build and gender-aware engine requests |
| [generate.py](generate.py) | Complete grid, streamed tasks/audits, publication |
| [export_benchmark.py](export_benchmark.py) | Sample 5,000 tasks in proportion to suffix populations, seed 69; preserve source rows and all accepted answers |
| [verify.py](verify.py) | Provenance, patch and artifact hashes, complete coordinate accounting, optional rederivation |
| [test_full.py](test_full.py) | Feminine references, gender-sensitive rules, prompt fairness, export/reverification, failure protection |

## Benchmark subset

[export_benchmark.py](export_benchmark.py) samples 5,000 distinct tasks from
the filtered full dataset, using seed **69**. Suffix quotas follow their
source proportions, rounded by largest remainder. Sampling within each suffix
is uniform and without replacement; the final output order is shuffled.
This step only reads existing tasks and uses the Python standard library.

```bash
python3 data/engine/taddhitanta/export_benchmark.py
```

The output is
[data/benchmark/taddhitanta/taddhitanta.json](../../benchmark/taddhitanta/taddhitanta.json).
Its companion [manifest](../../benchmark/taddhitanta/taddhitanta.manifest.json)
records all 175 suffix populations and quotas, coverage, seed, hashes, and
source indices. The 5,000 selected tasks cover 51 of the 129 suffixes with
source tasks; 78 nonempty groups round to zero, and 46 suffixes have no source
tasks. No minimum quota is imposed on rare suffixes. Every selected source
object and its complete accepted answer sets are preserved.

## Historical pilot

The historical prompt file `prompts/v2/vp_taddhitanta_pilot.txt` is absent in
this checkout. Consequently its old prompt-rendering test and pilot rerun
cannot currently complete. This is separate from the current exporter;
`test_full.py` and the new preflight do not use that template. The archived
reference results remain available for the new adapter's regression checks.

The preserved `pilot.py` is a **bounded pilot**. It uses MWlexnorm as the
only lexical inventory and the exact engine source shipped in Python
`vidyut==0.4.0`. Read the
[findings](../../datasets/taddhitanta/pilot/README.md) before extending scope.
The pilot command itself creates no `full.json`, Harbor split, or model benchmark.

From the repository root:

```bash
uv run --python 3.11 data/engine/taddhitanta/test_pilot.py
uv run --python 3.11 data/engine/taddhitanta/pilot.py
uv run --python 3.11 data/engine/taddhitanta/pilot.py --check
```

Python 3.11+ and Cargo/Rust are required. `uv` installs the pinned Python
dependency. The script downloads a checksum-pinned VP source archive, builds
a native Rust probe in temporary cache storage outside the repository, and
uses the checked-in Cargo lockfile. The source archive is the same release
used for the Python wheel; it is not the latest Rust crate from crates.io.
Python/Rust agreement is tested empirically on the entire unscoped grid.

`--check` repeats the pilot and requires byte-identical generated files.
`--output PATH` selects another pilot directory. `--sample-size N` is bounded
to 64–256 and must accommodate the fixed anchor and stem-type sample. The
default is 96. Existing pilot files can be regenerated. Full export is provided
separately by `generate.py` above.

## What is tested

| Component | Check |
| --- | --- |
| Input adapter | Reuse MWlexnorm normalization, deduplicate across source genders, retain all MW IDs |
| Broad exploratory grid | 96 bases × all 175 suffixes, with no artha restriction; compare Python and Rust outputs |
| Meaning control | Same bases × 10 suffixes × 6 explicit meanings using Rust `TaddhitantaBuilder::artha` |
| Reference examples | 24 positive/negative checks using forms from pinned upstream integration tests and two incompatible-meaning controls |
| Constructor diagnostics | Compare feminine `nyap` versus `basic` inputs, including explicit-meaning controls for four reference cases |
| Reproducibility | Rederive every Rust request with history logging enabled; check paired Devanagari/SLP1 and artifact hashes |
| Prompt preview | Gold-free hydration from resolved base, grammatical interpretation, technical suffix, and explicit meaning |

The sample includes named regression examples, two hash-ranked entries per
stem type, and deterministic hash fill. It is not a representative sample of
all MWlexnorm, and its nonempty-output fraction is not a quality estimate.

The provisional JSON preview contains `tva` and `tal` in `TasyaBhava`, and
`matup` in `TadAsyaAstiAsmin` on non-nyap bases only. Feminine `nyap + matup`
requests are withheld after a concrete reference failure. Observations from
unsupported or deliberately incompatible requests stay in diagnostic files;
they are not silently promoted to gold task records.

## Files

| File | Responsibility |
| --- | --- |
| [pilot.py](pilot.py) | Sample, build request grids, compare outputs, check references, write diagnostics and provisional tasks |
| [probe.rs](probe.rs) | Small JSON bridge to Rust VP with optional explicit meaning |
| [rust_probe.py](rust_probe.py) | Verify/download source, build with locked dependencies, execute batches |
| [probe.Cargo.lock](probe.Cargo.lock) | Pinned Rust dependency resolution |
| [test_pilot.py](test_pilot.py) | Gender deduplication, bounded sampling, prompt isolation, and known-risk preview exclusions |
| [pilot prompt](../prompts/v2/vp_taddhitanta_pilot.txt) | Provisional template; includes the base interpretation and meaning actually sent to VP |

The source archive omits its workspace root. The build helper therefore
adapts the Cargo manifest to remove development-only workspace/path
dependencies. Grammar `.rs` files remain unchanged. A compiler lint cap is
recorded for old WASM macros on the installed newer native Rust compiler;
this does not modify engine behavior. First-time lockfile maintenance is
available through `rust_probe.py --prepare-lock`; ordinary runs use `--locked`.

Pilot completion and linguistic readiness are separate. The command succeeds
when diagnostics were collected consistently; the report retains failing
reference checks and its original recommendation. The current exporter retains all 175 affixes while using the shared input
inventory and the compatibility fix described above. This is
engine testing, not an LLM evaluation, and it makes no model/API calls.
