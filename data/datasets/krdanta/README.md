# Kṛdanta: 27,470 answerable tasks

[full.json](full.json) is a UTF-8 JSON array of **27,470 tasks**, generated from
all **2,229 usable Dhātupāṭha entries × 14 reviewed classical suffixes**.
It contains uninflected nominal stems and complete indeclinables. There is no
sampling, train/dev/test split, teacher completion, or embedded prompt.

“Full” means exhaustive within the explicit suffix scope below. It does not
mean every Sanskrit derivation or all 122 suffixes exposed by the engine.

| File | Contents |
| --- | --- |
| [full.json](full.json) | All retained tasks; 7,285,060 bytes |
| [manifest.json](manifest.json) | Source/engine/code/prompt hashes, scope, counts, output hash, and every excluded request ID |
| [example.json](example.json) | Two small examples that exactly match records in `full.json` |

## Scope and fairness

The generator considers **31,206 requests**. It retains every nonempty,
representable engine result in the reviewed scope, except requests whose
rendered prompts are indistinguishable but have different accepted answers.

| Suffix | Requested formation | Retained tasks |
| --- | --- | ---: |
| `kta` | Past participle | 2,229 |
| `ktavatu` | Past active participle | 2,229 |
| `tfc` | Agent noun | 2,227 |
| `Rvul` | Agent noun | 2,229 |
| `tumun` | Infinitive | 2,227 |
| `ktvA` | Absolutive | 2,227 |
| `tavya` | Gerundive | 2,227 |
| `tavyat` | Gerundive | 2,227 |
| `anIyar` | Gerundive | 2,229 |
| `yat` | Gerundive, subject to root restrictions | 752 |
| `Ryat` | Gerundive, subject to root restrictions | 1,615 |
| `lyuw` | Nominal derivative | 2,229 |
| `Satf` | Present active participle, parasmaipada formation | 1,722 |
| `SAnac` | Present active participle, atmanepada formation | 1,101 |

The exact 0.4.0 source distribution was inspected for the suffix rules,
Python constructor, and participle defaults. Rule references and the source
archive's URL and SHA-256 are recorded in the manifest. The 108 other engine
suffixes are explicitly outside this reviewed scope, rather than being
assumed valid for every root. Extending the scope requires reviewing their
context, semantics, and engine support.

The generation excludes:

- **3,724 empty derivations**, including incompatible root/participle-pada
  combinations. They are not questions with blank answers.
- **12 ambiguous requests** across source entries `10.0257` and `10.0367`.
  Their visible root, class, meaning, and suffix match, but hidden subclass
  metadata changes the gold sets. Both members of each conflicting pair are
  excluded instead of grading on information absent from the prompt.
- **0 invalid gold encodings** and **0 engine errors**. An engine exception
  aborts generation before publishing a new export.

All distinct engine alternatives are accepted, not just the first result.
There are 2,387 tasks with multiple answers, with at most six answers per task.
These are engine-backed formal derivations with explicit input-fairness checks;
this is not independent linguistic certification of every output. There are
no claims that every derived word is textually attested. Lexical-family splits
and broader linguistic review remain downstream work before benchmark release.

## JSON contract

Like the previous branch's `data/finetune/task-data/finetune.json` (6,018
records at checkpoint `e94499639cf58a6518aa99139fab6818e93346d1`), each task
has exactly five top-level fields:

```json
{
  "id": "krdanta:08.0010:kta",
  "dhatu": {
    "code": "08.0010",
    "aupadeshika": "qukf\\Y",
    "gana": "Tanadi",
    "artha": "karaRe",
    "antargana": null,
    "prefixes": [],
    "sanadi": []
  },
  "morphology": {"krt": "kta"},
  "gold_slp1": ["kfta"],
  "gold_devanagari": ["कृत"]
}
```

`dhatu` retains the official loader's subclass/prefix metadata. SLP1 case and
citation markers are significant. `gold_slp1` is sorted and deduplicated;
`gold_devanagari` is its paired NFC conversion. The example requests कृत,
not the inflected masculine nominative कृतः. Inflection is a subanta task.

For `Satf` and `SAnac`, morphology is explicitly:

```json
{"krt": "Satf", "lakara": "Lat", "prayoga": "Kartari"}
```

These are the verified engine defaults, not extra independent axes. The
renderer and request builder reject future/passive participle requests and
other unsupported added conditions. The short ID is unique within this fixed
scope; adding variable prefixes, sanādi operations, or other conditions later
requires extending the identity to include those inputs.

## JSON → hydrated prompt

[common.py](../../engine/krdanta/common.py) provides `render_task(record)`.
It hydrates [vp_krdanta.txt](../../engine/prompts/v2/vp_krdanta.txt) using only
`dhatu` and `morphology`. The `id` selects the record; gold fields never enter
the prompt. English glosses come from the explicit suffix/class tables.

- The root citation, class, dictionary meaning, and requested suffix are shown.
  Root citation hiatus fixes from the archived renderer are preserved.
- A prefix line appears only for the four roots with loader-supplied prefixes:
  `02.0012`, `02.0041`, `02.0042`, and `10.0368`. Their 50 retained requests
  include those prefixes in both the prompt and engine input.
- No sanādi line is needed: every source entry has an empty added-sanādi list.
  The loader asserts this; the renderer rejects added operations.
- Present/active lines appear only for the two participle suffixes. Other
  suffixes do not take finite-verb tense/person/number coordinates.
- There is no generic `conditions` placeholder. Any future meaning condition
  must be expressible by the engine and serialized before it can enter a prompt.

Render a final LLM input from its ID:

```bash
uv run --python 3.11 data/engine/krdanta/render.py krdanta:08.0010:kta
```

The template owns response-format instructions; changing it requires
regeneration so the manifest's template and rendered-prompt hashes stay current.
See the [generator README](../../engine/krdanta/README.md) for build and
verification commands. Harbor packaging is not generated by this exporter.
