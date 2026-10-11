"""Mandatory test-process guard: no network, live ledgers/results, or external writes."""
import os,sys
from pathlib import Path
ALLOWED=Path(__file__).resolve().parents[1]
LIVE=ALLOWED.parents[3]
def path_ok(value):
    if isinstance(value,int) or value is None:return True
    return Path(os.fsdecode(value)).resolve().is_relative_to(ALLOWED)
def guard(event,args):
    if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn','os.posix_spawnp'}:
        raise RuntimeError('Prototype forbids network and child-process actions')
    if event=='open':
        path,mode,flags=args
        if isinstance(path,int):return
        p=Path(os.fsdecode(path)).resolve()
        if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
            if not path_ok(path) and p!=Path('/dev/null'):raise RuntimeError('Prototype write outside isolated directory: '+str(p))
        elif not path_ok(path) and (p.name=='.env' or ('credentials' in p.parts and not (p.suffix=='.py' and p.parent==LIVE/'.venv/lib/python3.10/site-packages/anthropic/lib/credentials')) or '/benchmarks/iterative-goal-20261006/' in str(p) or p.name=='results.json'):
            raise RuntimeError('Prototype cannot read live credentials, ledger or model results')
    if event=='os.symlink':
        # Dictionary loader creates only this read-only reference inside TMPDIR.
        target,destination=args[:2]
        if Path(target).resolve()!=LIVE/'data/finetune/task-data/vidyut_dhatupatha_5.tsv' or not path_ok(destination):
            raise RuntimeError('Prototype forbids this symlink')
        return
    if event in {'os.remove','os.unlink'}:
        path=Path(os.fsdecode(args[0]));parent=path.parent.resolve()
        if not parent.is_relative_to(ALLOWED):raise RuntimeError('Prototype unlink outside isolated directory')
        return
    if event in {'os.mkdir','os.rmdir','os.chmod','os.truncate'} and not path_ok(args[0]):
        raise RuntimeError('Prototype filesystem mutation outside isolated directory')
    if event in {'os.rename','os.replace','os.link'} and not all(path_ok(x) for x in args[:2]):
        raise RuntimeError('Prototype filesystem mutation outside isolated directory')
sys.addaudithook(guard)
