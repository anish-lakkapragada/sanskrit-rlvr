#!/usr/bin/env python
"""Local comparison UI for the campaign models.

Fans a prompt out to any subset of {base, tb20m-samayik100/67/50/33, grpo-r3}
served by the two vLLM OpenAI servers tunneled to localhost:8000/8001, and
renders outputs side by side. Every request pins
chat_template_kwargs.enable_thinking=False — the training/eval conditioning.

Run via ./serving/serve.sh (which starts the box, tunnels, then this app).
"""

import asyncio
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parents[1]

MODELS = {  # ui key -> (upstream base url, served model name)
    "base":    ("http://localhost:8000", "Qwen/Qwen3-4B"),
    "grpo-r3": ("http://localhost:8001", "grpo-r3"),
}
for _b in (10, 15, 20):
    for _s in (100, 67, 50, 33, 0):
        _k = f"tb{_b}m-samayik{_s}"
        MODELS[_k] = ("http://localhost:8000", _k)

# "-avg" twins: the same adapter served at half alpha, i.e. the exact 50/50
# weight average of the fine-tuned model with its serving base. For the SFT
# arms the anchor is stock Qwen3-4B; for grpo-r3 the anchor is its serving
# base merged-s67 (the SFT parent), NOT stock Qwen3.
MODELS.update({f"{k}-avg": (url, f"{served}-avg")
               for k, (url, served) in MODELS.items() if k != "base"})

# box-side adapter dir per ui key (for self-healing -avg registration when a
# server restarted without the -avg boot modules, e.g. an old box_setup.sh)
BOX_HOME = "/home/ubuntu/sanskrit"
ADAPTER_DIRS = {"grpo-r3": "adapter-grpo"}
for _b in (10, 15, 20):
    for _s in (100, 67, 50, 33, 0):
        _k = f"tb{_b}m-samayik{_s}"
        ADAPTER_DIRS[_k] = f"adapter-s{_s}" if (_b == 20 and _s != 0) else f"adapter-t{_b}s{_s}"

TEMPLATES = {
    "raw": None,
    "translation (v0 eval)": "prompts/v0/translation.txt",
    "elicitation scaffold": "prompts/v1/translation-elicitation/translation_scaffold.txt",
    "elicitation placebo": "prompts/v1/translation-elicitation/translation_placebo.txt",
    "drill costume (conjprompt)": "prompts/v1/translation-conjprompt/translation_drill_costume.txt",
}

app = FastAPI()


@app.get("/api/templates")
async def templates():
    return {name: ((ROOT / p).read_text() if p else None)
            for name, p in TEMPLATES.items()}


@app.get("/api/health")
async def health():
    out = {}
    async with httpx.AsyncClient(timeout=5) as cli:
        for port in (8000, 8001):
            try:
                r = await cli.get(f"http://localhost:{port}/v1/models")
                out[str(port)] = [m["id"] for m in r.json().get("data", [])]
            except Exception as e:
                out[str(port)] = f"DOWN ({type(e).__name__})"
    return out


@app.post("/api/generate")
async def generate(body: dict):
    prompt = body["prompt"]
    tpl = TEMPLATES.get(body.get("template", "raw"))
    if tpl:
        prompt = (ROOT / tpl).read_text().format(english=prompt)

    async def one(key):
        base_url, served = MODELS[key]
        payload = {
            "model": served,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(body.get("temperature", 0.2)),
            "max_tokens": int(body.get("max_tokens", 1024)),
            "chat_template_kwargs": {"enable_thinking": False},
        }
        try:
            async with httpx.AsyncClient(timeout=300) as cli:
                t0 = asyncio.get_event_loop().time()
                r = await cli.post(f"{base_url}/v1/chat/completions", json=payload)
                if r.status_code == 404 and key.endswith("-avg"):
                    # server restarted without the -avg module: register + retry
                    await cli.post(f"{base_url}/v1/load_lora_adapter", json={
                        "lora_name": served,
                        "lora_path": f"{BOX_HOME}/{ADAPTER_DIRS[key[:-4]]}-avg"})
                    r = await cli.post(f"{base_url}/v1/chat/completions", json=payload)
                dt = asyncio.get_event_loop().time() - t0
                if r.status_code != 200:
                    return key, f"[HTTP {r.status_code}] {r.text[:300]}", dt
                d = r.json()
                return key, d["choices"][0]["message"]["content"], dt
        except Exception as e:
            return key, f"[error] {type(e).__name__}: {e}", 0.0

    results = await asyncio.gather(*(one(k) for k in body["models"] if k in MODELS))
    return JSONResponse({
        "rendered_prompt": prompt,
        "results": [{"model": k, "output": o, "seconds": round(s, 1)}
                    for k, o, s in results],
    })


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>sanskrit model compare</title><style>
 body{font:14px/1.45 ui-monospace,Menlo,monospace;background:#111;color:#ddd;
      margin:0;padding:18px;max-width:1500px}
 h1{font-size:16px;color:#fff} textarea{width:100%;height:90px;background:#1b1b1b;
      color:#eee;border:1px solid #333;border-radius:6px;padding:8px;font:inherit}
 .row{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:10px 0}
 label{user-select:none} select,input[type=number]{background:#1b1b1b;color:#eee;
      border:1px solid #333;border-radius:4px;padding:3px 6px;font:inherit}
 button{background:#2a6df4;color:#fff;border:0;border-radius:6px;padding:8px 18px;
      font:inherit;cursor:pointer} button:disabled{opacity:.5}
 #grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));
      gap:12px;margin-top:14px}
 .card{background:#191919;border:1px solid #2c2c2c;border-radius:8px;padding:10px}
 .card h3{margin:0 0 6px;font-size:13px;color:#7fb3ff}
 .card pre{white-space:pre-wrap;word-break:break-word;margin:0;font-size:13px;
      max-height:480px;overflow:auto}
 .lat{color:#777;font-size:11px;float:right}
 #rendered{color:#888;font-size:12px;white-space:pre-wrap;max-height:170px;
      overflow:auto;background:#161616;border:1px dashed #333;border-radius:6px;
      padding:6px;margin-top:8px}
 #rendered b{color:#aaa}
</style></head><body>
<h1>campaign model compare <span style="color:#666">(bf16 A100 · enable_thinking=False pinned)</span></h1>
<textarea id="prompt" placeholder="English sentence (for templates) or a raw prompt...">The two of them will go to the village.</textarea>
<div class="row">
 <label>template <select id="template"></select></label>
 <label>temp <input id="temp" type="number" value="0.2" step="0.1" min="0" max="1.5" style="width:60px"></label>
 <label>max_tokens <input id="maxtok" type="number" value="1024" step="128" min="16" style="width:80px"></label>
 <label><input type="checkbox" id="avg"> enable averaging (½·adapter)</label>
 <button id="go">Generate</button>
 <span id="status" style="color:#888"></span>
</div>
<div class="row" id="models"></div>
<div id="rendered"></div>
<div id="grid"></div>
<script>
const GROUPS={
 "": ["base","grpo-r3"],
 "10M": ["tb10m-samayik100","tb10m-samayik67","tb10m-samayik50","tb10m-samayik33","tb10m-samayik0"],
 "15M": ["tb15m-samayik100","tb15m-samayik67","tb15m-samayik50","tb15m-samayik33","tb15m-samayik0"],
 "20M": ["tb20m-samayik100","tb20m-samayik67","tb20m-samayik50","tb20m-samayik33","tb20m-samayik0"],
};
const TEMPLATES=["raw","translation (v0 eval)","elicitation scaffold","elicitation placebo","drill costume (conjprompt)"];
const mdiv=document.getElementById("models");
const DEFAULT_ON=new Set(["base","tb20m-samayik67","grpo-r3"]);
mdiv.style.display="block";
for(const [g,ms] of Object.entries(GROUPS)){
 let row=`<div style="margin:2px 0"><span style="color:#666;display:inline-block;width:36px">${g}</span>`;
 ms.forEach(m=>{
  const short=g?m.replace(`tb${g.toLowerCase()}-samayik`,"s"):m;
  row+=`<label style="margin-right:12px"><input type="checkbox" value="${m}" ${DEFAULT_ON.has(m)?"checked":""}> ${short}</label>`;
 });
 mdiv.insertAdjacentHTML("beforeend",row+"</div>");
}
const tsel=document.getElementById("template");
TEMPLATES.forEach(t=>tsel.insertAdjacentHTML("beforeend",`<option>${t}</option>`));
tsel.value="translation (v0 eval)";
let TPL_TEXT={};
fetch("/api/templates").then(r=>r.json()).then(d=>{TPL_TEXT=d;preview();});
function preview(){
 const p=document.getElementById("prompt").value;
 const t=TPL_TEXT[tsel.value];
 const rendered=t?t.replaceAll("{english}",p):p;
 const rend=document.getElementById("rendered");
 rend.innerHTML="<b>prompt that will be sent:</b>\\n";
 rend.appendChild(document.createTextNode(rendered));
}
document.getElementById("prompt").addEventListener("input",preview);
tsel.addEventListener("change",preview);
const esc=s=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;");
async function go(){
 const models=[...mdiv.querySelectorAll("input:checked")].map(c=>c.value);
 const avgOn=document.getElementById("avg").checked;
 const btn=document.getElementById("go"), st=document.getElementById("status");
 const grid=document.getElementById("grid");
 btn.disabled=true; grid.innerHTML="";
 const body=m=>({prompt:document.getElementById("prompt").value,template:tsel.value,
  temperature:+document.getElementById("temp").value,
  max_tokens:+document.getElementById("maxtok").value,models:[m]});
 // one card per model up front; with averaging on, each card is two stacked
 // rows (original / ½·adapter) that fill in independently as they finish
 const jobs=[];  // [modelToQuery, outElementId]
 models.forEach(m=>{
  const avgNote=m==="grpo-r3"?" · anchor: sft-67 merge":" · anchor: base";
  let card=`<div class="card" id="card-${m}"><h3>${m}<span class="lat" id="lat-${m}"></span></h3>
   <pre id="out-${m}" style="color:#777">⏳ generating…</pre>`;
  if(avgOn){
   if(m==="base"){
    card+=`<h3 style="margin-top:8px;color:#888">averaged</h3>
     <pre style="color:#666">base is the anchor — nothing to average</pre>`;
   }else{
    card+=`<h3 style="margin-top:8px">${m} · averaged (½·adapter${avgNote})<span class="lat" id="lat-${m}-avg"></span></h3>
     <pre id="out-${m}-avg" style="color:#777">⏳ generating…</pre>`;
    jobs.push([`${m}-avg`,`${m}-avg`]);
   }
  }
  grid.insertAdjacentHTML("beforeend",card+"</div>");
  jobs.push([m,m]);
 });
 let done=0; st.textContent=`0/${jobs.length} done`;
 await Promise.all(jobs.map(async ([q,id])=>{
  try{
   const r=await fetch("/api/generate",{method:"POST",
    headers:{"Content-Type":"application/json"},body:JSON.stringify(body(q))});
   const x=(await r.json()).results[0];
   const el=document.getElementById(`out-${id}`);
   if(x.output.trim()===""){
    el.textContent="∅ empty completion — model emitted end-of-turn as its first token";
    el.style.color="#c77";
   }else{ el.innerHTML=esc(x.output); el.style.color=""; }
   document.getElementById(`lat-${id}`).textContent=x.seconds+"s";
  }catch(e){
   document.getElementById(`out-${id}`).textContent="[error] "+e;
  }
  st.textContent=`${++done}/${jobs.length} done`;
 }));
 btn.disabled=false;
}
document.getElementById("go").onclick=go;
</script></body></html>"""


@app.get("/")
async def index():
    return HTMLResponse(PAGE)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="warning")
