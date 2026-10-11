# Impersonal voice: a bounded 4D follow-up

Date: 2026-10-07. No model calls or model-answer inspection. No change to the active pilot08 inputs, code, source policy or analysis.

Bhāve is already a value of the voice coordinate; using it would preserve the four-dimensional task. Its grammatical interpretation must be licensed by the stated dhatu meaning. The [Kāśikā on 3.4.69](https://sanskritdocuments.org/~sanskrit/learning_tools/sarvanisutrani/3.4.69.htm) distinguishes impersonal use of intransitive verbs from personal passive use. The later commentary also discusses verbs whose object is not expressed; that interpretive extension is not adopted as a blanket benchmark permission.

The shared generator enforces third-person singular agreement but does not currently quarantine the known impersonal-aorist defect. The present discovery census excludes all bhāve, so this gap does not affect its paid tasks. Any new impersonal experiment must exclude Lun explicitly before the shared predicate can be updated after the frozen run.

The [Kāśikā on 3.1.66](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.66.htm) gives **aśāyi** for impersonal śī. The Laghusiddhāntakaumudī there gives **abhāvi** for bhū. Current installed VP produces neither expected form when asked for Bhave/Lun/Prathama/Eka. Its Karmani counterpart does produce those forms. This is direct source evidence for an answer-key defect, rather than a reason to count model disagreements as difficult questions.

The pinned upstream [vikaraṇa implementation](https://github.com/ambuda-org/vidyut/blob/8da2f90bee3ce1c07505fa432fc3729e3f7e02ea/vidyut-prakriya/src/vikarana.rs#L253) applies 3.1.66 only under the `Karmani` tag. This source snapshot explains the reproduced behavior; it is not a claim that the installed binary was independently verified to have been built from that commit.

[Fifty paired controls](controls.json) cover bhū, has, glai, ās and śī in all ten classical tenses/moods. All 45 non-aorist Bhave/Karmani engine comparisons have identical output sets; all five aorist comparisons differ. Four positive direct-source controls pass, including bhū's impersonal perfect **babhūve**, discussed in the [Bālamanoramā on 1.3.13](https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/1/1.3.13.htm). The two source-aorist controls fail. The Karmani comparisons are diagnostic engine inputs, not grammatical endorsements of personal passives for these intransitive meanings.

This establishes a bounded search option: source-clean intransitive dhatus, non-aorist tenses, and canonical agreement. It does **not** establish a broad new morphological mechanism or model weakness. Its output rules substantially overlap the already explored passive forms, and it would concentrate person/number. The separate historical-coverage review should decide whether a small prospective probe is justified; no paid request is proposed by these controls alone.

Reproduce with `.venv/bin/python -m misc.vp_4d_bhave_controls` in a fresh versioned output directory. The script preserves existing evidence and makes no network or paid calls.
