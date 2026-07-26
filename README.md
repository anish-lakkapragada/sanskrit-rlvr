# finetune/vidyut-prakriya

Scaffold branch for vidyut-prakriya experiments. Created as an orphan branch:
no shared history with main, containing only this README.

## Morphological axes: dhātu → finite verb in vidyut-prakriya

[vidyut-prakriya](https://github.com/ambuda-org/vidyut/tree/main/vidyut-prakriya)
is a Pāṇinian word generator: give it a dhātu (verbal root) plus a set of
morphological coordinates, and it derives every grammatically valid surface
form, each with a step-by-step derivation (prakriyā) citing Aṣṭādhyāyī rules.
This section enumerates **every axis the generator accepts for finite verbs
(tiṅantas)** — i.e. the full cartesian product of morphological permutations
per root.

### Input: the Dhātupāṭha TSV

[data/finetune/vidyut_dhatupatha_5.tsv](data/finetune/vidyut_dhatupatha_5.tsv)
is vidyut's Dhātupāṭha
([upstream copy](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/data/dhatupatha.tsv)):
2,259 rows covering all 10 gaṇas (30 rows are `-` placeholders — skip them).
Columns:

| column  | meaning | example |
|---------|---------|---------|
| `code`  | `gaṇa.index` — verb class (01–10) + position in that class | `01.0005` |
| `dhatu` | the root in *aupadeśika* (citation) form, SLP1-encoded, **with anubandhas** | `bADf~\` |
| `artha` | traditional meaning gloss (Sanskrit, locative) | `loqane, rowane` |

The `dhatu` strings must be passed **as-is, markers included**: `~` (nasal
it-vowel), `\` (anudātta), `^` (svarita), and letter-its (`Yi`, `wu`, `qu`
prefixes; `N Y w p z r x` finals) are metadata that the engine's
[it-saṃjñā rules](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/it_samjna.rs)
read (e.g. `\` on an it-vowel ⇒ ātmanepada; on the root vowel ⇒ aniṭ
behavior) and then delete. Stripping them yourself produces wrong forms.
Validation rules for the encoding live in
[`Slp1String`](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/args/slp1_string.rs).
Build the dhātu with
[`dhatupatha::create_dhatu(aupadeshika, gana, number)`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/dhatupatha/fn.create_dhatu.html)
(see [src/dhatupatha.rs](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/dhatupatha.rs)) —
it needs the row *number* to infer the antargaṇa, which plain
`Dhatu::mula(text, gana)` cannot know.

### Axis 1 — the dhātu itself ([`Dhatu`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Dhatu.html), [src/args/dhatu.rs](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/args/dhatu.rs))

| parameter | choices | notes |
|-----------|--------:|-------|
| [`Gana`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Gana.html) | **11** | the 10 classical classes (bhvādi … curādi) + `Kandvadi`; decides the present-stem affix (bhū→*bhava-*, tud→*tuda-*, rudh→*ruṇadh-* …); comes from the `code` column, not the root string |
| [`Antargana`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Antargana.html) | **5** (or none) | sub-lists with special behavior (`Ghatadi`, `Kutadi`, `Asvadiya`, `Adhrshiya`, `Akusmiya`); inferred from the row number |
| [`Sanadi`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Sanadi.html) stack | **5** verb-applicable (none, `san` desiderative, `Ric` causative, `yaN` intensive, `yaNluk`), stackable (e.g. `Ric`+`san`) | `kyac`/`kAmyac`/`kyaN` build verbs from nouns, not from these dhātus; `yaN` requires consonant-initial, one-vowel roots |
| prefixes (upasargas) | open set | *anu-*, *pra-*, *sam-*, … — lexical, not enumerated here |

### Axis 2 — the tiṅanta coordinates ([`Tinanta`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/struct.Tinanta.html), [src/args/tin.rs](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/args/tin.rs))

| parameter | choices | values |
|-----------|--------:|--------|
| [`Lakara`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Lakara.html) (tense/mood) | **11** | `Lat` present, `Lit` perfect, `Lut` periphrastic future, `Lrt` simple future, `Let` Vedic subjunctive (weak support), `Lot` imperative, `Lan` imperfect, `VidhiLin` optative, `AshirLin` benedictive, `Lun` aorist, `Lrn` conditional |
| [`Prayoga`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Prayoga.html) (voice) | **3** | `Kartari` active, `Karmani` passive, `Bhave` impersonal |
| [`Purusha`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Purusha.html) (person) | **3** | `Prathama` 3rd, `Madhyama` 2nd, `Uttama` 1st |
| [`Vacana`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Vacana.html) (number) | **3** | `Eka`, `Dvi`, `Bahu` (dual!) |
| [`DhatuPada`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.DhatuPada.html) (optional) | **2** | force `Parasmaipada`/`Atmanepada`; by default derived from the root's anubandhas + prayoga |
| `skip_at_agama` (optional) | bool | drop the past-tense *a-* augment (for *mā*-constructions) |

### The cartesian product

Per root, the queryable finite grid is:

```text
11 lakāras × 3 prayogas × 3 puruṣas × 3 vacanas             =   297 cells
practical (skip Let):  10 × 3 × 3 × 3                        =   270 cells
× 5 single sanādi choices (none/san/Ric/yaN/yaNluk)          = 1,350 cells
× 2,229 usable roots in the TSV                              ≈ 3.0 M cells
```

Sanādi *stacks* (`Ric+san`, `san+Ric`, …), upasarga prefixes, and forcing
`DhatuPada` (×2) multiply further. Note the grid is an **upper bound of
queries, not of words**:
[`Vyakarana::derive_tinantas`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/struct.Vyakarana.html)
returns a `Vec<Prakriya>` per cell — zero (cell doesn't exist for that
root), one, or several (optional forms are all derived).

```rust
use vidyut_prakriya::{Vyakarana, args::*, dhatupatha};

let v = Vyakarana::new();
let dhatu = dhatupatha::create_dhatu("bADf~\\", Gana::Bhvadi, 5)?; // row 01.0005
let args = Tinanta::builder()
    .dhatu(dhatu)
    .lakara(Lakara::Lat)         // 1 of 11
    .prayoga(Prayoga::Kartari)   // 1 of 3
    .purusha(Purusha::Prathama)  // 1 of 3
    .vacana(Vacana::Eka)         // 1 of 3
    .build()?;
for p in v.derive_tinantas(&args) {
    println!("{}", p.text());    // -> bADate
}
```

Reference documentation: [docs.rs API](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/)
· [args module (all enums)](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/index.html)
· [repo README with usage & CLI](https://github.com/ambuda-org/vidyut/tree/main/vidyut-prakriya)
· [ISCLS 2024 paper](https://iscls.github.io/assets/files/proceedings/2024.iscls.7.pdf)

## Getting back to main with all your files visible

This branch keeps an empty working tree. Main's untracked & gitignored working
files (`.env`, `runs/`, `results/`, `data/` caches, `Cargo.toml`, `src/`, …)
are parked in `../sanskrit-main-files/` — moved by same-disk rename, nothing
copied or deleted.

To switch back and restore everything:

```bash
git checkout main
bash ../sanskrit-main-files/sync-main-files.sh restore
```

If `git stash list` shows `main WIP: gitignore /target (cargo)`, also run
`git stash pop` to recover the uncommitted `.gitignore` edit.

To come back to this branch with a clean tree:

```bash
git checkout finetune/vidyut-prakriya
bash ../sanskrit-main-files/sync-main-files.sh park
```

### Optional: automate both directions

Install the sync script as a git hook and every branch switch handles the
files automatically:

```bash
cp ../sanskrit-main-files/sync-main-files.sh .git/hooks/post-checkout
chmod +x .git/hooks/post-checkout
```

Caveat: with the hook installed, commit your work on this branch before
switching away — anything left untracked here is treated as main's and gets
parked in `../sanskrit-main-files/` on your next visit.
