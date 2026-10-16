# Lexical source files

These are lexical source snapshots and explicitly labeled review exports for
task generators. Checksums, sizes, revisions, counts, and transformations
are in [sources.json](sources.json). Raw upstream files remain unchanged.

**Selected nominal source (2026-10-10): MWlexnorm is the sole lexical source
for the subanta and taddhitanta datasets.** The other downloaded nominal
sources are retained as review artifacts and are not inputs to those datasets.
Use [mw-lexnorm/nominal-entries.csv](mw-lexnorm/nominal-entries.csv), resolving its
grammatical metadata into explicit VP inputs before generation.
The [subanta generator](../subanta/README.md) now implements this adapter and
records per-row coverage and exclusion reasons in its export.

## Shared stem list: `shared-nominal-stems.json`

The new [shared stem list](shared-nominal-stems.json) resolves MWlexnorm into
explicit stem–gender pairs, with all original source analyses retained.
For example, `guru, m:f#vI:n` supplies masculine `guru`, feminine `gurvI`,
and neuter `guru`. Identical pairs merge across dictionary entries.

This is the common input-preparation step for both nominal generators.
The list now excludes rows that the current VP basic/nyap adapter cannot
represent, including source-marked compounds and unsupported stem classes.
Every retained row passes the reviewed representation rules and an actual VP
constructor check. Removed rows and their original metadata are preserved in
[the VP exclusion log](shared-nominal-stems.vp-exclusions.json).
Task-specific derivations and affix eligibility remain separate. The existing
task datasets still use their original adapters.

The [row audit](shared-nominal-stems.audit.json) accounts for every CSV row;
the [manifest](shared-nominal-stems.manifest.json) records counts, policies,
and checksums. See the [generator documentation](../nominal_stems/README.md)
for the schema, supported normalization rules, and regeneration command.

## Verbal roots: `vidyut_dhatupatha_5.tsv`

Copied byte-for-byte from the previous branch's
`data/finetune/task-data/vidyut_dhatupatha_5.tsv` at
project commit `e94499639cf58a6518aa99139fab6818e93346d1`. It also matches the
snapshot under `benchmarks/parallel-search-20261006/five_d/release64k-prototype-01/apply-check/`.
The [upstream Dhātupāṭha](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/data/dhatupatha.tsv)
may differ from this project snapshot.

The columns are `code`, `dhatu`, and `artha`. There are 2,259 data rows, including
30 `-` placeholders, leaving 2,229 usable roots. Sanskrit is encoded in SLP1.
Use the official Dhātupāṭha loader to retain citation markers and subclass
metadata. Derive class from the entry code; do not guess it from root spelling.

## Nominal stems: `nominal-stems.csv`

Source: the Monier-Williams data maintained in
[`sanskrit/data`](https://github.com/sanskrit/data/tree/e9a6e464dcac2e1f65e8ec97ce312e480741d2b7/monier-williams),
commit `e9a6e464dcac2e1f65e8ec97ce312e480741d2b7`.
[Download the exact CSV](https://raw.githubusercontent.com/sanskrit/data/e9a6e464dcac2e1f65e8ec97ce312e480741d2b7/monier-williams/nominal-stems.csv).
Its upstream README identifies a dictionary download dated 2015-04-08 from the
[Cologne Digital Sanskrit Dictionaries](https://www.sanskrit-lexicon.uni-koeln.de/).
The supplied data license is preserved in
[nominal-stems.LICENSE](nominal-stems.LICENSE): CC BY-NC-SA 3.0. Preserve that
attribution and license in derived dataset documentation.

The CSV contains 186,119 records and 170,576 distinct stem spellings:

| Column | Meaning |
| --- | --- |
| `stem` | Nominal stem in source SLP1 notation, including nouns and adjectives |
| `stem_genders` | Allowed gender letters: `m` masculine, `f` feminine, `n` neuter; combinations such as `mfn` |

This is the nominal stem document discussed previously. It supplies lexical
inputs, not precomputed inflections, definitions, or unique dictionary IDs.
Keep this raw file unchanged. A generator must separately resolve duplicates,
preserve source row identity, adapt unsupported spellings, map genders, and
select the appropriate VP stem constructor. A gender string does not authorize
every possible inflection or suffix derivation.

## Alternative nominal sources reviewed on 2026-10-10

**MWlexnorm provides the most useful additional lexical information for our
feminine-stem question.** Sanskrit Heritage provides a smaller independent set
of inflected forms against which we can check interpretations. The
learnsanskrit.org tables provide supporting paradigms and irregular examples.
These sources have different units of observation; their row counts cannot be
added together as a count of usable stems.

| Local file | Data rows | What the rows contain |
| --- | ---: | --- |
| [MWlexnorm nominal entries](mw-lexnorm/nominal-entries.csv) | 197,652 | Dictionary ID, headword, compound boundaries, normalized grammatical information including feminine hints |
| [Heritage nominal entries](sanskrit-heritage/nominal-entries.csv) | 20,762 | One lexical entry and observed gender, with actual nominative/accusative singular forms and available case/number slots |
| [Irregular nouns](learnsanskrit.org/nouns-irregular-inflected.csv) | 943 | Inflected examples covering 38 distinct source stems |
| [Irregular adjectives/numerals](learnsanskrit.org/adjectives-irregular-inflected.csv) | 163 | Inflected examples covering 16 distinct source stems |
| [Nominal inflection endings](learnsanskrit.org/nominal-endings-inflected.csv) | 1,405 | Ending templates for 24 distinct stem-type labels, rather than a word inventory |
| [Nominal compound endings](learnsanskrit.org/nominal-endings-compounded.csv) | 24 | Compound-ending templates |
| [Pronoun inflections](learnsanskrit.org/pronouns-inflected.csv) | 519 | Inflected examples covering 9 distinct source stems |
| [Pronoun compound forms](learnsanskrit.org/pronouns-compounded.csv) | 11 | Compound forms covering 9 distinct source stems |
| [Other sarvanama inflections](learnsanskrit.org/sarvanamas-inflected.csv) | 1,992 | Inflected examples covering 29 distinct source stems |

The seven learnsanskrit.org morphology CSVs are byte-for-byte downloads from
the same pinned `sanskrit/data` revision as the original nominal CSV. Its
[enums](learnsanskrit.org/enums.csv), [source documentation](learnsanskrit.org/README.md),
and [CC0 license](learnsanskrit.org/LICENSE) are also included. These are
hand-constructed tables, mainly based on Kale's grammar, and need checking
before becoming benchmark gold. For example, the irregular-adjective file
labels `azwan -> azwaBis` as case 2, while its own case convention makes
case 2 accusative; this is a source inconsistency to review, not to silently fix.

### MWlexnorm: dictionary metadata with feminine hints

Source: [funderburkjim/MWlexnorm](https://github.com/funderburkjim/MWlexnorm/tree/34e51125583b1f5026d44e6ef1e44d2a88b73670),
revision `34e51125583b1f5026d44e6ef1e44d2a88b73670`.
The unmodified [lexnorm-all2.txt](mw-lexnorm/lexnorm-all2.txt) is tab-separated.
Our CSV changes the delimiter and adds a header and original source-line number;
it preserves all four original fields and every record.

There are **177,606 distinct headword spellings**, with **8,134 records containing
an explicit `f#` feminine hint**. Exact headword matching finds 170,365 of the
original CSV's 170,576 spellings. The sources differ in scope and revision, so
the 211 unmatched original spellings should not be silently discarded.

Concrete examples, checked against the downloaded Heritage forms:

| Headword | Original CSV | MWlexnorm | Heritage feminine nominative singular |
| --- | --- | --- | --- |
| `deva` | `mfn` | `m:f#I:n` | `devI` (देवी) |
| `guru` | `mfn` | `m:f#vI:n` | `gurvI` (गुर्वी) |
| `alpa` | `mfn` | `m:f#A:n` | `alpA` (अल्पा) |
| `sundara` | `mfn` | `m:f#I:n` | `sundarI` (सुन्दरी) |

The original CSV also has noun rows for some of these spellings; the table
compares their adjective entries. `f#I` and `f#vI` are source hints, not ready
VP arguments or strings to append blindly. The [upstream explanation](mw-lexnorm/README.upstream.md)
specifically discusses `guru -> gurvI`. Resolving these hints still requires
reviewed stem-construction rules.

`mw_id` preserves distinct dictionary entries that the old two-column export
could collapse. `compound_headword` preserves compound boundaries. `lexnorm`
also retains special instructions such as `LEXID` and `INFLECTID`; the file
includes indeclinables and special classes, so 197,652 is not a count of ordinary
declinable nominal stems. It does not include definitions. This is another
extraction of Monier-Williams, not an independent dictionary witness.

MWlexnorm has no standalone license file at this revision. Its documentation
identifies the MW digitization as the source; the existing
[MW data license](nominal-stems.LICENSE) remains available. See the manifest's
provenance note rather than assuming an additional license grant.

### Sanskrit Heritage: actual forms with grammatical labels

The direct Heritage XML endpoint was unavailable during this review. We retained
an unmodified [SL_nouns.xml](sanskrit-heritage/SL_nouns.xml) snapshot from
[buda-base/sanskrit-stemming-data](https://github.com/buda-base/sanskrit-stemming-data/blob/aeddea423402739d48c3751418bb1751c30ac673/input/Heritage_XML/SL_nouns.xml),
revision `aeddea423402739d48c3751418bb1751c30ac673`. Its header identifies
Gérard Huet and the source date **2017-06-13**; this is not a current live export.
The original resource's [LGPLLR license](sanskrit-heritage/LICENSE) is preserved
from `sanskrit/data`, with that separate provenance recorded in the manifest.

The XML contains **234,560 form records and 447,941 grammatical analyses**.
The CSV is a local summary: **20,762 entry–gender pairs**, covering **10,974
source entries including homonym numbers**, or **10,867 distinct headword
spellings**. Of those spellings, 9,733 exactly match the original nominal CSV.

- `source_stem` retains the original lexical label, including `#1`, `#2`, etc.
  `headword` and `homonym` split those components without merging entries.
- `gender` is observed in the XML, not inferred from the spelling. It has
  8,261 `m`, 6,265 `f`, 6,226 `n`, and 10 `dei` rows. `dei` is the source's
  deictic category, not a fourth grammatical gender to send to VP.
- Singular-form columns contain JSON arrays, preserving alternatives. They
  are inflected forms, not automatically usable stems. An empty array means
  that singular form is absent from this snapshot; 34 rows lack a nominative
  singular.
- `observed_case_number_slots` is a JSON array such as `["1s", "2s"]`;
  case numbers follow the usual 1–8 convention, and `s/d/p` mean
  singular/dual/plural. **This source file contains no vocatives** and some
  entries have incomplete paradigms. It cannot supply every 24-slot paradigm.
- `source_first_record` is the first supporting `<f>` record, counted from 1;
  all supporting forms remain in the raw XML. Final `s`/`r` conventions also
  require explicit normalization before comparison with VP output.

The CSV was created on 2026-10-10 by the local exporter described below, from
Gérard Huet's resource (copyright 1994–2017), and retains its LGPLLR license.
No morphology engine was used to invent missing forms or feminine stems.

### Review and regeneration

The two review CSVs are generated with the standard-library-only exporter:

```sh
python3 data/engine/nominal_sources/export.py
python3 data/engine/nominal_sources/export.py --check
```

The exporter verifies source hashes, preserves MW IDs and Heritage homonyms,
and records source and generator hashes in the manifest. `--check` verifies
byte-identical exports and manifest metadata without writing files. Every raw
download has a commit-pinned URL in `sources.json`.

The subanta adapter interprets MWlexnorm's stem hints and validates its VP
requests. Both nominal generators use MWlexnorm alone. The full taddhitanta
export attempts all VP suffixes on renderable headwords and resolved stems,
without semantic filtering. For taddhitantas, MWlexnorm improves base
identification but does not supply all the meanings and suffix-specific
conditions needed to license a derivation.

See [TRAINING.md](../../../TRAINING.md) for generation and split requirements and
the [beginner's guide](https://github.com/anish-lakkapragada/sanskrit-rlvr/blob/e94499639cf58a6518aa99139fab6818e93346d1/benchmarks/a-b-c/VP-Other-Tasks-Explained.html) for
the grammar and API links.
