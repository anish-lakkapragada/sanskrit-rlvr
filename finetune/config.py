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
    lora: LoraSettings = field(default_factory=LoraSettings)


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


@dataclass
class RunConfig:
    run_name: str = ""
    model: str = "gemma3-12b"
    reward: str = "example"
    dataset: str = "data/finetune/finetune.json"  # 6,018 training tasks
    eval_dataset: str = "data/finetune/validation.json"  # Pass@K prompt source (held-out dhatus)
    iterations: int = 1000
    checkpoint_every: int = 100
    logging_every: int = 10
    seed: int = 42
    pass_at_k: PassAtKConfig = field(default_factory=PassAtKConfig)
    samayik_eval: SamayikEvalConfig = field(default_factory=SamayikEvalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    vllm: VllmConfig = field(default_factory=VllmConfig)

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
    longest_gen = max(cfg.generation.max_completion_length,
                      cfg.samayik_eval.max_new_tokens)
    if cfg.vllm.max_model_length <= longest_gen:
        problems.append(
            f"vllm.max_model_length ({cfg.vllm.max_model_length}) must leave room "
            f"for the prompt on top of the longest generation ({longest_gen})")

    from finetune import rewards
    try:
        rewards.get(cfg.reward)
    except KeyError as e:
        problems.append(str(e))

    if problems:
        raise ValueError(f"invalid config {path}:\n  - " + "\n  - ".join(problems))
    return cfg
