# finetune/vidyut-prakriya

Scaffold branch for vidyut-prakriya experiments. Created as an orphan branch:
no shared history with main, containing only this README.

## Task space: random dhātu × random tiṅanta coordinates

Goal: build a dataset of tasks of the form **(dhātu, tiṅanta coordinates) →
inflected verb form**, where every task is machine-checkable by calling
[vidyut-prakriya](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/), a
Pāṇinian generator that derives all grammatically valid forms for a given
coordinate tuple. The dhātu is *sampled* from the Dhātupāṭha TSV; the
coordinates are the axes we actually vary.

### The dhātu pool

[data/finetune/vidyut_dhatupatha_5.tsv](data/finetune/vidyut_dhatupatha_5.tsv)
is vidyut's Dhātupāṭha
([upstream](https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/data/dhatupatha.tsv)):
2,259 rows across all 10 gaṇas; 30 rows are `-` placeholders, leaving **2,229
usable roots**.

| column  | meaning | example |
|---------|---------|---------|
| `code`  | `gaṇa.index` — verb class (01–10) + position in that class | `01.0005` |
| `dhatu` | root in *aupadeśika* (citation) form, SLP1, **with anubandha markers** | `bADf~\` |
| `artha` | traditional meaning gloss (Sanskrit, locative case) | `loqane, rowane` |

Rules for consuming it:

- Pass the `dhatu` string **exactly as written** — the markers (`~`, `\`, `^`,
  and letter-its like `Yi`/`wu`/`qu`) encode voice and derivational behavior
  and are consumed, then deleted, by the engine. See
  [`Slp1String`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/struct.Slp1String.html)
  for the exact accepted encoding.
- The gaṇa comes from the `code` column (`01` →
  [`Gana::Bhvadi`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Gana.html), …),
  not from the root string — the same string can appear in several gaṇas as
  different verbs (`BU` appears three times).
- Load entries with the official loaders rather than `Dhatu.mula` alone: the
  row *number* determines the
  [`Antargana`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Antargana.html)
  (sub-class metadata some roots need to derive correctly). In Rust that is
  [`dhatupatha::create_dhatu`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/dhatupatha/fn.create_dhatu.html)
  (module docs: [`dhatupatha`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/dhatupatha/index.html));
  in Python, `Data.load_dhatu_entries()` (see the
  [Python prakriya docs](https://vidyut.readthedocs.io/en/latest/prakriya.html)).
- Held constant (defaults) for this dataset:
  [`Sanadi`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Sanadi.html)
  stack empty (no causatives/desideratives/intensives) and no upasarga
  prefixes. Both are extension axes for later.

### The coordinate axes (what a task varies)

All from the [`args` module](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/index.html);
a task is one choice from each row:

| axis | choices | values |
|------|--------:|--------|
| [`Lakara`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Lakara.html) (tense/mood) | **10** practical (11 with Vedic `Let`, which has weak support) | `Lat` present · `Lit` perfect · `Lut` periphrastic future · `Lrt` simple future · `Lot` imperative · `Lan` imperfect · `VidhiLin` optative · `AshirLin` benedictive · `Lun` aorist · `Lrn` conditional |
| [`Prayoga`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Prayoga.html) (voice) | **3** | `Kartari` active · `Karmani` passive · `Bhave` impersonal |
| [`Purusha`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Purusha.html) (person) | **3** | `Prathama` 3rd · `Madhyama` 2nd · `Uttama` 1st |
| [`Vacana`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Vacana.html) (number) | **3** | `Eka` singular · `Dvi` dual · `Bahu` plural |
| [`DhatuPada`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.DhatuPada.html) (optional) | **2** or unset | leave unset: the engine derives parasmaipada/ātmanepada from the root's anubandhas |

### Size of the space

```text
10 lakāras × 3 prayogas × 3 puruṣas × 3 vacanas =    270 cells per root
× 2,229 usable roots                            ≈ 601,830 candidate tasks
```

Each cell yields **0..n** valid forms
([`Vyakarana::derive_tinantas`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/struct.Vyakarana.html)
returns a list of derivations): 0 means the cell doesn't exist for that root
(drop it at generation time); >1 means several forms are all correct (a task
has a *set* of gold answers, not one).

### Verifying a task (the oracle call)

Python ([`vidyut` on PyPI](https://pypi.org/project/vidyut/),
[prakriya docs](https://vidyut.readthedocs.io/en/latest/prakriya.html)):

```python
from vidyut.prakriya import (
    Vyakarana, Dhatu, Gana, Pada, Prayoga, Purusha, Vacana, Lakara,
)

v = Vyakarana()
prakriyas = v.derive(Pada.Tinanta(
    dhatu=Dhatu.mula(aupadeshika="bADf~\\", gana=Gana.Bhvadi),
    prayoga=Prayoga.Kartari,
    lakara=Lakara.Lat,
    purusha=Purusha.Prathama,
    vacana=Vacana.Eka,
))
gold = {p.text for p in prakriyas}   # {'bADate'} — check model output ∈ gold
```

The Rust equivalent is
[`Tinanta::builder()`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/struct.Tinanta.html)
→ [`Vyakarana::derive_tinantas`](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/struct.Vyakarana.html).

Further reading: [docs.rs API](https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/)
· [Python docs](https://vidyut.readthedocs.io/en/latest/)
· [ISCLS 2024 paper](https://iscls.github.io/assets/files/proceedings/2024.iscls.7.pdf)
· [project README](https://github.com/ambuda-org/vidyut/tree/main/vidyut-prakriya)

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
