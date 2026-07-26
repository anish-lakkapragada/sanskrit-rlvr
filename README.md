# finetune/vidyut-prakriya

Scaffold branch for vidyut-prakriya experiments. Created as an orphan branch:
no shared history with main, containing only this README.

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
