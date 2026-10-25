from pathlib import Path
import unittest,socket,sys
TEMP=Path(__file__).resolve().parent
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('audit network blocked'))
suite=unittest.TestSuite()
suite.addTests(unittest.TestLoader().discover('tasks/018_verifact_gap_attribution',pattern='test018.py'))
suite.addTests(unittest.TestLoader().discover('tests',pattern='test_evaluation.py'))
with (TEMP/'tests.log').open('w',encoding='utf-8') as f:r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
print('tests',r.testsRun,'failures',len(r.failures),'errors',len(r.errors))
sys.exit(not r.wasSuccessful())
