from pathlib import Path
import sys, os, socket, json

ROOT = Path('D:/Research-VeriFact')
TEMP = Path(__file__).resolve().parent
number = sys.argv[1]
name = {'014':'014_qwen27b_baseline_comparison','015':'015_disagreement_adjudication'}[number]
sys.path.insert(0, str(ROOT/'tasks'/name))
original = Path.relative_to
def relative(self, other, *args):
    try:
        return original(self, other, *args)
    except ValueError:
        if str(self).startswith(str(TEMP)) and Path(other) == ROOT:
            return self
        raise
Path.relative_to = relative
socket.socket.connect = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('Audit network blocked'))
module = __import__('verify'+number)
module.verify(TEMP/('replay'+number+'_002'))
