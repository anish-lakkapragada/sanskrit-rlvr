"""Additive, offline source adjudication; never mutate historical keys or scores."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
CARRY = HERE.parent
CANDIDATE = CARRY.parent.parent / "candidate-1800-v1"
SOURCES = HERE / "lexical-holds-sources"


def binding(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


tasks = json.loads((CANDIDATE / "tasks.json").read_text())
prompts = {x["id"]: x["prompt"] for x in json.loads((CANDIDATE / "public-prompts.json").read_text())}
results = {p: json.loads((CARRY / "results" / p / "canonical.json").read_text()) for p in ("Anthropic", "OpenAI")}
prior = json.loads((HERE / "Anthropic-review.json").read_text())
inventory = json.loads((SOURCES / "ashta-dhatu-data.json").read_text())["data"]

cases = [
    {
        "index": 481, "disposition": "accepted", "disposition_scope": "Source-licensed answer for the identified ordinary lexeme; not a declaration that the historical public input is sound.",
        "input_status": "source_inconsistent_citation_requires_repair",
        "source_licensed_answer": "अरेबामहि", "canonical_key_action": "revoke_on_source_corrected_version",
        "unsupported_canonical_answer": "अरेबाम", "union_of_old_and_new_gold_defensible": False,
        "evidence": [
            {"source": "dhatupradipa-43.jpg", "printed_page": 33, "kind": "visually_read_primary", "passage": "रेबते", "explanation": "The b-final rebu/pl ebu entries have middle present forms; the typography of the heading is corroborated by the explicit b/v contrast on printed40."},
            {"source": "dhatupradipa-50.jpg", "printed_page": 40, "kind": "visually_read_primary", "passage": "पूर्वको रेबप्लेबौ पवर्गे पठितौ स्पर्शान्तौ", "explanation": "The commentator distinguishes earlier stop-final reb/pleb from approximant-final rev/plev and closes this section as atmanebhasa, udatta roots with anudatta it-markers."},
            {"source": "1.3.12.html", "kind": "primary_rule", "explanation": "Anudatta-it licenses the middle endings. No extra sanadi, prefix or semantic operation is needed."},
        ],
        "derivation": "The lexical source fixes the ordinary middle branch. Lan supplies aT (6.4.71); ordinary Bhvadi Kartari supplies SaP (3.1.68); Uttama/Bahu selects mahiN (3.4.78, with its marker removed), and a before m lengthens (7.3.101): a + reb + a + mahi -> arebAmahi. Lan is not Tit, so the Tit-only e replacement of 3.4.79 does not apply.",
        "repair_proposal": {"aupadeshika_slp1": "rebf~\\", "visible_citation": "रेबृँ॒", "same_other_fields": True, "canonical_gold_devanagari": ["अरेबामहि"], "status": "Proposal only; independent review and a new task/version are required."},
        "whole_input_scope": "All ordinary rebf~/plavagatO questions need citation and intrinsic-pada review, including previously scored successes. The current1800 contains one such question. The sources do not license retaining P solely because VP generated it from the damaged citation.",
    },
    {
        "index": 495, "disposition": "accepted", "disposition_scope": "Source-licensed answer for the identified ordinary lexeme; historical citation has a missing required accent.",
        "input_status": "source_inconsistent_citation_requires_repair",
        "source_licensed_answer": "खुण्डिताध्वे", "canonical_key_action": "revoke_on_source_corrected_version",
        "unsupported_canonical_answer": "खुण्डितास्थ", "union_of_old_and_new_gold_defensible": False,
        "evidence": [
            {"source": "kshira-110.jpg", "printed_page": 53, "kind": "visually_read_primary", "passage": "खुडि गतिवैकल्ये । खुण्डते", "explanation": "Kshiratarangini1.188 explicitly gives the exact meaning and middle form, distinguishes Curadi khud/breaking, and closes the group as udatta/anudatta-it."},
            {"source": "1.3.12.html", "kind": "primary_rule", "explanation": "The source's anudatta-it classification licenses intrinsic middle endings."},
            {"source": "sk-primary-text.json", "key": "82025", "kind": "primary_commentary_transcription", "passage": "धादौ प्रत्यये परे सलोपः स्यात् । एधिताध्वे", "explanation": "SK explicitly demonstrates the same Lut middle2pl ending; this is a complete productive derivation, not a demand for a separately printed khund paradigm."},
        ],
        "derivation": "The idit lexical entry gives khund by num (7.1.58). Lut supplies tAs (3.1.33), with it before this valadi ardhadhatuka affix (7.2.35). Middle Madhyama/Bahu uses dhvam (3.4.78), whose ti portion becomes e in Tit Lut (3.4.79): dhve. SK's 8.2.25 treatment, explicitly exemplified by edhitAdhve, removes s before dh: khund+i+tAs+dhve -> khunditAdhve. No Curadi or causative branch is invoked.",
        "repair_proposal": {"aupadeshika_slp1": "Kuqi~\\", "visible_citation": "खुडिँ॒", "same_other_fields": True, "canonical_gold_devanagari": ["खुण्डिताध्वे"], "status": "Proposal only; independent review and a new task/version are required."},
        "whole_input_scope": "All ordinary Kuqi~/gativEkalye questions need citation and intrinsic-pada review, including successes. The current1800 contains one such question. A P+A union is not supported by the exact inspected lexical source; the distinct Curadi breaking entry cannot supply a missing P branch here.",
    },
    {
        "index": 566, "disposition": "unresolved", "disposition_scope": "Do not certify a scored error while the exact supplied lexical reading remains unverified.",
        "input_status": "exact_dictionary_reading_unverified", "canonical_key_action": "hold_pending_source_identity_resolution",
        "union_of_old_and_new_gold_defensible": False,
        "evidence": [
            {"source": "kshira-141.jpg", "printed_page": 84, "kind": "visually_read_primary", "passage": "पेलृ फेलृ शेलृ गतौ", "explanation": "The cited alternate-reading locus prints shelf, with footnote7 self; it does not establish the supplied zalf (short a)."},
            {"source": "kshira-142.jpg", "printed_page": 85, "kind": "visually_read_primary", "passage": "सल गतौ । सलति", "explanation": "A separate sal entry is present; this does not itself establish the benchmark's final-r marker or its mapping to the shel/sel alternate."},
            {"source": "dhatupatha-svara.html", "kind": "primary_text_edition", "explanation": "The inspected accentuated text similarly distinguishes shel/sel at1.623/624 from zala at1.628. Its numbering is an edition's numbering, not the repo's synthetic1.0253."},
            {"source": "3.1.55.html", "kind": "primary_rule", "explanation": "The aN aorist class condition is puSadi/dyutadi or vocalic-l marker, not a generic vocalic-r marker. Thus asalatAm has not been licensed by confusing r-it with l-it."},
        ],
        "derivation": "No complete source-supported derivation for submitted asalatAm was found. It resembles the imperfect or an unlicensed aN aorist. This is insufficient to clear the question itself: the claimed Kshira cross-reference does not match the visible citation in the inspected edition. The canonical asAlizwAm remains only conditionally grammatical for a hypothetical ordinary set sal branch, not a newly certified answer to this exact dictionary citation.",
        "repair_proposal": {"status": "Retain the input hold. A future version should use a independently verified sal or shel/sel entry and regenerate/review its key; do not silently change short a to e or substitute a different marker in the historical task."},
        "whole_input_scope": "The same zalf~|Bhvadi identity also occurs as repo01.0759 outside this selected cohort. Any such inventory entries require the same source-identity hold. Only01.0253 appears in this1800 panel.",
    },
    {
        "index": 1186, "disposition": "rejected", "disposition_scope": "The literal citation selects an independently attested P variant; the middle homograph has an additional accent in its citation.",
        "input_status": "source_supported_distinct_citation", "canonical_key_action": "retain",
        "evidence": [
            {"source": "sk-primary-text.json", "key": "72005", "kind": "primary_commentary_transcription", "passage": "कड मदे । कडति । कडि इत्येके । कण्डति", "explanation": "The P kadi variant is explicitly attested, rather than merely inferred from absent engine accents."},
            {"source": "madhaviya170.jpg", "printed_page": 116, "kind": "visually_read_primary", "explanation": "The kada discussion gives kadati, records Kshirasvamin's kadi reading, and explicitly distinguishes the previously treated kandate."},
            {"source": "madhaviya160.jpg", "printed_page": 106, "kind": "visually_read_primary", "passage": "कडि मदे । कण्डते", "explanation": "The separate earlier middle entry is confirmed. Its existence does not erase the distinct P reading."},
            {"source": "dhatupatha-svara.html", "kind": "primary_text_edition", "explanation": "This text distinguishes1.316 kadi with anudatta from1.418 kadi under the udatta-it/P group. The actual benchmark renderer preserves that distinction."},
        ],
        "derivation": "For the supplied kadi without anudatta, the attested P variant gives kand (7.1.58), future i+sya (3.1.33,7.2.35), and mi (3.4.78), with a lengthening before m (7.3.101): kaRqizyAmi. Submitted kaRqizye selects the ending of the separate middle citation kaqi~\\, which the public prompt did not supply.",
        "repair_proposal": {"status": "No gold change warranted. For future clarity the general prompt may explicitly say that displayed accent/it markers identify the lexical entry; that is documentation, not a fifth task coordinate."},
        "whole_input_scope": "Do not conflate repo01.0418 kaqi~ with01.0316 kaqi~\\. Both have class1 and meaning made, but the citation itself differs visibly (कडिँ versus कडिँ॒). Only01.0418 occurs here.",
    },
]

for case in cases:
    i = case["index"]
    t = tasks[i]
    assert results["Anthropic"][i]["task_id"] == t["id"] == results["OpenAI"][i]["task_id"]
    case.update(task_id=t["id"], dhatu=t["dhatu"], morphology=t["morphology"], historical_gold=t["gold_devanagari"], public_prompt=prompts[t["id"]])
    case["paired_observations"] = {p: {"answer": results[p][i]["answer"], "historical_is_correct": results[p][i]["is_correct"]} for p in results}
    case["all_current_cohort_same_code_task_ids"] = [q["id"] for q in tasks if q["dhatu"]["code"] == t["dhatu"]["code"]]
    case["editorial_inventory_corrobation_not_primary_proof"] = [e for e in inventory if e["baseindex"] == t["dhatu"]["code"]]

plan = json.loads((CARRY.parent / "execution-plan.json").read_text())
dependencies = plan["dependencies"]
if isinstance(dependencies, dict):
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in dependencies.items())
else:
    assert all(hashlib.sha256((ROOT / p["path"]).read_bytes()).hexdigest() == p["sha256"] for p in dependencies)

out = {
    "schema": "vp-source-lexical-holds-followup-v1", "created_at": datetime.now(timezone.utc).isoformat(),
    "scope": "Four previously unresolved Opus lexical cases, with symmetric paired observations and explicit input/key defects. No historical files or scores changed.",
    "counts": {"accepted_source_licensed_answers_with_input_repair_required": 2, "rejected": 1, "unresolved": 1},
    "rows": cases,
    "symmetry_warning": "Reb and khund corrections would also revoke two currently correct Astra canonical answers under the identified source-backed lexemes. A false-to-true-only adjustment is insufficient and must not be used for these cases.",
    "historical_input_policy": "Preserve all1800 historical task objects, prompts and raw grades. Mark these two inputs as defective; adopt any explicit source-conditioned retrospective annotation separately. Repair citations and gold in a new benchmark version, with fresh evaluation or an explicit statement that old responses were to different prompts.",
    "no_silent_union": "Absence of an anudatta mark is not evidence that both endings are licensed. In the kaqi case both lexical readings are positively sourced and distinguished; in reb/khund the inspected exact lexemes support middle only.",
    "source_limits": ["The source inventory metadata is an editorial cross-reference, not an independent grammar proof.", "Exact final inflections for reb/khund follow productive primary rules and printed structural analogues; the full submitted inflections are not claimed to be separately printed dictionary witnesses.", "The Kshira edition inspected does not support the exact sal-r citation; absence in this bounded search is not a universal proof that no edition ever has it.", "No claim of full-paradigm certification or full755-family source certification follows from this four-case review."],
    "inputs": [binding(HERE / "Anthropic-review.json"), binding(CANDIDATE / "tasks.json"), binding(CANDIDATE / "public-prompts.json"), *[binding(CARRY / "results" / p / "canonical.json") for p in results]],
    "source_snapshots": [binding(p) for p in sorted(SOURCES.iterdir()) if p.is_file()],
    "primary_scan_urls": {"dhatupradipa-43.jpg": "https://jainqq.org/explore/004319/43", "dhatupradipa-50.jpg": "https://jainqq.org/explore/004319/50", "kshira-110.jpg": "https://jainqq.org/explore/002433/110", "kshira-141.jpg": "https://jainqq.org/explore/002433/141", "kshira-142.jpg": "https://jainqq.org/explore/002433/142", "madhaviya160.jpg": "https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha/mdhvscan/MDhVjpg/madhaviyahdhatuv00sayauoft_bw_0160.jpg", "madhaviya170.jpg": "https://sanskritlibrary.org/Sanskrit/Vyakarana/Dhatupatha/mdhvscan/MDhVjpg/madhaviyahdhatuv00sayauoft_bw_0170.jpg"},
    "frozen_dependency_count_verified": len(dependencies), "historical_mutations": 0, "provider_calls": 0, "ledger_changes": 0,
}
(HERE / "lexical-holds-followup.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"counts": out["counts"], "artifact": binding(HERE / "lexical-holds-followup.json"), "frozen_dependency_count_verified": len(dependencies)}, ensure_ascii=False))
