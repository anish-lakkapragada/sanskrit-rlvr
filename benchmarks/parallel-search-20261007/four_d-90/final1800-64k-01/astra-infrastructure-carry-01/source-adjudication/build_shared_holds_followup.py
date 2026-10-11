"""Bounded source-only follow-up. Writes additive review artifacts only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
CARRY = HERE.parent
CANDIDATE = CARRY.parent.parent / "candidate-1800-v1"
CACHE = HERE / "shared-holds-sources"


def binding(p):
    return {"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


tasks = json.loads((CANDIDATE / "tasks.json").read_text())
prompts = {r["id"]: r["prompt"] for r in json.loads((CANDIDATE / "public-prompts.json").read_text())}
results = {provider: json.loads((CARRY / "results" / provider / "canonical.json").read_text()) for provider in ["Anthropic", "OpenAI"]}
inventory = json.loads((HERE / "lexical-holds-sources/ashta-dhatu-data.json").read_text())["data"]
rows = [
    {
        "index": 229,
        "disposition": "accepted",
        "input_status": "source_supported_input_with_multiple_commentary_traditions",
        "accepted_submitted_form": "असरन्",
        "canonical_key_action": "retain_existing_form_and_add_licensed_alternative_after_independent_adoption",
        "proposed_gold_union": ["असार्षुः", "असरन्"],
        "public_input_repair_required": False,
        "why_this_is_not_class_confusion": "Kshiratarangini explicitly places the ang example in its Bhvadigana sṛ entry, alongside sarati. Nyasa7.4.16 also identifies the Bhvadi dictionary entry935. This is positive class-specific evidence, not an inference from Kashika failing to name the class.",
        "positive_sources_for_submission": [
            {"file": "shared-holds-sources/kshira-204.jpg", "url": "https://jainqq.org/explore/002433/204", "printed_page": 147, "entry": "Bhvadi667", "kind": "visually_inspected_primary_scan", "passage": "सृ गतौ । सरति ... सर्तिशास्त्यर्तिभ्यश्च ... लुङि अङ्—असरत्", "implication": "Explicit Bhvadi3sg ang-aorist supplies the same stem and branch needed for the requested3pl."},
            {"file": "shared-holds-sources/7.4.16.html", "url": "https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.4.16.htm", "kind": "primary_commentary", "commentary": "Nyasa", "passage": "असरत् ... सृ गतौ ... ९३५", "implication": "The commentator links asarat to the same Bhvadi lexical entry; ṛ becomes ar before aṅ."},
            {"file": "shared-holds-sources/3.1.56.html", "url": "https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/3/3.1.56.htm", "kind": "primary_commentary", "commentary": "Kashika/Nyasa", "implication": "Explicit ang rule and asarat witness. The supplied ordinary gatau sense does not require the separate rapid-motion dhāv replacement."},
        ],
        "positive_sources_for_retained_key": [
            {"file": "shared-holds-sources/madhaviya-309.jpg", "printed_page": 255, "kind": "visually_inspected_primary_scan", "entry": "Bhvadi656", "passage": "असार्षीत् । असार्ष्टाम्", "implication": "Direct ordinary Bhvadi sigmatic-aorist witnesses."},
            {"file": "shared-holds-sources/madhaviya-310.jpg", "printed_page": 256, "kind": "visually_inspected_primary_scan", "implication": "Continuation restricts3.1.56 to the Juhotyadi pair through association with śās, so denies aṅ here."},
            {"file": "lexical-holds-sources/sk-primary-text.json", "keys": ["72011", "31056"], "kind": "primary_commentary_transcription", "implication": "SK likewise gives asArzIt/asArzwAm for Bhvadi935 and expressly restricts aṅ to Juhotyadi."},
            {"file": "shared-holds-sources/3.4.109.html", "kind": "primary_rule_and_commentary", "implication": "Sigmatic third plural uses jus; printed akāṛṣuḥ-type examples supply the exact productive ending pattern."},
        ],
        "complete_submitted_derivation": [
            "Lun supplies cli (3.1.43); the Kshira/Kashika-Nyasa interpretation of3.1.56 substitutes aṅ after the ordinary Bhvadi sṛ.",
            "Lun supplies initial aṭ (6.4.71). Rule7.4.16 gives ṛ->ar before aṅ, including r by the usual ṛ/ar interpretation, so a+sṛ+a becomes asara-.",
            "Prathama/Bahu P uses jhi (3.4.78), jh->ant (7.1.3), and final i is deleted in the Ṅit lakara (3.4.100). The thematic a and ending a coalesce by6.1.97; final nt loses t by8.2.23. Result: asaran, असरन्.",
            "There is no sic on this branch, so the sic-conditioned jus rule3.4.109 does not replace this ending.",
        ],
        "complete_retained_key_derivation": [
            "On the Madhaviya/SK reading,3.1.56 is restricted to Juhotyadi and ordinary Bhvadi sṛ takes sic by3.1.44 after Lun cli.",
            "The source anudatta root is aniṭ under7.2.10. ṛ receives vṛddhi before sic/P under7.2.1: sṛ->sār. Prathama/Bahu jhi becomes jus after sic under3.4.109.",
            "With initial aṭ, a+sār+s+us becomes asārṣus by8.3.59 and word-final s becomes visarga through8.2.66/8.3.15: असार्षुः.",
        ],
        "all_input_scope": "The rule concerns ordinary Bhvadi sṛ/Lun, not only this observed answer. This cohort has exactly one such root-family task, index229. Other person/number cells of this branch need the same prospective tradition policy and complete ending derivations; this memo does not create blanket string aliases.",
        "school_policy": "The public prompt names no commentary school. It is indefensible to reject the explicit ordinary Bhvadi Kshira/Nyasa branch solely because the oracle follows the narrower SK/Madhaviya interpretation. Both complete licensed forms should be accepted symmetrically.",
    },
    {
        "index": 437,
        "disposition": "accepted",
        "disposition_scope": "Source-licensed response to the identified ordinary yawning lexeme; historical citation is incomplete/inconsistent and must not be certified as a clean item.",
        "input_status": "missing_source_required_anudatta_it_and_incomplete_nasal_branch",
        "accepted_submitted_form": "जम्भते",
        "canonical_key_action": "revoke_unsupported_P_key_on_source_corrected_version",
        "unsupported_canonical_form": "जभति",
        "public_input_repair_required": True,
        "P_plus_A_union_supported": False,
        "prospective_repair": {"aupadeshika_slp1": "jaBa~\\", "visible_citation": "जभँ॒", "preserve_class_meaning_and_four_coordinates": True, "source_supported_middle_forms": ["जम्भते", "जभते"], "status": "Proposed only, pending independent adoption; no historical prompt or key changed."},
        "positive_sources_for_submission": [
            {"file": "shared-holds-sources/dhatupradipa-44.jpg", "url": "https://jainqq.org/explore/004319/44", "printed_page": 34, "kind": "visually_inspected_primary_scan", "passage": "जभ जृभि गात्रविनामे ... जम्भते", "implication": "A direct unprefixed ordinary present witness under the jabh heading; the section closes as middle, udatta roots with anudatta it-markers."},
            {"file": "shared-holds-sources/daivam-purusakara.html", "url": "https://sa.wikisource.org/wiki/दैवम्_(पुरुषकारव्याख्यासमेतम्)", "kind": "primary_work_transcription", "locus": "verse145 and commentary", "passage": "जृम्भणे जम्भते ... जभ जृभि गात्रविनामे ... रधिजभोरचि", "implication": "Explicitly connects the a-reading jabh, the ordinary yawning sense, nasal present, and7.1.61. No causative or prefix is needed."},
            {"file": "shared-holds-sources/7.1.61.html", "url": "https://sanskritdocuments.org/learning_tools/ashtadhyayi/vyakhya/7/7.1.61.htm", "kind": "primary_commentary", "commentary": "Balamanorama", "passage": "जम्भत इति। शपि नुम्", "implication": "The nasal follows num before the vowel-initial śap, despite the root not being idit. The ending group is explicitly anudatta-it."},
            {"file": "shared-holds-sources/kshira-368.jpg", "url": "https://jainqq.org/explore/002433/368", "printed_page": 311, "kind": "visually_inspected_primary_scan", "implication": "While discussing a separate Curadi entry, the author expressly refers back to ordinary Bhvadi jabh/jabhi and prints jambhate. This is not an inference that the Curadi causative itself answers the task."},
        ],
        "positive_sources_for_nonnasal_middle_alternative": [
            {"file": "shared-holds-sources/kshira-122.jpg", "url": "https://jainqq.org/explore/002433/122", "printed_page": 65, "kind": "visually_inspected_primary_scan", "entry": "Bhvadi273", "passage": "जभ जृभि गात्रविनामे । जभते, जृम्भते", "implication": "The inspected edition directly prints the nonnasal middle present under the a-reading. This is a textual witness; it is not a claim that Balamanorama makes its num rule optional."},
        ],
        "complete_submitted_derivation": [
            "Identify the ordinary jabh/yawning entry as anudatta-it using the printed lexical section;1.3.12 fixes intrinsic middle endings. This lexical accent is absent from historical jaBa~ but would be visible as जभँ॒.",
            "Lat/Kartari/Bhvadi supplies śap (3.1.68). Before this vowel-initial suffix,7.1.61 supplies num to jabh; the placement before the final consonant yields janbh, then8.3.24 and8.4.58 give jambh.",
            "Prathama/Eka middle uses ta (3.4.78), with final e for Tit Lat under3.4.79: jambh+a+te -> jambhate, जम्भते.",
            "No rule or printed witness used here requires an added prefix, sanadi operation, or different meaning.",
        ],
        "nonnasal_limit": "Kshira's printed jabhate is an explicit contrasting source witness, while Balamanorama requires num on its branch. The inspected Kshira page does not explain its nonnasal finite stem and also cites num for nominal derivatives. Preserve that attribution and obtain independent confirmation before adopting the two-middle-form union. Do not describe it as arbitrary optional nasal insertion.",
        "engine_limit": "The parent independently regenerated the accent-only repair jaBa~\\ and obtained jabhate only. That does not invalidate the printed jambhate witnesses; an accent repair alone leaves the oracle's accepted union incomplete. This memo did not modify or rerun the oracle.",
        "all_input_scope": "All ordinary jaBa~/Bhvadi/gAtravinAme entries need lexical-accent and num-scope review, including currently correct outputs. Exactly one such task occurs in this1800; both models returned jambhate, so neither model has an already-credited P response on this specific row. Nonetheless the P key itself is unsupported and cannot be retained merely for monotonic grade adjustment.",
        "historical_policy": "Preserve the original public prompt and raw grades; annotate the input defect and source-licensed responses separately. Repaired citations and keys belong to a new benchmark version; old responses were not elicited from the repaired prompt.",
    },
    {
        "index": 566,
        "disposition": "unresolved",
        "input_status": "exact_zalf_citation_unverified_after_additional_primary_editions",
        "canonical_key_action": "retain_source_identity_hold_without_regrading",
        "new_evidence": [
            {"file": "shared-holds-sources/madhaviya-204.jpg", "printed_page": 150, "kind": "visually_inspected_primary_scan", "loci": [353, 357], "implication": "The first locus discusses shel/sel with e, including dental versus retroflex variants; the second separately prints ṣal with ordinary a-it. Neither establishes exact short-a ṣalṛ."},
            {"file": "shared-holds-sources/dhatupradipa-52.jpg", "url": "https://jainqq.org/explore/004319/52", "printed_page": 42, "kind": "visually_inspected_primary_scan", "implication": "Separate pel/fel/shel roots and sal gatau again fail to establish the claimed ṣalṛ spelling."},
        ],
        "scope_limit": "Two additional primary works strengthen the need for a citation hold but do not prove universal nonexistence. No licensed derivation for submitted asalatAm was discovered; the prior distinction between r-it and l-it remains. Do not reclassify an input-identity problem as a certified model error.",
    },
]

for r in rows:
    i = r["index"]
    t = tasks[i]
    assert all(results[p][i]["task_id"] == t["id"] for p in results)
    r.update(task_id=t["id"], dhatu=t["dhatu"], morphology=t["morphology"], historical_gold=t["gold_devanagari"], public_prompt=prompts[t["id"]])
    r["paired_observations"] = {p: {"answer": results[p][i]["answer"], "historical_is_correct": results[p][i]["is_correct"]} for p in results}
    r["all_current_cohort_same_family"] = [{"index": j, "task_id": q["id"]} for j, q in enumerate(tasks) if q["campaign"]["root_family"] == t["campaign"]["root_family"]]
    r["inventory_entry_editorial_not_primary_proof"] = [d for d in inventory if d["baseindex"] == t["dhatu"]["code"]]

plan = json.loads((CARRY.parent / "execution-plan.json").read_text())
deps = plan["dependencies"]
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in deps.items())
out = {
    "schema": "vp-shared-holds-source-followup-v1",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "requested_window_start": "2026-10-08T02:53:40Z",
    "scope": "Independent primary-source resolution of shared sṛ/jabh holds, with bounded additional ṣalṛ search. Historical outcomes preserved.",
    "counts": {"accepted_on_clean_existing_input": 1, "accepted_source_form_with_input_repair_required": 1, "unresolved_input_identity": 1},
    "rows": rows,
    "requires_independent_adoption_before_scoring": True,
    "all_input_scope_not_outcome_selected": "Every current task in each affected lexical family is listed, including paired canonical successes. No tasks are dropped and no observed form is accepted merely because a model produced it.",
    "source_limits": ["Printed finite witnesses plus productive primary ending rules support sṛ's complete3pl forms. The two sṛ traditions disagree in scope, and the public prompt chooses neither.", "The exact nasal middle jabh present is directly and independently witnessed. Kshira's nonnasal middle is a contrasting printed reading whose full underlying rationale is not established here.", "Source-licensed responses to an inconsistent citation do not make the historical input a clean benchmark question.", "The extra ṣalṛ search is bounded to the named editions; no universal nonexistence claim.", "No full755-family or full-paradigm certification."],
    "inputs": [binding(HERE / "Anthropic-review.json"), binding(HERE / "OpenAI-broad-review.json"), binding(HERE / "lexical-holds-followup.json"), binding(CANDIDATE / "tasks.json"), binding(CANDIDATE / "public-prompts.json"), *[binding(CARRY / "results" / p / "canonical.json") for p in results], binding(HERE / "lexical-holds-sources/sk-primary-text.json"), binding(HERE / "lexical-holds-sources/ashta-dhatu-data.json")],
    "new_source_snapshots": [binding(p) for p in sorted(CACHE.iterdir()) if p.is_file()],
    "frozen_dependency_count_verified": len(deps), "historical_mutations": 0, "provider_calls": 0, "ledger_changes": 0,
}
(HERE / "shared-holds-followup.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"counts": out["counts"], "artifact": binding(HERE / "shared-holds-followup.json"), "frozen_dependencies_verified": len(deps)}, ensure_ascii=False))
