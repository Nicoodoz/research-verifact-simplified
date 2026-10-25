"""087 offline primitives. No API, credential, or patient reads on import."""
from pathlib import Path
import copy, datetime, hashlib, json, math, sys

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'tasks/087_f4_evidence_intervention'
OUT = ROOT / 'outputs/087_f4_evidence_intervention'
ARMS = ('B', 'F4', 'CL4', 'X4')
LABELS = ('Supported', 'Not Supported', 'Not Addressed')
METHODS = ('raw', 'U0', 'U2', 'PriorG')
MODEL = 'deepseek-v4-flash-0731'
CAP = 20.0
PERMUTATION = (2, 3, 0, 1)

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def canonical(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
def h(x): return hashlib.sha256(x.encode('utf-8')).hexdigest()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):
    with Path(p).open(encoding='utf-8-sig') as f: return [json.loads(s) for s in f if s.strip()]
def put(p,x):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(x,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False); f.write('\n')
def putl(p,rows):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:
        for row in rows: f.write(canonical(row)+'\n')
def text(p,s):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)

def render(base,header,examples,arm):
    if arm=='B':return base
    if arm not in ARMS:raise ValueError(arm)
    docs=[]
    for i,x in enumerate(examples):
        d={'proposition':x['claim'],'physician_label':x['physician_label']}
        if arm!='CL4':d['reference']=examples[PERMUTATION[i] if arm=='X4' else i]['reference']
        docs.append(d)
    if arm=='CL4':
        old='Each example contains a proposition, EHR reference, and physician label.'
        if header.count(old)!=1:raise ValueError('unexpected example header')
        header=header.replace(old,'Each example contains a proposition and physician label.')
    return base+header+''.join(canonical(d)+'\n' for d in docs)

def make_body(template,system,claim,reference):
    b=copy.deepcopy(template);b['messages'][0]['content']=system
    b['messages'][1]['content']=json.dumps({'proposition':claim,'reference':reference},ensure_ascii=False,separators=(',',':'))
    return b

def priorg(scores):
    # Exact frozen 053 constants and tie ordering of common066.priorg.
    ref=(1108/1378,100/1378,170/1378);cal=(48/143,47/143,48/143)
    pb=[math.log(a/b) for a,b in zip(ref,cal)];pb=[x-pb[2] for x in pb]
    v=[math.log(max(float(scores[k])/100,1e-6))+pb[i]+(.1342909508820116 if i==0 else 0) for i,k in enumerate(LABELS)]
    return LABELS[max(range(3),key=lambda i:v[i])]

def attribution(base,candidate,gt):
    """Validity first; native missing raw never inferred from fallback."""
    br,cr=base.get('raw_verdict'),candidate.get('raw_verdict')
    bf,cf=base['final'],candidate['final']
    valid=bool(base['valid'] and candidate['valid'])
    if not valid:kind='invalid_or_fallback_related'
    elif (br==gt)!=(cr==gt):kind='raw_correctness_change'
    elif br==cr and bf!=cf:kind='valid_score_boundary_change'
    elif br!=cr:kind='other_raw_label_change'
    else:kind='unchanged_raw_and_final'
    return dict(kind=kind,both_valid=valid,base_raw=br,candidate_raw=cr,base_final=bf,candidate_final=cf,
                rescue=bf!=gt and cf==gt,harm=bf==gt and cf!=gt,
                raw_rescue=(br!=gt and cr==gt) if valid else None,
                raw_harm=(br==gt and cr!=gt) if valid else None)
