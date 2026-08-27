"""Self-Distillation Policy Optimization (SDPO), pure form.

Mechanism (one training step):
  1. STUDENT GENERATES: sample n rollouts from the plain v1 prompt (vLLM).
  2. GATE: score rollouts with vp_exact; if every rollout passes, skip the
     step (nothing to teach — the GRPO advantage-collapse case, now free).
  3. TEACHER RE-SCORES: the SAME model does one teacher-forced pass over each
     rollout under prompt + the task's privileged reference block (gold form +
     vidyut-prakriya derivation). No teacher decoding, ever.
  4. LOSS: per-token KL(teacher || student) over completion tokens only,
     block-weighted (thinking vs answer), averaged over kept rollouts.

No GRPO advantage term, no reward in the loss, no reference model, no
importance sampling. See configs/sdpo-upsample-2.yml.
"""
