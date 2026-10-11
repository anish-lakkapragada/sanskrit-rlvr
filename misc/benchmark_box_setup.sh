#!/bin/bash
# One leader prepares a shared environment/model for all four evaluation workers.
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
TASK_ROOT=/lambda/nfs/sanskrit-serve/grpo-r3-full-20260920
cd "$TASK_ROOT/repo"
export UV_CACHE_DIR=/lambda/nfs/sanskrit-serve/uv-cache
export HF_HOME=/lambda/nfs/sanskrit-serve/hf-cache
export UV_PROJECT_ENVIRONMENT="$TASK_ROOT/env"
export VLLM_ATTENTION_BACKEND=FLASH_ATTN
export VLLM_USE_FLASHINFER_SAMPLER=0
if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
if [ ! -f "$TASK_ROOT/env-ready.json" ]; then
    uv sync --extra train --frozen
    uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" \
        --index-url https://download.pytorch.org/whl/cu128 \
        'torch==2.11.0+cu128' 'torchvision==0.26.0+cu128' 'torchaudio==2.11.0+cu128'
    uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" --no-deps \
        'vllm @ https://github.com/vllm-project/vllm/releases/download/v0.25.1/vllm-0.25.1%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl'
    "$UV_PROJECT_ENVIRONMENT/bin/python" - <<'PY'
import json, torch, vllm
from pathlib import Path
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen3-4B')
assert torch.cuda.is_available()
assert AutoTokenizer.from_pretrained('Qwen/Qwen3-4B')('x')['input_ids']
Path('/lambda/nfs/sanskrit-serve/grpo-r3-full-20260920/env-ready.json').write_text(json.dumps({'torch':torch.__version__,'vllm':vllm.__version__}))
print('ENV-READY',flush=True)
PY
fi
if [ ! -f "$TASK_ROOT/model-ready.json" ]; then
    "$UV_PROJECT_ENVIRONMENT/bin/python" - <<'PY'
import hashlib, json
from pathlib import Path
manifest=json.loads(Path('manifest.json').read_text())
for key,local in [
 ('runs-final/sft-qwen3-4b-tb20m-samayik67/adapter/adapter_model.safetensors','adapter-s67/adapter_model.safetensors'),
 ('runs-final/grpo-r3-final/adapter/adapter_model.safetensors','adapter-grpo/adapter_model.safetensors')]:
 h=hashlib.sha256()
 with open(local,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
 assert h.hexdigest()==manifest['source_sha256'][key],local
print('ADAPTER-HASHES-VERIFIED',flush=True)
PY
    "$UV_PROJECT_ENVIRONMENT/bin/python" misc/merge_adapter.py adapter-s67 \
        --base Qwen/Qwen3-4B --out "$TASK_ROOT/merged-s67"
    "$UV_PROJECT_ENVIRONMENT/bin/python" - <<'PY'
import json
from pathlib import Path
p=Path('/lambda/nfs/sanskrit-serve/grpo-r3-full-20260920/merged-s67/tokenizer_config.json')
cfg=json.loads(p.read_text())
if cfg.pop('extra_special_tokens',None) is not None: p.write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
PY
    "$UV_PROJECT_ENVIRONMENT/bin/python" misc/merge_adapter.py adapter-grpo \
        --base "$TASK_ROOT/merged-s67" --out "$TASK_ROOT/grpo-r3-final-merged"
    "$UV_PROJECT_ENVIRONMENT/bin/python" - <<'PY'
import hashlib, json
from pathlib import Path
from transformers import AutoTokenizer
root=Path('/lambda/nfs/sanskrit-serve/grpo-r3-full-20260920')
model=root/'grpo-r3-final-merged'
p=model/'tokenizer_config.json'
cfg=json.loads(p.read_text())
if cfg.pop('extra_special_tokens',None) is not None: p.write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
assert AutoTokenizer.from_pretrained(model)('x')['input_ids']
hashes={}
for path in sorted(model.glob('*')):
 if path.is_file():
  h=hashlib.sha256()
  with path.open('rb') as f:
   for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
  hashes[path.name]=h.hexdigest()
(root/'model-ready.json').write_text(json.dumps(hashes,indent=2)+'\n')
print('MODEL-READY',flush=True)
PY
fi
echo SETUP-COMPLETE
