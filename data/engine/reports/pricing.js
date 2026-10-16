/* Shared by the standalone page and the calculation tests. No network calls. */
"use strict";

const Pricing = (() => {
  function bounded(value, fallback, min, max) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback;
  }

  function normalize(config, state) {
    return {
      selected: config.models.filter(m => state.selected.includes(m.id)).map(m => m.id),
      counts: Object.fromEntries(config.families.map(f => [f.id, Math.floor(bounded(state.counts[f.id], 0, 0, f.available))])),
      multipliers: Object.fromEntries(config.models.map(m => [m.id, bounded(state.multipliers[m.id], 1, .1, 10)])),
      budgets: Object.fromEntries(Object.keys(config.budgets).map(p => [p, bounded(state.budgets[p], 0, 0, 1e12)])),
      discount: Number(state.discount) === .5 ? .5 : 1
    };
  }

  function unit(model, family, multiplier, discount, stress = 1) {
    const usage = model.token_estimates[family.id];
    return (usage.input_tokens * model.input_rate + usage.output_tokens * multiplier * stress * model.output_rate) * discount / 1e6;
  }

  function calculate(config, rawState) {
    const state = normalize(config, rawState);
    const models = config.models.filter(m => state.selected.includes(m.id)).map(model => {
      const units = Object.fromEntries(config.families.map(f => [f.id, unit(model, f, state.multipliers[model.id], state.discount)]));
      const costs = Object.fromEntries(config.families.map(f => [f.id, units[f.id] * state.counts[f.id]]));
      const total = Object.values(costs).reduce((a, b) => a + b, 0);
      const stress = config.families.reduce((sum, f) => sum + state.counts[f.id] * unit(model, f, state.multipliers[model.id], state.discount, 2), 0);
      return {id: model.id, name: model.name, provider: model.provider, units, costs, total, stress};
    });
    const providers = Object.keys(config.budgets).map(provider => {
      const rows = models.filter(m => m.provider === provider);
      const total = rows.reduce((sum, m) => sum + m.total, 0);
      const stress = rows.reduce((sum, m) => sum + m.stress, 0);
      return {provider, models: rows.length, budget: state.budgets[provider], total, stress,
              remaining: state.budgets[provider] - total, stressRemaining: state.budgets[provider] - stress};
    });
    const tasks = Object.values(state.counts).reduce((a, b) => a + b, 0);
    return {state, models, providers, tasks, requests: tasks * models.length,
            total: models.reduce((sum, m) => sum + m.total, 0),
            stress: models.reduce((sum, m) => sum + m.stress, 0),
            families: Object.fromEntries(config.families.map(f => [f.id, models.reduce((sum, m) => sum + m.costs[f.id], 0)]))};
  }

  function fitEqual(config, rawState, stress = 1) {
    const state = normalize(config, rawState);
    if (!state.selected.length) return null;
    let count = Math.min(...config.families.map(f => f.available));
    for (const provider of Object.keys(config.budgets)) {
      const selected = config.models.filter(m => state.selected.includes(m.id) && m.provider === provider);
      const perSet = selected.reduce((sum, m) => sum + config.families.reduce(
        (subtotal, f) => subtotal + unit(m, f, state.multipliers[m.id], state.discount, stress), 0), 0);
      if (perSet > 0) count = Math.min(count, Math.floor(state.budgets[provider] / perSet));
    }
    // Floating-point division can put an exact budget boundary one task too high.
    while (count > 0) {
      const result = calculate(config, {...state, counts: Object.fromEntries(config.families.map(f => [f.id, count]))});
      if (result.providers.every(p => (stress === 2 ? p.stress : p.total) <= p.budget)) break;
      count -= 1;
    }
    return count;
  }

  function mount(doc, config) {
    const byId = id => doc.getElementById(id);
    const money = value => new Intl.NumberFormat("en-US", {style: "currency", currency: "USD"}).format(value);
    const count = value => new Intl.NumberFormat("en-US").format(value);
    const unitMoney = value => "$" + value.toFixed(6);
    const fields = selector => [...doc.querySelectorAll(selector)];
    const read = () => ({
      selected: fields("[data-model]").filter(el => el.checked).map(el => el.dataset.model),
      counts: Object.fromEntries(config.families.map(f => [f.id, byId("count-" + f.id).value])),
      multipliers: Object.fromEntries(config.models.map(m => [m.id, byId("scale-" + m.id).value])),
      budgets: Object.fromEntries(Object.keys(config.budgets).map(p => [p, byId("budget-" + p).value])),
      discount: byId("processing").value
    });
    function render() {
      const result = calculate(config, read());
      byId("request-count").textContent = `${count(result.tasks)} distinct tasks per model × ${result.models.length} selected models = ${count(result.requests)} API requests.`;
      for (const f of config.families) byId("share-" + f.id).textContent = (100 * result.state.counts[f.id] / f.available).toFixed(3) + "%";
      byId("budget-results").innerHTML = result.providers.map(p => `<tr><th scope="row">${p.provider}</th><td>${p.models}</td><td>${money(p.budget)}</td><td>${money(p.total)}</td><td>${money(Math.abs(p.remaining))} ${p.remaining >= 0 ? "remaining" : "OVER budget"}</td><td>${money(p.stress)}</td><td>${money(Math.abs(p.stressRemaining))} ${p.stressRemaining >= 0 ? "remaining" : "OVER budget"}</td></tr>`).join("");
      byId("grand-total").textContent = `Combined estimate: ${money(result.total)}. If output doubles: ${money(result.stress)}.`;
      byId("model-results").innerHTML = result.models.length ? result.models.map(m => `<tr><th scope="row">${m.name} xHigh</th>${config.families.map(f => `<td>${money(m.costs[f.id])}</td>`).join("")}<td>${money(m.total)}</td><td>${money(m.stress)}</td></tr>`).join("") : '<tr><td colspan="7">Select at least one model.</td></tr>';
      byId("family-totals").innerHTML = `<tr><th scope="row">All selected models</th>${config.families.map(f => `<td>${money(result.families[f.id])}</td>`).join("")}<td>${money(result.total)}</td><td>${money(result.stress)}</td></tr>`;
      byId("unit-results").innerHTML = result.models.length ? result.models.map(m => `<tr><th scope="row">${m.name} xHigh</th>${config.families.map(f => `<td>${unitMoney(m.units[f.id])}</td>`).join("")}</tr>`).join("") : '<tr><td colspan="5">Select at least one model.</td></tr>';
      byId("fit-mean").disabled = byId("fit-stress").disabled = result.models.length === 0;
      return result;
    }
    function rangeMax(family) {
      const range = byId("slider-range").value;
      return range === "all" ? family.available : Math.min(Number(range), family.available);
    }
    function adjustRange() {
      const current = normalize(config, read()).counts;
      const largest = Math.max(...Object.values(current));
      const selector = byId("slider-range");
      if (selector.value !== "all" && largest > Number(selector.value)) selector.value = largest <= 100000 ? "100000" : "all";
      for (const f of config.families) byId("slider-" + f.id).max = rangeMax(f);
    }
    function setCounts(values) {
      for (const f of config.families) byId("count-" + f.id).value = Math.floor(bounded(values[f.id], 0, 0, f.available));
      adjustRange();
      for (const f of config.families) byId("slider-" + f.id).value = byId("count-" + f.id).value;
    }
    function changed() {
      byId("fit-note").textContent = "Fit sets the same count for each family using the selected models and current usage multipliers.";
      render();
    }
    fields("[data-slider]").forEach(el => el.addEventListener("input", () => {
      byId("count-" + el.dataset.slider).value = el.value;
      changed();
    }));
    fields("[data-count]").forEach(el => el.addEventListener("input", () => {
      setCounts(read().counts);
      changed();
    }));
    fields("[data-model]").forEach(el => el.addEventListener("change", changed));
    fields("[data-scale]").forEach(el => {
      el.addEventListener("input", changed);
      el.addEventListener("change", () => {
        el.value = bounded(el.value, 1, .1, 10);
        changed();
      });
    });
    for (const provider of Object.keys(config.budgets)) byId("budget-" + provider).addEventListener("input", () => {
      const el = byId("budget-" + provider);
      el.value = bounded(el.value, 0, 0, 1e12);
      changed();
    });
    byId("processing").addEventListener("change", changed);
    byId("slider-range").addEventListener("change", () => {
      setCounts(Object.fromEntries(config.families.map(f => [f.id, Math.min(Number(byId("count-" + f.id).value), rangeMax(f))])));
      changed();
    });
    fields("[data-model-group]").forEach(button => button.addEventListener("click", () => {
      for (const model of config.models) byId("model-" + model.id).checked = button.dataset.modelGroup === "all" || button.dataset.modelGroup === model.provider;
      changed();
    }));
    fields("[data-preset]").forEach(button => button.addEventListener("click", () => {
      setCounts(Object.fromEntries(config.families.map(f => [f.id, button.dataset.preset === "all" ? f.available : Number(button.dataset.preset)])));
      changed();
    }));
    for (const [id, stress] of [["fit-mean", 1], ["fit-stress", 2]]) byId(id).addEventListener("click", () => {
      const amount = fitEqual(config, read(), stress);
      if (amount === null) return;
      setCounts(Object.fromEntries(config.families.map(f => [f.id, amount])));
      render();
      byId("fit-note").textContent = `Set ${count(amount)} tasks per family per selected model using ${stress === 2 ? "the 2× output scenario" : "the mean output estimate"}. This is a budget estimate, not a spending guarantee.`;
    });
    render();
    return {read, render};
  }
  return {normalize, unit, calculate, fitEqual, mount};
})();

if (typeof module !== "undefined" && module.exports) module.exports = Pricing;
if (typeof document !== "undefined") Pricing.mount(document, JSON.parse(document.getElementById("pricing-data").textContent));
