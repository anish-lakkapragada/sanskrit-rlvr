"""Build the correction browser and attach its route to the benchmark report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from benchmarks.correction import core
from finetune.prompts import GANA_EN, LAKARA_EN, PURUSHA_EN, VACANA_EN

START = "<!-- BEGIN VP CORRECTION ROUTE -->"
END = "<!-- END VP CORRECTION ROUTE -->"


def attach_route(html):
    if START in html:
        before, remainder = html.split(START, 1)
        _, after = remainder.split(END, 1)
        html = before.rstrip() + '\n' + after.lstrip()
    if 'href="#/correction"' not in html:
        html = html.replace('</nav>', '<a href="#/correction">Correction</a></nav>', 1)
    fragment = (core.DIRECTORY / "route.html").read_text()
    return html.replace('</body>', START + '\n' + fragment + '\n' + END + '\n</body>', 1)


def build(directory=core.DIRECTORY, attach=True):
    tasks = json.loads((directory / "tasks.json").read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    verification = json.loads((directory / "verification.json").read_text())
    if verification["status"] != "passed" or verification["tasks_sha256"] != core.file_sha(directory / "tasks.json"):
        raise ValueError("Verify the current task file before rendering")
    payload = {
        "tasks": [{**task, "root_devanagari": core.devanagari(task["dhatu"]["aupadeshika"])} for task in tasks],
        "manifest": manifest, "verification": verification,
        "labels": {"gana": GANA_EN, "lakara": LAKARA_EN, "purusha": PURUSHA_EN, "vacana": VACANA_EN},
    }
    evaluation_path = directory / "opus-50-20261009/analysis.json"
    if evaluation_path.exists():
        evaluation = json.loads(evaluation_path.read_text())
        if evaluation["full_dataset_sha256"] != core.file_sha(directory / "tasks.json"):
            raise ValueError("Evaluation belongs to a different correction dataset")
        payload["evaluation"] = evaluation
    safe = core.canonical_json(payload).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (core.DIRECTORY / "view.template.html").read_text()
    assert template.count("__CORRECTION_DATA__") == 1
    (directory / "index.html").write_text(template.replace("__CORRECTION_DATA__", safe))
    if attach:
        for path in [ROOT / "misc/benchmark_report.template.html", ROOT / "benchmarks/report.html"]:
            original = path.read_text()
            updated = attach_route(original)
            if updated != original:
                path.write_text(updated)
    return {"page": str(directory / "index.html"), "report_route": "report.html#/correction", "http_route": "/correction/"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=core.DIRECTORY)
    parser.add_argument("--no-attach", action="store_true")
    arguments = parser.parse_args()
    print(json.dumps(build(arguments.directory, not arguments.no_attach), indent=2))
