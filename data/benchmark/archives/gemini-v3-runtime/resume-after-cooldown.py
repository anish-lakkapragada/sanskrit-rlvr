from pathlib import Path
import json, os, sys, time
from datetime import datetime, timezone
root=Path(__file__).resolve().parents[4]
folder=root/'data/benchmark/results/gemini4-argon-high'
while True:
    m=json.loads((folder/'manifest.json').read_bytes())
    if m['status'] != 'running': break
    pid=m['execution'].get('pid')
    if not pid: raise RuntimeError('Running state has no worker PID')
    os.kill(pid,0)
    time.sleep(5)
if m['execution']['progress']['unsettled']:
    raise RuntimeError('Unresolved attempts require inspection')
print(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'event':'capacity_cooldown','seconds':300,'next_concurrency_ceiling':4}),flush=True)
time.sleep(300)
os.execv(sys.executable,[sys.executable,'-u',str(root/'data/engine/evaluation/supervise_gemini.py'),'--model','gemini4-argon-high','--concurrency-ceiling','4'])
