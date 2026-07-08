import Panini.Necessity

/-!
# How determined is the Śivasūtra ordering? The forced/free map

A live three-way dispute surrounds *why* the Śivasūtras are ordered as they are.
**Kiparsky** (1991) argues economy plus a principle of restrictiveness makes
Pāṇini's order essentially unique; **Staal** and **Cardona** hold that additional
phonetic principles must be doing work; **Petersen** (2008) counts ~12 million
equally-minimal arrangements absent restrictiveness. And the questions are
ancient: **Kātyāyana and Patañjali** already debated details of the arrangement —
the order of the sounds in *ha ya va ra Ṭ*, the necessity of listing `ḷ`, the
re-use of the marker `Ṇ`.

This file contributes the checkable core: for **every adjacent transposition of
two sounds within a line** (29 junctures), a kernel verdict on whether the 43
attested classes survive — a class survives if *some* well-formed pratyāhāra
still denotes it, possibly re-spelled. The result is a complete **forced/free
map** of the within-line order:

* **11 junctures are forced** — the class family itself pins the order:
  `a‑i, i‑u, h‑y, y‑v, v‑r, ñ‑m, m‑ṅ, jh‑bh, j‑b, ph‑ch, th‑c`.
  In particular the kernel settles Patañjali's *ha ya va ra* question: no two
  of `h y v r` may be interchanged.
* **18 junctures are free** — economy is silent, and phonetics or tradition
  must be what decides: `ṛ‑ḷ, e‑o, ai‑au, ṅ‑ṇ, ṇ‑n, gh‑ḍh, ḍh‑dh, b‑g, g‑ḍ,
  ḍ‑d, kh‑ph, ch‑ṭh, ṭh‑th, c‑ṭ, ṭ‑t, k‑p, ś‑ṣ, ṣ‑s`.
  Strikingly, `e‑o` and `ai‑au` are free: swapping them merely re-spells `eṄ`
  as "oṄ" and `aiC` as "auC" — the short-before-long and e-before-o
  conventions are phonetic/traditional choices, exactly Staal's point; while
  the attested-class boundaries (`ph‑ch`, `th‑c`, …) are forced, exactly
  Kiparsky's.

So neither side of the dispute holds outright: **the class family determines
the order at 11 of the 29 within-line junctures and leaves 18 to other
principles** — a quantitative, kernel-checked answer.

Method: a *forced* verdict is a witness class plus an exhaustive kernel search
over all 588 candidate encodings of the swapped alphabet (as in
`Necessity.lean`); a *free* verdict exhibits, for each of the 43 classes, an
explicit well-formed pratyāhāra of the swapped alphabet, each replayed by
`decide`.
-/

set_option maxRecDepth 65536

namespace Panini

open Sound Marker

/-- Swap the items at positions `k` and `k+1`. -/
def swapAdj (A : SAlphabet) (k : ℕ) : SAlphabet :=
  A.take k ++ (match A.drop k with
    | itm1 :: itm2 :: rest => itm2 :: itm1 :: rest
    | tail => tail)

/-- Swapping is a rearrangement: membership is preserved. -/
theorem mem_swapAdj {A : SAlphabet} (k : ℕ) {x : Item} (hx : x ∈ A) :
    x ∈ swapAdj A k := by
  unfold swapAdj
  rw [← List.take_append_drop k A] at hx
  rcases List.mem_append.mp hx with hmem | hmem
  · exact List.mem_append.mpr (Or.inl hmem)
  · refine List.mem_append.mpr (Or.inr ?_)
    cases hd : A.drop k with
    | nil => rw [hd] at hmem; simp at hmem
    | cons itm1 tl =>
      cases tl with
      | nil => rw [hd] at hmem; simpa using hmem
      | cons itm2 rest =>
        rw [hd] at hmem
        simp only [List.mem_cons] at hmem ⊢
        tauto

/-! ## Item positions
`0:a 1:i 2:u 3:Ṇ 4:ṛ 5:ḷ 6:K 7:e 8:o 9:Ṅ 10:ai 11:au 12:C 13:h 14:y 15:v 16:r
17:Ṭ 18:l 19:Ṇ 20:ñ 21:m 22:ṅ 23:ṇ 24:n 25:M 26:jh 27:bh 28:Ñ 29:gh 30:ḍh
31:dh 32:Ṣ 33:j 34:b 35:g 36:ḍ 37:d 38:Ś 39:kh 40:ph 41:ch 42:ṭh 43:th 44:c
45:ṭ 46:t 47:V 48:k 49:p 50:Y 51:ś 52:ṣ 53:s 54:R 55:h 56:L` -/

/-! ## The 11 forced junctures -/

/-- `a‑i` is **forced**: swapped, `iK` = {i u ṛ ḷ} dies. -/
theorem swap_a_i_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 0) paniniClasses :=
  not_SAlphabetT_of_witness (C := iK) (by decide +kernel) (by decide +kernel)

/-- `i‑u` is **forced**: swapped, `uK` = {u ṛ ḷ} dies. -/
theorem swap_i_u_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 1) paniniClasses :=
  not_SAlphabetT_of_witness (C := uK) (by decide +kernel) (by decide +kernel)

/-- `h‑y` is **forced**: swapped, `yaR` (consonants minus `h`) dies. -/
theorem swap_h_y_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 13) paniniClasses :=
  not_SAlphabetT_of_witness (C := yaR) (by decide +kernel) (by decide +kernel)

/-- `y‑v` is **forced**: swapped, `vaL` (consonants minus `y`) dies. -/
theorem swap_y_v_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 14) paniniClasses :=
  not_SAlphabetT_of_witness (C := vaL) (by decide +kernel) (by decide +kernel)

/-- `v‑r` is **forced**: swapped, `raL` (consonants minus `y v`) dies — with the previous two, Patañjali's *ha ya va ra* order is fully pinned. -/
theorem swap_v_r_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 15) paniniClasses :=
  not_SAlphabetT_of_witness (C := raL) (by decide +kernel) (by decide +kernel)

/-- `ñ‑m` is **forced**: swapped, `maY` dies. -/
theorem swap_ny_m_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 20) paniniClasses :=
  not_SAlphabetT_of_witness (C := maY) (by decide +kernel) (by decide +kernel)

/-- `m‑ṅ` is **forced**: swapped, `ṅaM` dies. -/
theorem swap_m_ng_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 21) paniniClasses :=
  not_SAlphabetT_of_witness (C := ngaM) (by decide +kernel) (by decide +kernel)

/-- `jh‑bh` is **forced**: swapped, `bhaṢ` dies. -/
theorem swap_jh_bh_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 26) paniniClasses :=
  not_SAlphabetT_of_witness (C := bhaSh) (by decide +kernel) (by decide +kernel)

/-- `j‑b` is **forced**: swapped, `baŚ` dies. -/
theorem swap_j_b_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 33) paniniClasses :=
  not_SAlphabetT_of_witness (C := baSx) (by decide +kernel) (by decide +kernel)

/-- `ph‑ch` is **forced**: swapped, `chaV` dies — an attested-class boundary. -/
theorem swap_ph_ch_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 40) paniniClasses :=
  not_SAlphabetT_of_witness (C := chaV) (by decide +kernel) (by decide +kernel)

/-- `th‑c` is **forced**: swapped, `caY` dies — the other class boundary. -/
theorem swap_th_c_breaks : ¬ IsSAlphabetT (swapAdj shivasutras 43) paniniClasses :=
  not_SAlphabetT_of_witness (C := caY) (by decide +kernel) (by decide +kernel)

/-! ## The 18 free junctures -/

/-- `ṛ‑ḷ` is **free**: no attested class starts at `ṛ` or `ḷ` or separates them. -/
theorem swap_r_l_free : IsSAlphabetT (swapAdj shivasutras 4) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `e‑o` is **free**: `eṄ` and `eC` survive re-spelled from `o` — that *e* comes first is convention, not necessity. -/
theorem swap_e_o_free : IsSAlphabetT (swapAdj shivasutras 7) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨o, .Ng, by decide, by decide⟩
  · exact ⟨o, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ai‑au` is **free**: `aiC` survives re-spelled \"auC\". -/
theorem swap_ai_au_free : IsSAlphabetT (swapAdj shivasutras 10) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨au, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ṅ‑ṇ` is **free**: `ṅaM` survives re-spelled \"ṇaM\". -/
theorem swap_ng_nr_free : IsSAlphabetT (swapAdj shivasutras 22) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nretro, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ṇ‑n` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_nr_n_free : IsSAlphabetT (swapAdj shivasutras 23) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `gh‑ḍh` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_gh_ddh_free : IsSAlphabetT (swapAdj shivasutras 29) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ḍh‑dh` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_ddh_dh_free : IsSAlphabetT (swapAdj shivasutras 30) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `b‑g` is **free**: `baŚ` survives re-spelled \"gaŚ\". -/
theorem swap_b_g_free : IsSAlphabetT (swapAdj shivasutras 34) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ga, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `g‑ḍ` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_g_dd_free : IsSAlphabetT (swapAdj shivasutras 35) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ḍ‑d` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_dd_d_free : IsSAlphabetT (swapAdj shivasutras 36) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `kh‑ph` is **free**: `khaR`/`khaY` survive re-spelled from `ph`. -/
theorem swap_kh_ph_free : IsSAlphabetT (swapAdj shivasutras 39) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨pha, .R, by decide, by decide⟩
  · exact ⟨pha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ch‑ṭh` is **free**: `chaV` survives re-spelled \"ṭhaV\". -/
theorem swap_ch_tth_free : IsSAlphabetT (swapAdj shivasutras 41) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨ttha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ṭh‑th` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_tth_th_free : IsSAlphabetT (swapAdj shivasutras 42) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `c‑ṭ` is **free**: `caY`/`caR` survive re-spelled from `ṭ`. -/
theorem swap_c_tt_free : IsSAlphabetT (swapAdj shivasutras 44) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨tta, .Y, by decide, by decide⟩
  · exact ⟨tta, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ṭ‑t` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_tt_t_free : IsSAlphabetT (swapAdj shivasutras 45) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `k‑p` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_k_p_free : IsSAlphabetT (swapAdj shivasutras 48) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

/-- `ś‑ṣ` is **free**: `śaL`/`śaR` survive re-spelled from `ṣ`. -/
theorem swap_sh_ss_free : IsSAlphabetT (swapAdj shivasutras 51) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨ssa, .L, by decide, by decide⟩
  · exact ⟨ssa, .R, by decide, by decide⟩

/-- `ṣ‑s` is **free**: Pāṇini's own spellings survive verbatim. -/
theorem swap_ss_s_free : IsSAlphabetT (swapAdj shivasutras 52) paniniClasses := by
  refine ⟨?_, fun s => mem_swapAdj _ (shivasutra_isSAlphabetT.2 s)⟩
  intro C hC
  simp only [paniniClasses, Finset.mem_insert, Finset.mem_singleton] at hC
  rcases hC with rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl|rfl
  · exact ⟨a, .N1, by decide, by decide⟩
  · exact ⟨a, .K, by decide, by decide⟩
  · exact ⟨a, .C, by decide, by decide⟩
  · exact ⟨a, .T1, by decide, by decide⟩
  · exact ⟨a, .N2, by decide, by decide⟩
  · exact ⟨a, .M, by decide, by decide⟩
  · exact ⟨a, .Sx, by decide, by decide⟩
  · exact ⟨a, .L, by decide, by decide⟩
  · exact ⟨i, .K, by decide, by decide⟩
  · exact ⟨i, .C, by decide, by decide⟩
  · exact ⟨i, .N2, by decide, by decide⟩
  · exact ⟨u, .K, by decide, by decide⟩
  · exact ⟨e, .Ng, by decide, by decide⟩
  · exact ⟨e, .C, by decide, by decide⟩
  · exact ⟨ai, .C, by decide, by decide⟩
  · exact ⟨h, .L, by decide, by decide⟩
  · exact ⟨h, .Sx, by decide, by decide⟩
  · exact ⟨y, .R, by decide, by decide⟩
  · exact ⟨y, .Y, by decide, by decide⟩
  · exact ⟨y, .Ny, by decide, by decide⟩
  · exact ⟨y, .M, by decide, by decide⟩
  · exact ⟨y, .N2, by decide, by decide⟩
  · exact ⟨v, .L, by decide, by decide⟩
  · exact ⟨v, .Sx, by decide, by decide⟩
  · exact ⟨r, .L, by decide, by decide⟩
  · exact ⟨nya, .M, by decide, by decide⟩
  · exact ⟨ma, .Y, by decide, by decide⟩
  · exact ⟨nga, .M, by decide, by decide⟩
  · exact ⟨jha, .L, by decide, by decide⟩
  · exact ⟨jha, .R, by decide, by decide⟩
  · exact ⟨jha, .Y, by decide, by decide⟩
  · exact ⟨jha, .Sx, by decide, by decide⟩
  · exact ⟨jha, .Sh, by decide, by decide⟩
  · exact ⟨bha, .Sh, by decide, by decide⟩
  · exact ⟨ja, .Sx, by decide, by decide⟩
  · exact ⟨ba, .Sx, by decide, by decide⟩
  · exact ⟨kha, .R, by decide, by decide⟩
  · exact ⟨kha, .Y, by decide, by decide⟩
  · exact ⟨cha, .V, by decide, by decide⟩
  · exact ⟨ca, .Y, by decide, by decide⟩
  · exact ⟨ca, .R, by decide, by decide⟩
  · exact ⟨sha, .L, by decide, by decide⟩
  · exact ⟨sha, .R, by decide, by decide⟩

end Panini
