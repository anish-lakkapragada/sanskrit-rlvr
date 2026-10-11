# Frozen-prompt and RL reward readiness review

The current exporter and benchmark exact scorer preserve the task contract. The live training path still needs integration: it reconstructs a legacy prompt, omits the fifth-coordinate recipe, and uses a 15% format bonus. This additive review demonstrates the small replacement pieces in isolated copies. **No training, provider calls, final membership, or pilot08 outcomes were used. All 15 snapshotted live files remain unchanged.**

[Machine-readable review](review.json), [test receipt](receipt.json), [isolated patch](integration.patch), [callsite sketch](integration-callsite.py.txt).

## What the offline demonstration proves

Four existing **development** questions cover ordinary 4D and the three current 5D recipes, with eight accepted Devanagari forms. Selection used current scope, recipe and presence of variants, never model answers. The fixture and source hashes are in `review.json`.

Twelve checks pass. Both the standard text and TRL conversational Dataset paths preserve each frozen prompt. Exported messages match both providers' pure request builders; no clients are created. The actual reward-recorder path is tested without constructing a trainer or model.

The public schema contains the dictionary citation, class and meaning; lakara, prayoga, purusha and vacana; and, for 5D, exactly one recipe ID. The public menu binds each ID to its **exact ordered** operations:

| Recipe ID | Ordered operations |
| --- | --- |
| `causative_of_intensive` | `yaN`, `Ric` |
| `causative_of_intensive_luk` | `yaNluk`, `Ric` |
| `desiderative` | `san` |

Unknown IDs, changed operations and reversed order are rejected. No independent pada, prefix or other coordinate is added. Generic Cartesian task mechanics permit a broader menu, so the final menu must be bound at the release boundary.

`demo-bundle/prompts.jsonl` contains only IDs, public input and prompt/messages. `private/answer-key.jsonl` contains full accepted unions; `private/audit.jsonl` retains traces and provenance. The original combined export is kept under `private/` as the comparison baseline. This is physical/schema separation, not encryption or filesystem access control. Only `messages` are model input; the private gold column is passed to reward code.

## Exact reward and conversational behavior

The proposed `vp_cartesian_exact` uses the same `exact_reward` implementation as the benchmark: exactly one nonempty `<answer>` block, NFC plus outer whitespace normalization, and membership in the full accepted-form union. Correct answer-only and each accepted alternate receive **1**; wrong, missing, empty, unclosed, multiple conflicting/identical answer blocks and two forms inside one answer receive **0**. There is no thinking requirement or bonus.

The current parser accepts outside prose when there is one correct answer block. The prototype preserves that behavior rather than silently tightening the benchmark. Provider refusal/truncation accounting remains separate from this content-only RL reward.

For TRL conversational completions, the adapter accepts exactly one assistant message with string content and no additional fields. Wrong-role, multiple-message, content-block and malformed structures receive 0. The isolated recorder adds `preserve_completion_structure=True`; its legacy default is unchanged. Without that option, the existing recorder concatenates message contents before the reward can inspect their structure.

## Family split enforcement

The master map has 462 RL, 700 development and 1,000 reserved-test dictionary families. Validation reconstructs the actual citation-plus-class family from the dictionary code and checks the master assignment. Relabeling a development or RL identity as test is rejected before gold regeneration. The dedicated training loader accepts only `rl_train`; it rejects this development fixture.

These checks do not create an RL corpus or prove checkpoint cleanliness. The split is by dictionary identity, not etymological relatedness, and legacy analysis inspected all families before the later test reserve. An independent RL-family corpus must still be generated and validated for any training deliverable.

## Minimal proposed integration

The patch contains only isolated additions to the loader and reward recorder, plus the separated-bundle verifier and exact reward module. It preserves all existing loader functions, reward definitions and recorder defaults. `integration-callsite.py.txt` shows the three required hooks: the RL-only frozen loader, registry name `vp_cartesian_exact`, and recorder structure-preservation option. The native HF Dataset and actual recorder are exercised in tests; GRPO itself is never instantiated.

This is **not a complete installed training entry point**. Before training, wire those hooks into an explicit Cartesian configuration, route dry-run and checkpoint Pass@K evaluation through the same frozen prompts and exact reward, and retain `remove_unused_columns=False` so the private gold column reaches the reward. Current `finetune/grpo.py` and `finetune/evals.py` still use the legacy path. Final-test questions must not enter training or checkpoint selection. No user's existing finetune edits were changed.

Final 4D and 5D exports also still need qualified fixed panels and protocol, the approved finite menu, fresh full regeneration, trusted manifest/dependency fingerprints, exact master-split validation, and separate public/restricted assets. No final N or membership is chosen here. Bundle file hashes in this proof are not a substitute for pinning the external release manifest and source/runtime dependencies.

The additive [runtime snapshot](../../runtime-20261007-01/snapshot.json) verifies 4,259 installed package files, including Vidyut, under the current Python runtime; [local verification](runtime-verification.json) passes. It is prospective provenance, not a claim about historical runtime bytes. No packages were changed.

## Reproduction and limits

Run `check.py` using the repository `.venv/bin/python`, with `PYTHONDONTWRITEBYTECODE=1`, offline Hugging Face variables, this directory's `tmp` as `TMPDIR`/`HF_HOME`, and `safety` on `PYTHONPATH`. It uses synthetic response strings only. The guard forbids network, child processes, model-result/ledger reads and external writes; narrow allowances cover `/dev/null`, the loader's dictionary symlink and installed SDK source fingerprinting. Earlier diagnostic attempts are preserved separately.

The fixture certifies these interface checks, not every Sanskrit form, all future datasets, training effectiveness or target accuracy. The full accepted unions come from the current validated engine tasks; this review adds no new grammatical gold claims.
