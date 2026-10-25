import sys,unittest,json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'src'))
sys.path.insert(0,str(root/'tasks/029_semantic_information_gate'))
import common029
common029.offline()
suite=unittest.TestSuite()
suite.addTests(unittest.defaultTestLoader.discover(str(root/'tasks/029_semantic_information_gate'),pattern='test029.py'))

with (Path(__file__).parent/'tests.log').open('w',encoding='utf-8') as log:
 result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
summary=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))
(Path(__file__).parent/'tests_summary.json').write_text(json.dumps(summary),encoding='utf-8')
print(summary)
assert result.wasSuccessful()
