
"""Compare frozen model folds, predictions, and evaluation bytes after full offline replay."""
import json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[3];a=Path(__file__).parent
old=root/'outputs/029_semantic_information_gate/run_001'
new=root/'outputs/replays/audit029_20260920_conda'
assert json.loads((new/'execution_status.json').read_text())['state']=='completed'
checked=[]
for scope in ('patient_OOF','025_to_026','026_to_025'):
 for p in (old/scope).rglob('*'):
  if not p.is_file() or p.name=='manifest.json':continue
  rel=p.relative_to(old)
  assert p.read_bytes()==(new/rel).read_bytes(),str(rel)
  checked.append(str(rel).replace('\\','/'))
result=dict(passed=True,exact_model_prediction_evaluation_files=len(checked),files=checked,excluded_run_metadata=['manifest timestamps','run execution timestamps','pid'],new_API_calls=0)
(a/'replay_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Exact files:',len(checked))
