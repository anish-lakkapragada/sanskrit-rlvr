"""Complete-panel direct-transport analysis; never substitutes batch outcomes."""
from pathlib import Path
from misc import vp_goal as r, oai_batch_eval as io
from misc.vp_simple_search_analyze import describe, paired

OUT = r.ROOT / 'benchmarks/parallel-search-20261007/acceleration'


def analyze():
    plan = io.read_json(OUT/'plan.json')
    s = r.load()
    result = {'updated_at':io.now(), 'tracks':{}, 'benchmark_ready':False,
              'transport':'direct', 'plan_sha256':io.sha256(OUT/'plan.json'),
              'protocol':'Same frozen600questions; Opus5.5 xHigh/65536; directAPI; no paid retries',
              'acceleration':{'extra_spending_cap_usd':100,
                             'execution':io.read_json(OUT/'execution.json') if (OUT/'execution.json').exists() else {'state':'prepared'}}}
    rows_by_arm = {}
    for arm, source in plan['sources'].items():
        stages = [x for x in plan['stages'] if x['arm']==arm]
        jobs = [s['jobs'].get(x['id']) for x in stages]
        if not all(j and j.get('settled') and j.get('collected_at') for j in jobs):
            continue
        original = s['jobs'][source['job']]
        tasks, _ = r.verify_job(original)
        if r.digest(tasks)!=source['tasks_digest']:
            raise ValueError('Frozen source panel changed')
        rows = []
        for stage, job in zip(stages,jobs):
            chunk, _ = r.verify_job(job)
            if (job['provider']!='Anthropic' or job['phase']!='confirm_64k' or
                job.get('transport')!='direct' or chunk!=tasks[stage['start']:stage['stop']]):
                raise ValueError('Changed direct protocol or membership')
            rr=io.read_json(r.OUT/'jobs'/job['id']/'results.json')
            if len(rr)!=len(chunk):raise ValueError('Incomplete direct stage')
            rows.extend(rr)
        if len(rows)!=200:raise ValueError('Incomplete direct panel')
        rows_by_arm[arm]=(tasks,rows)
    for track, arms in {'four_d':['four_d'],'modification':['modification','control']}.items():
        stages=[x for x in plan['stages'] if x['arm'] in arms]
        progress=[{'id':x['id'],'status':s['jobs'].get(x['id'],{}).get('status','prepared'),
                   'settled_requests':x['n'] if s['jobs'].get(x['id'],{}).get('settled') else 0} for x in stages]
        if not all(a in rows_by_arm for a in arms):
            result['tracks'][track]={'state':'waiting_for_complete_panel','jobs':progress,
                                    'settled_requests':sum(x['settled_requests'] for x in progress)}
            continue
        details={'state':'complete_pending_source_review','primary':describe(*rows_by_arm[arms[0]]),
                 'jobs':progress,'settled_requests':sum(x['settled_requests'] for x in progress)}
        if track=='modification':
            details.update(control=describe(*rows_by_arm['control']),
                           paired=paired(rows_by_arm['modification'][1],rows_by_arm['control'][1]))
        result['tracks'][track]=details
    if all(a in rows_by_arm for a in ['modification','control']):
        declaration=io.read_json(OUT.parent/'source-sensitivity-predeclaration.json')
        path=r.ROOT/declaration['hold_path']
        if io.sha256(path)!=declaration['hold_sha256']:raise ValueError('Source hold changed')
        hold=io.read_json(path);retained={}
        for arm,key in [('modification','modification_id'),('control','control_id')]:
            tasks,rows=rows_by_arm[arm];ids={x[key] for x in hold['pairs']}
            if not ids<={t['id'] for t in tasks}:raise ValueError('Missing held pair')
            retained[arm]=([t for t in tasks if t['id'] not in ids],[x for x in rows if x['task']['id'] not in ids])
        result['source_sensitivity']={'state':'complete_supplementary_sensitivity','held_pairs':len(hold['pairs']),
            'modification':describe(*retained['modification']),'control':describe(*retained['control']),
            'paired':paired(retained['modification'][1],retained['control'][1])}
    else:
        result['source_sensitivity']={'state':'waiting_for_both_complete_arms','held_pairs':1}
    ids={x['id'] for x in plan['stages']}
    result['acceleration']['settled_requests']=sum(j['n'] for k,j in s['jobs'].items() if k in ids and j.get('settled'))
    result['acceleration']['settled_cost_usd']=sum(j.get('actual_cost_upper_micro',0) for k,j in s['jobs'].items() if k in ids and j.get('settled'))/1e6
    result['acceleration']['committed_cost_usd']=sum(j['actual_cost_upper_micro'] if j.get('settled') else j['reservation_micro'] for k,j in s['jobs'].items() if k in ids)/1e6
    io.atomic_json(OUT/'analysis.json',result)
    return result
