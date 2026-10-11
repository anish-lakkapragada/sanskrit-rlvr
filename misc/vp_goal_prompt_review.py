"""Read-only paired review of whole-panel Sanskrit terminology comparisons."""
import copy
from collections import Counter

from misc import vp_goal as c, oai_batch_eval as io
from misc.vp_goal_analyze import summarize


PAIRS = [('opus-contrast-01', 'opus-contrast-sanskrit-prompt-02'),
         ('opus-paradigm-01', 'opus-paradigm-sanskrit-prompt-02'),
         ('opus-contrast-sanskrit-prompt-02', 'opus-contrast-dhatu-word-probe-03'),
         ('opus-paradigm-sanskrit-prompt-02', 'opus-paradigm-dhatu-word-probe-03'),
         ('opus-contrast-dhatu-word-probe-03', 'opus-contrast-line-format-probe-04'),
         ('opus-paradigm-dhatu-word-probe-03', 'opus-paradigm-line-format-probe-04'),
         ('opus-contrast-line-format-probe-04', 'opus-contrast-template-probe-05'),
         ('opus-paradigm-line-format-probe-04', 'opus-paradigm-template-probe-05'),
         ('opus-samasa-01', 'opus-samasa-template-probe-03'),
         ('opus-unadi-01', 'opus-unadi-sanskrit-probe-02'),
         ('opus-independent-creation-01', 'opus-independent-sanskrit-probe-02')]


def semantic_task(task):
    value = copy.deepcopy(task)
    value.pop('prompt_version')
    for key in ('prompt_sha256', 'probe_original_status', 'prompt_comparison_source_job', 'probe_selection'):
        value['campaign'].pop(key, None)
    return value


def review():
    ledger = c.load()
    result = {'updated_at': io.now(), 'comparisons': [],
              'selection': 'v2 reruns complete panels; v3 takes 16 random items per size; v4 and v5 rerun all v3 items. No correctness/refusal filtering.',
              'interpretation': 'v2 changes contextual wording; v3 substitutes verbal base for verbal root; v4 changes answer format to ordered lines; v5 extends the established single-form template with per-form fields. Repeated exposures do not add unique tasks. Fresh calibration is required before final selection.'}
    for source, target in PAIRS:
        source_job, target_job = ledger['jobs'][source], ledger['jobs'][target]
        source_tasks = io.read_json(c.OUT/'jobs'/source/'tasks.json')
        target_tasks = io.read_json(c.OUT/'jobs'/target/'tasks.json')
        source_by_id = {t['id']:t for t in source_tasks}
        matched_source_tasks = [source_by_id[t['id']] for t in target_tasks]
        if list(map(semantic_task, matched_source_tasks)) != list(map(semantic_task, target_tasks)):
            raise ValueError('Paired tasks differ beyond the declared prompt metadata')
        row = {'source_job':source, 'target_job':target, 'n':len(target_tasks),
               'source_transport':source_job.get('transport', 'batch'),
               'target_transport':target_job.get('transport', 'batch'),
               'transport_confound':source_job.get('transport', 'batch') != target_job.get('transport', 'batch'),
               'source_panel_n':len(source_tasks), 'semantic_identity_verified':True, 'unique_new_tasks':0,
               'source_tasks_digest':source_job['tasks_digest'],
               'target_tasks_digest':target_job['tasks_digest'],
               'status':'collected' if target_job.get('collected_at') else target_job['status']}
        if target_job.get('collected_at'):
            old = io.read_json(c.OUT/'jobs'/source/'results.json')
            new = io.read_json(c.OUT/'jobs'/target/'results.json')
            old_by_id = {r['task_id']:r for r in old}
            old = [old_by_id[r['task_id']] for r in new]
            if [r['task_id'] for r in old] != [r['task_id'] for r in new]:
                raise ValueError('Paired result IDs or order differ')
            row.update(source_summary=summarize(old), target_summary=summarize(new),
                       source_statuses=dict(Counter(r['status'] for r in old)),
                       target_statuses=dict(Counter(r['status'] for r in new)),
                       status_transitions=dict(Counter(a['status']+' -> '+b['status'] for a,b in zip(old,new))),
                       correctness_transitions=dict(Counter(str(bool(a['is_correct']))+' -> '+str(bool(b['is_correct'])) for a,b in zip(old,new))),
                       target_usage_cost_upper_usd=target_job['actual_cost_upper_micro']/1e6,
                       cells={})
            for label in sorted({r['task']['campaign']['construction'] for r in new}):
                row['cells'][label] = {
                    'source':summarize([r for r in old if r['task']['campaign']['construction']==label]),
                    'target':summarize([r for r in new if r['task']['campaign']['construction']==label])}
        result['comparisons'].append(row)
    io.atomic_json(c.OUT/'sanskrit-prompt-comparison-02.json', result)
    return result


if __name__ == '__main__':
    import json
    print(json.dumps(review(), ensure_ascii=False, indent=2))
