import os, sys, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
os.chdir(ROOT)
import common as c
import learning as l
datasets,folds,sources=c.load_data()
train=[r for r in datasets["old_R0"] if r["fold"]!=0]
z,y=c.arrays(train)
def go(name, fn):
    print("START",name,flush=True)
    try:
        v=fn()
        print("OK",name, str(v)[:500], flush=True)
        return v
    except BaseException as e:
        print("ERR",name,repr(e),flush=True)
        traceback.print_exc()
        raise
s=go("states", lambda:l.states(z,y,[r["sid"] for r in train]))
t=go("temperature", lambda:l.temperature(z,y,2.0))
j=go("joint", lambda:l.joint(z,y))
for kind in ("G","M","V","T"):
    go("legacy_"+kind, lambda kind=kind:c.legacy.fit(z,y,kind))
print("DONE",flush=True)
