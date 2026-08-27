"""YAML run-config loading and validation. No heavy (GPU) imports here."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class PassAtKConfig:
    ks: list[int] = field(default_factory=lambda: [1, 4, 8])
    num_prompts: int = 128
    samples_per_prompt: int = 8
    pass_threshold: float = 0.5
    temperature: float = 0.9


@dataclass
class SamayikEvalConfig:
    path: str = "data/eval/samayik.json"
    num_samples: int = 200
    max_new_tokens: int = 512
    temperature: float = 0.2


@dataclass
class GenerationConfig:
    num_generations: int = 8
    max_completion_length: int = 256
    temperature: float = 0.9


@dataclass
class SFTSettings:
    """LoRA SFT on a distilled trace corpus (finetune.sft). Defaults follow
    the LoRA-Without-Regret / TRL guidance: lr ~10x full-FT with cosine +
    short warmup, effective batch < 32, completion-only loss."""
    dataset: str = "data/finetune/sft-r1/claude-opus-5.json"
    prompt_template: str = "v1/vp_task_eval.txt"  # template the corpus was generated with
    epochs: float = 2.0
    max_steps: int = 0        # >0 OVERRIDES epochs: a fixed compute budget, so arms
                              # with different corpus sizes stay compute-matched
    val_datasets: dict = field(default_factory=dict)  # name -> path; each gets its own
                              # eval_<name>_loss curve (completion-only, same as train)
    eval_every: int = 0       # steps between validation passes (0 = no validation)
    save_every: int = 0       # steps between checkpoints (0 = save once per epoch)
    learning_rate: float = 2.0e-4
    per_device_train_batch_size: int = 4
    gradient_accumulation_steps: int = 4          # effective batch 16
    max_seq_len: int = 4096   # student tokenizer is less dense on Devanagari
                              # than the teacher's; over-length pairs are dropped
    warmup_ratio: float = 0.05
    weight_decay: float = 0.01
    lr_scheduler: str = "cosine"
    eval_prompts_per_epoch: int = 16              # 0 disables the per-epoch eval
    eval_samples_per_prompt: int = 4
    eval_max_new_tokens: int = 1024


@dataclass
class LoraSettings:
    r: int = 16
    alpha: int = 32
    dropout: float = 0.05


@dataclass
class TrainConfig:
    learning_rate: float = 1.0e-5
    per_device_train_batch_size: int = 4
    gradient_accumulation_steps: int = 1
    beta: float = 0.04
    bf16: bool = True
    gradient_checkpointing: bool = True
    quantization: str = "none"  # none | 4bit
    # GRPO round-1 audit: GRPOConfig previously got no scheduler args, so HF's
    # default LINEAR DECAY TO ZERO applied silently (last ~100 steps a no-op).
    lr_scheduler: str = "constant_with_warmup"
    warmup_ratio: float = 0.03
    # Teacher-forced completion-NLL probes (name -> path, SFT-schema records),
    # computed at every checkpoint eval when val_loss_every > 0. Drift
    # diagnostics ONLY: on the dhatu task val loss anti-predicts pass@1.
    val_datasets: dict = field(default_factory=dict)
    val_loss_every: int = 0
    lora: LoraSettings = field(default_factory=LoraSettings)


@dataclass
class SDPOSettings:
    """Self-Distillation Policy Optimization (pure: no GRPO advantage mixing).

    The student generates rollouts from the plain prompt; the SAME model
    re-scores each rollout (teacher-forced, no decoding) under the prompt +
    the task's privileged reference block; the loss is a per-token KL between
    the two distributions over completion tokens only."""
    # dataset records must carry `privileged_block` (built by
    # misc/data/make_sdpo_data.py, which EXCLUDES over-budget tasks and
    # reports the exclusion percentage).
    privileged_budget: int = 512     # documentation of the build-time budget
    kl_direction: str = "forward"    # forward = KL(teacher || student) | reverse
    kl_temperature: float = 1.0
    # Max per-token KL contribution to the loss (nats); 0 disables. Bounds
    # structural-token outliers that otherwise dominate the gradient.
    kl_clamp: float = 3.0
    thinking_block_weight: float = 1.0
    answer_block_weight: float = 2.0
    skip_all_correct: bool = True    # groups where every rollout passes: no update
    gate_threshold: float = 0.85     # vp_exact pass level used for the gate
    # Distill on at most this many rollouts per step, failed-first (correct
    # rollouts carry ~zero KL; scoring all n would double step time for
    # little signal).
    max_distill_rollouts: int = 4
    weight_sync_every: int = 1       # steps between policy pushes into vLLM
    logits_chunk: int = 512          # sequence-chunk size for full-vocab KL (memory)
    warmup_ratio: float = 0.03
    lr_scheduler: str = "constant_with_warmup"
    grad_clip: float = 1.0
    weight_decay: float = 0.0


@dataclass
class VllmConfig:
    mode: str = "colocate"  # colocate | server
    gpu_memory_utilization: float = 0.4
    # Gemma-3 advertises a 131k window; vLLM sizes its KV cache to fit one
    # request at that length and refuses to start if it can't. Our prompts are
    # ~250 tokens and completions <=512, so cap it and reclaim the memory.
    max_model_length: int = 2048
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    # NCCL weight-sync rendezvous port (server mode). Two trainer/server pairs
    # on one box MUST use distinct values — the client dictates it to the server.
    group_port: int = 51216


@dataclass
class RunConfig:
    run_name: str = ""
    model: str = "gemma3-12b"
    reward: str = "example"
    # Reward used to SCORE the checkpoint pass@k probe ("" = use `reward`).
    # Set this when the training reward is shaped (vp_chrf/vp_chrfpp): under a
    # 0.85 threshold those score a near-miss as a pass, so probe curves would
    # not be comparable across arms nor to the reported vp_exact numbers.
    eval_reward: str = ""
    # GRPO rollout/eval prompt template. Runs starting from an SFT checkpoint
    # must use the template the student was trained on (v1/vp_task_eval.txt).
    prompt_template: str = "v0/vp_task.txt"
    dataset: str = "data/finetune/task-data/finetune.json"  # 6,018 training tasks
    eval_dataset: str = "data/finetune/task-data/validation.json"  # Pass@K prompt source (held-out dhatus)
    iterations: int = 1000
    checkpoint_every: int = 100
    logging_every: int = 10
    seed: int = 42
    pass_at_k: PassAtKConfig = field(default_factory=PassAtKConfig)
    samayik_eval: SamayikEvalConfig = field(default_factory=SamayikEvalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    vllm: VllmConfig = field(default_factory=VllmConfig)
    sft: SFTSettings = field(default_factory=SFTSettings)
    sdpo: SDPOSettings = field(default_factory=SDPOSettings)

    @property
    def run_dir(self) -> Path:
        return ROOT / "runs" / self.run_name


def _build(cls, data: dict, path: str):
    """Construct a dataclass from a dict, recursing into nested dataclasses
    and rejecting unknown keys (typos in YAML should fail loudly)."""
    fields = {f.name: f for f in cls.__dataclass_fields__.values()}
    unknown = set(data) - set(fields)
    if unknown:
        raise ValueError(f"unknown config key(s) at {path}: {sorted(unknown)}")
    kwargs = {}
    for key, value in data.items():
        ftype = fields[key].type
        nested = {
            "PassAtKConfig": PassAtKConfig, "SamayikEvalConfig": SamayikEvalConfig,
            "GenerationConfig": GenerationConfig, "TrainConfig": TrainConfig,
            "VllmConfig": VllmConfig, "LoraSettings": LoraSettings,
            "SFTSettings": SFTSettings, "SDPOSettings": SDPOSettings,
        }.get(ftype if isinstance(ftype, str) else getattr(ftype, "__name__", ""))
        kwargs[key] = _build(nested, value, f"{path}.{key}") if nested else value
    return cls(**kwargs)


def load_config(path: str | Path) -> RunConfig:
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: config must be a YAML mapping")
    cfg = _build(RunConfig, raw, "config")

    # -- validation ---------------------------------------------------------
    problems = []
    if not cfg.run_name:
        problems.append("run_name is required")
    if not (ROOT / cfg.dataset).exists():
        problems.append(f"dataset not found: {cfg.dataset}")
    if not (ROOT / cfg.eval_dataset).exists():
        problems.append(f"eval_dataset not found: {cfg.eval_dataset}")
    if not (ROOT / cfg.samayik_eval.path).exists():
        problems.append(f"samayik eval file not found: {cfg.samayik_eval.path}")
    if cfg.checkpoint_every > cfg.iterations:
        problems.append("checkpoint_every must be <= iterations")
    if max(cfg.pass_at_k.ks) > cfg.pass_at_k.samples_per_prompt:
        problems.append("max(pass_at_k.ks) must be <= samples_per_prompt")
    if cfg.train.quantization not in ("none", "4bit"):
        problems.append("train.quantization must be 'none' or '4bit'")
    if cfg.vllm.mode not in ("colocate", "server"):
        problems.append("vllm.mode must be 'colocate' or 'server'")
    if cfg.sdpo.kl_direction not in ("forward", "reverse"):
        problems.append("sdpo.kl_direction must be 'forward' or 'reverse'")
    longest_gen = max(cfg.generation.max_completion_length,
                      cfg.samayik_eval.max_new_tokens)
    if cfg.vllm.max_model_length <= longest_gen:
        problems.append(
            f"vllm.max_model_length ({cfg.vllm.max_model_length}) must leave room "
            f"for the prompt on top of the longest generation ({longest_gen})")

    from finetune import rewards
    for name in filter(None, (cfg.reward, cfg.eval_reward)):
        try:
            rewards.get(name)
        except KeyError as e:
            problems.append(str(e))

    if problems:
        raise ValueError(f"invalid config {path}:\n  - " + "\n  - ".join(problems))
    return cfg
