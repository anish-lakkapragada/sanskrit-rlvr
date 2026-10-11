"""Render a dated, read-only summary of the frozen pilot08 development evidence.

Run with .venv/bin/python misc/build_vp_5d_report_summary.py, then refresh the report.
No generation, scoring changes, provider calls, or final-benchmark qualification.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from importlib.metadata import version
from pathlib import Path

from vidyut.prakriya import Sanadi

ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "benchmarks/parallel-search-20261006"
PANEL = SEARCH / "five_d/pilot-08/revision-02"
JOBS = ROOT / "benchmarks/iterative-goal-20261006/jobs"
LINK = "parallel-search-20261006/five_d/pilot-08/revision-02/"
BEGIN = "<!-- BEGIN FROZEN 5D PILOT08 SUMMARY -->"
END = "<!-- END FROZEN 5D PILOT08 SUMMARY -->"

NAMES = {
    ("Ric",): "Causative",
    ("san",): "Desiderative",
    ("yaN",): "Intensive",
    ("yaNluk",): "Intensive with suffix deletion",
    ("yaN", "Ric"): "Intensive → causative",
    ("yaNluk", "Ric"): "Intensive with suffix deletion → causative",
    ("yaN", "Ric", "san"): "Intensive → causative → desiderative",
}
LAKARAS = {
    "Lun": "Luṅ · aorist", "Lat": "Laṭ · present", "VidhiLin": "Vidhiliṅ · optative",
    "Lan": "Laṅ · imperfect", "AshirLin": "Āśīrliṅ · benedictive", "Lit": "Liṭ · perfect",
    "Lot": "Loṭ · imperative", "Lrn": "Lṛṅ · conditional", "Lrt": "Lṛṭ · simple future",
    "Lut": "Luṭ · periphrastic future",
}


def read(path):
    return json.loads(path.read_text())


def fingerprint(path):
    return {"path": str(path.relative_to(ROOT / "benchmarks")),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def percent(correct, n, places=2):
    return f"{100 * correct / n:.{places}f}%"


def main():
    plan, aggregate, tasks = (read(PANEL / name) for name in
                              ("plan.json", "aggregate-analysis.json", "tasks.json"))
    assert aggregate["all8settled_and_collected"]
    raw = aggregate["raw"]["opus_primary"]
    stats, strata = raw["statistics"], raw["strata"]
    assert len(tasks) == stats["fixed_n"] == 2400
    recipes = plan["recipe_operations"]
    sources = [fingerprint(PANEL / name) for name in ("plan.json", "aggregate-analysis.json", "tasks.json")]
    history = defaultdict(lambda: {"n": 0, "ids": set(), "jobs": set()})
    wrong_families, wrong_non_lun_families = set(), set()
    primary_ids = {t["id"] for t in tasks}
    primary_seen = set()
    for path in sorted(JOBS.glob("opus-five-d-pilot-*/results.json")):
        sources.append(fingerprint(path))
        for row in read(path):
            task = row["task"]
            ops = tuple(task["derivation"]["sanadi"])
            history[ops]["n"] += 1
            history[ops]["ids"].add(task["id"])
            history[ops]["jobs"].add(path.parent.name)
            if path.parent.name.startswith("opus-five-d-pilot-08-"):
                assert task["id"] in primary_ids and task["id"] not in primary_seen
                primary_seen.add(task["id"])
                usable = row["status"] == "completed" and row["answer"] is not None and not row["truncated"]
                if usable and not row["is_correct"]:
                    wrong_families.add(task["campaign"]["root_family"])
                    if task["morphology"]["lakara"] != "Lun":
                        wrong_non_lun_families.add(task["campaign"]["root_family"])
    assert primary_seen == primary_ids
    history_rows = [{"operations": list(ops), "label": NAMES[ops],
                     "submitted": value["n"], "unique_task_ids": len(value["ids"]),
                     "jobs": sorted(value["jobs"])} for ops, value in history.items()]
    assert set(history) == set(NAMES), "Review the prose when the explored recipe menu changes"
    cells = {}
    for dims in [("recipe", "lakara"), ("recipe", "lakara", "prayoga"),
                 ("recipe", "lakara", "prayoga", "purusha", "vacana")]:
        cells["×".join(dims)] = len({tuple(t["derivation"]["recipe_id"] if d == "recipe"
                                                  else t["morphology"][d] for d in dims) for t in tasks})
    matrix = {}
    for recipe in recipes:
        matrix[recipe] = {}
        for lakara in LAKARAS:
            entries = [v for k, v in strata.items()
                       if k.startswith(f"recipe_lakara_voice::{recipe}|{lakara}|")]
            matrix[recipe][lakara] = {field: sum(v[field] for v in entries)
                                     for field in ("n", "correct", "completed", "completed_correct")}
    lun = strata["lakara::Lun"]
    all_score = stats["all_request"]
    usable_score = stats["completed_answer"]
    wrong_usable = usable_score["n"] - usable_score["correct"]
    lun_wrong = lun["completed"] - lun["completed_correct"]
    equal_tense_score = sum(strata["lakara::" + la]["all_request_accuracy"] for la in LAKARAS) / 10
    api_values = [str(value) for value in Sanadi.choices()]
    assert set(api_values) == {"Ric", "san", "yaN", "yaNluk", "kAmyac", "kyaN", "kyac"}
    snapshot = {
        "date": "2026-10-07", "panel": "pilot-08/revision-02", "score_policy": "frozen policy21 raw",
        "status": "development accuracy target met; source review and final qualification open",
        "sources": sources, "current_menu": recipes, "historical_opus_pilot_recipe_counts": history_rows,
        "historical_count_scope": "Collected Opus exact5D pilot01–08 requests; before later source exclusions. Different prompts/protocols; not pooled accuracy.",
        "observed_coordinate_cells": cells, "nominal_five_coordinate_cells": 3 * 10 * 2 * 3 * 3,
        "nominal_denominator_caveat": "Counts ignore dhatu identity and grammatical applicability; not the number of legal Sanskrit combinations.",
        "recipe_lakara_matrix": matrix, "wrong_completed_families": len(wrong_families),
        "wrong_completed_non_lun_families": len(wrong_non_lun_families),
        "wrong_completed": wrong_usable, "wrong_completed_lun": lun_wrong,
        "installed_vidyut_version": version("vidyut"), "installed_sanadi_values": api_values,
        "descriptive_equal_tense_reweighting": {
            "accuracy": equal_tense_score,
            "method": "Arithmetic mean of the ten observed all-request tense accuracies; existing within-tense composition retained.",
            "caveat": "Post-hoc descriptive reweighting of current data, not a new run or a prediction for broader valid task supply.",
        },
        "documentation": [
            "https://vidyut.readthedocs.io/en/latest/prakriya.html#specifying-arguments",
            "https://vidyut.readthedocs.io/en/latest/api.html#vidyut.prakriya.Dhatu.with_sanadi",
            "https://vidyut.readthedocs.io/en/latest/api.html#vidyut.prakriya.Sanadi",
            "https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/args/dhatu.rs",
        ],
    }
    target = SEARCH / "five_d/pilot-08-report-summary.json"
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")

    recipe_rows = []
    for recipe, ops in recipes.items():
        total, l = strata["recipe::" + recipe], matrix[recipe]["Lun"]
        nc, nn = total["correct"] - l["correct"], total["n"] - l["n"]
        recipe_rows.append(f'<tr><td>{NAMES[tuple(ops)]}<div class="small"><code>{" → ".join(ops)}</code></div></td>'
                           f'<td class="num">{total["n"]:,}<div class="small">{percent(total["n"], 2400, 0)} of panel</div></td>'
                           f'<td class="num">{percent(total["correct"], total["n"])}</td>'
                           f'<td class="num">{percent(l["correct"], l["n"])}<div class="small">{l["correct"]}/{l["n"]}</div></td>'
                           f'<td class="num">{percent(nc, nn)}<div class="small">{nc}/{nn}</div></td></tr>')
    history_html = []
    for ops in NAMES:
        h = history[ops]
        selected = next((plan["recipe_counts"][r] for r, operations in recipes.items() if tuple(operations) == ops), 0)
        history_html.append(f'<tr><td>{NAMES[ops]}</td><td><code>{" → ".join(ops)}</code></td>'
                            f'<td class="num">{h["n"]:,}</td><td class="num">{selected:,}</td></tr>')
    matrix_html = []
    for lakara, label in LAKARAS.items():
        t = strata["lakara::" + lakara]
        row = f'<tr><th scope="row">{label}</th><td class="num">{t["n"]:,} · {percent(t["n"], 2400)}</td>'
        for recipe in recipes:
            c = matrix[recipe][lakara]
            color = "#f5e9d8" if c["correct"] / c["n"] < .8 else "#edf5eb"
            row += f'<td class="num" style="background:{color}">{percent(c["correct"], c["n"])}<div class="small">{c["correct"]}/{c["n"]}</div></td>'
        matrix_html.append(row + "</tr>")
    gh = "https://github.com/ambuda-org/vidyut/blob/main/vidyut-prakriya/src/args/dhatu.rs"
    fragment = f'''{BEGIN}
<article id="five-d-summary" class="panel panel-pad five-d-summary" aria-labelledby="five-d-title">
<span class="eyebrow">5D development result · 7 October 2026 · frozen pilot08</span>
<h3 id="five-d-title">80.125% accuracy. Three selected derivation recipes.</h3>
<p class="forward-copy">Opus 5.5 answered <strong>1,923 of 2,400 questions correctly</strong> under xHigh / 65,536 tokens. This meets the 79–81% development accuracy target. The panel is broad across dhātus and person/number, but its difficulty is concentrated in two related intensive–causative recipes, especially in luṅ (aorist). <strong>It does not comprehensively explore the fifth-coordinate space.</strong></p>
<div class="cards"><div class="card"><span class="kicker">Opus 5.5 · all requests</span><div class="big">80.125%</div><p>80.60% on 2,386 usable answers.<br>14 refusals; zero truncated answers.</p></div><div class="card"><span class="kicker">Current fifth coordinate</span><div class="big">3 recipes</div><p>Seven recipes evaluated in the exact5D Opus pilot series. Four basic root operations supply their building blocks.</p></div><div class="card"><span class="kicker">Luṅ concentration</span><div class="big">45% of tasks</div><p>{percent(lun_wrong, wrong_usable, 1)} of wrong completed answers are aorists: {lun_wrong}/{wrong_usable}.</p></div></div>
<p class="forward-copy"><strong>Task shape:</strong> dictionary dhātu + tense/mood × voice × person × number × derivation recipe → one accepted Devanagari finite form. One fifth-coordinate value may contain an ordered sequence. No prefix or independent ending-set choice is added.</p>

<h4>Exactly which fifth-coordinate choices produce this result?</h4>
<div class="table-scroll" tabindex="0" aria-label="Recipe accuracy, including luṅ and other tenses"><table class="five-d-wide"><thead><tr><th>Recipe / ordered operations</th><th class="num">Questions / share</th><th class="num">Overall</th><th class="num">Luṅ only</th><th class="num">Other nine tenses</th></tr></thead><tbody>{''.join(recipe_rows)}</tbody></table></div>
<p class="caption">All accuracies in this table count refusals as incorrect. Earlier development evidence determined the 56% / 24% / 20% mixture. All 2,400 new tuples were then frozen before their answers were read; individual failures were not selected afterward. The change from earlier pilots also involved protocol and class/family composition, so the improvement cannot be attributed solely to the increased desiderative share.</p>
<div class="note warm" style="margin:20px 0"><strong>The hard interaction is recipe × luṅ.</strong> Luṅ accuracy is {percent(lun['correct'], lun['n'])}; accuracy on the other nine tenses combined is {percent(all_score['correct'] - lun['correct'], 2400 - lun['n'])}. Within luṅ, desideratives score 97.69%, while the intensive-with-deletion → causative recipe scores 43.85%. This is evidence of a concentrated weakness in these constructions, not a claim that all aorists or all derived roots are equally difficult.</div>
<p class="forward-copy"><strong>How much does the tense weighting matter?</strong> Giving each of the ten observed tense slices equal 10% weight changes the aggregate to <strong>{100 * equal_tense_score:.2f}%</strong>, keeping the existing mix within each slice. This is a descriptive reweighting of the same development answers, not a new evaluation or a prediction for a broader task generator. It makes clear that the 45% luṅ allocation contributes substantially to reaching 80%.</p>

<h4>What Vidyut supports, and what we have actually explored</h4>
<p class="forward-copy">There are three different counts: <strong>3 selected recipes</strong> in this panel; <strong>7 distinct recipes evaluated</strong> across the exact5D Opus pilots 01–08; and <strong>4 basic operations</strong> relevant to the dictionary-root contract. The API accepts an ordered list, so a recipe and a basic operation are not the same unit.</p>
<div class="table-scroll" tabindex="0" aria-label="Basic root operations"><table><thead><tr><th>Basic operation</th><th>Meaning</th><th>Use in the current panel</th></tr></thead><tbody><tr><td><code>Ric</code> · ṇic</td><td>Causative</td><td>Second operation in both intensive recipes</td></tr><tr><td><code>san</code></td><td>Desiderative</td><td>Standalone fifth-coordinate choice</td></tr><tr><td><code>yaN</code> · yaṅ</td><td>Intensive</td><td>First operation before causative</td></tr><tr><td><code>yaNluk</code> · yaṅ-luk</td><td>Intensive with suffix deletion</td><td>First operation before causative</td></tr></tbody></table></div>
<p class="forward-copy">The installed Python Vidyut 0.4.0 <code>Sanadi</code> enum exposes <strong>seven API values</strong>: these four plus <code>kAmyac</code>, <code>kyaN</code> and <code>kyac</code>. Those last three form verbs from nominal bases and fall outside this benchmark’s dictionary-dhātu input contract. The upstream source also explains that other rule-required suffixes can be supplied automatically; this enum is not an exhaustive list of all Sanskrit derivational suffixes. <a href="https://vidyut.readthedocs.io/en/latest/api.html#vidyut.prakriya.Sanadi">Python enum documentation ↗</a> · <a href="{gh}">Upstream Sanadi definitions and applicability ↗</a></p>
<details class="five-d-detail"><summary>See all seven recipes evaluated in the exact5D pilot series</summary><div class="table-scroll" tabindex="0"><table class="five-d-wide"><thead><tr><th>Recipe</th><th>Operations, in order</th><th class="num">Historical Opus requests</th><th class="num">Current 2,400</th></tr></thead><tbody>{''.join(history_html)}</tbody></table></div><p class="caption">Historical counts include the current panel and count each collected Opus request in pilots 01–08, before later source exclusions. Protocols and prompts changed; these counts demonstrate search exposure, not pooled accuracy or equal audit strength. Some recipes received only 10–35 questions. Earlier expanded-format campaigns are separate and do not establish coverage under this exact task contract. <a href="parallel-search-20261006/five_d/pilot-08-report-summary.json">Counts, job IDs and source hashes ↗</a></p></details>
<p class="forward-copy"><strong>Remaining fifth-coordinate gaps:</strong> standalone causative and both standalone intensives have zero weight in the current panel. Other ordered compositions—such as causative → desiderative and desiderative → causative—are absent from the current menu, as are longer sequences. The first is explicitly illustrated by Vidyut’s <a href="https://docs.rs/vidyut-prakriya/latest/vidyut_prakriya/args/enum.Dhatu.html">Dhatu API documentation</a>. A complete-space denominator requires a declared recipe menu, maximum sequence length and grammatical applicability rules; arbitrary operation lists are not automatically valid. “3 of 7 tried” is a search-history statement, not coverage of all possible Sanskrit recipes.</p>
<p class="forward-copy">Implementation: <code>entry.dhatu.with_sanadi([Sanadi.yaN, Sanadi.Ric])</code>, followed by <code>Vyakarana.derive(Pada.Tinanta(...))</code> with the four existing coordinates. <a href="https://vidyut.readthedocs.io/en/latest/prakriya.html#specifying-arguments">Official Python walkthrough ↗</a> · <a href="https://vidyut.readthedocs.io/en/latest/api.html#vidyut.prakriya.Dhatu.with_sanadi">with_sanadi reference ↗</a> · <a href="../misc/vp_cartesian_task.py">Our generator ↗</a> · <a href="{LINK}plan.json">Exact frozen menu ↗</a></p>

<h4>Coverage across the other coordinates</h4>
<div class="table-scroll" tabindex="0" aria-label="Diversity and its limitations"><table><thead><tr><th>Axis</th><th>Coverage</th><th>Limitation</th></tr></thead><tbody>
<tr><td>Dhātu families</td><td>670; at most 8 tasks per family</td><td>Family = exact dictionary citation plus class, not an etymological grouping. Historical lexical exposure remains.</td></tr>
<tr><td>Tense / mood</td><td>All 10; every recipe appears in every tense</td><td>1,080 luṅ questions (45%); 1,320 elsewhere (55%)</td></tr>
<tr><td>Person × number</td><td>800 per person and per number; all nine pairs have 266 or 267 tasks</td><td>Balanced globally, not necessarily inside each recipe/tense cell</td></tr>
<tr><td>Verb class</td><td>All 10 classes</td><td>1,535/2,400 (63.96%) Bhvādi; Juhotyādi and Tanādi have only two families each</td></tr>
<tr><td>Voice</td><td>90% agentive; 10% passive</td><td>All luṅ questions are agentive; no bhāve questions</td></tr>
<tr><td>Fifth coordinate</td><td>Three recipes</td><td>80% of the panel uses two closely related intensive–causative recipes</td></tr>
</tbody></table></div>
<p class="forward-copy">The panel occupies <strong>{cells['recipe×lakara']}/30 recipe × tense cells</strong>, <strong>{cells['recipe×lakara×prayoga']}/60 recipe × tense × voice cells</strong>, and <strong>{cells['recipe×lakara×prayoga×purusha×vacana']}/540 nominal five-coordinate cells</strong>. The last denominator is 3 recipes × 10 tenses × 2 voices × 3 persons × 3 numbers, ignoring dhātu identity and applicability. These are descriptive grid counts, not percentages of all grammatically legal forms; no exhaustive legal-space census is claimed.</p>
<details class="five-d-detail" id="five-d-tense-matrix"><summary>Inspect every recipe × tense cell: accuracy and question count</summary><p class="caption">Opus all-request accuracy; correct/total below each percentage. Orange cells are below 80%. Voice, person and number are pooled.</p><div class="table-scroll" tabindex="0"><table class="five-d-wide"><thead><tr><th>Tense / mood</th><th class="num">Questions / share</th><th class="num">yaN → Ric</th><th class="num">yaNluk → Ric</th><th class="num">san</th></tr></thead><tbody>{''.join(matrix_html)}</tbody></table></div></details>
<p class="forward-copy">Wrong completed answers occur across <strong>{len(wrong_families)} families</strong>, including <strong>{len(wrong_non_lun_families)} with non-luṅ errors</strong>. Thus lexical diversity is meaningful, while the difficult grammatical mechanisms remain concentrated. These are current-key scoring disagreements; source review is still in progress.</p>
<div class="note" style="margin-top:20px"><strong>Assessment:</strong> a promising, deliberately selected challenge set for derived-verb composition, with broad root and person/number coverage. It is not yet a representative survey of the full 5D space. To support a broader claim, the next design would need declared recipe-coverage floors, more balanced sampling across valid recipe × tense combinations, and separate luṅ/non-luṅ results. Rebalancing could raise model accuracy; the current 80.125% does not establish that a broader mixture will also reach 80%.</div>
<p class="caption"><strong>Qualification still open.</strong> Frozen policy21 raw result; grammatical and accepted-spelling review remains open. All-request iid SE is {100*all_score['iid_standard_error']:.3f} percentage points; unstratified family SE is {100*all_score['root_cluster_sandwich_standard_error']:.3f}, just above the required &lt;1. Usable-answer family SE is {100*usable_score['root_cluster_sandwich_standard_error']:.3f}. The paired 240-question diagnostic scored Opus 83.75% and Astra 78.75%, but deliberately enriches repeated-aorist families and does not establish whole-panel Astra accuracy or strongest-model ordering. A separate frozen final evaluation and both-model precision checks remain necessary. No RL run or qualified final benchmark is claimed.</p>
<p class="caption"><a href="{LINK}aggregate-analysis.json">Frozen results and uncertainty ↗</a> · <a href="{LINK}analysis-predeclaration.json">Predeclared evaluation ↗</a> · <a href="parallel-search-20261006/five_d/pilot-08-report-summary.json">Coverage data and provenance ↗</a>. This summary is a dated snapshot; later source corrections must be reported separately without rewriting the raw record.</p>
</article>
{END}'''
    path = ROOT / "misc/benchmark_report.template.html"
    template = path.read_text()
    if BEGIN in template:
        start, end = template.index(BEGIN), template.index(END) + len(END)
        template = template[:start] + fragment + template[end:]
    else:
        anchor = '<div id="parallel-search-panel"'
        assert template.count(anchor) == 1
        template = template.replace(anchor, fragment + "\n" + anchor)
    path.write_text(template)
    print(json.dumps({"summary": str(target.relative_to(ROOT)), "recipes": len(recipes),
                      "historical_recipes": len(history), "cells": cells,
                      "wrong_completed_families": len(wrong_families)}))


if __name__ == "__main__":
    main()
