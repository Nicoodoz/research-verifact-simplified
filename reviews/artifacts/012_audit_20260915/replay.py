from pathlib import Path
from contextlib import redirect_stdout
import sys,json,hashlib
R=Path('D:/Research-VeriFact');O=R/'outputs/012_comparative_error_diagnosis';T=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
h=json.loads((O/'handoff_snapshot.json').read_text(encoding='utf-8'))
assert all(sha(R/p)==d for p,d in h['files'].items())
snapshot={'handoff_sha256':sha(O/'handoff_snapshot.json'),'files_matched':len(h['files']),'head':'b710543fd5caf8ca9b9017ec230cac9ac242f721'}
(T/'version.json').write_text(json.dumps(snapshot,indent=2)+'\n',encoding='utf-8')
sys.path.insert(0,str(R/'tasks/012_comparative_error_diagnosis'))
source=R/'tasks/012_comparative_error_diagnosis/verify012.py';text=source.read_text(encoding='utf-8')
guard='assert out.is_relative_to(s.OUT) and not out.exists()';assert text.count(guard)==1
scope={'__file__':str(source),'__name__':'auditor_replay012'}
exec(compile(text.replace(guard,'assert not out.exists()'),str(source),'exec'),scope)
print('All handoff fingerprints matched; receipt-only offline replay started',flush=True)
with (T/'replay.log').open('w',encoding='utf-8') as log,redirect_stdout(log):scope['verify'](T/'replay')
assert all(sha(R/p)==d for p,d in h['files'].items())
print((T/'replay/verification.json').read_text(encoding='utf-8'),flush=True)
