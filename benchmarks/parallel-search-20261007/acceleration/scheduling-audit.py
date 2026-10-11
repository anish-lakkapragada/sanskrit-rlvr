"""Timing/accounting-only retrospective simulation; no scheduler or provider calls."""
from pathlib import Path
import datetime,hashlib,heapq,json,statistics,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from misc import vp_goal as r
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(x):return datetime.datetime.fromisoformat(x).timestamp()

def main():
    state=r.load();intervals=[];stages=[];durations=[];files={}
    for n in range(1,21):
        name=f'astra-simple4d-direct-{n:02d}';j=state['jobs'][name];p=r.OUT/'jobs'/name
        assert j['settled'] and j['collected_at'] and j['transport']=='direct' and j['n']==10
        for i in range(10):
            cid=f'task-{i:05d}';ip=p/(cid+'.intent.json');hp=p/(cid+'.effective.http.json')
            # Ignore response body/text. Only local request and receipt timestamps are used.
            start=json.loads(ip.read_text())['attempted_at'];stop=json.loads(hp.read_text())['received_at']
            a,b=dt(start),dt(stop);assert b>=a
            intervals.append((a,b));durations.append(b-a)
            files[str(ip.relative_to(ROOT))]=sha(ip);files[str(hp.relative_to(ROOT))]=sha(hp)
        stages.append({'id':name,'start':dt(j['attempted_at']),'stop':dt(j['collected_at'])})
    wall=max(b for a,b in intervals)-min(a for a,b in intervals);active=maximum=0
    for _,change in sorted([(a,1) for a,b in intervals]+[(b,-1) for a,b in intervals]):active+=change;maximum=max(maximum,active)
    sim={}
    for workers in [8,16,24,32]:
        available=[0.]*workers
        for seconds in durations:heapq.heappush(available,heapq.heappop(available)+seconds)
        sim[str(workers)]={'makespan_seconds':max(available),'makespan_minutes':max(available)/60}
    pool_ids={'Anthropic':'ending-screen-direct-20261007','OpenAI':'simple4d-astra-standard-20261007'}
    budget={}
    for provider,pool_id in pool_ids.items():
        pool=state['submission_pools'][pool_id];spent=sum(j['actual_cost_upper_micro'] if j.get('settled') else j['reservation_micro'] for name,j in state['jobs'].items() if name in pool['job_ids'])
        rates=r.rates({'provider':provider,'transport':'direct'})
        one=1500*rates['input_rate']+65536*rates['output_rate']
        committed=r.committed(state,provider);protected=r.protected_remaining(state,provider);cap=r.PROVIDERS[provider]['cap_micro']
        scenarios={}
        for workers in [8,16,24,32]:
            reserve=workers*one
            scenarios[str(workers)]={'outstanding_maximum_usd':reserve/1e6,
                'lifetime_plus_protected_plus_outstanding_usd':(committed+protected+reserve)/1e6,
                'existing_pool_spent_plus_outstanding_usd':(spent+reserve)/1e6,
                'fits_lifetime_and_protected':committed+protected+reserve<=cap,
                'fits_arithmetic_unused_old_pool':spent+reserve<=pool['cap_micro']}
        budget[provider]={'lifetime_cap_usd':cap/1e6,'current_committed_usd':committed/1e6,
            'protected_remaining_usd':protected/1e6,'unprotected_headroom_usd':(cap-committed-protected)/1e6,
            'comparison_pool_id':pool_id,'comparison_pool_cap_usd':pool['cap_micro']/1e6,'comparison_pool_spent_usd':spent/1e6,
            'comparison_pool_unused_usd':(pool['cap_micro']-spent)/1e6,'one_65536_request_max_usd':one/1e6,
            'old_pool_has_only_completed_allowlisted_jobs':all(state['jobs'][name].get('settled') for name in pool['job_ids']),
            'new_work_authorized_by_unused_pool':False,'scenarios':scenarios}
    report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Retrospective timing-only input-order simulation and prospective arithmetic; no new execution authorization',
        'observations':{'requests':200,'stages':20,'requests_per_stage':10,'wall_seconds':wall,'wall_minutes':wall/60,
            'summed_service_seconds':sum(durations),'average_concurrency':sum(durations)/wall,'maximum_observed_concurrency':maximum,
            'eight_slot_utilization':sum(durations)/(8*wall),'request_seconds':{'min':min(durations),'median':statistics.median(durations),'mean':statistics.mean(durations),'max':max(durations)},
            'between_stage_overhead_seconds':sum(max(0,stages[i+1]['start']-stages[i]['stop']) for i in range(19))},
        'continuous_fixed_input_order_simulation':sim,'simulation_assumption':'Keep observed per-request service durations fixed, omit provider queuing/rate limits/restarts; not a wall-time promise.',
        'budget_snapshot':budget,'caps_and_protected_reserves_unchanged':True,
        'recommendation':['All evaluations are complete; do not mutate their frozen protocol or replay anything.',
            'For newly authorized future work, remove ten-question completion barriers before simply increasing concurrency. A persistent eight-slot pool already removes much idle capacity.',
            'Use one versioned coordinator: verify and atomically reserve each admitted fixed unit under a brief ledger lock, release it during network waits, and reacquire for validated usage settlement.',
            'Outstanding + uncertain maxima + settled actuals must fit both a newly authorized pool ceiling and the global ceiling after protected reserves. Reduce admission automatically when headroom shrinks; do not reduce the declared token cap.',
            'Before each POST persist intent and exact effective request; no retries for uncertain work; freeze input membership, model/effort/cap and full-panel-before-score analysis.',
            'Do not run concurrent unchanged submit() executors: their lock encloses all network requests, so they serialize or fail the nonblocking lock.',
            'A future test-split/final64k run requires its separate release/core-barrier protocol. These development pools and timing figures do not authorize final membership.'],
        'meaningful_regression_checks':['Simultaneous admission cannot overspend global or pool caps.','Crash before/after POST preserves intent, maxima and no replay.','Malformed/missing usage retains full reservation.','Settlement merges latest ledger state without losing other jobs.','Score visibility remains blocked until the fixed panel is complete.'],
        'raw_timing_file_hashes':files,'code_hashes':{p:sha(ROOT/p) for p in ['misc/vp_goal.py','misc/vp_simple_astra_compare.py']},
        'request_durations_seconds_in_frozen_order':durations,'model_answer_text_used':False,'accuracy_used':False,'paid_calls':0,'ledger_mutations':False}
    (OUT/'scheduling-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'observations':report['observations'],'simulations':sim,'budget':budget},indent=2))

if __name__=='__main__':main()
