"""The experiment orchestrator.

    python -m finetune.train finetune/configs/<name>.yaml

Reads one YAML config → runs the training backend → evaluates every
checkpoint (compile-rate + chrF++ on the config's eval prompts) → leaves a
complete, self-describing runs/<run_name>/ directory. See
finetune/configs/example.yaml for the schema.
"""

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from .common import (ROOT, RUNS, eval_benchmarks_mlx, read_jsonl,
                     record_eval_point)


def fail(msg: str):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_config(path: Path) -> dict:
    cfg = yaml.safe_load(path.read_text())
    if cfg.get("backend") not in ("mlx", "cuda"):
        fail(f"backend must be 'mlx' or 'cuda' (got {cfg.get('backend')!r})")
    if cfg.get("mode") not in ("sft", "grpo"):
        fail(f"mode must be 'sft' or 'grpo' (got {cfg.get('mode')!r})")
    for k in ("run_name", "model", "data", "hyperparameters", "eval"):
        if k not in cfg:
            fail(f"config missing required key: {k}")
    ev = cfg["eval"]
    # legacy schema: a single `prompts` file and `checkpoints: N` cadence
    if "benchmarks" not in ev:
        if "prompts" not in ev:
            fail("eval needs `benchmarks: {group: file}` (or legacy `prompts`)")
        ev["benchmarks"] = {"in_fragment": ev["prompts"]}
    if "samples" not in ev and "samples_per_checkpoint" in ev:
        ev["samples"] = ev["samples_per_checkpoint"]
    return cfg


def resolve_base_model(cfg: dict, run_dir: Path) -> str:
    """The SFT→GRPO handoff. cuda: the source run's final full-model
    checkpoint simply becomes this run's base (bf16, lossless). mlx: fuse
    that run's final adapter into its base and re-quantize to 4-bit (the
    18 GB compromise — the quantization cost is measured and recorded in
    metrics.jsonl)."""
    src_name = cfg["model"].get("init_from_run")
    if not src_name:
        return cfg["model"]["base"]
    src = RUNS / src_name
    if cfg["backend"] == "cuda":
        src_cfg = yaml.safe_load((src / "config.yaml").read_text())
        final = Path(src_cfg["model"].get("final_checkpoint")
                     or src / "checkpoints" / "final")
        if not final.is_absolute():
            final = ROOT / final
        if not (final / "config.json").exists():
            fail(f"init_from_run: {final} is not a full model checkpoint "
                 "(cuda runs must init from a completed cuda SFT run)")
        return str(final)
    adapter_dir = src / "checkpoints" / "final"
    if not (adapter_dir / "adapters.safetensors").exists():
        adapter_dir = src / "checkpoints"  # runs from before the <it>/ layout
    if not (adapter_dir / "adapters.safetensors").exists():
        fail(f"init_from_run: no final adapter under runs/{src_name}/checkpoints")
    src_cfg = yaml.safe_load((src / "config.yaml").read_text())
    fused = src / "fused_4bit"
    if not (fused / "config.json").exists():
        print(f"[init] fusing runs/{src_name} adapter into its base …", flush=True)
        tmp = src / "fused_bf16"
        subprocess.run([sys.executable, "-m", "mlx_lm", "fuse",
                        "--model", src_cfg["model"]["base"],
                        "--adapter-path", str(adapter_dir),
                        "--save-path", str(tmp)], check=True)
        print("[init] re-quantizing fused model to 4-bit …", flush=True)
        subprocess.run([sys.executable, "-m", "mlx_lm", "convert",
                        "--hf-path", str(tmp), "--mlx-path", str(fused),
                        "-q"], check=True)
        shutil.rmtree(tmp, ignore_errors=True)
    return str(fused)


def organize_mlx_checkpoints(ckpt_dir: Path, iters: int) -> list[tuple[int, Path]]:
    """mlx-lm-lora writes flat files (0000100_adapters.safetensors … plus a
    final adapters.safetensors). Repackage them as checkpoints/<iteration>/
    dirs — each independently loadable — with the last at checkpoints/final,
    mirroring the cuda layout. Returns [(iteration, dir)] to evaluate."""
    adapter_cfg = ckpt_dir / "adapter_config.json"
    points = []
    for f in sorted(ckpt_dir.glob("0*_adapters.safetensors")):
        it = int(f.name.split("_")[0])
        d = ckpt_dir / str(it)
        d.mkdir(exist_ok=True)
        f.rename(d / "adapters.safetensors")
        shutil.copy(adapter_cfg, d)
        points.append((it, d))
    final = ckpt_dir / "final"
    final.mkdir(exist_ok=True)
    if (ckpt_dir / "adapters.safetensors").exists():
        (ckpt_dir / "adapters.safetensors").rename(final / "adapters.safetensors")
        shutil.copy(adapter_cfg, final)
    adapter_cfg.unlink(missing_ok=True)
    # the trainer also dumps full-model + tokenizer files at the top level;
    # they belong with the final model
    for f in list(ckpt_dir.iterdir()):
        if f.is_file():
            f.rename(final / f.name)
    if not points or points[-1][0] != iters:
        points.append((iters, final))
    return points


def backend_command(cfg: dict, base: str, run_dir: Path,
                    iters: int, save_every: int) -> list[str]:
    hp = cfg["hyperparameters"]
    if cfg["backend"] == "cuda":
        return [sys.executable, "-m", "finetune.cuda_train",
                "--config", str(run_dir / "config.yaml"), "--base", base,
                "--iters", str(iters), "--save-every", str(save_every)]
    cmd = [sys.executable, "-m", "mlx_lm_lora.train",
           "--model", base, "--train", "--train-type", "lora",
           "--data", str(ROOT / cfg["data"]["dir"]),
           "--adapter-path", str(run_dir / "checkpoints"),
           "--learning-rate", str(hp["learning_rate"]),
           "--iters", str(iters),
           "--batch-size", str(hp.get("batch_size", 1)),
           "--num-layers", str(hp.get("num_layers", 16)),
           "--max-seq-length", str(hp.get("max_seq_length", 768)),
           "--save-every", str(save_every),
           "--steps-per-report", "1", "--steps-per-eval", str(max(save_every, 100)),
           "--val-batches", "2", "--seed", "7", "--grad-checkpoint"]
    if cfg["mode"] == "sft":
        cmd += ["--train-mode", "sft", "--mask-prompt"]
    else:
        cmd += ["--train-mode", "grpo",
                "--group-size", str(hp.get("group_size", 6)),
                "--beta", str(hp.get("beta", 0.1)),
                "--temperature", str(hp.get("temperature", 0.8)),
                "--max-completion-length", str(hp.get("max_completion_length", 200)),
                "--reward-functions-file", str(ROOT / "finetune" / "rewards_shim.py"),
                "--reward-functions",
                {"lean": "lean_sanskrit_reward",
                 "chrf": "chrf_format_reward"}[hp.get("reward", "lean")]]
    return cmd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing run directory")
    args = ap.parse_args()

    cfg = load_config(args.config)
    run_dir = RUNS / cfg["run_name"]
    if run_dir.exists():
        if not args.force:
            fail(f"runs/{cfg['run_name']} already exists (use --force to replace)")
        shutil.rmtree(run_dir)
    (run_dir / "checkpoints").mkdir(parents=True)
    (run_dir / "snapshots").mkdir()
    # freeze the *normalized* config (legacy fields resolved) — it is the
    # contract the trainer subprocess, evaluate.py and the dashboard read
    (run_dir / "config.yaml").write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

    # dashboard (idempotent: one server watches all runs)
    if cfg.get("dashboard", {}).get("enabled"):
        from .dashboard import ensure_running
        ensure_running(cfg["dashboard"].get("port", 8777))

    base = resolve_base_model(cfg, run_dir)

    hp = cfg["hyperparameters"]
    if hp.get("iters"):
        iters = int(hp["iters"])
    else:
        n = sum(1 for _ in (ROOT / cfg["data"]["dir"] / "train.jsonl").open())
        iters = math.ceil(n / hp.get("batch_size", 1)) * int(hp.get("epochs", 1))
    ev = cfg["eval"]
    if ev.get("every"):  # one knob: checkpoint + full eval every N iters
        save_every = max(1, int(ev["every"]))
    else:                # legacy: N evenly spaced checkpoints
        save_every = max(1, iters // int(ev.get("checkpoints", 4)))

    benchmarks = {}
    for group, rel in ev["benchmarks"].items():
        rows = read_jsonl(ROOT / rel)
        if ev.get("samples"):
            rows = rows[: int(ev["samples"])]
        benchmarks[group] = rows
    temp = float(ev.get("temperature", 0))

    # measure the starting point (checkpoint 0 = the base this run trains
    # from). cuda runs eval inside the trainer (live, incl. checkpoint 0) —
    # the orchestrator only evaluates here for mlx.
    if cfg["backend"] == "mlx":
        print(f"[eval] baseline of {Path(base).name} …", flush=True)
        record_eval_point(run_dir, 0, "init",
                          eval_benchmarks_mlx(base, None, benchmarks, temp))

    cmd = backend_command(cfg, base, run_dir, iters, save_every)
    print(f"[train] {cfg['mode']} for {iters} iters, checkpoint every "
          f"{save_every} → runs/{cfg['run_name']}/", flush=True)
    with (run_dir / "train.log").open("w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        fail(f"training exited {r.returncode} — see runs/{cfg['run_name']}/train.log")

    # evaluate every saved checkpoint, in order, then the final one.
    # (cuda already did this live, inside the trainer, at every save)
    if cfg["backend"] == "mlx":
        points = organize_mlx_checkpoints(run_dir / "checkpoints", iters)
        for it, ckpt in points:
            print(f"[eval] checkpoint {it}/{iters} …", flush=True)
            record_eval_point(run_dir, it, "checkpoint",
                              eval_benchmarks_mlx(base, ckpt, benchmarks, temp))

    print(f"[done] runs/{cfg['run_name']}/metrics.jsonl:")
    for line in (run_dir / "metrics.jsonl").open():
        d = json.loads(line)
        i, o = d.get("in_fragment", {}), d.get("out_of_fragment", {})
        print(f"  ckpt {d['checkpoint']:>5}  "
              f"compile={i.get('compile_rate')}  "
              f"chrf++(in)={i.get('chrf_pp')}  ter(in)={i.get('ter')}  "
              f"chrf++(out)={o.get('chrf_pp')}  ter(out)={o.get('ter')}")


if __name__ == "__main__":
    main()
