"""031 task I/O and fixed model recipes. No network/key reads on import."""
from pathlib import Path
import sys,hashlib,json,datetime
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/031_training_expansion_confirmation'
sys.path.insert(0,str(ROOT/'tasks/029_semantic_information_gate'))
import common029 as base
import learning029 as learning
read=base.read;lines=base.lines;put=base.put;jsonl=base.jsonl;csvwrite=base.csvwrite;csvread=base.csvread;sha=base.sha;require=base.require;now=base.now;write_text=base.write_text
LABELS=base.LABELS;CAP=80
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rank(s):return hashlib.sha256(('031/patient-split/v1:'+s).encode()).hexdigest()
