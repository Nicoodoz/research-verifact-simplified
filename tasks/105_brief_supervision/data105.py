"""Exact 104 answers, serialization-time verdict span, and causal token groups."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import common105 as c

sys.path.insert(0,str(c.ROOT/'tasks/104_supervision_evidence'))
import training104 as shared

def construct_answer(row):
    """Reconstruct byte-identical 104 JSON while recording the value position.

    No searching for a label, key substring or the last occurrence in a reason.
    Quotes enclosing the verdict are JSON structure, not classification text.
    """
    obj=shared.parse_answer(row)
    parts=['{'];size=1;span=None
    for ordinal,(key,value) in enumerate(obj.items()):
        prefix=(',' if ordinal else '')+c.canonical(key)+':'
        parts.append(prefix);size+=len(prefix)
        encoded=c.canonical(value)
        if key=='verdict':
            assert isinstance(value,str) and value in c.LABELS
            span=(size+1,size+len(encoded)-1)
        parts.append(encoded);size+=len(encoded)
    parts.append('}');text=''.join(parts)
    if text!=row['answer']:raise ValueError('Would change the frozen 104 supervision answer')
    assert span is not None and text[span[0]:span[1]]==row['GT']
    return text,span

def offsets(tok,text):
    backend=getattr(tok,'backend_tokenizer',None) or getattr(tok,'tokenizer',None)
    if backend is None:raise ValueError('Exact fast-tokenizer offsets are required')
    encoding=backend.encode(text,add_special_tokens=False)
    ids=list(encoding.ids);spans=[tuple(s) for s in encoding.offsets]
    assert ids==tok.encode(text,add_special_tokens=False)
    assert tok.decode(ids,skip_special_tokens=False)==text
    return ids,spans

def encode(tok,row):
    text,span=construct_answer(row)
    answer_ids,token_spans=offsets(tok,text)
    value=[];covered=set()
    for index,(start,end) in enumerate(token_spans):
        if start<span[1] and span[0]<end:
            if not span[0]<=start<end<=span[1]:
                raise ValueError('A BPE token crosses verdict-value/JSON-structure boundary')
            value.append(index);covered.update(range(start,end))
    if covered!=set(range(*span)):raise ValueError('Verdict token offsets do not cover the serialized value exactly')
    prefix=shared.prompt_ids(tok,row)
    eos=tok.convert_tokens_to_ids('<|im_end|>');assert isinstance(eos,int)
    suffix=answer_ids+[eos]
    groups=[0]*len(prefix)+[1 if i in value else 2 for i in range(len(suffix))]
    labels=[-100]*len(prefix)+suffix
    assert len(value)>0 and groups[-1]==2
    return dict(input_ids=prefix+suffix,labels=labels,groups=groups,
                prompt_tokens=len(prefix),answer_tokens=len(suffix),
                verdict_value_chars=list(span),verdict_answer_token_indices=value,
                answer_token_offsets=[list(s) for s in token_spans],
                prompt_token_sha256=c.digest(c.canonical(prefix)),answer_sha256=c.digest(text))

def training_plan(ids,epochs=2,accumulation=8):
    """Same original order every epoch, complete short tails, global step IDs."""
    step=0;consumed=0;result=[]
    for epoch in range(epochs):
        for start in range(0,len(ids),accumulation):
            which=ids[start:start+accumulation];step+=1;consumed+=len(which)
            result.append(dict(step=step,epoch=epoch+1,start=start,end=start+len(which),
                               ids=which,loss_divisor=len(which),consumed=consumed,
                               epoch_end=start+len(which)==len(ids)))
    return result

def validate_cursor(plan,step,consumed):
    if type(step) is not int or type(consumed) is not int or not 0<=step<=len(plan):raise ValueError('Invalid optimizer cursor')
    expected=plan[step-1]['consumed'] if step else 0
    if consumed!=expected:raise ValueError('Resume must be at an exact committed optimizer boundary')
    return plan[step:]

