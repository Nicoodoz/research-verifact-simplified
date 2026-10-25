"""Confirm the public verifier's behavior after an ordinary review index update."""
from pathlib import Path
import sys,json,traceback
root=Path('D:/Research-VeriFact'); scratch=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tasks/009_retrieval_baselines'))
source=root/'tasks/009_retrieval_baselines/verify009.py'
text=source.read_text(encoding='utf-8')
old='assert output.is_relative_to(s.OUT) and not output.exists()'
assert text.count(old)==1
namespace={'__name__':'auditor_post_review_replay','__file__':str(source)}
exec(compile(text.replace(old,'assert not output.exists()'),str(source),'exec'),namespace)
result={'only_in_memory_adaptation':'output location guard, identical to first successful replay','tests_repeated':False}
try:
    namespace['run'](scratch/'replay_after_review_update',False)
except AssertionError:
    result.update(status='blocked',traceback=traceback.format_exc())
    assert "assert set(evidence['tracked_changes'])<= {'README.md','AGENTS.md'}" in result['traceback']
else:
    result['status']='unexpected_success'
    raise AssertionError('Expected review-index restriction did not reproduce')
finally:
    (scratch/'post_review_replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
