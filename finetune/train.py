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
import time
from pathlib import Path

import yaml

from .common import ROOT, RUNS, append_jsonl, eval_checkpoint, read_jsonl


def fail(msg: str):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_config(path: Path) -> dict:
    cfg = yaml.safe_load(path.read_text())
    if cfg.get("backend") != "mlx":
        fail(f"backend must be 'mlx' (got {cfg.get('backend')!r}); "
             "no other backend is supported yet")
    if cfg.get("mode") not in ("sft", "grpo"):
        fail(f"mode must be 'sft' or 'grpo' (got {cfg.get('mode')!r})")
    for k in ("run_name", "model", "data", "hyperparameters", "eval"):
        if k not in cfg:
            fail(f"config missing required key: {k}")
    return cfg


def resolve_base_model(cfg: dict, run_dir: Path) -> str:
    """If init_from_run is set, fuse that run's final adapter into its base
    and re-quantize to 4-bit (the canonical SFT→GRPO handoff on 18 GB —
    the quantization cost is measured and recorded in metrics.jsonl)."""
    src_name = cfg["model"].get("init_from_run")
    if not src_name:
        return cfg["model"]["base"]
    src = RUNS / src_name
    if not (src / "checkpoints" / "adapters.safetensors").exists():
        fail(f"init_from_run: no final adapter under runs/{src_name}/checkpoints")
    src_cfg = yaml.safe_load((src / "config.yaml").read_text())
    fused = src / "fused_4bit"
    if not (fused / "config.json").exists():
        print(f"[init] fusing runs/{src_name} adapter into its base …", flush=True)
        tmp = src / "fused_bf16"
        subprocess.run([sys.executable, "-m", "mlx_lm", "fuse",
                        "--model", src_cfg["model"]["base"],
                        "--adapter-path", str(src / "checkpoints"),
                        "--save-path", str(tmp)], check=True)
        print("[init] re-quantizing fused model to 4-bit …", flush=True)
        subprocess.run([sys.executable, "-m", "mlx_lm", "convert",
                        "--hf-path", str(tmp), "--mlx-path", str(fused),
                        "-q"], check=True)
        shutil.rmtree(tmp, ignore_errors=True)
    return str(fused)


def backend_command(cfg: dict, base: str, run_dir: Path,
                    iters: int, save_every: int) -> list[str]:
    hp = cfg["hyperparameters"]
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
                "--reward-functions", "lean_sanskrit_reward"]
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
    shutil.copy(args.config, run_dir / "config.yaml")

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
    n_ckpt = int(cfg["eval"].get("checkpoints", 4))
    save_every = max(1, iters // n_ckpt)

    # measure the starting point (checkpoint 0 = the base this run trains from)
    eval_rows = read_jsonl(ROOT / cfg["eval"]["prompts"])
    eval_rows = eval_rows[: int(cfg["eval"].get("samples_per_checkpoint", 60))]
    print(f"[eval] baseline of {Path(base).name} …", flush=True)
    summary, records = eval_checkpoint(base, None, eval_rows,
                                       temp=float(cfg["eval"].get("temperature", 0)))
    append_jsonl(run_dir / "metrics.jsonl",
                 {"checkpoint": 0, "kind": "init", **summary, "t": time.time()})
    with (run_dir / "snapshots" / "checkpoint_0.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cmd = backend_command(cfg, base, run_dir, iters, save_every)
    print(f"[train] {cfg['mode']} for {iters} iters, checkpoint every "
          f"{save_every} → runs/{cfg['run_name']}/", flush=True)
    with (run_dir / "train.log").open("w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        fail(f"training exited {r.returncode} — see runs/{cfg['run_name']}/train.log")

    # evaluate every saved checkpoint, in order, then the final adapter
    ckpts = sorted((run_dir / "checkpoints").glob("0*_adapters.safetensors"))
    points = [(int(c.name.split("_")[0]), c) for c in ckpts]
    if not points or points[-1][0] != iters:
        points.append((iters, run_dir / "checkpoints" / "adapters.safetensors"))
    for it, ckpt in points:
        print(f"[eval] checkpoint {it}/{iters} …", flush=True)
        summary, records = eval_checkpoint(
            base, ckpt, eval_rows, temp=float(cfg["eval"].get("temperature", 0)))
        append_jsonl(run_dir / "metrics.jsonl",
                     {"checkpoint": it, "kind": "checkpoint", **summary,
                      "t": time.time()})
        with (run_dir / "snapshots" / f"checkpoint_{it}.jsonl").open("w") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[done] runs/{cfg['run_name']}/metrics.jsonl:")
    for line in (run_dir / "metrics.jsonl").open():
        d = json.loads(line)
        print(f"  ckpt {d['checkpoint']:>5}  compile={d['compile_rate']}  "
              f"chrf++={d['chrf_pp']}  reward={d['mean_reward']}")


if __name__ == "__main__":
    main()
