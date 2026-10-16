#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4==4.14.3", "vidyut==0.4.0"]
# ///
"""Check current samples, HTML, and token estimates against the full exports."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.reports.refresh_samples import FAMILIES, SAMPLES
from data.engine.subanta.common import sha256


def verify():
    data = ROOT / "data/datasets"
    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    page = BeautifulSoup((SAMPLES / "samples.html").read_text(), "html.parser")
    distribution = BeautifulSoup((data / "distribution.html").read_text(), "html.parser")
    embedded = json.loads(distribution.select_one("#manifest-data").string)
    costs = json.loads((data / "token-costs.json").read_text())
    assert len(page.select("article")) == 20
    assert not page.select("style, [style]")
    checked = {}
    for family, (_, common) in FAMILIES.items():
        metadata = json.loads((data / family / "manifest.json").read_text())
        samples = manifest["datasets"][family]
        total = metadata["counts"]["full"]
        expected_hash = metadata["files"]["full.json"]["sha256"]
        assert samples["source_records"] == total
        assert samples["source_sha256"] == expected_hash
        assert samples["template_sha256"] == sha256(common.TEMPLATE)
        if "engine" in samples:
            assert samples["engine"] == metadata["engine"]
        assert len(samples["samples"]) == len({s["record_index"] for s in samples["samples"]}) == 5
        targets = {s["record_index"]: s for s in samples["samples"]}
        digest = hashlib.sha256()
        found = count = 0
        with (data / family / "full.json").open("rb") as handle:
            opening = next(handle)
            assert opening == b"[\n"
            digest.update(opening)
            for line in handle:
                digest.update(line)
                if line.strip() == b"]":
                    assert not handle.read()
                    break
                if count in targets:
                    sample = targets[count]
                    row = json.loads(line.strip().removesuffix(b","))
                    assert row["id"] == sample["task_id"]
                    assert sample["inputs"] == {k: row[k] for k in sample["inputs"]}
                    assert not sample.get("warnings") and not row.get("warnings")
                    prompt = (SAMPLES / sample["path"]).read_text()
                    answer = (SAMPLES / sample["answer_path"]).read_text()
                    assert common.render_task(row) == prompt
                    assert sha256(SAMPLES / sample["path"]) == sample["prompt_sha256"]
                    assert sha256(SAMPLES / sample["answer_path"]) == sample["answer_sha256"]
                    assert json.loads(answer) == {k: row[k] for k in ("id", "gold_slp1", "gold_devanagari")}
                    number = Path(sample["path"]).parent.name
                    article = page.select_one(f"#{family}-{number}")
                    assert article.select_one('pre[data-kind="prompt"]').get_text() == "```text\n" + prompt.rstrip() + "\n```"
                    assert article.select_one('pre[data-kind="answers"]').get_text() == answer.rstrip()
                    assert article.select_one("[data-copy-prompt]")
                    assert len(article.select("nav a")) == 6
                    found += 1
                count += 1
            else:
                raise AssertionError("Missing closing array bracket")
        assert count == total and found == 5
        assert digest.hexdigest() == expected_hash
        assert embedded[family] == {"counts": metadata["counts"], "full_json": metadata["files"]["full.json"]}
        assert distribution.select_one(f"#{family} .family-count").get_text() == f"{total:,} tasks"
        assert costs["datasets"][family]["source_sha256"] == expected_hash
        assert costs["datasets"][family]["template_sha256"] == sha256(common.TEMPLATE)
        assert costs["datasets"][family]["records"] == total
        checked[family] = {"records": total, "manifest_sha256": sha256(data / family / "manifest.json"),
                           "full_sha256": expected_hash, "samples_checked": found}
        print(f"{family}: samples, HTML, counts, and source/template hashes match", flush=True)

    for html in (page, distribution):
        ids = [x["id"] for x in html.select("[id]")]
        assert len(ids) == len(set(ids))
        for link in html.select('a[href^="#"]'):
            assert link["href"][1:] in ids, link
        scripts = "\n".join(s.get_text() for s in html.select("script") if s.get("type") != "application/json")
        subprocess.run(["node", "--check"], input=scripts, text=True, check=True, capture_output=True)
    cells = distribution.select("#subanta-cells tbody td")
    assert len(cells) == 24 and all(float(c["data-share"]) == 100 / 24 for c in cells)
    suffix_rows = distribution.select("#suffix-table tbody tr")
    assert len(suffix_rows) == 175
    assert sum(int(r.select_one('[data-count="exported"]').get_text().replace(",", ""))
               for r in suffix_rows) == checked["taddhitanta"]["records"]
    for row in distribution.select("#generation tbody tr"):
        cells = row.select("td")
        assert len(cells) == 7
        assert abs(sum(float(c.get_text().rstrip("%")) for c in cells[1:]) - 100) < 0.00001
    assert "Excluded from the export:" in distribution.select_one("#tinanta").get_text()
    assert "Included in the total:" not in distribution.get_text()
    assert "@@" not in (data / "distribution.html").read_text()
    total = sum(c["records"] for c in checked.values())
    assert f"{total:,}" in distribution.select_one("#overview").get_text()
    return {"passed": True, "datasets": checked, "total_tasks": total,
            "checks": ["20 actual sampled records", "complete answer sets", "prompt hydration", "HTML text",
                       "navigation targets", "JavaScript syntax", "24 subanta cells", "175 suffix rows",
                       "outcome percentages", "manifest counts", "source and template hashes", "token estimates"]}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
