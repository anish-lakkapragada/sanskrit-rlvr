VP-Simple v1: a forward-morphology development prototype

The question is deliberately simple:
  Given the dictionary root, class, meaning, tense/mood, voice, person and
  number, produce ONE conjugated Sanskrit form.

The root is supplied. There is no inverse dictionary search, JSON analysis
set, hidden derivational operation, or English-to-taddhita semantic mapping.
Reasoning before the final answer is allowed but never required or rewarded.
One correct <answer>...</answer> block is sufficient. Devanagari, IAST and
SLP1 have equal standing. Every model uses the same answer extraction.

What was built
  train.jsonl:          20,000 new questions, with accepted forms
  train-sft.json:       20,000 prompt/completion records ready for SFT
  dev.jsonl:               400 new questions, with accepted forms
  test.jsonl:            1,000 new questions, with accepted forms
  *-prompts.jsonl:      IDs and prompts only, safe to send to a solver
  reserved-cells.json:  the held-out tense/voice cell for each root family
  manifest.json:       exact scope, hashes, seed, quotas, and limitations

Generation
  Engine: vidyut==0.4.0, using the original checked-in dictionary.
  Scope: all ten classical lakaras; kartari only; all three persons
  and numbers; ordinary dictionary formation with its required metadata.
  No added causative/desiderative/intensive or arbitrary prefix.
  Voice is supplied but FIXED TO ACTIVE (Kartari) in this first version.
  Passive and impersonal constructions are outside its scope. The original
  report flags many impersonal-coordinate concerns; the active-only scope
  also avoids requiring an additional passive/valency review at this stage.
  Tense/mood, person and number vary; this is a subset of the original 4D task.

  Each tense category contributes 2,000 train, 40 dev and 100 test
  questions. Fixed hashes determine ordering. Empty engine derivations are
  skipped. No model responses, rankings or error labels enter selection.

What the split measures
  This is NEW CONJUGATION CELLS FOR THE ORIGINAL TRAINING VOCABULARY.
  It is not an unseen-root benchmark. A family is exact dictionary citation
  plus verb class, not every possible spelling alias across senses/classes.

  For every eligible family, one entire tense/voice cell is reserved for
  test and a different one for dev. Neither reserved cell appears for that
  family in any of the original 6,687 questions. All nine person/number
  combinations in both cells are excluded from the new training data.
  Test and dev each contain at most one question per family.

  All original validation citation+class families are excluded from this
  package, including its training data. The old validation set can therefore
  still serve as a separate, already-inspected unseen-family development
  check. Previously inspected validation is not a fresh final holdout.

  The build verifies that the recorded SFT morphology IDs and GRPO prompt IDs
  are covered by the original task pool used for overlap exclusion. This
  checks the local training data; it cannot certify pretraining contamination
  or other unknown training corpora.

Scoring
  Binary correctness = a single nonempty answer block whose content is an
  accepted form. Extra reasoning outside that block is permitted. Multiple
  answer blocks and lists of alternatives fail. Only Unicode NFC and outer
  whitespace are normalized. There is no 15% thinking/format reward bonus.

  With four trials per question:
    pass@1 = correct responses / all responses
    pass@4 = questions with at least one correct response / all questions

  The scorer requires all four recorded trials. It rejects duplicates,
  missing trials and unresolved API errors instead of silently scoring
  missing infrastructure results as wrong Sanskrit. It reports truncations.

  Response JSONL schema:
    {"task_id":"vps1-...","trial":1,"output_text":"<answer>...</answer>"}
  Optional fields: status (completed/incomplete), truncated (true/false).

  From the repository root:
    .venv/bin/python misc/vp_simple_benchmark.py score \
      --tasks benchmarks/vp-simple-v1/test.jsonl \
      --responses YOUR_RESPONSES.jsonl --out YOUR_SCORES.json

Reproduction
  .venv/bin/python misc/vp_simple_benchmark.py build --out /tmp/vp-simple-copy
  The build refuses to overwrite a frozen manifest. Output data are
  deterministic under the pinned dependencies and source hashes.

How to use this for post-training
  1. First verify that the exact served SFT/GRPO checkpoint reproduces a small
     familiar original-VP control set. The ABC zero scores are not a reliable
     capacity test. Compare the old and new prompt styles on development only.
  2. Run a small morphology-focused SFT experiment on train-sft.json. Keep
     the same prompt and answer format for training and evaluation.
  3. Compare that with continuing GRPO-r3 on these same training questions.
     Choose the starting checkpoint and decoding settings using dev only.
     A GRPO integration must use the stored prompt verbatim and this binary
     correctness function. The old renderer/reward does not automatically
     adopt this protocol. train-sft.json already contains the exact prompts.
  4. Apply exact-answer RL after the model can regularly produce valid
     answers. Track correctness separately from answer formatting and length.
  5. Compare each candidate and frontier baseline on the frozen test prompts,
     with no tools, four trials, explicit generation settings and budgets.
     Report pass@1 and pass@4 at the same k, plus paired uncertainty.

  The initial 20,000 examples are a pilot corpus, not evidence that they are
  enough to win. If expanding the training corpus, preserve every reserved
  cell; do not generate test/dev answers into training. Do not choose test
  membership by looking for questions the frontier model happened to miss.

Status and limits
  This is a concrete, reproducible DEVELOPMENT PROTOTYPE. No training or
  model evaluation has been launched on it. Agreement with VP is the current
  reference; an independent linguistic review of keys is still needed before
  treating it as a certified benchmark. The original report and A/B/C data
  remain unchanged. This package does not establish a model ranking.

  The realistic claim to aim for is: "a 4B specialist produces new requested
  inflections for a known Sanskrit vocabulary more accurately than a general
  model under this declared protocol." It would not establish superiority at
  Sanskrit generally, inverse analysis, or taddhita derivation.
