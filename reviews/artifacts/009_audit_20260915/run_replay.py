from pathlib import Path
import sys
root=Path('D:/Research-VeriFact')
scratch=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tasks/009_retrieval_baselines'))
source=root/'tasks/009_retrieval_baselines/verify009.py'
original=source.read_text(encoding='utf-8')
old='assert output.is_relative_to(s.OUT) and not output.exists()'
assert original.count(old)==1
# Change only the output-location guard in memory so the executor's replay
# runs outside the frozen outputs. No repository source is edited.
adapted=original.replace(old,'assert not output.exists()')
namespace={'__file__':str(source),'__name__':'auditor_replay'}
exec(compile(adapted,str(source),'exec'),namespace)
namespace['run'](scratch/'replay',True)
