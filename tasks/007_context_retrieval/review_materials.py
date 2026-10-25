"""Build a balanced, traceable review set from 007; display full outputs/evidence."""
from collections import defaultdict, Counter
import argparse
import json
from pathlib import Path

import prepare as p
from retrieval import ARMS


def outcome(row,arm):
    if not row["claim"] or not row[arm]:
        return "missing"
    if row["claim"] != row["human_gt"] == row[arm]:
        return "improved"
    if row["claim"] == row["human_gt"] != row[arm]:
        return "degraded"
    if row["claim"] != row[arm]:
        return "both_wrong_changed"
    return "both_correct" if row["claim"]==row["human_gt"] else "both_wrong"


def build():
    run=p.OUT/"run_001"
    output=run/"review_001"
    output.mkdir(exist_ok=False)
    rows=p.pilot.read_csv(run/"analysis/transitions.csv")[1]
    inputs={r["proposition_id"]:r for r in p.pilot.jsonl(p.OUT/"preparation_003/inputs.jsonl")}
    responses={(r["proposition_id"],r["arm"]):r for r in p.pilot.jsonl(run/"analysis/normalized_responses.jsonl")}
    old={r["proposition_id"]:r for r in p.pilot.jsonl(p.OUT/"release_comparison_001/references.jsonl")}
    selected=defaultdict(list)
    for row in rows:
        row.update(**{a+"_outcome":outcome(row,a) for a in ARMS if a!="claim"})
    def pick(candidates,reason,n=1):
        fresh=[r for r in candidates if r["case_id"] not in selected]
        for row in sorted(fresh,key=lambda r:p.pilot.digest_text("007/review/v1:"+r["proposition_id"]))[:n]:
            selected[row["case_id"]].append(reason)
    for author in ("llm","human"):
        own=[r for r in rows if r["author_type"]==author]
        for kind in ("improved","degraded"):
            pick([r for r in own if r["mixed_outcome"]==kind],"primary_"+author+"_"+kind,2)
        pick([r for r in own if r["mixed_outcome"]=="both_wrong_changed"],"primary_"+author+"_both_wrong_changed")
        for arm in ("sentence","local"):
            pick([r for r in own if r[arm] and r[arm]!=r["claim"]],"diagnostic_"+author+"_"+arm)
        for correct in (True,False):
            pick([r for r in own if len({r[a] for a in ARMS})==1 and r["claim"] and (r["claim"]==r["human_gt"])==correct],
                "stable_"+author+"_"+("correct" if correct else "wrong"))
    for group in json.loads((run/"analysis/same_input_diagnostics.json").read_text(encoding="utf-8")):
        if group["labels_disagree"]:
            ids={rid.split(":",1)[1] for rid in group["request_ids"]}
            for row in rows:
                if row["proposition_id"] in ids:
                    selected[row["case_id"]].append("all_identical_input_label_disagreements")
    for row in rows:
        if any(not row[a] for a in ARMS):
            selected[row["case_id"]].append("all_missing_predictions")
    (output/"packets").mkdir()
    unions=defaultdict(dict)
    for row in rows:
        pid,cid=row["proposition_id"],row["case_id"]
        row["selection_reasons"]=";".join(selected[cid])
        item=inputs[pid]
        packet=dict(case=row,input=item,responses={a:responses.get((pid,a)) for a in (*ARMS,"claim_repeat")},released_reference=old[pid])
        p.pilot.write_json(output/"packets"/(cid+".json"),packet)
        if selected[cid]:
            for arm in ARMS:
                for number,pid_ref in enumerate(item["retrieval"][arm]["reference_passage_ids"],1):
                    span=next(x for x in item["retrieval"][arm]["passages"] if x["passage_id"]==pid_ref)
                    u=unions[row["subject_id"]].setdefault(pid_ref,dict(span,uses=[]))
                    u["uses"].append(dict(case_id=cid,arm=arm,reference_number=number,shown_end_exclusive=span["end_exclusive"]))
                    if span["end_exclusive"]>u["end_exclusive"]:
                        u.update(text=span["text"],end_exclusive=span["end_exclusive"])
    (output/"reference_unions").mkdir()
    for sid,union in unions.items():
        p.pilot.write_json(output/"reference_unions"/(sid+".json"),sorted(union.values(),key=lambda x:(x["date"],x["time"],x["note_id"],x["start"])))
    p.pilot.write_csv(output/"case_index.csv",rows)
    stats=dict(selected_cases=[r["case_id"] for r in rows if r["selection_reasons"]],
        unique_evidence_passages={sid:len(u) for sid,u in unions.items()},
        outcomes={author:{a:dict(Counter(r[a+"_outcome"] for r in rows if r["author_type"]==author)) for a in ARMS if a!="claim"} for author in ("llm","human")})
    p.pilot.write_json(output/"summary.json",stats)
    p.pilot.write_json(output/"manifest.json",dict(code_sha256=p.pilot.digest_file(Path(__file__)),
        scored_manifest_sha256=p.pilot.digest_file(run/"analysis/manifest.json"),
        output_sha256={x.relative_to(output).as_posix():p.pilot.digest_file(x) for x in output.rglob("*") if x.is_file()}))
    print(p.pilot.canonical(stats))


def read(cases,patient,start,count,mode):
    root=p.OUT/"run_001/review_001"
    if patient:
        union=json.loads((root/"reference_unions"/(patient+".json")).read_text(encoding="utf-8"))
        last=None
        for i in range(start,min(start+count,len(union))):
            span=union[i]
            header=f"NOTE {span['note_id']} {span['date']} {span['time']} {span['category']}"
            if last!=header:
                print("\n"+header)
                last=header
            print(f"[{i}] raw [{span['start']},{span['end_exclusive']}) "+span["text"])
        print(f"END [{start},{min(start+count,len(union))}) total={len(union)}")
    else:
        for cid in cases:
            packet=json.loads((root/"packets"/(cid+".json")).read_text(encoding="utf-8"))
            print("\n"+cid+" "+json.dumps({k:packet["case"][k] for k in ("author_type","subject_id","human_gt",*ARMS)},ensure_ascii=False))
            print("CLAIM: "+packet["input"]["text"])
            if mode=="release":
                print(packet["released_reference"]["reference"])
                continue
            print("QUERIES: "+json.dumps(packet["input"]["queries"],ensure_ascii=False))
            if mode=="outputs":
                for arm,response in packet["responses"].items():
                    if response:
                        print("\n"+arm+": "+str(response.get("output_text")))
                    elif arm!="claim_repeat":
                        print(arm+": NO RESPONSE")
            elif mode=="mapping":
                for arm in ARMS:
                    print(arm,packet["input"]["retrieval"][arm]["reference_passage_ids"])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["build","outputs","release","mapping","evidence"])
    parser.add_argument("--cases",nargs="*",default=[])
    parser.add_argument("--patient")
    parser.add_argument("--start",type=int,default=0)
    parser.add_argument("--count",type=int,default=25)
    a=parser.parse_args()
    build() if a.mode=="build" else read(a.cases,a.patient,a.start,a.count,a.mode)
