# Finite training spelling-policy proposal

This is an optional, pre-training proposal requiring independent review before adoption. It binds the exact materialized 1,400-question task hash. The generator reuses the unchanged `ending-screen-01/alias_policy.py` helper; it does not change benchmark scoring, source files, canonical keys, prompts or the running evaluation.

The map preserves all 2,518 canonical task/form entries and adds 2,721 aliases across 962 tasks. Thirteen representative controls cover all ten classes and all ten tenses. Every final n/t/d site follows a vowel. At most four independent original positions occur in a form; the same original-position combination rule handles them without recursive expansion or new grammatical conditions.

Fifty-seven tasks have 83 flagged contexts involving existing gemination or consonant clusters outside the finite expansion. These flags describe incomplete alias coverage; they do not establish that the corresponding canonical tasks are invalid.

An independently written regular-expression reconstruction matched all 1,400 maps. The scorer accepted all 5,239 canonical/alias task forms, routed 1,400 unlisted mutations to review, rejected unknown IDs and cross-task answers, and did not normalize 61 final-n retroflex mutations or 188 triple-final-stop mutations into accepted forms. These are software boundary checks, not independent proof that every invented negative control is grammatically impossible.

Unknown usable answers must receive actual source adjudication before receiving a final linguistic-error label. Do not turn `alias_aware_correct = false` into an automatic zero reward for an otherwise unreviewed spelling. Preserve canonical-only, finite-alias and adjudicated decisions separately, and apply supported corrections across every affected task/model. No training or model-output inspection occurred.
