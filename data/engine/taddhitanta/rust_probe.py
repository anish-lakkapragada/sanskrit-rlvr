"""Build a meaning-aware probe from the checksum-pinned Python 0.4.0 sdist.

The archive omits its workspace root. Adapt only its Cargo manifest for a
standalone build; every engine .rs file remains byte-for-byte unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
SDIST_URL = "https://files.pythonhosted.org/packages/69/b5/6876b3f807ac38812c6e29eb43738d28a6a21c2aed456486e654997efcdd/vidyut-0.4.0.tar.gz"
SDIST_SHA256 = "fb776ec751e66c8d44bd94ef71008f9ea05284f51055aa009cfaef33ccf5f454"
LOCK = HERE / "probe.Cargo.lock"
CARGO = '''[package]
name = "taddhitanta-probe"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "=1.0.215", features = ["derive"] }
serde_json = "=1.0.133"
vidyut-prakriya = { path = "engine" }
'''


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(prepare_lock=False):
    # Content-addressed scratch space: builds stay outside the repository.
    identity = hashlib.sha256((SDIST_SHA256 + sha256(HERE / "probe.rs") +
                               sha256(__file__)).encode()).hexdigest()[:16]
    cache = Path(tempfile.gettempdir()) / f"sanskrit-taddhitanta-{identity}"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "vidyut-0.4.0.tar.gz"
    if not archive.exists():
        print("Downloading checksum-pinned VP 0.4.0 source", flush=True)
        with urlopen(SDIST_URL, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != SDIST_SHA256:
            raise ValueError("VP source archive checksum mismatch")
        archive.write_bytes(data)
    if sha256(archive) != SDIST_SHA256:
        raise ValueError("Cached VP source archive changed")
    # Re-extract to guarantee source integrity even when reusing compiled output.
    with tarfile.open(archive) as tar:
        tar.extractall(cache, filter="data")
    source = cache / "vidyut-0.4.0"
    engine_source = source / "vidyut-prakriya"
    build = cache / "probe"
    (build / "src").mkdir(parents=True, exist_ok=True)
    (build / "engine").mkdir(exist_ok=True)
    shutil.copytree(engine_source / "src", build / "engine/src", dirs_exist_ok=True)
    original = (engine_source / "Cargo.toml").read_text()
    # Drop development-only path dependencies and benchmarks; the shipped
    # standalone crate cannot inherit missing workspace dependencies.
    manifest = original.split("[dev-dependencies]")[0] + "[features]" + original.split("[features]", 1)[1]
    manifest = manifest.replace('rustc-hash = { workspace = true }', 'rustc-hash = "=2.1.0"')
    manifest = manifest.replace('[[bench]]\nname = "microbenchmarks"\nharness = false\n', '')
    (build / "engine/Cargo.toml").write_text(manifest)
    shutil.copyfile(engine_source / "README.md", build / "engine/README.md")
    shutil.copyfile(HERE / "probe.rs", build / "src/main.rs")
    (build / "Cargo.toml").write_text(CARGO)
    if prepare_lock:
        shutil.copyfile(source / "bindings-python/Cargo.lock", build / "Cargo.lock")
    else:
        if not LOCK.exists():
            raise ValueError("Missing probe.Cargo.lock; initialize with rust_probe.py --prepare-lock")
        shutil.copyfile(LOCK, build / "Cargo.lock")
    command = ["cargo", "build", "--release", "--manifest-path", str(build / "Cargo.toml")]
    if not prepare_lock:
        command.append("--locked")
    # New Rust versions flag an old wasm-bindgen macro under the crate's
    # deny(unsafe_code). This native-only probe does not call the WASM bridge.
    # Cap compiler lints without editing any engine source or grammar rules.
    print("Building native VP probe (locked dependencies)", flush=True)
    result = subprocess.run(command, env={**os.environ, "RUSTFLAGS": "--cap-lints=allow"},
                            text=True, capture_output=True)
    (build / "build.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr)
    if prepare_lock:
        shutil.copyfile(build / "Cargo.lock", LOCK)
    return build / "target/release/taddhitanta-probe", source, {
        "sdist_url": SDIST_URL, "sdist_sha256": SDIST_SHA256,
        "cargo_lock_sha256": sha256(LOCK),
        "adapted_engine_cargo_sha256": sha256(build / "engine/Cargo.toml"),
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "rustflags": "--cap-lints=allow (old WASM macro compatibility; native probe)",
        "engine_source_changes": "None; only Cargo workspace/test configuration adapted.",
    }


def derive(binary, requests, log_steps=False):
    result = subprocess.run([str(binary)], input=json.dumps({"log_steps": log_steps, "requests": requests}),
                            text=True, capture_output=True, check=True)
    responses = json.loads(result.stdout)
    if [r["id"] for r in responses] != [r["id"] for r in requests]:
        raise ValueError("Rust probe lost/reordered requests")
    return responses


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-lock", action="store_true")
    args = parser.parse_args()
    binary, source, metadata = prepare(args.prepare_lock)
    print(json.dumps({"binary": str(binary), "source": str(source), **metadata}, indent=2))
