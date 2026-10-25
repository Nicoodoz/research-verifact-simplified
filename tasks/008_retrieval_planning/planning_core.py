"""Deterministic query, retrieval and evidence rules shared by every 008 arm."""
from collections import Counter
import math
import re
import numpy as np
import common as c

STOP=set("a an the this that these those is are was were be been being of to and or in on at for from by with as it its he she his her they their patient patients pt had has have did does do will would can could should".split())


def tokenize(text):
    text=re.sub(r"\[\*\*(.*?)\*\*\]",lambda m:" ".join(re.findall(r"\d+",m.group(1))),text)
    text=re.sub(r"(?<=[A-Za-z])[-‐‑](?=[A-Za-z])","",text)
    return [str(int(t)) if t.isdigit() else t for t in re.findall(r"[a-z]+|\d+(?:\.\d+)?",text.lower()) if t not in STOP]


def paragraph_spans(text,limit=640):
    offset=0
    edges=[]
    for separator in re.finditer(r"\n[ \t\r]*\n",text):
        edges.append((offset,separator.start()))
        offset=separator.end()
    edges.append((offset,len(text)))
    for lo,hi in edges:
        while lo<hi and text[lo].isspace():
            lo+=1
        while hi>lo and text[hi-1].isspace():
            hi-=1
        while hi-lo>limit:
            breaks=list(re.finditer(r"\s+",text[lo+limit//2:lo+limit]))
            end=lo+limit//2+breaks[-1].start() if breaks else lo+limit
            yield lo,end
            lo=end
            while lo<hi and text[lo].isspace():
                lo+=1
        if lo<hi:
            yield lo,hi


def source_context(prop,sentences):
    parent,bhc=prop["parent_text_chunk"],prop["brief_hospital_course"]
    locations=[m.start() for m in re.finditer(re.escape(parent),bhc)] if parent else []
    c.pilot.require(len(locations)==1,"Source parent must have unique literal location")
    lo=max(0,locations[0]-240)
    hi=locations[0]+len(parent)
    claim=set(tokenize(prop["text"]))
    candidates=sorted({r["text"] for r in sentences if r["brief_hospital_course"]==bhc and r["text"] and r["text"] in parent})
    def score(s):
        words=set(tokenize(s))
        return len(claim&words)/max(1,len(claim|words))
    chosen=min(candidates,key=lambda s:(-score(s),len(s),s)) if candidates else parent
    return dict(parent=parent,parent_start=locations[0],local=bhc[lo:hi],start=lo,end_exclusive=hi,
        sentence=chosen,sentence_rule="literal_max_token_jaccard" if candidates else "parent_fallback",
        bhc_sha256=c.pilot.digest_text(bhc))


class HybridIndex:
    def __init__(self,passages,vectors):
        self.passages=passages
        self.vectors=np.asarray(vectors,dtype=np.float64)
        self.vectors=self.vectors/np.linalg.norm(self.vectors,axis=1,keepdims=True)
        self.counts=[Counter(tokenize(x["search_text"])) for x in passages]
        self.lengths=np.array([sum(x.values()) for x in self.counts])
        self.average=float(self.lengths.mean())
        self.postings={}
        for i,counts in enumerate(self.counts):
            for token,n in counts.items():
                self.postings.setdefault(token,[]).append((i,n))

    def bm25(self,query):
        result=np.zeros(len(self.passages))
        for token in sorted(set(tokenize(query))):
            entries=self.postings.get(token,[])
            idf=math.log(1+(len(result)-len(entries)+.5)/(len(entries)+.5))
            for i,n in entries:
                result[i]+=idf*n*2.2/(n+1.2*(.25+.75*self.lengths[i]/max(1,self.average)))
        return sorted(((self.passages[i]["passage_id"],float(v)) for i,v in enumerate(result) if v>0),key=lambda x:(-x[1],x[0]))

    def retrieve(self,query,qvector,limit=80):
        lexical=self.bm25(query)[:limit]
        v=np.asarray(qvector,dtype=np.float64)
        scores=self.vectors@(v/np.linalg.norm(v))
        dense=sorted(((self.passages[i]["passage_id"],float(s)) for i,s in enumerate(scores)),key=lambda x:(-x[1],x[0]))[:limit]
        fused=Counter()
        for ranking in (lexical,dense):
            for rank,(pid,_) in enumerate(ranking,1):
                fused[pid]+=1/(60+rank)
        hybrid=sorted(fused,key=lambda pid:(-fused[pid],pid))
        return dict(bm25=lexical,dense=dense,hybrid=hybrid)


def candidate_pool(rankings,cap=48,reserve_direct=8):
    rankings=[r for i,r in enumerate(rankings) if r not in rankings[:i]]
    if len(rankings)==1:
        return rankings[0][:cap]
    scores=Counter()
    for j,ranking in enumerate(rankings):
        weight=.5 if j==0 else .5/(len(rankings)-1)
        for rank,pid in enumerate(ranking,1):
            scores[pid]+=weight/(60+rank)
    selected=list(rankings[0][:reserve_direct])
    for pid in sorted(scores,key=lambda k:(-scores[k],k)):
        if pid not in selected:
            selected.append(pid)
        if len(selected)==cap:
            break
    return selected


def display_line(i,p):
    return f"{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}"


def select_evidence(candidate_ids,scores,passages,admission,cap=8000,max_items=16,max_per_note=2):
    selected,skipped,seen=[],[],set()
    counts=Counter()
    size=0
    for pid in sorted(candidate_ids,key=lambda pid:(-scores[pid],pid)):
        span=passages[pid]
        duplicate=(span["date"],span["category"],span["text"])
        length=len(display_line(len(selected)+1,span))+1
        reason="duplicate_same_date_text" if duplicate in seen else "max_per_note" if counts[span["note_id"]]>=max_per_note else "character_cap" if size+length>cap else "max_items" if len(selected)>=max_items else None
        if reason:
            skipped.append(dict(passage_id=pid,reason=reason,score=scores[pid]))
            continue
        selected.append(pid)
        seen.add(duplicate)
        counts[span["note_id"]]+=1
        size+=length
    # Never trim a selected passage: the matching text remains exactly intact.
    ordered=sorted(selected,key=lambda pid:(passages[pid]["date"],passages[pid]["time"],passages[pid]["note_id"],passages[pid]["start"]))
    header=f"Hospital Admission Start: {admission['ADMITTIME']}\nHospital Admission End: {admission['DISCHTIME']}\nElectronic Health Record Context\nOrdered by Time (Earliest to Latest):\n"
    text=header+("\n".join(display_line(i,passages[pid]) for i,pid in enumerate(ordered,1)) or "No Electronic Health Record Context Found.")
    return dict(selected_ids=ordered,relevance_order=selected,selection_skips=skipped,reference=text,
        reference_sha256=c.pilot.digest_text(text),body_characters=size,character_ceiling=cap)


def parse_plan(raw,item):
    plan=c.pilot.strict_json(raw)
    expected={"evidence_needs","source_clues","terminology","queries","uncertainties"}
    c.pilot.require(isinstance(plan,dict) and set(plan)==expected,"Unexpected planner schema")
    c.pilot.require(isinstance(plan["evidence_needs"],list) and 1<=len(plan["evidence_needs"])<=4 and all(isinstance(x,str) for x in plan["evidence_needs"]),"Invalid needs")
    c.pilot.require(isinstance(plan["queries"],list) and len(plan["queries"])<=2 and all(isinstance(x,str) and 1<=len(x.strip())<=300 for x in plan["queries"]),"Invalid queries")
    c.pilot.require(isinstance(plan["source_clues"],list) and len(plan["source_clues"])<=5,"Invalid source clues")
    for x in plan["source_clues"]:
        c.pilot.require(isinstance(x,dict) and set(x)=={"quote","use"} and isinstance(x["quote"],str) and x["quote"] and x["quote"] in item["source"]["local"] and isinstance(x["use"],str),"Unverifiable source quote")
    c.pilot.require(isinstance(plan["terminology"],list) and all(isinstance(x,dict) and set(x)=={"term","alternative","basis"} and all(isinstance(t,str) for t in x.values()) for x in plan["terminology"]),"Invalid terminology")
    c.pilot.require(isinstance(plan["uncertainties"],list) and all(isinstance(x,str) for x in plan["uncertainties"]),"Invalid uncertainties")
    plan["queries"]=list(dict.fromkeys(x.strip() for x in plan["queries"]))
    return plan
