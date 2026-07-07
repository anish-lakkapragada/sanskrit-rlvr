import Panini.Markers

/-!
# Rung ②: the Śivasūtra ordering is *optimal*

This is the headline target. Following Wiebke Petersen, *A Mathematical Analysis of
Pāṇini's Śivasūtras* (J. Logic Lang. Inf. 2004, Prop. 4.2), we state and prove the
theorem that Pāṇini's arrangement of the sounds is an **optimal S-alphabet**: among
all orderings that let every natural class Pāṇini uses be read off as a contiguous
`pratyāhāra`, his needs the fewest "tricks."

Petersen's `optimal` (Def. 2.5) pointedly does **not** mean "shortest": it is a
*lexicographic* criterion — (1) fewest duplicated sounds, then (2) among alphabets
tied on duplications, fewest markers — always *relative to the class family actually
used*. That family (`paniniClasses`) and the criterion are exactly the parameters
the Staal / Kiparsky / Petersen debate turns on; here they are pinned down as
explicit definitions, so "optimal in what sense?" becomes a checkable hypothesis
rather than a slogan.

## Petersen's real argument, and how this file's route differs

Petersen's own proof is **graph-theoretic**: S-encodability of a family is
equivalent to *planarity* of the Hasse diagram of its intersection-closure
(her Thm. 3.4, via a Kuratowski `K⁵`/`K₃,₃`-minor argument); `h, v, l` form a
"`K⁵`-triple" forcing the duplication, and the marker count 14 is read off a
boundary-graph *run*. Mechanizing planarity and runs is a much larger undertaking
than this repository attempts. Instead we reach the same conclusions by elementary,
fully mechanized arguments:

* **Duplication half** — by *convexity/betweenness* (`Interval.lean`): three
  positionally independent sounds cannot all live in one repetition-free line.
  Instantiated with Petersen's own triple `h, v, l`, witnessed by the real
  pratyāhāras `aṬ`, `yaṆ`, `raL`. **Complete, hypothesis-free.**
* **Marker half** — by *rigidity of right edges* (`Markers.lean`): a marker
  occurrence can only serve ⊆-nested classes, so a ⊆-antichain of `k` encoded
  classes forces `k − 1` markers. Pāṇini's family contains an 11-antichain of
  attested pratyāhāras (`paniniAntichain`), giving `10 ≤ numMarkers` — proved.
  The tight bound 14 (which Petersen herself does not prove — she reads it off a
  figure, §4.2) also needs markers *between* nested classes forced by traversal
  reversals; that is precisely her boundary-graph machinery, and it remains the
  one honest gap, carried as an explicit hypothesis where needed.

## The class family

`paniniClasses` is no longer a sample: it is the full family of pratyāhāras
**attested in the Aṣṭādhyāyī**, following the standard enumeration (the canonical
count is "41 (+1 by later grammarians)"; enumerations differ at the margin by an
entry or two, and we include the standard list — 43 sound-classes below). Sources:
the tabulation in the Wikipedia *Shiva Sutras* article (which follows Böhtlingk's
index), cross-checked against the pratyāhāras actually exercised by the
`vidyut-prakriya` derivation engine (Ambuda project, `sounds.rs`), which implements
2000+ Aṣṭādhyāyī rules. Every content below is verified against the Śivasūtra text
itself by `decide` (the `shivasutra_isSAlphabet` witnesses replay each pratyāhāra).

## Status (all `sorry`-free)

Lax semantics (`Encodes` — marker optional):
* `shivasutra_isSAlphabet` — Pāṇini's alphabet encodes all 43 attested classes and
  lists every sound. **Proved** (each class replayed by `decide`).
* `numMarkers_shivasutras = 14`, `duplications_shivasutras = 1`,
  `cost_shivasutras = 15`, `h_is_unique_duplicate`. **Proved**.
* `one_le_duplications_for_panini` / `shivasutra_duplication_optimal` —
  **Petersen's criterion (1), complete**: duplication is forced, and no rival
  duplicates less. **Proved, hypothesis-free.**
* `paniniAntichain` + `ten_le_numMarkers` + `eleven_le_cost`. **Proved.**
* `lax_marker_bound_false` / `lax_cost_optimality_false` — **the tight 14-marker
  bound and full cost-optimality are FALSE for the lax reading**: deleting the
  final `L` (`shivasutras_noL`) gives a valid 13-marker, cost-14 rival. Attempting
  the tight proof produced this machine-checked refutation.

Strict semantics (`EncodesT` — the it-marker must occur; the traditional and
Petersen-faithful reading):
* `shivasutra_isSAlphabetT` — Pāṇini's alphabet is a strict S-alphabet. **Proved**.
* `noL_not_strict` — the counterexample dies: `raL` has no well-formed pratyāhāra
  without the final `L`. **Proved** (the final Śivasūtra is load-bearing).
* `shivasutra_duplication_optimal_strict`. **Proved, hypothesis-free.**
* `eleven_le_numMarkers` — the antichain now bites without slack: every strict
  rival carries ≥ 11 markers. **Proved.**
* `twelve_le_cost` — every strict rival costs ≥ 12 (vs. Pāṇini's 15). **Proved.**
* `shivasutra_cost_optimal_of_marker_bound_strict` — full cost-optimality,
  conditional on the tight strict bound `14 ≤ numMarkers` (= Petersen's
  Satz 6.1.1; see the end-of-file diagnosis of what proving it takes).
-/

-- `x`, `y`, `z` for sounds collide with the constructors `Sound.x` etc.; harmless.
set_option linter.constructorNameAsVariable false
-- `decide` over the 43-class family recurses deeper than the default limit.
set_option maxRecDepth 65536

namespace Panini

open Sound Marker

/-! ## The attested pratyāhāras

Named `xY` for pratyāhāra "x…Y", with our marker spellings (`N1`/`N2` for the two
`Ṇ`s, `Ng` = `Ṅ`, `Ny` = `Ñ`, `T1` = `Ṭ`, `Sh` = `Ṣ`, `Sx` = `Ś`). One-line comments
give the traditional gloss. -/

/-- `aṆ₁` — the simple short vowels (1.1.69 *aṇudit savarṇasya…*). -/
def aN1 : Class := {a, i, u}
/-- `aK` — the simple vowels (6.1.101 *akaḥ savarṇe dīrghaḥ*). -/
def aK : Class := {a, i, u, rvoc, lvoc}
/-- `aC` — all vowels. -/
def aC : Class := {a, i, u, rvoc, lvoc, e, o, ai, au}
/-- `aṬ` — vowels + `h y v r` (8.4.2 *aṭkupvāṅnumvyavāye'pi*). Contains `h` and `v`
but not `l` — one leg of the duplication-forcing triple. -/
def aT1 : Class := {a, i, u, rvoc, lvoc, e, o, ai, au, h, y, v, r}
/-- `aṆ₂` — vowels + `h y v r l` (8.4.57 *aṇo'pragṛhyasyānunāsikaḥ*). -/
def aN2 : Class := {a, i, u, rvoc, lvoc, e, o, ai, au, h, y, v, r, l}
/-- `aM` — vowels, `h y v r l`, and the nasals. -/
def aM : Class :=
  {a, i, u, rvoc, lvoc, e, o, ai, au, h, y, v, r, l, nya, ma, nga, nretro, na}
/-- `aŚ` — all voiced sounds. -/
def aSx : Class :=
  {a, i, u, rvoc, lvoc, e, o, ai, au, h, y, v, r, l, nya, ma, nga, nretro, na,
   jha, bha, gha, ddha, dha, ja, ba, ga, dda, da}
/-- `aL` — every sound (1.1.65 *alo'ntyāt…*). -/
def aL : Class := Finset.univ
/-- `iK` — the simple vowels except `a` (1.1.3 *iko guṇavṛddhī*). -/
def iK : Class := {i, u, rvoc, lvoc}
/-- `iC` — the vowels except `a`. -/
def iC : Class := {i, u, rvoc, lvoc, e, o, ai, au}
/-- `iṆ₂` — vowels except `a`, plus `h y v r l` (8.3.57 *iṇkoḥ*). -/
def iN2 : Class := {i, u, rvoc, lvoc, e, o, ai, au, h, y, v, r, l}
/-- `uK` — `u ṛ ḷ` (4.1.6 *ugitaś ca*). -/
def uK : Class := {u, rvoc, lvoc}
/-- `eṄ` — the guṇa diphthongs (6.1.94 *eṅi pararūpam*). -/
def eNg : Class := {e, o}
/-- `eC` — the diphthongs (1.1.48 *eca igghrasvādeśe*). -/
def eC : Class := {e, o, ai, au}
/-- `aiC` — the vṛddhi diphthongs (1.1.1 *vṛddhir ādaic*). -/
def aiC : Class := {ai, au}
/-- `haL` — all consonants (1.3.3 *halantyam*). -/
def haL : Class := consonants
/-- `haŚ` — the voiced consonants h…Ś (6.1.114 *haśi ca*). -/
def haSx : Class :=
  {h, y, v, r, l, nya, ma, nga, nretro, na, jha, bha, gha, ddha, dha,
   ja, ba, ga, dda, da}
/-- `yaR` — all consonants except `h` (8.4.45 *yaro'nunāsike…*). -/
def yaR : Class := consonants.erase h
/-- `yaY` — semivowels, nasals and stops (8.4.58 *anusvārasya yayi…*). -/
def yaY : Class :=
  {y, v, r, l, nya, ma, nga, nretro, na, jha, bha, gha, ddha, dha,
   ja, ba, ga, dda, da, kha, pha, cha, ttha, tha, ca, tta, ta, ka, pa}
/-- `yaÑ` — semivowels, nasals, `jh bh` (7.3.101 *ato dīrgho yañi*). -/
def yaNy : Class := {y, v, r, l, nya, ma, nga, nretro, na, jha, bha}
/-- `yaM` — the semivowels and nasals (8.4.64 *halo yamāṃ yami lopaḥ*). -/
def yaM : Class := {y, v, r, l, nya, ma, nga, nretro, na}
/-- `yaṆ` — the semivowels (6.1.77 *iko yaṇ aci*). Contains `v` and `l` but not
`h` — one leg of the duplication-forcing triple. -/
def yaN2 : Class := {y, v, r, l}
/-- `vaL` — all consonants except `y` (6.1.66 *lopo vyor vali*). -/
def vaL : Class := consonants.erase y
/-- `vaŚ` — `v r l`, nasals and voiced stops (7.2.8 *neḍ vaśi kṛti*). -/
def vaSx : Class :=
  {v, r, l, nya, ma, nga, nretro, na, jha, bha, gha, ddha, dha, ja, ba, ga, dda, da}
/-- `raL` — all consonants except `y v` (1.2.26 *ralo vyupadhād…*). Contains `h`
and `l` but not `v` — one leg of the duplication-forcing triple. In Pāṇini's own
alphabet this interval only closes *because* `h` is re-listed in line 14. -/
def raL : Class := (consonants.erase y).erase v
/-- `ñaM` — the five nasals. -/
def nyaM : Class := {nya, ma, nga, nretro, na}
/-- `maY` — `m ṅ ṇ n` and the oral stops (8.3.33 *maya uño vo vā*). -/
def maY : Class :=
  {ma, nga, nretro, na, jha, bha, gha, ddha, dha, ja, ba, ga, dda, da,
   kha, pha, cha, ttha, tha, ca, tta, ta, ka, pa}
/-- `ṅaM` — `ṅ ṇ n` (8.3.32 *ṅamo hrasvād…*). -/
def ngaM : Class := {nga, nretro, na}
/-- `jhaL` — the obstruents incl. `h` (8.2.26 *jhalo jhali*). -/
def jhaL : Class :=
  {jha, bha, gha, ddha, dha, ja, ba, ga, dda, da, kha, pha, cha, ttha, tha,
   ca, tta, ta, ka, pa, sha, ssa, sa, h}
/-- `jhaR` — the obstruents except `h` (8.4.65 *jharo jhari savarṇe*). -/
def jhaR : Class :=
  {jha, bha, gha, ddha, dha, ja, ba, ga, dda, da, kha, pha, cha, ttha, tha,
   ca, tta, ta, ka, pa, sha, ssa, sa}
/-- `jhaY` — the oral stops (8.4.62 *jhayo ho'nyatarasyām*). -/
def jhaY : Class :=
  {jha, bha, gha, ddha, dha, ja, ba, ga, dda, da, kha, pha, cha, ttha, tha,
   ca, tta, ta, ka, pa}
/-- `jhaŚ` — the voiced stops (8.4.53 *jhalāṃ jaś jhaśi*). -/
def jhaSx : Class := {jha, bha, gha, ddha, dha, ja, ba, ga, dda, da}
/-- `jhaṢ` — the voiced aspirated stops (8.2.40 *jhaṣas tathor dho'dhaḥ*). -/
def jhaSh : Class := {jha, bha, gha, ddha, dha}
/-- `bhaṢ` — `bh gh ḍh dh` (8.2.37 *ekāco baśo bhaṣ jhaṣantasya…*). -/
def bhaSh : Class := {bha, gha, ddha, dha}
/-- `jaŚ` — the voiced unaspirated stops (8.2.39 *jhalāṃ jaśo'nte*). -/
def jaSx : Class := {ja, ba, ga, dda, da}
/-- `baŚ` — `b g ḍ d` (8.2.37 *ekāco baśo…*). -/
def baSx : Class := {ba, ga, dda, da}
/-- `khaR` — the voiceless obstruents (8.4.55 *khari ca*). -/
def khaR : Class :=
  {kha, pha, cha, ttha, tha, ca, tta, ta, ka, pa, sha, ssa, sa}
/-- `khaY` — the voiceless stops (7.4.61 *śarpūrvāḥ khayaḥ*). -/
def khaY : Class := {kha, pha, cha, ttha, tha, ca, tta, ta, ka, pa}
/-- `chaV` — `ch ṭh th c ṭ t` (8.3.7 *naś chavy apraśān*). -/
def chaV : Class := {cha, ttha, tha, ca, tta, ta}
/-- `caY` — the voiceless unaspirated stops (8.4.48 *…cayo dvitīyāḥ*, vārttika). -/
def caY : Class := {ca, tta, ta, ka, pa}
/-- `caR` — voiceless unaspirated stops + sibilants (8.4.54 *abhyāse car ca*). -/
def caR : Class := {ca, tta, ta, ka, pa, sha, ssa, sa}
/-- `śaL` — the fricatives incl. `h` (3.1.45 *śal igupadhād aniṭaḥ kṣaḥ*). -/
def shaL : Class := {sha, ssa, sa, h}
/-- `śaR` — the sibilants (8.3.35 *śar pare visarjanīyaḥ*). -/
def shaR : Class := {sha, ssa, sa}

/-- **The class family of the theorem**: every pratyāhāra attested in the
Aṣṭādhyāyī. This is the contestable linguistic hypothesis, made explicit — swap
this family (or the cost criterion) to encode the Staal/Kiparsky/Petersen
disagreement. -/
def paniniClasses : Finset Class :=
  { aN1, aK, aC, aT1, aN2, aM, aSx, aL,
    iK, iC, iN2, uK, eNg, eC, aiC,
    haL, haSx,
    yaR, yaY, yaNy, yaM, yaN2,
    vaL, vaSx, raL,
    nyaM, maY, ngaM,
    jhaL, jhaR, jhaY, jhaSx, jhaSh, bhaSh, jaSx, baSx,
    khaR, khaY, chaV, caY, caR,
    shaL, shaR }

/-! ## Pāṇini's alphabet is an S-alphabet for the family -/

/-- Pāṇini's ordering **is** an S-alphabet for the classes he uses: every attested
class is encodable as a pratyāhāra, and every sound occurs. (First conjunct of
Prop. 4.2.) Each branch replays the actual pratyāhāra by `decide`. -/
theorem shivasutra_isSAlphabet : IsSAlphabet shivasutras paniniClasses := by
  refine ⟨?_, ?_⟩
  · intro C hC
    fin_cases hC
    · exact ⟨.a, .N1, by decide⟩     -- aṆ₁
    · exact ⟨.a, .K, by decide⟩      -- aK
    · exact ⟨.a, .C, by decide⟩      -- aC
    · exact ⟨.a, .T1, by decide⟩     -- aṬ
    · exact ⟨.a, .N2, by decide⟩     -- aṆ₂
    · exact ⟨.a, .M, by decide⟩      -- aM
    · exact ⟨.a, .Sx, by decide⟩     -- aŚ
    · exact ⟨.a, .L, by decide⟩      -- aL
    · exact ⟨.i, .K, by decide⟩      -- iK
    · exact ⟨.i, .C, by decide⟩      -- iC
    · exact ⟨.i, .N2, by decide⟩     -- iṆ₂
    · exact ⟨.u, .K, by decide⟩      -- uK
    · exact ⟨.e, .Ng, by decide⟩     -- eṄ
    · exact ⟨.e, .C, by decide⟩      -- eC
    · exact ⟨.ai, .C, by decide⟩     -- aiC
    · exact ⟨.h, .L, by decide⟩      -- haL
    · exact ⟨.h, .Sx, by decide⟩     -- haŚ
    · exact ⟨.y, .R, by decide⟩      -- yaR
    · exact ⟨.y, .Y, by decide⟩      -- yaY
    · exact ⟨.y, .Ny, by decide⟩     -- yaÑ
    · exact ⟨.y, .M, by decide⟩      -- yaM
    · exact ⟨.y, .N2, by decide⟩     -- yaṆ
    · exact ⟨.v, .L, by decide⟩      -- vaL
    · exact ⟨.v, .Sx, by decide⟩     -- vaŚ
    · exact ⟨.r, .L, by decide⟩      -- raL
    · exact ⟨.nya, .M, by decide⟩    -- ñaM
    · exact ⟨.ma, .Y, by decide⟩     -- maY
    · exact ⟨.nga, .M, by decide⟩    -- ṅaM
    · exact ⟨.jha, .L, by decide⟩    -- jhaL
    · exact ⟨.jha, .R, by decide⟩    -- jhaR
    · exact ⟨.jha, .Y, by decide⟩    -- jhaY
    · exact ⟨.jha, .Sx, by decide⟩   -- jhaŚ
    · exact ⟨.jha, .Sh, by decide⟩   -- jhaṢ
    · exact ⟨.bha, .Sh, by decide⟩   -- bhaṢ
    · exact ⟨.ja, .Sx, by decide⟩    -- jaŚ
    · exact ⟨.ba, .Sx, by decide⟩    -- baŚ
    · exact ⟨.kha, .R, by decide⟩    -- khaR
    · exact ⟨.kha, .Y, by decide⟩    -- khaY
    · exact ⟨.cha, .V, by decide⟩    -- chaV
    · exact ⟨.ca, .Y, by decide⟩     -- caY
    · exact ⟨.ca, .R, by decide⟩     -- caR
    · exact ⟨.sha, .L, by decide⟩    -- śaL
    · exact ⟨.sha, .R, by decide⟩    -- śaR
  · decide

/-! ## Pāṇini's own cost -/

/-- Pāṇini's alphabet uses exactly the 14 markers. -/
theorem numMarkers_shivasutras : shivasutras.numMarkers = 14 := by decide

/-- Pāṇini's alphabet duplicates exactly one sound-slot (the second `h`). -/
theorem duplications_shivasutras : shivasutras.duplications = 1 := by decide

/-- Hence its total (additive) cost is 15. -/
theorem cost_shivasutras : cost shivasutras = 15 := by decide

/-- `h` is the **only** sound Pāṇini writes twice; every other sound occurs once.
This is the concrete fact behind "only one repetition is necessary" (Kiparsky) /
"no other choice than duplicating h" (Petersen §4.2). -/
theorem h_is_unique_duplicate :
    ∀ s : Sound, 2 ≤ shivasutras.sounds.count s ↔ s = Sound.h := by decide

/-! ## The duplication lower bound — unconditional

Petersen's Fig. 5–6: "the class memberships of `h`, `v` and `l` are independent of
each other" — for every pair among `{h, v, l}`, some attested pratyāhāra contains
that pair while excluding the third sound:

* `{h, v}` without `l` — `aṬ` (vowels + `h y v r`).
* `{v, l}` without `h` — `yaṆ` (the semivowels).
* `{h, l}` without `v` — `raL` (consonants except `y v`).

All three are members of `paniniClasses`, so
`one_le_duplications_of_independent_triple` (`Interval.lean`) applies outright. -/

/-- **Duplication is forced.** Any S-alphabet encoding Pāṇini's attested classes
must repeat a sound — the mechanized form of "no other choice than duplicating
`h`." -/
theorem one_le_duplications_for_panini {A : SAlphabet}
    (hA : IsSAlphabet A paniniClasses) : 1 ≤ A.duplications := by
  have haT : Encodes A aT1 := hA.1 aT1 (by simp [paniniClasses])
  have hyaN : Encodes A yaN2 := hA.1 yaN2 (by simp [paniniClasses])
  have hraL : Encodes A raL := hA.1 raL (by simp [paniniClasses])
  exact one_le_duplications_of_independent_triple
    (x := h) (y := v) (z := l) (C1 := aT1) (C2 := yaN2) (C3 := raL)
    haT (by decide) (by decide) (by decide)
    hyaN (by decide) (by decide) (by decide)
    hraL (by decide) (by decide) (by decide)

/-- **Petersen's optimality criterion (1), complete and hypothesis-free.**
No S-alphabet for Pāṇini's attested classes duplicates fewer sound-slots than
Pāṇini's own (which duplicates exactly one, the second `h`). -/
theorem shivasutra_duplication_optimal {A : SAlphabet}
    (hA : IsSAlphabet A paniniClasses) :
    shivasutras.duplications ≤ A.duplications := by
  rw [duplications_shivasutras]
  exact one_le_duplications_for_panini hA

/-! ## The marker lower bound — 10 of 14, via the antichain

Eleven attested pratyāhāras, pairwise ⊆-incomparable (mostly pairwise disjoint;
`aṆ₁`/`uK` overlap in `u`, `chaV`/`caR` in `c ṭ t`, `caR`/`śaL` in `ś ṣ s` — each
pair still incomparable). By `Markers.lean`'s rigidity theorem, their right edges
are pairwise distinct, so any S-alphabet for the family carries ≥ 10 markers. -/
def paniniAntichain : Finset Class :=
  {aN1, uK, eNg, aiC, yaN2, nyaM, jhaSh, jaSx, chaV, caR, shaL}

theorem paniniAntichain_card : paniniAntichain.card = 11 := by decide

theorem paniniAntichain_subset : ∀ C ∈ paniniAntichain, C ∈ paniniClasses := by
  intro C hC
  simp only [paniniAntichain, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl <;>
    simp [paniniClasses]

theorem paniniAntichain_antichain :
    ∀ C ∈ paniniAntichain, ∀ D ∈ paniniAntichain, C ⊆ D → C = D := by
  intro C hC D hD
  simp only [paniniAntichain, Finset.mem_insert, Finset.mem_singleton] at hC hD
  rcases hC with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl <;>
    rcases hD with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl <;>
      decide

/-- **Marker lower bound (partial).** Any S-alphabet for Pāṇini's attested classes
carries at least 10 markers. (Pāṇini's own carries 14; closing the remaining gap of
4 needs Petersen's boundary-graph run argument — see the file header.) -/
theorem ten_le_numMarkers {A : SAlphabet} (hA : IsSAlphabet A paniniClasses) :
    10 ≤ A.numMarkers := by
  have hcard := card_le_numMarkers_succ_of_antichain
    (fun C hC => hA.1 C (paniniAntichain_subset C hC)) paniniAntichain_antichain
  rw [paniniAntichain_card] at hcard
  omega

/-! ## The cost bounds -/

/-- **Unconditional cost bound.** Every S-alphabet for Pāṇini's attested classes
costs at least 11 (markers ≥ 10, duplications ≥ 1) — against Pāṇini's 15. -/
theorem eleven_le_cost {A : SAlphabet} (hA : IsSAlphabet A paniniClasses) :
    11 ≤ cost A := by
  have h1 := ten_le_numMarkers hA
  have h2 := one_le_duplications_for_panini hA
  unfold cost
  omega

/-- **Full cost-optimality, conditional on the tight marker bound.** Given that
every rival S-alphabet needs 14 markers (the single remaining unmechanized step of
Petersen §4.2 — she reads it off her Fig. 10 boundary graph), Pāṇini's alphabet
minimizes `cost` outright. -/
theorem shivasutra_cost_optimal_of_marker_bound
    (hmark : ∀ B : SAlphabet, IsSAlphabet B paniniClasses → 14 ≤ B.numMarkers)
    {A : SAlphabet} (hA : IsSAlphabet A paniniClasses) :
    cost shivasutras ≤ cost A := by
  rw [cost_shivasutras]
  have h1 := hmark A hA
  have h2 := one_le_duplications_for_panini hA
  unfold cost
  omega

/-!
## The tight marker bound is FALSE in the lax model — a machine-checked refutation

Attempting to prove `14 ≤ numMarkers` for all (lax) S-alphabets produced a
**counterexample** instead. Our `pratyahara` is `takeWhile`-based: when the named
marker never occurs, the "interval" silently runs to the end of the list. So one may
delete Pāṇini's *final* marker — the lone `L` of the 14th Śivasūtra — and every
L-terminated pratyāhāra (`aL`, `haL`, `vaL`, `raL`, `jhaL`, `śaL`) still denotes the
right class, now as an unterminated suffix. The resulting alphabet has **13 markers
and total cost 14**, beating Pāṇini's 15.

This is a modeling artifact, not a fact about Sanskrit: the tradition reads a
pratyāhāra as "sound *s* up to the it-marker *m*", presupposing the marker — the
final `h L` sūtra exists precisely to close the L-pratyāhāras. Petersen's model
(markers form the alphabet's ground set) builds the requirement in. The strict
layer below (`EncodesT`) restores it, and the counterexample dies there
(`noL_not_strict`). -/

/-- Pāṇini's Śivasūtras with the final marker `L` (the 14th sūtra's anubandha)
deleted. Under the lax semantics this still encodes every attested class. -/
def shivasutras_noL : SAlphabet := shivasutras.dropLast

theorem numMarkers_noL : shivasutras_noL.numMarkers = 13 := by decide

theorem cost_noL : cost shivasutras_noL = 14 := by decide

/-- The truncated alphabet is still a **lax** S-alphabet for all 43 attested
classes — the six L-classes are captured as unterminated suffixes. -/
theorem isSAlphabet_noL : IsSAlphabet shivasutras_noL paniniClasses := by
  refine ⟨?_, ?_⟩
  · intro C hC
    fin_cases hC
    · exact ⟨.a, .N1, by decide⟩     -- aṆ₁
    · exact ⟨.a, .K, by decide⟩      -- aK
    · exact ⟨.a, .C, by decide⟩      -- aC
    · exact ⟨.a, .T1, by decide⟩     -- aṬ
    · exact ⟨.a, .N2, by decide⟩     -- aṆ₂
    · exact ⟨.a, .M, by decide⟩      -- aM
    · exact ⟨.a, .Sx, by decide⟩     -- aŚ
    · exact ⟨.a, .L, by decide⟩      -- aL   (unterminated suffix!)
    · exact ⟨.i, .K, by decide⟩      -- iK
    · exact ⟨.i, .C, by decide⟩      -- iC
    · exact ⟨.i, .N2, by decide⟩     -- iṆ₂
    · exact ⟨.u, .K, by decide⟩      -- uK
    · exact ⟨.e, .Ng, by decide⟩     -- eṄ
    · exact ⟨.e, .C, by decide⟩      -- eC
    · exact ⟨.ai, .C, by decide⟩     -- aiC
    · exact ⟨.h, .L, by decide⟩      -- haL  (unterminated suffix!)
    · exact ⟨.h, .Sx, by decide⟩     -- haŚ
    · exact ⟨.y, .R, by decide⟩      -- yaR
    · exact ⟨.y, .Y, by decide⟩      -- yaY
    · exact ⟨.y, .Ny, by decide⟩     -- yaÑ
    · exact ⟨.y, .M, by decide⟩      -- yaM
    · exact ⟨.y, .N2, by decide⟩     -- yaṆ
    · exact ⟨.v, .L, by decide⟩      -- vaL  (unterminated suffix!)
    · exact ⟨.v, .Sx, by decide⟩     -- vaŚ
    · exact ⟨.r, .L, by decide⟩      -- raL  (unterminated suffix!)
    · exact ⟨.nya, .M, by decide⟩    -- ñaM
    · exact ⟨.ma, .Y, by decide⟩     -- maY
    · exact ⟨.nga, .M, by decide⟩    -- ṅaM
    · exact ⟨.jha, .L, by decide⟩    -- jhaL (unterminated suffix!)
    · exact ⟨.jha, .R, by decide⟩    -- jhaR
    · exact ⟨.jha, .Y, by decide⟩    -- jhaY
    · exact ⟨.jha, .Sx, by decide⟩   -- jhaŚ
    · exact ⟨.jha, .Sh, by decide⟩   -- jhaṢ
    · exact ⟨.bha, .Sh, by decide⟩   -- bhaṢ
    · exact ⟨.ja, .Sx, by decide⟩    -- jaŚ
    · exact ⟨.ba, .Sx, by decide⟩    -- baŚ
    · exact ⟨.kha, .R, by decide⟩    -- khaR
    · exact ⟨.kha, .Y, by decide⟩    -- khaY
    · exact ⟨.cha, .V, by decide⟩    -- chaV
    · exact ⟨.ca, .Y, by decide⟩     -- caY
    · exact ⟨.ca, .R, by decide⟩     -- caR
    · exact ⟨.sha, .L, by decide⟩    -- śaL  (unterminated suffix!)
    · exact ⟨.sha, .R, by decide⟩    -- śaR
  · decide

/-- **The lax tight marker bound is false.** There is a lax S-alphabet for the
attested family with only 13 markers. In particular the hypothesis `hmark` of
`shivasutra_cost_optimal_of_marker_bound` is *unsatisfiable* for the lax reading —
attempting to prove it produced this refutation. -/
theorem lax_marker_bound_false :
    ¬ ∀ A : SAlphabet, IsSAlphabet A paniniClasses → 14 ≤ A.numMarkers := by
  intro h
  have := h shivasutras_noL isSAlphabet_noL
  rw [numMarkers_noL] at this
  omega

/-- **Lax cost-optimality is false outright**: the truncated alphabet costs 14,
beating Pāṇini's 15. The lax semantics is therefore the wrong arena for Petersen's
theorem; the strict layer below is the right one. -/
theorem lax_cost_optimality_false :
    ¬ ∀ A : SAlphabet, IsSAlphabet A paniniClasses → cost shivasutras ≤ cost A := by
  intro h
  have := h shivasutras_noL isSAlphabet_noL
  rw [cost_shivasutras, cost_noL] at this
  omega

/-! ## The strict theorems

Everything above re-proved for the faithful semantics (`EncodesT`: the it-marker
must occur), where the marker-dropping trick is impossible. Pāṇini's own alphabet
is a strict S-alphabet — his final `L` is exactly what the strict reading needs —
and the antichain bound now bites without slack: **11 ≤ numMarkers** and
**12 ≤ cost**, unconditionally. -/

/-- Pāṇini's ordering is a **strict** S-alphabet: every attested class has a
well-formed pratyāhāra (marker present). Same witnesses as the lax theorem — every
pratyāhāra Pāṇini actually uses names a marker that exists. -/
theorem shivasutra_isSAlphabetT : IsSAlphabetT shivasutras paniniClasses := by
  refine ⟨?_, ?_⟩
  · intro C hC
    fin_cases hC
    · exact ⟨.a, .N1, by decide, by decide⟩
    · exact ⟨.a, .K, by decide, by decide⟩
    · exact ⟨.a, .C, by decide, by decide⟩
    · exact ⟨.a, .T1, by decide, by decide⟩
    · exact ⟨.a, .N2, by decide, by decide⟩
    · exact ⟨.a, .M, by decide, by decide⟩
    · exact ⟨.a, .Sx, by decide, by decide⟩
    · exact ⟨.a, .L, by decide, by decide⟩
    · exact ⟨.i, .K, by decide, by decide⟩
    · exact ⟨.i, .C, by decide, by decide⟩
    · exact ⟨.i, .N2, by decide, by decide⟩
    · exact ⟨.u, .K, by decide, by decide⟩
    · exact ⟨.e, .Ng, by decide, by decide⟩
    · exact ⟨.e, .C, by decide, by decide⟩
    · exact ⟨.ai, .C, by decide, by decide⟩
    · exact ⟨.h, .L, by decide, by decide⟩
    · exact ⟨.h, .Sx, by decide, by decide⟩
    · exact ⟨.y, .R, by decide, by decide⟩
    · exact ⟨.y, .Y, by decide, by decide⟩
    · exact ⟨.y, .Ny, by decide, by decide⟩
    · exact ⟨.y, .M, by decide, by decide⟩
    · exact ⟨.y, .N2, by decide, by decide⟩
    · exact ⟨.v, .L, by decide, by decide⟩
    · exact ⟨.v, .Sx, by decide, by decide⟩
    · exact ⟨.r, .L, by decide, by decide⟩
    · exact ⟨.nya, .M, by decide, by decide⟩
    · exact ⟨.ma, .Y, by decide, by decide⟩
    · exact ⟨.nga, .M, by decide, by decide⟩
    · exact ⟨.jha, .L, by decide, by decide⟩
    · exact ⟨.jha, .R, by decide, by decide⟩
    · exact ⟨.jha, .Y, by decide, by decide⟩
    · exact ⟨.jha, .Sx, by decide, by decide⟩
    · exact ⟨.jha, .Sh, by decide, by decide⟩
    · exact ⟨.bha, .Sh, by decide, by decide⟩
    · exact ⟨.ja, .Sx, by decide, by decide⟩
    · exact ⟨.ba, .Sx, by decide, by decide⟩
    · exact ⟨.kha, .R, by decide, by decide⟩
    · exact ⟨.kha, .Y, by decide, by decide⟩
    · exact ⟨.cha, .V, by decide, by decide⟩
    · exact ⟨.ca, .Y, by decide, by decide⟩
    · exact ⟨.ca, .R, by decide, by decide⟩
    · exact ⟨.sha, .L, by decide, by decide⟩
    · exact ⟨.sha, .R, by decide, by decide⟩
  · decide

/-- Strictness kills the counterexample: the truncated alphabet is **not** a
strict S-alphabet — `raL` (consonants minus `y v`, which needs the trailing
`h … L`) has no well-formed pratyāhāra once the final `L` is gone. -/
theorem noL_not_strict : ¬ IsSAlphabetT shivasutras_noL paniniClasses := by
  intro h
  have hraL := h.1 raL (by simp [paniniClasses])
  exact (by decide : ¬ EncodesT shivasutras_noL raL) hraL

/-- Duplication is forced under strict semantics (a fortiori from the lax case). -/
theorem one_le_duplications_for_panini_strict {A : SAlphabet}
    (hA : IsSAlphabetT A paniniClasses) : 1 ≤ A.duplications :=
  one_le_duplications_for_panini hA.isSAlphabet

/-- **Petersen's criterion (1), strict form, hypothesis-free**: no strict rival
duplicates fewer sound-slots than Pāṇini's single repeated `h`. -/
theorem shivasutra_duplication_optimal_strict {A : SAlphabet}
    (hA : IsSAlphabetT A paniniClasses) :
    shivasutras.duplications ≤ A.duplications :=
  shivasutra_duplication_optimal hA.isSAlphabet

/-- **Strict marker lower bound — 11 of 14, no slack.** Every strict S-alphabet
for the attested family carries at least 11 markers: the 11-antichain's right
edges are pairwise-distinct genuine marker occurrences. -/
theorem eleven_le_numMarkers {A : SAlphabet} (hA : IsSAlphabetT A paniniClasses) :
    11 ≤ A.numMarkers := by
  have hcard := card_le_numMarkers_of_antichainT
    (fun C hC => hA.1 C (paniniAntichain_subset C hC)) paniniAntichain_antichain
  rw [paniniAntichain_card] at hcard
  omega

/-- **Unconditional strict cost bound.** Every strict S-alphabet costs at least 12
(11 markers + 1 duplication) — against Pāṇini's 15. -/
theorem twelve_le_cost {A : SAlphabet} (hA : IsSAlphabetT A paniniClasses) :
    12 ≤ cost A := by
  have h1 := eleven_le_numMarkers hA
  have h2 := one_le_duplications_for_panini_strict hA
  unfold cost
  omega

/-- **Full cost-optimality, conditional on the tight strict marker bound.** Unlike
its lax predecessor (whose hypothesis `lax_marker_bound_false` refutes), the strict
hypothesis is consistent with everything proved here and is exactly Petersen's
Satz 6.1.1 (2008 dissertation, pp. 149–152). -/
theorem shivasutra_cost_optimal_of_marker_bound_strict
    (hmark : ∀ B : SAlphabet, IsSAlphabetT B paniniClasses → 14 ≤ B.numMarkers)
    {A : SAlphabet} (hA : IsSAlphabetT A paniniClasses) :
    cost shivasutras ≤ cost A := by
  rw [cost_shivasutras]
  have h1 := hmark A hA
  have h2 := one_le_duplications_for_panini_strict hA
  unfold cost
  omega

/-!
## The remaining gap, diagnosed from Petersen's actual proof

Attempting the tight bound produced, first, the refutation above (the lax reading is
simply the wrong statement), and second, a precise map of what the strict bound
requires. Petersen's dissertation (*Zur Minimalität von Pāṇinis Śivasūtras*,
Düsseldorf 2008 — the only rigorous source; her 2004 JoLLI paper calls the count
"obvious") proves `14 ≤ markers` as **Satz 6.1.1** in two steps:

1. **The `h`-free class system needs 13 markers.** Delete `h` from every class:
   the resulting family is S-representable without duplication, and the minimum
   marker count over *all* its alphabets is 13. This rests on her Chapter-5 theory
   of *runs through S-graphs* (plane Hasse diagrams of the concept lattice; markers
   correspond to descents of a boundary run; minimality is read off the two
   possible run directions). Our antichain bound reaches 11 of these 13; the two
   extra edges (hers terminate `aṬ∖h` and `yaÑ`) are forced by run reversals that
   plain ⊆-incomparability cannot see.
2. **Adding `h` costs one more.** Because `caR = {c ṭ t k p ś ṣ s}`,
   `śaR = {ś ṣ s}`, `śaL = {ś ṣ s h}` are all attested, in a duplication-minimal
   alphabet `h` must *follow* `ś ṣ s` and be cut off from them by a fresh marker —
   which is exactly why Pāṇini's list ends `… ś ṣ s R h L`.

Two honest caveats carried from this analysis. (i) Her bound is proved **relative
to duplication-minimal extensions** (her "perfekt erweitert"); whether `14 ≤`
holds for strict alphabets with *unboundedly many* duplications is not settled by
her text — our exploration of many-duplication layouts found each candidate
13-marker architecture dying at a first-occurrence obstruction, but no proof.
(ii) Her S-alphabets start a pratyāhāra at a *chosen copy* of a sound, ours at the
*first* copy — our model is strictly more constrained, so her lower bound does not
transfer verbatim; the fully faithful target is
`shivasutra_cost_optimal_of_marker_bound_strict`'s hypothesis, possibly with a
`duplications ≤ 1` guard. Mechanizing step 1 (plane Hasse diagrams, S-graphs,
runs) is a self-contained project of its own — the genuine remaining work.

Note on route (a) ("bound, then decide"): still not viable — even after a
normal-form cap the candidate space is ~`42!` arrangements, far beyond kernel
reduction. The bound must stay structural.
-/

end Panini
