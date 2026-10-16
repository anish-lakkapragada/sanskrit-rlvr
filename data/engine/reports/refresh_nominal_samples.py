#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["vidyut==0.4.0"]
# ///
"""Refresh five subanta/taddhitanta samples and their existing HTML viewer."""

from datetime import datetime, timezone
from html import escape
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from data.engine.subanta import common as subanta
from data.engine.taddhitanta import common as taddhitanta

SAMPLES = ROOT / "data/engine/prompts/v2/samples"
FAMILIES = {"subanta": ("Subanta", subanta), "taddhitanta": ("Taddhitānta", taddhitanta)}


def highlight_json(text):
    result, end = [], 0
    for match in re.finditer(r'"(?:[^"\\]|\\.)*"|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?', text):
        result.append(escape(text[end:match.start()]))
        color = "#0000aa" if text[match.end():].lstrip().startswith(":") else "#006400"
        result.append(f'<font color="{color}">{escape(match.group())}</font>')
        end = match.end()
    return "".join(result) + escape(text[end:])


def article(family, label, number, task_id, prompt, answer):
    navigation = " | ".join(
        f'<a href="#{family}-{i:02d}"' + (' aria-current="location"' if i == number else '') + '>'
        + (f'<strong>{i}</strong>' if i == number else str(i)) + '</a>' for i in range(1, 6))
    return f'''<article id="{family}-{number:02d}">
<h3>Sample {number}</h3>
<nav aria-label="{label} sample navigation"><p>Samples: {navigation} · <a href="#sample-index">All categories</a></p></nav>
<p><button type="button" data-copy-prompt>Copy prompt</button> <span data-copy-status role="status" aria-live="polite"></span></p>
<p>Task ID: <code>{escape(task_id)}</code></p>
<table border="1" cellpadding="8" aria-label="{label} sample {number}: prompt and accepted answers">
<thead><tr>
<th scope="col"><a href="{family}/{number:02d}/prompt.txt">prompt.txt</a></th>
<th scope="col"><a href="{family}/{number:02d}/answer.json">answer.json</a></th>
</tr></thead><tbody><tr>
<td valign="top"><pre data-kind="prompt"><code>```text
{escape(prompt.rstrip())}
```</code></pre></td>
<td valign="top"><pre data-kind="answers"><code>{highlight_json(answer.rstrip())}</code></pre></td>
</tr></tbody></table>
</article>'''


def refresh():
    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    page = (SAMPLES / "samples.html").read_text()
    files = {}
    for old in manifest["datasets"].values():
        old.setdefault("sampling", manifest["sampling"])
    for family, (label, common) in FAMILIES.items():
        dataset = ROOT / "data/datasets" / family
        metadata = json.loads((dataset / "manifest.json").read_text())
        subanta.require(metadata["schema_version"] == 2 and metadata["generation_complete"], "Expected completed shared-input export")
        source = dataset / "full.json"
        digest = subanta.sha256(source)
        subanta.require(digest == metadata["files"]["full.json"]["sha256"], "Dataset hash changed")
        total = metadata["counts"]["full"]
        seed = f"{manifest['seed']}:{family}:{digest}"
        indices = random.Random(seed).sample(range(total), 5)
        targets = set(indices)
        rows = {}
        observed = 0
        for index, row in enumerate(subanta.iter_array(source)):
            if index in targets:
                rows[index] = row
            observed += 1
        subanta.require(observed == total and len(rows) == 5, "Incomplete sample source")
        samples = []
        for number, index in enumerate(indices, 1):
            row = rows[index]
            prompt = common.render_task(row)
            answer = json.dumps({k: row[k] for k in ("id", "gold_slp1", "gold_devanagari")},
                                ensure_ascii=False, indent=2) + "\n"
            prefix = f"{family}/{number:02d}"
            files[f"{prefix}/prompt.txt"] = prompt
            files[f"{prefix}/answer.json"] = answer
            samples.append({"path": f"{prefix}/prompt.txt", "record_index": index, "task_id": row["id"],
                            "inputs": {k: row[k] for k in ("pratipadika", "morphology")}, "warnings": [],
                            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                            "answer_path": f"{prefix}/answer.json", "answer_sha256": hashlib.sha256(answer.encode()).hexdigest()})
            pattern = rf'<article id="{family}-{number:02d}">.*?</article>'
            page, replaced = re.subn(pattern, lambda _: article(family, label, number, row["id"], prompt, answer), page, flags=re.S)
            subanta.require(replaced == 1, f"Missing/duplicate sample article: {prefix}")
        manifest["datasets"][family] = {
            "source": source.relative_to(ROOT).as_posix(), "source_sha256": digest, "source_records": total,
            "template": common.TEMPLATE.relative_to(ROOT).as_posix(), "template_sha256": subanta.sha256(common.TEMPLATE),
            "engine": metadata["engine"], "sampling": "Uniform random.sample of five distinct record indices; no filtering or retries",
            "sampling_seed": seed, "samples": samples,
        }
        print(f"Refreshed {family}: five samples from {total:,} tasks", flush=True)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest["sampling"] = "Five distinct record indices per family; each dataset records its sampling method. Unchanged families retain their previous selections."
    files["samples.html"] = page
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    with tempfile.TemporaryDirectory(prefix=".sample-refresh-", dir=SAMPLES.parent) as temp:
        for name, text in files.items():
            path = Path(temp) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        for name in files:
            (Path(temp) / name).replace(SAMPLES / name)


if __name__ == "__main__":
    refresh()
