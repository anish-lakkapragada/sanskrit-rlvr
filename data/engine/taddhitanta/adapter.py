"""Pinned VP build with an opt-in, source-gender-aware nominal adapter.

The historical probe remains unmodified. This build applies the checked-in
compatibility patch, records its hash, and shares no mutable engine state with it.
"""

from functools import lru_cache
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from data.engine.taddhitanta import rust_probe

HERE = Path(__file__).resolve().parent
PATCH = HERE / "nominal-input.patch"
CODE = (Path(__file__), HERE / "adapter.rs", PATCH, HERE / "rust_probe.py", HERE / "probe.rs", rust_probe.LOCK)


@lru_cache(maxsize=1)
def prepare():
    # Separate exporter/preflight processes can start together. Protect source
    # extraction and patching as well as compilation; Cargo locks only its build.
    lock_path = Path(tempfile.gettempdir()) / "sanskrit-nominal-adapter-build.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _prepare_locked()


def _prepare_locked():
    original_binary, source, original_metadata = rust_probe.prepare()
    identity = hashlib.sha256((rust_probe.SDIST_SHA256 + "".join(rust_probe.sha256(p) for p in CODE)).encode()).hexdigest()[:16]
    build = Path(tempfile.gettempdir()) / f"sanskrit-nominal-adapter-{identity}"
    (build / "src").mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / "vidyut-prakriya/src", build / "engine/src", dirs_exist_ok=True)
    old_build = original_binary.parents[2]
    shutil.copyfile(old_build / "engine/Cargo.toml", build / "engine/Cargo.toml")
    shutil.copyfile(old_build / "engine/README.md", build / "engine/README.md")
    shutil.copyfile(rust_probe.LOCK, build / "Cargo.lock")
    (build / "Cargo.toml").write_text(rust_probe.CARGO)
    shutil.copyfile(HERE / "adapter.rs", build / "src/main.rs")
    subprocess.run(["patch", "--batch", "--fuzz=0", "-p1", "-i", str(PATCH)],
                   cwd=build / "engine", check=True, capture_output=True, text=True)
    result = subprocess.run(["cargo", "build", "--release", "--locked", "--manifest-path", str(build / "Cargo.toml")],
                            env={**os.environ, "RUSTFLAGS": "--cap-lints=allow"}, capture_output=True, text=True)
    (build / "build.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr)
    metadata = {**original_metadata,
                "engine_source_changes": "Opt-in nominal-input.patch: source gender on base term; remove empty nyap marker for taddhita input only.",
                "adapter_files": {p.name: rust_probe.sha256(p) for p in CODE},
                "patched_engine_files": {str(p.relative_to(build / "engine")): rust_probe.sha256(p)
                                         for p in (build / "engine/src/args/taddhita.rs", build / "engine/src/ashtadhyayi.rs")}}
    return build / "target/release/taddhitanta-probe", metadata


def derive(binary, requests, log_steps=False):
    return rust_probe.derive(binary, requests, log_steps)
