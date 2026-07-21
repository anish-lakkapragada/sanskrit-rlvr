"""The live dashboard — private, local, zero dependencies.

    python -m finetune.dashboard [--port 8777]      # or dashboard.enabled: true

One stdlib HTTP server watches ALL of runs/: for each run it shows the live
training curve (parsed straight from train.log as it grows), the checkpoint
metrics (compile-rate / chrF++ / reward), and the latest sample generations
with their Lean verdicts. The page polls every 5 s.
"""

import argparse
import json
import re
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RUNS = Path(__file__).resolve().parent.parent / "runs"

# one pattern per trainer's log format: mlx-lm-lora prose, TRL log dicts
_REWARDS = [re.compile(r"Total Rewards:\s*μ=([0-9.]+)"),
            re.compile(r"'reward':\s*(-?[0-9.]+)")]
_LOSSES = [re.compile(r"Train loss ([0-9.]+)"),
           re.compile(r"'loss':\s*(-?[0-9.]+)")]


def _first_match(text: str, patterns) -> list[float]:
    for pat in patterns:
        found = pat.findall(text)
        if found:
            return [float(x) for x in found]
    return []


def run_state(run: Path) -> dict:
    state = {"name": run.name, "curve": [], "curve_kind": "", "metrics": [],
             "samples": []}
    log = run / "train.log"
    if log.exists():
        text = log.read_text(errors="replace")
        rewards = _first_match(text, _REWARDS)
        if rewards:
            state["curve"] = rewards[-2000:]
            state["curve_kind"] = "group-mean reward"
        else:
            state["curve"] = _first_match(text, _LOSSES)[-2000:]
            state["curve_kind"] = "train loss"
    m = run / "metrics.jsonl"
    if m.exists():
        state["metrics"] = [json.loads(l) for l in m.open()]
    # snapshots: new layout is a folder per eval point with one jsonl per
    # benchmark group; old layout was a single checkpoint_<it>.jsonl
    snaps = sorted((run / "snapshots").glob("checkpoint_*"),
                   key=lambda p: int(p.stem.split("_")[1])) \
        if (run / "snapshots").exists() else []
    if snaps:
        latest = snaps[-1]
        src = latest / "in_fragment.jsonl" if latest.is_dir() else latest
        if src.exists():
            rows = [json.loads(l) for l in src.open()][:4]
            state["samples"] = [{"prompt": r["prompt"][:110],
                                 "answer": r["answer"],
                                 "ok": r.get("grammatical")} for r in rows]
            state["samples_from"] = latest.stem
    return state


PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>runs — live</title><style>
body{font-family:system-ui;margin:24px;background:#111;color:#eee}
h1{font-size:18px} h2{font-size:15px;margin:24px 0 4px}
.small{color:#999;font-size:12px}
svg{background:#1a1a1a;border-radius:8px}
table{border-collapse:collapse;font-size:13px;margin-top:6px}
td,th{padding:3px 10px;border-bottom:1px solid #333;text-align:left}
.ok{color:#6c6}.bad{color:#e77}
</style></head><body>
<h1>runs/ — live <span class="small" id="ts"></span></h1>
<div id="root">loading…</div>
<script>
async function tick(){
  const r = await fetch('/api/state'); const runs = await r.json();
  document.getElementById('ts').textContent = new Date().toLocaleTimeString();
  let h = '';
  for (const s of runs){
    h += `<h2>${s.name} <span class="small">${s.curve_kind}, ${s.curve.length} pts</span></h2>`;
    if (s.curve.length > 1){
      const W=700,H=90,n=s.curve.length;
      const mx=Math.max(...s.curve),mn=Math.min(...s.curve);
      const pts=s.curve.map((v,i)=>`${(i/(n-1))*W},${H-4-(H-8)*(v-mn)/((mx-mn)||1)}`).join(' ');
      h += `<svg width="${W}" height="${H}"><polyline points="${pts}" fill="none" stroke="#5af" stroke-width="1.5"/></svg>
            <div class="small">min ${mn.toFixed(3)} · max ${mx.toFixed(3)} · last ${s.curve[n-1].toFixed(3)}</div>`;
    }
    if (s.metrics.length){
      h += '<table><tr><th>ckpt</th><th>compile (in)</th><th>chrF++ (in)</th><th>TER (in)</th><th>chrF++ (out)</th><th>TER (out)</th><th>reward</th></tr>';
      for (const m of s.metrics){
        const i = m.in_fragment ?? m, o = m.out_of_fragment ?? {};   // ?? m: legacy flat rows
        const f = v => v ?? '—';
        h += `<tr><td>${m.checkpoint}${m.kind==='init'?' (init)':''}</td><td>${f(i.compile_rate)}</td><td>${f(i.chrf_pp)}</td><td>${f(i.ter)}</td><td>${f(o.chrf_pp)}</td><td>${f(o.ter)}</td><td>${f(i.mean_reward)}</td></tr>`;
      }
      h += '</table>';
    }
    if (s.samples && s.samples.length){
      h += `<div class="small" style="margin-top:6px">${s.samples_from}:</div><table>`;
      for (const x of s.samples)
        h += `<tr><td class="small">${x.prompt}</td><td>${x.answer}</td>
              <td class="${x.ok?'ok':'bad'}">${x.ok===null?'':(x.ok?'✓':'✗')}</td></tr>`;
      h += '</table>';
    }
  }
  document.getElementById('root').innerHTML = h || 'no runs yet';
}
tick(); setInterval(tick, 5000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/state":
            runs = sorted([d for d in RUNS.iterdir() if d.is_dir()],
                          key=lambda d: d.stat().st_mtime, reverse=True) \
                if RUNS.exists() else []
            body = json.dumps([run_state(r) for r in runs]).encode()
            ctype = "application/json"
        else:
            body, ctype = PAGE.encode(), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def ensure_running(port: int = 8777):
    """Idempotent: start a detached dashboard if nothing listens on the port."""
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            return
    subprocess.Popen([sys.executable, "-m", "finetune.dashboard",
                      "--port", str(port)],
                     cwd=RUNS.parent, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    print(f"[dashboard] live at http://localhost:{port}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8777)
    args = ap.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"dashboard: http://localhost:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
