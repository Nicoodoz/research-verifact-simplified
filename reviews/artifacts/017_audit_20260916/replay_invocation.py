from pathlib import Path
import sys,socket,unittest,contextlib
ROOT=Path('D:/Research-VeriFact');TEMP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tasks/017_verification_supervised_evidence_utility'))
original=Path.relative_to
def relative(self,other,*args):
    try:return original(self,other,*args)
    except ValueError:
        if self.is_relative_to(TEMP) and Path(other)==ROOT:return self
        raise
Path.relative_to=relative
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('Audit network blocked'))
from verify017 import verify
from report017 import render
with (TEMP/'replay.log').open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f):
    verify(TEMP/'replay')
    render(TEMP/'rendered/report.md')
assert (TEMP/'rendered/report.md').read_bytes()==(ROOT/'outputs/017_verification_supervised_evidence_utility/report.md').read_bytes()
print('replay and report bytes PASS')
with (TEMP/'tests.log').open('w',encoding='utf-8') as f:
    result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
print('tests',result.testsRun,'failures',len(result.failures),'errors',len(result.errors))
sys.exit(not result.wasSuccessful())
