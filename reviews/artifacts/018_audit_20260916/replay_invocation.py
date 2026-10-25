from pathlib import Path
import sys,socket,contextlib,unittest
ROOT=Path('D:/Research-VeriFact');TEMP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tasks/018_verifact_gap_attribution'))
orig=Path.relative_to
def relative(self,other,*args):
    try:return orig(self,other,*args)
    except ValueError:
        if self.is_relative_to(TEMP) and Path(other)==ROOT:return self
        raise
Path.relative_to=relative
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('audit network blocked'))
from verify018 import verify
with (TEMP/'replay.log').open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f):verify(TEMP/'replay')
suite=unittest.defaultTestLoader.discover('tasks/018_verifact_gap_attribution',pattern='test018.py')
suite.addTests(unittest.defaultTestLoader.discover('tests',pattern='test_evaluation.py'))
with (TEMP/'tests.log').open('w',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
print('replay PASS; tests',result.testsRun,'failures',len(result.failures),'errors',len(result.errors))
sys.exit(not result.wasSuccessful())
