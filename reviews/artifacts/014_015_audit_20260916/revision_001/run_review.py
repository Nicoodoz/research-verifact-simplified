from pathlib import Path
import sys,socket
ROOT=Path('D:/Research-VeriFact'); TEMP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tasks/014_qwen27b_baseline_comparison'))
original=Path.relative_to
def relative(self,other,*args):
    try:return original(self,other,*args)
    except ValueError:
        if str(self).startswith(str(TEMP)) and Path(other)==ROOT:return self
        raise
Path.relative_to=relative
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('Audit network blocked'))
from check_revision014015 import checks
checks(TEMP/'checks')
