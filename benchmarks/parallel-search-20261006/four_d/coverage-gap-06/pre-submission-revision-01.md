# Pre-submission revision 01: usable-response variance

The coordinator found that the original usable-response SE used the number of usable families in the finite-sample correction. This revision retains every fixed family unit in the ratio-influence sandwich, including families with no usable response.

For G fixed families, M usable responses and usable accuracy p, the SE is

`sqrt(G / (G - 1) * p * (1 - p) / M)`.

With one question per family, the residual for family g is `y_g - p*c_g`, where c indicates usability and y indicates a usable correct response. Nonusable families have zero residual but remain in G. The previous `sqrt(p*(1-p)/(M-1))` agrees only when all responses are usable. The analyzer also reports the plug-in iid SE separately. Zero usable responses give undefined usable SE; an all-success empirical zero SE is still degenerate, not a precision guarantee.

The original analyzer, tests, declaration, manifest, request, decision and all manifest-linked files are preserved byte-for-byte in [pre-submission-revision-00](pre-submission-revision-00/snapshot-receipt.json). No paid job or results existed before the correction. Question bytes, exact ordered membership, branch descriptors, source controls and the exploratory trigger are unchanged.

Seven synthetic tests pass. The new test has 44 usable responses split 22 correct / 22 wrong plus one truncated and one refused response. It computes the 46-family influence sum directly, verifies the corrected SE and separately verifies iid SE; it rejects equality with the prior complete-case correction. The current declaration, manifest and execution request contain refreshed fingerprints.
