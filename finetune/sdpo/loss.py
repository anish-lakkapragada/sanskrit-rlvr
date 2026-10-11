"""Per-token KL between the teacher-conditioned and student-conditioned
distributions of the SAME model, over completion tokens only.

Two variants:
  sdpo_kl       full-vocab KL, fp32 in sequence chunks (~chunk x 151k x 4B x 2
                transient).
  sdpo_topk_kl  top-K distillation (paper section 2.2 / 4.2): the student's
                top-K token log-probs plus ONE tail-mass bucket form a (K+1)-bin
                categorical; the teacher is gathered at the same K indices with
                its own tail. KL between the coarsened distributions lower-bounds
                the full KL and captures |y| x (K+1) advantages per sequence.

Model forwards are done by the caller with ``logits_to_keep`` so only
completion-region logits materialize.

CPU self-test:  uv run --with torch python -m finetune.sdpo.loss
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


def _log1mexp(m):
    """log(1 - exp(m)) for m < 0, numerically stable in both regimes.

    m is clamped to <= -1e-7 first: a top-K mass of ~1.0 (near-deterministic
    position) would otherwise send the tail bucket to log(0) = -inf; the clamp
    floors the tail at ~1e-7 probability, whose KL contribution is ~0 either
    way because the matching p-weight is equally tiny."""
    import torch

    m = m.clamp(max=-1e-7)
    # standard split at log(1/2): log1p(-exp(m)) is accurate for very negative
    # m, log(-expm1(m)) for m near 0.
    return torch.where(m < -0.693, torch.log1p(-m.exp()), torch.log(-torch.expm1(m)))


def sdpo_topk_kl(student_logits, teacher_logits, weights, *, direction: str,
                 temperature: float, top_k: int, chunk: int, clamp: float = 0.0):
    """Weighted mean per-token top-K KL (K student-top tokens + tail bucket).

    The K indices are taken under the STUDENT distribution (paper section 4.2:
    "credit assignment over the 100 most likely tokens (under the student)").
    Teacher log-probs are gathered at the same indices, so both (K+1)-bin
    categoricals share the same vocabulary partition and their KL is exact for
    the coarsened distributions. Only [c, K+1] fp32 tensors carry gradient
    state beyond the logsumexp normalizers, vs [c, V] x 2 for the full KL.

    Same signature contract as sdpo_kl; returns (loss, kl_per_token [T])."""
    import torch

    assert student_logits.shape == teacher_logits.shape, \
        (student_logits.shape, teacher_logits.shape)
    T, V = student_logits.shape
    if top_k >= V:                       # degenerate: fall back to full KL
        return sdpo_kl(student_logits, teacher_logits, weights,
                       direction=direction, temperature=temperature,
                       chunk=chunk, clamp=clamp)
    kls = []
    for i in range(0, T, chunk):
        s = student_logits[i:i + chunk].float() / temperature   # [c, V] grad
        with torch.no_grad():
            idx = s.topk(top_k, dim=-1).indices                 # [c, K]
            t = teacher_logits[i:i + chunk].float() / temperature
            t_top = t.gather(-1, idx) - torch.logsumexp(t, dim=-1, keepdim=True)
            t_tail = _log1mexp(torch.logsumexp(t_top, dim=-1))
            t_bins = torch.cat([t_top, t_tail.unsqueeze(-1)], dim=-1)  # [c, K+1]
            del t, t_top, t_tail
        s_top = s.gather(-1, idx) - torch.logsumexp(s, dim=-1, keepdim=True)
        s_tail = _log1mexp(torch.logsumexp(s_top, dim=-1))
        s_bins = torch.cat([s_top, s_tail.unsqueeze(-1)], dim=-1)      # [c, K+1]
        if direction == "forward":       # KL(teacher || student): mass-covering
            kl = (t_bins.exp() * (t_bins - s_bins)).sum(-1)
        else:                            # reverse: KL(student || teacher)
            kl = (s_bins.exp() * (s_bins - t_bins)).sum(-1)
        kls.append(kl)
    kl_t = torch.cat(kls)                                  # [T], grad flows
    if clamp > 0:
        kl_t = kl_t.clamp(max=clamp)
    loss = (kl_t * weights).sum() / weights.sum().clamp(min=1e-8)
    return loss, kl_t.detach()


if __name__ == "__main__":
    import torch

    torch.manual_seed(0)
    T, V, K = 64, 512, 100
    w = torch.ones(T)

    # identical distributions -> zero KL in every variant
    s = torch.randn(T, V, requires_grad=True)
    for fn, kw in ((sdpo_kl, {}), (sdpo_topk_kl, {"top_k": K})):
        loss, kl = fn(s, s.detach(), w, direction="reverse", temperature=1.0,
                      chunk=17, **kw)
        assert loss.item() < 1e-5, (fn.__name__, loss.item())

    # top-K KL lower-bounds the full KL (coarsening) and stays non-negative
    t = (torch.randn(T, V) * 1.5).detach()
    full, _ = sdpo_kl(s, t, w, direction="reverse", temperature=1.0, chunk=17)
    topk, kl_t = sdpo_topk_kl(s, t, w, direction="reverse", temperature=1.0,
                              top_k=K, chunk=17)
    assert kl_t.min() >= -1e-6, kl_t.min()
    assert topk.item() <= full.item() + 1e-5, (topk.item(), full.item())

    # K = V-1 recovers the full KL (tail bucket is the one missing token)
    near, _ = sdpo_topk_kl(s, t, w, direction="reverse", temperature=1.0,
                           top_k=V - 1, chunk=17)
    assert abs(near.item() - full.item()) < 1e-4, (near.item(), full.item())

    # gradient flows to the student and is finite, both directions,
    # including a near-deterministic row (tail mass ~0 -> _log1mexp clamp path)
    for direction in ("forward", "reverse"):
        s2 = torch.randn(T, V, requires_grad=True)
        with torch.no_grad():
            s2[0] += 0.0
        peaked = s2.clone()
        loss, _ = sdpo_topk_kl(peaked * 30.0, t, w, direction=direction,
                               temperature=1.0, top_k=K, chunk=17, clamp=3.0)
        loss.backward()
        assert s2.grad is not None and torch.isfinite(s2.grad).all(), direction

    print("sdpo loss self-test OK: zero-KL, lower-bound, K=V-1 exactness, "
          "finite grads (fwd+rev, peaked rows)")
