"""Conservative, claim-blind same-note repairs. Every addition is a raw span."""
from bisect import bisect_right, bisect_left
from collections import Counter
import re
import study011 as s

MAX_EDGE_EXTENSION=240
MAX_HEADING_DISTANCE=2000
MAX_CONTEXT_CHARS=240
SPECIAL={'24 Hour Events','Physical Examination','Assessment and Plan','Labs / Radiology'}
LIST=re.compile(r'(?m)^[ \t]*(?:\d{1,2}[.)][ \t]*(?:\n[ \t]*)?(?=[A-Za-z])|[-*][ \t]+(?=[A-Za-z])|#[.]?[ \t]*(?=[A-Za-z]))')
LABEL=re.compile(r'^([A-Za-z][A-Za-z /()&,-]{1,60}:)')
ABBREVIATIONS={'dr','mr','mrs','ms','vs','approx','fig','no','e.g','i.e'}

def trim(text,lo,hi):
    while lo<hi and text[lo].isspace():lo+=1
    while hi>lo and text[hi-1].isspace():hi-=1
    return lo,hi

def geometry(text):
    paragraphs=[];offset=0
    for m in re.finditer(r'\n[ \t\r]*\n',text):
        if text[offset:m.start()].strip():paragraphs.append(trim(text,offset,m.start()))
        offset=m.end()
    if text[offset:].strip():paragraphs.append(trim(text,offset,len(text)))
    headings=[];tests=[];offset=0
    for line in text.splitlines(keepends=True):
        lo,hi=trim(text,offset,offset+len(line));clean=text[lo:hi]
        match=LABEL.match(clean)
        if match:
            # Every explicit field bounds scope, regardless of capitalization.
            # Only a standalone heading can be reattached as structural context.
            end=hi if clean.endswith(':') else lo+match.end()
            headings.append(dict(start=lo,end_exclusive=end,text=text[lo:end],standalone=clean.endswith(':')))
        elif clean in SPECIAL:
            headings.append(dict(start=lo,end_exclusive=hi,text=clean,standalone=True))
        elif re.fullmatch(r'[_=\-]{3,}|[A-Z][A-Z /]{2,80}',clean):
            # Dividers and unpunctuated report/column headings end prior scope.
            # They are barriers only, never inferred semantic headings to attach.
            headings.append(dict(start=lo,end_exclusive=hi,text=clean,standalone=False))
        if clean.startswith('Test: ') and len(clean)<=120:
            tests.append(dict(start=lo,end_exclusive=hi,text=clean))
        offset+=len(line)
    for i,h in enumerate(headings):
        h['scope_end']=headings[i+1]['start'] if i+1<len(headings) else len(text)
    # Scope is syntactic and deliberately conservative, not a medical ontology.
    return dict(paragraphs=paragraphs,headings=headings,tests=tests)

def sentence_edges(text,lo,hi):
    result={lo,hi}
    for m in re.finditer(r'[.!?](?=\s+(?:[A-Z]|\d{1,2}\.\s)|\s*$)',text[lo:hi]):
        edge=lo+m.end()
        prefix=text[lo:edge-1]
        last=re.search(r'([A-Za-z.]+)$',prefix)
        if m.group()=='.' and last and (last.group(1).lower() in ABBREVIATIONS or len(last.group(1))==1):continue
        # Never split within a de-identification placeholder.
        if text.rfind('[**',lo,edge)>text.rfind('**]',lo,edge):continue
        result.add(edge)
    return sorted(result)

def repair_span(p,note,g=None):
    text=note['TEXT'];start,end=p['start'],p['end_exclusive'];g=g or geometry(text)
    assert note['ROW_ID']==p['note_id'] and note['SUBJECT_ID']==p['subject_id']
    assert s.pilot.digest_text(text)==p['note_sha256'] and text[start:end]==p['text']
    para=next((pair for pair in g['paragraphs'] if pair[0]<=start and end<=pair[1]),None)
    if para is None:return start,end,dict(unresolved=['cross_paragraph_original'],added=0)
    lo,hi=para;edges=set(sentence_edges(text,lo,hi))
    def outside_parentheses(pos):
        prefix=text[lo:pos]
        return prefix.count('(')==prefix.count(')')
    hs=[h for h in g['headings'] if lo<=h['start']<hi and outside_parentheses(h['start'])]
    for h in hs:edges.update((h['start'],h['end_exclusive']))
    lists=[lo+m.start() for m in LIST.finditer(text[lo:hi])]
    edges.update(lists);edges=sorted(e for e in edges if e in (lo,hi) or outside_parentheses(e))
    # A list item is an indivisible boundary unit, including all its sentences.
    stops=sorted(set(lists+[h['start'] for h in hs]+[hi]))
    def containing_list(pos):
        possible=[a for a in lists if a<=pos]
        if not possible:return None
        a=max(possible);b=next(x for x in stops if x>a)
        return (a,b) if a<=pos<b else None
    left_unit=containing_list(start)
    right_unit=containing_list(end-1)
    left=left_unit[0] if left_unit else edges[max(0,bisect_right(edges,start)-1)]
    right=right_unit[1] if right_unit else edges[min(len(edges)-1,bisect_left(edges,end))]
    left,_=trim(text,left,start) if left<start else (start,start)
    _,right=trim(text,end,right) if end<right else (end,end)
    unresolved=[]
    if start-left>MAX_EDGE_EXTENSION:left=start;unresolved.append('left_boundary_beyond_240')
    if right-end>MAX_EDGE_EXTENSION:right=end;unresolved.append('right_boundary_beyond_240')
    assert left<=start<end<=right and text[left:right].find(p['text'])>=0
    return left,right,dict(unresolved=unresolved,added=start-left+right-end)

def make_views(p,note,g=None):
    g=g or geometry(note['TEXT']);lo,hi,repair=repair_span(p,note,g)
    b=dict(p,start=lo,end_exclusive=hi,text=note['TEXT'][lo:hi],source_context=[],repair=repair)
    assert b['description']==note['DESCRIPTION']
    contexts=[]
    # An unambiguous single Echo Test field describes the entire examination.
    if p['category'].strip().lower()=='echo' and len(g['tests'])==1:
        t=g['tests'][0]
        if t['text'] not in b['text']:
            contexts.append(dict(t,kind='unique_note_test',scope_start=0,scope_end=len(note['TEXT'])))
    def local_paragraph_link(h):
        body=next((span for span in g['paragraphs'] if span[0]<=lo and hi<=span[1]),None)
        if body is None:return False
        if body[0]<=h['start']:return True
        index=g['paragraphs'].index(body)
        return index>0 and g['paragraphs'][index-1]==(h['start'],h['end_exclusive'])
    headings=[h for h in g['headings'] if h['standalone'] and local_paragraph_link(h) and h['end_exclusive']<=lo and hi<=h['scope_end']
        and 0<=lo-h['end_exclusive']<=MAX_HEADING_DISTANCE and h['text'] not in b['text']]
    if headings:
        h=max(headings,key=lambda h:h['start'])
        contexts.append(dict(h,kind='enclosing_local_heading',scope_start=h['end_exclusive']))
    contexts=[h for h in contexts if len(h['text'])<=MAX_CONTEXT_CHARS]
    c=dict(b,source_context=contexts)
    return dict(A=p,B=b,C=c)

def display(i,p,arm):
    if arm=='A':return s.previous.core.display_line(i,p)
    line=f"{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note Description: {p['description']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']})"
    for context in p['source_context']:
        line+=f" | Source heading [{context['start']},{context['end_exclusive']}): {context['text']}"
    return line+' | Text: '+p['text']

def pack(ids,scores,views,admission,arm,cap=8000):
    assert set(ids)<=set(scores),'Never invent missing rerank scores'
    if arm=='A':return s.previous.core.select_evidence(ids,scores,{k:v['A'] for k,v in views.items()},admission,cap=cap)
    selected=[];skipped=[];seen=set();counts=Counter();size=0
    for pid in sorted(ids,key=lambda x:(-scores[x],x)):
        p=views[pid][arm];duplicate=(p['date'],p['category'],p['text'])
        length=len(display(len(selected)+1,p,arm))+1
        reason='duplicate_same_date_text' if duplicate in seen else 'max_per_note' if counts[p['note_id']]>=2 else 'character_cap' if size+length>cap else 'max_items' if len(selected)>=16 else None
        if reason:skipped.append(dict(passage_id=pid,reason=reason,score=scores[pid]));continue
        selected.append(pid);seen.add(duplicate);counts[p['note_id']]+=1;size+=length
    ordered=sorted(selected,key=lambda pid:(views[pid][arm]['date'],views[pid][arm]['time'],views[pid][arm]['note_id'],views[pid][arm]['start']))
    header=f"Hospital Admission Start: {admission['ADMITTIME']}\nHospital Admission End: {admission['DISCHTIME']}\nElectronic Health Record Context\nOrdered by Time (Earliest to Latest):\n"
    reference=header+('\n'.join(display(i,views[pid][arm],arm) for i,pid in enumerate(ordered,1)) or 'No Electronic Health Record Context Found.')
    assert size<=cap
    return dict(selected_ids=ordered,relevance_order=selected,selection_skips=skipped,reference=reference,
        reference_sha256=s.pilot.digest_text(reference),body_characters=size,character_ceiling=cap)
