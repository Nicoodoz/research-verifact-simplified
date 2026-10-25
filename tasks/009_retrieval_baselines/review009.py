"""Freeze balanced qualitative samples and display full claim/evidence/model outputs."""
from collections import defaultdict
from pathlib import Path
import argparse
import study009 as s


def prepare(folder):
    analysis=folder/"analysis_001"
    s.check(analysis)
    rows=s.pilot.read_csv(analysis/"transitions.csv")[1]
    inputs={r["proposition_id"]:r for r in s.pilot.jsonl(folder/"judge_preparation/inputs.jsonl")}
    outputs={r["request_id"]:r for r in s.pilot.jsonl(analysis/"normalized_responses.jsonl")}
    passages={r["passage_id"]:r for r in s.pilot.jsonl(folder/"preparation/corpus.jsonl")}
    chosen=defaultdict(list)
    key=lambda row:s.pilot.digest_text("009/review/v1:"+row["proposition_id"])
    changed=[r for r in rows if any(r[k] in {"improved","worsened","changed_wrong"} for k in ("B_minus_A","C_minus_A"))]
    if folder.name.startswith("development"):
        for r in rows:
            if r["case_id"] in {"P058","P080","P081","P128"}:
                chosen[r["proposition_id"]].append("008_user_named_loss_anchor")
            if r["C_minus_A"]=="improved" or r["B_minus_A"]=="improved":
                chosen[r["proposition_id"]].append("development_gain")
        for author in ("llm","human"):
            for r in sorted([r for r in changed if r["author_type"]==author and r["B_minus_A"]=="worsened"],key=key)[:2]:
                chosen[r["proposition_id"]].append("development_regression_control")
    elif len(changed)<=24:
        for r in changed:
            chosen[r["proposition_id"]].append("all_confirmation_changes")
    else:
        for author in ("llm","human"):
            for category in ("improved","worsened","changed_wrong"):
                # Two per comparison means at most four per author/outcome cell.
                for contrast in ("B_minus_A","C_minus_A"):
                    for r in sorted([r for r in changed if r["author_type"]==author and r[contrast]==category],key=key)[:2]:
                        chosen[r["proposition_id"]].append(contrast+":"+category)
    for author in ("llm","human"):
        for kind in ("stable_correct","stable_wrong"):
            pool=[r for r in rows if r["author_type"]==author and r["B_minus_A"]==kind and r["C_minus_A"]==kind and
                any(inputs[r["proposition_id"]]["retrieval"][a].get("body_sha256")!=inputs[r["proposition_id"]]["retrieval"]["A48"].get("body_sha256") for a in ("B48","C48"))]
            for r in sorted(pool,key=key)[:1 if folder.name.startswith("development") else 2]:
                chosen[r["proposition_id"]].append(kind+"_changed_evidence")
    packets,index=[],[]
    for r in rows:
        pid=r["proposition_id"]
        if pid not in chosen:
            continue
        item=inputs[pid]
        selected=sorted({key for a in ("A48","B48","C48") for key in item["retrieval"][a].get("selected_ids",[])})
        packet=dict(row=r,input=item,reasons=chosen[pid],outputs={a:outputs.get(item["retrieval"][a].get("request_id"),{}) for a in ("A48","B48","C48")},
            passages={key:passages[key] for key in selected})
        packets.append(packet)
        index.append(dict(case_id=r["case_id"],proposition_id=pid,author_type=r["author_type"],gt=r["human_gt"],A48=r["A48"],B48=r["B48"],C48=r["C48"],reasons=";".join(chosen[pid])))
    out=folder/"review_001"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"packets.jsonl",packets)
    s.pilot.write_csv(out/"index.csv",index)
    summary=dict(cases=len(packets),total_changed=len(changed),selected_case_ids=[r["case_id"] for r in index],selection_before_full_output_read=True,
        not_gold_evidence=True,unique_model_outputs=len({x.get("request_id") for p in packets for x in p["outputs"].values() if x}))
    s.pilot.write_json(out/"selection.json",summary)
    s.seal(out,[analysis/"manifest.json",folder/"judge_preparation/manifest.json"],[Path(__file__)])
    print(s.pilot.canonical(summary))


def show(folder,case_ids):
    for packet in s.pilot.jsonl(folder/"review_001/packets.jsonl"):
        row=packet["row"]
        if row["case_id"] not in case_ids:
            continue
        print("\nCASE",row["case_id"],row["author_type"],"GT",row["human_gt"],{a:row[a] for a in ("A48","B48","C48")})
        print("CLAIM:",packet["input"]["text"])
        for pid,p in sorted(packet["passages"].items(),key=lambda pair:(pair[1]["date"],pair[1]["time"],pair[1]["note_id"],pair[1]["start"])):
            members={a:packet["input"]["retrieval"][a]["selected_ids"].index(pid)+1 for a in ("A48","B48","C48") if pid in packet["input"]["retrieval"][a].get("selected_ids",[])}
            print("EHR",p["note_id"],p["date"],p["time"],"OFFSET",p["start"],p["end_exclusive"],"REF",members,"ID",pid)
            print(p["text"])
        seen={}
        for a in ("A48","B48","C48"):
            result=packet["outputs"][a]
            rid=result.get("request_id")
            if rid in seen:
                print("JUDGE",a,"same canonical result as",seen[rid])
            else:
                print("FULL JUDGE",a,result.get("output_text"),result.get("structural_errors"))
                seen[rid]=a


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    p.add_argument("cases",nargs="*")
    a=p.parse_args()
    folder=a.folder.resolve()
    show(folder,set(a.cases)) if a.cases else prepare(folder)
