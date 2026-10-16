"use strict";
const DATA = JSON.parse(document.getElementById("benchmark-data").textContent);
const FAMILY_NAMES = {tinanta:"Tiṅanta",taddhitanta:"Taddhitānta",krdanta:"Kṛdanta",subanta:"Subanta"};
const METRICS = {tokens:{label:"output tokens",unit:"tokens"},duration:{label:"wall-clock duration",unit:"seconds"},cost:{label:"cost",unit:"USD"}};
const state = {family:"average",score:"answer",frontierMetric:"cost",medianMetric:"tokens",frontierLog:true,medianLog:false,
  showSd:true,distributionMetric:"tokens",distributionLog:true,pairA:"astra-xhigh",pairB:"opus55-xhigh"};
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pct = x => x.toFixed(3)+"%";
const integer = x => new Intl.NumberFormat("en-US",{maximumFractionDigits:1}).format(x);
const color = model => `var(--${model.provider})`;
const effortLabel = model => model.effort === "high" ? "HIGH" : "xHigh";
const markerClass = model => ({openai:"legend-dot",anthropic:"legend-diamond",google:"legend-square"})[model.provider];

function aggregate(values,mode){
  if(mode==="maximum") return Math.max(...values);
  if(mode==="minimum") return Math.min(...values);
  return values.reduce((a,b)=>a+b,0)/values.length;
}
function selectedRows(){
  const individual = DATA.families.includes(state.family);
  return DATA.models.map(model=>{
    const families = individual ? [model.families[state.family]] : DATA.families.map(f=>model.families[f]);
    const combine = fn=>aggregate(families.map(fn),state.family);
    const mean={},median={};
    for(const key of Object.keys(METRICS)){mean[key]=combine(f=>f.mean[key]);median[key]=combine(f=>f.median[key]);}
    return {...model,answer:combine(f=>f.answer),strict:combine(f=>f.strict),score:combine(f=>f[state.score]),mean,median,n:individual?5000:20000,
      sd:state.family==="average"?model.familyScoreSd[state.score]:null};
  });
}
function scopeKey(){return DATA.families.includes(state.family)?state.family:"all";}
function scopeLabel(){return scopeKey()==="all"?"All 20,000 tasks pooled":`${FAMILY_NAMES[state.family]} · 5,000 tasks`;}
function scopedRows(){return DATA.models.map(m=>{const stats=scopeKey()==="all"?m.pooled:m.families[state.family];return {...m,...stats,score:stats[state.score]};});}
function comparison(){return DATA.comparisons[scopeKey()][state.score];}
function pareto(rows,stat,metric){
  return rows.filter(a=>!rows.some(b=>b.id!==a.id && b[stat][metric]<=a[stat][metric] && b.score>=a.score && (b[stat][metric]<a[stat][metric] || b.score>a.score))).sort((a,b)=>a[stat][metric]-b[stat][metric] || b.score-a.score);
}
function formatMetric(value,metric,compact=false){
  if(metric==="cost"){
    if(compact) return "$"+(value>=1?value.toFixed(1):value>=.01?value.toFixed(2):value.toFixed(value>=.001?3:4));
    return "$"+value.toFixed(value<.01?6:5);
  }
  if(metric==="duration") return value>=60 ? (value/60).toFixed(compact?1:2)+" min" : value.toFixed(compact?0:2)+" s";
  return compact && value>=1000 ? (value/1000).toFixed(value>=10000?0:1)+"k" : integer(value);
}
function modeLabel(){return FAMILY_NAMES[state.family] || ({average:"Average across four families",maximum:"Maximum across four families",minimum:"Minimum across four families"})[state.family];}
function scoreLabel(){return state.score==="answer"?"Answer accuracy":"Answer + required format";}
function niceStep(span,count){const raw=span/count;const power=10**Math.floor(Math.log10(raw||1));const n=raw/power;return (n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*power;}
function axisFor(values,log,width){
  const min=Math.min(...values),max=Math.max(...values);
  if(log && min>0){
    const lo=Math.log10(min)-.13,hi=Math.log10(max)+.16;
    let ticks=[];
    for(let p=Math.floor(lo);p<=Math.ceil(hi);p++) for(const m of [1,2,5]){const v=m*10**p;if(Math.log10(v)>=lo && Math.log10(v)<=hi)ticks.push(v);}
    if(ticks.length>7)ticks=ticks.filter((_,i)=>i%2===0);
    if(width<500 && ticks.length>4)ticks=ticks.filter((_,i)=>i%2===0);
    return {ratio:v=>(Math.log10(v)-lo)/(hi-lo),ticks};
  }
  const step=niceStep(max*1.15,width<500?3:5),hi=Math.ceil(max*1.12/step)*step;
  return {ratio:v=>v/hi,ticks:Array.from({length:Math.floor(hi/step)+1},(_,i)=>i*step)};
}

function showTooltip(event,row,stat,metric,frontier=false){
  const tip=$("tooltip");
  tip.innerHTML=`<strong>${esc(row.label)}</strong><div class="tip-sub">${esc(modeLabel())} · ${effortLabel(row)}</div><div class="tip-row"><span>Answer accuracy</span><span>${pct(row.answer)}</span></div><div class="tip-row"><span>Answer + format</span><span>${pct(row.strict)}</span></div>${row.sd!==null&&row.sd!==undefined?`<div class="tip-row"><span>SD across 4 families</span><span>${row.sd.toFixed(3)} pp</span></div>`:""}<div class="tip-row"><span>${stat==="mean"?"Mean":"Median"} ${esc(METRICS[metric].label)}</span><span>${formatMetric(row[stat][metric],metric)}</span></div>${frontier?'<div class="tip-foot">On the Pareto frontier for this view.</div>':""}`;
  tip.hidden=false;
  const bounds=event.currentTarget.getBoundingClientRect();
  const x=Number.isFinite(event.clientX) && event.type!=="focus"?event.clientX:bounds.left+bounds.width/2;
  const y=Number.isFinite(event.clientY) && event.type!=="focus"?event.clientY:bounds.top;
  const tw=tip.offsetWidth||235,th=tip.offsetHeight||160;
  tip.style.left=Math.max(12,Math.min(window.innerWidth-tw-12,x+15))+"px";
  tip.style.top=Math.max(12,Math.min(window.innerHeight-th-12,y+15))+"px";
}
function hideTooltip(){$("tooltip").hidden=true;}
function bindTooltip(el,row,stat,metric,frontier=false){
  el.addEventListener("pointerenter",e=>showTooltip(e,row,stat,metric,frontier));
  el.addEventListener("pointermove",e=>showTooltip(e,row,stat,metric,frontier));
  el.addEventListener("pointerleave",hideTooltip);
  el.addEventListener("focus",e=>showTooltip(e,row,stat,metric,frontier));
  el.addEventListener("blur",hideTooltip);
}
function overlap(a,b){return Math.max(0,Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x))*Math.max(0,Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y));}
function placeLabels(points,box){
  const placed=[];
  return [...points].sort((a,b)=>b.row.score-a.row.score).map(point=>{
    const w=point.row.short.length*6.7+7,h=18;
    const candidates=[];
    for(const [dx,dy] of [[13,-10],[13,10],[-w-13,-10],[-w-13,10],[-w/2,-26],[-w/2,17],[13,-33],[-w-13,-33],[13,33],[-w-13,33],[-w/2,-47],[-w/2,39]]){
      const rect={x:Math.max(box.left,Math.min(box.right-w,point.x+dx)),y:Math.max(box.top,Math.min(box.bottom-h,point.y+dy)),w,h};
      let penalty=placed.reduce((sum,r)=>sum+overlap(rect,r)*50,0);
      for(const p of points)penalty+=overlap(rect,{x:p.x-8,y:p.y-8,w:16,h:16})*35;
      penalty+=Math.hypot(rect.x+w/2-point.x,rect.y+h/2-point.y);
      candidates.push({...rect,penalty});
    }
    candidates.sort((a,b)=>a.penalty-b.penalty);const rect=candidates[0];placed.push(rect);
    return {...point,rect};
  });
}

function drawScatter(containerId,rows,stat,metric,isFrontier,log){
  const container=$(containerId),width=Math.max(288,container.clientWidth||960),mobile=width<540;
  const height=mobile?335:370,pad={left:mobile?40:54,right:mobile?17:26,top:34,bottom:51};
  const xaxis=axisFor(rows.map(r=>r[stat][metric]),log,width);
  const lowest=Math.min(...rows.map(r=>r.score));
  const yMin=Math.max(0,Math.floor((lowest-4)/10)*10),yMax=100;
  const x=v=>pad.left+xaxis.ratio(v)*(width-pad.left-pad.right),y=v=>pad.top+(yMax-v)/(yMax-yMin)*(height-pad.top-pad.bottom);
  const front=pareto(rows,stat,metric),frontIds=new Set(front.map(r=>r.id));
  const scoreName=scoreLabel();
  let html=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="${containerId}-title ${containerId}-desc"><title id="${containerId}-title">${esc(scoreName)} versus ${stat} ${esc(METRICS[metric].label)}</title><desc id="${containerId}-desc">${esc(modeLabel())}. ${rows.map(r=>`${r.label}: ${pct(r.score)}, ${formatMetric(r[stat][metric],metric)}.`).join(" ")} ${isFrontier?"Dashed line: Pareto frontier.":""}</desc>`;
  const yStep=niceStep(yMax-yMin,5);
  for(let v=yMin;v<=yMax+.001;v+=yStep) html+=`<line class="grid-line" x1="${pad.left}" x2="${width-pad.right}" y1="${y(v)}" y2="${y(v)}"/><text class="axis-text" x="${pad.left-11}" y="${y(v)+3}" text-anchor="end">${v}%</text>`;
  for(const v of xaxis.ticks) html+=`<line class="grid-line" x1="${x(v)}" x2="${x(v)}" y1="${pad.top}" y2="${height-pad.bottom}"/><text class="axis-text" x="${x(v)}" y="${height-pad.bottom+20}" text-anchor="middle">${formatMetric(v,metric,true)}</text>`;
  html+=`<line class="axis-line" x1="${pad.left}" x2="${width-pad.right}" y1="${height-pad.bottom}" y2="${height-pad.bottom}"/><text class="axis-caption" x="${pad.left}" y="14">${esc(scoreName)} ↑</text><text class="axis-caption" x="${width-pad.right}" y="${height-5}" text-anchor="end">${stat==="mean"?"Mean":"Median"} ${esc(METRICS[metric].label)} / trial${log?" · log scale":""}</text>`;
  if(isFrontier && front.length>1){
    const path=front.map((r,i)=>`${i?"L":"M"}${x(r[stat][metric])},${y(r.score)}`).join(" ");
    html+=`<path class="frontier-path" d="${path}"/>`;
  }
  const points=rows.map(row=>({row,x:x(row[stat][metric]),y:y(row.score)}));
  const labels=placeLabels(points,{left:pad.left+3,right:width-pad.right,top:pad.top-8,bottom:height-pad.bottom-3});
  for(const {row,x:px,y:py,rect} of labels){
    const lx=Math.max(rect.x,Math.min(rect.x+rect.w,px)),ly=Math.max(rect.y,Math.min(rect.y+rect.h,py));
    if(Math.hypot(lx-px,ly-py)>17) html+=`<line class="label-leader" x1="${px}" y1="${py}" x2="${lx}" y2="${ly}"/>`;
    html+=`<text class="point-label" x="${rect.x+3}" y="${rect.y+12}" pointer-events="none">${esc(row.short)}</text>`;
  }
  for(const {row,x:px,y:py} of points){
    const accessible=`${row.label}, ${pct(row.score)}, ${stat} ${METRICS[metric].label}: ${formatMetric(row[stat][metric],metric)}`;
    html+=`<g class="model-point" tabindex="0" role="img" data-model="${row.id}" aria-label="${esc(accessible)}" style="color:${color(row)}"><title>${esc(accessible)}</title><circle class="point-halo" cx="${px}" cy="${py}" r="12"/><circle cx="${px}" cy="${py}" r="15" fill="transparent"/>`;
    if(row.provider==="anthropic")html+=`<path class="point-shape" fill="currentColor" d="M${px},${py-7}l7,7 -7,7 -7,-7z"/>`;
    else if(row.provider==="google")html+=`<rect class="point-shape" x="${px-6}" y="${py-6}" width="12" height="12" fill="currentColor"/>`;
    else html+=`<circle class="point-shape" cx="${px}" cy="${py}" r="6" fill="currentColor"/>`;
    html+="</g>";
  }
  html+="</svg>";container.innerHTML=html;
  container.querySelectorAll("[data-model]").forEach(el=>{const row=rows.find(r=>r.id===el.dataset.model);bindTooltip(el,row,stat,metric,isFrontier&&frontIds.has(row.id));});
  return front;
}

function renderLeaderboard(rows){
  const sorted=[...rows].sort((a,b)=>b.score-a.score);
  const show=state.showSd&&state.family==="average";
  $("show-sd").disabled=state.family!=="average";
  $("performance-error-note").textContent=state.family==="average"?(show?"Whiskers: mean ±1 population SD across four family scores (N = 4).":"Family SD hidden. Toggle to show variation across four family scores."):"Family SD is shown in the average view. This view shows the selected score only.";
  $("performance-chart").innerHTML=`<div class="board-header" aria-hidden="true"><span>MODEL / EFFORT</span><div class="board-ticks"><span>0</span><span>20</span><span>40</span><span>60</span><span>80</span><span>100%</span></div><span>${show?"MEAN ± SD":"SCORE"}</span></div>`+sorted.map(row=>{
    const lo=Math.max(0,row.score-(row.sd||0)),hi=Math.min(100,row.score+(row.sd||0));
    return `<div class="board-row" role="listitem" tabindex="0" data-model="${row.id}" aria-label="${esc(row.label)}, ${effortLabel(row)}, ${pct(row.score)}${show?`, standard deviation across families ${row.sd.toFixed(3)} percentage points`:""}"><div><div class="model-name"><i class="${markerClass(row)}" aria-hidden="true"></i>${esc(row.label.replace("Claude ",""))}</div><div class="model-effort">[${row.effort}]</div></div><div class="bar-lane" aria-hidden="true"><div class="bar-fill" style="--value:${row.score}%;--color:${color(row)}"></div>${show?`<span class="sd-whisker" data-sd="${row.sd}" style="left:${lo}%;width:${hi-lo}%"></span><span class="sd-center" style="left:${row.score}%"></span>`:""}</div><div class="board-value">${pct(row.score)}${show?`<small>± ${row.sd.toFixed(2)} pp</small>`:""}</div></div>`;
  }).join("");
  $("performance-chart").querySelectorAll("[data-model]").forEach(el=>bindTooltip(el,rows.find(r=>r.id===el.dataset.model),"mean",state.frontierMetric));
  const best=sorted[0],gap=best.score-sorted[1].score;
  $("performance-caption").innerHTML=`<span class="caption-label">READOUT</span><strong>${esc(best.label)}</strong> leads at <strong>${pct(best.score)}</strong> · ${gap.toFixed(3)} pp ahead of ${esc(sorted[1].short)}.${show?" Whiskers describe family variation, not repeated-run uncertainty.":""}`;
}

function render(){
  hideTooltip();const rows=selectedRows(),individual=DATA.families.includes(state.family);
  $("scope-note").textContent=individual?`${FAMILY_NAMES[state.family]} · 5,000 shared tasks per model. The family matrix retains all four columns for context.`:state.family==="average"?"Scores and efficiency summaries weight the four families equally. Distribution and paired-outcome plots pool all 20,000 tasks.":`${state.family==="maximum"?"Largest":"Smallest"} family value per metric in the performance and efficiency summaries. Distribution and paired-outcome plots pool all 20,000 tasks.`;
  $("performance-scope").textContent=individual?"5,000 tasks / model":state.family==="average"?"20,000 tasks / model":`${state.family==="maximum"?"Maximum":"Minimum"} of four family scores`;
  const front=drawScatter("frontier-chart",rows,"mean",state.frontierMetric,true,state.frontierLog);
  $("frontier-caption").innerHTML=`<span class="caption-label">FRONTIER</span><strong>${front.map(r=>esc(r.short)).join(" → ")}</strong>. No other included model is both at least as accurate and at least as efficient, with one strict improvement, at these points.`;
  renderLeaderboard(rows);
  renderOverview();renderFamilies();renderDistributions();renderFormat();renderConsensus();renderPairwise();
  $("efficiency-title").textContent="Score vs. median "+METRICS[state.medianMetric].label;
  drawScatter("median-chart",rows,"median",state.medianMetric,false,state.medianLog);
  const mostAccurate=[...rows].sort((a,b)=>b.score-a.score)[0];
  const economical=[...rows].sort((a,b)=>a.median[state.medianMetric]-b.median[state.medianMetric])[0];
  $("median-caption").innerHTML=`<span class="caption-label">READOUT</span><strong>${esc(mostAccurate.short)}</strong> reaches ${pct(mostAccurate.score)} at <strong>${formatMetric(mostAccurate.median[state.medianMetric],state.medianMetric)}</strong>. ${esc(economical.short)} has the lowest value on this axis at ${formatMetric(economical.median[state.medianMetric],state.medianMetric)}. ${individual?"Medians use all 5,000 selected responses.":"Medians are calculated per family, then combined using the selected aggregation."}`;
  $("data-table").innerHTML=[...rows].sort((a,b)=>b.score-a.score).map(r=>`<tr data-model="${r.id}"><td><a href="../${r.id}/manifest.json" title="Open ${esc(r.label)} source manifest">${esc(r.label)} ↗</a></td><td>${pct(r.answer)}</td><td>${pct(r.strict)}</td><td>${formatMetric(r.mean.cost,"cost")}</td><td>${integer(r.median.tokens)}</td><td>${formatMetric(r.median.duration,"duration")}</td><td>${formatMetric(r.median.cost,"cost")}</td></tr>`).join("");
  $("table-note").textContent=`${modeLabel()}. All costs in USD. Mean and median resource use refer to selected attempts; earlier failed/retried attempts are excluded. Model names open the source manifests.`;
  $("view-status").textContent=`Showing ${scoreLabel().toLowerCase()}, ${modeLabel().toLowerCase()}, for ${DATA.models.length} models.`;
}

$("family-select").addEventListener("change",e=>{state.family=e.target.value;render();});
$("score-select").addEventListener("change",e=>{state.score=e.target.value;render();});
$("frontier-metric").addEventListener("change",e=>{state.frontierMetric=e.target.value;render();});
$("median-metric").addEventListener("change",e=>{state.medianMetric=e.target.value;render();});
$("frontier-log").addEventListener("change",e=>{state.frontierLog=e.target.checked;render();});
$("median-log").addEventListener("change",e=>{state.medianLog=e.target.checked;render();});
$("show-sd").addEventListener("change",e=>{state.showSd=e.target.checked;render();});
$("distribution-metric").addEventListener("change",e=>{state.distributionMetric=e.target.value;renderDistributions();});
$("distribution-log").addEventListener("change",e=>{state.distributionLog=e.target.checked;renderDistributions();});
document.addEventListener("keydown",e=>{if(e.key==="Escape")hideTooltip();});
window.addEventListener("scroll",hideTooltip,{passive:true});

function setTheme(dark){document.documentElement.dataset.theme=dark?"dark":"light";$("theme-toggle").setAttribute("aria-label",`Switch to ${dark?"light":"dark"} theme`);$("theme-toggle").setAttribute("aria-pressed",String(dark));}
try{setTheme(localStorage.getItem("vp-results-theme")==="dark");}catch{setTheme(false);}
$("theme-toggle").addEventListener("click",()=>{const dark=document.documentElement.dataset.theme!=="dark";setTheme(dark);try{localStorage.setItem("vp-results-theme",dark?"dark":"light");}catch{}});
$("download-csv").addEventListener("click",()=>{
  const head=["model","provider","effort","family_view","answer_accuracy_percent","answer_and_format_percent","answer_family_sd_pp","strict_family_sd_pp","mean_cost_usd","mean_output_tokens","mean_duration_seconds","median_cost_usd","median_output_tokens","median_duration_seconds"];
  const values=selectedRows().sort((a,b)=>b.score-a.score).map(r=>[r.model,r.provider,r.effort,state.family,r.answer,r.strict,state.family==="average"?r.familyScoreSd.answer:"",state.family==="average"?r.familyScoreSd.strict:"",r.mean.cost,r.mean.tokens,r.mean.duration,r.median.cost,r.median.tokens,r.median.duration]);
  const csv=[head,...values].map(row=>row.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(",")).join("\r\n")+"\r\n";
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a");a.href=url;a.download=`vidyut-prakriya-v3-${state.family}.csv`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$("known-spend").textContent=new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(DATA.models.reduce((s,m)=>s+m.knownRunCost,0));
$("unknown-attempts").textContent=DATA.models.reduce((s,m)=>s+m.unknownCostAttempts,0);
$("source-links").innerHTML=DATA.models.map(m=>`<a href="../${m.id}/manifest.json">${esc(m.label)} ↗</a>`).join("");
$("updated-date").textContent="Completed "+new Date(DATA.updatedAt).toLocaleDateString("en-US",{timeZone:"UTC",month:"long",day:"numeric",year:"numeric"});
let resizeFrame;
window.addEventListener("resize",()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(render);});
render();
