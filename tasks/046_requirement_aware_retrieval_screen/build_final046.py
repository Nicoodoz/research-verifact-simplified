"""Build R1-R6 raw-EHR references and deduplicated fixed-DeepSeek final jobs."""
from pathlib import Path
import json,re,hashlib,copy
from collections import defaultdict,Counter
import sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/046_requirement_aware_retrieval_screen";R031=ROOT/"outputs/031_training_expansion_confirmation";R044=ROOT/"outputs/044_incremental_evidence_recovery"
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/046_requirement_aware_retrieval_screen"))
import run046
STOP=set("a an the this that these those is are was were be been being of to and or in on at for from by with as it its he she his her they their patient patients pt had has have did does do will would can could should".split())
def toks(s):return set(x for x in re.findall(r"[a-z]+|\d+(?:\.\d+)?",s.lower()) if x not in STOP)
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def put(p,v):
    with Path(p).open("x",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
def jsonl(p,rows):
    with Path(p).open("x",encoding="utf-8",newline="\n") as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
def hid(pid):return hashlib.sha256(pid.encode()).hexdigest()[:24]
def norm(s):return re.sub(r"\s+"," ",s).strip()
def line(i,p):return f"{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}"
def append_passages(base,pids,corpus,budget=1500,max_items=3):
    nums=[int(x) for x in re.findall(r"(?m)^(\d+)\. Date:",base)];n=max(nums)+1 if nums else 1
    used=0;out=[];parts=[base.rstrip()]
    base_text={norm(m.group(1)) for m in re.finditer(r"\| Text: ([\s\S]*?)(?=\n\d+\. Date:|\Z)",base)}
    for pid in pids:
        if pid not in corpus or norm(corpus[pid]["text"]) in base_text or pid in out:continue
        s=line(n+len(out),corpus[pid]);L=len(s)+1
        if used+L>budget:continue
        out.append(pid);parts.append(s);used+=L
        if len(out)>=max_items:break
    return "\n".join(parts),out,used

def sentence_window(p,claim,max_chars=520):
    text=p["text"];spans=[]
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)",text):
        if m.group(0).strip():spans.append((m.start(),m.end()))
    if not spans:return p
    q=toks(claim);best=max(range(len(spans)),key=lambda i:(len(q&toks(text[spans[i][0]:spans[i][1]])),spans[i][1]-spans[i][0]))
    lo=max(0,best-1);hi=min(len(spans)-1,best+1);a=spans[lo][0];b=spans[hi][1]
    if b-a>max_chars:a,b=spans[best]
    sub=text[a:b].strip()
    return dict(p,date=p["date"],time=p["time"],category=p["category"],note_id=p["note_id"],
                start=p["start"]+a,end_exclusive=p["start"]+b,text=sub)

def append_objects(base,objs,budget=1500,max_items=3):
    nums=[int(x) for x in re.findall(r"(?m)^(\d+)\. Date:",base)];n=max(nums)+1 if nums else 1
    used=0;parts=[base.rstrip()];kept=[]
    for p in objs:
        s=line(n+len(kept),p);L=len(s)+1
        if used+L>budget:continue
        parts.append(s);kept.append(p);used+=L
        if len(kept)>=max_items:break
    return "\n".join(parts),kept,used
def main():
    if (OUT/"stage3_jobs.jsonl").exists():raise RuntimeError("stage3 exists")
    cohort={x["id"]:x for x in lines(OUT/"cohort.jsonl")};s1={x["id"]:x for x in lines(OUT/"stage1_selections.jsonl")}
    attempts,term=run046.state();corpus={x["passage_id"]:x for x in lines(R031/"materials_001/corpus.jsonl")}
    bynote=defaultdict(list)
    for p in corpus.values():bynote[(str(p["subject_id"]),p["note_id"])].append(p)
    for k in bynote:bynote[k].sort(key=lambda p:p["start"])
    jobs044={x["request_id"]:x for x in lines(R044/"eval_score/jobs.jsonl")}
    mapping=[];unique={}
    for pid,x in cohort.items():
        routes={}
        # R1/R2/R4 selector outputs already mapped to passage IDs.
        for route in ("R1","R2","R4"):
            ref,kept,chars=append_passages(x["base_reference"],s1[pid][route]["selected_pids"],corpus)
            routes[route]=dict(reference=ref,selected_pids=kept,added_chars=chars,source="D48")
        # R3: exact contiguous sentence windows from R1-selected passages.
        objs=[sentence_window(corpus[p],x["claim"]) for p in s1[pid]["R1"]["selected_pids"] if p in corpus]
        ref,kept,chars=append_objects(x["base_reference"],objs)
        routes["R3"]=dict(reference=ref,selected_pids=s1[pid]["R1"]["selected_pids"],added_chars=chars,source="R1_short_window",
                           windows=[dict(note_id=p["note_id"],start=p["start"],end_exclusive=p["end_exclusive"],text=p["text"]) for p in kept])
        # R5: R1 full passages plus at most one truly adjacent same-note paragraph span if budget permits.
        pids=list(s1[pid]["R1"]["selected_pids"]);neighbor=[]
        for spid in pids:
            p=corpus.get(spid)
            if not p:continue
            arr=bynote[(str(p["subject_id"]),p["note_id"])];idx=next((i for i,z in enumerate(arr) if z["passage_id"]==spid),None)
            if idx is None:continue
            cand=[]
            if idx>0 and abs(p["start"]-arr[idx-1]["end_exclusive"])<=5:cand.append(arr[idx-1])
            if idx+1<len(arr) and abs(arr[idx+1]["start"]-p["end_exclusive"])<=5:cand.append(arr[idx+1])
            if cand:
                q=toks(x["claim"]);z=max(cand,key=lambda y:len(q&toks(y["text"])))
                if z["passage_id"] not in pids:neighbor.append(z["passage_id"])
            if neighbor:break
        ref,kept,chars=append_passages(x["base_reference"],pids+neighbor,corpus)
        routes["R5"]=dict(reference=ref,selected_pids=kept,added_chars=chars,source="R1_plus_adjacent",neighbor_pids=neighbor)

        # R6 semantic rerank result.
        plan=s1[pid]["R6plan"];sel=[]
        rid="046_R6rank_"+hid(pid)
        if rid in term and term[rid]["parsed"].get("status")=="valid":
            obj=term[rid]["parsed"].get("parsed") or {};allowed=plan["candidate_short_to_pid"]
            sel=[allowed[z] for z in obj.get("selected",[]) if z in allowed][:3]
        ref,kept,chars=append_passages(x["base_reference"],sel,corpus)
        routes["R6"]=dict(reference=ref,selected_pids=kept,added_chars=chars,source="full_EHR_BM25_semantic",
                          gap=plan.get("gap"),queries=plan.get("queries"),rerank_selected=sel)
        for route,z in routes.items():
            changed=z["reference"]!=x["base_reference"];rid=None
            if changed:
                body=copy.deepcopy(jobs044[x["base_request_id"]]["body"])
                payload=json.loads(body["messages"][1]["content"]);payload["reference"]=z["reference"]
                body["messages"][1]["content"]=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
                bh=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
                rid="046_final_"+bh[:32]
                unique.setdefault(rid,dict(request_id=rid,route="shared_final",kind="judge",model_key="deepseek",id=pid,body=body))
            mapping.append(dict(id=pid,route=route,request_id=rid,reference_changed=changed,selected_pids=z.get("selected_pids",[]),
                                added_chars=z.get("added_chars",0),source=z.get("source"),details={k:v for k,v in z.items() if k not in ("reference","selected_pids","added_chars","source")}))
    jobs=sorted(unique.values(),key=lambda x:x["request_id"])
    jsonl(OUT/"final_mapping.jsonl",mapping);jsonl(OUT/"stage3_jobs.jsonl",jobs)
    put(OUT/"stage3_freeze.json",dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
      logical_changed=dict(Counter(m["route"] for m in mapping if m["reference_changed"])),unique_final_jobs=len(jobs),
      cumulative_cost_cny=sum(a["cost"] for a in attempts),GT_used=False))
    print(json.dumps(read(OUT/"stage3_freeze.json"),ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
