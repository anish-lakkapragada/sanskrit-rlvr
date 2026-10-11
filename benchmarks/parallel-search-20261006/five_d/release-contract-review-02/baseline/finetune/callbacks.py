"""Training-side instrumentation: reward history + checkpoint eval hook."""

import json
import os
import time
from pathlib import Path

import numpy as np


def completion_text(completion) -> str:
    """Normalize a TRL completion (str, or conversational message list) to text."""
    if isinstance(completion, str):
        return completion
    if isinstance(completion, list):
        return "".join(m.get("content", "") for m in completion if isinstance(m, dict))
    return str(completion)


class RewardHistoryRecorder:
    """Wraps a registry reward function for GRPOTrainer.

    - Normalizes conversational prompts/completions to plain strings, keeping
      the user-facing reward contract (list[str]).
    - Appends every training batch's raw rewards to reward_history.jsonl
      (one line per call, with global step + rank) for distribution-shift
      analysis.
    - Mirrors the distribution to TensorBoard as a `reward/dist` histogram
      (rank 0 only).
    """

    def __init__(self, fn, run_dir: Path, writer=None):
        self.fn = fn
        self.__name__ = getattr(fn, "__name__", "reward")
        self.path = Path(run_dir) / "reward_history.jsonl"
        self.writer = writer
        self.rank = int(os.environ.get("RANK", os.environ.get("LOCAL_RANK", 0)))
        self._calls = 0

    def __call__(self, prompts, completions, **kwargs):
        prompts = [completion_text(p) for p in prompts]
        completions = [completion_text(c) for c in completions]
        rewards = self.fn(prompts, completions, **kwargs)

        state = kwargs.get("trainer_state")
        step = int(state.global_step) if state is not None else self._calls
        self._calls += 1

        valid = [r for r in rewards if r is not None]
        record = {
            "step": step,
            "rank": self.rank,
            "time": time.time(),
            "n": len(rewards),
            "mean": float(np.mean(valid)) if valid else None,
            "std": float(np.std(valid)) if valid else None,
            "rewards": rewards,
        }
        with self.path.open("a") as f:
            f.write(json.dumps(record) + "\n")
        if self.writer is not None and self.rank == 0 and valid:
            self.writer.add_histogram("reward/dist", np.asarray(valid, dtype=float), step)
        return rewards


def make_checkpoint_eval_callback(eval_suite):
    """TrainerCallback that runs the eval suite at every save point.

    transformers is imported lazily so this module stays importable in
    --dry-run environments without GPU deps.
    """
    from transformers import TrainerCallback

    class CheckpointEvalCallback(TrainerCallback):
        def on_save(self, args, state, control, **kwargs):
            if state.is_world_process_zero:
                eval_suite(int(state.global_step))
            return control

    return CheckpointEvalCallback()
