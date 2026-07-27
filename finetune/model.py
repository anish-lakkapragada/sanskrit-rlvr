"""Model presets and loading (text-only). Heavy imports stay inside functions
so config validation and --dry-run work without GPU dependencies."""

from finetune.config import RunConfig

PRESETS = {
    "gemma3-12b": "google/gemma-3-12b-it",
    # MoE (26.5B total / 128 experts top-8). LoRA covers attention + dense MLP
    # Linears; the fused 3D expert tensors (experts.gate_up_proj/down_proj)
    # are not nn.Linear and stay frozen. Needs transformers>=5.5 + vllm>=0.25.
    "gemma4-26b": "google/gemma-4-26B-A4B-it",
}

LORA_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj",
]


def resolve_model_id(name: str) -> str:
    """Preset key -> HF id; anything else is treated as a raw HF id."""
    return PRESETS.get(name, name)


def load_tokenizer(cfg: RunConfig):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(resolve_model_id(cfg.model))


def build_peft_config(cfg: RunConfig):
    from peft import LoraConfig

    lora = cfg.train.lora
    return LoraConfig(
        r=lora.r,
        lora_alpha=lora.alpha,
        lora_dropout=lora.dropout,
        target_modules=LORA_TARGET_MODULES,
        task_type="CAUSAL_LM",
    )


def load_model(cfg: RunConfig):
    """Text-only causal LM. The gemma -it checkpoints are multimodal; the
    Gemma*ForCausalLM classes load just the language model (no vision tower)."""
    import torch
    from transformers import AutoModelForCausalLM

    model_id = resolve_model_id(cfg.model)
    kwargs: dict = {
        "dtype": torch.bfloat16 if cfg.train.bf16 else torch.float32,
    }
    if cfg.train.quantization == "4bit":
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    try:
        return AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    except ValueError:
        # Multimodal checkpoint whose auto-mapping refuses CausalLM: load the
        # text tower explicitly.
        from transformers import AutoConfig

        if AutoConfig.from_pretrained(model_id).model_type == "gemma4":
            from transformers import Gemma4ForCausalLM

            return Gemma4ForCausalLM.from_pretrained(model_id, **kwargs)
        from transformers import Gemma3ForCausalLM

        return Gemma3ForCausalLM.from_pretrained(model_id, **kwargs)
