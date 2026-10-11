# serving/ — interactive model comparison app

Query any campaign model (base, the four 20M mixture arms, GRPO-r3) side by side
on your own prompts, served from a 1x A100 (bf16, the exact eval stack — not a
quantized approximation).

## Run

```bash
./serving/serve.sh          # launch (or reuse) the box, start servers, open UI
./serving/serve.sh stop     # terminate the box (verify NONE)
```

First run: ~30-40 min to interactive (box boot + env + Qwen download + two
engine loads). While the box stays up, re-running serve.sh reconnects in
seconds. The box costs ~$2/h and self-terminates after 6h as a backstop —
`stop` it when you're done.

UI: http://localhost:7860 once serve.sh says READY.

## What it serves

| model key | what it is | upstream |
|---|---|---|
| base | Qwen/Qwen3-4B (bf16) | :8000 |
| tb20m-samayik100 / 67 / 50 / 33 | mixture arms (LoRA on base) | :8000 |
| grpo-r3 | GRPO-r3 final (LoRA on merged 20M-67%) | :8001 |

Every request pins `enable_thinking=False` (chat_template_kwargs) so you are
probing the models under the same conditioning as training and every table in
misc/figures/. Template dropdown wraps your input in the exact eval prompts
(v0 translation, elicitation scaffold/placebo, drill costume) or sends it raw.

## Averaging (adapter composition)

The "enable averaging (½·adapter)" checkbox turns each panel into two stacked
rows: the original model on top, the 50/50 weight-average with its serving
base below. Implementation: every adapter has a `-avg` twin (hardlinked
weights, `lora_alpha` halved), so vLLM applies exactly `0.5·ΔW` — no extra
VRAM, no new checkpoints. Built + registered by box_setup.sh; on an already
running box they can be hot-loaded via `/v1/load_lora_adapter`.

Caveat: the SFT arms average toward stock Qwen3-4B, but `grpo-r3-avg`
averages toward its serving base `merged-s67` (its SFT parent) — vLLM can't
stack two LoRAs, so a true grpo-vs-stock average would need a separately
merged checkpoint. Empirically ½·SFT-adapter restores general chat (e.g.
"Name three Indian foods." answers instead of emitting EOT) while keeping
easy translations intact; grpo-r3-avg stays chat-collapsed because its
anchor is itself collapsed.
