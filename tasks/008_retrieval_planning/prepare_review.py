"""Freeze balanced reading cases from the preregistered rule, with complete outputs."""
from collections import defaultdict
from pathlib import Path
import argparse
import common as c
from build_stages import seal


def prepare():
    base=c.OUT/"run_001/analysis"
    c.check_files(base)
    rows=c.pilot.read_csv(base/"transitions.csv")[1]
    before={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"preparation_001/inputs.jsonl")}
    evidence={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"judge_preparation_001/inputs.jsonl")}
    plans={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"plans_001/plans.jsonl")}
    candidates={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"candidates_001/candidates.jsonl")}
    passages={x["passage_id"]:x for x in c.pilot.jsonl(c.OUT/"preparation_001/corpus.jsonl")}
    normalized={x["request_id"]:x for x in c.pilot.jsonl(base/"normalized_responses.jsonl")}
    chosen=defaultdict(list)
    key=lambda r:c.pilot.digest_text("008/review/v1:"+r["proposition_id"])
    changes=[x for x in rows if x["planner_vs_direct"] in {"improved","worsened","changed_wrong"}]
    selected_changes=changes
    if len(changes)>24:
        selected_changes=[x for author in ("llm","human") for category in ("improved","worsened","changed_wrong") for x in sorted([r for r in changes if r["author_type"]==author and r["planner_vs_direct"]==category],key=key)[:4]]
    for x in selected_changes:
        chosen[x["proposition_id"]].append("primary_"+x["planner_vs_direct"])
    for author in ("llm","human"):
        controls=[x for x in rows if x["author_type"]==author and x["planner_vs_direct"].startswith("stable") and
            evidence[x["proposition_id"]]["retrieval"]["planner"]["body_sha256"]!=evidence[x["proposition_id"]]["retrieval"]["direct"]["body_sha256"]]
        for x in sorted(controls,key=key)[:4]:
            chosen[x["proposition_id"]].append("stable_label_evidence_change_control")
    better_simple=[x for x in rows if x["simple"]==x["human_gt"] and x["planner"]!=x["human_gt"]]
    for x in sorted(better_simple,key=key)[:6]:
        chosen[x["proposition_id"]].append("simple_correct_planner_wrong")
    packs,index=[],[]
    for r in rows:
        pid=r["proposition_id"]
        if pid not in chosen:
            continue
        item=evidence[pid]
        outputs={a:normalized[item["retrieval"][a]["request_id"]] for a in c.METHODS}
        union=sorted(set(key for a in c.METHODS for key in item["retrieval"][a]["selected_ids"]))
        packs.append(dict(row=r,selection_reasons=chosen[pid],original=before[pid],planner=plans[pid],evidence=item,
            candidate=candidates[pid],outputs=outputs,passages={key:passages[key] for key in union}))
        index.append(dict(case_id=r["case_id"],proposition_id=pid,subject_id=r["subject_id"],author_type=r["author_type"],gt=r["human_gt"],
            direct=r["direct"],simple=r["simple"],planner=r["planner"],selection_reasons=";".join(chosen[pid])))
    out=c.OUT/"run_001/review_001"
    out.mkdir(parents=True,exist_ok=False)
    c.pilot.write_jsonl(out/"case_packets.jsonl",packs)
    c.pilot.write_csv(out/"case_index.csv",index)
    c.pilot.write_json(out/"selection.json",dict(primary_changes_total=len(changes),primary_changes_selected=len(selected_changes),cases=len(index),
        fixed_rule=True,no_new_gold=True,case_ids=[r["case_id"] for r in index]))
    seal(out,[base/"manifest.json",c.OUT/"judge_preparation_001/manifest.json",c.OUT/"plans_001/manifest.json"],code_files=[Path(__file__)])
    print(c.pilot.canonical(c.read_json(out/"selection.json")))


def show(ids):
    for pack in c.pilot.jsonl(c.OUT/"run_001/review_001/case_packets.jsonl"):
        r=pack["row"]
        if r["case_id"] not in ids:
            continue
        print("\nCASE",r["case_id"],r["author_type"],"GT",r["human_gt"],{a:r[a] for a in c.METHODS})
        print("CLAIM:",pack["original"]["text"])
        print("SOURCE:",pack["original"]["source"]["local"])
        print("FULL PLANNER:",pack["planner"]["output_text"])
        # Display shared passages once, with exact per-arm reference numbers.
        for pid,p in sorted(pack["passages"].items(),key=lambda kv:(kv[1]["date"],kv[1]["time"],kv[1]["note_id"],kv[1]["start"])):
            membership={a:pack["evidence"]["retrieval"][a]["selected_ids"].index(pid)+1 for a in c.METHODS if pid in pack["evidence"]["retrieval"][a]["selected_ids"]}
            print("EHR",pid,"ARMS",membership,"NOTE",p["note_id"],p["date"],p["time"],p["category"],"OFFSET",p["start"],p["end_exclusive"])
            print(p["text"])
        seen=set()
        for arm in c.METHODS:
            output=pack["outputs"][arm]
            if output["request_id"] not in seen:
                print("FULL JUDGE",arm,output.get("output_text"))
                seen.add(output["request_id"])
            else:
                print("JUDGE",arm,"reuses preceding identical body/result")


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("cases",nargs="*")
    args=ap.parse_args()
    show(set(args.cases)) if args.cases else prepare()
