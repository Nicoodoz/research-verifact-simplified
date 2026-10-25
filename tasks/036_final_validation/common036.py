"""036 task-owned storage; importing this module never reads keys or blocks networking."""
from pathlib import Path
import sys, hashlib, json, time, os
ROOT=Path(__file__).resolve().parents[2]; TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/036_final_validation'; CAP=150
sys.path.insert(0,str(ROOT/'tasks/029_semantic_information_gate'))
import common029 as base
read=base.read; lines=base.lines; csvread=base.csvread; sha=base.sha; require=base.require; now=base.now
LABELS=base.LABELS
def write_text(path,text):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:f.write(text);f.flush();os.fsync(f.fileno())
    for attempt in range(20):
        try:os.replace(tmp,path);return
        except PermissionError:
            if attempt==19:raise
            time.sleep(.1)
base.write_text=write_text
put=base.put; jsonl=base.jsonl; csvwrite=base.csvwrite
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()

