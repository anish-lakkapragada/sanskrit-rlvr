# Tiṅanta: 423,324 eligible tasks

The generator considers **601,830 candidates** (2,229 roots × 270 coordinates).
It excludes **178,320** bhāve requests outside third-person singular before
calling VP, then excludes **186** requests whose identical rendered prompts
have conflicting gold sets. The remaining **423,324** tasks have nonempty,
round-trippable answers and no recorded warnings. No engine errors occurred.

| File | Contents |
| --- | --- |
| [full.json](full.json) | All 423,324 retained tasks |
| [excluded_tasks.json](excluded_tasks.json) | All 178,506 excluded IDs and reasons |
| [manifest.json](manifest.json) | Source/engine/code/template hashes, scope, counts, and export hashes |

These are UTF-8 JSON arrays with one record per line for streaming. Prompts are
hydrated separately; `gold_*` values come from VP, not model responses.

```json
{
  "id": "01.0001:Lat:Kartari:Prathama:Eka",
  "dhatu": {
    "code": "01.0001",
    "aupadeshika": "BU",
    "gana": "Bhvadi",
    "artha": "sattAyAm",
    "antargana": null,
    "prefixes": [],
    "sanadi": []
  },
  "morphology": {
    "lakara": "Lat",
    "prayoga": "Kartari",
    "purusha": "Prathama",
    "vacana": "Eka"
  },
  "gold_slp1": ["Bavati"],
  "gold_devanagari": ["भवति"],
  "status": "ok",
  "warnings": []
}
```

SLP1 capitalization and citation markers are significant. Gold forms are
unique and sorted by SLP1, with paired NFC Devanagari. There are **117,719**
tasks with multiple accepted forms; the largest set contains 17 forms.
The renderer includes loader-supplied prefixes for the four entries that have
them. Every retained record has been rederived with VP logging enabled;
every candidate is accounted for by the export or exclusion audit.

The bhāve restriction is enforced by our generator. VP does not supply a
general validity-warning field and can produce forms for incompatible
coordinates. This export applies the documented eligibility checks; it is
not an independent linguistic certification of every engine result.

No train/dev/test split or Harbor packaging has been applied. See the
[generator instructions](../../engine/tinanta/README.md),
[v2 prompt](../../engine/prompts/v2/vp_tinanta.txt), and
[distribution report](../distribution.html).
