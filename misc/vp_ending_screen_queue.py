"""Wait for the existing Astra comparison; never interrupt or retry paid work."""
import fcntl
import time
from misc.vp_ending_screen_run import OUT, register, execute
from misc import vp_goal as r, oai_batch_eval as io


def main():
    with (OUT/'queue.lock').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        started=time.monotonic()
        expected=[f'astra-simple4d-direct-{i:02}' for i in range(1,21)]
        while True:
            s=r.load()
            ready=all(s['jobs'].get(name,{}).get('settled') and
                      s['jobs'].get(name,{}).get('collected_at') for name in expected)
            prior_execution=r.ROOT/'benchmarks/parallel-search-20261007/astra-comparison-01/execution.json'
            ready=ready and prior_execution.exists() and io.read_json(prior_execution).get('state')=='complete'
            if ready:break
            io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'queued_behind_astra',
                'n':96,'reason':'Preserve uninterrupted existing comparison and shared budget lock; no paid calls yet.',
                'prior_settled':sum(bool(s['jobs'].get(name,{}).get('settled')) for name in expected)*10})
            if time.monotonic()-started>6*3600:
                io.atomic_json(OUT/'execution.json',{'updated_at':io.now(),'state':'stopped_without_submission',
                    'reason':'Prior comparison did not fully settle within six hours; no paid requests.'})
                return
            time.sleep(15)
        register()
        execute()


if __name__=='__main__':main()
