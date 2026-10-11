# Prospective final output-cap recommendation

Prefer a **common65,536-token ceiling for both references**, subject to the coordinator’s fixed-N and funding approval. It gives both models the same limit, four times the current primary cap and3.18times the largest diagnostic output. It reduces reservation pressure relative128k without choosing a limit to preserve low accuracy. **These were128k runs, not65,536 runs**: observed lengths would all fit, but accuracy, behavior and costs under the proposed ceiling are unmeasured. No final protocol is approved here.

The128k Astra diagnostic completed60/60, versus50/60 at16k. It scored44/60, whereas the old usable-only40/50 hid a difficult omitted subset: the ten recovered questions scored4/10. Six correct answers regressed and ten wrong/missing answers improved; the paired accuracy difference interval is−6.67to+20pp. A cap increase repairs substantial censoring, but this small panel does not precisely establish accuracy or reference ordering. Mean output was9,586tokens,95th percentile17,564, maximum20,577; six outputs exceeded16,384.

Applying candidate04’s exact quotas aggregated to eight recipe×aorist/other×voice cells gives the following OpenAI forecasts. Settled spending is$727.478150, leaving$1,272.521850 before any other allocation.

| Cost model | Mean/question | 4,800 calls | Lifetime total | Model-based95% interval for lifetime mean cost |
|---|---:|---:|---:|---:|
| Direct high-cap standardization | $0.24100 | $1,156.80 | $1,884.27 | $1,786–1,984 |
| Exact-tense16k baseline plus paired cap increment | $0.24061 | $1,154.94 | $1,882.42 | $1,759–2,008 |

Thus4,800 is plausible at observed means, with roughly$116headroom, but not securely funded against all reasonable uncertainty. The diagnostic covers26of42exact target cells;552candidate questions lie in unsampled exact cells. Non-aorist and class transport remain assumptions. Bootstrap intervals cannot discover unseen long-output tails. About1.7% additional tasks near the65,536ceiling—or0.81% near128k—would consume the point headroom. All remaining OpenAI funds are implicitly available in these calculations; any other spending reduces it.

| Common cap | OpenAI maximum/task, including1,500reserved input tokens | Maximum for50 calls | Maximum for500 calls |
|---|---:|---:|---:|
| 65,536 | $1.64590 | $82.295 | $822.95 |
| 128,000 | $3.20750 | $160.375 | $1,603.75 |

Small immutable transport chunks are necessary near the funding limit. At the point forecast, a final50-question chunk fits the65,536reservation, while128k needs fewer than40; actual costs can still prevent completion. Funding failure must leave the fixed evaluation incomplete, without shrinking N after seeing answers. The original1,000-core/extension membership rule still needs coordinator-owned transport implementation and documented reserve reallocation.

Using the actual929-family candidate allocation and highcap coarse-cell moments, at assumed common within-family correlation.20, expected all/usable sandwich SE is **.863pp empirical or.917pp smoothed** with full completion. At correlation.30 it becomes **.950or1.018pp**. A95% completion sensitivity gives all-request.922–.952pp at rho.20 and1.022–1.059pp at rho.30. Cell-moment uncertainty alone reaches about1.00pp at rho.20/full completion. These are conditional scenarios:60unique diagnostic families contain **no within-family pairs**, so highcap covariance remains unidentified. They use the original sandwich estimator; no estimator is chosen to force a pass. Actual iid and family SE must pass for both models.

Opus16k pilot06 usage projects about$109.48for4,800, with one truncation among594current-scope requests. Its128k/65,536behavior is unmeasured; full pilot07 confirmation is also16k. Await both2,400confirmation chunks without partial analysis, then decide the prospective common-cap protocol. Another60-question Opus probe would not certify1pp accuracy equivalence, rare-tail safety or Astra family dependence; I do not recommend it solely to justify the common65,536ceiling.

[Machine-readable cost summary](cap-protocol-assessment-02.cost-summary.json), [full cost/variance scenarios](cap-protocol-assessment-02.json), [preserved initial128k assessment](cap-protocol-assessment-01.json). No partialpilot07 or final answers were read; no provider calls, shared edits or frozen-dependency changes were made.
