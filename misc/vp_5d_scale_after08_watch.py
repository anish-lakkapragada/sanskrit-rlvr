"""Wait for the full frozen pilot analysis, then compute unpaid size scenarios."""
import fcntl
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from misc import oai_batch_eval as io


def main():
    base = ROOT / 'benchmarks/parallel-search-20261006/five_d'
    output = base / 'pilot-08-scale-options-policy21'
    declaration = output / 'post08-scenarios-predeclaration.json'
    with (output / 'post08-scenarios-watch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = {'pid': os.getpid(), 'started_at': io.now(), 'paid_calls': 0,
                   'declaration_sha256': io.sha256(declaration)}
        deadline = time.monotonic() + 24 * 3600
        try:
            while time.monotonic() < deadline:
                if io.sha256(declaration) != receipt['declaration_sha256']:
                    raise ValueError('Prospective declaration changed')
                if (output / 'post08-scenarios-watch.STOP').exists():
                    receipt['status'] = 'stopped_without_analysis'
                    break
                if (base / 'pilot-08/revision-02/aggregate-analysis.json').exists():
                    from misc.vp_5d_scale_after08 import analyze
                    result = analyze()
                    receipt.update(status='complete_pending_coordinator_review',
                                   output=str(result), output_sha256=io.sha256(result))
                    break
                receipt.update(status='waiting_for_complete_aggregate', updated_at=io.now())
                io.atomic_json(output / 'post08-scenarios-watch.json', receipt)
                time.sleep(30)
            else:
                receipt['status'] = 'deadline_without_analysis'
        except Exception as exc:
            receipt.update(status='error_no_payment', error_type=type(exc).__name__, message=str(exc))
        receipt['updated_at'] = io.now()
        io.atomic_json(output / 'post08-scenarios-watch.json', receipt)


if __name__ == '__main__':
    main()
