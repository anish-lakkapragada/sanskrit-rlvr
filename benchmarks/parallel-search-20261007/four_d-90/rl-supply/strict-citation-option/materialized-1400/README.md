# Materialized 1,400-question RL curriculum

Prepared 2026-10-07 Pacific / 2026-10-08 UTC. This export makes the existing strict-citation training curriculum concrete. It preserves every metadata ID, coordinate tuple, position and block without replacing or reordering any question. No training, model evaluation or provider call was performed.

Use [public-tasks.jsonl](public-tasks.jsonl) as the public training inputs and [canonical-gold.jsonl](canonical-gold.jsonl) as a separate answer-key file. Both contain 1,400 aligned records in curriculum order and join on `id`. Give the learner only the public record's `prompt`; keep the answer union in the reward/evaluation component. `tasks.json` combines inputs, canonical keys and oracle metadata for local inspection and must not be used as the learner's prompt. `public-prompts.json` is a convenient prompt-only export, and `curriculum-metadata.json` is a byte-identical copy of the original ordered metadata.

The prompt is the unchanged exact4D renderer and explicitly says “Sanskrit verbal root.” Its input is a dictionary citation/class/meaning plus lakara, prayoga, purusha and vacana. All questions use Kartari. No prefix, selected pada or added sanadi operation is introduced; intrinsic dictionary grammar still applies.

| Component | Questions | Families | Questions per family |
|---|---:|---:|---:|
| Short-penultimate adanta Curadi, non-aorist | 728 | 9 | 80–81 |
| Other adanta Curadi, aorist | 112 | 15 | 7–8 |
| Other verb classes | 560 | 308 | 1–2 |
| Total | 1,400 | 332 | Maximum 81 |

There are 56 consecutive blocks of 25 questions, each preserving the 13/2/10 composition. The curriculum covers all ten classes and ten tenses. Aorist has 168 questions (12%); other tenses have 136–137. Persons and numbers each have counts 466/467/467. These are the existing input-only sampling decisions, not a new difficulty-based selection.

Every question passed fresh VP regeneration, complete canonical-union hash checks, exact prompt-hash checks, master `rl_train` membership and the current shared/local/source guards. There are 2,518 canonical task/form entries. Every canonical variant is exported; rewards must not accept only the first answer in a multi-answer union. Public JSONL fields contain neither gold nor derivation traces, and removing those fields from combined tasks leaves all rendered prompts unchanged.

Separation from the frozen 1,800-question candidate is zero-overlap by root family, raw citation, rendered citation, family-coordinate key, full public tuple and prompt. Training citations also do not overlap any current master development/test citation. All original strict-citation files and all 44 paid-run dependency hashes remained unchanged. No held-out model responses were read.

The separate [spelling-policy proposal](spelling-policy-proposal/README.md) uses the same previously reviewed finite spelling helper, with no new grammar. It adds 2,721 aliases across 962 tasks while preserving canonical keys. It is **pending independent review and has not been adopted as a reward policy**. Every usable answer outside the canonical and any eventually adopted finite map requires source adjudication before being treated as a linguistic error. Keep unresolved cases explicit and apply source corrections consistently to training and evaluation.

Mechanical regeneration and inherited source controls do not independently certify every form or every licensed spelling. Exact citation separation does not exclude related stems, meanings, alternate marker spellings or pretraining knowledge. The nine-family hard training component remains small; replaying its many coordinates does not create new lexical families. No learned model, improvement over frontier references or generalization result is claimed.

`manifest.json`, `materialization-audit.json` and `verification-receipt.json` record hashes, membership, source checks, export alignment and separation. `materialize.py` refuses to overwrite an existing completed export and reports row blockers without silently substituting questions.
