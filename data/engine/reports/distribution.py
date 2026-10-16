#!/usr/bin/env python3
"""Build the offline dataset report: python3 data/engine/reports/distribution.py."""

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/datasets"
FAMILIES = ("tinanta", "krdanta", "subanta", "taddhitanta")
NAMES = dict(zip(FAMILIES, ("Tiṅanta", "Kṛdanta", "Subanta", "Taddhitānta")))


def n(value):
    return f"{value:,}"


def bar(label, count, denominator, color, detail="", percentage_only=False):
    value = f"{100 * count / denominator:.6f}%" if percentage_only else n(count)
    return (
        f'<div class="bar-row"><div class="bar-label"><span>{label}</span>'
        f'<span class="number">{value}{detail}</span></div>'
        f'<div class="track" aria-hidden="true"><div style="width:{100 * count / denominator:.7f}%;'
        f'background:var(--{color})"></div></div></div>'
    )


def build():
    manifests = {f: json.loads((DATA / f / "manifest.json").read_text()) for f in FAMILIES}
    counts = {f: m["counts"] for f, m in manifests.items()}
    totals = {f: c["all"] if f == "tinanta" else c["full"] for f, c in counts.items()}
    total = sum(totals.values())
    t, k, s, d = (counts[f] for f in FAMILIES)
    candidates = {f: c["candidates"] for f, c in counts.items()}
    total_attempts = sum(candidates.values())
    suffixes = json.loads((DATA / "taddhitanta/suffixes.json").read_text())
    suffix_names = {x["id"]: x["technical_name_devanagari"] for x in suffixes}
    assert len(suffixes) == d["suffixes"] == len(d["per_suffix"])
    assert sum(d["tasks_per_base"].values()) == d["bases"]
    assert sum(int(a) * b for a, b in d["tasks_per_base"].items()) == d["full"]
    assert sum(x["exported"] for x in d["per_suffix"].values()) == d["full"]
    assert d["full"] + d["no_forms"] + d["invalid_gold_encoding"] + d["engine_errors"] == d["candidates"]
    assert k["full"] + sum(k["excluded"].values()) + k["engine_errors"] == k["candidates"]
    assert sum(s["per_gender"].values()) == s["full"]
    # The explanatory prose describes these fixed grammatical scopes.
    assert t["roots"] == k["roots"] and t["candidate_coordinates_per_root"] == 270
    assert t["coordinates_per_root"] == 190
    assert k["suffixes"] == 14 and d["suffixes"] == 175
    assert manifests["subanta"]["scope"]["tasks_per_stem_gender"] == 24
    assert manifests["subanta"]["schema_version"] == manifests["taddhitanta"]["schema_version"] == 2
    assert manifests["subanta"]["source"]["sha256"] == manifests["taddhitanta"]["source"]["sha256"]
    assert s["stem_gender_pairs"] == d["bases"]
    for f, c in counts.items():
        assert sum(c["gold_forms_per_task"].values()) == totals[f]

    overview = "".join(bar(f'<a href="#{f}">{NAMES[f]}</a>', candidates[f], total_attempts, f,
                           percentage_only=True) for f in FAMILIES)
    segments = "".join(f'<span style="width:{100 * candidates[f] / total_attempts:.7f}%;background:var(--{f})" '
                       f'title="{NAMES[f]}: {n(candidates[f])} candidates"></span>' for f in FAMILIES)
    outcome_counts = {
        "tinanta": [totals["tinanta"], t["excluded_by_reason"]["bhave_requires_third_person_singular"],
                    t["excluded_by_reason"]["no_forms"], t["excluded_by_reason"]["invalid_gold_encoding"],
                    t["excluded_by_reason"]["ambiguous_prompt"], t["status"]["error"]],
        "krdanta": [k["full"], 0, k["excluded"]["no_forms"], k["excluded"]["invalid_gold_encoding"],
                    k["excluded"]["ambiguous_prompt"], k["engine_errors"]],
        "subanta": [s["full"], 0, s["excluded_by_reason"].get("no_forms", 0),
                    s["excluded_by_reason"].get("invalid_gold_encoding", 0), 0, s["engine_errors"]],
        "taddhitanta": [d["full"], 0, d["no_forms"], d["invalid_gold_encoding"], 0, d["engine_errors"]],
    }
    for f, values in outcome_counts.items():
        assert sum(values) == candidates[f]
    attempt_rows = "".join(
        f'<tr><th scope="row">{NAMES[f]}</th><td>{n(candidates[f])}</td>'
        + "".join(f'<td title="{n(value)} / {n(candidates[f])} candidates">{100 * value / candidates[f]:.6f}%</td>'
                  for value in outcome_counts[f]) + '</tr>'
        for f in FAMILIES
    )
    krt_bars = "".join(bar(f'<code>{escape(suffix)}</code> <span class="muted">{escape(manifests["krdanta"]["scope"]["suffixes"][suffix]["gloss"])}</span>',
                            count, k["candidates"], "krdanta", percentage_only=True) for suffix, count in k["per_suffix"].items())
    gender_names = {"Pum": "Masculine", "Stri": "Feminine", "Napumsaka": "Neuter"}
    gender_bars = "".join(bar(gender_names[g], s["per_gender"][g], s["full"], "subanta",
                               f' <span class="muted">· {100 * s["per_gender"][g] / s["full"]:.2f}%</span>')
                          for g in ("Pum", "Stri", "Napumsaka"))
    rows_hist = "".join(f'<tr><th scope="row">{a}</th><td>{n(b)}</td></tr>'
                        for a, b in s["source_rows"]["exported_tasks_per_row"].items())
    case_names = ("Nominative", "Accusative", "Instrumental", "Dative", "Ablative", "Genitive", "Locative", "Vocative")
    assert s["full"] == s["candidates"] == s["stem_gender_pairs"] * 24
    subanta_cells = "".join(
        f'<tr><th scope="row">{name}</th>' + "".join(
            f'<td class="outcome-cell" data-share="{100 / 24}" title="{n(s["stem_gender_pairs"])} / {n(s["candidates"])} attempts">'
            f'{100 / 24:.2f}%</td>' for _ in range(3)) + '</tr>' for name in case_names
    )
    hist = d["tasks_per_base"]
    mode = max(hist, key=hist.get)
    peak = max(hist.values())
    lower, upper = min(map(int, hist)), max(map(int, hist))
    hist_bars = "".join(
        f'<div class="hist-bin"><div class="hist-space"><span style="height:{100 * hist.get(str(i), 0) / peak:.4f}%" '
        f'title="{i} tasks: {n(hist.get(str(i), 0))} nominal inputs"></span></div>'
        f'<span class="hist-tick">{i if (i - lower) % 4 == 0 else ""}</span></div>'
        for i in range(lower, upper + 1)
    )
    hist_rows = "".join(f'<tr><th scope="row">{a} / {d["suffixes"]}</th><td>{100 * int(a) / d["suffixes"]:.6f}%</td><td>{n(b)}</td></tr>'
                        for a, b in hist.items())
    suffix_rows = "".join(
        f'<tr data-suffix="{escape(suffix, quote=True)}" data-deva="{escape(suffix_names[suffix], quote=True)}">'
        f'<th scope="row"><code>{escape(suffix)}</code></th><td lang="sa">{escape(suffix_names[suffix])}</td>'
        f'<td>{100 / d["suffixes"]:.6f}%</td>'
        f'<td data-count="exported">{n(values["exported"])}</td>'
        f'<td data-outcome="exported">{100 * values["exported"] / d["candidates"]:.6f}%</td>'
        f'<td data-outcome="no_forms">{100 * values["no_forms"] / d["candidates"]:.6f}%</td>'
        f'<td data-outcome="encoding">{100 * values["invalid_gold_encoding"] / d["candidates"]:.6f}%</td></tr>'
        for suffix, values in sorted(d["per_suffix"].items(), key=lambda x: (-x[1]["exported"], x[0]))
    )
    zero_suffixes = ", ".join(f'<code>{escape(a)}</code>' for a, b in d["per_suffix"].items() if not b["exported"])
    nonempty_suffixes = sum(v["exported"] > 0 for v in d["per_suffix"].values())
    multiple_rows = "".join(
        f'<tr><th scope="row">{NAMES[f]}</th><td>{n(c["gold_forms_per_task"]["1"])}</td>'
        f'<td>{n(totals[f] - c["gold_forms_per_task"]["1"])}</td>'
        f'<td>{100 * (totals[f] - c["gold_forms_per_task"]["1"]) / candidates[f]:.6f}%</td></tr>'
        for f, c in counts.items()
    )
    sources = "".join(f'<li><a href="{f}/manifest.json">{NAMES[f]} manifest</a> · '
                       f'<a href="{f}/README.md">dataset notes</a></li>' for f in FAMILIES)
    timestamps = [datetime.fromtimestamp((DATA / f / "manifest.json").stat().st_mtime, timezone.utc) for f in FAMILIES]
    snapshot = max(timestamps).strftime("%Y-%m-%d %H:%M UTC")
    # Replace template literals before inserting generated tables. Counts in
    # explanatory prose must follow the manifests just like the charts do.
    literal_counts = {
        "601,830": t["all"], "2,229": t["roots"],
        "178,320": t["excluded_by_reason"]["bhave_requires_third_person_singular"],
        "27,470": k["full"], "31,206": k["candidates"],
        "3,724": k["excluded"]["no_forms"], "1,792,152": s["full"],
        "74,673": s["stem_gender_pairs"], "224,019": s["full"] // 8,
        "597,384": s["full"] // 3, "55,230": s["source_rows"]["rows_with_tasks"],
        "197,652": s["source_rows"]["rows"],
        "142,422": s["source_rows"]["row_status"]["excluded"],
        "8,731,509": d["full"], "196,769": d["bases"],
        "34,434,575": d["candidates"], "25,703,033": d["no_forms"],
    }
    import re
    text = re.sub("|".join(map(re.escape, literal_counts)),
                  lambda match: n(literal_counts[match.group()]), TEMPLATE)
    text = text.replace("Another 12", f'Another {n(k["excluded"]["ambiguous_prompt"])}')
    text = text.replace("33 produced", f'{n(d["invalid_gold_encoding"])} produced')
    text = text.replace("34–58", f"{lower}–{upper}").replace("34 to 58", f"{lower} to {upper}")
    text = text.replace("<strong>21</strong>", f'<strong>{d["suffixes"] - nonempty_suffixes}</strong>')
    text = text.replace("The 21 suffixes", f'The {d["suffixes"] - nonempty_suffixes} suffixes')
    substitutions = {
        "TOTAL": n(total), "TOTAL_ATTEMPTS": n(total_attempts),
        "TINANTA_CANDIDATES": n(t["candidates"]), "TINANTA_ATTEMPTED": n(t["attempted"]),
        "TINANTA_CONFLICTS": n(t["excluded_by_reason"]["ambiguous_prompt"]),
        "TADDHITA_SHARE": f'{100 * d["candidates"] / total_attempts:.2f}',
        "OVERVIEW": overview, "SEGMENTS": segments, "ATTEMPT_ROWS": attempt_rows,
        "KRT_BARS": krt_bars, "GENDER_BARS": gender_bars, "SOURCE_ROW_HIST": rows_hist,
        "HIST_BARS": hist_bars, "HIST_ROWS": hist_rows, "SUFFIX_ROWS": suffix_rows,
        "ZERO_SUFFIXES": zero_suffixes, "NONEMPTY_SUFFIXES": str(nonempty_suffixes),
        "MEAN_PER_BASE": f'{d["full"] / d["bases"]:.2f}', "MULTIPLE_ROWS": multiple_rows,
        "SOURCES": sources, "SNAPSHOT": snapshot,
        "SUBANTA_CELLS": subanta_cells,
        "TADDHITA_NO_FORMS": f'{100 * d["no_forms"] / d["candidates"]:.6f}',
        "TADDHITA_ENCODING": f'{100 * d["invalid_gold_encoding"] / d["candidates"]:.6f}',
        "TADDHITA_EXPORT_SHARE": f'{100 * d["full"] / d["candidates"]:.6f}',
        "TADDHITA_EXPORT_COUNT": n(d["full"]),
        "TADDHITA_SUFFIX_SHARE": f'{100 / d["suffixes"]:.6f}',
        "TADDHITA_RETENTION": f'{100 * d["full"] / d["candidates"]:.2f}',
        "TOP_BIN_SHARE": f'{100 * hist[mode] / d["bases"]:.2f}',
        "MODE": mode, "MODE_INPUTS": n(hist[mode]),
        "MODE_SHARE": f'{100 * int(mode) / d["suffixes"]:.2f}',
        "RANGE_SHARE": f'{100 * lower / d["suffixes"]:.2f}–{100 * upper / d["suffixes"]:.2f}',
        "HIST_PEAK": n(peak), "HIST_HALF": n(peak // 2),
        "NOMINAL_SHARE": f'{100 * (s["candidates"] + d["candidates"]) / total_attempts:.2f}',
        "MANIFEST_DATA": json.dumps({f: {"counts": counts[f], "full_json": manifests[f]["files"]["full.json"]}
                                      for f in FAMILIES}, ensure_ascii=False).replace("<", "\\u003c"),
    }
    for key, value in substitutions.items():
        text = text.replace("@@" + key + "@@", value)
    assert "@@" not in text
    output = DATA / "distribution.html"
    output.write_text(text, encoding="utf-8")
    print(f"Wrote {output} ({n(output.stat().st_size)} bytes; {n(total)} tasks)")


TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Distribution, generation scope, and suffix coverage of the four Sanskrit morphology task inventories.">
<title>Sanskrit morphology · Task distribution</title>
<style>
:root{--paper:#f5f3ed;--panel:#fffefa;--ink:#202b31;--muted:#56646b;--line:#d8dedb;--track:#e7ebe7;--tinanta:#386eb7;--krdanta:#b25b2c;--subanta:#7156a6;--taddhitanta:#137b70;--accent:#095f57;--notice:#f9f0db;--notice-ink:#694515;--code:#ebeeea;color-scheme:light}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans Devanagari",sans-serif}a{color:var(--accent);text-underline-offset:3px}a:hover{text-decoration-thickness:2px}button,input{font:inherit}a:focus-visible,summary:focus-visible,input:focus-visible{outline:3px solid var(--tinanta);outline-offset:4px}h1,h2,h3,p{margin:0}h1{font-size:clamp(2.2rem,5vw,4rem);line-height:1.09;letter-spacing:-.045em;font-weight:650;max-width:800px}h2{font-size:1.55rem;line-height:1.3;letter-spacing:-.025em}h3{font-size:1.08rem;line-height:1.4}p+p{margin-top:12px}.wrap{max-width:1120px;margin:auto;padding:0 32px}.top{border-bottom:1px solid var(--line)}.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:20px;padding-top:19px;padding-bottom:19px}.brand{font-size:12px;font-weight:700;letter-spacing:.13em;text-transform:uppercase}.top nav{display:flex;gap:20px;flex-wrap:wrap;font-size:13px}.top a{text-decoration:none}.hero{padding:58px 0 28px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:650;color:var(--muted);margin-bottom:15px}.lead{max-width:790px;margin-top:23px;color:var(--muted);font-size:18px;line-height:1.6}.hero-total{display:flex;align-items:baseline;gap:15px;flex-wrap:wrap;margin:27px 0 8px}.hero-total strong{font-size:clamp(2.2rem,6vw,3.8rem);line-height:1.15;letter-spacing:-.035em;font-weight:600;font-variant-numeric:tabular-nums}.muted,.caption{color:var(--muted)}.caption{font-size:13px;line-height:1.6}.number,td{font-variant-numeric:tabular-nums}.section{padding:34px 0;border-top:1px solid var(--line)}.section-intro{max-width:800px;margin:12px 0 25px;color:var(--muted)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:26px}.grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:30px}.grid-equal{grid-template-columns:repeat(2,minmax(0,1fr))}.bar-row+.bar-row{margin-top:18px}.bar-label{display:flex;align-items:baseline;justify-content:space-between;gap:16px;line-height:1.5;margin-bottom:7px}.bar-label a{color:var(--ink);text-decoration:none;font-weight:600}.bar-label .number{white-space:nowrap;font-size:14px}.track{height:9px;background:var(--track);overflow:hidden;border-radius:2px}.track>div{height:100%}.stack{display:flex;height:25px;margin:23px 0 28px;border-radius:4px;overflow:hidden}.stack>span{height:100%}.takeaway{font-size:1.35rem;line-height:1.5;letter-spacing:-.02em;margin-bottom:18px}.takeaway strong{color:var(--taddhitanta)}.factline{display:flex;justify-content:space-between;gap:20px;padding:12px 0;border-top:1px solid var(--line);font-size:14px}.factline strong{font-variant-numeric:tabular-nums;white-space:nowrap}.family-heading{display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:18px}.family-heading h2:before{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--family);margin-right:12px}.family-count{font-size:24px;font-weight:600;font-variant-numeric:tabular-nums;color:var(--family)}.formula{font-size:18px;font-weight:600;margin:14px 0;color:var(--family);line-height:1.6}.example{padding:17px 20px;border-left:3px solid var(--family);background:var(--panel);margin:20px 0}.example .sa{font-size:23px;line-height:1.9}.example small{display:block;color:var(--muted)}.note{padding:16px 18px;background:var(--notice);color:var(--notice-ink);border-radius:8px;font-size:14px;margin-top:18px}.detail-title{margin:24px 0 13px}ul{padding-left:21px;margin:12px 0}li+li{margin-top:5px}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em;background:var(--code);padding:2px 5px;border-radius:3px;overflow-wrap:anywhere}.table-wrap{overflow-x:auto;margin:18px 0}table{width:100%;border-collapse:collapse;font-size:14px}caption{text-align:left;font-weight:600;margin-bottom:10px}th,td{padding:12px 13px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}thead th{font-size:12px;color:var(--muted);font-weight:600}th:first-child{text-align:left}tbody th{font-weight:500}tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}.table-wrap>.small-table{max-width:520px}details{border-top:1px solid var(--line);padding-top:16px;margin-top:20px}summary{cursor:pointer;font-weight:600;min-height:32px;line-height:1.6}details[open]>summary{margin-bottom:16px}.histogram{display:grid;grid-template-columns:49px minmax(0,1fr);gap:10px;margin-top:18px}.hist-axis{height:200px;display:flex;flex-direction:column;justify-content:space-between;text-align:right;font-size:11px;color:var(--muted);line-height:1}.hist-plot{display:grid;grid-template-columns:repeat(25,minmax(0,1fr));gap:3px;background:linear-gradient(to bottom,transparent calc(50% - 14px),var(--line) calc(50% - 14px),var(--line) calc(50% - 13px),transparent calc(50% - 13px));border-top:1px solid var(--line)}.hist-space{height:199px;display:flex;align-items:flex-end;border-bottom:1px solid var(--line)}.hist-space span{display:block;width:100%;background:var(--taddhitanta)}.hist-tick{display:block;text-align:center;font-size:11px;color:var(--muted);height:27px;padding-top:4px}.axis-label{text-align:center;font-size:12px;color:var(--muted);margin:7px 0 15px}.search{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin:18px 0}.search label{font-size:14px;font-weight:600}.search input{padding:9px 12px;max-width:100%;min-width:240px;border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink)}.search output{font-size:13px;color:var(--muted)}[hidden]{display:none!important}.sources{display:flex;gap:24px;flex-wrap:wrap;list-style:none;padding:0;font-size:13px}.sources li{margin:0}.footer{padding:24px 0 45px;color:var(--muted);font-size:12px}.nowrap{white-space:nowrap}.compact-bars .bar-label{font-size:14px}.compact-bars .bar-label>span:first-child{max-width:75%}.compact-bars .bar-row+.bar-row{margin-top:12px}.compact-bars .track{height:6px}
.outcome-cell{background:color-mix(in srgb,var(--subanta) 12%,transparent);font-weight:600}tfoot td,tfoot th{border-top:2px solid var(--line);font-weight:600}
.request-flow{margin:0}.flow-source,.flow-node{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:20px;min-width:0}.flow-source{border-top:3px solid var(--accent)}.flow-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:16px 0 0}.flow-fields dt{font-size:13px;font-weight:600}.flow-fields dd{margin:7px 0 0}.flow-fields .caption{margin-top:8px}.flow-lanes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px}.flow-lane{min-width:0;--lane:var(--subanta)}.flow-lane.taddhita{--lane:var(--taddhitanta)}.flow-lane h3{color:var(--lane)}.flow-arrow{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:48px;color:var(--lane);line-height:1.15;font-size:25px}.flow-arrow small{font-size:12px;margin-top:4px}.flow-node{border-left:3px solid var(--lane)}.flow-node h4{font-size:15px;margin:0 0 10px}.flow-node p,.flow-node li{font-size:14px}.flow-node ol,.flow-node ul{margin:10px 0 0}.flow-node .caption{font-size:12px}.flow-path+.flow-path{border-top:1px solid var(--line);padding-top:14px;margin-top:14px}.flow-node pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.65;margin:14px 0 0;background:var(--code);padding:13px;border-radius:6px}.flow-node pre code{background:none;padding:0}.flow-result{font-size:20px!important;color:var(--lane);font-weight:600;margin:10px 0!important}.flow-inventory{border-top:1px solid var(--line);padding-top:12px;margin-top:14px!important}.flow-legend{margin-top:20px}.flow-step{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:8px!important}
@media(max-width:760px){.flow-fields,.flow-lanes{grid-template-columns:1fr}.flow-fields{gap:12px}.flow-fields>div+div{border-top:1px solid var(--line);padding-top:12px}.flow-node,.flow-source{padding:16px}.flow-lanes{gap:16px}}
@media(prefers-color-scheme:dark){:root{--paper:#172124;--panel:#1d292d;--ink:#edf1ec;--muted:#b0c0c4;--line:#3b4b50;--track:#344248;--tinanta:#8db6f0;--krdanta:#edaa7c;--subanta:#b9a4e0;--taddhitanta:#6bc7b1;--accent:#94d9c7;--notice:#373020;--notice-ink:#eed4a0;--code:#344248;color-scheme:dark}}
@media(max-width:760px){.wrap{padding:0 20px}.top .wrap{align-items:flex-start;flex-direction:column;gap:10px}.hero{padding-top:34px}.grid,.grid-equal{grid-template-columns:1fr;gap:24px}.panel{padding:20px}.section{padding:28px 0}.lead{font-size:16px}.top nav{gap:17px}.bar-label{gap:10px}.bar-label .number{font-size:13px}.family-count{font-size:21px}.hist-plot{gap:2px}.hist-tick{font-size:10px}.compact-bars .bar-label .muted{display:block;font-size:12px}.sources{gap:12px 20px}th,td{padding:10px}.search input{min-width:0;width:100%}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{background:white;color:black;font-size:11px}.wrap{max-width:none;padding:0}.top nav,.search{display:none}.hero{padding-top:20px}h1{font-size:32px}.section{break-inside:avoid}.panel{background:none}.grid{grid-template-columns:1fr 1fr}.table-wrap{overflow:visible}a{color:inherit}.footer{padding-bottom:0}}
</style>
</head>
<body>
<header class="top"><div class="wrap"><a class="brand" href="#overview">Sanskrit / Dataset atlas</a><nav aria-label="Report sections"><a href="#overview">Distribution</a><a href="#generation">Generation</a><a href="#taddhitanta">Suffix coverage</a><a href="#sources">Sources</a><a href="#row-to-request">Row → request</a></nav></div></header>
<main class="wrap">
<header class="hero" id="overview"><p class="eyebrow">Four morphology families · VP 0.4.0</p><h1>How the tasks<br>are distributed.</h1><p class="lead">Percentages use the complete candidate space, including invalid coordinates and requests that produced no form. Within each family, every percentage is labelled with its denominator.</p><div class="hero-total"><strong>@@TOTAL_ATTEMPTS@@</strong><span class="muted">candidate requests</span></div><p class="caption">@@TOTAL@@ requests were exported as tasks. Multiple accepted forms still count as one task.</p></header>
<section class="section" aria-labelledby="mix-title"><div class="grid"><div><h2 id="mix-title">Share of all candidate requests</h2><div class="stack" role="img" aria-label="Proportional distribution of the four task families; exact counts and percentages follow.">@@SEGMENTS@@</div>@@OVERVIEW@@<p class="caption" style="margin-top:18px">All four bars use the same scale: percentage of all @@TOTAL_ATTEMPTS@@ candidate requests, including empty results.</p></div><aside class="panel"><p class="takeaway"><strong>@@TADDHITA_SHARE@@% of candidates are taddhitānta.</strong> The broad stem inventory and 175 suffix attempts per input drive the overall distribution.</p><p class="muted">Within a family, the denominator is its complete request grid: 270 cells per verbal root, 14 selected primary suffixes per root, 24 case–number cells per stem–gender pair, or 175 secondary suffixes per nominal input.</p><div class="factline" style="margin-top:19px"><span>Candidates starting from nominal stems</span><strong>@@NOMINAL_SHARE@@%</strong></div><div class="factline"><span>Different family scopes</span><strong>4</strong></div><p class="caption">The candidate space includes exported, empty, and excluded results. It describes the current generation scope.</p></aside></div></section>
<section class="section" id="generation" aria-labelledby="generation-title"><h2 id="generation-title">Candidates → exported questions</h2><p class="section-intro">A candidate is one input combination in the full request grid. Invalid tiṅanta coordinates are excluded before calling VP; the remaining candidates are sent to the engine. A retained task has usable output under its family’s export rules. Each row below accounts for 100% of its candidate space, including excluded requests.</p><div class="table-wrap"><table><caption>Outcomes as a percentage of all candidates in each family</caption><thead><tr><th scope="col">Family</th><th scope="col">Candidates</th><th scope="col">Exported</th><th scope="col">Invalid coordinate</th><th scope="col">No forms</th><th scope="col">Encoding failure</th><th scope="col">Conflicting prompt</th><th scope="col">Engine error</th></tr></thead><tbody>@@ATTEMPT_ROWS@@</tbody></table></div><p class="caption">Subanta attempts begin after stem selection; excluded source rows are outside that denominator. Tiṅanta’s denominator includes invalid coordinates, but its exported tasks exclude them. No engine errors were recorded in these exports. Percentages may differ slightly from 100% when added after rounding.</p></section>
<section class="section" id="tinanta" style="--family:var(--tinanta)"><div class="family-heading"><h2>Tiṅanta · Conjugate a verb</h2><span class="family-count">601,830 tasks</span></div><div class="grid"><div><p>Start with a verbal root and specify its tense or mood, construction, person, and number. The answer is the inflected verb.</p><p class="formula">2,229 roots × 10 × 3 × 3 × 3<br>= 270 candidate cells per root<br>190 eligible cells × 2,229 roots<br>= @@TINANTA_ATTEMPTED@@ engine requests</p><div class="example"><div class="sa" lang="sa">भू → भवति</div><small>Present · active · third person · singular</small></div><p class="caption">Source: the pinned Dhātupāṭha. All 2,229 roots are considered. Bhāve (impersonal) permits only third-person singular, leaving 90 active + 90 passive + 10 impersonal cells per root. Conflicting prompts are then removed.</p></div><div class="panel"><h3>Share of the raw 270-cell candidate space</h3><div class="factline" style="margin-top:12px"><span>Each of 10 tense/mood categories</span><strong>10.00%</strong></div><div class="factline"><span>Each of 3 constructions</span><strong>33.33%</strong></div><div class="factline"><span>Each of 3 persons</span><strong>33.33%</strong></div><div class="factline"><span>Each of 3 numbers</span><strong>33.33%</strong></div><p class="caption">Each fully specified tense/mood × construction × person × number cell represents <strong>1 / 270 = 0.37037%</strong> of all @@TINANTA_CANDIDATES@@ tiṅanta candidates, before exclusions. The axis percentages above are separate marginal distributions; they do not describe the retained tasks.</p></div></div><div class="note"><strong>Excluded from the export:</strong> 178,320 impersonal (bhāve) coordinates fall outside third-person singular. Another @@TINANTA_CONFLICTS@@ requests produce identical prompts with conflicting answer sets. Both exclusions are recorded in <a href="tinanta/excluded_tasks.json">the audit</a>; no warning-bearing rows remain in <code>full.json</code>.</div></section>
<section class="section" id="krdanta" style="--family:var(--krdanta)"><div class="family-heading"><h2>Kṛdanta · Derive from a verbal root</h2><span class="family-count">27,470 tasks</span></div><div class="grid"><div><p>Apply a primary suffix to a root to form a participle, agent noun, infinitive, absolutive, gerundive, or another nominal derivative.</p><p class="formula">2,229 roots × 14 selected suffixes<br>= 31,206 attempts</p><div class="example"><div class="sa" lang="sa">कृ + क्त → कृत</div><small>Derived stem; no case-and-number inflection is added.</small></div><p>3,724 attempts produced no forms. Another 12 were excluded because identical prompts had conflicting answer sets.</p><p class="caption" style="margin-top:14px">This family still uses the existing 14-suffix scope. The all-suffix expansion applies to taddhitānta.</p></div><div><h3>Exported share of all 14-suffix attempts</h3><p class="caption" style="margin:8px 0 16px">Denominator: 31,206 root × suffix attempts. Each suffix has a 1 / 14 = 7.14286% share available; the bar shows the portion exported. Bars use a 0–100% scale. IDs are case-sensitive SLP1.</p><div class="compact-bars">@@KRT_BARS@@</div></div></div></section>
<section class="section" id="subanta" style="--family:var(--subanta)"><div class="family-heading"><h2>Subanta · Decline a nominal stem</h2><span class="family-count">1,792,152 tasks</span></div><div class="grid"><div><p>Start from a resolved nominal stem and gender, then ask for a case and number. The feminine stem is supplied when its spelling changes.</p><p class="formula">74,673 stem–gender pairs<br>× 8 cases × 3 numbers = 24 per pair</p><div class="example"><div class="sa" lang="sa">देव → देवेन</div><small>Masculine · instrumental · singular</small></div><p>One gender can contribute 24 questions; two, 48; three, 72. Entries with alternative stems can contribute more. Duplicate grammatical inputs across dictionary entries are merged.</p></div><div class="panel"><h3>Distribution by gender</h3><div style="margin-top:20px">@@GENDER_BARS@@</div><p class="caption" style="margin-top:18px">Each bar shows its share of all subanta attempts; all attempts were retained. Cases include the vocative; numbers are singular, dual, and plural.</p><div class="factline" style="margin-top:17px"><span>Each case: 3 of 24 cells</span><strong>12.50%</strong></div><div class="factline"><span>Each number: 8 of 24 cells</span><strong>33.33%</strong></div></div></div><div class="cell-space"><h3 style="margin-top:25px">All 24 case–number cells</h3><p class="caption" style="margin-top:8px">Each cell is <strong>1 / 24 = 4.16667%</strong> of the complete subanta space. All 74,673 stem–gender pairs were attempted in every cell, and all results were retained. The denominator is 1,792,152 attempts.</p><div class="table-wrap"><table id="subanta-cells"><caption>Share of all subanta attempts, by case and number</caption><thead><tr><th scope="col">Case</th><th scope="col">Singular</th><th scope="col">Dual</th><th scope="col">Plural</th></tr></thead><tbody>@@SUBANTA_CELLS@@</tbody><tfoot><tr><th scope="row">All 24 cells</th><td colspan="3">100.00% attempted · 100.00% retained</td></tr></tfoot></table></div><p class="caption">Displayed cells are rounded to two decimals; their unrounded shares add to 100%.</p></div><details><summary>How MWlexnorm rows become subanta tasks</summary><p>55,230 of 197,652 source rows contribute tasks. The remaining 142,422 rows fall outside this adapter's current scope. Compound boundaries, unresolved feminine stems, special lexical metadata, and unsupported stem classes account for the exclusions.</p><div class="table-wrap"><table class="small-table"><caption>Associated tasks per source row</caption><thead><tr><th scope="col">Tasks associated with a row</th><th scope="col">Source rows</th></tr></thead><tbody>@@SOURCE_ROW_HIST@@</tbody></table></div><p class="caption">These row counts include tasks shared by multiple dictionary entries. Multiplying and summing the rows would double-count some tasks. The unique total is 1,792,152.</p></details></section>
<section class="section" id="taddhitanta" style="--family:var(--taddhitanta)"><div class="family-heading"><h2>Taddhitānta · Derive from a nominal stem</h2><span class="family-count">8,731,509 tasks</span></div><div class="grid"><div><p>Apply a secondary suffix to a nominal input. All 175 suffix choices exposed by VP were attempted for every input, with no specific meaning (<em>artha</em>) imposed.</p><p class="formula">196,769 inputs × 175 suffixes<br>= 34,434,575 attempts</p><div class="example"><div class="sa" lang="sa">धन + मतुप् → धनवत्</div><small>A derived stem meaning “possessing wealth.”</small></div><p>Across all 175 attempts per input: <strong>@@TADDHITA_EXPORT_SHARE@@%</strong> were exported, <strong>@@TADDHITA_NO_FORMS@@%</strong> produced no form, and <strong>@@TADDHITA_ENCODING@@%</strong> failed the output transliteration check.</p><p class="caption" style="margin-top:14px">Each input already includes its source-listed gender. There is no case or number multiplier: the target is a derived stem or a complete indeclinable.</p></div><div class="panel"><h3>What counts as a nominal input?</h3><p style="margin-top:12px">Both nominal families use the same 74,673 resolved stem–gender pairs in <a href="../engine/files/shared-nominal-stems.json">shared-nominal-stems.json</a>. The dictionary normalization and VP representation filter have already been applied.</p><p>Each request preserves the stem, its basic/nyap interpretation, and its source gender. Gender can affect affix eligibility. It does not specify the gender of the resulting word.</p><p class="caption" style="margin-top:14px">MWlexnorm is the sole lexical source. Excluded raw headwords are not added back. Taddhitānta uses the documented VP compatibility patch for feminine inputs.</p></div></div>
<div class="grid grid-equal" style="margin-top:32px"><div><h3>How many tasks does one input yield?</h3><p class="caption" style="margin-top:8px">Number of nominal inputs, grouped by retained task count.</p><div class="histogram" role="img" aria-label="Retained tasks per nominal input range from 34 to 58. The most common count is @@MODE@@, produced by @@MODE_INPUTS@@ inputs. The exact data table follows."><div class="hist-axis"><span>@@HIST_PEAK@@</span><span>@@HIST_HALF@@</span><span>0</span></div><div class="hist-plot">@@HIST_BARS@@</div></div><p class="axis-label">Retained tasks per nominal input</p><p class="caption">Average: <strong>@@MEAN_PER_BASE@@ / 175 = @@TADDHITA_RETENTION@@%</strong> of attempts retained. Range: <strong>34–58 / 175 = @@RANGE_SHARE@@%</strong>. The most common count, <strong>@@MODE@@ / 175</strong>, represents <strong>@@MODE_SHARE@@%</strong> of an input’s attempted space.</p><details><summary>Exact tasks-per-input distribution</summary><div class="table-wrap"><table><thead><tr><th scope="col">Tasks / 175 attempts</th><th scope="col">Retained share of 175</th><th scope="col">Inputs</th></tr></thead><tbody>@@HIST_ROWS@@</tbody></table></div><p class="caption">Counts omitted from the table have zero inputs; the chart includes the full 34–58 range.</p></details></div><div class="panel"><h3>All suffixes attempted; coverage varies</h3><div class="factline" style="margin-top:13px"><span>Suffix choices attempted per input</span><strong>175</strong></div><div class="factline"><span>Suffixes with retained tasks somewhere</span><strong>@@NONEMPTY_SUFFIXES@@</strong></div><div class="factline"><span>Suffixes with no retained tasks</span><strong>21</strong></div><p class="caption" style="margin-top:13px">A suffix can yield tasks for almost every input or for just a few lexical entries. Zero output here describes this source inventory and engine configuration.</p><details><summary>The 21 suffixes with no retained tasks</summary><p>@@ZERO_SUFFIXES@@</p></details></div></div>
<details id="suffix-detail"><summary>Explore all 175 taddhita suffixes</summary><p class="caption">Every percentage in this table uses <strong>34,434,575 = 196,769 inputs × 175 suffixes</strong> as its denominator. Each suffix occupies <strong>1 / 175 = @@TADDHITA_SUFFIX_SHARE@@%</strong> of the whole attempted space. Its exported, no-form, and encoding-failure shares partition that amount. Sanskrit labels are technical suffix names, including markers.</p><div class="search"><label for="suffix-search">Find a suffix</label><input id="suffix-search" type="search" placeholder="e.g. matup or मतुप्" autocomplete="off" spellcheck="false" aria-describedby="search-note"><output id="suffix-count" aria-live="polite">175 suffixes</output></div><p class="caption" id="search-note">SLP1 IDs are case-sensitive. Search also accepts Devanagari.</p><div class="table-wrap"><table id="suffix-table"><thead><tr><th scope="col">Suffix ID</th><th scope="col">Technical name</th><th scope="col">Attempted share</th><th scope="col">Exported tasks</th><th scope="col">Exported share</th><th scope="col">No-form share</th><th scope="col">Encoding-failure share</th></tr></thead><tbody>@@SUFFIX_ROWS@@</tbody><tfoot><tr><th scope="row" colspan="2">All 175 suffixes</th><td>100.000000%</td><td data-count="exported-total">@@TADDHITA_EXPORT_COUNT@@</td><td>@@TADDHITA_EXPORT_SHARE@@%</td><td>@@TADDHITA_NO_FORMS@@%</td><td>@@TADDHITA_ENCODING@@%</td></tr></tfoot></table></div><p id="suffix-empty" class="caption" hidden>No suffixes match this search.</p></details>
</section>
<section class="section" aria-labelledby="answers-title"><h2 id="answers-title">One question can accept several forms</h2><p class="section-intro">The task count measures unique grammatical requests. The gold answer set can contain several accepted forms. Hydration uses the task's grammatical inputs; gold answers stay separate for scoring.</p><div class="table-wrap"><table><thead><tr><th scope="col">Family</th><th scope="col">One accepted form</th><th scope="col">Multiple accepted forms</th><th scope="col">Multiple forms / all family candidates</th></tr></thead><tbody>@@MULTIPLE_ROWS@@</tbody></table></div><p class="caption">The final column divides multiple-answer tasks by all candidate requests in that family, including excluded coordinates and attempts with no exported task. LLM performance requires a separate evaluation.</p></section>
<section class="section" id="sources" aria-labelledby="sources-title"><h2 id="sources-title">Source and scope notes</h2><p class="section-intro">Counts are read from the four saved dataset manifests. Attempted-space denominators include empty results and exclusions, within each family’s selected scope. Totals exclude the taddhitānta pilot and historical model traces. These inventories use VP 0.4.0; taddhitānta additionally uses the pinned nominal-input compatibility patch recorded in its manifest. They do not define a train/dev/test split.</p><ul class="sources">@@SOURCES@@</ul><p class="caption">Latest source-manifest modification: @@SNAPSHOT@@. This report is a static snapshot. Rebuild with <code>python3 data/engine/reports/distribution.py</code> after changing the datasets.</p><p class="caption" style="margin-top:10px">The report works offline. Source links resolve when it remains in <code>data/datasets/</code>.</p></section>
<section class="section" id="row-to-request" aria-labelledby="row-to-request-title">
<h2 id="row-to-request-title">From a dictionary row to actual requests</h2>
<p class="section-intro">One shared preparation step reads the MWlexnorm CSV, resolves the listed stems and genders, merges repeated pairs, and filters unsupported VP representations. Both task families then expand the same saved list.</p>
<figure class="request-flow" aria-label="Two paths from MWlexnorm CSV rows to subanta and taddhitānta requests">
<div class="flow-source">
<p class="flow-step">Shared source · one row per dictionary entry</p>
<h3><a href="../engine/files/mw-lexnorm/nominal-entries.csv">MWlexnorm nominal-entries.csv</a></h3>
<p class="caption">197,652 rows. Example: dictionary entry <code>mw_id = 65987</code>. The Sanskrit spellings use SLP1; capital <code>I</code> means long ī.</p>
<dl class="flow-fields">
<div><dt><code>headword</code></dt><dd><code>guru</code><p class="caption">The dictionary entry’s lookup spelling: गुरु.</p></dd></div>
<div><dt><code>compound_headword</code></dt><dd><code>guru</code><p class="caption">Spelling with any source-marked compound boundaries. Here it is unchanged; another row has <code>rAja-putra</code>.</p></dd></div>
<div><dt><code>lexnorm</code></dt><dd><code>m:f#vI:n</code><p class="caption">Masculine; feminine with a formation hint; neuter. The feminine hint gives <code>gurvI</code> (गुर्वी).</p></dd></div>
</dl>
</div>
<div class="flow-arrow" aria-hidden="true">↓<small>Resolve stems and genders · merge duplicates · filter VP representations</small></div>
<div class="flow-source"><h3><a href="../engine/files/shared-nominal-stems.json">shared-nominal-stems.json</a></h3>
<p><strong>74,673 stem–gender pairs.</strong> For this row: masculine <code>guru</code>, feminine <code>gurvI</code>, and neuter <code>guru</code>. Each saved pair keeps all contributing dictionary IDs.</p></div>
<div class="flow-lanes">
<div class="flow-lane" aria-labelledby="subanta-flow-title">
<div class="flow-arrow" aria-hidden="true">↓<small>Read the shared stem–gender list</small></div>
<div class="flow-node">
<p class="flow-step">Subanta · step 1</p><h3 id="subanta-flow-title">Use the resolved stem and gender</h3>
<ul><li><code>guru</code> + masculine + ordinary stem</li><li><code>gurvI</code> + feminine + feminine-suffix stem</li><li><code>guru</code> + neuter + ordinary stem</li></ul>
<p class="caption" style="margin-top:12px">The shared preparation step has already checked compound boundaries and grammatical hints. Unsupported entries are recorded in the shared source audit. Across the CSV, 55,230 rows contribute inputs.</p>
</div>
<div class="flow-arrow" aria-hidden="true">↓<small>Use the reviewed basic/nyap constructor</small></div>
<div class="flow-node">
<p class="flow-step">Subanta · step 2</p><h4>Create the VP stem and gender</h4>
<p>Choose the reviewed basic/nyap constructor for the resolved spelling and pass its listed gender to VP. Masculine and neuter <code>guru</code> stay separate because inflection depends on gender. The shared list has already merged repeated dictionary entries.</p>
<p class="flow-inventory"><strong>74,673 distinct inputs</strong> across the entire source → <a href="subanta/stems.json">stems.json</a>.</p>
</div>
<div class="flow-arrow" aria-hidden="true">↓<small>Expand each input into 24 choices</small></div>
<div class="flow-node">
<p class="flow-step">Subanta · step 3</p><h4>Stem + gender + case + number</h4>
<p><strong>8 cases × 3 numbers = 24 requests per input.</strong> This example row contributes 3 inputs × 24 = 72 requests, some shared with other dictionary rows.</p>
<p class="caption" style="margin-top:12px">One concrete VP request:</p>
<pre><code>Pada.Subanta(
    pratipadika=Pratipadika.basic("guru"),
    linga=Linga.Pum,           # masculine
    vibhakti=Vibhakti.Prathama, # nominative
    vacana=Vacana.Eka,         # singular
)</code></pre>
</div>
<div class="flow-arrow" aria-hidden="true">↓<small>Run the request through VP</small></div>
<div class="flow-node">
<p class="flow-step">Subanta · result</p><h4>An inflected word</h4>
<p class="flow-result"><code>guruH</code> · <span lang="sa">गुरुः</span></p>
<p>Store the request’s grammatical inputs and the accepted answer set as one task.</p>
<p class="flow-inventory"><strong>74,673 × 24 = 1,792,152 requests.</strong><br>All were retained in <a href="subanta/full.json">subanta/full.json</a>.</p>
</div>
</div>
<div class="flow-lane taddhita" aria-labelledby="taddhitanta-flow-title">
<div class="flow-arrow" aria-hidden="true">↓<small>Read the same shared stem–gender list</small></div>
<div class="flow-node">
<p class="flow-step">Taddhitānta · step 1</p><h3 id="taddhitanta-flow-title">Use the same three inputs</h3>
<ul><li>Masculine <code>guru</code></li><li>Feminine <code>gurvI</code></li><li>Neuter <code>guru</code></li></ul>
<p>The spelling and source gender are already resolved. No additional raw-headword list or gender merging is involved.</p>
</div>
<div class="flow-arrow" aria-hidden="true">↓<small>Preserve the full stem and source gender</small></div>
<div class="flow-node">
<p class="flow-step">Taddhitānta · step 2</p><h4>Prepare the nominal input for VP</h4>
<p>The compatibility adapter keeps the stem’s feminine tags and removes VP’s empty nyap marker before affix rules run. It supplies source gender without forcing the gender of the derived result.</p>
<p class="flow-inventory"><strong>196,769 inputs</strong>, one for every shared pair → <a href="taddhitanta/bases.json">bases.json</a>.</p>
</div>
<div class="flow-arrow" aria-hidden="true">↓<small>Try every one of the 175 suffixes</small></div>
<div class="flow-node">
<p class="flow-step">Taddhitānta · step 3</p><h4>Stem + source gender + affix</h4>
<p><strong>175 requests per input.</strong> Source gender is supplied by the shared input; there is no case or number choice. This dictionary row gives 3 inputs × 175 = 525 attempts. Meaning is unrestricted.</p>
<p class="caption" style="margin-top:12px">One request sent to the gender-aware VP bridge:</p>
<pre><code>{
  "stem": "guru",
  "is_nyap": false,
  "gender": "Pum",
  "suffix": "tva",
  "artha": null
}</code></pre>
</div>
<div class="flow-arrow" aria-hidden="true">↓<small>Run the request through VP</small></div>
<div class="flow-node">
<p class="flow-step">Taddhitānta · result</p><h4>A derived stem or complete indeclinable</h4>
<p class="flow-result"><code>gurutva</code> · <span lang="sa">गुरुत्व</span></p>
<p>Store usable, nonempty answer sets as tasks. Record empty results and encoding failures in the attempt audit.</p>
<p class="flow-inventory"><strong>196,769 × 175 = 34,434,575 requests.</strong><br><strong>8,731,509 tasks</strong> retained in <a href="taddhitanta/full.json">taddhitanta/full.json</a>.</p>
</div>
</div>
</div>
<figcaption class="caption flow-legend">“Ordinary stem” corresponds to VP’s <code>basic</code> constructor; “feminine-suffix stem” corresponds to <code>nyap</code>. Both pipelines preserve source gender and dictionary IDs. Subanta adds case and number; taddhitānta adds an affix. In the resulting task JSON, grammatical inputs hydrate the LLM prompt; accepted answers stay separate for scoring.</figcaption>
</figure>
</section>
</main><footer class="wrap footer">Sanskrit morphology inventories · Counts describe the current export scopes and engine outputs.</footer>
<script type="application/json" id="manifest-data">@@MANIFEST_DATA@@</script>
<script>
(() => {
  const input = document.getElementById('suffix-search');
  const rows = Array.from(document.querySelectorAll('#suffix-table tbody tr'));
  const count = document.getElementById('suffix-count');
  const empty = document.getElementById('suffix-empty');
  input.addEventListener('input', () => {
    const query = input.value.trim();
    let visible = 0;
    rows.forEach(row => {
      row.hidden = !(row.dataset.suffix.includes(query) || row.dataset.deva.includes(query));
      if (!row.hidden) visible += 1;
    });
    count.textContent = `${visible} of ${rows.length} suffixes`;
    empty.hidden = visible > 0;
  });
})();
</script>
</body>
</html>
'''


if __name__ == "__main__":
    build()
