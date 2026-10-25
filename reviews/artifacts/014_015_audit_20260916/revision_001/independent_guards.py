from pathlib import Path
from unittest.mock import patch
import sys,json,hashlib
ROOT=Path('D:/Research-VeriFact');TEMP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tasks/014_qwen27b_baseline_comparison'))
import replay_history as h,common014 as c
hist=json.loads((ROOT/'outputs/015_disagreement_adjudication/preparation_001/history_sha256.json').read_text())
original=Path.read_bytes
results=[]
for name in [h.VERIFIER,h.ORIGINAL,'tasks/014_qwen27b_baseline_comparison/common014.py',
             'outputs/014_qwen27b_baseline_comparison/report.md',
             'outputs/009_retrieval_baselines/revision_001/README.md']:
    data=original(ROOT/name)+b'\nchanged\n'
    selected={h.VERIFIER:hist[h.VERIFIER]} if name in [h.VERIFIER,h.ORIGINAL] else {name:hist[name]}
    def changed(p):return data if p==ROOT/name else original(p)
    try:
        with patch.object(Path,'read_bytes',changed):h.check_history(selected)
    except ValueError as e:results.append(dict(path=name,rejected=True,error=str(e)))
    else:raise AssertionError('Unexpected acceptance '+name)
for name in ['reviews/README.md','.gitattributes']:
    data=original(ROOT/name)+b'\nnormal status update\n'
    def changed(p):return data if p==ROOT/name else original(p)
    with patch.object(Path,'read_bytes',changed):
        result=h.check_history({name:hist[name]})
        assert result['mutable_entries'][0]['changed']
        try:c.check_hashes({name:hist[name]})
        except ValueError:pass
        else:raise AssertionError('Experiment hash checker relaxed')
    results.append(dict(path=name,history_drift_visible=True,experiment_binding_still_strict=True))
try:h.check_history({},bindings={'tasks/014_qwen27b_baseline_comparison/common014.py':{}})
except ValueError:results.append(dict(unregistered_computation_rebinding_rejected=True))
else:raise AssertionError('Model code rebind accepted')
(TEMP/'independent_guards.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('Independent guard checks passed:',len(results))
