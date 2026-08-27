"""Colocated vLLM rollout engine with a FUNCTIONAL weight push.

Unlike TRL's colocate sync (merge_adapter -> push -> unmerge_adapter, which
mutates the trainer's base weights in place and accumulates bf16 round-trip
error over thousands of steps — the r2 campaign's suspected-drift hazard),
this push never touches the training model: for each LoRA-targeted Linear we
compute ``W_eff = W + (B @ A) * scaling`` into a FRESH tensor (fp32 accumulate,
cast to the base dtype) and hand that to vLLM's ``load_weights``. The trainer's
parameters are read-only here.
"""


def build_engine(cfg, model_path: str):
    import os

    # Keep the v1 EngineCore IN-PROCESS (same trick TRL colocate uses):
    # with the default multiprocess engine the model object lives in a child
    # process and push_policy_weights cannot reach it.
    os.environ["VLLM_ENABLE_V1_MULTIPROCESSING"] = "0"
    from vllm import LLM

    return LLM(
        model=model_path,
        dtype="bfloat16",
        max_model_len=cfg.vllm.max_model_length,
        gpu_memory_utilization=cfg.vllm.gpu_memory_utilization,
        enforce_eager=False,  # cudagraphs ~3x decode speed; TRL colocate runs the same way
        seed=cfg.seed,
    )


def _vllm_model(llm):
    """The in-process model object, across vLLM v0/v1 internal layouts."""
    chains = [
        ("llm_engine", "model_executor", "driver_worker", "model_runner", "model"),
        ("llm_engine", "engine_core", "engine_core", "model_executor",
         "driver_worker", "model_runner", "model"),
        ("llm_engine", "engine_core", "engine_core", "model_executor",
         "driver_worker", "worker", "model_runner", "model"),
    ]
    tried = []
    for chain in chains:
        obj = llm
        try:
            for attr in chain:
                obj = getattr(obj, attr)
            return obj
        except AttributeError:
            tried.append(".".join(chain))
    raise AttributeError(
        "could not locate the vLLM model object; tried: " + " | ".join(tried)
        + " — is VLLM_ENABLE_V1_MULTIPROCESSING=0 set before engine build?")


def iter_effective_lora_weights(peft_model):
    """Yield (vllm_param_name, W_eff) for every LoRA-wrapped Linear."""
    import torch

    for name, module in peft_model.named_modules():
        lora_A = getattr(module, "lora_A", None)
        if lora_A is None or "default" not in getattr(lora_A, "keys", lambda: [])():
            continue
        base_w = module.base_layer.weight.data
        A = module.lora_A["default"].weight.data      # [r, in]
        B = module.lora_B["default"].weight.data      # [out, r]
        scaling = module.scaling["default"]
        delta = (B.float() @ A.float()) * scaling
        w_eff = (base_w.float() + delta).to(base_w.dtype)
        vllm_name = (name.removeprefix("base_model.model.")
                     + ".weight").replace(".base_layer", "")
        yield vllm_name, w_eff


def push_policy_weights(llm, peft_model) -> int:
    """Load current-policy effective weights into vLLM; returns #params pushed."""
    model = _vllm_model(llm)
    n = 0
    for vllm_name, w_eff in iter_effective_lora_weights(peft_model):
        model.load_weights([(vllm_name, w_eff)])
        n += 1
    llm.reset_prefix_cache()
    return n


def generate(llm, texts: list[str], n: int, temperature: float,
             max_tokens: int) -> list[list[str]]:
    from vllm import SamplingParams

    params = SamplingParams(n=n, temperature=max(temperature, 1e-6),
                            top_p=1.0, max_tokens=max_tokens)
    outs = llm.generate(texts, params, use_tqdm=False)
    return [[o.text for o in out.outputs] for out in outs]
