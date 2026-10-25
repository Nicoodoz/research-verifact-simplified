"""Run repository unit tests with network disabled, retaining a task-local log."""
from pathlib import Path
import contextlib, json, socket, sys, unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/019_support_boundary_screen'
sys.path.insert(0,str(ROOT/'src'))

def blocked(*args,**kwargs):
    raise RuntimeError('External network blocked during019 regression tests')

if __name__=='__main__':
    path=OUT/'full_repository_regression_001.txt'
    with path.open('x',encoding='utf-8') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log),patch.object(socket,'create_connection',blocked),patch.object(socket.socket,'connect',blocked):
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    summary=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        passed=result.wasSuccessful(),network_blocked=True,new_API_calls=0,scope='existing tests/;019 new tests recorded separately')
    (OUT/'full_repository_regression_001.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary),flush=True)
    if not result.wasSuccessful():print(path.read_text(encoding='utf-8')[-16000:])
