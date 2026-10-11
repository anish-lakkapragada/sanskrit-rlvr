#!/usr/bin/env python
"""Build misc/vp-transfer-status-report.html — the project status report.

Embeds misc/report_examples.json (behavior battery via the serving app) into a
self-contained HTML with an example browser, plus the findings / temporary
conclusion / can-we-conclude analysis / rated-next-steps sections. Re-run after
updating RESULTS_14B / SDPO_VERDICT below (they start as 'pending').

Usage: python3 misc/build_behavior_report.py
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
EXAMPLES = json.loads((HERE / "report_examples.json").read_text())
OUT = HERE / "vp-transfer-status-report.html"

# ---- filled in when the Qwen3-14B scale probe lands -------------------------
RESULTS_14B = {
    "status": "done",
    "nothink": {"pass1": "0.70%", "pass16": "pass@16 3.59% (24/669 tasks)", "tag": "100%"},
    "think": {"pass1": "1.64%", "pass16": "pass@4 4.04% (669×4 run)", "tag": "88.1%"},
    "p_flip": "~10%",
    "value": "3",
    "reading": ("<b>Measured, both arms:</b> thinking OFF (669×16): pass@1 0.70% / pass@16 "
                "3.59% (24/669 tasks, tag 100%). Thinking ON (669×4): pass@1 1.64% / pass@4 "
                "4.04% (tag 88.1% — native reasoning sometimes exhausts the 4096 budget before "
                "the answer). Native reasoning roughly <b>doubles</b> the base rate (pass@4 "
                "1.90% → 4.04%), and 14B is ~8× the 4B floor — but 1.6% pass@1 is still two "
                "orders of magnitude below any SFT arm (46–62%). Verdict: no step-change; the "
                "SFT cold start and its recipe risks remain mandatory at 14B, at 3× the cost "
                "per pipeline stage. Scale is not the unlock."),
}
SDPO_VERDICT = {
    "status": "done",
    "rating": "2/10 <span class='dim'>from base</span><br>8/10 <span class='dim'>from SFT ckpt</span>",
    "one_line": ("The repo's SDPO is privileged-context self-distillation (Hübotter et al., "
                 "arXiv:2601.20802) — fully implemented in finetune/sdpo/, never run. From base "
                 "Qwen3-4B it fails; from the existing SFT checkpoint it is the cheapest, "
                 "best-motivated next experiment."),
    "detail": (
        "<b>What it actually is:</b> not preference optimization — the student samples rollouts, "
        "failures are re-scored by the <i>same model</i> given a privileged hint (gold form + "
        "sutra-numbered vidyut derivation trace; 5,822 pre-built tasks), and the loss is per-token "
        "forward KL(teacher-conditioned ‖ student) over completion tokens, span-weighted, on a "
        "fresh LoRA over the SFT policy.<br><br>"
        "<b>Why it fails from base (high confidence):</b> the teacher is the same 0.03%-pass@1 "
        "model with the answer pasted into context — it can only teach \"copy that string,\" and "
        "even that signal arrives as a few clamped 3-nat tokens drowned in full-weight KL over "
        "4096-token off-format rollouts (no &lt;answer&gt; tag → span weighting degrades to "
        "uniform). Base models ≤20B can't use the Devanagari derivation traces (the repo's own "
        "notation-hypothesis sweeps), matching the paper's reported failure mode on small models. "
        "SDPO-from-base is strictly dominated by plain SFT on the same privileged data.<br><br>"
        "<b>Where it shines instead:</b> from the SFT checkpoint, targeting exactly the tasks "
        "where GRPO has zero gradient (all-rollouts-fail groups — the 32.7% zero-variance "
        "pathology of round 2): the teacher still sees the gold derivation there, so SDPO has "
        "signal where GRPO is provably signal-free. ~1 A100 × 2000 steps; data + code already "
        "built and dry-run. Watch samayik chrF every 100 steps (self-distillation drifts harder "
        "than GRPO — arXiv:2607.01763); implement the configured-but-unenforced step-0 "
        "pass@1 ≥ 0.55 abort before launching."),
}

HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<title>VP → Translation: status report</title><style>
 body{font:15px/1.55 ui-monospace,Menlo,monospace;background:#101010;color:#d6d6d6;
      margin:0 auto;padding:28px 22px;max-width:1150px}
 h1{font-size:21px;color:#fff;margin:0 0 4px} h2{font-size:17px;color:#8fb8ff;margin:34px 0 10px}
 h3{font-size:14px;color:#bbb;margin:18px 0 6px}
 .sub{color:#888;font-size:13px;margin-bottom:22px}
 li{margin:7px 0} b{color:#fff} .dim{color:#8a8a8a}
 .verdict{background:#161d16;border:1px solid #2c4a2c;border-radius:8px;padding:12px 16px;margin:12px 0}
 .warn{background:#1d1a14;border:1px solid #4a3d20;border-radius:8px;padding:12px 16px;margin:12px 0}
 table{border-collapse:collapse;margin:10px 0;width:100%}
 td,th{border:1px solid #2c2c2c;padding:6px 9px;text-align:left;font-size:13px;vertical-align:top}
 th{color:#9db8d8;background:#161616}
 .score{font-size:16px;color:#fff;white-space:nowrap}
 .pending{color:#c9a227;font-style:italic}
 /* example browser */
 #probes,#modelrow{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
 .pill{background:#1b1b1b;border:1px solid #333;border-radius:14px;padding:3px 11px;
       cursor:pointer;font-size:12.5px;color:#bbb;user-select:none}
 .pill.on{background:#24406e;border-color:#3b64a8;color:#fff}
 #excard{background:#181818;border:1px solid #2c2c2c;border-radius:8px;padding:12px;margin-top:10px}
 #excard pre{white-space:pre-wrap;word-break:break-word;font-size:13px;max-height:320px;overflow:auto;margin:6px 0}
 .badge{display:inline-block;border-radius:4px;padding:1px 7px;font-size:11.5px;margin-left:8px}
 .b-EOS{background:#5a2323;color:#f4b8b8}.b-chat{background:#1e4620;color:#b8e6bb}
 .b-trans{background:#1e3a52;color:#b3d6f2}.b-think{background:#4a3a14;color:#e8d49a}
 .b-answr{background:#3a2a52;color:#d0bcf0}
 .note{color:#777;font-size:12px}
 .matrix td{text-align:center;font-size:12px;padding:4px 6px}
</style></head><body>
<h1>Does vidyut-prakriya morphology training improve EN→SA translation?</h1>
<div class="sub">Status report · Qwen3-4B campaign (15 mixture arms + GRPO-r3) · all models
servable via <span style="color:#aaa">serving/serve.sh</span> · examples below are real outputs,
bf16, enable_thinking=False, T=0.2</div>

<h2>1 · What is wrong with the current models</h2>
<ul>
<li><b>Instruction-following is destroyed.</b> Explicit, trivial instructions ("answer with
exactly one word", "reply with only this JSON") are followed by <b>0 of 6</b> fine-tuned
models in the battery below, while base Qwen3-4B follows every one. The failure is usually
total silence: the model emits end-of-turn as its <i>first token</i>. The same immunity holds
inside the trained format — a scaffold instruction to derive the verb before translating was
executed in <b>0/750</b> eval generations.</li>
<li><b>The models are siloed into exactly two prompt programs.</b> Every input is routed by
surface format: the translation template triggers an instant <code>&lt;translation&gt;</code>
(zero deliberation, 8/8 models), the drill costume triggers thinking + a one-word verb form
(the whole program including its output format — chrF collapses −32 when it fires), and the
routing ignores content: one arm translated a JSON-echo <i>instruction</i> into Sanskrit.
No prompt reaches a composed behavior (derive <i>and</i> translate).</li>
<li><b>Everything outside the two silos falls off an EOS cliff — but the abilities are
suppressed, not erased.</b> Off-format prompts get 1-token empty completions from most arms
(the more translation SFT, the harder the collapse — the pure-drill arm still chats). Halving
the adapter (<code>-avg</code> twins = exact 50/50 weight average with base) restores chat in
most cells (s67-avg: 5/6), while grpo-r3-avg stays silent because its anchor is its already-
collapsed SFT parent. Recovery-by-interpolation is the wrapper hypothesis made visible.</li>
</ul>

<h3>Evidence browser — 72 real outputs (9 probes × 8 models)</h3>
<div class="note">Pick a probe, then a model. Badge = behavior class. No generation happens —
these are frozen outputs from the live serving stack.</div>
<div id="probes"></div>
<div id="modelrow"></div>
<div id="excard"><span class="dim">select a probe + model</span></div>
<h3>Behavior matrix</h3>
<div id="matrix"></div>

<h2>2 · Temporary conclusion</h2>
<div class="verdict">
Under this recipe (completion-only SFT on drill traces + translation pairs at 4B, then
verified-reward GRPO on drills), morphological skill does <b>not</b> transfer to EN→SA
translation. Drill accuracy moved 0.45% → 87.9% pass@16 while <b>four</b> translation
instruments — chrF, chrF++, an LLM-judge scalar (GEMBA-DA_ref) and a grammar-error count
(GEMBA-MQM, judge-calibrated: 76% span-exact detection of injected inflection errors) —
stayed flat within confidence intervals (paired Samayik DA Δ +0.53 [−0.50, +1.59]). The
mechanism is now identified: the two skills live behind format-locked doors, are not
composable by any prompt, and the fine-tuning that installed them also stripped the
instruction-following a transfer pathway would need. <b>This is a verdict on the recipe at
this scale — not yet on the hypothesis.</b>
</div>

<h2>3 · Is the question settled?</h2>
<ul>
<li><b>Settled (for 4B + this recipe):</b> the correlation answer is no — controlled
matched-token titration (same translation tokens, +0/+5/+10M drill tokens → chrF and judge
metrics flat), RL-only contrast (+16.3pp drill pass@1, all translation metrics unchanged),
and the null survives a grammar-sensitive, calibrated instrument with ~10–20× headroom.</li>
<li><b>Not settled in general — the remaining outs:</b></li>
<li class="dim" style="margin-left:22px">— <b>Scale:</b> everything is one 4B model; composition
ability is known to improve with scale. (The 14B base probe below is the first data point.)</li>
<li class="dim" style="margin-left:22px">— <b>Recipe confound:</b> the SFT that installed the skills
also destroyed instruction-following and general chat; a model that can still follow
instructions might be able to <i>use</i> its drill skill when asked. The transfer failure and
the capability collapse are currently inseparable.</li>
<li class="dim" style="margin-left:22px">— <b>Support mismatch:</b> drills cover one paradigm cell
per (dhātu, lakāra) sampled over the whole grid; prose is dominated by a few common cells.
Zero transfer is partly a distribution gap, not only a generalization failure.</li>
<li class="dim" style="margin-left:22px">— <b>Task narrowness:</b> "morphology" here = finite-verb
conjugation only (no nominal declension, sandhi, kṛdanta); the headline claim should say
<i>verb-drill</i> training.</li>
<li class="dim" style="margin-left:22px">— <b>Untested designs:</b> curriculum (drills-first →
translation SFT), bridge/composition SFT (~100 examples), and translation-side RL with a
vidyut grammaticality reward all remain open.</li>
<li><b>Bottom line:</b> "VP drills don't help EN→SA translation at 4B with disjoint-format
SFT" is established. "VP morphology cannot help translation" is <b>not</b> — the honest
statement is that this recipe never gave the skill a pathway into translation.</li>
</ul>

<h2>4 · What to try next — ranked by chance the conclusion changes</h2>
<div class="note">"Conclusion changes" = the headline "VP drill training does not improve EN→SA
translation" would need rewriting. Each row states the falsifiable hypothesis for <i>why this
time would be different</i>. Ranked by P(flip), honest estimates.</div>
<table>
<tr><th style="width:22%">Intervention</th><th style="width:9%">P(conclusion changes)</th>
<th style="width:9%">Value /10</th><th>Hypothesis — what would be different this time, and why</th></tr>
<tr>
 <td><b>1 · Broader SFT rerun</b>: mixture + general instruction/chat replay + KL-to-base
 anchor, then GRPO (~$60–120)</td>
 <td class="score">~30%</td>
 <td class="score">8.5</td>
 <td><b>Hypothesis: the null was produced by a model with no pathway to EXPRESS transfer,
 so removing the blockage changes the result.</b> Transfer can surface two ways: implicit
 weight-sharing (tested — flat on 4 metrics) or behavioral composition (never tested,
 because the recipe destroyed the machinery it needs: instructions don't bind → the
 derive-then-translate scaffold executed in 0/750 generations; chat collapse → off-format
 prompts die at the EOS cliff before grammar could show). Replay + KL keeps completion
 entropy up, so format doors stay soft, instructions keep binding, and the elicitation
 experiments become <i>runnable</i> instead of vacuous. Why ~30% and not more: the
 weight-sharing null (matched-token titration) is real and would likely persist — this
 mainly opens the composed/elicited channel. Either outcome upgrades the claim: a flip
 shows transfer was recipe-blocked; a surviving null upgrades "recipe artifact" to "real
 dissociation in a general, instruction-following model."</td>
</tr>
<tr>
 <td><b>2 · Composition/bridge SFT</b>: ~100 derive-then-translate examples on the current
 policy (~$5)</td>
 <td class="score">~25%</td>
 <td class="score">7</td>
 <td><b>Hypothesis: both programs exist (drill thinking fires 94–99% behind its door;
 translation at chrF 41 behind its own) — only the wire between them is missing, and the
 wrapper literature says wires cost ~100 examples.</b> If grammar-in-translation improves
 after a $5 fine-tune, the conclusion flips to "drills DID deposit usable skill; transfer
 needs composition supervision, not more drills." Why only ~25%: the drill-costume
 experiment showed the derivation engine engaging real sentences poorly (derived verbs
 matched the reference verb ~1% of the time — support mismatch between drilled paradigm
 cells and prose) — so the wire may connect a skill that misfires on out-of-distribution
 content. That partial outcome is still informative: it localizes the failure to skill
 coverage rather than wiring.</td>
</tr>
<tr>
 <td><b>3 · Bigger base (Qwen3-14B)</b>, same recipe</td>
 <td class="score" id="rate-14b">__14B_P__</td>
 <td class="score">__14B_VALUE__</td>
 <td id="cell-14b"><b>Hypothesis: two scale effects could change the result — (a) a higher
 base floor (more latent Sanskrit/morphology from pretraining) and (b) capacity: skill
 composition and interference-resistance improve with size, so the same SFT might weld
 less and generalize more.</b> The falsifiable part being measured right now: if base 14B
 is still ≈0% on drills (like every ≤20B model in our earlier sweeps), then scale alone
 buys no new pathway and the whole pipeline just costs 3× more — P stays low. If 14B
 escapes the floor (especially with native thinking), the capability-threshold story gains
 teeth and the recipe deserves one 14B run. __14B_READING__</td>
</tr>
<tr>
 <td><b>4 · Translation-side RL</b> with vidyut grammaticality reward (from an SFT policy)</td>
 <td class="score">~10%</td>
 <td class="score">7.5</td>
 <td><b>Hypothesis: none about transfer — this replaces the transfer bet rather than
 re-testing it.</b> It optimizes grammar <i>inside</i> translation directly (verified,
 unhackable reward; Hu et al. 2026 precedent), so it would likely produce a better
 grammatical translator (~60–70% for a positive result) — but a win would NOT show drill
 transfer, and so mostly doesn't change the headline (~10%: only if the reward works
 dramatically better on drill-pretrained arms than on pure-translation arms, which would
 itself be evidence of latent transfer). High value as the constructive sequel; low value
 as a test of the original question.</td>
</tr>
<tr>
 <td><b>5 · SDPO</b> (from base / from SFT checkpoint)</td>
 <td class="score">~5%</td>
 <td class="score" id="rate-sdpo">__SDPO_RATING__</td>
 <td id="cell-sdpo"><b>Hypothesis: none that touches translation — SDPO attacks drill
 pass@1, and we already know +16.3pp of drill skill (GRPO-r3) moved translation by 0.0 on
 four metrics.</b> Even a perfect SDPO run (rescuing the pass@8=0 tasks where GRPO has
 provably zero gradient) would add more of the same drill skill whose translation coupling
 is measured at nil — so P(headline changes) ≈ 5%. Run it for the task-side result, not
 the transfer question. __SDPO_READING__</td>
</tr>
</table>

<h2>Appendix · Qwen3-14B base VP probe (669×16, protocol-identical)</h2>
<div id="app14b" class="warn">__14B_BLOCK__</div>

<h2>Appendix · SDPO feasibility</h2>
<div id="appsdpo" class="warn">__SDPO_BLOCK__</div>

<div class="note" style="margin-top:30px">Sources: misc/figures/data-mixture-results.md
(all metric tables + GEMBA addendum + judge calibration), misc/answer-key-ceiling/ (chrF
ceiling), evals-elicitation/ + evals-conjprompt/ (format-lock experiments),
misc/report_examples.json (this battery). Serving stack: serving/serve.sh.</div>

<script>
const EX = __EXAMPLES__;
const MODELS = ["base","tb20m-samayik100","tb20m-samayik67","tb20m-samayik0","grpo-r3",
                "tb20m-samayik100-avg","tb20m-samayik67-avg","grpo-r3-avg"];
const cat = o => { o=o.trim();
  if(!o) return "EOS";
  if(o.includes("<translation>")) return "trans";
  if(o.includes("<thinking>")) return "think";
  if(o.includes("<answer>")) return "answr";
  return "chat"; };
const probes = [...new Set(EX.map(e=>e.probe))];
let curP = probes[0], curM = "base";
const pdiv=document.getElementById("probes"), mdiv=document.getElementById("modelrow");
function render(){
  pdiv.innerHTML = probes.map(p=>`<span class="pill ${p===curP?"on":""}" onclick="setP('${p}')">${p}</span>`).join("");
  mdiv.innerHTML = MODELS.map(m=>{
    const e = EX.find(x=>x.probe===curP && x.model===m);
    const c = e?cat(e.output):"?";
    return `<span class="pill ${m===curM?"on":""}" onclick="setM('${m}')">${m.replace("tb20m-samayik","s")}<span class="badge b-${c}">${c}</span></span>`;
  }).join("");
  const e = EX.find(x=>x.probe===curP && x.model===curM);
  if(!e){document.getElementById("excard").innerHTML="<span class=dim>no example</span>";return;}
  const esc=s=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;");
  document.getElementById("excard").innerHTML =
    `<div class="dim">${e.note} · template: <b>${e.template}</b> · ${e.seconds}s</div>
     <div style="margin-top:6px"><span class="dim">input:</span> ${esc(e.input)}</div>
     <div style="margin-top:6px"><span class="dim">output</span><span class="badge b-${cat(e.output)}">${cat(e.output)}</span></div>
     <pre>${e.output.trim()?esc(e.output):"∅  (model emitted end-of-turn as its first token)"}</pre>`;
}
function setP(p){curP=p;render()} function setM(m){curM=m;render()}
render();
// matrix
let mt = `<table class="matrix"><tr><th>probe</th>${MODELS.map(m=>`<th>${m.replace("tb20m-samayik","s")}</th>`).join("")}</tr>`;
for(const p of probes){
  mt += `<tr><td style="text-align:left">${p}</td>` + MODELS.map(m=>{
    const e = EX.find(x=>x.probe===p && x.model===m);
    const c = e?cat(e.output):"–";
    return `<td><span class="badge b-${c}" style="margin:0">${c}</span></td>`;}).join("") + "</tr>";
}
document.getElementById("matrix").innerHTML = mt + "</table>";
</script></body></html>
"""


def block_14b():
    if RESULTS_14B["status"] == "pending":
        return ("<b>PENDING</b> — " + RESULTS_14B["reading"])
    rows = []
    for key, label in (("nothink", "thinking OFF (training-comparable, 669×16)"),
                       ("think", "thinking ON (native reasoning, 669×4)")):
        r = RESULTS_14B[key]
        if r is None:
            rows.append(f"<tr><td>{label}</td><td colspan=3 class=pending>running…</td></tr>")
            continue
        rows.append(f"<tr><td>{label}</td><td>{r['pass1']}</td><td>{r['pass16']}</td>"
                    f"<td>{r['tag']}</td></tr>")
    return ("<table><tr><th>config</th><th>pass@1</th><th>pass@16</th><th>answer-tag rate</th></tr>"
            + "".join(rows) + "</table>" + RESULTS_14B["reading"]
            + "<div class='note'>4B base reference: 0.03% pass@1 / 0.45% pass@16.</div>")


def block_sdpo():
    if SDPO_VERDICT["status"] == "pending":
        return "<b>PENDING</b> — " + SDPO_VERDICT["one_line"]
    return f"<b>{SDPO_VERDICT['one_line']}</b><br><br>{SDPO_VERDICT['detail']}"


html = (HTML
        .replace("__EXAMPLES__", json.dumps(EXAMPLES, ensure_ascii=False))
        .replace("__14B_BLOCK__", block_14b())
        .replace("__SDPO_BLOCK__", block_sdpo())
        .replace("__14B_READING__", RESULTS_14B["reading"])
        .replace("__14B_P__", RESULTS_14B.get("p_flip", "<span class='pending'>pending<br>(prior ~10–15%)</span>"))
        .replace("__14B_VALUE__", RESULTS_14B.get("value", "<span class='pending'>pending</span>"))
        .replace("__SDPO_RATING__", SDPO_VERDICT.get("rating", "<span class='pending'>pending</span>"))
        .replace("__SDPO_READING__", SDPO_VERDICT["one_line"]))
OUT.write_text(html)
print(f"wrote {OUT} ({len(html):,} bytes, {len(EXAMPLES)} examples embedded)")
