"""Offline-only entrypoint; invoke with the documented safety PYTHONPATH."""
from pathlib import Path
import json,sys,unittest,shutil
# Use absolute paths for cleanup so the audit hook can fail closed on relative dir_fd mutations.
shutil._use_fd_functions=False
from datetime import datetime,timezone
import sitecustomize
from misc import vp_goal as runner
from misc import ant_batch_eval as ant,oai_batch_eval as io
assert Path(runner.ROOT).resolve()==Path(__file__).resolve().parent/'worktree'
assert Path(sitecustomize.__file__).resolve()==Path(__file__).resolve().parent/'safety/sitecustomize.py'
client_calls=[]
def forbidden(*a,**kw):
    client_calls.append('blocked')
    raise AssertionError('Provider clients are disabled in the prototype test harness')
runner.client_for=ant.api_client=io.api_client=forbidden
names=['misc.test_vp_goal','misc.test_vp_cartesian_release','misc.test_vp_cartesian_release_run','misc.test_vp_cartesian_final_analyze','misc.test_vp_cartesian_release64k','test_isolation']
suite=unittest.defaultTestLoader.loadTestsFromNames(names)
result=unittest.TextTestRunner(verbosity=2).run(suite)
receipt=dict(at=datetime.now(timezone.utc).isoformat(),tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),provider_client_calls=len(client_calls),network_guard_enabled=True,live_ledger_and_results_read_guard_enabled=True,outside_prototype_write_guard_enabled=True,synthetic_fixture_only=True,test_modules=names)
(Path(__file__).resolve().parent/'test-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if not result.wasSuccessful():sys.exit(1)
