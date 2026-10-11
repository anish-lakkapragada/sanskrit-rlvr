# VP correction pilot

Generated 9 October 2026. This pilot contains **200 tasks using 200 distinct dictionary dhātus and 200 distinct citation strings** from the existing 4D candidate inventory. There are 20 questions per classical tense/mood, all ten conjugation classes, all 90 active tense × person × number combinations, and one task per dhātu. All use Kartari; this pilot does not cover the other voice choices.

Open `../report.html#/correction`, or open `index.html` directly. A static server whose document root is `benchmarks/` also serves `/correction/`.

## Opus 5.5 pilot results

Evaluated 50 tasks on 9 October 2026: **24/50 (48%) strict full-answer pass**, **50/50 correct first-error positions**, **50/50 correct final words**, and **50/50 valid answer schemas**. All 26 failures concern intermediate trace checkpoints. These include term segmentation, technical markers, and derivation order; the result measures exact VP trace repair and does not establish 26 substantive conjugation failures.

The input-only selection covers 50 distinct dhātus, five tasks per tense, all ten classes, and 17 person / 17 number / 16 tense substitutions. One direct `claude-opus-5-5` request per task used adaptive thinking at xHigh effort and a 65,536-token output ceiling. **Tools were explicitly disabled** (`tools: []`, `tool_choice: {"type": "none"}`); no browser, internet, code execution, or VP access was available to the evaluated model. Each request contained only the saved user prompt. No paid retries, task replacements, or outcome-based stopping occurred.

All 50 requests completed normally, with no refusals, truncations, or API errors. Recorded usage cost **$2.267960**, within the existing $1,000 Anthropic and $2,000 OpenAI lifetime caps. This is a 50-task exploratory pilot; each response contributes two percentage points, and it does not meet a less-than-one-percent uncertainty requirement.

The report has separate diagnostic rates, pass/fail filters, and side-by-side JSON code blocks with accepted-branch selection, the first differing checkpoint, and the raw response. Frozen requests, protocol, receipts, and scored outputs are in `opus-50-20261009/`. The paid run is complete and must not be replayed. Refresh its analysis and rendering without API calls:

```sh
.venv/bin/python benchmarks/correction/analyze_opus.py
.venv/bin/python benchmarks/correction/verify_opus.py
.venv/bin/python benchmarks/correction/build_report.py
```

## Generate, verify, render

Run from the repository root with its existing virtual environment:

```sh
.venv/bin/python benchmarks/correction/generate.py
.venv/bin/python benchmarks/correction/verify.py
.venv/bin/python benchmarks/correction/independent_audit.py
.venv/bin/python benchmarks/correction/build_report.py
```

Generation is pinned to vidyut 0.4.0, explicit grammar settings, source files, a seed, and a prompt template. It makes no model/API requests. `generate.py --output /some/directory` can build another copy without overwriting the saved pilot. The verifier repeats generation and requires identical task and oracle objects.

## What the error means

This first implementation is **single-coordinate substitution**. VP generates a target derivation and a donor derivation for the same dictionary dhātu with exactly one changed tense, person, or number. The donor provides the complete proposed trace, including downstream steps. It is grammatical for the donor coordinates, but incorrect for the requested coordinates. This avoids inventing or loosely simulating later grammatical transformations.

The public prompt does not identify the changed coordinate or the first wrong step. It asks the model to identify that position and return one complete repair. This is an initial correction family, not a general collection of phonological errors. The Opus pilot above measures strict trace repair on 50 of these tasks.

For each donor, the generator compares its entire prefix against every projected target path. The first prefix with no compatible target path identifies the error. At least two prior checkpoints must be valid, and at least two proposed checkpoints must remain from the error onward. The donor's final form must not be any accepted target final form.

## Representation and gold answers

Project every raw VP history into an ordered sequence of nonempty Devanagari term arrays. Omit empty/deleted terms and consecutive identical arrays. Keep technical markers and accent signs. Final words are stored separately. Raw rule identifiers and the mapping from projected checkpoints to raw history positions are retained in `oracle.jsonl`.

Every term must round-trip through the transliterator without losing phonemes. Equivalent ordering of contiguous SLP1 accent/nasal markers is allowed for this audit; the grader normalizes only Unicode NFC. An input is excluded if any target branch cannot be rendered losslessly. Donor coordinates with a lossy branch are also excluded. Previously held lexical entries and the existing prospective VP oracle policy are respected.

Gold contains every distinct complete target continuation sharing the correct observed prefix. Alternatives can have different lengths. A single final form can have multiple intermediate paths, so answers are never deduplicated by final word alone.

The answer schema is:

```json
{
  "first_incorrect_step": 5,
  "corrected_steps": [
    {"step": 5, "terms": ["गम्", "तिप्"]}
  ],
  "final_answer": "गच्छति"
}
```

This abbreviated object illustrates the schema only: a real answer must contain **every** remaining checkpoint. Consult `answers.jsonl` for complete accepted answers.

`scoring.grade(response, accepted_answers)` parses JSON, rejects duplicate keys and malformed schemas, checks consecutive integer step numbers, normalizes Unicode, and matches the entire structured answer. Whitespace between JSON tokens and object-key order do not matter. Term boundaries, term order, vowel length, technical markers, all intermediate states, and the final word do matter. There is no LLM judge.

## Files

| File | Purpose |
|---|---|
| `core.py` | VP generation, projection, prefix checking, gold continuation construction |
| `generate.py` | Seeded diversity selection and reproducible dataset generation |
| `prompt.txt` | Single deterministic public prompt template |
| `scoring.py` | Standard-library-only answer parser and gold-set grader |
| `verify.py` | VP regeneration, completeness, negative grading checks, determinism |
| `tasks.json` | All task metadata, exact prompts, and accepted answers |
| `prompts.jsonl` | Public task IDs and prompts, with no gold/private donor metadata |
| `answers.jsonl` | Task IDs and complete accepted answer sets |
| `oracle.jsonl` | Raw VP target/donor histories and checkpoint provenance |
| `manifest.json` | Coverage, selection policy, version, settings, and file hashes |
| `verification.json` | Mechanical verification result |
| `independent_audit.py`, `independent-audit.json` | Separate implementation checking every target/donor path and gold set |
| `view.template.html`, `build_report.py`, `route.html` | Reusable browser and persistent report navigation |
| `browser_check.cjs`, `browser-check.json` | Checks all displayed prompts/answers, filters, routes, downloads, and responsive layout |
| `run_opus.py` | Frozen one-shot Opus evaluation with shared lifetime budget accounting |
| `analyze_opus.py`, `verify_opus.py` | Offline grading, diagnostics, and independent receipt/score verification |
| `opus-50-20261009/` | Selected tasks, exact API requests, immutable receipts, results, and cost records |
| `previous-artifacts/` | Preserved artifacts from a different earlier prototype; not the current gold set |

## Scope and limitations

The 200 roots are drawn from the 755 dictionary entries in `benchmarks/parallel-search-20261007/four_d-90/candidate-1800-v1/tasks.json`; coordinates can be newly generated. Existing evaluation answers do not affect selection. Classes are balanced as closely as the inventory allows, with smaller classes exhausted first. Equal citation strings are assigned to the smaller available class before selection so all 200 selected citations are distinct. Tense, person, number, and error-coordinate schedules are seeded independently of model results.

These are **VP-relative mechanically verified** answers under the specified trace representation. The engine does not certify every possible Sanskrit analysis or every alternate scholarly derivation order. Existing source holds reduce known problems but are not independent linguistic certification of all new coordinate combinations. This is a development pilot, not an untouched benchmark test split. Its measured strict trace difficulty should not be conflated with conjugation difficulty or generalized beyond the sampled tasks.

The branch exploration mechanism and trace API are documented in the [VP guide](https://vidyut.readthedocs.io/en/latest/prakriya.html) and [PrakriyaStack source](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/core/prakriya_stack.rs).
