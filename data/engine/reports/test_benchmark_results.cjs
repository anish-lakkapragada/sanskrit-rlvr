/* Offline DOM and numerical verification. Requires jsdom; does not render screenshots. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('jsdom');
const html = fs.readFileSync(path.resolve(__dirname, '../../benchmark/results/summaries/results.html'), 'utf8');
const errors = [], virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', error => errors.push(String(error)));
let width = 960, csv = '';
const dom = new JSDOM(html, {runScripts: 'dangerously', pretendToBeVisual: true,
  url: 'http://localhost/results.html', virtualConsole,
  beforeParse(w) {
    Object.defineProperty(w.HTMLElement.prototype, 'clientWidth', {get() {return width;}});
    w.Blob = class {constructor(parts) {this.parts = parts;}};
    w.URL.createObjectURL = blob => {csv = blob.parts.join(''); return 'blob:test';};
    w.URL.revokeObjectURL = () => {};
    w.HTMLAnchorElement.prototype.click = function() {};
  }
});
const w = dom.window, d = w.document;
const data = JSON.parse(d.getElementById('benchmark-data').textContent);
const close = (a, b, tolerance = 1e-10) => assert(Math.abs(a - b) < tolerance, `${a} != ${b}`);
const sum = xs => xs.reduce((a, b) => a + b, 0);
const change = (id, value) => {const el=d.getElementById(id); el.value=value; el.dispatchEvent(new w.Event('change'));};
const check = (id, checked) => {const el=d.getElementById(id); el.checked=checked; el.dispatchEvent(new w.Event('change'));};
const count = selector => d.querySelectorAll(selector).length;

assert.equal(data.models.length, 8);
assert.equal(data.standardDeviation.ddof, 0);
assert.equal(data.tasksPerModel, 20000);
assert(!/__BENCHMARK_|__MODEL_COUNT__/.test(html));
assert.equal(count('script[src],link[rel="stylesheet"]'), 0, 'Page stays standalone');
assert.equal(count('#source-links a'), 8);

// Audit pooled scores, percentile ordering, family SD, and paired outcomes independently.
for (const m of data.models) {
  for (const score of ['answer', 'strict']) {
    const values = data.families.map(f => m.families[f][score]);
    const mean = sum(values)/values.length;
    close(m.pooled[score], mean);
    close(m.familyScoreSd[score], Math.sqrt(sum(values.map(v => (v-mean)**2))/values.length));
  }
  for (const stats of [m.pooled, ...Object.values(m.families)]) {
    assert(stats.strict <= stats.answer);
    for (const metric of ['cost','tokens','duration']) {
      const q = stats.distribution[metric];
      const ordered = ['min','p10','q1','median','q3','p90','p99','max'].map(k => q[k]);
      assert(ordered.every((v,i) => Number.isFinite(v) && (i===0 || v >= ordered[i-1])));
      close(q.median, stats.median[metric]);
      assert.equal(stats.metricCounts[metric], stats.n);
    }
  }
}
for (const [scope, scores] of Object.entries(data.comparisons)) {
  for (const [score, c] of Object.entries(scores)) {
    assert.equal(c.n, scope === 'all' ? 20000 : 5000);
    assert.equal(sum(c.consensus), c.n);
    assert.equal(sum(c.consensus.map((n,k) => n*k)), sum(c.correct));
    for (let i=0; i<c.ids.length; i++) {
      const model = data.models.find(m => m.id===c.ids[i]);
      const stats = scope==='all' ? model.pooled : model.families[scope];
      assert.equal(c.correct[i], score==='answer' ? stats.correct : stats.strictCorrect);
      assert.equal(c.wins[i][i], 0);
      for (let j=0; j<c.ids.length; j++) {
        const aOnly=c.wins[i][j], bOnly=c.wins[j][i], both=c.correct[i]-aOnly;
        assert(both >= 0 && c.n-both-aOnly-bOnly >= 0);
        assert.equal(both+bOnly, c.correct[j]);
      }
    }
  }
}
for (const score of ['answer','strict']) {
  const all=data.comparisons.all[score];
  for(let k=0;k<9;k++) assert.equal(all.consensus[k], sum(data.families.map(f=>data.comparisons[f][score].consensus[k])));
  for(let i=0;i<8;i++) for(let j=0;j<8;j++) assert.equal(all.wins[i][j], sum(data.families.map(f=>data.comparisons[f][score].wins[i][j])));
}

let views=0;
for(const viewport of [960,340]) {
  width=viewport;
  for(const family of ['average','maximum','minimum',...data.families]) {
    change('family-select',family);
    for(const score of ['answer','strict']) {
      change('score-select',score);
      const c=data.comparisons[data.families.includes(family)?family:'all'][score];
      assert.equal(count('.sd-whisker'), family==='average'?8:0);
      assert.equal(d.getElementById('show-sd').disabled, family!=='average');
      for(const metric of ['cost','tokens','duration']) {
        change('frontier-metric',metric); change('median-metric',metric); change('distribution-metric',metric);
        for(const selector of ['#data-table tr','#performance-chart [data-model]','#frontier-chart .model-point',
          '#median-chart .model-point','#distribution-chart .box-point','#format-chart .dumbbell-row']) assert.equal(count(selector),8,selector);
        assert.equal(count('#family-matrix button'),32);
        assert.equal(count('#consensus-chart .consensus-bar'),9);
        assert.equal(count('#pair-matrix button'),56);
        const chartHTML=['frontier-chart','median-chart','distribution-chart','format-chart','consensus-chart','performance-chart','pair-matrix'].map(id=>d.getElementById(id).innerHTML).join('');
        assert(!/NaN|undefined|Infinity/.test(chartHTML));
        for(const el of d.querySelectorAll('svg [width],svg [height],svg [r]')) {
          for(const name of ['width','height','r']) if(el.hasAttribute(name)) assert(Number(el.getAttribute(name))>=0);
        }
        for(const bar of d.querySelectorAll('.consensus-bar')) {
          const expected=c.consensus[Number(bar.dataset.count)];
          assert(bar.getAttribute('aria-label').includes(expected.toLocaleString('en-US')+' tasks'));
        }
        if(family==='average') for(const row of d.querySelectorAll('#performance-chart [data-model]')) {
          const m=data.models.find(m=>m.id===row.dataset.model), whisker=row.querySelector('.sd-whisker');
          close(Number(whisker.dataset.sd),m.familyScoreSd[score]);
          const lo=Math.max(0,m.pooled[score]-m.familyScoreSd[score]);
          const hi=Math.min(100,m.pooled[score]+m.familyScoreSd[score]);
          close(parseFloat(whisker.style.left),lo);
          close(parseFloat(whisker.style.width),hi-lo);
        }
        views++;
      }
    }
  }
}
change('family-select','average'); change('score-select','answer');
check('show-sd',false); assert.equal(count('.sd-whisker'),0);
check('show-sd',true); assert.equal(count('.sd-whisker'),8);
for(const control of ['frontier-log','median-log','distribution-log']) {check(control,false);check(control,true);}

const heatCell=d.querySelector('#family-matrix [data-model="astra-xhigh"][data-family="subanta"]');
heatCell.click(); assert.equal(d.getElementById('family-select').value,'subanta');
assert.equal(count('.heat-cell.selected'),8);assert.equal(count('.sd-whisker'),0);
assert.equal(d.activeElement.dataset.family,'subanta');
change('family-select','average');
const pair=d.querySelector('#pair-matrix [data-a="gemini4-argon-high"][data-b="opus55-xhigh"]');
pair.click(); assert.equal(count('.pair-cell.active'),1);
assert.equal(d.activeElement.dataset.a,'gemini4-argon-high');
const c=data.comparisons.all.answer, i=c.ids.indexOf('gemini4-argon-high'),j=c.ids.indexOf('opus55-xhigh');
const both=c.correct[i]-c.wins[i][j], union=both+c.wins[i][j]+c.wins[j][i];
assert.equal(d.querySelector('.pair-total strong').textContent,(100*union/c.n).toFixed(2)+'%');
close(sum([...d.querySelectorAll('.pair-stack span')].map(el=>parseFloat(el.style.width))),100);
for(const selector of ['#frontier-chart .model-point','#distribution-chart .box-point','.heat-cell','.pair-cell','.consensus-bar','.dumbbell-row']) {
  d.querySelector(selector).dispatchEvent(new w.FocusEvent('focus'));
  assert.equal(d.getElementById('tooltip').hidden,false);
  d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape'}));
  assert.equal(d.getElementById('tooltip').hidden,true);
}
const flashPoint=d.querySelector('#frontier-chart [data-model="gemini38-flash-high"]');
flashPoint.dispatchEvent(new w.FocusEvent('focus'));assert(d.getElementById('tooltip').textContent.includes('HIGH'));
const theme=d.documentElement.dataset.theme;d.getElementById('theme-toggle').click();assert.notEqual(d.documentElement.dataset.theme,theme);
function csvRows() {d.getElementById('download-csv').click();return csv.trim().split(/\r?\n/).map(line=>line.slice(1,-1).split('","'));}
let rows=csvRows();assert.equal(rows.length,9);assert.equal(rows[0][6],'answer_family_sd_pp');assert(rows.slice(1).every(row=>Number(row[6])>0));
change('family-select','tinanta');rows=csvRows();assert(rows.slice(1).every(row=>row[6]===''&&row[7]===''));
const ids=[...d.querySelectorAll('[id]')].map(el=>el.id);assert.equal(new Set(ids).size,ids.length,'Unique element IDs');
for(const el of d.querySelectorAll('a[href^="#"]')) assert(d.getElementById(el.getAttribute('href').slice(1)),'Valid anchor target');
assert.equal(errors.length,0,errors.join('\n'));
console.log(JSON.stringify({models:8,responses:160000,viewsChecked:views,pairedOutcomeScopes:10,
  sdVerified:true,heatmapFilter:true,distributionControls:true,pairSelection:true,csv:true,theme:true,
  runtimeErrors:errors,method:'Offline DOM and statistical checks; not screenshot-based visual review'},null,2));
dom.window.close();
