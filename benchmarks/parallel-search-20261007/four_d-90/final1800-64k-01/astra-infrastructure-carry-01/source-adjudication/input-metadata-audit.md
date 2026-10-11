# Input-only inventory audit

All **755 selected families / 1,800 fixed tasks** were compared against2,259 inventory records, joined uniquely by `baseindex`. No response, outcome, receipt body or score file was opened. The audit does not adopt source truth or change grades.

Code/class matches:755/755. Accent-stripped citations match754/755. Meaning text matches754/755. Inventory citations carry no accent signs at all (0/2,259), so missing accents in its text are not evidence of missing accents in the public prompt.

There are12 present-probe pada-label differences. The actual selected contexts also show12 families /18 tasks, but the sets differ: śad has a present-only middle condition absent in selected perfect; vṛt gains P specifically in the selected conditional. The union of all metadata flags covers24 families /30 tasks. These overlapping diagnostics are not a proposed exclusion count.

**Known public-entry conflicts:** reb01.0248 and khund01.0946 lack the source-required final it-marker anudatta in the visible citation. Independent primary reviews establish middle-only entries; literal input drives frozen VP P. This audit finds both without using correctness. Jabh01.0150 has the same inventory-A/engine-P pattern but retains separate unresolved lexical/num evidence.

**Other priority source checks:** śrā01.0922 and jñā01.0923 are explicitly described by the inventory as common references rather than independent roots. Six root-accent tag discrepancies include śrā plus vid06.0168, druh/muh/sṇuh04.0094–96, and puṣ04.0121. Tanadi vanu08.0008 has a Kaumudi2547.2 P branch needing exact scope verification. These are diagnostic leads, not newly certified oracle errors.

**Differences that must not become blanket holds:** intrinsic āya/optional ṇic and specific pada rules explain most label differences. Ṣasj01.0229 has P in the flat field but its own note explicitly supports both padas. Vṛt has an explicit inventory pada_note allowing P in sya contexts. The lone citation segment difference is omitted candrabindu in inventory pebr01.0208, with A classification agreeing; the lone meaning difference for ruṅ01.1114 is itself recorded as an alternate reading in the inventory note. Vedic tags on03.0017 and05.0033 coexist with already independently reviewed classical exceptions.

Every family row records visible citation, full matching metadata notes, local accent tests, present and actual selected-context pada probes, exact task IDs/indices/coordinates/prompt hashes, and source work needed. All1,800 probe unions reproduce frozen canonical keys. This is a reproducible metadata diagnostic, not a fresh independent Sanskrit certification.

| Code | Tasks | Flags | Interpretation |
|---|---:|---|---|
| 07.0017 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | conditional_pada_rule_not_inventory_contradiction |
| 01.0946 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | independently_confirmed_visible_entry_conflict |
| 01.0991 | 1 | present_probe_pada_label_difference | lakara_condition_not_general_pada_conflict |
| 01.0922 | 1 | root_accent_tag_difference, inventory_marks_no_independent_forms | root_accent_tag_needs_primary_comparison; placeholder_entry_source_hold_candidate |
| 04.0094 | 1 | root_accent_tag_difference | root_accent_tag_needs_primary_comparison |
| 03.0017 | 1 | vedic_tag_with_preexisting_classical_exception | previously_reviewed_classical_exception_not_new_hold |
| 10.0449 | 7 | present_probe_pada_label_difference, selected_context_pada_label_difference | intrinsic_derivation_or_context_not_bare_pada_conflict |
| 01.0923 | 1 | inventory_marks_no_independent_forms | placeholder_entry_source_hold_candidate |
| 01.0150 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | missing_it_accent_candidate |
| 05.0033 | 1 | vedic_tag_with_preexisting_classical_exception | previously_reviewed_classical_exception_not_new_hold |
| 04.0095 | 1 | root_accent_tag_difference | root_accent_tag_needs_primary_comparison |
| 01.0507 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | intrinsic_derivation_or_context_not_bare_pada_conflict |
| 01.0508 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | intrinsic_derivation_or_context_not_bare_pada_conflict |
| 01.0208 | 1 | citation_segment_difference | editorial_nasal_marker_omission_candidate |
| 04.0121 | 1 | root_accent_tag_difference | root_accent_tag_needs_primary_comparison |
| 01.0248 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | independently_confirmed_visible_entry_conflict |
| 01.1114 | 1 | artha_reading_difference | explicit_variant_reading_in_inventory_note |
| 01.1164 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | conditional_pada_rule_not_inventory_contradiction |
| 08.0008 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | pada_label_scope_needs_primary_confirmation |
| 01.0862 | 1 | selected_context_pada_label_difference | lakara_condition_explicitly_explained_by_inventory |
| 06.0168 | 1 | root_accent_tag_difference | root_accent_tag_needs_primary_comparison |
| 04.0096 | 1 | root_accent_tag_difference | root_accent_tag_needs_primary_comparison |
| 01.1077 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | conditional_pada_rule_not_inventory_contradiction |
| 01.0229 | 1 | present_probe_pada_label_difference, selected_context_pada_label_difference | inventory_field_vs_own_note |

Reproduce from repository root:
.venv/bin/python /Users/anish/Documents/git-repos/sanskrit/benchmarks/parallel-search-20261007/four_d-90/final1800-64k-01/astra-infrastructure-carry-01/source-adjudication/audit_input_metadata.py

The script and JSON pin the task, public-prompt, inventory and local interpretation-code hashes. Canonical-success tasks are included by full input enumeration; no outcome was used to identify or prioritize a family.
