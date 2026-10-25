"""090 primitives: immutable inputs, original-text units, frozen decision mapping."""
from pathlib import Path
import copy, hashlib, json, os, re, sys
ROOT=Path(__file__).resolve().parents[2]
TASK=ROOT/'tasks/090_demo_constructor_repair_validation'
PUB=ROOT/'outputs/090_demo_constructor_repair_validation'
OUT=ROOT/'outputs/replays/090_demo_constructor_repair_validation'
sys.path.insert(0,str(ROOT/'tasks/087_f4_evidence_intervention'))
from common087 import canonical,h,sha,read,lines,now,LABELS,METHODS,priorg,attribution,make_body
ARMS=('B','F4','P90','Q90')
MODEL='deepseek-v4-flash-0731'
BUILDER='qwen3.5-flash-2026-02-23'
PRICES={MODEL:(3.,9.),BUILDER:(.2,2.)}
CAP=40.

def put(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(obj,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    tmp.rename(path)
def putl(path,objects):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        for x in objects:f.write(canonical(x)+'\n')
def text(path,s):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(s)

def token_proxy(s):
    # Deterministic English word/number/punctuation units, NOT provider tokens.
    return len(re.findall(r'[A-Za-z]+|\d+|[^\w\s]',s))

def unitize(reference):
    starts=[m.start() for m in re.finditer(r'(?m)^\d+\. Date: ',reference)]
    if not starts:return dict(prefix='',units=[dict(id='U001',start=0,end=len(reference),text=reference,sha256=h(reference),
                                                  proxy_tokens=token_proxy(reference),metadata=None,boundary='whole_reference_no_recognized_note_header')])
    prefix=reference[:starts[0]];units=[]
    for i,start in enumerate(starts):
        end=starts[i+1] if i+1<len(starts) else len(reference);body=reference[start:end]
        match=re.match(r'(\d+)\. Date: (.*?), Time: (.*?), Note Category: (.*?), Note ID: (.*?), Raw characters: \[(\d+),(\d+)\) \| Text: ',body)
        assert match,'unrecognized source metadata; do not guess'
        units.append(dict(id=f'U{i+1:03d}',start=start,end=end,text=body,sha256=h(body),proxy_tokens=token_proxy(body),
            metadata=dict(original_ordinal=int(match[1]),date=match[2],time=match[3],category=match[4],note_id=match[5],
                          raw_start=int(match[6]),raw_end=int(match[7])),boundary='whole_existing_reference_passage',
            source_ends_without_sentence_punctuation=body.rstrip()[-1:] not in '.!?'))
    assert prefix+''.join(x['text'] for x in units)==reference
    return dict(prefix=prefix,units=units)

def render_reference(source,selected):
    units=source['units'];allowed={x['id'] for x in units}
    if not selected or len(selected)!=len(set(selected)) or not set(selected)<=allowed:raise ValueError('invalid source IDs')
    # Full source is byte-identical; otherwise keep original headers/order, with explicit paragraph separation.
    if set(selected)==allowed:return source['prefix']+''.join(x['text'] for x in units)
    return source['prefix']+'\n\n'.join(x['text'].rstrip('\r\n') for x in units if x['id'] in selected)

def source_check(reference,source,selected,result):
    assert reference==source['prefix']+''.join(x['text'] for x in source['units'])
    for x in source['units']:
        assert reference[x['start']:x['end']]==x['text'] and h(x['text'])==x['sha256']
    assert render_reference(source,selected)==result
    # Every retained passage, including negation/condition/time/metadata, is indivisible.
    return True

def render_system(base,header,examples):
    return base+header+''.join(canonical(dict(proposition=x['claim'],reference=x['reference'],physician_label=x['physician_label']))+'\n' for x in examples)
