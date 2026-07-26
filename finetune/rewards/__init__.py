"""Reward-function registry.

A reward function is a plain callable with the TRL-native shape:

    @register("my_reward")
    def my_reward(prompts: list[str], completions: list[str], **kwargs) -> list[float]:
        ...

- ``prompts`` / ``completions`` are plain strings (the training wrapper
  normalizes TRL's conversational message dicts to strings before calling).
- ``kwargs`` receives every extra dataset column as a list aligned with
  ``completions`` (``id``, ``dhatu``, ``morphology``, ``gold_slp1``,
  ``gold_devanagari``, ...) plus TRL extras such as ``trainer_state`` and
  ``log_metric`` when running under GRPOTrainer. Always accept ``**kwargs``.
- Return one float per completion (``None`` for not-applicable samples).

Config files reference rewards by registry name (``reward: example``).
"""

import importlib
import pkgutil

REGISTRY: dict[str, callable] = {}
_DISCOVERED = False


def register(name: str):
    """Decorator: add a reward function to the registry under ``name``."""

    def deco(fn):
        if name in REGISTRY and REGISTRY[name] is not fn:
            raise ValueError(f"reward {name!r} is already registered")
        REGISTRY[name] = fn
        return fn

    return deco


def _discover() -> None:
    """Import every module in this package so @register decorators run."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    for mod in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{__name__}.{mod.name}")
    _DISCOVERED = True


def get(name: str):
    _discover()
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"unknown reward {name!r}; available: {sorted(REGISTRY)}"
        ) from None


def names() -> list[str]:
    _discover()
    return sorted(REGISTRY)
