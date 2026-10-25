from pathlib import Path
import unittest,socket,sys,contextlib
ROOT=Path('D:/Research-VeriFact');OUT=Path(__file__).resolve().parent
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('audit network blocked'))
suite=unittest.TestSuite()
for folder,pattern in [('tests','test*.py'),('tasks/019_support_boundary_screen','test*.py'),('tasks/020_lambda2_patient_validation','test*.py')]:
 suite.addTests(unittest.TestLoader().discover(str(ROOT/folder),pattern=pattern))
with (OUT/'tests.log').open('w',encoding='utf-8') as f,contextlib.redirect_stdout(f):
 r=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
print('tests',r.testsRun,'failures',len(r.failures),'errors',len(r.errors))
sys.exit(not r.wasSuccessful())
