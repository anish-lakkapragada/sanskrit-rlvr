# No-dhatu modification pilot 01

**200 modification questions and 200 matched ordinary 4D controls are prepared for parent review.** They use 200 distinct development families, all ten classes and no model-error selection. No paid request, training or final qualification is performed by this worker.

The modification prompt exposes only one Devanagari source word, its four coordinates and four target coordinates. It explicitly requests ordinary classical conjugation without adding a prefix or Sanadi suffix. The renderer reads only `source_form_devanagari`, `source_morphology` and `target_morphology`; dictionary identity, citation, class, meaning and gold are private metadata. The answer format is one accepted form inside `<answer>...</answer>`.

Only **lakara changes**. Prayoga is Kartari throughout; person and number remain fixed within each pair. Source tenses are Lat/Lit/Lan/Lun, exactly 50 each. All ten target tenses have 20 questions each, so target Lun is 10%. Source and target tense differ, and the source word is absent from the entire target gold union. Nine person/number combinations have 23,23,22,22,22,22,22,22,22 questions.

The exact 4D control for each modification asks for the same target coordinates from the private dictionary entry, using `cartesian-4d-v3-sanskrit`. Both arms have byte-identical full gold lists. No separate pada is supplied or imposed: the target accepts the same full pada/variant union as the 4D control. The comparison therefore changes how the underlying dictionary entry is presented, not the target answer set.

## Ambiguity and scope

The inverse audit covers four source tenses × all nine person/number combinations, over every current source-eligible dictionary entry in **all** family splits. It indexes every canonical engine source variant. It also derives a shadow index over all 2,229 dictionary entries using the classical engine, before scope exclusions. A source key is blocked if it collides with any excluded entry or uncertified source context. This prevents source-policy filtering from manufacturing uniqueness.

Every retained source word plus source coordinates maps to exactly one citation-plus-gana family. Multiple dictionary codes within that family are permitted only when **all** analyses yield exactly the same full target union. Cross-family/cross-split ambiguity is excluded. The validator recomputes the full eligible and shadow profile for each used coordinate combination, verifies hashes, rederives every candidate target and checks the master split. All selected families are development; RL/test entries are used only for input-collision screening.

Current policy21 applies to both source and target. Additional prospective holds cover unresolved04.0137/10.0023 and canonical vowel+r+C spellings pending the accepted-spelling review. This is an input-defined hold applied to both arms. The old 5D source review is preserved unfinished and contributes no model-error selection.

**Uniqueness is bounded to this audited dictionary and its generated canonical source forms, not all Sanskrit.** Dictionary omissions, contextual meanings, alternative unimplemented spellings and unlisted derivations are outside that proof. The task is ordinary dictionary conjugation; no prefix or new Sanadi operation is allowed. The frozen `inventory_family_counts` audit field counts entries by split; [the additive clarification](inventory-count-clarification.json) supplies distinct-family counts.

## Selection and checks

A fixed seed assigns a PN pair per family. Candidate target tuples must be fresh against all immutable task/component inputs from both campaign ledgers; no result files are read. Class quotas give at least two entries per available class, then apportion the remainder by eligible family supply. A fixed source-target joint table and balanced shuffled PN slots are allocated using integral min-cost flow with input-hash costs. Exactly one question per family is selected.

Class counts are Bhvadi99, Curadi44, Tudadi17, Divadi11, Kryadi10, Adadi7, Svadi4, Rudhadi4, Juhotyadi2 and Tanadi2. These are diversity-aware supply quotas, not equal-class sampling. The 623 eligible candidate families reflect this PN/novelty design, not total possible supply.

All 200 modifications regenerate and pass collision validation. All 200 controls pass the shared Cartesian validator. Six offline checks pass, including real excluded-source collisions, split/gold tampering, public-only renderer invariance, exact distributions and every accepted target variant. [Receipt](test-receipt.json), [manifest](manifest.json), [collision audit](collision-audit.json), [novelty audit](novelty-audit.json).

The frozen [analysis declaration](analysis-predeclaration.json) requires both complete arms before paired analysis. Report all-request/usable accuracy, missing bounds, completion, paired transitions/differences, family uncertainty and source/target/class strata. This 200-family development diagnostic is neither a precision-qualified final benchmark nor evidence that difficulty is below90% until evaluated.

Core files: `tasks.json`, `controls.json`, `prompts.jsonl`, `plan.json`; renderer `misc/vp_modification_prompt_v1.py`; validator `misc/vp_modification_task_v1.py`; generator `misc/vp_modification_prepare_01.py`. Parent owns runner dispatch, independent review and submission. Helpers and frozen core files must not change after submission.
