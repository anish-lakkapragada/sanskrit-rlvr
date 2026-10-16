/* Embedded in the same script as benchmark_results.js. No network dependencies. */
function showDetail(event,title,items,foot=""){
  const tip=$("tooltip");
  tip.innerHTML=`<strong>${esc(title)}</strong>${items.map(([a,b])=>`<div class="tip-row"><span>${esc(a)}</span><span>${esc(b)}</span></div>`).join("")}${foot?`<div class="tip-foot">${esc(foot)}</div>`:""}`;
  tip.hidden=false;
  const bounds=event.currentTarget.getBoundingClientRect(),focused=event.type==="focus";
  const x=focused?bounds.left+bounds.width/2:event.clientX,y=focused?bounds.top:event.clientY;
  tip.style.left=Math.max(12,Math.min(window.innerWidth-(tip.offsetWidth||235)-12,x+15))+"px";
  tip.style.top=Math.max(12,Math.min(window.innerHeight-(tip.offsetHeight||160)-12,y+15))+"px";
}
function bindDetail(el,title,items,foot=""){
  for(const type of ["pointerenter","pointermove","focus"])el.addEventListener(type,e=>showDetail(e,title,items,foot));
  for(const type of ["pointerleave","blur"])el.addEventListener(type,hideTooltip);
}
function svgStart(id,width,height,title,description){
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="${id}-title ${id}-desc"><title id="${id}-title">${esc(title)}</title><desc id="${id}-desc">${esc(description)}</desc>`;
}
function renderOverview(){
  const rows=scopedRows(),best=[...rows].sort((a,b)=>b.score-a.score)[0],c=comparison(),all=c.consensus[DATA.models.length],none=c.consensus[0];
  const tiles=[{label:"Leading score",value:pct(best.score),sub:`${best.short} · ${scoreLabel().toLowerCase()}`,share:best.score,color:color(best)},
    {label:"All eight correct",value:(100*all/c.n).toFixed(1)+"%",sub:`${integer(all)} of ${integer(c.n)} shared tasks`,share:100*all/c.n,color:"var(--good)"},
    {label:"None correct",value:integer(none),sub:`${(100*none/c.n).toFixed(2)}% of ${scopeKey()==="all"?"all tasks":FAMILY_NAMES[state.family]}`,share:100*none/c.n,color:"var(--bad)"}];
  $("overview-strip").innerHTML=tiles.map(t=>`<div class="overview-item"><div class="overview-label">${esc(t.label)}</div><div class="overview-value">${t.value}</div><p class="overview-sub">${esc(t.sub)}</p><div class="overview-meter" aria-hidden="true"><span style="width:${t.share}%;background:${t.color}"></span></div></div>`).join("");
}
function renderFamilies(){
  const rows=[...DATA.models].sort((a,b)=>b.pooled[state.score]-a.pooled[state.score]);
  const maxima=Object.fromEntries(DATA.families.map(f=>[f,Math.max(...rows.map(r=>r.families[f][state.score]))]));
  $("family-matrix").innerHTML=`<table class="family-matrix"><caption class="sr-only">${esc(scoreLabel())} across all four task families. Click a score to filter the other plots.</caption><thead><tr><th scope="col">MODEL</th>${DATA.families.map(f=>`<th scope="col">${FAMILY_NAMES[f]}<small>n = 5,000</small></th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr><td><span class="model-name"><i class="${markerClass(r)}" aria-hidden="true"></i>${esc(r.short)}</span></td>${DATA.families.map(f=>{
    const score=r.families[f][state.score],winner=score===maxima[f];
    return `<td><button type="button" class="heat-cell${winner?" winner":""}${state.family===f?" selected":""}" data-model="${r.id}" data-family="${f}" aria-pressed="${state.family===f}" aria-label="${esc(r.label)}, ${FAMILY_NAMES[f]}, ${scoreLabel()}, ${pct(score)}${winner?", highest in this family":""}. Filter to this family." style="--intensity:${score*.52}%">${score.toFixed(2)}%</button></td>`;
  }).join("")}</tr>`).join("")}</tbody></table>`;
  $("family-matrix").querySelectorAll("button").forEach(el=>{
    const r=DATA.models.find(m=>m.id===el.dataset.model),f=el.dataset.family,stats=r.families[f];
    bindDetail(el,r.label,[["Task family",FAMILY_NAMES[f]],[scoreLabel(),pct(stats[state.score])],["Correct",`${integer(state.score==="answer"?stats.correct:stats.strictCorrect)} / 5,000`]],"Click to filter the plots to this family.");
    el.addEventListener("click",()=>{state.family=f;$("family-select").value=f;render();$("family-matrix").querySelector(`[data-model="${r.id}"][data-family="${f}"]`).focus();});
  });
  const averages=DATA.families.map(f=>({family:f,value:rows.reduce((n,r)=>n+r.families[f][state.score],0)/rows.length})).sort((a,b)=>a.value-b.value);
  $("family-caption").innerHTML=`<span class="caption-label">CROSS-MODEL MEAN</span><strong>${FAMILY_NAMES[averages[0].family]}</strong> ${averages[0].value.toFixed(2)}% <span aria-hidden="true">→</span> <strong>${FAMILY_NAMES[averages.at(-1).family]}</strong> ${averages.at(-1).value.toFixed(2)}%.`;
}
function renderDistributions(){
  const metric=state.distributionMetric,rows=scopedRows().sort((a,b)=>a.distribution[metric].median-b.distribution[metric].median);
  const container=$("distribution-chart");container.style.minWidth="640px";
  const width=Math.max(640,container.clientWidth||960),height=rows.length*46+65,pad={left:145,right:95,top:22,bottom:43};
  const values=rows.flatMap(r=>[r.distribution[metric].p10,r.distribution[metric].p90]);
  const useLog=state.distributionLog&&values.every(v=>v>0),axis=axisFor(values,useLog,width-pad.left-pad.right);
  const x=v=>pad.left+axis.ratio(v)*(width-pad.left-pad.right),y=i=>pad.top+i*46+23;
  let html=svgStart("distribution",width,height,`Distribution of ${METRICS[metric].label}`,`${scopeLabel()}. Whiskers mark the 10th and 90th percentiles; boxes mark the middle 50%; the center line is the median.`);
  for(const tick of axis.ticks)html+=`<line class="grid-line" x1="${x(tick)}" x2="${x(tick)}" y1="${pad.top-4}" y2="${height-pad.bottom}"/><text class="axis-text" x="${x(tick)}" y="${height-pad.bottom+20}" text-anchor="middle">${formatMetric(tick,metric,true)}</text>`;
  html+=`<text class="axis-caption" x="0" y="11">MODEL</text><text class="axis-caption" x="${width-1}" y="11" text-anchor="end">MEDIAN</text><text class="axis-caption" x="${width-pad.right}" y="${height-3}" text-anchor="end">${esc(METRICS[metric].label)}${useLog?" · log scale":""}</text>`;
  rows.forEach((r,i)=>{const q=r.distribution[metric],cy=y(i);
    html+=`<line class="row-rule" x1="0" x2="${width}" y1="${cy+22}" y2="${cy+22}"/><g class="box-point" tabindex="0" data-model="${r.id}" aria-label="${esc(r.label)}, median ${formatMetric(q.median,metric)}, P10 ${formatMetric(q.p10,metric)}, P90 ${formatMetric(q.p90,metric)}" style="color:${color(r)}"><rect x="0" y="${cy-21}" width="${width}" height="42" fill="transparent"/><text class="row-label" x="0" y="${cy+4}">${esc(r.short)}</text><line class="box-range" x1="${x(q.p10)}" x2="${x(q.p90)}" y1="${cy}" y2="${cy}"/><line class="box-range" x1="${x(q.p10)}" x2="${x(q.p10)}" y1="${cy-5}" y2="${cy+5}"/><line class="box-range" x1="${x(q.p90)}" x2="${x(q.p90)}" y1="${cy-5}" y2="${cy+5}"/><rect class="box-body" x="${x(q.q1)}" y="${cy-9}" width="${Math.max(.5,x(q.q3)-x(q.q1))}" height="18"/><line class="box-median" x1="${x(q.median)}" x2="${x(q.median)}" y1="${cy-11}" y2="${cy+11}"/><text class="row-stat" x="${width-1}" y="${cy+4}" text-anchor="end">${formatMetric(q.median,metric,true)}</text></g>`;
  });
  container.innerHTML=html+"</svg>";
  container.querySelectorAll("[data-model]").forEach(el=>{const r=rows.find(r=>r.id===el.dataset.model),q=r.distribution[metric];bindDetail(el,r.label,[["P10",formatMetric(q.p10,metric)],["P25",formatMetric(q.q1,metric)],["Median",formatMetric(q.median,metric)],["P75",formatMetric(q.q3,metric)],["P90",formatMetric(q.p90,metric)],["P99",formatMetric(q.p99,metric)]],scopeLabel());});
  $("distribution-scope").textContent=scopeLabel();
  const tails=rows.filter(r=>r.distribution[metric].median>0).map(r=>({r,ratio:r.distribution[metric].p90/r.distribution[metric].median})).sort((a,b)=>b.ratio-a.ratio);
  $("distribution-caption").innerHTML=`<span class="caption-label">TAIL / MEDIAN</span><strong>${esc(tails[0].r.short)}</strong> reaches ${tails[0].ratio.toFixed(1)}× at P90. Hover or focus a row for all percentiles.`;
}
function renderFormat(){
  const rows=scopedRows().sort((a,b)=>(b.answer-b.strict)-(a.answer-a.strict)),container=$("format-chart"),width=Math.max(288,container.clientWidth||480),height=356;
  const left=82,right=52,top=23,bottom=35,x=v=>left+v/100*(width-left-right),y=i=>top+16+i*36;
  let html=svgStart("format",width,height,"Correct answers versus required format",`${scopeLabel()}. Filled dots show answer accuracy; hollow dots show strict accuracy.`);
  for(const tick of [0,25,50,75,100])html+=`<line class="grid-line" x1="${x(tick)}" x2="${x(tick)}" y1="${top-5}" y2="${height-bottom}"/><text class="axis-text" x="${x(tick)}" y="${height-bottom+20}" text-anchor="middle">${tick}%</text>`;
  html+=`<text class="axis-caption" x="${width}" y="10" text-anchor="end">GAP · pp</text>`;
  rows.forEach((r,i)=>{const cy=y(i),gap=r.answer-r.strict;html+=`<g class="dumbbell-row" tabindex="0" data-model="${r.id}" style="color:${color(r)}" aria-label="${esc(r.label)}, answer ${pct(r.answer)}, strict ${pct(r.strict)}, format penalty ${gap.toFixed(3)} percentage points"><rect x="0" y="${cy-16}" width="${width}" height="32" fill="transparent"/><text class="row-label" x="0" y="${cy+4}">${esc(r.short)}</text><line class="gap-line" x1="${x(r.strict)}" x2="${x(r.answer)}" y1="${cy}" y2="${cy}" stroke="currentColor" stroke-width="3"/><circle cx="${x(r.strict)}" cy="${cy}" r="5" fill="var(--bg)" stroke="currentColor" stroke-width="1.5"/><circle cx="${x(r.answer)}" cy="${cy}" r="3" fill="currentColor"/><text class="row-stat" x="${width}" y="${cy+4}" text-anchor="end">${gap.toFixed(2)}</text></g>`;});
  container.innerHTML=html+"</svg>";
  container.querySelectorAll("[data-model]").forEach(el=>{const r=rows.find(r=>r.id===el.dataset.model);bindDetail(el,r.label,[["Answer accuracy",pct(r.answer)],["Answer + format",pct(r.strict)],["Correct, wrong format",integer(r.correct-r.strictCorrect)]],scopeLabel());});
  $("format-caption").innerHTML=`<strong>${esc(rows[0].short)}</strong>: ${(rows[0].answer-rows[0].strict).toFixed(2)} pp lost to formatting.`;
}
function renderConsensus(){
  const c=comparison(),container=$("consensus-chart"),width=Math.max(288,container.clientWidth||480),height=270,left=36,right=8,top=22,bottom=40;
  const max=Math.max(...c.consensus)/c.n*100,step=niceStep(max,4),upper=Math.max(step,Math.ceil(max/step)*step),plot=height-top-bottom;
  const band=(width-left-right)/c.consensus.length,x=i=>left+band*i+band*.18,y=v=>top+(1-v/upper)*plot;
  let html=svgStart("consensus",width,height,"Number of models correct on each task",`${scopeLabel()}. ${scoreLabel()}. Each task contributes once to the histogram.`);
  for(let tick=0;tick<=upper+.001;tick+=step)html+=`<line class="grid-line" x1="${left}" x2="${width-right}" y1="${y(tick)}" y2="${y(tick)}"/><text class="axis-text" x="${left-7}" y="${y(tick)+3}" text-anchor="end">${tick}%</text>`;
  c.consensus.forEach((count,i)=>{const percent=count/c.n*100,barColor=i===0?"var(--bad)":i===DATA.models.length?"var(--good)":"var(--google)";html+=`<g class="consensus-bar" tabindex="0" data-count="${i}" aria-label="${i} of ${DATA.models.length} models correct: ${integer(count)} tasks, ${percent.toFixed(2)} percent"><rect x="${x(i)}" y="${top}" width="${band*.64}" height="${plot}" fill="transparent"/><rect x="${x(i)}" y="${y(percent)}" width="${band*.64}" height="${Math.max(0,plot-(y(percent)-top))}" fill="${barColor}" opacity="${i===0||i===DATA.models.length?1:.55}"/><text class="axis-text" x="${x(i)+band*.32}" y="${y(percent)-6}" text-anchor="middle">${percent.toFixed(1)}</text><text class="axis-text" x="${x(i)+band*.32}" y="${height-bottom+18}" text-anchor="middle">${i}</text></g>`;});
  html+=`<text class="axis-caption" x="${left}" y="10">SHARE OF TASKS</text><text class="axis-caption" x="${width-right}" y="${height-3}" text-anchor="end">Number of models correct</text></svg>`;container.innerHTML=html;
  container.querySelectorAll("[data-count]").forEach(el=>{const n=Number(el.dataset.count);bindDetail(el,`${n} / ${DATA.models.length} models correct`,[["Tasks",integer(c.consensus[n])],["Share",(100*c.consensus[n]/c.n).toFixed(2)+"%"]],`${scopeLabel()} · ${scoreLabel()}`);});
  $("consensus-summary").innerHTML=`<div><strong>${integer(c.consensus[0])}</strong><span>No model correct</span></div><div><strong>${integer(c.consensus.at(-1))}</strong><span>All eight correct</span></div>`;
  $("consensus-caption").textContent=`${integer(c.n)} tasks · ${scoreLabel().toLowerCase()}. Each task is counted once.`;
  $("outcomes-scope").textContent=scopeLabel();
}
function renderPairwise(){
  const c=comparison(),rows=scopedRows().sort((a,b)=>b.score-a.score),max=Math.max(1,...c.wins.flat());
  const matrix=$("pair-matrix");
  matrix.innerHTML=`<table class="pair-matrix"><caption class="sr-only">Share of shared tasks where the row model is correct and the column model is incorrect.</caption><thead><tr><th scope="col">ROW ↓ / COL →</th>${rows.map(r=>`<th scope="col" title="${esc(r.label)}">${esc(r.short)}</th>`).join("")}</tr></thead><tbody>${rows.map(a=>`<tr><th scope="row" title="${esc(a.label)}">${esc(a.short)}</th>${rows.map(b=>{
    if(a.id===b.id)return '<td class="pair-diagonal" aria-label="Same model">—</td>';
    const count=c.wins[c.ids.indexOf(a.id)][c.ids.indexOf(b.id)],value=100*count/c.n;
    return `<td><button type="button" class="pair-cell${state.pairA===a.id&&state.pairB===b.id?" active":""}" data-a="${a.id}" data-b="${b.id}" aria-pressed="${state.pairA===a.id&&state.pairB===b.id}" aria-label="${esc(a.label)} correct, ${esc(b.label)} incorrect: ${value.toFixed(2)} percent, ${integer(count)} tasks" style="--intensity:${count/max*58}%">${value.toFixed(1)}</button></td>`;
  }).join("")}</tr>`).join("")}</tbody></table>`;
  matrix.querySelectorAll("button").forEach(el=>{
    const a=rows.find(r=>r.id===el.dataset.a),b=rows.find(r=>r.id===el.dataset.b),count=c.wins[c.ids.indexOf(a.id)][c.ids.indexOf(b.id)];
    bindDetail(el,`${a.short} → ${b.short}`,[["Row correct, column wrong",integer(count)],["Share of shared tasks",(100*count/c.n).toFixed(2)+"%"]],"Select for the full paired comparison.");
    el.addEventListener("click",()=>{state.pairA=a.id;state.pairB=b.id;hideTooltip();renderPairwise();matrix.querySelector(`[data-a="${a.id}"][data-b="${b.id}"]`).focus();});
  });
  const a=rows.find(r=>r.id===state.pairA),b=rows.find(r=>r.id===state.pairB),i=c.ids.indexOf(a.id),j=c.ids.indexOf(b.id);
  const aOnly=c.wins[i][j],bOnly=c.wins[j][i],both=c.correct[i]-aOnly,neither=c.n-both-aOnly-bOnly;
  const parts=[{name:"Both correct",n:both,color:"var(--good)"},{name:`${a.short} only`,n:aOnly,color:"var(--violet)"},{name:`${b.short} only`,n:bOnly,color:"var(--format)"},{name:"Neither correct",n:neither,color:"var(--faint)"}];
  $("pair-detail").innerHTML=`<div><div class="mini-label">Selected pair</div><h3>${esc(a.short)} <span class="muted">×</span> ${esc(b.short)}</h3></div><div class="pair-stack" aria-hidden="true">${parts.map(p=>`<span style="width:${100*p.n/c.n}%;background:${p.color}"></span>`).join("")}</div><div>${parts.map(p=>`<div class="pair-key"><span><i style="background:${p.color}"></i>${esc(p.name)}</span><strong>${(100*p.n/c.n).toFixed(2)}%</strong></div>`).join("")}</div><div class="pair-total"><strong>${(100*(c.n-neither)/c.n).toFixed(2)}%</strong><span>Either answer correct · ${integer(c.n-neither)} tasks</span></div>`;
  $("agreement-scope").textContent=scopeLabel();
  $("agreement-caption").textContent=`${scoreLabel()}. Either-correct coverage uses the two observed responses; it is not an evaluated ensemble.`;
}
