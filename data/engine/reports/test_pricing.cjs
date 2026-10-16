"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const pricing = require("./pricing.js");
const root = path.resolve(__dirname, "../../..");
const config = JSON.parse(fs.readFileSync(path.join(root, "data/benchmark/pricing-data.json"), "utf8"));
function state(overrides = {}) {
  return {selected: config.models.map(m => m.id),
          counts: Object.fromEntries(config.families.map(f => [f.id, 1000])),
          multipliers: Object.fromEntries(config.models.map(m => [m.id, 1])),
          budgets: {...config.budgets}, discount: 1, ...overrides};
}
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);

test("one request bills input and total output once, at the selected model rate", () => {
  const one = state({selected: ["gpt-6-astra"], counts: {tinanta: 1, krdanta: 0, subanta: 0, taddhitanta: 0}});
  const f = config.models.find(m => m.id === "gpt-6-astra").token_estimates.tinanta;
  const r = pricing.calculate(config, one);
  close(r.total, (f.input_tokens * 10 + f.output_tokens * 50) / 1e6);
  close(r.stress, (f.input_tokens * 10 + f.output_tokens * 2 * 50) / 1e6);
  assert.equal(r.tasks, 1); assert.equal(r.requests, 1);
});

test("provider budgets stay separate, and deselecting models removes all their costs", () => {
  const all = pricing.calculate(config, state());
  assert.equal(all.requests, 24000);
  close(all.total, all.providers.reduce((sum, p) => sum + p.total, 0));
  const openai = pricing.calculate(config, state({selected: config.models.filter(m => m.provider === "OpenAI").map(m => m.id)}));
  assert.equal(openai.requests, 12000);
  assert.equal(openai.providers.find(p => p.provider === "Anthropic").total, 0);
  close(openai.total, all.providers.find(p => p.provider === "OpenAI").total);
});

test("batch halves cost; output scaling does not multiply input costs", () => {
  const original = state();
  const normal = pricing.calculate(config, original);
  const batch = pricing.calculate(config, {...original, discount: .5});
  close(batch.total, normal.total / 2); close(batch.stress, normal.stress / 2);
  const doubled = pricing.calculate(config, {...original, multipliers: Object.fromEntries(config.models.map(m => [m.id, 2]))});
  close(doubled.total, normal.stress);
  assert.ok(doubled.total < 2 * normal.total);
});

test("no models or zero task counts produces no charges and handles fitting", () => {
  const none = state({selected: []});
  assert.equal(pricing.calculate(config, none).total, 0);
  assert.equal(pricing.calculate(config, none).requests, 0);
  assert.equal(pricing.fitEqual(config, none), null);
  assert.equal(pricing.calculate(config, state({counts: {}})).total, 0);
  assert.equal(pricing.fitEqual(config, state({budgets: {OpenAI: 0, Anthropic: 0}})), 0);
});

test("budget fit respects both budgets and is maximal for equal family counts", () => {
  for (const discount of [1, .5]) for (const stress of [1, 2]) {
    const input = state({discount});
    const fitted = pricing.fitEqual(config, input, stress);
    const fittedState = n => ({...input, counts: Object.fromEntries(config.families.map(f => [f.id, n]))});
    const output = pricing.calculate(config, fittedState(fitted));
    assert.ok(output.providers.every(p => (stress === 2 ? p.stress : p.total) <= p.budget));
    // Cheap scenarios can reach the smallest family's entire inventory first.
    if (fitted < Math.min(...config.families.map(f => f.available))) {
      assert.ok(pricing.calculate(config, fittedState(fitted + 1)).providers.some(p => (stress === 2 ? p.stress : p.total) > p.budget));
    }
  }
});

test("family caps, fractions, negatives, and nonfinite inputs cannot inflate task counts", () => {
  const bounded = pricing.normalize(config, state({counts: {tinanta: -10, krdanta: 1e10, subanta: 3.9, taddhitanta: NaN}}));
  assert.deepEqual(bounded.counts, {tinanta: 0, krdanta: 27470, subanta: 3, taddhitanta: 0});
  const fit = pricing.fitEqual(config, state({budgets: {OpenAI: 1e12, Anthropic: 1e12}}));
  assert.equal(fit, 27470);
});

test("calculator uses verified answer-only measurements and current inventory hashes", () => {
  assert.equal(config.calibration.requests, 200);
  assert.equal(config.calibration.response_format, "answer_only");
  for (const f of config.families) {
    const m = JSON.parse(fs.readFileSync(path.join(root, "data/datasets", f.id, "manifest.json"), "utf8"));
    assert.equal(f.available, m.counts.full);
    assert.equal(f.full_sha256, m.files["full.json"].sha256);
    for (const model of Object.values(config.calibration.by_model)) {
      assert.equal(model[f.id].attempts, 25);
      assert.ok(model[f.id].usable_responses > 0);
      assert.ok(!model[f.id].task_ids.includes("10.0333:Lun:Bhave:Madhyama:Eka"));
    }
  }
});

test("each measured model reproduces nonrefused pilot spend at its own token lengths", () => {
  const receipts = JSON.parse(fs.readFileSync(path.join(root, config.calibration.run, "results.json"), "utf8"));
  for (const model of config.models.filter(m => m.measured)) {
    const rows = receipts.filter(r => r.actual_model === model.id && r.status === "completed" && !r.structured_safety_flag && !r.structured_cyber_flag);
    const counts = Object.fromEntries(config.families.map(f => [f.id, rows.filter(r => r.family === f.id).length]));
    const calculated = pricing.calculate(config, state({selected: [model.id], counts}));
    close(calculated.total, rows.reduce((sum, r) => sum + r.usage_based_cost_usd, 0));
  }
  const astra = config.models.find(m => m.id === "gpt-6-astra");
  const opus = config.models.find(m => m.id === "claude-opus-5-5");
  assert.notDeepEqual(astra.token_estimates, opus.token_estimates);
});

test("unmeasured models are labeled and use their provider's measured baseline", () => {
  for (const model of config.models.filter(m => !m.measured)) {
    const anchor = config.models.find(m => m.id === model.calibration_model);
    assert.equal(anchor.provider, model.provider);
    assert.deepEqual(model.token_estimates, anchor.token_estimates);
    assert.match(model.output_basis, /Unmeasured/);
  }
});

test("standalone HTML embeds the tested code and data with no CSS or remote scripts", () => {
  const html = fs.readFileSync(path.join(root, "data/benchmark/pricing.html"), "utf8");
  assert.ok(!/<style\b|\sstyle\s*=|rel=["']stylesheet/i.test(html));
  assert.ok(!/<script\b[^>]*\bsrc\s*=/i.test(html));
  assert.equal((html.match(/data-model="/g) || []).length, 6);
  assert.equal((html.match(/data-slider="/g) || []).length, 4);
  assert.deepEqual(JSON.parse(html.match(/<script type="application\/json" id="pricing-data">([\s\S]*?)<\/script>/)[1]), config);
  assert.ok(html.includes(fs.readFileSync(path.join(__dirname, "pricing.js"), "utf8")));
});
