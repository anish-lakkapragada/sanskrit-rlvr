# Vidyut Prakriya Bench

Four Sanskrit morphology datasets with **5,574,202 tasks**: tiṅanta, kṛdanta,
subanta, and taddhitānta. Local generators use pinned VP 0.4.0 derivations and
explicit eligibility checks. Each task stores grammatical inputs and all
accepted answers; v2 templates hydrate those inputs into model prompts.

```text
data/
  engine/
    files/          # pinned lexical sources and filtered shared nominal stems
    prompts/v2/     # four templates and hydrated samples with accepted answers
    tinanta/        # finite verb generator, renderer, tests, and verifier
    krdanta/        # verbal-root suffix tasks
    subanta/        # nominal inflection tasks
    taddhitanta/    # nominal suffix tasks
    reports/       # distribution, sample refresh, and token estimates
  datasets/
    tinanta/        # 423,324 tasks
    krdanta/        # 27,470 tasks
    subanta/        # 1,780,632 tasks
    taddhitanta/    # 3,342,776 tasks
    traces-opus-5/  # preserved historical teacher traces
```

Open the [distribution report](data/datasets/distribution.html),
[prompt samples](data/engine/prompts/v2/samples/samples.html), or
[dataset documentation](data/datasets/README.md). All four templates request
a `<thinking>` block followed by an `<answer>` block.

[TRAINING.md](TRAINING.md) describes the planned Harbor packaging and training
rewrite. The old code, configurations, benchmarks, and results are preserved
on [finetune/vidyut-prakriya](https://github.com/anish-lakkapragada/sanskrit-rlvr/tree/finetune/vidyut-prakriya).
