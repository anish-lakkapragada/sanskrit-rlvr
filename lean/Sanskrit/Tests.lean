import Sanskrit.Sentence

/-!
# Gold tests, as theorems

Paradigm cells from standard grammars (Whitney) and attested corpus forms
(DCS harvest — see data/dcs/harvest.json) stated as propositions and
replayed by the kernel at every build. Sentence-level checks use
`native_decide` (the sentence pipeline is too big for kernel reduction).
-/

namespace Sanskrit

-- declension, v1 classes: deva (note devena/devāya; ṇatva absent without a trigger)
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

-- new vowel classes: vāri, madhu-type, dhenu, vadhū
example : decline "vAri" .i_n .nom .pl = ["vArIRi"] := by native_decide
example : decline "vAri" .i_n .ins .sg = ["vAriRA"] := by native_decide
example : decline "maDu" .u_n .nom .pl = ["maDUni"] := by native_decide
example : decline "maDu" .u_n .ins .sg = ["maDunA"] := by native_decide
example : decline "Denu" .u_f .ins .sg = ["DenvA"] := by native_decide
example : decline "Denu" .u_f .dat .sg = ["Denave", "DenvE"] := by native_decide
example : decline "vaDU" .U_f .nom .sg = ["vaDUH"] := by native_decide
example : decline "vaDU" .U_f .ins .sg = ["vaDvA"] := by native_decide

-- ṛ-stems: guṇa pitaram vs vṛddhi hotāram; fem acc pl mātṝḥ; gen pl with ṇatva
example : decline "pitf" .f_m .nom .sg = ["pitA"] := by native_decide
example : decline "pitf" .f_m .acc .sg = ["pitaram"] := by native_decide
example : decline "pitf" .f_m .ins .sg = ["pitrA"] := by native_decide
example : decline "pitf" .f_m .gen .sg = ["pituH"] := by native_decide
example : decline "pitf" .f_m .loc .sg = ["pitari"] := by native_decide
example : decline "pitf" .f_m .acc .pl = ["pitFn"] := by native_decide
example : decline "pitf" .f_m .gen .pl = ["pitFRAm"] := by native_decide
example : decline "hotf" .f_m_v .acc .sg = ["hotAram"] := by native_decide
example : decline "hotf" .f_m_v .nom .pl = ["hotAraH"] := by native_decide
example : decline "mAtf" .f_f .acc .sg = ["mAtaram"] := by native_decide
example : decline "mAtf" .f_f .acc .pl = ["mAtFH"] := by native_decide

-- an-stems: syncope rājñā/nāmnā/pūṣṇā vs kept -a- ātmanā/karmaṇā
example : decline "rAjan" .an_m .nom .sg = ["rAjA"] := by native_decide
example : decline "rAjan" .an_m .acc .sg = ["rAjAnam"] := by native_decide
example : decline "rAjan" .an_m .ins .sg = ["rAjYA"] := by native_decide
example : decline "rAjan" .an_m .gen .sg = ["rAjYaH"] := by native_decide
example : decline "rAjan" .an_m .loc .sg = ["rAjYi", "rAjani"] := by native_decide
example : decline "rAjan" .an_m .ins .pl = ["rAjaBiH"] := by native_decide
example : decline "pUzan" .an_m .ins .sg = ["pUzRA"] := by native_decide
example : decline "Atman" .an_m_a .ins .sg = ["AtmanA"] := by native_decide
example : decline "Atman" .an_m_a .nom .sg = ["AtmA"] := by native_decide
example : decline "karman" .an_n_a .nom .sg = ["karma"] := by native_decide
example : decline "karman" .an_n_a .ins .sg = ["karmaRA"] := by native_decide
example : decline "karman" .an_n_a .nom .pl = ["karmARi"] := by native_decide
example : decline "nAman" .an_n .ins .sg = ["nAmnA"] := by native_decide
example : decline "nAman" .an_n .nom .pl = ["nAmAni"] := by native_decide

-- in-stems: yogī, yoginam, yogibhiḥ
example : decline "yogin" .in_m .nom .sg = ["yogI"] := by native_decide
example : decline "yogin" .in_m .acc .sg = ["yoginam"] := by native_decide
example : decline "yogin" .in_m .ins .pl = ["yogiBiH"] := by native_decide
example : decline "yogin" .in_m .loc .pl = ["yogizu"] := by native_decide

-- neuter s-stems: manaḥ/manasā/manāṃsi/manobhiḥ; haviṣā/havirbhiḥ; cakṣūṃṣi
example : decline "manas" .as_n .nom .sg = ["manaH"] := by native_decide
example : decline "manas" .as_n .ins .sg = ["manasA"] := by native_decide
example : decline "manas" .as_n .nom .pl = ["manAMsi"] := by native_decide
example : decline "manas" .as_n .ins .pl = ["manoBiH"] := by native_decide
example : decline "manas" .as_n .loc .pl = ["manaHsu"] := by native_decide
example : decline "havis" .is_n .ins .sg = ["havizA"] := by native_decide
example : decline "havis" .is_n .nom .pl = ["havIMzi"] := by native_decide
example : decline "havis" .is_n .ins .pl = ["havirBiH"] := by native_decide
example : decline "cakzus" .us_n .nom .pl = ["cakzUMzi"] := by native_decide

-- mat/vat-stems: bhagavān/bhagavantam/bhagavadbhiḥ; mahān strengthens to mahānt-
example : decline "Bagavat" .mat_m .nom .sg = ["BagavAn"] := by native_decide
example : decline "Bagavat" .mat_m .acc .sg = ["Bagavantam"] := by native_decide
example : decline "Bagavat" .mat_m .ins .sg = ["BagavatA"] := by native_decide
example : decline "Bagavat" .mat_m .ins .pl = ["BagavadBiH"] := by native_decide
example : decline "Bagavat" .mat_m .loc .pl = ["Bagavatsu"] := by native_decide
example : decline "mahat" .mat_m .nom .sg = ["mahAn"] := by native_decide
example : decline "mahat" .mat_m .acc .sg = ["mahAntam"] := by native_decide
example : decline "mahat" .mat_m .ins .sg = ["mahatA"] := by native_decide
example : decline "jagat" .mat_n .nom .sg = ["jagat"] := by native_decide
example : decline "jagat" .mat_n .nom .pl = ["jaganti"] := by native_decide

-- root stems: vāk/vācam/vāgbhiḥ/vākṣu; dik/digbhiḥ/dikṣu
example : decline "vAc" .cons_f .nom .sg "vAk" = ["vAk"] := by native_decide
example : decline "vAc" .cons_f .acc .sg "vAk" = ["vAcam"] := by native_decide
example : decline "vAc" .cons_f .ins .pl "vAk" = ["vAgBiH"] := by native_decide
example : decline "vAc" .cons_f .loc .pl "vAk" = ["vAkzu"] := by native_decide
example : decline "diS" .cons_f .nom .sg "dik" = ["dik"] := by native_decide
example : decline "diS" .cons_f .ins .pl "dik" = ["digBiH"] := by native_decide
example : decline "diS" .cons_f .loc .pl "dik" = ["dikzu"] := by native_decide
example : decline "marut" .cons_m .loc .pl "marut" = ["marutsu"] := by native_decide

-- pronominal adjectives: sarve/sarvasmai/sarveṣām; anyat; pūrve and pūrvāḥ both
example : decline "sarva" .pron_m .nom .pl = ["sarve"] := by native_decide
example : decline "sarva" .pron_m .ins .sg = ["sarveRa"] := by native_decide
example : decline "sarva" .pron_m .dat .sg = ["sarvasmE"] := by native_decide
example : decline "sarva" .pron_m .gen .pl = ["sarvezAm"] := by native_decide
example : decline "anya" .pron_n_at .nom .sg = ["anyat"] := by native_decide
example : decline "sarvA" .pron_f .loc .sg = ["sarvasyAm"] := by native_decide
example : decline "pUrva" .pron_opt_m .nom .pl = ["pUrve", "pUrvAH"] := by native_decide

-- thematic conjugation
example : conjugate "gacCa" .P .third .sg = "gacCati" := by native_decide
example : conjugate "gacCa" .P .first .pl = "gacCAmaH" := by native_decide
example : conjugate "laBa" .A .third .sg = "laBate" := by native_decide
example : conjugate "laBa" .A .first .sg = "laBe" := by native_decide
example : conjugate "smara" .P .third .pl = "smaranti" := by native_decide
example : conjugate "cara" .P .third .sg = "carati" := by native_decide

-- athematic verbs, via their lexicon tables (as, kṛ, dā, hu, śru, jñā, i, han)
private def athem (lemma : String) (pada : Pada) (p : Person) (n : Number) : List String :=
  match verbs.find? fun e => e.lemma == lemma && e.pada == pada with
  | some e => e.presentForms p n
  | none => []

example : athem "as" .P .third .sg = ["asti"] := by native_decide
example : athem "as" .P .third .pl = ["santi"] := by native_decide
example : athem "kf" .P .third .sg = ["karoti"] := by native_decide
example : athem "kf" .P .third .pl = ["kurvanti"] := by native_decide
example : athem "kf" .A .third .sg = ["kurute"] := by native_decide
example : athem "dA" .P .third .sg = ["dadAti"] := by native_decide
example : athem "hu" .P .third .sg = ["juhoti"] := by native_decide
example : athem "Sru" .P .third .sg = ["SfRoti"] := by native_decide
example : athem "Sru" .P .third .pl = ["SfRvanti"] := by native_decide
example : athem "jYA" .P .third .sg = ["jAnAti"] := by native_decide
example : athem "i" .P .third .sg = ["eti"] := by native_decide
example : athem "han" .P .third .sg = ["hanti"] := by native_decide
example : athem "han" .P .third .pl = ["Gnanti"] := by native_decide

-- grammatical sentences compile…
example : Grammatical "rāmo grāmaṃ gacchati" := by native_decide
example : Grammatical "bālo grāmaṃ gacchati" := by native_decide
example : Grammatical "bālaḥ grāmam gacchati" := by native_decide  -- pausa spelling
example : Grammatical "ahaṃ jalaṃ pibāmi" := by native_decide
example : Grammatical "kanyā phalaṃ labhate" := by native_decide
example : Grammatical "devāś ca gacchanti" := by native_decide
example : Grammatical "muniḥ satyaṃ vadati" := by native_decide
example : Grammatical "kumāro nadyāṃ carati" := by native_decide

-- …including the new morphology, end to end
example : Grammatical "rājā grāmaṃ gacchati" := by native_decide
example : Grammatical "bhagavān satyaṃ vadati" := by native_decide
example : Grammatical "pitā jalaṃ pibati" := by native_decide
example : Grammatical "rājā karma karoti" := by native_decide
example : Grammatical "munayo vācaṃ śṛṇvanti" := by native_decide
example : Grammatical "sarve devā gacchanti" := by native_decide
example : Grammatical "mahān rājā bhavati" := by native_decide
example : Grammatical "rājñaḥ putro gacchati" := by native_decide
example : Grammatical "rājñā saha gacchati bālaḥ" := by native_decide

-- multi-clause sentences: k verbs licensed by k−1 coordinators
example : Grammatical "rāmo gacchati kanyā ca phalaṃ labhate" := by native_decide
example : Grammatical
  "rāmo grāmaṃ gacchati kanyā ca phalaṃ labhate munayaś ca satyaṃ vadanti" := by
  native_decide
example : ¬ Grammatical "rāmo gacchati kanyā phalaṃ labhate" := by native_decide
example : ¬ Grammatical "rāmo gacchati gacchanti ca" := by native_decide

-- …and ungrammatical ones do not
example : ¬ Grammatical "bālāḥ grāmaṃ gacchati" := by native_decide  -- number clash
example : ¬ Grammatical "ahaṃ gacchati" := by native_decide          -- person clash
example : ¬ Grammatical "priyā bālo gacchati" := by native_decide    -- gender clash
example : ¬ Grammatical "rājā gacchanti" := by native_decide         -- number clash
example : ¬ Grammatical "bhagavān gacchanti" := by native_decide     -- number clash
example : ¬ Grammatical "kumārāḥ nadyāṃ carati" := by native_decide  -- number clash
example : ¬ Grammatical "bālaḥ grāmam" := by native_decide           -- no verb
example : ¬ Grammatical "the boy goes home" := by native_decide      -- not Sanskrit

end Sanskrit
