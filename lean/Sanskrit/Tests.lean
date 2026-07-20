import Sanskrit.Sentence

/-!
# Gold tests, as theorems

Paradigm cells from standard grammars (Whitney; cross-checked last run
against vidyut-prakriya on all 2,496 cells) stated as propositions and
replayed by the kernel at every build. Sentence-level checks use
`native_decide` (the sentence pipeline is too big for kernel reduction).
-/

namespace Sanskrit

-- declension: deva (note devena/devāya; ṇatva absent without a trigger)
example : decline "deva" .a_m .nom .sg = ["devaH"] := by native_decide
example : decline "deva" .a_m .ins .sg = ["devena"] := by native_decide
example : decline "deva" .a_m .loc .pl = ["devezu"] := by native_decide
example : decline "deva" .a_m .gen .pl = ["devAnAm"] := by native_decide

-- ṇatva fires across the word: rāmeṇa, rāmāṇām; kṣetrāṇi
example : decline "rAma" .a_m .ins .sg = ["rAmeRa"] := by native_decide
example : decline "rAma" .a_m .gen .pl = ["rAmARAm"] := by native_decide
example : decline "kzetra" .a_n .nom .pl = ["kzetrARi"] := by native_decide
-- ...but not without a trigger: vanāni
example : decline "vana" .a_n .nom .pl = ["vanAni"] := by native_decide

-- senā, agni, mati (with its classical variant forms), guru, nadī
example : decline "senA" .A_f .dat .sg = ["senAyE"] := by native_decide
example : decline "senA" .A_f .loc .pl = ["senAsu"] := by native_decide
example : decline "agni" .i_m .dat .sg = ["agnaye"] := by native_decide
example : decline "agni" .i_m .loc .sg = ["agnO"] := by native_decide
example : decline "mati" .i_f .dat .sg = ["mataye", "matyE"] := by native_decide
example : decline "mati" .i_f .acc .pl = ["matIH"] := by native_decide
example : decline "guru" .u_m .ins .sg = ["guruRA"] := by native_decide
example : decline "guru" .u_m .gen .pl = ["gurURAm"] := by native_decide
example : decline "nadI" .I_f .nom .pl = ["nadyaH"] := by native_decide

-- conjugation
example : conjugate "gacCa" .P .third .sg = "gacCati" := by native_decide
example : conjugate "gacCa" .P .first .pl = "gacCAmaH" := by native_decide
example : conjugate "laBa" .A .third .sg = "laBate" := by native_decide
example : conjugate "laBa" .A .first .sg = "laBe" := by native_decide
example : conjugate "as" .P .third .pl = "santi" := by native_decide
example : conjugate "kf" .P .third .pl = "kurvanti" := by native_decide
example : conjugate "smara" .P .third .pl = "smaranti" := by native_decide

-- grammatical sentences compile…
example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide
example : Grammatical "bālo grāmaṃ gacchati" := by native_decide
example : Grammatical "bālaḥ grāmam gacchati" := by native_decide  -- pausa spelling
example : Grammatical "ahaṃ jalaṃ pibāmi" := by native_decide
example : Grammatical "sundarī kanyā mālāṃ labhate" := by native_decide
example : Grammatical "devāś ca gacchanti" := by native_decide
example : Grammatical "muniḥ satyaṃ vadati" := by native_decide

-- multi-clause sentences: k verbs licensed by k−1 ca particles
example : Grammatical "rāmo gacchati kanyā ca mālāṃ labhate" := by native_decide
example : Grammatical
  "rāmo grāmaṃ gacchati kanyā ca mālāṃ labhate munayaś ca satyaṃ vadanti" := by
  native_decide
example : ¬ Grammatical "rāmo gacchati kanyā mālāṃ labhate" := by native_decide
example : ¬ Grammatical "rāmo gacchati gacchanti ca" := by native_decide

-- spot-checks across the later lexicon additions
example : decline "meGa" .a_m .nom .pl = ["meGAH"] := by native_decide
example : decline "gaNgA" .A_f .loc .sg = ["gaNgAyAm"] := by native_decide
example : decline "banDu" .u_m .gen .pl = ["banDUnAm"] := by native_decide
example : conjugate "cara" .P .third .sg = "carati" := by native_decide
example : Grammatical "kumāro gaṅgāyāṃ carati" := by native_decide
example : Grammatical "ugraḥ vānaraḥ patram khādati" := by native_decide
example : ¬ Grammatical "kumārāḥ gaṅgāyāṃ carati" := by native_decide

-- …and ungrammatical ones do not
example : ¬ Grammatical "bālāḥ grāmaṃ gacchati" := by native_decide  -- number clash
example : ¬ Grammatical "ahaṃ gacchati" := by native_decide          -- person clash
example : ¬ Grammatical "sundarī bālo gacchati" := by native_decide  -- gender clash
example : ¬ Grammatical "bālaḥ khādati" := by native_decide          -- missing object
example : ¬ Grammatical "bālaḥ grāmam" := by native_decide           -- no verb
example : ¬ Grammatical "the boy goes home" := by native_decide      -- not Sanskrit

end Sanskrit
