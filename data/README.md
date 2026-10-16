# Benchmark data

| Path | Purpose |
| --- | --- |
| [engine/files/](engine/files/README.md) | Pinned Dhātupāṭha and MWlexnorm snapshots, provenance, and shared filtered nominal inputs |
| [engine/prompts/v2/](engine/prompts/v2/) | Four answer-only templates, each requiring one Devanagari `<answer>` block |
| [engine/prompts/v2/samples/samples.html](engine/prompts/v2/samples/samples.html) | Five hydrated prompts and complete accepted answer sets per family |
| [datasets/](datasets/README.md) | All four generated inventories: 5,574,202 eligible tasks |
| [datasets/distribution.html](datasets/distribution.html) | Candidate-space outcomes and exported task counts |
| [benchmark/subanta/subanta.json](benchmark/subanta/subanta.json) | 5,000 unique subanta tasks balanced across 24 case × number cells, seed 69 |
| [benchmark/tinanta/tinanta.json](benchmark/tinanta/tinanta.json) | 5,000 unique tinanta tasks balanced across 190 valid tense/mood × construction × person × number cells, seed 69 |
| [benchmark/krdanta/krdanta.json](benchmark/krdanta/krdanta.json) | 5,000 unique krdanta tasks sampled in proportion to the 14 suffix populations, seed 69 |
| [benchmark/taddhitanta/taddhitanta.json](benchmark/taddhitanta/taddhitanta.json) | 5,000 unique taddhitanta tasks sampled in proportion to suffix populations, covering 51 suffixes, seed 69 |
| [benchmark/pricing.html](benchmark/pricing.html) | Interactive six-model evaluation cost calculator with task sliders and provider budgets |
| [datasets/validity-audit.json](datasets/validity-audit.json) | Eligibility checks and current verification results |
| [datasets/traces-opus-5/](datasets/traces-opus-5/README.md) | Preserved original Opus traces in v1 format |
| [benchmark/answer-only-pilot-20261013/](benchmark/answer-only-pilot-20261013/) | Current 200-request Astra/Opus calibration, safety audit, and immutable receipts |

Each current family has a `full.json` and manifest, with exclusions audited
separately. No training/test split or Harbor export has been made. Future
splits will live at `data/datasets/<family>/{train,dev,test}/<task-id>/`.
Read [TRAINING.md](../TRAINING.md) for the task contract and archived training
implementation.
