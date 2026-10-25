"""Exact whole-source-text factoring; never reads a claim, GT or model verdict."""
import re
from collections import defaultdict
HEADER=re.compile(r'(?m)^\d+\. Date: [^\n]*?Raw characters: \[(\d+),(\d+)\) \| Text: ')
TABLE='\n\nVerbatim shared source text table:\n'
def encode_with_dictionary(reference,dictionary):
    prefix,entries=parse(reference);reverse={v:k for k,v in dictionary.items()}
    body=prefix+''.join(v['header']+reverse.get(v['text'],v['text'])+v['separator'] for v in entries)
    appendix=TABLE+''.join(k+'\n'+v+'\n[[END_'+k[2:]+'\n' for k,v in dictionary.items()) if dictionary else ''
    return body+appendix,body
def parse(reference):
    matches=list(HEADER.finditer(reference));entries=[]
    if not matches:raise ValueError('unrecognized C48 source format')
    for i,m in enumerate(matches):
        end=m.end()+int(m[2])-int(m[1]);next_start=matches[i+1].start() if i+1<len(matches) else len(reference)
        if end>next_start:raise ValueError('source-length mismatch')
        entries.append(dict(header=reference[m.start():m.end()],text=reference[m.end():end],separator=reference[end:next_start]))
    prefix=reference[:matches[0].start()]
    assert prefix+''.join(v['header']+v['text']+v['separator'] for v in entries)==reference
    return prefix,entries
def factor(reference):
    if '[[SOURCE_TEXT_' in reference or TABLE in reference:raise ValueError('marker collision')
    prefix,entries=parse(reference);groups=defaultdict(list)
    for i,row in enumerate(entries):groups[row['text']].append(i)
    repeated=[(text,indices) for text,indices in groups.items() if len(indices)>1 and len(text)>=160]
    repeated.sort(key=lambda x:(-(len(x[0])*(len(x[1])-1)),x[1][0]))
    dictionary={f'[[SOURCE_TEXT_{i+1:03d}]]':text for i,(text,_) in enumerate(repeated[:4])}
    packed,body=encode_with_dictionary(reference,dictionary)
    if len(packed)>=len(reference):return dict(reference=reference,body=reference,dictionary={},saved=0,groups=0,occurrences=0)
    restored=body
    for key,text in dictionary.items():restored=restored.replace(key,text)
    assert restored==reference
    return dict(reference=packed,body=body,dictionary=dictionary,saved=len(reference)-len(packed),groups=len(dictionary),occurrences=sum(len(groups[text]) for text in dictionary.values()))
