"""Build exhaustive full-corpus rankings and freeze expanded evidence audit jobs."""
import json,os,sys
from collections import Counter
import numpy as np
import common039 as c
import execute039 as ex

R036=c.ROOT/"outputs/036_final_validation"
PLAN=c.OUT/"planning_001"
OUT=c.OUT/"search_001"
MAX_EXTERNAL=32

sys.path.insert(0,str(c.ROOT/"tasks/036_final_validation"))
import api036
sys.path.insert(0,str(c.ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc

def parse_c48(reference,passage_lookup):
    starts=list(__import__("re").finditer(r"(?m)^(\d+)\. Date:",reference));entries=[];ids=set()
    for i,m in enumerate(starts):
        end=starts[i+1].start() if i+1<len(starts) else len(reference)
        text=reference[m.start():end].strip();num=int(m.group(1))
        mm=__import__("re").search(r"Note ID: (\d+), Raw characters: \[(\d+),(\d+)\)",text)
        pid=None
        if mm:pid=passage_lookup.get((mm.group(1),int(mm.group(2)),int(mm.group(3))))
        if pid:ids.add(pid)
        entries.append((f"C{num}",text,pid))
    c.require(entries,"empty C48")
    return entries,ids

def line_external(i,p):
    return f"E{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}"
def main():
    c.require(not OUT.exists(),"search exists")
    jobs=c.jsonl(PLAN/"query_jobs.jsonl");attempts,terminal=ex.state()
    for j in jobs:c.require(j["request_id"] in terminal and terminal[j["request_id"]]["parsed"]["status"]=="valid","query incomplete")
    queries={j["proposition_id"]:terminal[j["request_id"]]["parsed"] for j in jobs}

    inputs={r["proposition_id"]:r for r in c.jsonl(R036/"materials_001/inputs.jsonl")}
    cohort=c.csvread(PLAN/"cohort_key.csv")
    needed={r["id"] for r in cohort};subjects={r["sid"] for r in cohort}
    corpus=[r for r in c.jsonl(R036/"materials_001/corpus.jsonl") if r["subject_id"] in subjects]
    passages={r["passage_id"]:r for r in corpus}
    plook={(str(r["note_id"]),int(r["start"]),int(r["end_exclusive"])):r["passage_id"] for r in corpus}
    mats={r["proposition_id"]:r for r in c.jsonl(R036/"judge_inputs_001/materials.jsonl") if r["proposition_id"] in needed}

    mat=R036/"materials_001";catalog=c.read(mat/"embedding_catalog.json")
    keys=c.read(mat/"embedding_ids.json");vectors=dict(zip(keys,np.load(mat/"vectors.npy",allow_pickle=False)))
    _,term036,_=api036.state()
    for job in c.jsonl(mat/"embedding_jobs.jsonl"):
        if job["request_id"] not in term036:continue
        rr=term036[job["request_id"]];c.require(rr["parsed"]["status"]=="success","036 embedding invalid")
        native=json.loads(rr["transport"]["body_text"])
        for z in native["data"]:vectors[job["text_ids"][z["index"]]]=np.asarray(z["embedding"],float)
    c.require(all(inputs[pid]["claim_embedding_id"] in vectors for pid in needed),"claim vector missing")
    c.require(all(p["embedding_id"] in vectors for p in corpus),"corpus vector missing")
    indices={}
    for sid in sorted(subjects):
        pp=[p for p in corpus if p["subject_id"]==sid]
        indices[sid]=pc.HybridIndex(pp,[vectors[p["embedding_id"]] for p in pp])

    contexts=[];audit_jobs=[]
    for n,row in enumerate(cohort,1):
        pid=row["id"];item=inputs[pid];idx=indices[row["sid"]];q=queries[pid]
        full=idx.retrieve(item["text"],vectors[item["claim_embedding_id"]],limit=len(idx.passages))
        rankings=[[x[0] for x in full["dense"]],[x[0] for x in full["bm25"]]]
        for query in q["queries"]:rankings.append([x[0] for x in idx.bm25(query)])
        fused=Counter()
        for ranking in rankings:
            for rank,pid2 in enumerate(ranking,1):fused[pid2]+=1/(60+rank)
        c48_entries,c48_ids=parse_c48(mats[pid]["reference"],plook)
        ordered=[x for x in sorted(fused,key=lambda x:(-fused[x],x)) if x not in c48_ids]
        selected=ordered[:MAX_EXTERNAL]
        c48_text="\n".join(f"{cid}. {txt.split('. ',1)[1] if '. ' in txt else txt}" for cid,txt,_ in c48_entries)
        ext_lines=[line_external(i,passages[x]) for i,x in enumerate(selected,1)]
        expanded="\n".join(ext_lines) if ext_lines else "No additional EHR passages selected."
        lookup={cid:dict(source="C48",text=txt,passage_id=pp) for cid,txt,pp in c48_entries}
        lookup.update({f"E{i}":dict(source="EHR",text=line_external(i,passages[x]),passage_id=x) for i,x in enumerate(selected,1)})
        job=dict(request_id="039_audit_"+pid,kind="audit",model_key=c.MODEL_KEY,proposition_id=pid,
                 body=c.audit_body(item["text"],c48_text,expanded),evidence_lookup=lookup)
        audit_jobs.append(job)
        contexts.append(dict(id=pid,sid=row["sid"],audit_group=row["audit_group"],
          c48_passage_ids=sorted(c48_ids),external_passage_ids=selected,
          query_requirements=q["requirements"],queries=q["queries"],
          corpus_passages=len(idx.passages),external_selected=len(selected),
          audit_body_bytes=len(c.canonical(job["body"]).encode())))
    OUT.mkdir(parents=True)
    with (OUT/"contexts.jsonl").open("x",encoding="utf-8",newline="\n") as f:
        for r in contexts:f.write(json.dumps(r,ensure_ascii=False)+"\n")
    with (OUT/"audit_jobs.jsonl").open("x",encoding="utf-8",newline="\n") as f:
        for j in audit_jobs:f.write(json.dumps(j,ensure_ascii=False,sort_keys=True)+"\n")
    used=sum(a["charge_cny"] for a in attempts)
    bound=sum(c.bound(j) for j in audit_jobs)
    c.require(used+bound<=c.CAP+1e-9,f"039 budget forecast {used+bound:.3f}>{c.CAP}")
    c.put(OUT/"summary.json",dict(created_utc=c.now(),claims=len(contexts),max_external=MAX_EXTERNAL,
      mean_audit_body_bytes=float(np.mean([r["audit_body_bytes"] for r in contexts])),
      p95_audit_body_bytes=float(np.percentile([r["audit_body_bytes"] for r in contexts],95)),
      current_used_cny=used,audit_conservative_reservation_cny=bound,total_bound_cny=used+bound,
      full_corpus_ranked=True,dense_original_claim=True,bm25_original_plus_expanded_queries=True))
    print("039 search built",len(contexts),"audit bound",round(bound,3),"total",round(used+bound,3))

if __name__=="__main__":main()
