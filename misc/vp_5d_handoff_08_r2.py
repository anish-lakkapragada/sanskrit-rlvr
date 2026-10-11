"""Final unpaid handoff for exact two-tuple policy21 repair."""
import json
from pathlib import Path
from misc.vp_5d_prepare_04 import ROOT,OUT,now,sha,atomic_json,status
from misc.vp_5d_analyze_08_r2 import verify_panel,JOBS
from misc.vp_5d_candidate_4800_p18 import digest
P=OUT/'pilot-08/revision-02';Q=P/'astra-subset';A=OUT/'pilot-08/revision-01'
def read(p):return json.loads(p.read_text())
def main():
 ts,ch,sub,ach=verify_panel(P);p=read(P/'plan.json');decl=read(P/'analysis-predeclaration.json');repair=read(P/'minimal-repair-audit.json');source=read(P/'source-rule-delta-audit.json')
 for f,d in decl['frozen_files'].items():assert sha(P/f)==d
 for f,d in decl['analysis_dependencies'].items():assert sha(ROOT/f)==d
 for r in p['source_hashes'].values():assert sha(Path(r['path']))==r['sha256']
 assert not source['new_rule_ids'] and not source['new_recipe_rule_contexts'];assert repair['primary_shared_ids']==2398 and repair['subset_shared_ids']==238
 ledgerpath=ROOT/'benchmarks/iterative-goal-20261006/ledger.json';ledger=read(ledgerpath);jobs08=[j for j in ledger['jobs'].values() if j['id'].startswith(('opus-five-d-pilot-08-','astra-five-d-pilot-08-'))];assert not jobs08
 artifacts=['plan.json','manifest.json','analysis-predeclaration.json','source-rule-delta-audit.json','minimal-repair-audit.json','astra-subset/plan.json','astra-subset/manifest.json']
 audit=dict(created_at=now(),passed=True,source_hashes=p['source_hashes'],analysis_dependency_hashes=decl['analysis_dependencies'],checked_artifacts={f:sha(P/f) for f in artifacts},both_panels_fully_regenerated=True,all_quotas_PN_families_and_chunk_counts_unchanged=True,global_optimal_objectives_unchanged=True,minimum_two_changed_tuples_attained=True,new_source_contexts=0,synthetic_tests_passed=5,policy21_supply_update_sha256=sha(OUT/'policy21-supply-mask-update.json'),registered_pilot08_jobs_before_handoff=0,ledger_sha256_at_check=sha(ledgerpath),no_answers_read=True,paid_calls=0);atomic_json(P/'preflight-audit.json',audit)
 jobs=[]
 for i,((jid,n,provider),rows) in enumerate(zip(JOBS,ch+ach)):
  cp=P/f'chunk-{i+1:02}.tasks.json' if i<6 else Q/f'chunk-{i-5:02}.tasks.json'
  jobs.append(dict(id=jid,provider=provider,phase='confirm_64k',effort='xhigh',max_output_tokens=65536,n=n,tasks_path=str(cp),tasks_sha256=sha(cp),tasks_digest=digest(rows),maximum_reservation_usd=263.344 if provider=='Anthropic' else 197.508,condition='Next provider chunk only after prior settlement and coordinator financial gate. Require all8settled before analysis; no score-based stopping.'))
 handoff=dict(created_at=now(),panel='five-d-pilot-08-revision-02',status='unpaid_ready_for_coordinator_review',fixed_primary_n=2400,fixed_paired_n=240,extra_unique_questions=0,tasks_path=str(P/'tasks.json'),tasks_sha256=sha(P/'tasks.json'),tasks_digest=digest(ts),paired_tasks_path=str(Q/'tasks.json'),paired_tasks_sha256=sha(Q/'tasks.json'),paired_tasks_digest=digest(sub),saved_artifacts={f:dict(path=str(P/f),sha256=sha(P/f)) for f in artifacts+['preflight-audit.json']},generation_source_hashes=p['source_hashes'],analysis_dependency_hashes=decl['analysis_dependencies'],analyzer_module='misc.vp_5d_analyze_08_r2',analysis_command='.venv/bin/python -m misc.vp_5d_analyze_08_r2 analyze '+str(P),jobs=jobs,source_policy='oracle-policy-21',source_policy_sha256=sha(OUT.parent/'oracle-policy-21.json'),adapter_sha256=sha(ROOT/'misc/vp_cartesian_task.py'),source_review='Single-san trace7.4.7 is conservatively excluded because its ni-before-caN condition is absent. Exact two-tuple repair avoids it without new broad recipe-rule contexts; independently reviewed ordinaryRic caN controls are preserved.',previous_artifacts_preserved=True,primary_shared_ids=2398,paired_shared_ids=238,all_approved_quotas_seed_and_objectives_unchanged=True,preexposure_ledger_check_sha256=sha(ledgerpath),final_n=None,final_membership_approved=False,paid_authorization_created=False,paid_calls=0,no_final_model_answers_read=True,benchmark_ready=False)
 atomic_json(P/'preflight-handoff.json',handoff);atomic_json(P/'experiment-request.json',handoff)
 (P/'README.md').write_text('''# Pilot 08, revision 02

This is the current unpaid preparation: **2,400 fresh exact development tuples from 670 families**, plus a fixed **240-question same-input Astra subset from 116 families**. Both references use xhigh with a common 65,536-token output ceiling. Six Opus chunks contain 400 questions each; two Astra chunks contain 120 each. All eight jobs must settle and collect before analysis. Parent owns registration, financial gates, submission and settlement.

Policy 21 holds single-san derivations whose trace applies 7.4.7 without the required ṇi-before-caN context. The affected tṛp10.0351 aorist was replaced through a deterministic two-task swap with the existing paired Curadi10.0177 benedictive singleton: tṛp now receives AshirLin/Uttama/Dvi, while10.0177 receives Lun/Prathama/Bahu. Both remain Kartari with the san recipe. The partner is the first valid fresh swap in SHA256 order using the original seed and partner ID; no model outcomes were used.

**Exactly two tuple IDs change in each panel.** The other2,398primary and238paired questions retain identical grammar, gold and rendered prompts. Every original file remains preserved. Placing each replacement in the matching tense/PN slot preserves every chunk's grammatical counts as well as global recipe, class, voice, tense, person and number quotas. All selected families, family loads and subset pair support remain unchanged.

The original optimal allocation is preserved:670families,560aorists beyond the first per family, and squared-load sum9,994. The feasible set only shrank under the new source rule; attaining the old optimum therefore certifies optimality under the narrower scope. Retaining the affected singleton family and exact tense quotas requires at least two tuple changes, and the repair attains that lower bound. Caps remain eight total and five aorists per family, with no repeated non-aorist tense.

The fixed mixture remains56%yaN→Ric,24%yaNluk→Ric and20%san;45%aorist,55%across the other nine lakaras;10%passive; all ten classes. Curadi145/Bhvadi1535 class quotas and all other quotas are unchanged. The causalized intensive recipes test inherited reduplication and stem preservation after different suffix-deletion histories. San supplies a shorter licensed contrast and broader lexical coverage. Mere chain length is not the difficulty rationale.

The paired subset retains43independent-family repeated-aorist pairs:26yaN/yaN,9luk/luk and8mixed. It also has82mixed-tense pairs from42families and45non-aorist pairs from33families. All42parent grammar cells and all ten classes are supported, including three Curadi aorists. Intentional family enrichment limits population interpretation; matching margins does not repair class/recipe/tense interaction gaps or within-cell selection. No san-containing repeated-aorist pair is measured. The frozen analyzer reports paired differences, cost/completion standardization, family uncertainty and these limitations separately from the2,400-question primary screen.

All forms regenerated successfully under policy21; exact historical novelty, prompt hashes, partitions and minimal-repair invariants pass. There are no new recipe-rule contexts in the broad reviewed inventory. Five synthetic analyzer tests pass. The source-mask update re-derived all147,195previously eligible single-san tuples, removing90development and54test tuples without removing eligible families. Non-san masks remain unchanged from hashed policy20 records.

The previous policy20cost/variance forecasts remain historical context in [revision01](../revision-01/cost-precision-context.json). No broader re-fitting was performed for this narrow repair. The prior4,800scale witness is not certified under the new masks; a fresh feasibility check is required before any final freeze. FinalN, membership, precision and funding remain unapproved. Actual64k behavior, repeated-family dependence and spending risk await this fixed confirmation and paired diagnostic.

All development families have historical exposure.235questions introduce a new exact recipe for a known family;2,165reuse an exposed recipe-family combination. Legacy6,687-item analysis inspected all dictionary families, including later reserved test families. Exact-tuple novelty and new-campaign separation do not establish globally unseen lexical roots. RL families remain separate. No held-out model answers were read.

[Preflight](preflight-handoff.json), [minimal repair](minimal-repair-audit.json), [analysis declaration](analysis-predeclaration.json), [source delta](source-rule-delta-audit.json), and [paired plan](astra-subset/plan.json) contain the checked hashes. No benchmark is qualified and no paid authorization was created by this worker.
''')
 current=OUT/'current.md';text=current.read_text();old=current.parent/'current-policy20-historical.md'
 if not old.exists():old.write_text(text)
 current.write_text('''# Current five-coordinate benchmark research

**Pilot08 revision02 is ready for coordinator review; no final benchmark is qualified.** It contains2,400fresh exact development tuples from670families and240same-input Astra questions from116families. The common prospective ceiling is65,536tokens at xhigh. All six Opus400 and two Astra120jobs must settle before the frozen analyzer reads outcomes.

Policy21 excludes single-san trace7.4.7 where its ṇi-before-caN condition is absent. An input-only, deterministic two-tuple swap repairs the affected tṛp aorist while preserving all families, global and per-chunk grammar/PN quotas, subset pair support and all three optimal allocation objectives. Exactly2IDs change per panel; all original artifacts remain immutable. [Current preparation](pilot-08/revision-02/README.md), [handoff](pilot-08/revision-02/preflight-handoff.json), [repair proof](pilot-08/revision-02/minimal-repair-audit.json), [frozen analyzer declaration](pilot-08/revision-02/analysis-predeclaration.json).

The approved mixture remains56%yaN→Ric,24%yaNluk→Ric,20%san;45%aorist,55%across the other nine lakaras;10%passive; all ten classes, with Curadi145/Bhvadi1535. Allocation covers670families, with560additional aorists and squared loads9,994. Caps are eight total and five aorists per family, each other tense at most once. The subset retains43independent-family repeated-aorist pairs plus mixed and non-aorist controls. Its nonuniform family enrichment makes cost/completion calibration and covariance conditional diagnostics, not unbiased population estimates.

All2,400and240forms regenerate under policy21. Exact two-campaign novelty, prompt hashes, unchanged allocation, all eight partitions and five analyzer tests pass. There are no new contexts beyond the broad reviewed source inventory. [Updated census evidence](policy21-supply-mask-update.json) removes90development and54test san tuples but no eligible families. The old4,800scale witness and policy20forecasts remain historical context; updated scale feasibility is required before any final membership freeze.

Earlier full07confirmation failed its target screen. The new confirmation uses an unchanged prospective79–81%screen for all-request and usable Opus accuracy and both missing-response bounds. The paired240diagnostic informs reference ordering, cost, completion and covariance. Future final evaluation still requires both iid and family-sandwich SE below one percentage point for both models, with fixedN chosen before final answers. [Preserved forecast and funding discussion](current-policy20-historical.md).

Hard cumulative caps remain$1,000Anthropic/$2,000OpenAI. Token tails, actual64kbehavior, family dependence and protected-reserve decisions can prevent completion. FinalN, membership and funding remain unapproved.

The task remains a cited dictionary verb entry, four grammatical coordinates and one ordered recipe from a finite menu, requesting one accepted Devanagari form. Sanskritv3 is unchanged. There are no prefixes, separately chosen pada, synthetic roots or nominal/multiple-answer tasks. All development families were previously exposed; legacy6,687-item analysis inspected all dictionary families, including later reserved test families. Current exact-tuple novelty is not globally unseen-root evidence. RL families remain separate. No held-out model answers or paid calls were used by this worker.
''')
 status('Policy21 revision02 ready for execution review','Exactly two tuples repaired in primary and paired panels. All quotas, family support, optimal allocation and chunk counts are preserved. Full regeneration and five analyzer tests pass. No paid calls or final benchmark approval.')
 print(json.dumps(dict(handoff=str(P/'preflight-handoff.json'),handoff_sha256=sha(P/'preflight-handoff.json'),primary_sha256=sha(P/'tasks.json'),subset_sha256=sha(Q/'tasks.json'),analyzer_sha256=sha(ROOT/'misc/vp_5d_analyze_08_r2.py'),declaration_sha256=sha(P/'analysis-predeclaration.json')),indent=2))
if __name__=='__main__':main()
