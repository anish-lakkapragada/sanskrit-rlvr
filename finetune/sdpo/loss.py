"""Per-token KL between the teacher-conditioned and student-conditioned
distributions of the SAME model, over completion tokens only.

Memory notes: full-vocab KL at Qwen3's 151k vocab is computed in fp32 in
sequence chunks (``chunk`` tokens at a time) so the transient never exceeds
~chunk x vocab x 4 bytes x 2. Model forwards are done by the caller with
``logits_to_keep`` so only completion-region logits materialize.
"""


def sdpo_kl(student_logits, teacher_logits, weights, *, direction: str,
            temperature: float, chunk: int, clamp: float = 0.0):
    """Weighted mean per-token KL.

    student_logits: [T, V] with grad. teacher_logits: [T, V] no grad
    (positions aligned on the same T completion tokens).
    weights: [T] float tensor. Returns (loss, kl_per_token detached [T])."""
    import torch
    import torch.nn.functional as F

    assert student_logits.shape == teacher_logits.shape, \
        (student_logits.shape, teacher_logits.shape)
    T = student_logits.shape[0]
    kls = []
    for i in range(0, T, chunk):
        s = student_logits[i:i + chunk].float() / temperature
        t = teacher_logits[i:i + chunk].float() / temperature
        s_logp = F.log_softmax(s, dim=-1)
        t_logp = F.log_softmax(t, dim=-1)
        if direction == "forward":       # KL(teacher || student): mass-covering
            kl = (t_logp.exp() * (t_logp - s_logp)).sum(-1)
        else:                            # reverse: KL(student || teacher)
            kl = (s_logp.exp() * (s_logp - t_logp)).sum(-1)
        kls.append(kl)
    kl_t = torch.cat(kls)                                  # [T], grad flows
    if clamp > 0:
        # Bound per-token contributions so no single (usually structural)
        # token dominates the gradient.
        kl_t = kl_t.clamp(max=clamp)
    loss = (kl_t * weights).sum() / weights.sum().clamp(min=1e-8)
    return loss, kl_t.detach()
